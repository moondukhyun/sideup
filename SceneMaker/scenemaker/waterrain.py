"""물 위에 떨어지는 빗방울 (2026-10-01): 호수·계곡·물웅덩이 수면에 부딪히는 순간 + 번지는 동심원.

실제 비 오는 수면에서 보이는 것
- 부딪히는 순간 1~2프레임: 작은 밝은 점, 가까우면 위로 솟는 짧은 물기둥
- 그 뒤 0.5~0.8초: 원근 때문에 납작한 타원 고리가 퍼지며 약해짐 — 그려진 선이 아니라
  수면이 휘어 배경 반사가 일그러지는 것(굴절)이라, 높이 지도를 만들어 배경을 휘게 한다.
- 멀수록 작고 촘촘하고 흐리며, 가까울수록 크고 드물게 보인다.
모든 이벤트는 루프 N 프레임 안에서 (f - 탄생) mod N 으로 반복 → 이음새 없음.
"""

import numpy as np
from PIL import Image


def water_mask(bg, depth, extra=None, relaxed=False):
    """bg: float RGB (H,W,3) 0..1, depth: (H,W) 0..1 (1 = 가까움), extra: 추가로 물로 볼 곳(Wan 움직임 등).

    잔잔한 수면 = 멀어지는 수평면(아래로 갈수록 가까워짐) + 초록 아님 + 매끈함(바위·풀보다 결이 적음).
    """
    import cv2
    H, W = bg.shape[:2]
    sw, sh = 480, max(8, round(480 * H / W))
    rgb = cv2.resize(bg, (sw, sh), interpolation=cv2.INTER_AREA)
    d = cv2.resize(depth.astype(np.float32), (sw, sh), interpolation=cv2.INTER_AREA)
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    k = 4
    gy = np.zeros_like(d)
    gy[:-k] = d[k:] - d[:-k]
    flat = np.clip((gy + 0.001) / 0.01, 0, 1)
    if relaxed:                                                   # 텐트 문 너머 먼 호수: 깊이 변화가 거의 없어서 '수평면' 판정이 약함 → 푸르스름·회색에 매끈한 곳이면 물로 인정
        rws = np.linspace(0, 1, sh, dtype=np.float32)[:, None]
        flat = np.maximum(flat, np.clip((gy + 0.0005) / 0.004, 0, 1) * 0.9)
        flat = np.maximum(flat, np.clip((rws - 0.38) / 0.07, 0, 1) * np.clip((0.72 - rws) / 0.06, 0, 1))      # 화면 가운데쯤의 매끈한 면 = 호수 (자갈·산은 결이 많아 아래 '매끈함'에서 걸러짐)
    not_green = np.clip(1 - (rgb[..., 1] - np.maximum(rgb[..., 0], rgb[..., 2])) * 12, 0, 1)
    mean = cv2.GaussianBlur(lum, (0, 0), 2)
    var = cv2.GaussianBlur((lum - mean) ** 2, (0, 0), 2) * 40
    smooth = np.clip(1.0 - var / 0.12, 0, 1)
    # 하늘 제외: 화면 위 1/3 의 밝고 색 없는 곳
    sat = rgb.max(-1) - rgb.min(-1)
    rows = np.linspace(0, 1, sh, dtype=np.float32)[:, None]
    sky = (lum > 0.7) * (sat < 0.08) * (rows < 0.45)
    m = flat * not_green * smooth * (1 - sky)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    m = cv2.GaussianBlur(m, (0, 0), 2)
    m = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)
    if extra is not None:
        m = np.maximum(m, np.clip(extra.astype(np.float32) * 1.3, 0, 1))
    return np.clip(m, 0, 1)


