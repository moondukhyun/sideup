"""4단계: Wan 2.2 로 물·안개 부분만 AI 움직임 (선택 기능, --wan).

원리
1. 배경을 848x480 으로 줄여 Wan 2.2 I2V 14B 에 '첫 프레임 = 끝 프레임 = 배경' 으로 넣는다
   → 제자리로 돌아오는 5초(81프레임, 16fps) 클립. (lightx2v 4스텝 LoRA, 12GB 에서 약 수 분)
2. 움직임이 실제로 생긴 곳(흐르는 물·물보라·안개)에만 Wan 픽셀을 확대해 합성한다.
   (원본을 흐름으로 휘게 하는 방식은 흐르는 물이 앞뒤로 출렁이기만 해서 버림 — 2026-09-30 시험)
3. 그 순간 거의 안 변한 곳에는 원본의 선명한 디테일을 되돌려 480p 티를 줄인다.
4. 초록 잎은 제외 (AI 잎 움직임은 어색 → 기존 절차적 흔들림 유지).
5. 끝 프레임을 첫 프레임에 맞추는 선형 보정 → 루프 이음새 0.
"""

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

WAN_W, WAN_H, WAN_LEN, WAN_FPS = 848, 480, 81, 16
WAN_NEG = ("camera movement, zoom, pan, shaking, flicker, color shift, blurry, distorted, morphing, "
           "people, animals, text, watermark, rain streaks")
WAN_MODELS = {
    "high": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
    "low": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors",
    "lora_high": "wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors",
    "lora_low": "wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors",
    "clip": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
    "vae": "wan_2.1_vae.safetensors",
}


def build_wan_flf(image_name, prompt, seed, negative=None):
    """첫·끝 프레임이 같은 Wan 2.2 I2V 워크플로 (4스텝 가속 LoRA, high→low 2단계)."""
    m = WAN_MODELS
    ks = dict(noise_seed=seed, steps=4, cfg=1.0, sampler_name="euler", scheduler="simple",
              positive=["F", 0], negative=["F", 1])
    return {
        "U1": {"class_type": "UNETLoader", "inputs": {"unet_name": m["high"], "weight_dtype": "default"}},
        "U2": {"class_type": "UNETLoader", "inputs": {"unet_name": m["low"], "weight_dtype": "default"}},
        "L1": {"class_type": "LoraLoaderModelOnly",
               "inputs": {"model": ["U1", 0], "lora_name": m["lora_high"], "strength_model": 1.0}},
        "L2": {"class_type": "LoraLoaderModelOnly",
               "inputs": {"model": ["U2", 0], "lora_name": m["lora_low"], "strength_model": 1.0}},
        "M1": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["L1", 0], "shift": 5.0}},
        "M2": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["L2", 0], "shift": 5.0}},
        "C": {"class_type": "CLIPLoader", "inputs": {"clip_name": m["clip"], "type": "wan", "device": "default"}},
        "V": {"class_type": "VAELoader", "inputs": {"vae_name": m["vae"]}},
        "P": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["C", 0], "text": prompt}},
        "N": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["C", 0], "text": negative or WAN_NEG}},
        "I": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "F": {"class_type": "WanFirstLastFrameToVideo",
              "inputs": {"positive": ["P", 0], "negative": ["N", 0], "vae": ["V", 0], "width": WAN_W,
                         "height": WAN_H, "length": WAN_LEN, "batch_size": 1,
                         "start_image": ["I", 0], "end_image": ["I", 0]}},
        "K1": {"class_type": "KSamplerAdvanced",
               "inputs": {**ks, "model": ["M1", 0], "add_noise": "enable", "latent_image": ["F", 2],
                          "start_at_step": 0, "end_at_step": 2, "return_with_leftover_noise": "enable"}},
        "K2": {"class_type": "KSamplerAdvanced",
               "inputs": {**ks, "model": ["M2", 0], "add_noise": "disable", "latent_image": ["K1", 0],
                          "start_at_step": 2, "end_at_step": 10000, "return_with_leftover_noise": "disable"}},
        "D": {"class_type": "VAEDecode", "inputs": {"samples": ["K2", 0], "vae": ["V", 0]}},
        "S": {"class_type": "PreviewImage", "inputs": {"images": ["D", 0]}},   # 임시 폴더 (81장이 output 에 쌓이지 않게)
    }


