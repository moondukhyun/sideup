import argparse

import numpy as np
import json
import random
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

from PIL import Image

from .comfy import ComfyClient, ComfyError, build_img2img, build_txt2img, build_zimage, fit_cover, naturalize
from .config import format_duration, load_config, parse_duration
from . import lora as lora_mod
from . import variety
from . import details as details_mod
from .rain import RainRenderer, RainSettings
from .scenes import NATURAL_COMFY, NATURAL_NEGATIVE, NATURAL_POST, NATURAL_STYLE, NEGATIVE, SCENES, get_scene
from .video import (RESOLUTIONS, assemble, budget_kbps, ffmpeg_bin, loopable_audio, parse_durations,
                    render_master, segment_for_duration)

RAIN_OPTS = ["intensity", "angle", "speed", "brightness", "darken", "fog", "lightning", "grade", "grain"]


# ---------- 공통 ----------
def _job_dir(cfg, label):
    d = Path(cfg["output"]["dir"]) / f"{datetime.now():%Y%m%d_%H%M%S}_{label}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _scene_names(arg):
    return list(SCENES) if arg == "all" else [get_scene(arg).name]


def _rain_settings(cfg, scene_name, args, job_rain=None):
    """우선순위: config < 씬 < 이미지 생성 때 정한 다양화 값(meta) < 명령줄."""
    scene_rain = get_scene(scene_name).rain if scene_name else {}
    cli = {k: getattr(args, k, None) for k in RAIN_OPTS}
    if getattr(args, "no_splashes", False):
        cli["splashes"] = False
    if getattr(args, "classic_rain", False):
        cli["style"] = "classic"
    if getattr(args, "no_wet", False):          # v11.19: 젖은 바위·물줄기·수면 빗방울 끄기
        cli["wet"] = 0.0
        cli["water_rain"] = 0.0
    return RainSettings.from_dict(cfg["rain"], scene_rain, job_rain or {}, cli)


