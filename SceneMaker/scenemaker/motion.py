"""배경 자체의 미세한 움직임 (AI 영상 모델 없이, 루프에서 정확히 반복).

원리: 두 개의 부드러운 노이즈 장 A, B 로 변위 d(t) = A·cos(ωt) + B·sin(ωt), ω = 2πk/N.
     → t = N 에서 정확히 원래로 돌아오고, 공간적으로 물결치듯 움직인다.
- 나뭇잎·풀: 초록 영역에서 1~3px 흔들림 (먼 곳은 작게, 위쪽 가지는 크게)
- 물웅덩이·젖은 길: 반사가 일렁이는 작고 빠른 변위
"""

import numpy as np
from PIL import Image, ImageFilter


def _noise(h, w, scale, rng):
    """주기 경계와 무관한 부드러운 노이즈 (-1..1)."""
    small = rng.standard_normal((max(2, h // scale), max(2, w // scale))).astype(np.float32)
    img = Image.fromarray(((small - small.min()) / (np.ptp(small) + 1e-6) * 255).astype(np.uint8))
    img = img.resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(scale / 4))
    a = np.asarray(img, dtype=np.float32)
    a = (a - a.mean()) / (a.std() + 1e-6)
    return np.clip(a, -2.5, 2.5)


def vegetation_mask(bg, depth):
    """초록(식물) 영역 × 너무 가깝지 않은 곳. bg: float RGB (H,W,3) 0..1"""
    r, g, b = bg[..., 0], bg[..., 1], bg[..., 2]
    green = np.clip((g - np.maximum(r, b)) * 6, 0, 1)            # 초록이 우세할수록 1
    m = green * np.clip((0.85 - depth) / 0.3, 0, 1)                # 바로 앞 물체(의자 등) 제외
    img = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))
    return np.asarray(img, dtype=np.float32) / 255.0


def foliage_mask(bg, depth, mode="green", exclude=None):
    """흔들릴 잎 영역. mode="green": 초록만(여름 씬). mode="autumn": 채도 높은 빨강~노랑~초록 모두
    (2026-10-03: 가을 잎은 노랑·주황이라 초록 마스크로는 화면의 1.3%만 잡혀 잎이 거의 안 움직였음).
    exclude: (H,W) 0..1 — 땅(낙엽이 깔린 길) 등 흔들리면 안 되는 곳."""
    if mode != "autumn":
        m = vegetation_mask(bg, depth)
    else:
        mx, mn = bg.max(-1), bg.min(-1)
        sat = (mx - mn) / (mx + 1e-6)
        leaf = np.clip((sat - 0.24) / 0.12, 0, 1) * np.clip((mx - 0.2) / 0.1, 0, 1)    # 채도 있고 어둡지 않은 곳
        leaf = leaf * np.clip((0.88 - depth) / 0.25, 0, 1)                              # 바로 앞 물체 제외
        img = Image.fromarray((leaf * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))
        m = np.asarray(img, dtype=np.float32) / 255.0
    if exclude is not None:
        m = m * (1.0 - np.clip(np.asarray(exclude, np.float32) * 1.5, 0, 1))
    return m