WAN_ROOM_NEG = ("camera movement, zoom, pan, shaking, color shift, blurry, distorted, morphing, text, watermark, "
                "a person, people, waking up, standing up, head turning, running, jumping, new objects appearing, "
                "changing furniture, flickering whole room, strobe")


def wan_room_prompt(fire, n_candles, pets, extra="", steam=False):
    """실내 장면용 Wan 프롬프트: 움직여야 하는 것만 말하고 나머지는 가만히 있게."""
    parts = ["static camera, locked-off tripod shot, cozy room at night, realistic natural video footage, "
             "everything stays perfectly still except the following"]
    if fire:
        parts.append("the real wood fire in the fireplace burns naturally, the flames flicker and dance upward, "
                     "glowing embers pulse, the logs stay in place")
    if n_candles:
        parts.append("the small candle flames flicker very gently, the candles themselves stay still")
    if pets:
        parts.append("the sleeping " + " and ".join(sorted(set(pets))) + " stay fast asleep and do not lift or turn their heads, "
                     "only their bodies rise and fall slowly with calm breathing")
    if steam:
        parts.append("thin delicate wisps of steam rise slowly from the hot drink, translucent and faint, swirling gently and fading out "
                     "within a few centimeters above the cup, subtle, realistic, no smoke, no thick vapor")
    return ", ".join(parts + ([extra] if extra else []))


def wan_prompt(scene_title="", extra=""):
    base = ("static camera, locked-off tripod shot, only water and mist move: gentle ripples and flowing water, "
            "thin mist drifting slowly, calm rainy day, realistic nature footage")
    return ", ".join(x for x in (base, scene_title, extra) if x)


def generate_clip(client, bg, job, prompt, seed, negative=None):
    """Wan 클립을 만들어 job/wan/ 에 저장 (이미 있으면 재사용 — GPU 수 분 절약). 프레임 목록 반환."""
    from .comfy import fit_cover
    out = Path(job) / "wan"
    done = out / "clip.json"
    if done.exists():
        info = json.loads(done.read_text(encoding="utf-8"))
        if info.get("prompt") == prompt and info.get("seed") == seed:
            frames = [Image.open(out / f"f{i:03d}.png").convert("RGB") for i in range(info["frames"])]
            print(f"  Wan 클립 재사용: {out} ({len(frames)}프레임)")
            return frames
    out.mkdir(parents=True, exist_ok=True)
    small = fit_cover(bg, WAN_W, WAN_H)
    small.save(out / "start.png")
    name = client.upload_image(small, f"wan_start_{Path(job).name[:40]}.png")
    import time
    t0 = time.time()
    print(f"  Wan 2.2 클립 생성 중 ({WAN_W}x{WAN_H}, {WAN_LEN}프레임) — 보통 5~15분 ...")
    frames = client.generate(build_wan_flf(name, prompt, seed, negative))
    for i, f in enumerate(frames):
        f.save(out / f"f{i:03d}.png")
    done.write_text(json.dumps({"prompt": prompt, "seed": seed, "frames": len(frames),
                                "seconds": round(time.time() - t0)}, ensure_ascii=False), encoding="utf-8")
    print(f"  Wan 클립 완성: {len(frames)}프레임 ({time.time() - t0:.0f}s)")
    return frames


def _gray(img):
    return np.asarray(img.convert("L"), dtype=np.uint8)