def _read_meta(job):
    p = Path(job) / "meta.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _write_meta(job, **updates):
    meta = _read_meta(job)
    meta.update(updates)
    (Path(job) / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _post_args(post):
    """scenes 의 post dict → naturalize 인자 ('autumn_mute' 는 짧은 이름)."""
    p = dict(post or {})
    if "autumn_mute" in p:
        p["autumn_mute_strength"] = p.pop("autumn_mute")
    return p


def _parse_lora(spec):
    name, _, strength = spec.partition(":")
    if not name.endswith(".safetensors"):
        name += ".safetensors"
    return name, float(strength) if strength else 0.8


def lora_trigger(name):
    """somnia_hanok-000004.safetensors -> somnia_hanok (학습 시 트리거 단어 = 파일명)."""
    stem = Path(name).stem
    base, _, suffix = stem.rpartition("-")
    return base if base and suffix.isdigit() else stem


def _resolve_loras(client, cfg, scene, cli_loras):
    """config + 씬 + --lora 를 합쳐, ComfyUI 에 실제 설치된 것만 반환."""
    specs = list(cfg["comfy"].get("loras", []))
    if scene.lora:
        specs.append(scene.lora)
    specs += cli_loras or []
    if not specs:
        return []
    installed = set(client.loras())
    out = []
    for spec in specs:
        # "A|B": 설치된 첫 번째 LoRA 사용
        options = [_parse_lora(o) for o in spec.split("|")]
        found = next(((n, w) for n, w in options if n in installed), None)
        if found:
            out.append(found)
            continue
        name = options[0][0]
        if spec in (cli_loras or []):
            raise SystemExit(f"LoRA 를 찾을 수 없습니다: {name} (설치됨: {', '.join(sorted(installed)) or '없음'})")
    return out


# ---------- 이미지 생성 ----------
def generate_images(cfg, scene_name, count, seed=None, extra="", cli_loras=None, diversify=True,
                    rain_level=None):
    scene = get_scene(scene_name)
    # 우선순위: config < 씬 설정 < 명령줄(--checkpoint)
    c = {**cfg["comfy"], **scene.comfy, **cfg.get("comfy_cli", {})}
    c["upscale_to"] = (cfg["output"]["width"], cfg["output"]["height"])
    if not c["checkpoint"]:
        raise SystemExit("config.toml 의 [comfy] checkpoint 를 설정하세요. (`python -m scenemaker check` 로 목록 확인)")
    client = ComfyClient(c["url"], max(c["timeout"], 1800) if c.get("upscale_model") else c["timeout"])
    family = c.get("family", "sdxl")
    if family == "zimage" and (scene.lora or cli_loras or c.get("loras")):
        print("  (Z-Image: SDXL 용 LoRA 는 호환되지 않아 적용하지 않음)")
    loras = [] if family == "zimage" else _resolve_loras(client, cfg, scene, cli_loras)
    triggers = ", ".join(dict.fromkeys(lora_trigger(n) for n, _ in loras))
    if loras:
        print(f"LoRA 적용: {', '.join(f'{n}({w})' for n, w in loras)}")
    W, H = cfg["output"]["width"], cfg["output"]["height"]
    jobs = []
    for i in range(count):
        s = seed + i if seed is not None else random.randrange(2**32)
        picks, rain_override = {}, {}
        if diversify:
            vtext, picks = variety.diversify(scene.name, s, rain_level)
            rain_override = variety.jitter_rain({**cfg["rain"], **scene.rain}, s, rain_level)
            extra_s = ", ".join(x for x in (extra, vtext) if x)
        else:
            extra_s = extra
        positive, negative = scene.build_prompt(random.Random(s), extra_s)
        if triggers:
            positive = f"{triggers}, {positive}"
        print(f"[{scene.name}] 이미지 생성 {i + 1}/{count} (seed={s}) ...")
        t0 = time.time()
        if family == "zimage":
            img = client.generate(build_zimage(c, positive, negative, s, prefix=f"scenemaker/{scene.name}"))[0]
        else:
            img = client.generate(build_txt2img(c, positive, negative, s, prefix=f"scenemaker/{scene.name}",
                                                loras=loras))[0]
        job = _job_dir(cfg, f"{scene.name}_{s}")
        img = fit_cover(img, W, H)
        if scene.post:
            img = naturalize(img, seed=s, **_post_args(scene.post))
        img.save(job / "background.png")
        variety.warn_similar(img, "이 배경은")
        _write_meta(job, variety=picks, rain_override=rain_override)
        _write_meta(job, scene=scene.name, title=scene.title, seed=s, prompt=positive,
                    negative=negative, checkpoint=c["checkpoint"] if family != "zimage" else "z-image-turbo",
                    loras=[list(l) for l in loras],
                    size=[W, H])
        print(f"  -> {job / 'background.png'} ({time.time() - t0:.0f}s)"
              + (f"  [{', '.join(picks.values())}]" if picks else ""))
        jobs.append(job)
    return jobs


# ---------- 루프 영상 ----------
def make_loop(cfg, image, scene_name, args, job=None):
    image = Path(image)
    if not image.exists():
        raise SystemExit(f"이미지를 찾을 수 없습니다: {image}")
    v = dict(cfg["video"])
    for key in ("loop_seconds", "encoder", "resolution", "max_size_gb"):
        if getattr(args, key, None):
            v[key] = getattr(args, key)
    durations = parse_durations(getattr(args, "duration", None) or v["duration"], parse_duration)

    if job is None:
        job = image.parent if (image.parent / "meta.json").exists() else _job_dir(cfg, image.stem)
        if image.parent != job:
            shutil.copy(image, job / "background.png")
    meta = _read_meta(job)
    scene_name = scene_name or meta.get("scene")

    W, H = RESOLUTIONS[v["resolution"]]
    bg = fit_cover(Image.open(image).convert("RGB"), W, H)
    rs = _rain_settings(cfg, scene_name, args, meta.get("rain_override"))
    if variety.warn_similar(bg, "이 배경은"):
        print("  → 다른 배경을 쓰거나, 그대로 쓰려면 무시하세요.")
    renderer = RainRenderer(bg, rs, v["fps"], v["loop_seconds"])
    v["loop_seconds"] = renderer.N / v["fps"]
    _attach_details(cfg, renderer, job, bg, rs, args)
    if getattr(args, "wan", False):
        _attach_wan(cfg, renderer, job, bg, meta, args)

    renderer.frame_image(0).save(job / "preview.png")
    print(f"미리보기: {job / 'preview.png'}  ({W}x{H})")
    master = render_master(renderer, job / "loop_master.mp4", v)
    _write_meta(job, rain=vars(rs), video={k: v[k] for k in ("fps", "loop_seconds", "encoder", "resolution",
                                                             "max_size_gb")})

    if getattr(args, "segment_only", False):
        seg, kbps = segment_for_duration(master, job, max(durations), v, {})
        print(f"루프 구간: {seg} ({kbps}kbps)")
        return seg
    audio = getattr(args, "audio", None)
    if audio and not Path(audio).exists():
        raise SystemExit(f"오디오 파일을 찾을 수 없습니다: {audio}")

    if audio:
        audio = loopable_audio(audio, job)
    cache, finals = {}, []
    for duration in durations:
        label = format_duration(duration)
        seg, kbps = segment_for_duration(master, job, duration, v, cache)
        final = job / f"final_{label}_{v['resolution']}.mp4"
        print(f"[{label}] 조립 중 — {v['resolution']} {v['encoder']} {kbps / 1000:.1f}Mbps")
        assemble(seg, final, duration, v, audio=audio)
        gb = final.stat().st_size / 1e9
        print(f"  -> {final.name}  {gb:.2f}GB (상한 {v['max_size_gb']}GB)")
        finals.append({"file": final.name, "duration": duration, "kbps": kbps, "gb": round(gb, 2)})
    _write_meta(job, finals=finals, audio=str(audio) if audio else None)
    n = variety.mark_used(job / "background.png", note=", ".join(f["file"] for f in finals))
    print(f"완료: {len(finals)}개 영상  (사용 기록 {n}개)")
    return finals


def _attach_wan(cfg, renderer, job, bg, meta, args):
    """4단계: Wan 2.2 로 물·안개 부분만 AI 움직임 (잎은 기존 절차적 흔들림 유지)."""
    from . import wanmotion
    from .motion import vegetation_mask
    client = ComfyClient(cfg["comfy"]["url"], timeout=3600)
    try:
        client.ping()
    except ComfyError as e:
        raise SystemExit(f"Wan 움직임에는 ComfyUI 가 필요합니다: {e}")
    prompt = wanmotion.wan_prompt(extra=getattr(args, "wan_prompt", "") or "")
    seed = args.wan_seed if getattr(args, "wan_seed", None) is not None else int(meta.get("seed", 7))
    frames = wanmotion.generate_clip(client, bg, job, prompt, seed)
    dp = Path(job) / "depth.png"
    depth = (np.asarray(Image.open(dp).convert("L").resize(bg.size, Image.BILINEAR), dtype=np.float32) / 255.0
             if dp.exists() else np.zeros((bg.size[1], bg.size[0]), np.float32))
    wm = wanmotion.WanMotion(renderer.bg, frames, renderer.N, renderer.fps, base=renderer.motion,
                             veg=vegetation_mask(renderer.bg, depth), period=getattr(args, "wan_period", None))
    wanmotion.mask_preview(renderer.bg, wm, Path(job) / "wan" / "mask.jpg")
    if not wm.active:
        print("  Wan 움직임: 물·안개로 볼 만한 움직임이 없어 사용하지 않음")
        return
    renderer.motion = wm
    print(f"  Wan 움직임: 화면의 {wm.coverage:.0%} (물·안개), {wm.frames_per_cycle / renderer.fps:.1f}초 주기"
          f"  — 적용 영역 확인: wan\\mask.jpg")
    rs = renderer.s
    if rs.water_rain > 0 and not getattr(args, "no_wet", False) and getattr(renderer, "_depth_full", None) is not None:
        _attach_water(renderer, rs, renderer._depth_full, extra=wm.mask[..., 0])   # 흐르는 물 위에도 빗방울


def _set_rain_depth(renderer, bg, depth_path):
    """깊이 지도(없으면 화면 위치·하늘로 추정)를 빗줄기 거리 계산에만 사용."""
    if depth_path:
        d = np.asarray(Image.open(depth_path).convert("L").resize(bg.size, Image.BILINEAR), dtype=np.float32) / 255.0
    else:
        from .finish import estimate_depth
        d = estimate_depth(np.asarray(bg, dtype=np.float32) / 255.0)
        print("  깊이 지도 없음 → 화면 위치로 대략 추정해 거리별 빗줄기 적용")
    renderer.set_depth(d)


def _attach_details(cfg, renderer, job, bg, rs, args):
    """깊이 지도로 땅 물 튀김·물웅덩이 물결·모서리 물방울 + 잎 흔들림·물 일렁임 + (v11.19) 젖은 바위·물줄기·수면 빗방울.

    v11.19 수정: 예전에는 '땅 물 튀김'(splashes)이 꺼진 씬(계곡·호수·나뭇잎)이면 잎 흔들림까지 통째로 건너뛰었다.
    잎 흔들림·물 일렁임은 물 튀김과 별개이므로 따로 판단한다. (깊이 모델이 없어도 추정 깊이로 잎은 흔들림)"""
    src = Path(job) / "background.png"
    depth_rain = renderer.depth_style           # 거리별 빗줄기는 물 디테일을 꺼도 깊이를 씀
    no_details = getattr(args, "no_details", False)
    no_motion = getattr(args, "no_motion", False)
    no_wet = getattr(args, "no_wet", False)
    want_window = rs.window and not no_details
    want_details = rs.splashes and not rs.window and not no_details
    want_motion = not rs.window and not no_motion
    want_wet = not rs.window and not no_wet and (rs.wet > 0 or rs.water_rain > 0)
    if not (want_window or want_details or want_motion or want_wet):
        if depth_rain:
            dp = details_mod.depth_map(src, Path(job) / "depth.png", cfg) if src.exists() else None
            _set_rain_depth(renderer, bg, dp)
        return
    depth = details_mod.depth_map(src, Path(job) / "depth.png", cfg) if src.exists() else None
    real = bool(depth)
    if real:
        dfull = np.asarray(Image.open(depth).convert("L").resize(bg.size, Image.BILINEAR), dtype=np.float32) / 255.0
    else:
        from .finish import estimate_depth
        dfull = estimate_depth(np.asarray(bg, dtype=np.float32) / 255.0)
        if depth_rain:
            print("  깊이 지도 없음 → 화면 위치로 대략 추정해 거리별 빗줄기 적용")
    if real or depth_rain:
        renderer.set_depth(dfull)
    if want_window:
        if not real:
            return
        from .glass import GlassRain, window_mask
        renderer.glass = GlassRain(renderer.bg, window_mask(dfull, renderer.bg), renderer.N, renderer.fps,
                                   amount=rs.intensity, seed=rs.seed)
        print(f"  창 유리: 작은 물방울 4그룹 · 흘러내리는 방울 {len(renderer.glass.sliders)}개")
        return
    if not real and (want_motion or want_wet):
        print("  깊이 지도 없음 → 추정 깊이로 잎 흔들림·젖은 바위만 적용 (물 튀김·물웅덩이는 생략)")
    maps = (details_mod.build_maps(bg, Image.open(depth).resize(bg.size, Image.BILINEAR), seed=rs.seed)
            if real else None)
    if want_details and real:
        renderer.details = details_mod.WeatherDetails(maps, renderer.W, renderer.H, renderer.N, renderer.fps,
                                                      intensity=rs.intensity, seed=rs.seed)
        d = renderer.details
        print(f"  디테일: 물 튀김 {len(d.splashes)} · 물결 {len(d.ripples)} · 물방울 {len(d.drips)} (루프당)")
    renderer._depth_full = dfull
    if want_wet and rs.wet > 0:
        rock = _attach_wet(renderer, job, dfull, rs)   # 배경 자체를 젖은 돌로 바꾸므로 잎 흔들림보다 먼저
        if rock is not None and maps is not None:
            maps["puddle"] = maps["puddle"] * (1.0 - np.clip(rock * 1.5, 0, 1))   # 바위가 물처럼 일렁이지 않게
    if want_motion:
        from .motion import BackgroundMotion
        if maps is None:
            zero = np.zeros_like(dfull)
            maps = {"depth": dfull, "puddle": zero, "ground": zero}
        renderer.motion = BackgroundMotion(renderer.bg, maps["depth"], maps["puddle"], renderer.N, seed=rs.seed,
                                           fps=renderer.fps, foliage=rs.foliage, exclude=maps["ground"],
                                           kicks=rs.leaf_kicks)
        print(f"  배경 움직임: {'잎 흔들림·물 일렁임' if renderer.motion.active else '해당 영역 없음 (초록 잎을 거의 못 찾음)'}")
    if want_wet and rs.water_rain > 0:
        _attach_water(renderer, rs, dfull)


def _attach_wet(renderer, job, dfull, rs):
    """바위 영역을 찾아 젖은 돌로 바꾸고, 바위 면을 따라 흘러내리는 물줄기를 붙인다 (wet_mask.jpg 로 영역 확인)."""
    from .motion import foliage_mask
    from .wetrock import WetRocks, rock_mask, wet_look
    veg = foliage_mask(renderer.bg, dfull, rs.foliage)
    m = rock_mask(renderer.bg, dfull, veg)
    cov = float((m > 0.5).mean())
    if cov < 0.02:
        print("  젖은 바위: 바위로 볼 만한 영역이 거의 없어 사용하지 않음")
        return None
    renderer.bg = wet_look(renderer.bg, m, rs.wet, renderer.res)
    renderer.wet = WetRocks(renderer.bg, m, renderer.N, renderer.fps, wet=rs.wet, seed=rs.seed)
    tint = (np.clip(renderer.bg, 0, 1) * 255).astype(np.float32)
    tint[..., 0] = tint[..., 0] * (1 - m * 0.5) + 255 * m * 0.5
    Image.fromarray(np.clip(tint, 0, 255).astype(np.uint8)).resize((1280, 720)).save(Path(job) / "wet_mask.jpg")
    print(f"  젖은 바위: 화면의 {cov:.0%} · 흘러내리는 물줄기 {len(renderer.wet.rivulets)}개"
          f"  — 적용 영역 확인: wet_mask.jpg (빨간색)")
    return m


def _attach_water(renderer, rs, dfull, extra=None):
    """계곡·호수 수면에 떨어지는 빗방울 물결 (waterrain.py). extra: Wan 이 움직인 물 영역도 수면으로 인정."""
    from .waterrain import WaterRain, water_mask
    m = water_mask(renderer.bg, dfull, extra)
    cov = float(m.mean())
    if cov < 0.02:
        print("  수면 빗방울: 물 영역이 거의 없어 사용하지 않음")
        return
    renderer.water = WaterRain(m, dfull, renderer.W, renderer.H, renderer.N, renderer.fps,
                               intensity=rs.intensity * rs.water_rain, seed=rs.seed)
    print(f"  수면 빗방울: 물 영역 {cov:.0%} · 루프당 {renderer.water.count}개")


def cmd_realloop(cfg, args):
    """직접 촬영한 영상 구간을 끝·처음 크로스페이드로 이음새 없는 루프로 만들고, 업스케일·용량 예산에 맞춰 장시간 영상 생성."""
    import subprocess
    src = Path(args.video)
    if not src.exists():
        raise SystemExit(f"영상을 찾을 수 없습니다: {src}")
    v = dict(cfg["video"])
    for key in ("resolution", "max_size_gb", "encoder"):
        if getattr(args, key, None):
            v[key] = getattr(args, key)
    W, H = RESOLUTIONS[v["resolution"]]
    L, X = float(args.length), float(args.crossfade)
    job = _job_dir(cfg, f"real_{src.stem[:30]}")
    master = job / "loop_master.mp4"
    # [start, start+L+X] 를 잘라, 앞 L 초 + (끝 X 초를 처음 X 초 위에 겹침) → 길이 L 의 무이음새 루프
    s0 = float(args.start)
    vf = (f"[0:v]trim={s0}:{s0 + L + X},setpts=PTS-STARTPTS,fps={v['fps']},"
          f"scale={W}:{H}:flags=lanczos,unsharp=5:5:0.5,format=yuv420p,split[a][b];"
          f"[a]trim=0:{X},setpts=PTS-STARTPTS[head];"
          f"[a2]null[dummy];"
          f"[b]trim={X}:{L + X},setpts=PTS-STARTPTS,split[body][tailsrc];"
          f"[tailsrc]trim={L - X}:{L},setpts=PTS-STARTPTS[tail];"
          f"[body]trim=0:{L - X},setpts=PTS-STARTPTS[mid];"
          f"[tail][head]blend=all_expr='A*(1-T/{X})+B*(T/{X})'[xf];"
          f"[xf][mid]concat=n=2:v=1:a=0[out]")
    vf = vf.replace("[a2]null[dummy];", "")
    subprocess.run([ffmpeg_bin(), "-y", "-loglevel", "error", "-i", str(src), "-filter_complex", vf,
                    "-map", "[out]", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "8",
                    "-g", str(max(1, v["fps"] // 2)), str(master)], check=True)
    v["loop_seconds"] = L
    print(f"실제 영상 루프: {src.name} {s0:.0f}s부터 {L:.0f}초, 이음새 {X:.0f}초 크로스페이드 → {W}x{H}")
    frame = job / "background.png"
    subprocess.run([ffmpeg_bin(), "-y", "-loglevel", "error", "-i", str(master), "-frames:v", "1", str(frame)])
    audio = loopable_audio(args.audio, job) if args.audio else None
    cache, finals = {}, []
    for duration in parse_durations(args.duration or v["duration"], parse_duration):
        seg, kbps = segment_for_duration(master, job, duration, v, cache)
        final = job / f"final_{format_duration(duration)}_{v['resolution']}.mp4"
        assemble(seg, final, duration, v, audio=audio)
        gb = final.stat().st_size / 1e9
        print(f"  -> {final.name}  {gb:.2f}GB ({kbps / 1000:.1f}Mbps)")
        finals.append({"file": final.name, "duration": duration, "gb": round(gb, 2)})
    _write_meta(job, source=str(src), start=s0, length=L, crossfade=X, finals=finals, real_footage=True)


def cmd_plan(cfg, args):
    """길이별 예상 비트레이트·용량 표."""
    v = dict(cfg["video"])
    for key in ("resolution", "max_size_gb", "encoder"):
        if getattr(args, key, None):
            v[key] = getattr(args, key)
    audio_kbps = int(str(v["audio_bitrate"]).rstrip("k"))
    print(f"{v['resolution']} / {v['encoder']} / 상한 {v['max_size_gb']}GB")
    for d in parse_durations(getattr(args, "duration", None) or "all", parse_duration):
        k = budget_kbps(d, v)
        gb = (k + audio_kbps) * 1000 / 8 * d / 1e9
        print(f"  {format_duration(d):>6}: 영상 {k / 1000:5.1f}Mbps → 약 {gb:5.1f}GB")


# ---------- 명령 ----------
def cmd_scenes(cfg, args):
    for s in SCENES.values():
        print(f"{s.name:16} {s.title}")


def cmd_check(cfg, args):
    ok = True
    try:
        print(f"ffmpeg: {ffmpeg_bin()}")
    except SystemExit as e:
        print(e); ok = False
    client = ComfyClient(cfg["comfy"]["url"])
    try:
        stats = client.ping()
        dev = stats.get("devices", [{}])[0]
        print(f"ComfyUI: {cfg['comfy']['url']} OK ({dev.get('name', '?')})")
        ckpts = client.checkpoints()
        print("체크포인트:")
        for name in ckpts:
            mark = "*" if name == cfg["comfy"]["checkpoint"] else " "
            print(f"  {mark} {name}")
        if cfg["comfy"]["checkpoint"] not in ckpts:
            print(f"! config 의 checkpoint '{cfg['comfy']['checkpoint']}' 가 목록에 없습니다.")
            ok = False
    except ComfyError as e:
        print(f"ComfyUI: {e}"); ok = False
    return 0 if ok else 1


def cmd_image(cfg, args):
    for name in _scene_names(args.scene):
        generate_images(cfg, name, args.count, args.seed, args.extra, args.lora, not args.no_diversify,
                        args.rain)


def cmd_preview(cfg, args):
    image = Path(args.image)
    scene = args.scene or _read_meta(image.parent).get("scene")
    W, H = cfg["output"]["width"], cfg["output"]["height"]
    bg = fit_cover(Image.open(image).convert("RGB"), W, H)
    rs = _rain_settings(cfg, scene, args)
    r = RainRenderer(bg, rs, cfg["video"]["fps"], 1)
    if (image.parent / "meta.json").exists() and image.name == "background.png":
        _attach_details(cfg, r, image.parent, bg, rs, args)
    out = Path(args.out) if args.out else image.with_name(image.stem + "_preview.png")
    r.frame_image(0).save(out)
    print(f"미리보기: {out}")


def cmd_loop(cfg, args):
    make_loop(cfg, args.image, args.scene, args)


VARY_SIZE = (1664, 936)   # img2img 작업 해상도 (16:9, 8의 배수)


def _load_source(path, at):
    """이미지 또는 영상(at 초 지점 프레임)을 PIL 이미지로."""
    path = Path(path)
    if not path.exists():
        raise SystemExit(f"파일을 찾을 수 없습니다: {path}")
    if path.suffix.lower() in lora_mod.VIDEO_EXT:
        dur = lora_mod._probe_duration(path)
        t = at if at is not None else dur / 2
        tmp = Path(cfg_tmp_dir()) / f"_frame_{path.stem[:20]}_{int(t)}.png"
        import subprocess
        subprocess.run([ffmpeg_bin(), "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(path),
                        "-frames:v", "1", str(tmp)], check=True)
        return Image.open(tmp).convert("RGB")
    return Image.open(path).convert("RGB")


def cfg_tmp_dir():
    d = Path(load_config()["output"]["dir"]) / "_tmp"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cmd_vary(cfg, args):
    """실제 사진/영상 장면을 바탕으로 구도·디테일만 바꾼 새 배경 생성 (img2img)."""
    src = _load_source(args.source, args.at)
    if args.scene:
        scene = get_scene(args.scene)
        c = {**cfg["comfy"], **scene.comfy, **cfg.get("comfy_cli", {})}
        c["upscale_to"] = (cfg["output"]["width"], cfg["output"]["height"])
        base_prompt, negative = scene.build_prompt(random.Random(0), args.prompt or "")
        post = scene.post
    else:
        scene = None
        c = {**cfg["comfy"], **NATURAL_COMFY, **cfg.get("comfy_cli", {})}
        c["upscale_to"] = (cfg["output"]["width"], cfg["output"]["height"])
        base_prompt = ", ".join(x for x in (args.prompt, "rainy day, wet", NATURAL_STYLE) if x)
        negative = f"{NEGATIVE}, {NATURAL_NEGATIVE}"
        post = NATURAL_POST
    client = ComfyClient(c["url"], c["timeout"])
    loras = (_resolve_loras(client, cfg, scene, args.lora) if scene
             else [_parse_lora(l) for l in (args.lora or [])])
    work = fit_cover(src, *VARY_SIZE)
    name = client.upload_image(work, f"scenemaker_vary_{Path(args.source).stem[:30]}.png")
    W, H = cfg["output"]["width"], cfg["output"]["height"]
    job = _job_dir(cfg, f"vary_{Path(args.source).stem[:30]}")
    fit_cover(src, W, H).save(job / "source.png")
    print(f"변형 생성: 강도 {args.strength} x {args.count}장 → {job}")
    for i in range(args.count):
        seed = (args.seed + i) if args.seed is not None else random.randrange(2**32)
        t0 = time.time()
        img = client.generate(build_img2img(c, base_prompt, negative, seed, name, args.strength, loras=loras))[0]
        img = fit_cover(img, W, H)
        if post:
            img = naturalize(img, seed=seed, **_post_args(post))
        out = job / f"vary_{i + 1:02d}_seed{seed}.png"
        img.save(out)
        variety.warn_similar(img, out.name)
        print(f"  -> {out.name} ({time.time() - t0:.0f}s)")
    _write_meta(job, source=str(args.source), at=args.at, strength=args.strength, prompt=base_prompt,
                negative=negative, checkpoint=c["checkpoint"], scene=scene.name if scene else None)


def cmd_upscale(cfg, args):
    """이미 만든 배경을 AI 업스케일 (예: 예전 1080p 배경 → 4K)."""
    from .comfy import build_upscale
    c = cfg["comfy"]
    if not c.get("upscale_model"):
        raise SystemExit("config.toml 의 [comfy] upscale_model 을 설정하세요.")
    client = ComfyClient(c["url"], max(c["timeout"], 1800))     # 업스케일은 오래 걸릴 수 있음
    W, H = cfg["output"]["width"], cfg["output"]["height"]
    for p in args.images:
        p = Path(p)
        src = Image.open(p).convert("RGB")
        name = client.upload_image(src, f"scenemaker_up_{p.stem[:40]}.png")
        t0 = time.time()
        img = client.generate(build_upscale(name, c["upscale_model"], W, H))[0]
        out = p.with_name(p.stem + f"_{W}x{H}.png") if not args.replace else p
        if args.replace:
            shutil.copy(p, p.with_name(p.stem + "_orig.png"))
        img.save(out)
        print(f"{p.name} → {out.name} ({src.width}x{src.height} → {W}x{H}, {time.time() - t0:.0f}s)")


def cmd_used(cfg, args):
    if args.action == "add":
        for p in args.images:
            n = variety.mark_used(p, args.note)
            print(f"기록: {p} (총 {n}개)")
    elif args.action == "check":
        for p in args.images:
            hits = variety.warn_similar(Image.open(p), Path(p).name)
            if not hits:
                print(f"  ✓ {Path(p).name}: 사용한 배경들과 충분히 다릅니다")
    else:
        entries = variety.load_registry()
        for e in entries:
            print(f"{e['date']}  {e['path']}  {e.get('note', '')}")
        print(f"총 {len(entries)}개")


def cmd_make(cfg, args):
    for name in _scene_names(args.scene):
        for job in generate_images(cfg, name, args.count, args.seed, args.extra, args.lora,
                                   not args.no_diversify, args.rain):
            make_loop(cfg, job / "background.png", name, args, job=job)


def cmd_lora_dataset(cfg, args):
    lora_mod.build_dataset(args.name, args.sources, args.trigger or f"somnia_{args.name}", args.caption,
                           per_video=args.per_video, repeats=args.repeats,
                           trim=lora_mod.DREAMINA_TRIM if args.dreamina else args.trim,
                           extra_crops=args.extra_crops)


def cmd_lora_train(cfg, args):
    lora_mod.train(cfg, args.name, epochs=args.epochs, dim=args.dim, lr=args.lr, save_every=args.save_every,
                   max_steps=args.max_steps)


def cmd_lora_compare(cfg, args):
    """학습 단계별 LoRA 를 같은 씬/시드로 생성해 한 장의 비교 이미지로."""
    from PIL import ImageDraw
    c = cfg["comfy"]
    client = ComfyClient(c["url"], c["timeout"])
    scene = get_scene(args.scene)
    files = sorted(n for n in client.loras() if lora_trigger(n) == f"somnia_{args.name}")
    variants = [("no LoRA", [])] + [(n, [(n, args.strength)]) for n in files]
    if len(variants) == 1:
        raise SystemExit(f"somnia_{args.name}*.safetensors LoRA 가 ComfyUI 에 없습니다.")
    positive, negative = scene.build_prompt(random.Random(args.seed), args.extra)
    tiles = []
    for label, loras in variants:
        print(f"생성: {label}")
        p = f"somnia_{args.name}, {positive}" if loras else positive
        img = client.generate(build_txt2img(c, p, negative, args.seed, prefix="scenemaker/compare", loras=loras))[0]
        img = fit_cover(img, 640, 360)
        ImageDraw.Draw(img).text((10, 8), label, fill=(255, 255, 255))
        tiles.append(img)
    cols = min(3, len(tiles))
    rows = (len(tiles) + cols - 1) // cols
    grid = Image.new("RGB", (640 * cols, 360 * rows))
    for i, t in enumerate(tiles):
        grid.paste(t, ((i % cols) * 640, (i // cols) * 360))
    out = lora_mod.dataset_dir(args.name) / f"compare_{args.scene}_{args.seed}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    grid.save(out)
    print(f"비교 이미지: {out}")


def _add_rain_args(p):
    g = p.add_argument_group("빗줄기 옵션 (씬 프리셋 덮어쓰기)")
    g.add_argument("--intensity", type=float, help="빗방울 양 배율")
    g.add_argument("--angle", type=float, help="기울기(도)")
    g.add_argument("--speed", type=float, help="낙하 속도 배율")
    g.add_argument("--brightness", type=float, help="빗줄기 밝기 0~1")
    g.add_argument("--darken", type=float, help="배경 어둡게 0~0.5")
    g.add_argument("--fog", type=float, help="안개 강도 0~1")
    g.add_argument("--lightning", type=int, help="루프당 번개 횟수")
    g.add_argument("--no-splashes", action="store_true", help="물 튀김 끄기")
    g.add_argument("--no-details", action="store_true", help="깊이 기반 물 튀김·물결·물방울 끄기")
    g.add_argument("--no-motion", action="store_true", help="잎 흔들림·물 일렁임(배경 움직임) 끄기")
    g.add_argument("--no-wet", action="store_true", help="젖은 바위·흘러내리는 물줄기·수면 빗방울 끄기")
    g.add_argument("--grade", type=float, help="색 보정 강도 (기본 1.0, 0 = 끔)")
    g.add_argument("--grain", type=float, help="필름 그레인 강도 (기본 1.0, 0 = 끔)")
    g.add_argument("--classic-rain", action="store_true", help="예전 빗줄기 방식 (거리별 빗줄기·색 보정·그레인 끔)")


def _add_video_args(p):
    p.add_argument("--wan", action="store_true", help="물·안개 부분에 Wan 2.2 AI 움직임 (ComfyUI, 5~15분 추가)")
    p.add_argument("--wan-prompt", default="", help="Wan 움직임 묘사 추가 (영어)")
    p.add_argument("--wan-seed", type=int, help="Wan 시드 (기본: 배경 시드)")
    p.add_argument("--wan-period", type=float, help="Wan 움직임 한 바퀴 길이(초, 기본: 원래 속도 5초), 루프를 나누도록 조정됨")
    p.add_argument("--duration", help="길이: 3m / 1h / 10h, 여러 개 '3m,1h,10h', 전부 'all'")
    p.add_argument("--resolution", choices=list(RESOLUTIONS), help="출력 해상도 (기본 1440p)")
    p.add_argument("--max-size-gb", type=float, help="최종 파일 용량 상한 (기본 40)")
    p.add_argument("--audio", help="반복 재생할 빗소리 오디오 파일")
    p.add_argument("--loop-seconds", type=float, help="루프 구간 길이(초)")
    p.add_argument("--encoder", help="hevc_nvenc | h264_nvenc | libx265 | libx264")
    p.add_argument("--segment-only", action="store_true", help="루프 구간만 만들고 장시간 조립은 생략")


def _add_image_args(p):
    p.add_argument("--scene", required=True, help="씬 이름 또는 all")
    p.add_argument("--count", type=int, default=1, help="씬당 생성 개수")
    p.add_argument("--seed", type=int, help="시작 시드 (미지정 시 랜덤)")
    p.add_argument("--extra", default="", help="프롬프트에 추가할 문구")
    p.add_argument("--checkpoint", help="사용할 SD 체크포인트 파일명 (config 덮어쓰기)")
    p.add_argument("--lora", action="append", help="추가 LoRA '파일명[:강도]' (여러 번 지정 가능)")
    p.add_argument("--no-diversify", action="store_true", help="시간대·계절·구도 자동 다양화 끄기")
    p.add_argument("--model", choices=["sdxl", "zimage"], help="이미지 모델 계열 (기본 sdxl, 씬 설정 따름)")
    p.add_argument("--rain", choices=["light", "steady", "heavy"],
                   help="녹음한 빗소리 세기에 화면 비를 맞춤 (가랑비/보통/폭우)")


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="scenemaker", description="somnia-forest 빗소리 배경/루프 영상 생성기")
    ap.add_argument("--config", help="설정 파일 경로 (기본: config.toml)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("scenes", help="씬 프리셋 목록").set_defaults(fn=cmd_scenes)
    sub.add_parser("check", help="ffmpeg / ComfyUI / 체크포인트 점검").set_defaults(fn=cmd_check)

    p = sub.add_parser("image", help="SD 로 배경 이미지만 생성")
    _add_image_args(p)
    p.set_defaults(fn=cmd_image)

    p = sub.add_parser("preview", help="이미지에 빗줄기 1프레임 합성 (빠른 확인용)")
    p.add_argument("image")
    p.add_argument("--scene")
    p.add_argument("--out")
    _add_rain_args(p)
    p.set_defaults(fn=cmd_preview)

    p = sub.add_parser("loop", help="기존 이미지로 루프 영상 생성")
    p.add_argument("image")
    p.add_argument("--scene", help="빗줄기 프리셋으로 쓸 씬 (job 폴더면 자동)")
    _add_video_args(p)
    _add_rain_args(p)
    p.set_defaults(fn=cmd_loop)

    p = sub.add_parser("make", help="이미지 생성 + 루프 영상까지 한 번에")
    _add_image_args(p)
    _add_video_args(p)
    _add_rain_args(p)
    p.set_defaults(fn=cmd_make)

    p = sub.add_parser("realloop", help="직접 촬영한 영상을 이음새 없는 루프로 → 장시간 영상")
    p.add_argument("video")
    p.add_argument("--start", default=600, help="사용할 구간 시작(초)")
    p.add_argument("--length", default=30, help="루프 길이(초)")
    p.add_argument("--crossfade", default=2, help="이음새 크로스페이드(초)")
    p.add_argument("--duration")
    p.add_argument("--audio")
    p.add_argument("--resolution", choices=list(RESOLUTIONS))
    p.add_argument("--max-size-gb", type=float)
    p.add_argument("--encoder")
    p.set_defaults(fn=cmd_realloop)

    p = sub.add_parser("upscale", help="기존 배경 이미지를 AI 업스케일 (4K)")
    p.add_argument("images", nargs="+")
    p.add_argument("--replace", action="store_true", help="원본을 _orig.png 로 남기고 교체")
    p.set_defaults(fn=cmd_upscale)

    p = sub.add_parser("plan", help="길이별 예상 비트레이트·용량 확인")
    p.add_argument("--duration", help="기본: all")
    p.add_argument("--resolution", choices=list(RESOLUTIONS))
    p.add_argument("--max-size-gb", type=float)
    p.add_argument("--encoder")
    p.set_defaults(fn=cmd_plan)

    p = sub.add_parser("used", help="영상에 사용한 배경 기록 (중복 방지)")
    p.add_argument("action", choices=["list", "add", "check"])
    p.add_argument("images", nargs="*")
    p.add_argument("--note", default="", help="영상 제목 등 메모")
    p.set_defaults(fn=cmd_used)

    p = sub.add_parser("vary", help="실제 사진/영상 장면을 바탕으로 새 배경 변형 생성")
    p.add_argument("source", help="이미지 또는 영상 파일")
    p.add_argument("--at", type=float, help="영상에서 가져올 시점(초), 기본: 중간")
    p.add_argument("--prompt", default="", help="장면 설명 (예: bamboo forest in the rain)")
    p.add_argument("--scene", help="씬 프리셋의 프롬프트/모델/LoRA 사용")
    p.add_argument("--strength", type=float, default=0.45, help="변형 강도 0.2(거의 원본)~0.7(많이 바뀜)")
    p.add_argument("--count", type=int, default=4)
    p.add_argument("--seed", type=int)
    p.add_argument("--checkpoint")
    p.add_argument("--lora", action="append")
    p.set_defaults(fn=cmd_vary)

    p = sub.add_parser("lora-dataset", help="영상/사진 폴더에서 LoRA 학습 데이터셋 만들기")
    p.add_argument("name", help="데이터셋 이름 (예: hanok) → 트리거 단어 somnia_<name>")
    p.add_argument("sources", nargs="+", help="영상/이미지 파일 또는 폴더")
    p.add_argument("--caption", default="photo, rainy day", help="모든 이미지 공통 캡션")
    p.add_argument("--trigger", help="트리거 단어 (기본 somnia_<name>)")
    p.add_argument("--per-video", type=int, default=12, help="영상당 추출할 프레임 수")
    p.add_argument("--repeats", type=int, default=10, help="에폭당 이미지 반복 횟수")
    p.add_argument("--dreamina", action="store_true", help="Dreamina/CapCut 워터마크 영역 잘라내기")
    p.add_argument("--trim", type=lambda v: tuple(float(x) for x in v.split(",")),
                   help="잘라낼 비율 '위,아래,왼쪽,오른쪽' (예: 0.1,0.1,0,0)")
    p.add_argument("--extra-crops", action="store_true", help="왼쪽/오른쪽 구도 추가 (데이터 적을 때)")
    p.set_defaults(fn=cmd_lora_dataset)

    p = sub.add_parser("lora-train", help="kohya sd-scripts 로 LoRA 학습")
    p.add_argument("name")
    p.add_argument("--epochs", type=int, default=10)
    p.add_argument("--dim", type=int, default=32, help="LoRA 랭크")
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--save-every", type=int, default=2, help="N 에폭마다 중간 저장 (비교용)")
    p.add_argument("--checkpoint", help="학습 기준 체크포인트")
    p.add_argument("--max-steps", type=int, help="최대 스텝 (테스트용)")
    p.set_defaults(fn=cmd_lora_train)

    p = sub.add_parser("lora-compare", help="학습 단계별 LoRA 결과 비교 이미지")
    p.add_argument("name")
    p.add_argument("--scene", default="hanok_courtyard")
    p.add_argument("--seed", type=int, default=100)
    p.add_argument("--strength", type=float, default=0.8)
    p.add_argument("--extra", default="")
    p.set_defaults(fn=cmd_lora_compare)

    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    if getattr(args, "checkpoint", None):
        cfg["comfy"]["checkpoint"] = args.checkpoint
        cfg["comfy_cli"] = {"checkpoint": args.checkpoint}
    if getattr(args, "model", None):
        cfg.setdefault("comfy_cli", {})["family"] = args.model
    try:
        return args.fn(cfg, args) or 0
    except ComfyError as e:
        print(f"오류: {e}")
        return 1
