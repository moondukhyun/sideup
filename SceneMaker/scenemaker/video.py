"""ffmpeg 기반 루프 구간 인코딩 및 장시간 영상 조립.

흐름: 빗줄기 프레임 → 고화질 마스터(1회 렌더) → 길이별 용량 예산에 맞춘 루프 구간 인코딩
      → 재인코딩 없이 이어붙여 최종 영상 (+ 직접 녹음한 오디오 반복)
최종 파일 = 루프 구간의 반복이므로, 구간의 비트레이트가 곧 최종 비트레이트 → 용량을 정확히 맞출 수 있다.
"""

import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

RESOLUTIONS = {"720p": (1280, 720), "1080p": (1920, 1080), "1440p": (2560, 1440), "2160p": (3840, 2160)}
# 해상도별 비트레이트 상한 (kbps) — 짧은 영상은 용량 여유가 있어도 이 이상은 무의미
MAX_KBPS = {"720p": 8000, "1080p": 16000, "1440p": 24000, "2160p": 45000}
MIN_KBPS = 2500
DURATION_PRESETS = ["3m", "1h", "3h", "5h", "8h", "10h"]


def ffmpeg_bin():
    exe = shutil.which("ffmpeg")
    if not exe:
        raise SystemExit("ffmpeg 를 찾을 수 없습니다. PATH 에 ffmpeg 를 추가하세요.")
    return exe