class WanMotion:
    """Wan 클립의 물·안개 움직임을 고해상도 배경에 합성한다.

    - 움직이는 곳: Wan 픽셀(확대)을 쓰되, 원본과 Wan 첫 프레임의 차이(= 원본의 선명한 디테일·색)를
      '그 순간 거의 안 변한 곳'에 다시 더한다 → 멈춘 물·바위는 원본만큼 선명, 흐르는 물만 AI 픽셀.
    - 끝 프레임을 첫 프레임에 맞추는 선형 보정 → 한 바퀴가 정확히 이어짐.
    - 16fps → 30fps 는 인접 프레임 사이 광학 흐름으로 중간 프레임을 만든다 (겹쳐 보이는 잔상 방지).
    base 는 frame(f) 를 가진 BackgroundMotion(잎 흔들림) 또는 None.
    """

    def __init__(self, bg, frames, N, fps, base=None, veg=None, period=None, keep_gain=6.0):
        import cv2
        self.cv2 = cv2
        self.bg = bg
        self.base = base
        self.H, self.W = bg.shape[:2]
        self.N, self.fps = N, fps
        K = len(frames) - 1
        self.K = K
        F = np.stack([np.asarray(f, dtype=np.float32) / 255.0 for f in frames])      # (K+1,h,w,3)
        # 끝 = 처음 이 되도록 선형 보정 (Wan 의 마지막 프레임은 첫 프레임과 '거의' 같을 뿐)
        ramp = np.linspace(0, 1, K + 1, dtype=np.float32)[:, None, None, None]
        F += ramp * (F[:1] - F[-1:])
        np.clip(F, 0, 1, out=F)
        self.F = F
        h, w = F.shape[1:3]
        self.h, self.w = h, w
        gray = [cv2.cvtColor((f * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY) for f in F]
        # 인접 프레임 사이 흐름 (중간 프레임 보간용): fwd[k]: k→k+1, bwd[k]: k+1→k
        args = (None, 0.5, 3, 15, 3, 5, 1.2, 0)
        self.fwd = np.stack([cv2.calcOpticalFlowFarneback(gray[k], gray[k + 1], *args) for k in range(K)])
        self.bwd = np.stack([cv2.calcOpticalFlowFarneback(gray[k + 1], gray[k], *args) for k in range(K)])
        self.gx, self.gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))

        # 움직임 지도: 흐린 프레임 기준 흐름 크기 + 밝기 변화 (물결·물보라·안개)
        # - 흐리게 보는 이유: 기와·창살 같은 잔무늬는 Wan 이 프레임마다 반짝이게 다시 그려서 '움직임'으로 잡힘
        # - 절대 기준값 (2026-09-30 측정, 흐린 480p 기준 상위 1%):
        #   움직임 없는 한옥 마당 흐름 0.16px·밝기 2.2 / 호수 물결 0.59px·8.3 / 계곡물은 그보다 훨씬 큼
        #   예전엔 클립 안 상대 순위(상위 45%)라 안 움직이는 장면에서도 지붕·창살이 골라졌음
        blur = [cv2.GaussianBlur(g, (0, 0), 2.5) for g in gray]
        mag = np.mean([np.sqrt((cv2.calcOpticalFlowFarneback(blur[k], blur[k + 1], *args) ** 2).sum(-1))
                       for k in range(K)], 0)
        std = np.stack([cv2.GaussianBlur(f, (0, 0), 2.5) for f in F]).std(0).mean(-1) * 255
        # 잔무늬 대비 변화율: 기와 반짝임은 '결이 많은 곳의 변화', 잔잔한 호수 물결은 '매끈한 곳의 변화'
        #   (한옥 상위 1% 0.46 / 호수 수면 중앙값 0.49·상위 10% 0.87)
        g0 = np.asarray(gray, np.float32)
        tex = np.sqrt(cv2.GaussianBlur((g0[0] - cv2.GaussianBlur(g0[0], (0, 0), 2)) ** 2, (0, 0), 4))
        ratio = cv2.GaussianBlur(g0.std(0), (0, 0), 4) / (tex + 2.0)
        energy = np.maximum.reduce([np.clip((mag - 0.25) / 0.25, 0, 1), np.clip((std - 3.0) / 3.0, 0, 1),
                                    np.clip((ratio - 0.5) / 0.3, 0, 1)])
        # 조각난 물결 영역을 이어 붙임 (수면 한가운데만 멈춰 보이지 않게)
        m = cv2.morphologyEx(cv2.GaussianBlur(energy, (0, 0), 3), cv2.MORPH_CLOSE,
                             cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41)))
        if veg is not None:     # 잎은 AI 움직임이 어색 → 기존 절차적 흔들림에 맡김
            m *= 1.0 - np.clip(cv2.resize(veg.astype(np.float32), (w, h), interpolation=cv2.INTER_AREA) * 3.0, 0, 1)
        edge = np.minimum.reduce([self.gx, self.gy, w - 1 - self.gx, h - 1 - self.gy]) / 10.0
        m *= np.clip(edge, 0, 1)                       # 화면 테두리는 Wan 이 자주 틀림
        m = cv2.GaussianBlur(cv2.dilate(m, np.ones((5, 5), np.uint8)), (0, 0), 4)
        self.coverage = float((m > 0.25).mean())
        self.mask = cv2.resize(m, (self.W, self.H), interpolation=cv2.INTER_LINEAR)[..., None]
        self.up0 = self._up(F[0])
        self.detail = bg - self.up0                     # 원본만의 선명함·색 (Wan 첫 프레임 대비)
        self.keep_gain = keep_gain
        # 재생 속도: 기본은 Wan 원래 속도(81프레임 = 5초). 루프 길이를 정수 번 나누도록 맞춤
        loop_sec = N / fps
        natural = K / WAN_FPS
        cycles = max(1, int(round(loop_sec / (period or natural))))
        self.frames_per_cycle = N / cycles
        self.active = self.coverage > 0.005

    def _up(self, a):
        cv2 = self.cv2
        u = cv2.resize(a, (self.W, self.H), interpolation=cv2.INTER_CUBIC)
        blur = cv2.GaussianBlur(u, (0, 0), 1.2)
        return np.clip(u + (u - blur) * 0.6, 0, 1)      # 확대로 무뎌진 결을 살짝 세움

    def small_frame(self, f):
        """루프 위치 f 의 Wan 프레임 (480p), 인접 프레임 사이는 흐름 보간."""
        cv2 = self.cv2
        ph = (f % self.frames_per_cycle) / self.frames_per_cycle * self.K
        k = min(int(ph), self.K - 1)
        t = ph - k
        if t < 1e-3:
            return self.F[k]
        a = cv2.remap(self.F[k], self.gx + self.bwd[k][..., 0] * t, self.gy + self.bwd[k][..., 1] * t,
                      cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        b = cv2.remap(self.F[k + 1], self.gx + self.fwd[k][..., 0] * (1 - t), self.gy + self.fwd[k][..., 1] * (1 - t),
                      cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return a * (1 - t) + b * t

    def frame(self, f):
        base = self.base.frame(f) if self.base is not None else self.bg
        if not self.active:
            return base
        cv2 = self.cv2
        cur = self.small_frame(f)
        change = np.abs(cur - self.F[0]).mean(-1)
        keep = np.clip(1.0 - cv2.GaussianBlur(change, (0, 0), 2) * self.keep_gain, 0, 1)
        keep = cv2.resize(keep, (self.W, self.H), interpolation=cv2.INTER_LINEAR)[..., None]
        wan = np.clip(self._up(cur) + self.detail * keep, 0, 1)
        return base * (1 - self.mask) + wan * self.mask


def mask_preview(bg, wm, path):
    """움직임이 들어가는 곳을 파란색으로 표시한 확인용 이미지."""
    a = (bg * 255).astype(np.uint8) if bg.dtype != np.uint8 else bg
    m = wm.mask[..., 0]
    tint = a.astype(np.float32)
    tint[..., 2] = tint[..., 2] * (1 - m) + 255 * m * 0.8 + tint[..., 2] * m * 0.2
    tint[..., 0] *= 1 - m * 0.5
    Image.fromarray(np.clip(tint, 0, 255).astype(np.uint8)).resize((1280, 720)).save(path)
