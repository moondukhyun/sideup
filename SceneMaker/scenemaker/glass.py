"""창가 씬: 유리에 맺힌 물방울 + 멈췄다 흘렀다 하며 흘러내리는 큰 방울과 자국 (루프에서 정확히 반복).

v11.20 사실감 개선 (실제 창문 촬영처럼):
- 물방울 크기·밀도 재설계: 눈에 보이는 중간·큰 방울(3~15px) + 아주 작은 안개 방울. 예전엔 대부분 1~2px 이라 거의 안 보였음
- 방울 광학: 뒤 풍경을 거꾸로 작게 비추는 렌즈 + 또렷한 테두리(어두운 고리) + 위쪽 큰 반사광 + 아래쪽 약한 반사광
- 방울이 서서히 맺혔다가 갑자기 쓸려 내려간 것처럼 사라지는 시간 변화(톱니 모양), 그룹 5개가 서로 어긋남
- 흘러내리는 방울 6~12개: 속도에 따라 길쭉해지고, 지나간 자리에 가는 물길 + 작은 방울이 줄지어 남음
- 아래쪽으로 갈수록 살짝 뿌연 결로(김서림) — 방울이 지나간 자리는 맑게

- 창 영역: 깊이 지도에서 먼 곳(바깥 풍경) = 유리 너머
- 작은 물방울: 네 그룹으로 나눠 미리 굴절 렌더링 → 그룹마다 천천히 생겼다 사라짐 (주기적)
- 흘러내리는 방울: 경로를 미리 계산(멈춤·미끄러짐 반복, 좌우 흔들림), 지나간 자리에 작은 방울 자국
각 방울은 뒤 풍경을 거꾸로 작게 비추는 렌즈로 그림 (흰 점이 아님).
"""

import numpy as np
from PIL import Image, ImageFilter


def window_mask(depth, bg=None, shrink=4):
    """창밖(유리 너머) = 1. depth: 0..1 (1 = 가까움).
    먼 곳 → 구멍 메우기 → 큰 덩어리만 남김 → 그 뒤에 '창 앞의 가까운 물체'(잔·화분·접시)를 다시 빼서
    구멍 메우기에 삼켜지지 않게 한다 (2026-10-01 Cowork 검토: 잔·화분 잎 위에 물방울/빗줄기가 그려지던 버그)."""
    import cv2
    thr = np.percentile(depth, 60)
    far = (depth < min(thr, 0.55))
    # 창 앞 물체: 창 영역(먼 곳)보다 확실히 가까운 값 — 창 뒤 가까운 가로수 등은 깊이가 낮아 영향 없음
    d_far = float(np.median(depth[far])) if far.any() else 0.0
    near_obj = depth > max(d_far + 0.18, 0.42)
    m = far.astype(np.uint8)
    if bg is not None:                                       # 조명 받은 밝고 따뜻한 실내 벽 제외
        sm = cv2.GaussianBlur(bg, (0, 0), 6)
        warm = (sm[..., 0] - sm[..., 2] > 0.07) & (sm.mean(-1) > 0.45)
        m[warm] = 0
    k = max(3, int(depth.shape[0] / 60)) | 1
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    if n > 1:
        areas = stats[1:, cv2.CC_STAT_AREA]
        keep = 1 + np.nonzero(areas >= areas.max() * 0.15)[0]
        m = np.isin(lab, keep).astype(np.uint8)
    if bg is not None:                                        # 창틀: 어둡고(밝기<0.14) 매끈한(분산 작음) 세로로 긴 덩어리
        lum = bg @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
        mean = cv2.GaussianBlur(lum, (0, 0), 4)
        var = cv2.GaussianBlur((lum - mean) ** 2, (0, 0), 4)
        dark = ((mean < 0.14) & (var < 0.0012)).astype(np.uint8)
        dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        n2, lab2, st2, _ = cv2.connectedComponentsWithStats(dark, 8)
        frame = np.zeros_like(dark)
        for i in range(1, n2):
            w_, h_, area = st2[i, cv2.CC_STAT_WIDTH], st2[i, cv2.CC_STAT_HEIGHT], st2[i, cv2.CC_STAT_AREA]
            if area > depth.size * 0.002 and (h_ > 2.0 * w_ or w_ > 2.0 * h_):      # 길쭉한 어두운 덩어리 = 창틀
                frame[lab2 == i] = 1
        frame = cv2.dilate(frame, np.ones((7, 7), np.uint8))                        # 3px 침식 효과 (경계 여유)
        m[frame > 0] = 0
    # 가까운 물체는 가장자리 여유를 두고 제외 (물체 윤곽을 따라 12px 확장)
    ex = int(depth.shape[0] / 120) * 2 + 1
    near_u8 = cv2.dilate(near_obj.astype(np.uint8), np.ones((ex, ex), np.uint8))
    m[near_u8 > 0] = 0
    img = Image.fromarray(m * 255)
    img = img.filter(ImageFilter.MinFilter(2 * shrink + 1)).filter(ImageFilter.GaussianBlur(2))
    return np.asarray(img, dtype=np.float32) / 255.0


