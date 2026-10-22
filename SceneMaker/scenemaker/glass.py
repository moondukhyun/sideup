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
    """한 방울의 굴절 패치 (좌표, RGB, 알파). 물방울은 작은 볼록 렌즈: 뒤 풍경이 거꾸로 작게 맺힌다.
    v11.22: 모든 방울이 똑같은 동그라미로 보이지 않게 방울마다 모양이 다르다 —
    울퉁불퉁한 윤곽, 중력 때문에 아래쪽이 불룩한 물방울꼴, 굴절 세기·테두리·반사광 위치 차이, 가끔 두 방울이 붙은 모양."""
    rs = np.random.default_rng((int(x * 7919) * 31 + int(y * 104729) + int(rad * 1009)) & 0xFFFFFFFF)   # 위치로 정해져서 프레임마다 같은 모양
    big = float(np.clip(rad / 6.0, 0.25, 1.0))                     # 작은 방울일수록 거의 동그랗다
    ext = 1.0 + 0.40 * big
    rx, ry = rad, rad * stretch
    H, W = src.shape[:2]
    x0, y0, x1, y1 = int(x - rx * ext) - 2, int(y - ry * ext) - 2, int(x + rx * ext) + 3, int(y + ry * ext) + 3
    if x0 < 0 or y0 < 0 or x1 >= W or y1 >= H or rx < 0.6:
        return None
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    ex, ey = (xx - x) / rx, (yy - y) / ry
    th = np.arctan2(ey, ex)                                        # +y = 아래쪽
    rb = np.ones_like(th)
    for k in (2, 3, 4, 5):                                         # 울퉁불퉁한 윤곽 (저차 조화 성분)
        rb += float(rs.uniform(0.0, 0.17 / (k - 0.6))) * big * np.cos(k * th + float(rs.uniform(0, 6.28)))
    drop = float(rs.uniform(0.04, 0.20)) * big                      # 물방울꼴: 아래가 불룩하고 위가 좁음
    rb *= 1.0 + drop * np.clip(np.sin(th), 0, 1) - 0.55 * drop * np.clip(-np.sin(th), 0, 1)
    rb *= 1.0 + float(rs.uniform(-0.12, 0.12)) * big * ex.clip(-1, 1)    # 한쪽으로 쏠린 모양
    r = np.sqrt(ex * ex + ey * ey) / np.maximum(rb, 0.55)
    rr = r * r
    alpha = np.clip((1 - rr) * 3.2, 0, 1)                         # 가장자리가 또렷한 방울
    k = (7.0 + rad * 0.22) * float(rs.uniform(0.7, 1.35))         # 굴절 세기도 방울마다 다름
    mx = (x - ex * rx * k).astype(np.float32)
    my = (y - ey * ry * k).astype(np.float32)
    lens = cv2.remap(src, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    lens = lens * float(rs.uniform(1.02, 1.18)) + 0.012            # 물방울은 빛을 모아 살짝 밝다
    rim = np.clip(1 - np.abs(r - 0.90) / float(rs.uniform(0.11, 0.2)), 0, 1)
    rim_w = rim * (float(rs.uniform(0.14, 0.32)) + 0.34 * (ey > 0))      # 테두리 어두운 고리 (아래쪽이 더 진함)
    lens = lens * (1.0 - rim_w[..., None])
    hx, hy = -0.32 + float(rs.uniform(-0.14, 0.14)), -0.38 + float(rs.uniform(-0.12, 0.12))
    hl = np.exp(-(((ex - hx) / float(rs.uniform(0.14, 0.26))) ** 2 + ((ey - hy) / float(rs.uniform(0.14, 0.26))) ** 2)) * 0.55   # 위쪽 큰 반사광
    hl2 = np.exp(-(((ex - 0.30) / 0.15) ** 2 + ((ey - 0.46) / 0.10) ** 2)) * 0.16     # 아래쪽 약한 반사광
    hs = float(np.clip(rad / 5.0, 0.28, 1.0)) * float(rs.uniform(0.45, 1.0))          # 반사광 세기도 제각각
    lens = lens + ((hl + hl2) * hs)[..., None]
    return x0, y0, x1, y1, lens, alpha


class GlassRain:
    GROUPS = 5

    def __init__(self, bg, mask, N, fps, amount=1.0, seed=7, view_blur=9.0, cover=1.0, n_sliders=None):
        import cv2
        self.cv2 = cv2
        self.bg, self.mask, self.N, self.fps = bg, mask, N, fps
        self.fast = n_sliders is not None                      # 폭우: 방울이 오래 매달려 있지 않고 계속 흘러내림
        self.H, self.W = bg.shape[:2]
        res = self.H / 1080.0
        self.res = res
        rng = np.random.default_rng(seed + 101)
        # 뒤 풍경은 초점 밖처럼 흐리게 (초점은 유리 위 물방울)
        wm0 = np.clip(mask, 0, 1)[..., None].astype(np.float32)
        blur = cv2.GaussianBlur(bg * wm0, (0, 0), view_blur * res) / (cv2.GaussianBlur(wm0, (0, 0), view_blur * res)[..., None] + 1e-3)   # 유리 안쪽 색끼리만 흐리게 (밝은 창틀·벽 색이 유리로 번져 들어와 창 가장자리에 뿌연 안개처럼 보이던 문제)
        blur = np.where(wm0 > 0.02, blur, bg)
        self.base = bg * (1 - mask[..., None]) + blur * mask[..., None]
        # 방울이 비추는 풍경: 창 영역의 색만 넓게 번지게 채우고(창틀·실내가 들어오지 않게) 살짝 흐리게 → 방울마다 창 모양이 똑같이 보이지 않음
        wm = np.clip(mask, 0, 1)[..., None].astype(np.float32)
        num = cv2.GaussianBlur(self.base * wm, (0, 0), 22 * res)
        den = cv2.GaussianBlur(wm, (0, 0), 22 * res)[..., None] + 1e-4
        fill = num / den
        self.lens_src = cv2.GaussianBlur(self.base * wm + fill * (1 - wm), (0, 0), 2.2 * res)

        # 결로(김서림): 아래쪽일수록 살짝 뿌옇게 — 주변 색을 밝게 끌어올린 안개. 방울이 지나간 자리는 맑아짐
        y = np.linspace(0, 1, self.H, dtype=np.float32)[:, None]
        local = cv2.GaussianBlur(self.base * wm0, (0, 0), 45 * res) / (cv2.GaussianBlur(wm0, (0, 0), 45 * res)[..., None] + 1e-3)      # 결로 색도 유리 안쪽 색만으로
        self.fog_col = np.clip(local * 1.7 + 0.04, 0, 1)
        self.fog = (np.clip((y - 0.30) / 0.70, 0, 1) ** 1.4 * 0.10 * min(1.5, amount) * mask).astype(np.float32)
        # 결로를 균일한 띠가 아니라 얼룩덜룩한 '번진 김서림'으로 (폭우일수록 진하게)
        patch_ = cv2.GaussianBlur(np.random.default_rng(seed + 55).normal(0, 1, (self.H // 8 + 2, self.W // 8 + 2)).astype(np.float32), (0, 0), 3.0)
        patch_ = cv2.resize(patch_, (self.W, self.H), interpolation=cv2.INTER_CUBIC)
        patch_ = np.clip(0.55 + 0.9 * (patch_ - patch_.mean()) / (patch_.std() + 1e-6) * 0.5, 0.05, 1.4)
        self.fog = (self.fog * (1.0 + 0.9 * min(amount, 2.0)) * patch_).astype(np.float32)
        # 유리 위를 천천히 흘러내리는 얇은 물막: 세로로 길쭉한 결이 루프 동안 정수 번 내려옴 (이음새 없음)
        Pn = max(48, int(self.H * 0.5))
        base_n = np.random.default_rng(seed + 77).normal(0, 1, (Pn, self.W // 3 + 2)).astype(np.float32)
        t3 = cv2.GaussianBlur(np.tile(base_n, (3, 1)), (0, 0), sigmaX=1.4, sigmaY=26 * res)
        sheet = t3[Pn:2 * Pn]
        sheet = cv2.resize(sheet / (float(sheet.std()) + 1e-6), (self.W, Pn), interpolation=cv2.INTER_LINEAR)
        self._sheet_P = Pn
        self._sheet = np.tile(sheet, (self.H // Pn + 3, 1)).astype(np.float32)
        self._sheet_k = max(1, int(round(0.10 * self.H * (N / float(fps)) / Pn)))      # 초당 화면 높이의 약 10% 속도
        self._sheet_amt = 0.030 * min(amount, 2.0)
        self.clear = np.zeros((self.H, self.W), np.float32)         # 쓸려 내려간 자리 (정지)
        self._sweep = np.zeros((self.H, self.W), np.float32)        # 프레임마다 쓰는 임시 지도

        # 정지 물방울: 눈에 보이는 중간·큰 방울 + 아주 작은 안개 방울, 그룹 5개 (시간차로 생겼다 사라짐)
        # 개수는 '유리 면적 중 방울이 덮는 비율'로 정한다. (실제 비 오는 창: 중간·큰 방울 약 8~12%, 안개 방울 약 3~5%)
        glass_px = float((mask > 0.5).sum())
        flat = (mask > 0.5).ravel().astype(np.float64)
        self._cdf = np.cumsum(flat / max(flat.sum(), 1.0))              # 위치 뽑기용 누적분포 (한 번만 계산)
        G = self.GROUPS
        a_amt = float(np.clip(amount, 0.5, 1.5))
        med_cov, micro_cov = 0.10 * a_amt * cover, 0.035 * a_amt * cover
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
                        rad = float(np.clip(rng.lognormal(np.log(2.9), 0.55), 1.6, 11.0)) * res          # 실제 창의 방울은 작은 것이 대부분
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
        n_slide = int(n_sliders) if n_sliders else int(np.clip(round(8 * amount), 6, 12))
        paths = sorted((self._make_path(rng, N, mask, res) for _ in range(n_slide)), key=lambda p: -p["rad"])   # 큰 방울이 먼저
        for i, sl in enumerate(paths):
            sl["start"] = int((i + float(rng.uniform(0, 0.8))) / n_slide * N) % N
            sl["n_eff"] = len(sl["xs"])                  # 다른 방울에 합쳐져 사라지는 시점 (기본: 끝까지)
            sl["merge_t"] = None                         # 다른 방울을 흡수해 커진 시점
            sl["beads"] = self._make_beads(sl, rng, res)
            self.sliders.append(sl)
        self._find_merges(N, res)
        for sl in self.sliders:
            self._clear_trail(sl)

    # ---------- 도우미 ----------
    def _put(self, layer, alpha, x, y, rad, stretch, cv2):
        p = _lens(self.lens_src, x, y, rad, stretch, cv2)
        if p is None:
            return
        x0, y0, x1, y1, lens, a = p
        a = a * self.mask[y0:y1, x0:x1]                                # 창 유리 밖(창틀·벽)에는 안 그림
        region = layer[y0:y1, x0:x1]
        region += (lens - region) * a[..., None]
        alpha[y0:y1, x0:x1] = np.maximum(alpha[y0:y1, x0:x1], a)
        if rad > 3.0 * self.res and ((int(x * 13) + int(y * 7)) % 9 == 0):          # 가끔 옆에 작은 방울이 붙어 합쳐진 모양
            ang = ((int(x) * 37 + int(y) * 11) % 628) / 100.0
            q = _lens(self.lens_src, x + np.cos(ang) * rad * 0.95, y + abs(np.sin(ang)) * rad * 0.9, rad * 0.62, stretch, cv2)
            if q:
                qx0, qy0, qx1, qy1, ql, qa = q
                qa = qa * self.mask[qy0:qy1, qx0:qx1]
                rg = layer[qy0:qy1, qx0:qx1]
                rg += (ql - rg) * qa[..., None]
                alpha[qy0:qy1, qx0:qx1] = np.maximum(alpha[qy0:qy1, qx0:qx1], qa)

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
        """멈춤-미끄러짐(stick-slip) 경로. 실제 유리처럼:
        - 큰 방울은 무거워서 오래 안 매달리고 먼저·빠르게·멀리 미끄러진다 (작은 방울은 오래 매달려 있다가 짧게)
        - 미끄러질 때마다 방향이 조금씩 바뀌고 살짝 휘어서 구불구불하다 (일직선 아님)"""
        cols = np.nonzero((mask > 0.5).any(axis=0))[0]
        x = float(rng.choice(cols)) if len(cols) else self.W / 2
        rows = np.nonzero(mask[:, int(x)] > 0.5)[0]
        top, bot = (float(rows.min()), float(rows.max())) if len(rows) else (0.0, float(self.H))
        y = top + rng.uniform(0, 0.45) * (bot - top)
        run = int(period * rng.uniform(0.55, 0.95))
        rad = float(np.clip(rng.lognormal(np.log(4.6), 0.42), 2.6, 10.0)) * res          # 크기는 제각각 (작은 방울이 더 많음)
        mass = (rad / (4.6 * res)) ** 1.15                                               # 클수록 무겁다
        fps_k = 30.0 / self.fps
        hang_lo, hang_hi = (14, 40) if self.fast else (26, 70)
        theta = float(rng.normal(0, 0.10))                                               # 진행 방향 (0 = 곧장 아래, 라디안)
        xs, ys = [], []
        while len(xs) < run and y < bot:
            for _ in range(int(rng.integers(hang_lo, hang_hi) / mass ** 1.4) + 1):       # 매달려 거의 정지 (큰 방울일수록 짧게)
                xs.append(x + float(rng.normal(0, 0.12)) * res); ys.append(y)
            theta = 0.5 * theta + float(rng.normal(0, 0.13))                             # 미끄러질 때마다 방향이 달라짐
            v0 = float(rng.uniform(4.0, 10.0)) * res * mass * fps_k                       # 큰 방울일수록 빠르게 시작
            n_slide = int(rng.integers(10, 26) * (0.65 + 0.55 * mass))                    # 큰 방울일수록 멀리
            for k in range(n_slide):
                v = v0 * (1.0 - 0.7 * k / n_slide)                                        # 점점 느려지며 멈춤
                theta += float(rng.normal(0, 0.03))                                       # 가는 동안 살짝 휘어짐
                theta = float(np.clip(theta, -0.45, 0.45))
                y += v * float(np.cos(theta))
                x += v * float(np.sin(theta)) + float(rng.normal(0, 0.25)) * res
                xs.append(x); ys.append(y)
                if y > bot:
                    break
        return {"xs": np.array(xs), "ys": np.array(ys), "period": period, "rad": rad, "mass": mass}

    def _find_merges(self, N, res):
        """흐르는 방울끼리 만나면 작은 쪽이 큰 쪽에 합쳐진다: 작은 방울은 그 자리에서 사라지고 큰 방울은 잠깐 부풀었다가 더 커진 채 흐른다."""
        S = len(self.sliders)
        pos = np.full((S, N, 2), np.nan, np.float32)
        for si, s in enumerate(self.sliders):
            for f in range(N):
                t = (f - s["start"]) % s["period"]
                if t < s["n_eff"]:
                    pos[si, f] = (s["xs"][t], s["ys"][t])
        for a in range(S):
            for b in range(a + 1, S):
                if self.sliders[a]["n_eff"] <= 0 or self.sliders[b]["n_eff"] <= 0:
                    continue
                d = np.hypot(pos[a, :, 0] - pos[b, :, 0], pos[a, :, 1] - pos[b, :, 1])
                reach = 0.9 * (self.sliders[a]["rad"] + self.sliders[b]["rad"])
                hit = np.nonzero(d < reach)[0]
                if not len(hit):
                    continue
                f = int(hit[0])
                big, small = (a, b) if self.sliders[a]["rad"] >= self.sliders[b]["rad"] else (b, a)
                sb, ss = self.sliders[big], self.sliders[small]
                if ss["merge_t"] is not None or sb["merge_t"] is not None:
                    continue
                ss["n_eff"] = int((f - ss["start"]) % ss["period"])        # 작은 방울은 여기서 사라짐
                sb["merge_t"] = int((f - sb["start"]) % sb["period"])
                sb["gain"] = 1.0 + 0.35 * ss["rad"] / sb["rad"]
                for si in (small,):
                    pos[si, :, :] = np.nan
                    for ff in range(N):
                        t = (ff - ss["start"]) % ss["period"]
                        if t < ss["n_eff"]:
                            pos[si, ff] = (ss["xs"][t], ss["ys"][t])

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
        for i in range(0, int(sl.get("n_eff", len(sl["xs"]))), 2):
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
            n = int(s.get("n_eff", len(s["xs"])))
            if t >= n + int(fade) or n <= 0:
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
        sh = int(round(self._sheet_k * self._sheet_P * (f % self.N) / self.N)) % self._sheet_P
        sheet = self._sheet[self._sheet_P - sh:self._sheet_P - sh + self.H, :self.W]
        out = out * (1.0 + (self._sheet_amt * sheet)[..., None] * m * (1.0 - np.clip(self.clear, 0, 1)[..., None] * 0.5))   # 얇은 물막이 흐르는 결
        sweep = self._sweep_map(f)
        for layer, alpha, ph in self.groups:
            a = (alpha * self._env(f, ph) * (1.0 - sweep))[..., None]
            out = out + (layer - out) * a
        for s in self.sliders:
            t = (f - s["start"]) % s["period"]
            n = len(s["xs"])
            n_eff = s.get("n_eff", n)
            fade = 4.0 * self.fps
            if t >= n + int(fade):
                continue
            head = min(t, n_eff - 1) if n_eff > 0 else 0
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
                mm = mm * self.mask[y0:y1, x0:x1]
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
                p = _lens(self.lens_src, s["xs"][bi] + bx, s["ys"][bi], brad, 1.2, cv2)
                if p:
                    x0, y0, x1, y1, lens, a = p
                    region = out[y0:y1, x0:x1]
                    region += (lens - region) * (a * keep * self.mask[y0:y1, x0:x1])[..., None]
            if t < n_eff:                                   # 머리 방울: 움직일 때 위아래로 길쭉
                v = float(s["ys"][head] - s["ys"][max(0, head - 3)])
                stretch = 1.25 + float(np.clip(v * 0.25, 0, 0.8))
                grow = 1.0 + 0.30 * head / max(n, 1)         # 흘러가며 물을 모아 점점 커짐
                mt = s.get("merge_t")
                if mt is not None and t >= mt:               # 다른 방울을 흡수: 잠깐 크게 부풀었다가 가라앉아 더 커진 채로
                    pulse = 0.22 * max(0.0, 1.0 - (t - mt) / (0.5 * self.fps)) * s.get("gain", 1.0)
                    grow *= s.get("gain", 1.0) + pulse
                    stretch += 0.25 * max(0.0, 1.0 - (t - mt) / (0.5 * self.fps))
                p = _lens(self.lens_src, s["xs"][head], s["ys"][head], s["rad"] * grow, stretch, cv2)
                if p:
                    x0, y0, x1, y1, lens, a = p
                    region = out[y0:y1, x0:x1]
                    region += (lens - region) * (a * self.mask[y0:y1, x0:x1])[..., None]
        return out


def window_mask_cool(bg, depth=None):
    """실내 장면용 창 유리 찾기 (v11.22): 창밖 = 푸르스름·무채색 / 실내 = 따뜻한 색 이라는 점을 이용한다.
    따뜻한 창틀·가로세로 격자(창살)·벽은 자동으로 빠져서 격자는 선명하게 남고, 벽·침대·천장에는 물방울이 맺히지 않는다.
    depth 가 있으면 '먼 곳'만 남긴다. 못 찾으면 None."""
    import cv2
    H, W = bg.shape[:2]
    sw = 960
    s = sw / float(W)
    sh = max(8, int(round(H * s)))
    small = cv2.resize(bg, (sw, sh), interpolation=cv2.INTER_AREA)
    r, g, b = small[..., 0], small[..., 1], small[..., 2]
    lum = small @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    warm = cv2.GaussianBlur(r - b, (0, 0), 1.2)
    bluish = cv2.GaussianBlur(b - r, (0, 0), 1.2) > 0.012                      # 어두운 밤 창은 푸르스름함 — 그림자 진 어두운 벽(무채색)은 창이 아님
    cool = ((warm < 0.055) & (lum < 0.78) & (bluish | (lum > 0.45))).astype(np.uint8)   # 푸르스름하거나 밝은 무채색 (실내 벽·나무·조명은 따뜻해서 제외)
    if depth is not None:
        d = cv2.resize(np.asarray(depth, np.float32), (sw, sh), interpolation=cv2.INTER_AREA)
        cand = cool.astype(bool)
        if cand.sum() > 0:
            far = (d < min(0.5, float(np.percentile(d[cand], 60)) + 0.05))
            if (cand & far).sum() > 0.004 * sw * sh:
                cool = (cand & far).astype(np.uint8)
    cool = cv2.morphologyEx(cool, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(cool, connectivity=4)
    keep = np.zeros((sh, sw), np.uint8)
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if a < 0.0015 * sw * sh or w < 0.03 * sw or h < 0.04 * sh:
            continue
        if a / float(w * h) < 0.55 or max(w / float(h), h / float(w)) > 6:         # 창 칸은 네모에 가깝게 꽉 찬 모양
            continue
        keep[lab == i] = 1
    if keep.sum() < 0.01 * sw * sh:
        return None
    keep = cv2.erode(keep, np.ones((3, 3), np.uint8))                              # 창틀 쪽 가장자리 여유
    m = cv2.GaussianBlur(keep.astype(np.float32), (0, 0), 1.2)
    return np.clip(cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR), 0, 1)


def window_mask_boxes(bg, boxes):
    """사용자·Claude 가 표시한 창 유리 상자(전체 해상도 픽셀)를 마스크로. 창살(가는 밝은 선)과 밝은 크림색 창틀은 빼서 선명하게 남긴다.
    색으로 자동 판별이 틀려 칸이 빠졌을 때 보정용."""
    import cv2
    H, W = bg.shape[:2]
    m = np.zeros((H, W), np.uint8)
    for x0, y0, x1, y1 in boxes:
        m[max(0, int(y0)):min(H, int(y1)), max(0, int(x0)):min(W, int(x1))] = 1
    if not m.any():
        return None
    res = H / 1080.0
    lum = bg @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    warm = bg[..., 0] - bg[..., 2]
    solid = (((lum > 0.55) & (warm > 0.04)) | (lum > 0.82)).astype(np.uint8)          # 창살·창틀: 밝고 크림색
    k = max(5, int(14 * res)) | 1
    thin = solid & ~cv2.morphologyEx(solid, cv2.MORPH_OPEN, np.ones((k, k), np.uint8)).astype(bool)   # 가는 선
    wide = cv2.morphologyEx(solid, cv2.MORPH_OPEN, np.ones((k, k), np.uint8)) & (lum > 0.72).astype(np.uint8)
    bars = cv2.dilate(np.maximum(thin, wide), np.ones((3, 3), np.uint8))
    m = (m & (1 - bars)).astype(np.uint8)
    m = cv2.erode(m, np.ones((3, 3), np.uint8))
    return np.clip(cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.2), 0, 1)
