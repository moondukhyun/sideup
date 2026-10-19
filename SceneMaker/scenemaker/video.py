"""ffmpeg 기반 루프 구간 인코딩 및 장시간 영상 조립.

흐름: 빗줄기 프레임 → 고화질 마스터(1회 렌더) → 길이별 용량 예산에 맞춘 루프 구간 인코딩
      → 재인코딩 없이 이어붙여 최종 영상 (+ 직접 녹음한 오디오 반복)
최종 파일 = 루프 구간의 반복이므로, 구간의 비트레이트가 곧 최종 비트레이트 → 용량을 정확히 맞출 수 있다.
"""

import math
import shutil
import subprocess
import sys
import time
from pathlib import Path

RESOLUTIONS = {"1080p": (1920, 1080), "1440p": (2560, 1440), "2160p": (3840, 2160)}
# 해상도별 비트레이트 상한 (kbps) — 짧은 영상은 용량 여유가 있어도 이 이상은 무의미
MAX_KBPS = {"1080p": 16000, "1440p": 24000, "2160p": 45000}
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


def render_master(renderer, out_path, v):
    """빗줄기 합성 프레임을 거의 무손실 마스터로 1회 렌더 (길이별 인코딩의 원본)."""
    out_path = Path(out_path)
    cmd = [
        ffmpeg_bin(), "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{renderer.W}x{renderer.H}",
        "-r", str(v["fps"]), "-i", "-",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "6", "-pix_fmt", "yuv420p",
        "-g", str(_gop(v)), str(out_path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    try:
        for f in range(renderer.N):
            proc.stdin.write(renderer.frame(f).tobytes())
            if f % max(1, renderer.N // 20) == 0 or f == renderer.N - 1:
                pct = (f + 1) / renderer.N
                eta = (time.time() - t0) / pct * (1 - pct)
                sys.stdout.write(f"\r  루프 구간 렌더링 {f + 1}/{renderer.N} ({pct:4.0%}, 남은 시간 ~{eta:.0f}s)")
                sys.stdout.flush()
    finally:
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
    line = f"file '{segment.resolve().as_posix()}'\n"
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
            cmd += ["-filter_complex", ";".join(parts) + ";" + "".join(labels) + mix + tail + "[am]",
                    "-map", "0:v", "-map", "[am]", "-c:a", "aac", "-b:a", v["audio_bitrate"], "-ar", "48000"]
        elif audio:
            cmd += ["-stream_loop", "-1", "-i", str(audio),
                    "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", v["audio_bitrate"], "-ar", "48000"]
        cmd += ["-c:v", "copy", "-t", f"{duration:.3f}", "-movflags", "+faststart", str(out_path)]
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


def parse_durations(value, parse_duration):
    """'3m,1h,10h' 또는 'all' → 초 목록 (중복 제거, 짧은 순)."""
    items = DURATION_PRESETS if str(value).strip().lower() == "all" else str(value).split(",")
    return sorted({parse_duration(x.strip()) for x in items if x.strip()})
