"""비에 젖은 바위 + 바위 면을 따라 흘러내리는 물줄기 (v11.19, 루프에서 정확히 반복).

- rock_mask():   바위 영역 = 결이 많고(분산 큼) 초록이 아니며 색이 옅은 곳. 잔잔한 물(매끈함)·하늘·잎은 제외.
- wet_look():    바위 영역만 어둡게 + 국소 대비↑ + 살짝 차가운 색 → 젖은 돌 느낌 (정지 이미지에 1회)
- WetRocks:      프레임마다 (1) 젖은 돌의 반짝임이 천천히 일렁이고 (2) 얇은 물줄기 위로 물이 맺혀 아래로 흘러내림
                 모든 움직임이 N 프레임 뒤 제자리로 돌아와 이음새가 없다.
"""

import numpy as np

LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def rock_mask(bg, depth, veg=None):
    """bg: float RGB (H,W,3) 0..1, depth: (H,W) 0..1 (1 = 가까움), veg: 잎 영역 마스크(있으면 제외). 반환 (H,W) 0..1"""
    import cv2
    H, W = bg.shape[:2]
    sw, sh = 480, max(8, round(480 * H / W))
    rgb = cv2.resize(bg, (sw, sh), interpolation=cv2.INTER_AREA)
    d = cv2.resize(depth.astype(np.float32), (sw, sh), interpolation=cv2.INTER_AREA)
    lum = rgb @ LUMA
    sat = rgb.max(-1) - rgb.min(-1)
    not_green = np.clip(1 - (rgb[..., 1] - np.maximum(rgb[..., 0], rgb[..., 2])) * 12, 0, 1)
    mean = cv2.GaussianBlur(lum, (0, 0), 2)
    var = cv2.GaussianBlur((lum - mean) ** 2, (0, 0), 2) * 40
    tex = np.clip((var - 0.03) / 0.07, 0, 1)                   # 바위·자갈은 결이 많고, 잔잔한 물은 매끈함 (물은 아래에서 한 번 더 제외)
    low_sat = np.clip(1 - (sat - 0.22) / 0.2, 0, 1)             # 회색·갈색 계열 (선명한 색은 제외)
    near = np.clip((d - 0.10) / 0.15, 0, 1)                     # 아주 먼 곳(하늘·먼 산) 제외
    rows = np.linspace(0, 1, sh, dtype=np.float32)[:, None]
    sky = (lum > 0.7) * (sat < 0.08) * (rows < 0.5)
    m = tex * not_green * low_sat * near * (1 - sky)
    if veg is not None:
        v = cv2.resize(veg.astype(np.float32), (sw, sh), interpolation=cv2.INTER_AREA)
        m *= 1 - np.clip(v * 2.0, 0, 1)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    m = cv2.GaussianBlur(m, (0, 0), 2.5)
    m = np.clip(cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR), 0, 1)
    from .waterrain import water_mask                         # 수면(매끈하고 수평)으로 판정된 곳은 바위에서 제외
    m *= 1.0 - np.clip(water_mask(bg, depth) * 1.5, 0, 1)
    return m


def wet_look(bg, mask, wet=1.0, res=1.0):
    """바위 영역만 젖은 돌처럼: 어둡게 + 국소 대비 + 차가운 색. 정지 이미지에 한 번만 적용."""
    import cv2
    m = mask[..., None].astype(np.float32)
    blur = cv2.GaussianBlur(bg, (0, 0), 5.0 * res)
    local = bg + (bg - blur) * (0.35 * wet)                     # 물에 젖어 결이 또렷해짐
    tint = np.array([0.965, 0.99, 1.035], dtype=np.float32)
    wet_bg = np.clip(local * (1.0 - 0.22 * wet) * tint, 0, 1)
    return (bg * (1 - m) + wet_bg * m).astype(np.float32)


def _smooth_noise(h, w, scale, rng):
    from .motion import _noise
    return _noise(h, w, scale, rng)


