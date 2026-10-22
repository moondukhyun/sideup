"""끊김 없이 반복되는(seamless) 빗줄기/안개/번개 오버레이 렌더러.

루프 원리: 모든 움직임이 N 프레임 뒤 정확히 제자리로 돌아오게 만든다.
- 빗방울: 낙하 구간 S 를 루프 동안 정수 k 바퀴 돌도록 속도를 양자화 (v = k*S/N)
- 안개: FFT 로 만든 주기적(tileable) 노이즈를 루프 동안 화면 폭의 정수배만큼 이동
- 물 튀김: 프레임 번호(f mod N)를 시드로 사용
"""

import math
from dataclasses import dataclass, field, fields

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


@dataclass
class RainSettings:
    intensity: float = 1.0
    angle: float = 8.0
    speed: float = 1.0
    brightness: float = 0.55
    color: tuple = (205, 215, 225)
    darken: float = 0.08
    fog: float = 0.15
    fog_color: tuple = (150, 165, 170)
    splashes: bool = True
    lightning: int = 0
    window: bool = False      # 창가 씬: 빗줄기는 창밖에만, 유리에 물방울
    style: str = "depth"      # "depth"(2026-10-01, 거리별 빗줄기) | "classic"(예전 방식)
    grade: float = 1.0        # 색 보정 강도 (0 = 끔)
    grain: float = 1.0        # 필름 그레인 강도 (0 = 끔)
    foliage: str = "green"   # 잎 흔들림 영역: green(초록) | autumn(노랑·주황·빨강 포함)
    leaf_kicks: float = 1.0   # 빗방울 맞고 튕기는 잎 세기 (0=끔)
    wet: float = 0.7          # 젖은 표면(돌·지붕·기둥) + 흘러내리는 빗물 + 대나무·기둥 줄기 물줄기 세기 (0 = 끔)
    stream: float = 0.0       # v11.21: 대롱·폭포의 멈춘 물줄기를 찾아 실제로 흘러내리게 (0 = 끔)
    wan_hint: str = ""        # v11.21: 이 씬에서 Wan 에게 줄 물 움직임 설명(영어)
    water_rain: float = 0.0   # v11.19: 수면(계곡·호수)에 떨어지는 빗방울 물결 (0 = 끔)
    gust: float = 1.0         # v11.20: 바람(돌풍)에 따라 빗줄기 기울기가 천천히 흔들리는 세기 (0 = 끔)
    bloom: float = 1.0        # v11.20: 밝은 빛(하늘·가로등) 주변 번짐 (0 = 끔)
    wet_ground: float = 0.5   # v11.20: 젖은 바닥(어두워짐 + 웅덩이에 하늘 반사) 세기 (0 = 끔)
    wan_ok: bool = True       # v11.20: False 면 물·안개가 거의 없는 씬이라 Wan(AI 물 움직임)을 건너뜀
    interior: float = 0.0     # v11.22: 아늑한 실내 — 촛불·벽난로 불꽃·방 안 불빛 일렁임·반려동물 숨쉬기 세기 (0 = 끔)
    fire: float = 1.0         # v11.22: 벽난로 불 세기 배율
    sway: bool = True         # v11.22: False 면 잎 흔들림(식물 감지)을 건너뜀 (실내 장면)
    vinyl_sound: bool = False # v11.22: True 면 레코드판 특유의 지직거리는 소리를 자동으로 합성해 섞음
    fire_sound: bool = False  # v11.22: True 면 벽난로 타닥거리는 소리를 자동으로 합성해 섞음
    outside_only: bool = False  # v11.23: True 면 텐트 안쪽(천·바닥)에는 비를 그리지 않고 열린 바깥 풍경에만 내림
    veil: float = 1.0          # 창밖 먼 비 '장막'(세로 결이 아래로 흐르는 옅은 막) 세기 배율. 큰 어두운 창에서는 검은 띠·뿌연 띠가 번갈아 내려와 보이므로 0 으로 끔
    big_flame: bool = False   # v11.23: True 면 화면 가득한 큰 촛불 클로즈업용 불꽃 감지·움직임 (일반 촛불 감지는 작은 불꽃만 인정)
    dof: float = 0.0          # 깊이 기반 피사계심도 (0 = 끔). 가을 씬은 1.0 (2026-10-02 Cowork: 잘린 종이 느낌 해소)
    seed: int = 7

    @classmethod
    def from_dict(cls, *dicts):
        names = {f.name for f in fields(cls)}
        merged = {}
        for d in dicts:
            merged.update({k: v for k, v in (d or {}).items() if k in names and v is not None})
        return cls(**merged)