def _gop(v):
    return max(1, int(v["fps"]) // 2)          # 유튜브 권장: 프레임레이트의 절반, closed GOP


def budget_kbps(duration, v):
    """최종 파일이 max_size_gb 를 넘지 않는 영상 비트레이트 (오디오·컨테이너 여유 3% 제외)."""
    cap_bits = float(v["max_size_gb"]) * 1e9 * 8 * 0.97
    audio_kbps = int(str(v["audio_bitrate"]).rstrip("k"))
    kbps = cap_bits / duration / 1000 - audio_kbps
    return int(max(MIN_KBPS, min(MAX_KBPS[v["resolution"]], kbps)))


def _rate_args(v, kbps):
    enc, g = v["encoder"], str(_gop(v))
    common = ["-g", g, "-bf", "2", "-pix_fmt", "yuv420p",
              "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
    if enc == "hevc_nvenc":
        return ["-c:v", "hevc_nvenc", "-preset", "p7", "-tune", "hq", "-rc", "vbr", "-multipass", "fullres",
                "-b:v", f"{kbps}k", "-maxrate", f"{int(kbps * 1.5)}k", "-bufsize", f"{kbps * 2}k",
                "-profile:v", "main", "-tag:v", "hvc1", "-strict_gop", "1", *common]
    if enc == "h264_nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p7", "-tune", "hq", "-rc", "vbr", "-multipass", "fullres",
                "-b:v", f"{kbps}k", "-maxrate", f"{int(kbps * 1.5)}k", "-bufsize", f"{kbps * 2}k",
                "-profile:v", "high", "-strict_gop", "1", *common]
    if enc == "libx265":
        return ["-c:v", "libx265", "-preset", v["preset"], "-b:v", f"{kbps}k",
                "-x265-params", f"keyint={g}:min-keyint={g}:no-open-gop=1:vbv-maxrate={int(kbps * 1.5)}:"
                                f"vbv-bufsize={kbps * 2}", "-tag:v", "hvc1", *common]
    return ["-c:v", "libx264", "-preset", v["preset"], "-b:v", f"{kbps}k",
            "-maxrate", f"{int(kbps * 1.5)}k", "-bufsize", f"{kbps * 2}k",
            "-profile:v", "high", "-x264-params", "open-gop=0", *common]


def render_threads(renderer):
    """프레임을 동시에 그릴 스레드 수. 환경변수 LOOPMAKER_THREADS 로 지정(1 = 끔), 없으면 CPU 코어 수에 맞춰 자동.
    Wan(AI 움직임)을 쓰는 경우는 안전을 위해 한 프레임씩."""
    import os as _os
    env = _os.environ.get("LOOPMAKER_THREADS", "").strip()
    if env.isdigit():
        return max(1, min(16, int(env)))
    if getattr(renderer, "wan_room", None) is not None or "wan" in type(getattr(renderer, "motion", None)).__name__.lower():
        return 1
    n = _os.cpu_count() or 2
    return max(1, min(6, n - 1))


def render_master(renderer, out_path, v, limit=None):
    """빗줄기 합성 프레임을 거의 무손실 마스터로 1회 렌더 (길이별 인코딩의 원본)."""
    out_path = Path(out_path)
    total = min(renderer.N, int(limit)) if limit else renderer.N                  # limit: 샘플용 — 루프 앞부분만
    cmd = [
        ffmpeg_bin(), "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{renderer.W}x{renderer.H}",
        "-r", str(v["fps"]), "-i", "-",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "6", "-pix_fmt", "yuv420p",
        "-g", str(_gop(v)), str(out_path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    workers = render_threads(renderer)
    if workers > 1:
        print(f"  렌더링 스레드 {workers}개로 여러 프레임을 동시에 그려요 (CPU 코어 {os.cpu_count()}개)")
    try:
        if workers <= 1:
            frames = (renderer.frame(f) for f in range(total))
            pool = None
        else:
            from concurrent.futures import ThreadPoolExecutor
            pool = ThreadPoolExecutor(workers)
            ahead = workers * 2                                  # 앞서 그려 둘 프레임 수 (메모리: 프레임당 약 11MB @1440p)
            futs = {}
            nxt = 0

            def _gen():
                nonlocal nxt
                for f in range(total):
                    while nxt < total and nxt < f + ahead:
                        futs[nxt] = pool.submit(renderer.frame, nxt)
                        nxt += 1
                    yield futs.pop(f).result()
            frames = _gen()
        for f, fr in enumerate(frames):
            proc.stdin.write(fr.tobytes())
            if f % max(1, total // 20) == 0 or f == total - 1:
                pct = (f + 1) / total
                eta = (time.time() - t0) / pct * (1 - pct)
                sys.stdout.write(f"\r  루프 구간 렌더링 {f + 1}/{total} ({pct:4.0%}, 남은 시간 ~{eta:.0f}s)")
                sys.stdout.flush()
        if pool is not None:
            pool.shutdown(wait=True)
    finally:
        if workers > 1 and 'pool' in locals() and pool is not None:
            pool.shutdown(wait=False, cancel_futures=True)
        proc.stdin.close()
        rc = proc.wait()
    print()
    if rc != 0:
        raise SystemExit(f"ffmpeg 렌더링 실패 (exit {rc})")
    return out_path


def encode_segment(master, out_path, v, kbps):
    cmd = [ffmpeg_bin(), "-y", "-loglevel", "error", "-i", str(master), *_rate_args(v, kbps),
           "-an", "-movflags", "+faststart", str(out_path)]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"구간 인코딩 실패 ({v['encoder']}, exit {e.returncode})")
    return Path(out_path)


def segment_for_duration(master, job, duration, v, cache):
    """duration 길이 영상이 용량 상한을 넘지 않는 구간 파일 (같은 비트레이트면 재사용)."""
    kbps = budget_kbps(duration, v)
    for attempt in range(3):
        if kbps in cache:
            return cache[kbps], kbps
        seg = Path(job) / f"loop_segment_{v['resolution']}_{kbps}k.mp4"
        encode_segment(master, seg, v, kbps)
        seg_len = v["loop_seconds"]
        audio_bytes = int(str(v["audio_bitrate"]).rstrip("k")) * 1000 / 8 * duration
        projected = seg.stat().st_size * (duration / seg_len) + audio_bytes
        if projected <= float(v["max_size_gb"]) * 1e9 or kbps <= MIN_KBPS:
            cache[kbps] = seg
            return seg, kbps
        # 인코더가 목표보다 크게 만든 경우: 비율만큼 낮춰 재시도
        seg.unlink(missing_ok=True)
        kbps = max(MIN_KBPS, int(kbps * float(v["max_size_gb"]) * 1e9 / projected * 0.97))
    cache[kbps] = seg
    return seg, kbps


def _probe_seconds(path):
    out = subprocess.run([shutil.which("ffprobe") or "ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True)
    return float(out.stdout.strip() or 0)


def loopable_audio(audio, job, fade=3.0):
    """녹음 파일의 끝을 처음과 크로스페이드해 이음새 없이 반복되는 WAV 로 (한 번 만들고 재사용).
    반복 재생 시: ...끝(처음과 겹쳐 서서히 전환) → 처음 이후 부분 으로 자연스럽게 이어진다."""
    audio = Path(audio)
    L = _probe_seconds(audio)
    if L < fade * 4:
        return audio                      # 너무 짧으면 그대로 반복
    out = Path(job) / f"audio_loop_{audio.stem[:40]}.wav"
    if out.exists() and out.stat().st_mtime >= audio.stat().st_mtime:
        return out
    x = fade
    graph = (f"[0:a]aresample=48000,asplit=3[a][b][c];"
             f"[a]atrim={x}:{L - x},asetpts=PTS-STARTPTS[mid];"
             f"[b]atrim={L - x}:{L},asetpts=PTS-STARTPTS[tail];"
             f"[c]atrim=0:{x},asetpts=PTS-STARTPTS[head];"
             f"[tail][head]acrossfade=d={x}:c1=qsin:c2=qsin[xf];"
             f"[mid][xf]concat=n=2:v=0:a=1[out]")
    subprocess.run([ffmpeg_bin(), "-y", "-loglevel", "error", "-i", str(audio), "-filter_complex", graph,
                    "-map", "[out]", "-c:a", "pcm_s16le", str(out)], check=True)
    print(f"  오디오 루프: {audio.name} ({L / 60:.1f}분) → 끝·처음 {x:.0f}초 크로스페이드")
    return out


def assemble(segment, out_path, duration, v, audio=None, extra=None):
    """루프 구간을 재인코딩 없이 이어붙여 duration 초 길이 영상 생성 (+ 오디오 반복)."""
    segment, out_path = Path(segment), Path(out_path)
    seg_len = v["loop_seconds"]
    repeats = max(1, math.ceil(duration / seg_len))
    listfile = out_path.with_suffix(".concat.txt")
    join_src = segment
    ts = segment.with_suffix(".ts")
    try:                                                         # 구간을 MPEG-TS 로 바꿔 이어붙이면 이음새의 타임스탬프가 어긋나지 않음
        if not ts.exists() or ts.stat().st_mtime < segment.stat().st_mtime:
            subprocess.run([ffmpeg_bin(), "-y", "-loglevel", "error", "-i", str(segment), "-c", "copy", "-f", "mpegts", str(ts)], check=True)
        join_src = ts
    except (subprocess.CalledProcessError, OSError):
        join_src = segment
    line = f"file '{join_src.resolve().as_posix()}'\n"
    listfile.write_text(line * repeats, encoding="utf-8")

    def build(normalize):
        cmd = [ffmpeg_bin(), "-y", "-loglevel", "error", "-stats",
               "-f", "concat", "-safe", "0", "-i", str(listfile)]
        if audio and extra:                        # 녹음 오디오 + 합성 환경음(벽난로 등)을 섞음 (v11.22)
            cmd += ["-stream_loop", "-1", "-i", str(audio)]
            labels, parts = ["[a0]"], ["[1:a]aresample=48000[a0]"]
            for i, (path, db) in enumerate(extra):
                cmd += ["-stream_loop", "-1", "-i", str(path)]
                parts.append(f"[{i + 2}:a]aresample=48000,volume={db:.1f}dB[a{i + 1}]")
                labels.append(f"[a{i + 1}]")
            mix = f"amix=inputs={len(labels)}:duration=first" + (":normalize=0" if normalize else "")
            tail = "" if normalize else f",volume={len(labels)}"
            cmd += ["-filter_complex", ";".join(parts) + ";" + "".join(labels) + mix + tail + ",alimiter=limit=0.97[am]",   # 합쳐서 커져도 찌그러지지 않게
                    "-map", "0:v", "-map", "[am]", "-c:a", "aac", "-b:a", v["audio_bitrate"], "-ar", "48000"]
        elif audio:
            cmd += ["-stream_loop", "-1", "-i", str(audio),
                    "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", v["audio_bitrate"], "-ar", "48000"]
        cmd += ["-c:v", "copy", *(["-tag:v", "hvc1"] if v.get("encoder") in ("hevc_nvenc", "libx265") else []),
                "-t", f"{duration:.3f}", "-movflags", "+faststart", str(out_path)]
        return cmd

    try:
        try:
            subprocess.run(build(True), check=True)
        except subprocess.CalledProcessError:
            if not (audio and extra):
                raise
            subprocess.run(build(False), check=True)      # 오래된 ffmpeg: amix normalize 옵션 없음
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"영상 조립 실패 (exit {e.returncode})")
    finally:
        listfile.unlink(missing_ok=True)
    return out_path


def seam_report(final, seg_len, fps, joins=3):
    """완성 영상의 루프 이음새(예: 20초, 40초 지점)를 실제로 확인해 로그로 알려 준다.
    ① 프레임 시간 간격이 어긋난(멈칫·중복·누락) 곳 수  ② 이음새 앞뒤의 화면 변화량이 평소 변화량과 비슷한지."""
    import numpy as np
    out = {"timing": None, "joins": []}
    try:
        head = f"%+{seg_len * (joins + 1) + 10:.0f}"                  # 10시간 영상도 앞부분(이음새 몇 개)만 읽어서 몇 초 안에 끝냄
        probe = subprocess.run([shutil.which("ffprobe") or "ffprobe", "-v", "error", "-select_streams", "v", "-read_intervals", head,
                                "-show_entries", "frame=pts_time", "-of", "csv=p=0", str(final)], capture_output=True, text=True, timeout=300)
        pts = sorted(float(x) for x in probe.stdout.replace(",", " ").split() if x.strip())
        if len(pts) > 3:
            d = np.diff(pts)
            bad = int(((d > 1.6 / fps) | (d < 0.4 / fps)).sum())
            out["timing"] = (len(pts), bad)
        N = int(round(seg_len * fps))
        total = len(pts) if pts else 0
        idx = []
        for k in range(1, joins + 1):
            j = k * N
            if total and j + 3 < total:
                idx += list(range(j - 3, j + 3))
        idx += list(range(200, 206))
        if not idx:
            return out
        sel = "+".join(f"eq(n\\,{i})" for i in idx)
        gw, gh = 160, 90
        raw = subprocess.run([ffmpeg_bin(), "-loglevel", "error", "-t", f"{seg_len * (joins + 1) + 10:.0f}", "-i", str(final), "-vf", f"select='{sel}',scale={gw}:{gh},format=gray",
                              "-vsync", "0", "-f", "rawvideo", "-"], capture_output=True, timeout=600).stdout
        fr = np.frombuffer(raw, np.uint8).reshape(-1, gh, gw).astype(np.float32)
        order = sorted(idx)
        if len(fr) != len(order):
            return out
        pos = {n: i for i, n in enumerate(order)}
        def hf(a):                                               # 가는 빗줄기·방울의 양 (고주파 에너지)
            return float(np.abs(np.diff(a, axis=1)).mean() + np.abs(np.diff(a, axis=0)).mean())
        typ = np.mean([np.abs(fr[pos[n + 1]] - fr[pos[n]]).mean() for n in range(200, 205)])
        typ_hf = np.mean([hf(fr[pos[n]]) for n in range(200, 206)])
        for k in range(1, joins + 1):
            j = k * N
            if j - 1 in pos and j in pos:
                step = float(np.abs(fr[pos[j]] - fr[pos[j - 1]]).mean())
                near_hf = np.mean([hf(fr[pos[n]]) for n in range(j - 3, j + 3) if n in pos])
                out["joins"].append((k * seg_len, step, float(typ), near_hf / (typ_hf + 1e-6)))
    except Exception:
        pass
    return out


def print_seam_report(rep, seg_len):
    if rep.get("timing"):
        n, bad = rep["timing"]
        print(f"  이음새 점검: 프레임 {n}장 중 시간 간격이 어긋난 곳 {bad}곳" + (" ✅" if bad == 0 else " ⚠ (멈칫·중복 프레임)"))
    for t, step, typ, hfr in rep.get("joins", []):
        ok = step < 2.5 * max(typ, 0.05) and hfr > 0.75
        print(f"  이음새 점검 {t:.0f}초 지점: 앞뒤 화면 변화 {step:.2f} (평소 {typ:.2f}) · 빗줄기 양 평소의 {hfr:.0%}" + (" ✅" if ok else " ⚠ 이음새에서 끊김"))


def parse_durations(value, parse_duration):
    """'3m,1h,10h' 또는 'all' → 초 목록 (중복 제거, 짧은 순)."""
    items = DURATION_PRESETS if str(value).strip().lower() == "all" else str(value).split(",")
    return sorted({parse_duration(x.strip()) for x in items if x.strip()})