def _smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _lens(src, x, y, rad, stretch, cv2):
    """한 방울의 굴절 패치 (좌표, RGB, 알파). 물방울은 작은 볼록 렌즈: 뒤 풍경이 거꾸로 작게 맺힌다."""
    rx, ry = rad, rad * stretch
    H, W = src.shape[:2]
    x0, y0, x1, y1 = int(x - rx) - 2, int(y - ry) - 2, int(x + rx) + 3, int(y + ry) + 3
    if x0 < 0 or y0 < 0 or x1 >= W or y1 >= H or rx < 0.6:
        return None
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    ex, ey = (xx - x) / rx, (yy - y) / ry
    rr = ex * ex + ey * ey
    r = np.sqrt(rr)
    alpha = np.clip((1 - rr) * 3.2, 0, 1)                         # 가장자리가 또렷한 방울
    k = 7.0 + rad * 0.22                                           # 방울은 넓은 풍경을 거꾸로 작게 담는다 (어두운 곳에서도 불빛이 보임)
    mx = (x - ex * rx * k).astype(np.float32)
    my = (y - ey * ry * k).astype(np.float32)
    lens = cv2.remap(src, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    lens = lens * 1.12 + 0.012                                     # 물방울은 빛을 모아 살짝 밝다
    rim = np.clip(1 - np.abs(r - 0.90) / 0.15, 0, 1)
    rim_w = rim * (0.26 + 0.34 * (ey > 0))                         # 테두리 어두운 고리 (아래쪽이 더 진함)
    lens = lens * (1.0 - rim_w[..., None])
    hl = np.exp(-(((ex + 0.32) / 0.20) ** 2 + ((ey + 0.38) / 0.20) ** 2)) * 0.55      # 위쪽 큰 반사광
    hl2 = np.exp(-(((ex - 0.30) / 0.15) ** 2 + ((ey - 0.46) / 0.10) ** 2)) * 0.16     # 아래쪽 약한 반사광
    hs = float(np.clip(rad / 5.0, 0.28, 1.0))                      # 작은 방울은 반사광도 작고 약하게 (별처럼 반짝이지 않게)
    lens = lens + ((hl + hl2) * hs)[..., None]
    return x0, y0, x1, y1, lens, alpha


class GlassRain:
    GROUPS = 5

    def __init__(self, bg, mask, N, fps, amount=1.0, seed=7, view_blur=9.0):
        import cv2
        self.cv2 = cv2
        self.bg, self.mask, self.N, self.fps = bg, mask, N, fps
        self.H, self.W = bg.shape[:2]
        res = self.H / 1080.0
        self.res = res
        rng = np.random.default_rng(seed + 101)
        # 뒤 풍경은 초점 밖처럼 흐리게 (초점은 유리 위 물방울)
        blur = cv2.GaussianBlur(bg, (0, 0), view_blur * res)
        self.base = bg * (1 - mask[..., None]) + blur * mask[..., None]

        # 결로(김서림): 아래쪽일수록 살짝 뿌옇게 — 주변 색을 밝게 끌어올린 안개. 방울이 지나간 자리는 맑아짐
        y = np.linspace(0, 1, self.H, dtype=np.float32)[:, None]
        local = cv2.GaussianBlur(self.base, (0, 0), 45 * res)
        self.fog_col = np.clip(local * 1.7 + 0.04, 0, 1)
        self.fog = (np.clip((y - 0.30) / 0.70, 0, 1) ** 1.4 * 0.10 * min(1.5, amount) * mask).astype(np.float32)
        self.clear = np.zeros((self.H, self.W), np.float32)         # 쓸려 내려간 자리 (정지)
        self._sweep = np.zeros((self.H, self.W), np.float32)        # 프레임마다 쓰는 임시 지도

        # 정지 물방울: 눈에 보이는 중간·큰 방울 + 아주 작은 안개 방울, 그룹 5개 (시간차로 생겼다 사라짐)
        # 개수는 '유리 면적 중 방울이 덮는 비율'로 정한다. (실제 비 오는 창: 중간·큰 방울 약 8~12%, 안개 방울 약 3~5%)
        glass_px = float((mask > 0.5).sum())
        flat = (mask > 0.5).ravel().astype(np.float64)
        self._cdf = np.cumsum(flat / max(flat.sum(), 1.0))              # 위치 뽑기용 누적분포 (한 번만 계산)
        G = self.GROUPS
        a_amt = float(np.clip(amount, 0.5, 1.5))
        med_cov, micro_cov = 0.10 * a_amt, 0.035 * a_amt
        self.groups = []
        self.stats = {"med": 0, "micro": 0}
        for g in range(G):
            layer = self.base.copy()
            alpha = np.zeros((self.H, self.W), np.float32)
            for cov, kind in ((med_cov, "med"), (micro_cov, "micro")):
                budget, n = cov * glass_px / G, 0
                pts = self._sample_fast(8000, rng)
                while budget > 0 and n < len(pts):
                    if kind == "med":
                        rad = float(np.clip(rng.lognormal(np.log(4.6), 0.60), 2.2, 24.0)) * res
                        stretch = (1.0 + min(0.55, rad / (28.0 * res)) * float(rng.uniform(0.3, 1.0))) * float(rng.uniform(0.9, 1.1))
                    else:
                        rad = float(rng.uniform(0.8, 1.9)) * res
                        stretch = float(rng.uniform(0.9, 1.25))
                    self._put(layer, alpha, pts[n][0], pts[n][1], rad, stretch, cv2)
                    budget -= np.pi * rad * rad * stretch
                    n += 1
                self.stats[kind] += n
            self.groups.append((layer, alpha, g / G + float(rng.uniform(-0.04, 0.04))))

        # 흘러내리는 방울 (속도·크기 제각각)
        self.sliders = []
        n_slide = int(np.clip(round(8 * amount), 6, 12))
        for i in range(n_slide):
            sl = self._make_path(rng, N, mask, res)
            sl["start"] = int((i + float(rng.uniform(0, 0.8))) / n_slide * N) % N
            sl["beads"] = self._make_beads(sl, rng, res)
            self.sliders.append(sl)
            self._clear_trail(sl)

    # ---------- 도우미 ----------
    def _put(self, layer, alpha, x, y, rad, stretch, cv2):
        p = _lens(self.base, x, y, rad, stretch, cv2)
        if p is None:
            return
        x0, y0, x1, y1, lens, a = p
        region = layer[y0:y1, x0:x1]
        region += (lens - region) * a[..., None]
        alpha[y0:y1, x0:x1] = np.maximum(alpha[y0:y1, x0:x1], a)

    def _sample_fast(self, n, rng):
        """유리 영역 안의 무작위 좌표 n개 (누적분포로 한 번에)."""
        idx = np.searchsorted(self._cdf, rng.random(n))
        idx = np.minimum(idx, self.H * self.W - 1)
        ys, xs = np.divmod(idx, self.W)
        return list(zip(xs.astype(float) + rng.uniform(-0.5, 0.5, n), ys.astype(float)))

    def _sample(self, mask, n, rng):
        p = (mask > 0.5).ravel().astype(np.float64)
        if n <= 0 or p.sum() == 0:
            return []
        p /= p.sum()
        idx = rng.choice(p.size, size=n, p=p)
        ys, xs = np.divmod(idx, self.W)
        return list(zip(xs.astype(float) + rng.uniform(-0.5, 0.5, n), ys.astype(float)))

    def _make_path(self, rng, period, mask, res):
        """멈춤-미끄러짐(stick-slip) 경로: 한참 매달려 있다가 순간 미끄러지며 감속, 다시 멈춤을 반복.
        한 번 미끄러질 때 약 100~400px (1440p), 주기 동안 위→아래로 한 번 흐르고 사라진다."""
        cols = np.nonzero((mask > 0.5).any(axis=0))[0]
        x = float(rng.choice(cols)) if len(cols) else self.W / 2
        rows = np.nonzero(mask[:, int(x)] > 0.5)[0]
        top, bot = (float(rows.min()), float(rows.max())) if len(rows) else (0.0, float(self.H))
        y = top + rng.uniform(0, 0.35) * (bot - top)
        run = int(period * rng.uniform(0.45, 0.85))
        drift = float(rng.uniform(-0.25, 0.25))
        big = rng.random() < 0.25
        rad = float(rng.uniform(9.0, 13.0) if big else rng.uniform(5.5, 8.5)) * res      # 흘러내리는 방울은 합쳐져서 정지 방울보다 큼
        mass = 0.8 + rad / (13.0 * res)                            # 큰 방울일수록 빠르고 멀리
        fps_k = 30.0 / self.fps
        xs, ys = [], []
        while len(xs) < run and y < bot:
            for _ in range(int(rng.integers(8, 48))):               # 매달려 거의 정지 (아주 미세하게 흔들림)
                xs.append(x + float(rng.normal(0, 0.12)) * res); ys.append(y)
            v0 = float(rng.uniform(4.0, 11.0)) * res * mass * fps_k   # 미끄러짐 시작 속도 (px/프레임)
            for k in range(int(rng.integers(7, 22))):
                v = v0 * (1.0 - 0.75 * k / 22.0)                    # 점점 느려지며 멈춤
                y += v
                x += drift * res * fps_k + float(rng.normal(0, 0.28)) * res
                xs.append(x); ys.append(y)
                if y > bot:
                    break
        return {"xs": np.array(xs), "ys": np.array(ys), "period": period, "rad": rad}

    def _make_beads(self, sl, rng, res):
        """지나간 자리에 남는 작은 방울들: (경로 인덱스, 반지름). 머리가 지나간 뒤 서서히 사라진다."""
        beads, i = [], int(rng.integers(8, 30))
        while i < len(sl["xs"]) - 2:
            beads.append((i, float(rng.uniform(0.9, 2.1)) * res, float(rng.uniform(-1.8, 1.8)) * res))
            i += int(rng.integers(14, 40))
        return beads

    def _clear_trail(self, sl):
        """방울이 지나간 자리는 김서림이 쓸려 맑아진다 (정지 지도에 한 번 기록)."""
        cv2 = self.cv2
        w = max(2, int(sl["rad"] * 1.4))
        for i in range(0, len(sl["xs"]), 2):
            cv2.circle(self.clear, (int(sl["xs"][i]), int(sl["ys"][i])), w, 1.0, -1)

    # ---------- 프레임 ----------
    def _env(self, f, ph):
        """맺히며 서서히 커졌다가(나타남) 쓸려 내려가듯 빠르게 사라지는 톱니 모양 시간 변화."""
        t = (f / self.N + ph) % 1.0
        return float(_smoothstep(0.0, 0.34, t) * (1.0 - _smoothstep(0.90, 1.0, t)))

    def _sweep_map(self, f):
        """미끄러진 방울이 지나가며 쓸어 담은 자리(정지 방울이 사라진 길). 시간이 지나면 다시 맺힌다."""
        cv2 = self.cv2
        buf = self._sweep
        buf.fill(0)
        fade = 6.0 * self.fps
        for s in self.sliders:
            t = (f - s["start"]) % s["period"]
            n = len(s["xs"])
            if t >= n + int(fade):
                continue
            head = min(t, n - 1)
            w = max(3, int(s["rad"] * 1.7))
            for i in range(0, head, 3):
                age = t - i
                if age < fade:
                    cv2.line(buf, (int(s["xs"][i]), int(s["ys"][i])),
                             (int(s["xs"][min(i + 3, head)]), int(s["ys"][min(i + 3, head)])),
                             float(1.0 - age / fade), w)
        return buf

    def apply(self, out, f):
        """out: 빗줄기까지 그려진 프레임(float). 창 영역을 유리 효과로 교체."""
        cv2 = self.cv2
        m = self.mask[..., None]
        fog = (self.fog * (1.0 - np.clip(self.clear * 1.2, 0, 1)))[..., None]
        out = out * (1 - m) + (self.base * 0.92 + out * 0.08) * m    # 창밖은 초점 밖: 흐린 배경 위주
        out = out + (self.fog_col - out) * fog                         # 결로 (지나간 자리는 맑음)
        sweep = self._sweep_map(f)
        for layer, alpha, ph in self.groups:
            a = (alpha * self._env(f, ph) * (1.0 - sweep))[..., None]
            out = out + (layer - out) * a
        for s in self.sliders:
            t = (f - s["start"]) % s["period"]
            n = len(s["xs"])
            fade = 4.0 * self.fps
            if t >= n + int(fade):
                continue
            head = min(t, n - 1)
            # 지나간 자리의 가는 물길 (3~4초에 걸쳐 옅어짐)
            for i in range(0, head, 2):
                age = t - i
                if age >= fade:
                    continue
                k = 1 - age / fade
                xa, ya = s["xs"][i], s["ys"][i]
                w_ = max(1.8, s["rad"] * 0.62)
                x0, y0, x1, y1 = int(xa - w_ - 2), int(ya - 4 * w_ - 2), int(xa + w_ + 3), int(ya + 4 * w_ + 3)
                if x0 < 0 or y0 < 0 or x1 >= self.W or y1 >= self.H:
                    continue
                yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
                dxn = np.abs(xx - xa) / w_
                mm = np.clip(1 - np.hypot((xx - xa) / w_, (yy - ya) / (4 * w_)), 0, 1) ** 0.6 * k * 0.85
                # 물길: 가장자리는 어둡고(물 막의 테두리) 가운데는 가늘게 밝은(빛을 모으는) 선
                edge = np.clip(1.0 - np.abs(dxn - 0.85) / 0.35, 0, 1)
                core = np.clip(1.0 - dxn / 0.45, 0, 1)
                lens = self.base[y0:y1, x0:x1] * (1.0 - 0.16 * edge[..., None]) * (1.0 + 0.20 * core[..., None]) \
                    + (0.045 * core)[..., None]
                region = out[y0:y1, x0:x1]
                region += (lens - region) * mm[..., None]
            # 길에 남은 작은 방울들 (머리가 지나간 뒤 나타나 천천히 사라짐)
            for (bi, brad, bx) in s["beads"]:
                if bi >= head:
                    continue
                age = t - bi
                if age >= fade * 1.4:
                    continue
                keep = 1.0 - _smoothstep(0.5, 1.0, age / (fade * 1.4))
                p = _lens(self.base, s["xs"][bi] + bx, s["ys"][bi], brad, 1.2, cv2)
                if p:
                    x0, y0, x1, y1, lens, a = p
                    region = out[y0:y1, x0:x1]
                    region += (lens - region) * (a * keep)[..., None]
            if t < n:                                       # 머리 방울: 움직일 때 위아래로 길쭉
                v = float(s["ys"][head] - s["ys"][max(0, head - 3)])
                stretch = 1.25 + float(np.clip(v * 0.25, 0, 0.8))
                p = _lens(self.base, s["xs"][head], s["ys"][head], s["rad"], stretch, cv2)
                if p:
                    x0, y0, x1, y1, lens, a = p
                    region = out[y0:y1, x0:x1]
                    region += (lens - region) * a[..., None]
        return out