@dataclass
class _Layer:
    scale: float      # 렌더 해상도 배율 (작을수록 멀고 흐림)
    count: int        # 1080p 기준 빗방울 수
    speed: float      # 1080p/30fps 기준 px/frame
    length: float
    width: int
    alpha: float
    blur: float = 0.0
    near: float = 1.0 # 이 층의 거리 (0 = 아주 멀리, 1 = 카메라 바로 앞). 장면이 이보다 가까우면 가려짐
    drops: dict = field(default_factory=dict)


LAYERS = [
    _Layer(scale=0.25, count=3200, speed=13, length=20, width=1, alpha=0.45, blur=0.4, near=0.18),  # 먼 숲·산 앞의 가는 비
    _Layer(scale=0.35, count=1100, speed=20, length=34, width=1, alpha=0.34, blur=0.5, near=0.45),
    _Layer(scale=0.6, count=450, speed=32, length=60, width=1, alpha=0.48, blur=0.5, near=0.75),
    _Layer(scale=1.0, count=90, speed=52, length=130, width=3, alpha=0.38, blur=1.8),   # 렌즈 가까운 흐린 빗방울
]


# 2026-10-01 거리별 빗줄기: 먼 비는 가늘고 짧고 옅게(저해상도 확대로 굵어지던 문제 해결),
# 가까운 비는 초점이 안 맞아 넓고 흐릿하게. 빗방울마다 밝기·길이 편차를 크게.
#
# 2026-10-01 (2차) 카메라 셔터처럼: 빗줄기 길이 = 한 프레임 낙하 거리 x 셔터(1/60초 = 0.5프레임).
# 예전엔 줄이 낙하 거리보다 길어서 한 방울이 미끄러져 내려가는 게 눈으로 따라가져 'CG 오버레이'처럼 보였다.
# 실제 영상처럼 방울이 프레임마다 훌쩍 건너뛰어 개별 방울을 따라갈 수 없게 속도를 올리고,
# 방울마다 기울기를 조금씩 다르게(완벽한 평행선 방지), 선은 부드러운 안티에일리어싱으로 그린다.
# (length 는 이 방식에선 쓰지 않음 — 속도 x SHUTTER 로 정해짐)
SHUTTER = 0.5
GUST_AMP = 0.028          # 돌풍으로 기울기(tan)가 흔들리는 최대 폭 (약 ±1.6°)
LAYERS_DEPTH = [
    _Layer(scale=0.5, count=2600, speed=26, length=0, width=1, alpha=0.25, blur=0.3, near=0.18),
    _Layer(scale=0.75, count=1300, speed=42, length=0, width=1, alpha=0.33, blur=0.3, near=0.45),
    _Layer(scale=1.0, count=480, speed=70, length=0, width=1, alpha=0.50, blur=0.5, near=0.75),
    _Layer(scale=0.5, count=45, speed=130, length=0, width=3, alpha=0.24, blur=4.0),    # 렌즈 앞 흐린 빗방울
]