class WaterRain:
    def __init__(self, mask, depth, W, H, N, fps, intensity=1.0, seed=7, boost=1.0):
        self.W, self.H, self.N, self.fps = W, H, N, fps
        self.res = H / 1080.0
        self.depth = depth
        rng = np.random.default_rng(seed + 211)
        area = float(mask.mean())
        secs = N / fps
        # 초당 부딪힘 수: 물 넓이에 비례 (수면이 화면 30% 면 1080p 기준 초당 약 150개)
        n = int(500 * intensity * area * secs)
        self.count = n
        self.coverage = area
        p = mask.ravel().astype(np.float64)
        self.events = []
        if n <= 0 or p.sum() < 1e-3:
            return
        p /= p.sum()
        idx = rng.choice(p.size, size=n, p=p)
        ys, xs = np.divmod(idx, W)
        for x, y, b in zip(xs, ys, rng.integers(0, N, n)):
            dd = float(depth[y, x])
            near = dd ** 1.3
            R = (3.0 + 30.0 * near) * self.res * rng.uniform(0.7, 1.3) * boost       # 다 퍼졌을 때 반지름 (boost: 먼 호수 물결이 안 보일 때 키움)
            life = int((0.45 + 0.35 * near) * fps * rng.uniform(0.8, 1.2))    # 약 0.5~0.8초
            self.events.append(dict(x=float(x) + rng.uniform(-0.5, 0.5), y=float(y), b=int(b), d=dd,
                                    R=R, life=max(6, life), flat=0.10 + 0.32 * near,
                                    amp=(0.6 + 2.2 * near) * self.res * rng.uniform(0.7, 1.2) * boost,
                                    lam=max(2.0, (1.6 + 5.0 * near) * self.res),
                                    speck=0.10 + 0.25 * near, seed=int(rng.integers(1 << 30))))

    def apply(self, out, f):
        """out: float RGB (H,W,3). 수면 높이 지도 → 배경 굴절 + 하늘빛 반사, 부딪힌 순간의 밝은 점."""
        import cv2
        if not self.events:
            return out
        h = None
        specks = []
        boxes = []
        for e in self.events:
            age = (f - e["b"]) % self.N
            if age >= e["life"]:
                continue
            if h is None:
                h = np.zeros((self.H, self.W), np.float32)
            t = age / e["life"]
            if age <= 1:
                specks.append((e, age))
            rf = e["R"] * (0.12 + 0.88 * t ** 0.6)               # 고리 앞머리 (처음엔 빠르게, 점점 느리게)
            amp = e["amp"] * (1 - t) ** 1.6
            if age == 0:
                continue
            pw = int(rf + 3 * e["lam"]) + 2
            ph = int(pw * e["flat"]) + 2
            x0, y0 = max(0, int(e["x"]) - pw), max(0, int(e["y"]) - ph)
            x1, y1 = min(self.W, int(e["x"]) + pw + 1), min(self.H, int(e["y"]) + ph + 1)
            if x1 <= x0 or y1 <= y0:
                continue
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            r = np.sqrt((xx - e["x"]) ** 2 + ((yy - e["y"]) / e["flat"]) ** 2)
            u = (r - rf) / e["lam"]
            # 앞머리 뒤로 2~3겹 잔물결, 안쪽은 이미 잔잔해짐
            ring = np.cos(u * 2 * np.pi) * np.exp(-(u / 1.1) ** 2) * (u < 1.5)
            h[y0:y1, x0:x1] += amp * ring
            boxes.append((x0, y0, x1, y1))
        if h is not None and boxes:
            bx0 = min(b[0] for b in boxes); by0 = min(b[1] for b in boxes)
            bx1 = max(b[2] for b in boxes); by1 = max(b[3] for b in boxes)
            bx0, by0 = max(0, bx0 - 2), max(0, by0 - 2)
            bx1, by1 = min(self.W, bx1 + 2), min(self.H, by1 + 2)
            hs = h[by0:by1, bx0:bx1]
            gx = cv2.Sobel(hs, cv2.CV_32F, 1, 0, ksize=3) * 0.125
            gyy = cv2.Sobel(hs, cv2.CV_32F, 0, 1, ksize=3) * 0.125
            yy, xx = np.mgrid[by0:by1, bx0:bx1].astype(np.float32)
            # 기울어진 수면에 비친 배경이 옆으로 밀림 (세로는 원근 때문에 더 크게)
            warped = cv2.remap(out, xx + gx * 2.0, yy + gyy * 3.5, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            # 카메라 쪽으로 기운 면은 하늘을 더 비춰 살짝 밝게, 반대쪽은 어둡게
            shade = np.clip(-gyy * 0.05 - gx * 0.01, -0.05, 0.08)[..., None]
            out[by0:by1, bx0:bx1] = warped + shade * (0.6 + 0.4 * warped)
        for e, age in specks:
            self._speck(out, e, age)
        return out

    def _speck(self, out, e, age):
        """부딪힌 순간: 납작한 밝은 점, 가까운 물은 위로 솟는 짧은 물기둥."""
        s = max(0.8, e["R"] * 0.06)
        rng = np.random.default_rng(e["seed"])
        a = e["speck"] * (1.0 if age == 0 else 0.5) * rng.uniform(0.6, 1.1)
        x, y = e["x"], e["y"] - (s * 1.5 * age if e["d"] > 0.5 else 0)
        rx, ry = s * (1.0 if age else 1.4), s * (0.6 if age else 0.35)
        if e["d"] > 0.5 and age == 1:
            ry = s * 1.6                                   # 솟는 물기둥
        x0, x1 = int(x - rx - 2), int(x + rx + 3)
        y0, y1 = int(y - ry - 2), int(y + ry + 3)
        if x0 < 0 or y0 < 0 or x1 > self.W or y1 > self.H:
            return
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        g = np.exp(-(((xx - x) / rx) ** 2 + ((yy - y) / ry) ** 2) * 1.5)[..., None]
        patch = out[y0:y1, x0:x1]
        out[y0:y1, x0:x1] = patch + (0.92 - patch) * g * a


def preview_mask(bg, mask, path):
    a = (np.clip(bg, 0, 1) * 255).astype(np.float32)
    a[..., 0] = a[..., 0] * (1 - mask) + 40 * mask
    a[..., 1] = a[..., 1] * (1 - mask * 0.3)
    a[..., 2] = a[..., 2] * (1 - mask) + 255 * mask * 0.8 + a[..., 2] * mask * 0.2
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((1280, 720)).save(path)