class WetRocks:
    def __init__(self, bg, mask, N, fps, wet=1.0, seed=7):
        """bg: wet_look 이 이미 적용된 float RGB (H,W,3). mask: rock_mask 결과."""
        import cv2
        self.cv2 = cv2
        self.bg, self.mask = bg, mask
        self.H, self.W = bg.shape[:2]
        self.N, self.fps, self.wet = N, fps, wet
        self.res = self.H / 1080.0
        rng = np.random.default_rng(seed + 313)
        self.coverage = float((mask > 0.5).mean())

        # (1) 반짝임: 바위 결의 밝은 부분(국소 하이라이트)이 천천히 일렁임 — A·cos + B·sin, 주기 = N/k
        lum = bg @ LUMA
        hp = lum - cv2.GaussianBlur(lum, (0, 0), 6.0 * self.res)
        hl = np.clip(hp * 7.0, 0, 1) * mask
        a = _smooth_noise(self.H, self.W, max(16, int(90 * self.res)), rng) * 0.5
        b = _smooth_noise(self.H, self.W, max(16, int(90 * self.res)), rng) * 0.5
        self.h0 = (hl * 0.55).astype(np.float32)
        self.ha = (hl * a * 0.45).astype(np.float32)
        self.hb = (hl * b * 0.45).astype(np.float32)
        self.k_sheen = 3
        self.sheen_gain = 0.42 * wet

        # (2) 흘러내리는 물줄기
        self.rivulets = self._make_rivulets(mask, rng, wet)
        self._buf = np.zeros((self.H, self.W), np.uint8)
        self.trail = self._draw_trails()

    # ---------- 물줄기 경로 ----------
    def _make_rivulets(self, mask, rng, wet):
        res = self.res
        n = int(np.clip(self.coverage * 170 * wet, 4, 70)) if self.coverage > 0.01 else 0
        if n == 0:
            return []
        weight = (mask > 0.55).astype(np.float64)
        weight *= np.linspace(1.6, 0.6, self.H)[:, None]            # 바위 위쪽에서 시작하는 물줄기를 더 많이
        flat = weight.ravel()
        if flat.sum() < 1e-3:
            return []
        flat /= flat.sum()
        out = []
        for idx in rng.choice(flat.size, size=n, p=flat):
            y0, x0 = divmod(int(idx), self.W)
            length = rng.uniform(70, 220) * res
            amp = rng.uniform(2.0, 7.0) * res
            lam = rng.uniform(25.0, 60.0) * res
            ph = rng.uniform(0, 2 * np.pi)
            pts, y = [], float(y0)
            while y < y0 + length and y < self.H - 2:
                x = x0 + amp * np.sin((y - y0) / lam + ph) + 0.06 * (y - y0) * rng.uniform(-1, 1) * 0.0
                xi, yi = int(round(x)), int(round(y))
                if not (0 <= xi < self.W) or mask[yi, xi] < 0.35:
                    break                                           # 바위가 끝나면 물줄기도 멈춤
                pts.append((xi, yi))
                y += 3.0 * res
            if len(pts) >= 6:
                out.append({"pts": np.array(pts, np.int32), "k": int(rng.integers(1, 4)),
                            "phase": float(rng.uniform(0, 1)), "w": max(1, int(round(rng.uniform(0.9, 1.7) * res)))})
        return out

    def _draw_trails(self):
        """물이 지나간 젖은 자국을 한 번만 그려 둔다: 어두운 가장자리(젖은 돌) + 가운데 가늘게 반짝이는 물 막."""
        cv2 = self.cv2
        edge = np.zeros((self.H, self.W), np.uint8)
        core = np.zeros((self.H, self.W), np.uint8)
        for r in self.rivulets:
            line = r["pts"].reshape(-1, 1, 2)
            cv2.polylines(edge, [line], False, 255, r["w"] + 2, cv2.LINE_AA)
            cv2.polylines(core, [line], False, 255, max(1, int(round(r["w"] * 0.6))), cv2.LINE_AA)
        edge = cv2.GaussianBlur(edge, (0, 0), 1.1 * self.res)
        self.trail_dark = (edge.astype(np.float32) * (1 / 255.0) * 0.30 * min(1.4, self.wet)).astype(np.float32)
        self.trail_core = (core.astype(np.float32) * (1 / 255.0) * 0.20 * min(1.4, self.wet)).astype(np.float32)
        return self.trail_dark

    # ---------- 프레임 ----------
    def apply(self, out, f):
        """out: float RGB (H,W,3) 0..1 제자리 수정 후 반환."""
        cv2 = self.cv2
        if self.rivulets:                                           # 젖은 자국: 어두운 가장자리 + 반짝이는 물 막
            out *= (1.0 - self.trail_dark)[..., None]
            out += (0.92 - out) * self.trail_core[..., None]
        # 돌 표면 반짝임 일렁임 (루프 N 에서 정확히 k 바퀴)
        t = 2 * np.pi * self.k_sheen * f / self.N
        sheen = self.h0 + self.ha * np.cos(t) + self.hb * np.sin(t)
        out += ((1.0 - out) * (sheen * self.sheen_gain)[..., None])
        # 흘러내리는 물방울: 밝은 머리(방울) + 늘어진 꼬리
        if self.rivulets:
            buf = self._buf
            buf.fill(0)
            tail = ((255, 2), (205, 2), (150, 2), (100, 2), (60, 2), (30, 2))     # (밝기, 구간 길이=경로 점 수)
            for r in self.rivulets:
                pts = r["pts"]
                n = len(pts)
                head = int(((f / self.N) * r["k"] + r["phase"]) % 1.0 * (n + 16) - 8)   # 경로 앞뒤로 여유를 두고 지나감
                i1 = head
                for a, step in tail:
                    i0 = i1 - step
                    lo, hi = max(i0, 0), min(i1, n - 1)
                    if lo < hi:
                        cv2.line(buf, (int(pts[lo][0]), int(pts[lo][1])), (int(pts[hi][0]), int(pts[hi][1])),
                                 a, r["w"] + 1, cv2.LINE_AA)
                    i1 = i0
                if 0 <= head < n:                                   # 맨 앞의 작고 동그란 물방울
                    cv2.circle(buf, (int(pts[head][0]), int(pts[head][1])), max(1, int(round(1.7 * self.res))),
                               255, -1, cv2.LINE_AA)
            drops = buf.astype(np.float32) * (1 / 255.0) * (0.62 * min(1.4, self.wet))
            out += ((0.96 - out) * drops[..., None])
        return out