class RainRenderer:
    def __init__(self, background: Image.Image, settings: RainSettings, fps: int, loop_seconds: float):
        self.s = settings
        self.W, self.H = background.size
        self.fps = fps
        self.N = max(1, int(round(fps * loop_seconds)))
        self.res = self.H / 1080.0          # 해상도 보정
        self.tempo = 30.0 / fps              # fps 보정 (px/frame)
        rng = np.random.default_rng(settings.seed)

        bg = np.asarray(background.convert("RGB"), dtype=np.float32) / 255.0
        self.depth_style = settings.style != "classic"
        if self.depth_style and settings.grade > 0:
            from .finish import soften_background
            bg = soften_background(bg, settings.grade, self.res)
        self.bg = bg * (1.0 - settings.darken)
        self.rain_color = np.array(settings.color, dtype=np.float32) / 255.0
        self.fog_color = np.array(settings.fog_color, dtype=np.float32) / 255.0
        self.tan = math.tan(math.radians(settings.angle))

        self.bloom = None
        if self.depth_style and settings.grade > 0 and settings.bloom > 0:
            self.bloom = self._make_bloom(bg, settings.bloom)
        self.layers = [self._init_layer(_Layer(**{f.name: getattr(l, f.name) for f in fields(l)}), rng)
                       for l in (LAYERS_DEPTH if self.depth_style else LAYERS)]
        self.vis = self._make_visibility(bg)
        self.fog = self._make_fog(rng) if settings.fog > 0 else None
        self.flash = self._make_flash(rng)
        self.layer_w = None          # set_depth(): 층별 원근 가림
        self.veil = None
        self.details = None          # details.WeatherDetails (깊이 기반 물 튀김·물결·물방울)
        self.motion = None           # motion.BackgroundMotion (잎 흔들림·물 일렁임)
        self.glass = None            # glass.GlassRain (창가 씬: 유리 물방울, 빗줄기는 창밖에만)
        self.water = None            # waterrain.WaterRain (호수·계곡·물웅덩이 수면에 떨어지는 빗방울)
        self.wet = None              # wetrock.WetRocks (젖은 표면 반짝임 + 흘러내리는 빗물, v11.19)
        self.interior = None         # interior.Interior (촛불·벽난로 불꽃·불빛 일렁임, v11.22)
        self.wan_room = None         # wanroom.WanRoom (Wan 이 만든 불꽃·촛불·숨쉬기 움직임, v11.22)
        self.tonearm = None          # interior.TonearmBob (톤암 오르내림, v11.22)
        self.records = None          # interior.RecordSpin (턴테이블 레코드판 회전, v11.22)
        self.steam = None            # interior.Steam (커피잔·주전자 김, v11.24)
        self.fans = None             # interior.FanSpin (천장 선풍기 회전, v11.22)
        self.pets = None             # interior.PetBreath (반려동물 숨쉬기, v11.22)
        self.stream = None           # streamflow.StreamFlow (대롱·폭포 물줄기 흐름, v11.21)
        self.detail_color = np.array([235, 240, 245], dtype=np.float32) / 255.0
        self.haze = None             # set_depth(): 먼 곳이 빗속 공기에 묻히는 원근감 (depth 방식)
        self.finish = None
        if self.depth_style and (settings.grade > 0 or settings.grain > 0):
            from .finish import Finish
            self.finish = Finish(self.W, self.H, self.N, settings.grade, settings.grain, seed=settings.seed + 3)

    def set_outside(self, om):
        """om: (H,W) 0..1 — 비가 내리는 바깥 영역. 빗줄기·장막·안개를 이 영역으로 제한 (텐트 천·텐트 안 바닥에는 비가 안 보이게)."""
        om = np.asarray(om, dtype=np.float32)
        self.outside = om
        if self.layer_w:
            self.layer_w = [(w * om).astype(np.float32) for w in self.layer_w]
        if getattr(self, "veil", None) is not None:
            self.veil = self.veil * om
        if getattr(self, "haze", None) is not None:
            self.haze = self.haze * om[..., None]

    def set_depth(self, depth):
        """depth: (H,W) 0..1, 1 = 가까움. 층마다 '그 층보다 먼 곳에만' 보이게 + 먼 곳 빗줄기 장막."""
        d = np.asarray(depth, dtype=np.float32)
        if getattr(self.s, "dof", 0) > 0 and not getattr(self, "_dof_done", False):
            from .finish import depth_of_field
            self.bg = depth_of_field(self.bg, d, self.res, far_blur=2.2 * float(self.s.dof))
            self._dof_done = True
        self.layer_w = []
        for layer in self.layers:
            w = np.clip((layer.near - d) / 0.12 + 0.5, 0, 1)
            if layer.near < 0.3:                    # 아주 먼 층: 먼 곳일수록 촘촘히 보임
                w = w * (0.6 + 0.8 * np.clip((0.35 - d) / 0.35, 0, 1))
            self.layer_w.append(w.astype(np.float32))
        # 비 장막: 먼 곳에서 개별 빗줄기 대신 보이는 세로 결의 흐름 (루프 동안 정수 바퀴 아래로 이동)
        rng = np.random.default_rng(self.s.seed + 57)
        h, w_ = self.H, max(8, self.W // 3)
        tex = rng.random((h // 6, w_)).astype(np.float32)
        img = Image.fromarray((tex * 255).astype(np.uint8)).resize((self.W, h), Image.BILINEAR)
        img = img.filter(ImageFilter.GaussianBlur((0.6, 18)))
        tex = np.asarray(img, dtype=np.float32) / 255.0
        tex = np.clip((tex - tex.mean()) * 4 + 0.5, 0, 1)
        far = np.clip((0.4 - d) / 0.3, 0, 1)
        self.veil = tex * far * 0.14 * self.s.intensity * self.s.veil     # veil 0 = 끔 (촛불 창 장면: 큰 어두운 창에서 띠가 번갈아 훑고 지나가 보임)
        self.veil_cycles = max(1, int(round(self.N / self.fps * 0.8)))   # 초당 약 0.8화면 높이
        if self.depth_style:
            self.veil = self.veil * 0.8
            far = np.clip((0.45 - d) / 0.4, 0, 1) ** 1.2
            self.haze = (far * 0.10 * min(1.5, self.s.intensity))[..., None].astype(np.float32)

    # ---------- 초기화 ----------
    def _init_layer(self, layer, rng):
        lw = max(1, round(self.W * layer.scale))
        lh = max(1, round(self.H * layer.scale))
        k = layer.scale * self.res
        n = max(1, int(layer.count * self.s.intensity * (self.W * self.H) / (1920 * 1080)))
        target_v = layer.speed * k * self.s.speed * self.tempo * rng.uniform(0.85, 1.15, n)
        if self.depth_style:
            # 셔터 동안 움직인 거리만큼만 번진 줄 (방울 크기 차이로 길이·밝기 편차)
            length = target_v * SHUTTER * rng.uniform(0.8, 1.2, n)
            tans = self.tan + rng.normal(0, 0.035, n)                     # 방울마다 약 ±2° (바람·크기 차이)
        else:
            length = layer.length * k * rng.uniform(0.7, 1.3, n)
            tans = np.full(n, self.tan)
        span = lh + length.max() + 2                                   # 낙하 구간 S
        cycles = np.maximum(1, np.round(target_v * self.N / span))     # 정수 바퀴 → seamless
        margin = (float(np.abs(tans).max()) + GUST_AMP) * span + 4
        layer.drops = {
            "x0": rng.uniform(0, lw + margin, n),
            "y0": rng.uniform(0, span, n),
            "v": cycles * span / self.N,
            "len": length,
            "tan": tans,
            # classic: 3토막 테이퍼로 평균 밝기가 줄어든 만큼 보정 (x1.7) / depth: 고른 밝기의 번진 줄
            "a": np.minimum(255, layer.alpha * (1.0 if self.depth_style else 1.7)
                            * rng.uniform(0.25 if self.depth_style else 0.5, 1.0, n) * 255).astype(np.int32),
            "wd": (1 + (rng.random(n) < (0.30 if (self.depth_style and layer.scale >= 1.0 and layer.blur < 2) else 0.0))
                   ).astype(np.int32),                              # 가까운 비는 일부가 더 굵게
            "span": span,
            "margin": margin,
            "size": (lw, lh),
        }
        return layer

    def _make_bloom(self, bg, gain):
        """밝은 부분(하늘·가로등) 주변으로 번지는 빛(halation): 카메라 렌즈 특유의 부드러운 번짐. 정지 이미지에서 한 번만 계산."""
        import cv2
        lum = bg @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
        hi = np.clip((lum - 0.74) / 0.26, 0, 1)[..., None] * bg
        glow = cv2.GaussianBlur(hi, (0, 0), 14.0 * self.res) * 0.5 + cv2.GaussianBlur(hi, (0, 0), 40.0 * self.res) * 0.5
        return (glow * 0.20 * gain).astype(np.float32)

    def _make_visibility(self, bg):
        """빗줄기는 어두운 배경 앞에서 잘 보이고 밝은 하늘 앞에서는 거의 안 보인다 (빛 굴절)."""
        lum = bg @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
        small = Image.fromarray((lum * 255).astype(np.uint8)).resize((max(8, self.W // 16), max(8, self.H // 16)),
                                                                     Image.BILINEAR)
        lum = np.asarray(small.filter(ImageFilter.GaussianBlur(2)).resize((self.W, self.H), Image.BILINEAR),
                         dtype=np.float32) / 255.0
        if self.depth_style:   # 밝은 하늘 앞에서는 거의 안 보이게 (예전: 최소 0.4)
            vis = 0.2 + 1.3 * (1.0 - lum) ** 1.3
            # v11.20: 가로등·창문 불빛처럼 아주 밝은 점광원 주변의 비는 빛을 받아 더 밝게 번쩍인다 (역광 빗줄기)
            import cv2
            src = np.clip((lum - 0.82) / 0.18, 0, 1).astype(np.float32)
            if src.max() > 0.05:
                vis = vis + 1.6 * np.clip(cv2.GaussianBlur(src, (0, 0), 28.0 * self.res) * 3.0, 0, 1)
            return np.clip(vis, 0.15, 2.2)[..., None]
        return np.clip(0.6 + 0.9 * (1.0 - lum) ** 1.3, 0.4, 1.4)[..., None]

    def _make_fog(self, rng):
        """FFT 저주파 노이즈 → 양방향으로 주기적인 안개 텍스처."""
        h, w = max(8, self.H // 4), max(8, self.W // 4)
        noise = rng.standard_normal((h, w))
        fy = np.fft.fftfreq(h)[:, None]
        fx = np.fft.rfftfreq(w)[None, :]
        f = np.sqrt(fx ** 2 + (fy * w / h) ** 2)
        spec = np.fft.rfft2(noise) / (1.0 + (f * 60) ** 2.2)
        tex = np.fft.irfft2(spec, s=(h, w))
        tex = (tex - tex.min()) / (np.ptp(tex) + 1e-6)
        tex = np.clip((tex - 0.25) / 0.75, 0, 1) ** 1.5
        img = Image.fromarray((tex * 255).astype(np.uint8)).resize((self.W, self.H), Image.BICUBIC)
        tex = np.asarray(img, dtype=np.float32) / 255.0
        grad = np.linspace(0.35, 1.0, self.H, dtype=np.float32)[:, None] ** 1.5   # 아래쪽이 짙게
        return tex * grad * self.s.fog

    def _make_flash(self, rng):
        flash = np.zeros(self.N, dtype=np.float32)
        for _ in range(max(0, int(self.s.lightning))):
            start = int(rng.integers(0, self.N))
            env = [0.9, 0.3, 0.7, 0.4, 0.25, 0.15, 0.08, 0.04]   # 두 번 번쩍이는 번개
            for i, e in enumerate(env):
                idx = (start + int(i * self.fps / 30)) % self.N
                flash[idx] = max(flash[idx], e)
        return flash

    def _gust(self, f, li):
        """바람 세기에 따라 빗줄기 기울기가 천천히 흔들림 (층마다 위상이 달라 시차가 생김, 루프 N 에서 정확히 반복)."""
        if self.s.gust <= 0:
            return 0.0
        t = 2 * math.pi * f / self.N
        ph = 1.3 * li
        return GUST_AMP * self.s.gust * (0.6 * math.sin(2 * t + ph) + 0.4 * math.sin(5 * t + 1.7 * ph))

    # ---------- 프레임 ----------
    def _rain_mask(self, f):
        mask = np.zeros((self.H, self.W), dtype=np.float32)
        if self.s.intensity <= 0:                            # 비 없는 장면(모닥불·촛불 클로즈업): 빗방울을 한 줄기도 그리지 않음
            return mask
        for li, layer in enumerate(self.layers):
            d = layer.drops
            lw, lh = d["size"]
            y = (d["y0"] + d["v"] * f) % d["span"]
            tan_t = d["tan"] + self._gust(f, li)
            x = (d["x0"] + y * tan_t) % (lw + d["margin"]) - d["margin"] / 2
            dy = d["len"]
            dx = dy * tan_t
            w = max(1, round(layer.width * (self.res if layer.scale >= 1 else 1)))
            if self.depth_style:
                # 번진 빗줄기: 고른 밝기 + 부드러운 가장자리 (1/16 픽셀 정밀도 안티에일리어싱)
                import cv2
                arr = np.zeros((lh, lw), np.uint8)
                for xi, yi, dxi, dyi, ai, wi in zip(x, y, dx, dy, d["a"], d["wd"]):
                    ww = w * int(wi)
                    # 실제 빗줄기처럼 가운데가 가장 진하고 양 끝이 흐려지는 번짐: 전체 길이(옅게) + 가운데 60%(진하게)
                    cv2.line(arr, (int((xi - dxi) * 16), int((yi - dyi) * 16)), (int(xi * 16), int(yi * 16)),
                             int(ai * 0.55), ww, cv2.LINE_AA, 4)
                    cv2.line(arr, (int((xi - dxi * 0.8) * 16), int((yi - dyi * 0.8) * 16)),
                             (int((xi - dxi * 0.2) * 16), int((yi - dyi * 0.2) * 16)), int(ai), ww, cv2.LINE_AA, 4)
                img = Image.fromarray(arr)
                draw = ImageDraw.Draw(img)
            else:
                img = Image.new("L", (lw, lh), 0)
                draw = ImageDraw.Draw(img)
                # 꼬리→머리로 갈수록 진해지는 3토막 (균일한 막대선보다 실제 빗줄기에 가깝다)
                for xi, yi, dxi, dyi, ai in zip(x, y, dx, dy, d["a"]):
                    x1, y1 = xi - dxi, yi - dyi
                    xa, ya = x1 + dxi * 0.4, y1 + dyi * 0.4
                    xb, yb = x1 + dxi * 0.75, y1 + dyi * 0.75
                    draw.line((x1, y1, xa, ya), fill=int(ai * 0.3), width=w)
                    draw.line((xa, ya, xb, yb), fill=int(ai * 0.65), width=w)
                    draw.line((xb, yb, xi, yi), fill=int(ai), width=w)
            if li == len(self.layers) - 1 and self.s.splashes and self.details is None:
                self._draw_splashes(draw, f, lw, lh)
            if layer.blur:
                img = img.filter(ImageFilter.GaussianBlur(layer.blur * self.res * layer.scale ** 0.5))
            if img.size != (self.W, self.H):
                img = img.resize((self.W, self.H), Image.BILINEAR)
            a = np.asarray(img, dtype=np.float32) * (1 / 255.0)
            if self.layer_w is not None:
                a *= self.layer_w[li]
            np.add(mask, a, out=mask)
        if self.veil is not None:
            shift = int(round(self.H * self.veil_cycles * f / self.N)) % self.H
            np.add(mask, np.roll(self.veil, shift, axis=0), out=mask)
        return np.minimum(mask, 1.0, out=mask)

    def _draw_splashes(self, draw, f, lw, lh):
        rng = np.random.default_rng(self.s.seed * 100003 + (f % self.N))
        n = int(40 * self.s.intensity * lw / 1920)
        xs = rng.uniform(0, lw, n)
        ys = lh * (0.72 + 0.28 * rng.random(n) ** 0.7)
        sz = (1.5 + 3.5 * (ys / lh - 0.72) / 0.28) * self.res
        for x, y, r in zip(xs, ys, sz):
            a = int(rng.uniform(60, 140))
            draw.line((x - r, y, x - r * 1.8, y - r * 1.3), fill=a, width=1)
            draw.line((x + r, y, x + r * 1.8, y - r * 1.3), fill=a, width=1)

    def frame(self, f):
        f %= self.N
        out = self.motion.frame(f).copy() if self.motion is not None else self.bg.copy()
        if self.wan_room is not None:
            out = self.wan_room.apply(out, f)                # AI 가 만든 불꽃·촛불·숨쉬기 (v11.22)
        if self.pets is not None:
            out = self.pets.apply(out, f)                    # 자는 반려동물 숨쉬기 (v11.22)
        if self.tonearm is not None:
            out = self.tonearm.apply(out, f)                 # 톤암 오르내림 (v11.22)
        if self.records is not None:
            out = self.records.apply(out, f)                 # 턴테이블 레코드판 (v11.22)
        if self.fans is not None:
            out = self.fans.apply(out, f)                    # 천장 선풍기 회전 (v11.22)
        if self.interior is not None:
            out = self.interior.apply(out, f)                # 촛불·벽난로 불꽃·방 안 불빛 일렁임 (v11.22)
        if self.steam is not None:
            out = self.steam.apply(out, f)                   # 김 (v11.24, 루프 이음새 없음)
        if self.bloom is not None:
            out += self.bloom                                # 밝은 빛 번짐 (halation)
        if self.water is not None:
            out = self.water.apply(out, f)                  # 수면 굴절 → 그 위에 안개·빗줄기
        if self.stream is not None:
            out = self.stream.apply(out, f)                 # 대롱·폭포 물줄기가 위에서 아래로 흐름 (v11.21)
        if self.wet is not None:
            out = self.wet.apply(out, f)                    # 젖은 표면 반짝임·흘러내리는 빗물 (v11.19)
        if self.haze is not None:
            out += (self.fog_color - out) * self.haze
        if self.fog is not None:
            shift = int(round(self.W * f / self.N))       # 루프당 화면 폭 1바퀴 이동
            fog = np.roll(self.fog, shift, axis=1)[..., None]
            out += (self.fog_color - out) * fog
        rm = self._rain_mask(f)
        if self.glass is not None:
            # 초점이 유리(실내)에 있으므로 창밖 빗줄기도 배경만큼 흐리게 → 개별 줄 대신 흐릿한 비 결
            import cv2
            soft, gain = (1.7, 3.0) if self.s.interior > 0 else (5.0, 2.2)     # 실내 장면: 창밖 빗줄기를 더 또렷하고 많이
            rm = np.minimum(cv2.GaussianBlur(rm, (0, 0), soft * self.res) * gain, 1.0)
            rm = rm * self.glass.mask                           # 실내에는 비가 오지 않음
        mask = rm[..., None] * self.s.brightness * self.vis
        out += (self.rain_color - out) * np.minimum(mask, 1.0)
        if self.details is not None:
            out = self.details.apply(out, f)                # 물결·물방울 = 배경 굴절
            layer = np.asarray(self.details.draw(f), dtype=np.float32)[..., None] * (1.0 / 255.0)
            # 흰색으로 덮지 않고 '그 자리 색의 밝은 버전'으로 (어두운 낙엽 길에서 흰 점이 반짝이던 문제)
            bright = np.minimum(out * 1.9 + 0.07, 1.0)
            out += (bright - out) * np.minimum(layer * 1.25, 1.0)
        if self.glass is not None:
            out = self.glass.apply(out, f)
        if self.flash[f] > 0:
            if self.glass is not None:                      # 번개는 창밖과 유리에서만 번쩍, 실내는 아주 살짝 (v11.22)
                wgt = (0.05 + 0.95 * self.glass.mask)[..., None]
                out += (1.0 - out) * (0.35 * self.flash[f]) * wgt
            else:
                out += (1.0 - out) * (0.35 * self.flash[f])
        if self.finish is not None:
            out = self.finish.apply(out, f)
        return (np.clip(out, 0, 1) * 255).astype(np.uint8)

    def frame_image(self, f):
        return Image.fromarray(self.frame(f))