class BackgroundMotion:
    def __init__(self, bg, depth, puddle, N, sway=1.0, water=1.0, seed=7, fps=30,
                 foliage="green", exclude=None, kicks=1.0):
        """bg: float RGB (H,W,3), depth/puddle: float (H,W) 0..1, N: 루프 프레임 수.
        foliage: "green"|"autumn" (잎 색 판정), exclude: 흔들지 않을 영역(땅), kicks: 빗방울 맞고 튕기는 세기(0=끔)."""
        self.bg = bg
        self.H, self.W = bg.shape[:2]
        self.N = N
        self.fps = fps
        res = self.H / 1080.0
        rng = np.random.default_rng(seed + 29)
        veg = foliage_mask(bg, depth, foliage, exclude)
        self.veg_coverage = float((veg > 0.25).mean())          # 화면에서 잎으로 인식한 비율 (로그 확인용)
        self._init_kicks(veg, depth, res, kicks, rng)
        # 위쪽(가지·잎)은 더 크게, 먼 곳은 작게 흔들림
        rows = np.linspace(1.4, 0.5, self.H, dtype=np.float32)[:, None]
        # 목표: 잎 평균 약 3px, 가까운 잎 최대 8px 정도 (1440p 기준)
        amp_leaf = veg * rows * (0.4 + 0.6 * np.clip(depth / 0.6, 0, 1)) * 3.0 * res * sway
        # 서로 다른 박자·크기의 바람 3개 (가지마다 따로 흔들리게), 모두 루프 주기의 정수배
        self.leaf = []
        for k, scale, w in ((2, 160, 0.55), (5, 70, 0.3), (11, 36, 0.15)):
            comps = [(_noise(self.H, self.W, scale, rng) * amp_leaf * w,
                      _noise(self.H, self.W, scale, rng) * amp_leaf * w * 0.45) for _ in range(2)]
            self.leaf.append((k, comps))
        self.gust_phase = float(rng.uniform(0, 2 * np.pi))       # 돌풍: 루프 동안 두 번 세졌다 약해짐
        # 물 일렁임은 물웅덩이·젖은 길만 (가까운 물체 윗면 — 의자 등 — 은 제외)
        amp_w = puddle * np.clip((0.8 - depth) / 0.1, 0, 1) * 1.6 * res * water
        self.water = [(_noise(self.H, self.W, 24, rng) * amp_w, _noise(self.H, self.W, 24, rng) * amp_w)
                      for _ in range(2)]
        self.k_water = 6                                              # 더 빠른 일렁임
        self.active = float(amp_leaf.max()) > 0.05 or float(amp_w.max()) > 0.05 or getattr(self, 'kick_on', False)
        self.yy, self.xx = np.mgrid[0:self.H, 0:self.W].astype(np.float32)

    def _init_kicks(self, veg, depth, res, kicks, rng):
        """잎마다 따로: 빗방울에 맞는 순간(불규칙 간격 ~0.5~1.5초) 아래로 톡 눌렸다가 감쇠 진동으로 되돌아옴.
        셀(약 14px) 단위 이벤트 → 부드럽게 퍼뜨려 잎 크기 정도의 덩어리가 독립적으로 움직임. 루프에서 정확히 반복."""
        import cv2
        self.kick_on = kicks > 0 and float(veg.max()) > 0.1
        if not self.kick_on:
            return
        self.cell = max(10, int(round(26 * res)))      # 잎 한두 장 크기 (약 35px @1440p)
        gh, gw = self.H // self.cell, self.W // self.cell
        self.gh, self.gw = gh, gw
        # 픽셀당 최대 이동량(px): 가까울수록 크게
        self.kick_amp = (veg * (0.45 + 0.55 * np.clip(depth / 0.6, 0, 1)) * 15.0 * res * kicks).astype(np.float32)
        cell_amp = cv2.resize(veg, (gw, gh), interpolation=cv2.INTER_AREA)
        cells = np.nonzero(cell_amp.ravel() > 0.25)[0]
        secs = self.N / self.fps
        ev_cell, ev_t, ev_a, ev_T, ev_sx = [], [], [], [], []
        for c in cells:
            k = int(rng.poisson(1.1 * secs * float(np.clip(cell_amp.ravel()[c] * 1.5, 0.3, 1.0))))
            if k == 0:
                continue
            ev_cell.append(np.full(k, c, np.int32))
            ev_t.append(rng.uniform(0, self.N, k))
            ev_a.append(rng.uniform(0.5, 1.5, k))                 # 맞은 세기
            ev_T.append(rng.uniform(7, 13, k))                     # 진동 주기(프레임) = 약 2.3~4Hz
            ev_sx.append(rng.uniform(-0.45, 0.45, k))              # 좌우로 살짝 비껴 튕김
        if not ev_cell:
            self.kick_on = False
            return
        self.ev_cell = np.concatenate(ev_cell)
        self.ev_t = np.concatenate(ev_t)
        self.ev_a = np.concatenate(ev_a)
        self.ev_T = np.concatenate(ev_T)
        self.ev_sx = np.concatenate(ev_sx)

    def kick_field(self, f):
        """이 프레임의 튕김 변위 (dx, dy) 전체 해상도. 아래로 먼저 눌리고(+y) 감쇠 진동."""
        import cv2
        tau = (f - self.ev_t) % self.N
        act = tau < 3.0 * 13
        if not act.any():
            return None
        tt, T = tau[act], self.ev_T[act]
        resp = self.ev_a[act] * np.exp(-tt / (0.6 * T)) * np.sin(2 * np.pi * tt / T)
        size = self.gh * self.gw
        fy = np.bincount(self.ev_cell[act], weights=resp, minlength=size).reshape(self.gh, self.gw)
        fx = np.bincount(self.ev_cell[act], weights=resp * self.ev_sx[act], minlength=size).reshape(self.gh, self.gw)
        out = []
        for fld in (fx, fy):
            fld = cv2.GaussianBlur(fld.astype(np.float32), (0, 0), 0.8)
            out.append(cv2.resize(fld, (self.W, self.H), interpolation=cv2.INTER_CUBIC) * self.kick_amp)
        return out[0], out[1]

    def frame(self, f):
        if not self.active and not getattr(self, "kick_on", False):
            return self.bg
        gust = 0.6 + 0.4 * np.cos(2 * np.pi * 2 * f / self.N + self.gust_phase)
        dx = np.zeros((self.H, self.W), np.float32)
        dy = np.zeros((self.H, self.W), np.float32)
        for k, ((ax, ay), (bx, by)) in self.leaf:
            t = 2 * np.pi * k * f / self.N
            dx += (ax * np.cos(t) + bx * np.sin(t)) * gust
            dy += (ay * np.cos(t) + by * np.sin(t)) * gust
        tw = 2 * np.pi * self.k_water * f / self.N
        (wx1, wy1), (wx2, wy2) = self.water
        dx += wx1 * np.cos(tw) + wx2 * np.sin(tw)
        dy += wy1 * np.cos(tw) + wy2 * np.sin(tw)
        if getattr(self, "kick_on", False):
            kf = self.kick_field(f)
            if kf is not None:
                dx += kf[0]
                dy += kf[1]
        return _remap(self.bg, self.xx + dx, self.yy + dy)


def _remap(img, x, y):
    try:
        import cv2
        return cv2.remap(img, x.astype(np.float32), y.astype(np.float32), cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_REFLECT)
    except ImportError:
        return _bilinear(img, x, y)


def _bilinear(img, x, y):
    H, W = img.shape[:2]
    x = np.clip(x, 0, W - 1.001)
    y = np.clip(y, 0, H - 1.001)
    x0 = x.astype(np.int32)
    y0 = y.astype(np.int32)
    fx = (x - x0)[..., None]
    fy = (y - y0)[..., None]
    a = img[y0, x0]
    b = img[y0, x0 + 1]
    c = img[y0 + 1, x0]
    d = img[y0 + 1, x0 + 1]
    top = a + (b - a) * fx
    bot = c + (d - c) * fx
    return top + (bot - top) * fy
