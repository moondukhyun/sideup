"""아늑한 실내 장면 (v11.22): 촛불·벽난로 불꽃·방 안 불빛 일렁임·반려동물 숨쉬기.

모든 움직임은 루프 N 프레임 동안 '정수 번' 반복되는 신호로 만들어 이음새가 없다.

- find_lights():  그림에서 촛불 불꽃(작고 밝은 따뜻한 점)과 벽난로 불(크고 주황·노랑인 덩어리)을 찾는다
- Interior:       촛불 흔들림 + 벽난로 불꽃 일렁임·불티 + 불빛이 방 안 벽·가구·바닥에 일렁이며 닿는 효과
                  + 반려동물 숨쉬기 (위치는 pets.json 또는 --pet 로 지정)
"""

import numpy as np

LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
WARM = np.array([1.0, 0.84, 0.62], dtype=np.float32)         # 불빛이 닿은 곳의 색 변화 (빨강이 가장 크게)


# ---------------------------------------------------------------- 불빛 찾기
def find_lights(bg, max_candles=24, exclude=None, fire_box=None, candle_pts=None, big_flame=False):
    """bg: float RGB (H,W,3) 0..1.  exclude: (H,W) 0~1 — 이 영역(창문 유리 등)의 불빛은 무시.
    반환: {"candles": [{"x","y","w","h"}...], "fire": {"mask","box","cx","cy","base"} 또는 None}  (전체 해상도 좌표)

    fire_box: (x0,y0,x1,y1) 전체 해상도 픽셀 — Claude 가 알려준 벽난로 불 위치(있으면 그 안에서만 찾음). candle_pts: [(x,y)...] 촛불 불꽃 위치.
    벽난로 불 = '뜨거운 핵'(노랑·흰빛으로 아주 밝은 덩어리)가 있는 가장 큰 덩어리. 불빛 받은 러그·벽·돌은 주황이어도 핵이 없어 제외된다.
    촛불 불꽃 = 주변보다 확 튀는 작고 따뜻한 밝은 점 (top-hat)."""
    import cv2
    H, W = bg.shape[:2]
    sw = 960
    s = sw / float(W)
    sh = max(8, int(round(H * s)))
    small = cv2.resize(bg, (sw, sh), interpolation=cv2.INTER_AREA)
    lum = small @ LUMA
    r, g, b = small[..., 0], small[..., 1], small[..., 2]
    area_px = float(sw * sh)
    if big_flame:                                                     # 큰 촛불 클로즈업: 화면에서 가장 크고 밝은 따뜻한 덩어리 = 불꽃 하나
        bright = ((lum > 0.62) & ((r - b) > 0.10)).astype(np.uint8)
        bright = cv2.morphologyEx(bright, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
        n_, lab_, st_, cen_ = cv2.connectedComponentsWithStats(bright, connectivity=8)
        best, pick_ = 0.0, None
        for i in range(1, n_):
            x_, y_, w_, h_, a_ = st_[i]
            if a_ < 0.0006 * area_px or a_ > 0.30 * area_px:
                continue
            sc_ = float(lum[lab_ == i].max()) * a_ * (1.0 + 0.6 * (h_ > 1.2 * w_))      # 밝고 크고 위로 길쭉한 것(불꽃 모양) 우선
            if sc_ > best:
                best, pick_ = sc_, i
        out_ = []
        if pick_ is not None:
            x_, y_, w_, h_, a_ = st_[pick_]
            fw_ = float(np.clip(0.6 * w_, 6, 0.22 * sw))                                  # 불꽃 몸통 폭(바깥 번짐 제외)
            fh_ = float(np.clip(h_, 12, 0.60 * sh))
            out_.append({"x": (x_ + w_ / 2.0) / s, "y": (y_ + 0.55 * h_) / s, "w": max(6.0, fw_ / s), "h": max(12.0, fh_ / s)})
        return {"candles": out_, "fire": None}
    ex = None
    if exclude is not None:
        ex = cv2.resize(np.asarray(exclude, np.float32), (sw, sh), interpolation=cv2.INTER_AREA) > 0.4
        ex = cv2.dilate(ex.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0

    # ---- 벽난로 불 ----
    hint = None
    if fire_box is not None:
        hx0, hy0, hx1, hy1 = [int(v * s) for v in fire_box]
        hint = (max(0, hx0), max(0, hy0), min(sw, hx1), min(sh, hy1))
    if hint is not None:                                              # Claude 가 알려준 영역 안에서는 기준을 느슨하게
        hot = ((lum > 0.5) & (r > 0.6) & ((r - b) > 0.08)).astype(np.uint8)
        zone = np.zeros_like(hot)
        zone[hint[1]:hint[3], hint[0]:hint[2]] = 1
        hot *= zone
    else:
        hot = ((r > 0.72) & (g > 0.42) & (lum > 0.58) & ((r - b) > 0.12)).astype(np.uint8)
    if ex is not None:
        hot[ex] = 0
    hot = cv2.morphologyEx(hot, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, lab, stats, cent = cv2.connectedComponentsWithStats(hot, connectivity=8)
    fire_info = None
    fire_zone = np.zeros((sh, sw), np.uint8)
    best, pick = 0.0, None
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if a < 0.0004 * area_px or w < 0.012 * sw or h < 0.025 * sh:
            continue
        mi = (lab == i)
        if hint is None:
            # 진짜 불: 주변보다 확 밝고(어두운 벽난로 속) 흰빛 도는 뜨거운 핵이 있다. 불빛 받은 바닥·벽은 대비가 약하고 핵이 없다.
            ring = (cv2.dilate(mi.astype(np.uint8), np.ones((31, 31), np.uint8)) > 0) & ~(cv2.dilate(mi.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0)
            contrast = float(lum[mi].mean() - lum[ring].mean()) if ring.any() else 0.0
            core = int((mi & (lum > 0.82)).sum())
            if core < 20 or contrast < 0.10 or w > 3.2 * h + 8:
                continue
            score = contrast * contrast * min(a, 3000)                  # 크기보다 '주변과의 대비'를 훨씬 중요하게 (불빛 받은 바닥·창턱이 더 커도 지지 않게)
        else:
            score = float(a)
        if score > best:
            best, pick = score, i
    if pick is not None:
        x, y, w, h, a = stats[pick]
        bx0, bx1 = max(0, int(x - 0.6 * w)), min(sw, int(x + w + 0.6 * w))
        by0, by1 = max(0, int(y - 0.45 * h)), min(sh, int(y + h + 0.12 * h))
        orange = ((r > 0.45) & ((r - b) > 0.18) & (lum > 0.28)).astype(np.uint8)
        box = np.zeros_like(orange)
        box[by0:by1, bx0:bx1] = 1
        body = (orange & box)
        body = cv2.morphologyEx(body, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        n2, lab2, st2, _ = cv2.connectedComponentsWithStats(body, connectivity=8)
        core_lab = set(np.unique(lab2[lab == pick]).tolist()) - {0}
        sel = np.isin(lab2, list(core_lab)).astype(np.uint8) if core_lab else (lab == pick).astype(np.uint8)
        sel = np.maximum(sel, (lab == pick).astype(np.uint8))
        near = cv2.dilate(sel, np.ones((int(0.3 * w) | 1, int(0.3 * h) | 1), np.uint8))          # 옆에서 따로 타는 작은 불꽃도 포함 (떨어져 있어 고정돼 보이던 불꽃)
        for i2 in range(1, n2):                                                                    # 단 불빛 받은 돌벽·벽은 불꽃만큼 밝지 않으므로 제외
            mi2 = (lab2 == i2)
            if st2[i2][4] > 12 and near[mi2].any() and float(np.percentile(lum[mi2], 90)) > 0.72:
                sel = np.maximum(sel, mi2.astype(np.uint8))
        ys, xs = np.nonzero(sel)
        fire_zone = cv2.dilate(sel, np.ones((25, 25), np.uint8))
        # 불꽃 = 밝은 주황·노랑. 어둡게 이글거리는 옆 불꽃까지 포함하되(너무 높은 기준이면 그 불꽃만 고정돼 보임), 어두운 뒷벽·장작은 가중치가 낮아 거의 안 움직임
        hotness = np.clip((lum - 0.27) / 0.30, 0, 1) * np.clip((g - 0.16) / 0.22, 0, 1) * np.clip((r - b - 0.10) / 0.22, 0, 1)
        m = np.clip(cv2.GaussianBlur((cv2.dilate(sel, np.ones((5, 5), np.uint8)) * hotness).astype(np.float32), (0, 0), 1.6) * 1.1, 0, 1)
        fire_info = {
            "mask": np.clip(cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR), 0, 1),
            "box": (xs.min() / s, ys.min() / s, xs.max() / s, ys.max() / s),
            "cx": float(xs.mean()) / s, "cy": float(ys.mean()) / s, "base": float(ys.max()) / s,
        }

    # ---- 촛불 불꽃: 주황빛 밝은 덩어리(불꽃 + 불빛 받은 양초) 안에서 '가장 밝은 점' = 불꽃 심 ----
    candles = []
    if candle_pts:                                                   # Claude 가 알려준 위치 주변에서 불꽃 끝을 정확히 찾음
        for (hx, hy) in candle_pts:
            px, py = int(hx * s), int(hy * s)
            y0_, y1_, x0_, x1_ = max(0, py - 22), min(sh, py + 26), max(0, px - 15), min(sw, px + 16)
            win = lum[y0_:y1_, x0_:x1_]
            if win.size == 0:
                continue
            mx = float(win.max())
            if mx < 0.6:
                continue
            ys_, xs_ = np.nonzero(win >= max(0.62, 0.86 * mx))
            tip = int(ys_.min())
            rows = xs_[ys_ <= tip + 3]
            fw = float(min(max(rows.max() - rows.min() + 1, 3), 11))
            fh = float(min(max(2.4 * fw, 8), 24))
            xt = x0_ + float(rows.mean())
            candles.append((mx * 60.0, xt - fw / 2.0, y0_ + tip + 0.2 * fh, fw, fh))
    sm_lum = cv2.GaussianBlur(lum, (0, 0), 1.2)
    for thr, redness, peak_min in ((0.70, 0.22, 0.88), (0.62, 0.18, 0.80)):
        if candles or candle_pts:
            break                                      # 또렷한 불꽃을 찾았으면 느슨한 기준은 쓰지 않음
        seed = ((lum > thr) & ((r - b) > redness)).astype(np.uint8)
        seed[fire_zone > 0] = 0
        if ex is not None:
            seed[ex] = 0
        seed = cv2.dilate(seed, np.ones((7, 7), np.uint8))           # 불꽃 심은 거의 흰색이라 주황 테두리까지 포함해 한 덩어리로
        n, lab, stats, cent = cv2.connectedComponentsWithStats(seed, connectivity=8)
        # 불꽃 끝(밝은 곳의 맨 위)을 세로줄마다 찾고, 그 윤곽에서 '뾰족하게 솟은 곳'마다 불꽃 하나
        bright = (sm_lum >= peak_min - 0.03) & (seed > 0)
        has = bright.any(0)
        top = np.where(has, bright.argmax(0), sh).astype(np.int32)
        k_ = 7
        tips = []
        for xc in range(k_, sw - k_):
            if top[xc] >= sh:
                continue
            win_ = top[xc - k_:xc + k_ + 1]
            if top[xc] <= win_.min() and (win_ > top[xc]).any():
                if not tips or xc - tips[-1][0] > k_:
                    tips.append((xc, int(top[xc])))
                elif top[xc] < tips[-1][1]:
                    tips[-1] = (xc, int(top[xc]))
        for xt, yt in tips:
            blob_id = int(lab[min(sh - 1, yt + 2), xt])
            if blob_id == 0:
                continue
            x, y, w, h, a = stats[blob_id]
            if a < 6 or a > 0.02 * area_px or w > 0.12 * sw:
                continue                               # 너무 작은 점·너무 큰 덩어리(벽·창)는 제외
            row = bright[min(sh - 1, yt + 3), max(0, xt - 14):xt + 15]
            fw = float(row.sum())
            if fw > 13:                                # 위가 넓적하게 밝으면 램프 갓·반사광이지 불꽃이 아님
                continue
            fw = float(min(max(fw, 3), 11))
            fh = float(min(max(2.4 * fw, 8), 24))
            peak = float(sm_lum[yt:yt + 6, max(0, xt - 3):xt + 4].max())
            candles.append((peak * min(a, 120), xt - fw / 2.0, yt + 0.2 * fh, fw, fh))
    # 같은 세로줄에 겹쳐 잡힌 것 = 불꽃 + 그 아래 밝게 비친 양초 몸통 → 위쪽(불꽃)만 남김
    keep = []
    for c in candles:
        _, x, y, w, h = c
        dup = False
        for d in candles:
            if d is c:
                continue
            _, x2, y2, w2, h2 = d
            if abs((x + w / 2.0) - (x2 + w2 / 2.0)) < 1.6 * max(w, w2) + 2 and 0 < (y - y2) < 10 * max(h, h2):
                dup = True
                break
        if not dup:
            keep.append(c)
    keep.sort(reverse=True)
    out = []
    for _, x, y, w, h in keep[:max_candles]:
        out.append({"x": (x + w / 2.0) / s, "y": (y + h / 2.0) / s, "w": max(3.0, w / s), "h": max(5.0, h / s)})
    return {"candles": out, "fire": fire_info}


def _signal(rng, N, lo, hi, n_terms=5):
    """주기가 루프 길이의 약수인 사인파 합 (평균 0, 표준편차 1). lo~hi = 루프당 반복 횟수 범위."""
    hi = max(lo + 1, min(hi, int(N * 0.42)))
    freqs = rng.integers(lo, hi + 1, n_terms)
    amps = 1.0 / (freqs.astype(np.float64) ** 0.55)
    t = np.arange(N) / float(N)
    sig = np.zeros(N)
    for k, a in zip(freqs, amps):
        sig += a * np.cos(2 * np.pi * (k * t + rng.random()))
    sig -= sig.mean()
    sig /= (sig.std() + 1e-9)
    return sig.astype(np.float32)


def _sig_hz(rng, N, fps, lo_hz, hi_hz, n_terms=5):
    """초당 lo_hz~hi_hz 번 정도로 변하는 신호 (루프 안에서 정수 번 반복 → 이음새 없음). 평균 0, 표준편차 1."""
    sec = N / float(fps)
    lo = max(1, int(round(lo_hz * sec)))
    hi = max(lo + 1, int(round(hi_hz * sec)))
    return _signal(rng, N, lo, hi, n_terms)


def _periodic_noise(rng, P, w, sy, sx, cv2):
    """세로 방향으로 이음새 없이 이어지는 무늬 (P x w), 표준편차 1."""
    base = rng.normal(0, 1, (P, w)).astype(np.float32)
    t3 = cv2.GaussianBlur(np.tile(base, (3, 1)), (0, 0), sigmaX=max(0.3, sx), sigmaY=max(0.3, sy))
    out = t3[P:2 * P]
    return out / (float(out.std()) + 1e-6)


def _smooth(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- 렌더러
class Interior:
    def __init__(self, bg, N, fps, strength=1.0, fire_strength=1.0, pets=None, seed=7, info=None, fire_speed=0.45):
        import cv2
        self.cv2 = cv2
        H, W = bg.shape[:2]
        self.H, self.W, self.N, self.fps = H, W, N, fps
        self.res = H / 1080.0
        self.strength = float(strength)
        self.fire_strength = float(fire_strength)
        self.procedural = True                     # False 면 불꽃·촛불 모양 움직임은 Wan 이 만들므로 방 안 불빛 일렁임만 담당
        self.wan_mix = 0.0                         # >0 이면 Wan 이 만든 불꽃·촛불 위에 수식 일렁임을 이 비율만큼 덧입힘 (Wan 이 거의 안 움직인 불꽃·촛불도 살아 움직이게)
        rng = np.random.default_rng(seed + 811)
        self.rng = rng
        info = info if info is not None else find_lights(bg)
        self.info = info
        self.bg0 = bg
        self.candles = info["candles"]
        self.fire = info["fire"]
        res = self.res
        sec = N / float(fps)

        # ----- 불빛이 방 안에 닿는 효과 (낮은 해상도 곱셈 지도) -----
        self.lw, self.lh = max(48, W // 10), max(27, H // 10)
        yy, xx = np.mgrid[0:self.lh, 0:self.lw].astype(np.float32)
        maps, sigs = [], []
        shared = _sig_hz(rng, N, fps, 0.06, 0.30, 3)                # 방 안 공기 흐름: 촛불이 다 같이 아주 천천히 흔들림
        nc = max(1, len(self.candles))
        self.candle_sigs = []
        for c in self.candles:
            own = _sig_hz(rng, N, fps, 0.25, 1.6, 6)                # 촛불 밝기: 초당 한두 번 정도로 느긋하게
            sig = 0.78 * own + 0.45 * shared
            sig /= (sig.std() + 1e-6)
            self.candle_sigs.append(sig)
            cx, cy = c["x"] / W * self.lw, c["y"] / H * self.lh
            sx = (0.15 if nc <= 2 else 0.10) * self.lw * (1.0 + 0.15 * min(c["h"] / (0.05 * H), 3))
            sy = sx * 0.85
            amp = (0.045 if nc <= 2 else 0.030 if nc <= 6 else 0.022) * self.strength       # 촛불 불빛 일렁임: 방 전체가 어두워졌다 밝아지지 않게 아주 작게
            maps.append(amp * np.exp(-(((xx - cx) / sx) ** 2 + ((yy - cy) / sy) ** 2) / 2.0))
            sigs.append(sig)
        self.fire_sig = None
        if self.fire is not None:
            fs = 0.8 * _sig_hz(rng, N, fps, 0.12, 1.3 * fire_speed / 0.6, 7) + 0.4 * shared      # 장작불: 천천히 크게 일렁이다 가라앉음
            fs /= (fs.std() + 1e-6)
            self.fire_sig = fs
            cx, cy = self.fire["cx"] / W * self.lw, self.fire["cy"] / H * self.lh
            sx, sy = 0.26 * self.lw, 0.22 * self.lh
            fa = 0.065 * self.fire_strength                                              # 벽난로 불빛 일렁임 (실제 벽에 비친 불빛은 몇 % 수준)
            maps.append(fa * np.exp(-(((xx - cx) / sx) ** 2 + ((yy - cy) / sy) ** 2) / 2.0))
            sigs.append(fs)
            floor_y = min(self.fire["base"] / H * self.lh + 0.16 * self.lh, self.lh - 1)          # 앞 바닥·러그에 퍼지는 불빛
            maps.append(0.035 * self.fire_strength * np.exp(-(((xx - cx) / (0.34 * self.lw)) ** 2 +
                                                           ((yy - floor_y) / (0.12 * self.lh)) ** 2) / 2.0))
            sigs.append(fs)
        self.light_maps = np.stack(maps).astype(np.float32) if maps else None
        self.light_sigs = np.stack(sigs).astype(np.float32) if sigs else None

        # ----- 촛불 불꽃 (흔들림 + 밝기) -----
        self.flames = []
        for i, c in enumerate(self.candles):
            fh, fw = c["h"], c["w"]
            half_w = int(max(26 * res, 6.0 * fw))
            up, dn = int(max(34 * res, 3.2 * fh)), int(max(14 * res, 1.4 * fh))
            x0, x1 = max(0, int(c["x"] - half_w)), min(W, int(c["x"] + half_w))
            y0, y1 = max(0, int(c["y"] - up)), min(H, int(c["y"] + dn))
            if x1 - x0 < 6 or y1 - y0 < 6:
                continue
            yy_, xx_ = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            edge = _smooth(np.minimum(np.minimum(xx_ - x0, x1 - 1 - xx_), np.minimum(yy_ - y0, y1 - 1 - yy_)) / max(4.0, 0.22 * min(x1 - x0, y1 - y0)))
            base_y = c["y"] + 0.45 * fh                                                    # 불꽃 맨 아래 (이 아래의 심지·양초 몸통은 절대 안 움직임)
            win = (np.exp(-((xx_ - c["x"]) / (0.8 * fw + 1.5 * res)) ** 2)
                   * _smooth((base_y - yy_) / (0.35 * fh + 1.0)) * _smooth((yy_ - (c["y"] - 1.7 * fh)) / (0.5 * fh + 1.0)))
            win = win * edge                                                              # 조각 가장자리에서 변형 0 → 네모 경계가 안 보임
            above = np.clip((base_y - yy_) / max(fh, 4.0), 0, 1.2) ** 1.4                 # 불꽃 끝으로 갈수록 더 흔들림
            core = np.exp(-(((xx_ - c["x"]) / (0.9 * fw + 2)) ** 2 + ((yy_ - c["y"]) / (0.7 * fh + 2)) ** 2)) * edge
            halo = np.exp(-(((xx_ - c["x"]) / (2.0 * fw + 5 * res)) ** 2 + ((yy_ - c["y"]) / (1.7 * fh + 5 * res)) ** 2) / 2) * edge
            sway = 0.80 * _sig_hz(rng, N, fps, 0.15, 0.9, 4) + 0.45 * shared
            sway /= (sway.std() + 1e-6)
            sway = 1.6 * np.tanh(sway / 1.6)                                               # 가끔 크게 휘어도 한계가 있음
            self.flames.append({
                "idx": i, "box": (x0, y0, x1, y1), "win": win.astype(np.float32), "above2": above.astype(np.float32),
                "core": core.astype(np.float32), "halo": halo.astype(np.float32),
                "amp": (0.11 * fw + 0.9 * res) * (2.4 if fh > 70 * res else 1.0) * self.strength,      # 화면 가득한 큰 불꽃은 크기에 맞게 더 크게 일렁임
                "sway": sway, "sig": self.candle_sigs[i],
                "xx": xx_ - x0, "yy": yy_ - y0,
            })

        # ----- 벽난로 불꽃 -----
        self.fx = None
        if self.fire is not None:
            bx0, by0, bx1, by1 = self.fire["box"]
            pad = int(26 * res)
            fx0, fy0 = max(0, int(bx0) - pad), max(0, int(by0 - 0.42 * (by1 - by0)) - pad)
            fx1, fy1 = min(W, int(bx1) + pad), min(H, int(by1) + pad // 2)
            bh, bw = fy1 - fy0, fx1 - fx0
            if bh > 16 and bw > 16:
                P = max(48, bh)
                self.fP = P
                self.fk = max(1, int(round(0.75 * fire_speed * bh * sec / P)))   # 초당 불꽃 높이의 약 0.34배 속도 (fire_speed 0.45 기준, 빠르면 출렁이는 물결처럼 보임)
                self.fn1 = _periodic_noise(rng, P, bw, 34 * res, 4.5 * res, cv2)       # 세로로 길쭉한 결 → 불꽃 혀가 기둥처럼 좌우로 흔들림 (물결처럼 보이지 않게)
                self.fn2 = _periodic_noise(rng, P, bw, 14 * res, 2.5 * res, cv2)
                self.fn3 = _periodic_noise(rng, P, bw, 30 * res, 14 * res, cv2)
                reps = (bh + 2 * P) // P + 2
                self.fn1, self.fn2, self.fn3 = [np.tile(a, (reps, 1)) for a in (self.fn1, self.fn2, self.fn3)]
                m = self.fire["mask"][fy0:fy1, fx0:fx1]
                yy_, xx_ = np.mgrid[0:bh, 0:bw].astype(np.float32)
                topw = _smooth((self.fire["base"] - fy0 - yy_) / max(1.0, (self.fire["base"] - by0) * 0.9))   # 위로 갈수록 크게 일렁
                self.fx = {"box": (fx0, fy0, fx1, fy1), "mask": m[..., None].astype(np.float32), "topw": topw.astype(np.float32),
                           "ax": (0.028 * bw + 2.5 * res), "bh": bh, "bw": bw,
                           "X": xx_, "Y": yy_, "src": bg[fy0:fy1, fx0:fx1].copy()}
                self.ember = self._make_embers(rng, bw, bh, fx0, fy0)

    # ------------------------------------------------------------ 불티
    def _make_embers(self, rng, bw, bh, fx0, fy0):
        n = 0                                                    # 불티(떠오르는 점)는 방울처럼 보여서 뺌 — AI 움직임(Wan)을 쓰면 AI 가 불티까지 만듦
        bx0, by0, bx1, by1 = self.fire["box"]
        em = []
        for _ in range(n):
            em.append({
                "x0": float(rng.uniform(bx0 + 0.12 * (bx1 - bx0), bx1 - 0.12 * (bx1 - bx0))),
                "y0": float(self.fire["base"] - rng.uniform(0.0, 0.5) * (by1 - by0)),
                "rise": float((1.0 + rng.uniform(0.0, 1.6)) * (by1 - by0)),
                "c": int(rng.integers(1, 4)), "ph": float(rng.random()),
                "sway": float(rng.uniform(5, 26) * self.res), "sc": int(rng.integers(1, 4)), "sp": float(rng.random()),
                "size": float(rng.uniform(1.0, 2.4) * self.res + 0.4), "br": float(rng.uniform(0.55, 1.0)),
            })
        return em

    def _draw_embers(self, out, f):
        H, W = self.H, self.W
        for e in self.ember:
            t = (e["c"] * f / self.N + e["ph"]) % 1.0
            x = e["x0"] + e["sway"] * np.sin(2 * np.pi * (e["sc"] * f / self.N + e["sp"])) * t + 0.12 * e["sway"] * t * 8
            y = e["y0"] - e["rise"] * t
            a = (np.sin(np.pi * t) ** 0.8) * e["br"] * (0.7 + 0.3 * np.sin(2 * np.pi * (5 * f / self.N + e["sp"])))
            r = e["size"] * (1.0 - 0.35 * t)
            R = int(r * 3) + 2
            xi, yi = int(round(x)), int(round(y))
            x0, x1, y0, y1 = max(0, xi - R), min(W, xi + R + 1), max(0, yi - R), min(H, yi + R + 1)
            if x1 <= x0 or y1 <= y0 or a <= 0.02:
                continue
            gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            spot = np.exp(-((gx - x) ** 2 + (gy - y) ** 2) / (2 * r * r))[..., None]
            out[y0:y1, x0:x1] += spot * (a * 1.15) * np.array([1.0, 0.52, 0.14], np.float32)

    # ------------------------------------------------------------ 한 프레임
    def apply(self, out, f):
        """out: float RGB (H,W,3) 0..1 (이미 배경 움직임이 들어간 프레임) → 제자리 수정 후 반환."""
        cv2 = self.cv2
        f %= self.N
        st = self.strength
        # 1) 벽난로 불꽃 일렁임
        if self.fx is not None and (self.procedural or self.wan_mix > 0):
            fx = self.fx
            mix = 1.0 if self.procedural else self.wan_mix
            x0, y0, x1, y1 = fx["box"]
            P, k = self.fP, self.fk
            shift = int(round(k * P * f / self.N)) % P
            rows = slice(shift, shift + fx["bh"])                  # 무늬가 '위로' 올라감 (이전에는 아래로 흘러내려 불꽃이 부자연스러웠음)
            shift2 = int(round(2 * k * P * f / self.N)) % P                      # 잔불꽃은 두 배 빠르게 (정수 배 → 루프 이음새 없음)
            n1, n3 = self.fn1[rows], self.fn3[rows]
            n2 = self.fn2[shift2:shift2 + fx["bh"]]
            fs = float(self.fire_sig[f])
            ax = fx["ax"] * (1.0 + 0.12 * fs) * self.fire_strength * mix
            tw = fx["topw"]
            lean = 0.45 * ax * fs * tw ** 1.5                                                   # 바람 따라 불꽃 전체가 천천히 한쪽으로 휘었다 돌아옴
            dx = (0.65 * n1 + 0.35 * n2) * ax * tw + lean
            dy = (0.55 * n3 + 0.30 * n2) * ax * 0.9 * tw                                        # 불꽃 혀가 위로 늘어났다 줄어듦 (제자리에서 흔들리기만 하면 어색)
            src = fx["src"] if self.procedural else np.ascontiguousarray(out[y0:y1, x0:x1])     # Wan 사용 시: Wan 이 만든 현재 화면을 흔듦
            warped = cv2.remap(src, (fx["X"] + dx).astype(np.float32), (fx["Y"] + dy).astype(np.float32),
                               cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            m = fx["mask"]
            dg = (0.09 * n3[..., None] + 0.07 * n2[..., None] * tw[..., None] + 0.05 * fs) * self.fire_strength * mix      # 불꽃 밝기가 천천히 오르내림 + 끝부분은 빠르게 깜빡
            flame = np.clip(warped * (1.0 + dg * np.array([1.0, 0.80, 0.45], np.float32)), 0, 1)   # 밝아져도 푸르스름해지지 않게 따뜻한 색 쪽으로만
            reg = out[y0:y1, x0:x1]
            reg[...] = reg * (1 - m) + flame * m
            self._draw_embers(out, f)
        # 2) 촛불 불꽃 흔들림 + 번쩍임
        for c in (self.flames if (self.procedural or self.wan_mix > 0) else ()):
            x0, y0, x1, y1 = c["box"]
            reg = out[y0:y1, x0:x1]
            s = float(c["sway"][f])
            dx = s * c["amp"] * c["above2"] * (1.0 if self.procedural else self.wan_mix)
            warped = cv2.remap(reg, (c["xx"] + dx).astype(np.float32), c["yy"].astype(np.float32), cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_REPLICATE)
            w = c["win"][..., None]
            reg[...] = reg * (1 - w) + warped * w
            b = float(c["sig"][f])
            reg += (c["core"][..., None] * (0.05 * b * st * (1.0 if self.procedural else self.wan_mix)) + c["halo"][..., None] * (0.035 * b * st * (1.0 if self.procedural else self.wan_mix))) * WARM
        # 3) 불빛이 방 안에 일렁이며 닿는 효과 (곱셈 → 질감은 그대로, 밝기만 변함)
        if self.light_maps is not None:
            lo = np.tensordot(self.light_sigs[:, f], self.light_maps, axes=(0, 0))
            lo = 0.055 * np.tanh(lo / 0.055)                        # 방 전체 밝기 변화는 최대 약 ±5% 로 제한 (어두워졌다 밝아졌다 하지 않게)
            L = cv2.resize(lo, (self.W, self.H), interpolation=cv2.INTER_LINEAR)
            out *= 1.0 + L[..., None] * WARM
        return out

    def set_signals(self, fire=None, candles=None):
        """방 안 불빛 일렁임을 다른 신호(예: Wan 영상 속 불꽃의 실제 밝기 변화)로 바꾼다. candles: {후보 번호: 신호}."""
        if candles:
            for i, s in candles.items():
                if 0 <= i < len(self.candle_sigs):
                    self.candle_sigs[i] = np.asarray(s, np.float32)
        if fire is not None and self.fire is not None:
            self.fire_sig = np.asarray(fire, np.float32)
        sigs = list(self.candle_sigs) + ([self.fire_sig, self.fire_sig] if self.fire is not None else [])
        if sigs:
            self.light_sigs = np.stack(sigs).astype(np.float32)

    def describe(self):
        lines = []
        if self.fire is not None:
            bx0, by0, bx1, by1 = self.fire["box"]
            lines.append(f"벽난로 불: 화면의 {((bx1 - bx0) * (by1 - by0)) / (self.W * self.H):.1%} 영역을 타오르게 + 불티 {len(self.ember) if self.fx else 0}개")
        if self.flames:
            lines.append(f"촛불: {len(self.flames)}개의 불꽃을 흔들리게 (방 안 불빛도 같이 일렁임)")
        return lines


# ---------------------------------------------------------------- 반려동물 숨쉬기
def poly_mask(poly, box, W, H, feather=2.0):
    """다각형(0~1 비율 점들)을 box(픽셀 x0,y0,x1,y1) 크기의 0~1 마스크로. 가장자리는 feather 픽셀만큼 부드럽게."""
    import cv2
    x0, y0, x1, y1 = box
    m = np.zeros((y1 - y0, x1 - x0), np.uint8)
    pts = np.array([[p[0] * W - x0, p[1] * H - y0] for p in poly], np.int32)
    cv2.fillPoly(m, [pts], 1)
    m = m.astype(np.float32)
    return cv2.GaussianBlur(m, (0, 0), feather) if feather > 0 else m


class PetBreath:
    """pets: [{"x0","y0","x1","y1" (0~1 비율), "kind": "dog"|"cat"}].
    상자 안의 몸을 '바닥 쪽을 고정하고 위로 아주 조금 늘렸다 줄이는' 방식으로 숨쉬게 한다.
    상자 가장자리에서는 변형이 0 이 되므로 경계선이 보이지 않는다."""

    def __init__(self, pets, W, H, N, fps, seed=7):
        import cv2
        self.cv2 = cv2
        self.W, self.H, self.N = W, H, N
        self.items = []
        rng = np.random.default_rng(seed + 977)
        sec = N / float(fps)
        for p in pets:
            if p.get("kind", "dog") not in ("dog", "cat"):
                continue
            x0, y0 = int(max(0, min(1, p["x0"])) * W), int(max(0, min(1, p["y0"])) * H)
            x1, y1 = int(max(0, min(1, p["x1"])) * W), int(max(0, min(1, p["y1"])) * H)
            if x1 - x0 < 24 or y1 - y0 < 16:
                continue
            kind = p.get("kind", "dog")
            period = 4.2 if kind == "dog" else 3.0                    # 자는 개 ≈ 호흡 14/분, 고양이 ≈ 20/분
            cycles = max(1, int(round(sec / period)))
            amp = (0.024 if kind == "dog" else 0.020) * float(p.get("amount", 1.0))      # 잠든 개·고양이의 갈비뼈·배가 눈에 보일 만큼 오르내림
            yy, xx = np.mgrid[0:y1 - y0, 0:x1 - x0].astype(np.float32)
            bw, bh = x1 - x0, y1 - y0
            wx = _smooth(np.minimum(xx, bw - 1 - xx) / (0.20 * bw))
            edge = _smooth(np.minimum(yy, bh - 1 - yy) / (0.12 * bh))
            yb = bh - 1.0
            pmask = poly_mask(p["poly"], (x0, y0, x1, y1), W, H, feather=max(2.0, 0.03 * bw)) if p.get("poly") else None
            if pmask is not None and pmask.sum() > 50:                    # 몸 윤곽의 무게중심 = 배 위치
                tot = float(pmask.sum())
                cxb, cyb = float((pmask * xx).sum() / tot), float((pmask * yy).sum() / tot)
            else:
                cxb, cyb = bw * 0.5, bh * 0.58
            # 배(몸통 가운데)만 부풀었다 가라앉는 국소 변형: 머리·다리·꼬리·바닥은 거의 안 움직임
            g = np.exp(-(((xx - cxb) / (0.26 * bw)) ** 2 + ((yy - cyb) / (0.24 * bh)) ** 2))
            wgt = (g * wx * edge).astype(np.float32)
            if pmask is not None:                                          # 직접 그린 윤곽 안쪽만
                wgt = wgt * pmask
            self.items.append({
                "box": (x0, y0, x1, y1), "X": xx, "Y": yy, "w": wgt, "yb": yb, "bh": float(bh), "xc": cxb,
                "cycles": cycles, "amp": amp, "ph": float(rng.random()), "kind": kind,
                "deep": max(1, int(round(sec / 13.0))), "ph2": float(rng.random()),
            })

    def apply(self, out, f):
        cv2 = self.cv2
        for it in self.items:
            th = 2 * np.pi * (it["cycles"] * f / self.N + it["ph"])
            b = np.sin(th) + 0.25 * np.sin(2 * th + 0.7)              # 들이쉼은 길고 내쉼은 짧게
            x0, y0, x1, y1 = it["box"]
            reg = out[y0:y1, x0:x1]
            deep = 1.0 + 0.30 * np.sin(2 * np.pi * (it["deep"] * f / self.N + it["ph2"]))     # 가끔 한 번씩 더 깊게 숨을 쉼
            a = it["amp"] * b * deep
            dy = a * it["bh"] * it["w"]                               # 배 부분이 위로 살짝 부풀어 오름
            dx = (it["X"] - it["xc"]) * a * 0.45 * it["w"]            # 옆으로도 아주 조금 퍼짐
            warped = cv2.remap(reg, (it["X"] + dx).astype(np.float32), (it["Y"] + dy).astype(np.float32),
                               cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            reg[...] = warped
        return out


# ---------------------------------------------------------------- 천장 선풍기 회전
class FanSpin:
    """fans: [{"x0","y0","x1","y1" (0~1 비율), "kind": "fan"}]. 상자 안에 꼭 맞는 타원(아래에서 올려다본 날개)을
    천천히 돌린다. 한 루프에 정수 바퀴 → 이음새 없음. 가운데 몸통은 고정하고 날개 부분만 돌며 살짝 흐려진다."""

    def __init__(self, fans, W, H, N, fps, rps=0.5, seed=7):
        import cv2
        self.cv2 = cv2
        self.N = N
        sec = N / float(fps)
        self.k = max(1, int(round(rps * sec)))                       # 루프당 바퀴 수 (초당 약 0.5바퀴 = 느릿한 선풍기)
        self.items = []
        for p in fans:
            x0, y0 = int(max(0, min(1, p["x0"])) * W), int(max(0, min(1, p["y0"])) * H)
            x1, y1 = int(max(0, min(1, p["x1"])) * W), int(max(0, min(1, p["y1"])) * H)
            if x1 - x0 < 12 or y1 - y0 < 6:
                continue
            cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
            a, b = (x1 - x0) / 2.0, (y1 - y0) / 2.0
            pad = 3
            rx0, ry0, rx1, ry1 = max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad), min(H, y1 + pad)
            yy, xx = np.mgrid[ry0:ry1, rx0:rx1].astype(np.float32)
            u, v = (xx - cx) / a, (yy - cy) / b
            r = np.sqrt(u * u + v * v)
            w = _smooth((1.02 - r) / 0.22) * _smooth((r - 0.05) / 0.08)    # 바깥 가장자리·가운데 몸통에서는 변형 0
            if p.get("poly"):
                w = w * poly_mask(p["poly"], (rx0, ry0, rx1, ry1), W, H, feather=2.0)
            self.items.append({"box": (rx0, ry0, rx1, ry1), "u": u, "v": v, "cx": cx, "cy": cy, "a": a, "b": b,
                               "w": w[..., None].astype(np.float32), "xx": xx, "yy": yy})

    def apply(self, out, f):
        cv2 = self.cv2
        th = 2 * np.pi * self.k * (f % self.N) / self.N
        blur = np.radians(np.array([-5.0, -2.5, 0.0, 2.5, 5.0]))
        for it in self.items:
            x0, y0, x1, y1 = it["box"]
            reg = out[y0:y1, x0:x1]
            acc = np.zeros_like(reg)
            for d in blur:
                c, s = np.cos(th + d), np.sin(th + d)
                us = it["u"] * c + it["v"] * s
                vs = -it["u"] * s + it["v"] * c
                acc += cv2.remap(reg, (it["cx"] + it["a"] * us - x0).astype(np.float32),
                                 (it["cy"] + it["b"] * vs - y0).astype(np.float32), cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_REPLICATE)
            reg[...] = reg * (1 - it["w"]) + (acc / len(blur)) * it["w"]
        return out


# ---------------------------------------------------------------- 커피잔·찻잔·주전자 김
def _torus_noise(rng, P, Q, sy, sx, cv2):
    """가로·세로 모두 이음새 없이 이어지는 무늬 (P x Q), 평균 0 · 표준편차 1."""
    base = rng.normal(0, 1, (P, Q)).astype(np.float32)
    t = cv2.GaussianBlur(np.tile(base, (3, 3)), (0, 0), sigmaX=max(0.3, sx), sigmaY=max(0.3, sy))
    out = t[P:2 * P, Q:2 * Q]
    return (out - out.mean()) / (float(out.std()) + 1e-6)


class Steam:
    """steams: [{"x0","y0","x1","y1" (0~1 비율), "kind": "steam"}] — 컵 입구·주전자 주둥이를 감싼 작은 상자.
    상자 위쪽 가운데에서 김이 천천히 피어올라 구불구불 퍼지며 사라진다.
    루프 이음새가 없게 하는 원리: 김 무늬는 아주 긴 무늬를 정확히 정수 칸(k)만큼 올려 보내고,
    좌우 굽이침·무늬 변화는 모두 정수 번 반복하는 사인파라서 마지막 프레임 다음이 첫 프레임과 완전히 같다.
    clean=True 면 그림에 이미 그려져 있던 (멈춰 있는) 김 자국을 지우고 그 자리에 움직이는 김을 그린다."""

    def __init__(self, steams, W, H, N, fps, seed=7, amount=1.0, bg=None, clean=True, speed=1.0):
        import cv2
        self.cv2 = cv2
        self.N = N
        self.W, self.H = W, H
        sec = N / float(fps)
        self.items = []
        for i, p in enumerate(steams):
            x0, y0 = max(0.0, min(1.0, p["x0"])) * W, max(0.0, min(1.0, p["y0"])) * H
            x1, y1 = max(0.0, min(1.0, p["x1"])) * W, max(0.0, min(1.0, p["y1"])) * H
            bw = max(10.0, x1 - x0)
            rng = np.random.RandomState((seed * 131 + i * 17) % (2 ** 31 - 1))
            bw = min(bw, 0.05 * W)                                       # 상자를 크게 그려도 김 폭은 컵·주둥이 크기로 제한
            ox, oy = (x0 + x1) / 2.0, y0 + 0.2 * (y1 - y0)               # 김이 나오는 점: 상자 위쪽 가운데 (주둥이·컵 입구)
            hp = float(np.clip(max(0.11 * H, 4.0 * bw), 0.09 * H, 0.24 * H)) * (0.8 + 0.4 * amount)   # 김이 올라가는 높이(px)
            hw0 = 0.5 * bw                                               # 처음 폭의 절반
            hw1 = max(hw0 * 3.0, 0.15 * hp)                              # 맨 위에서의 폭의 절반
            lean = float(rng.choice([-1.0, 1.0]) * rng.uniform(0.25, 0.6))   # 바람에 살짝 기울어지는 방향 (정해진 한쪽)
            side = int(hw1 * 3.6 + 16)
            rx0, rx1 = int(max(0, ox - side)), int(min(W, ox + side))
            ry0, ry1 = int(max(0, oy - hp - 8)), int(min(H, oy + 6))
            if rx1 - rx0 < 8 or ry1 - ry0 < 8:
                continue
            v_px = hp / 8.0 * float(speed)                                             # 초당 올라가는 거리(px): 맨 위까지 약 11초 (천천히)
            P = int(max(2.4 * hp, 160))                                  # 무늬 세로 길이 (김 높이보다 훨씬 길어 같은 무늬가 반복돼 보이지 않음)
            k = int(round(v_px * sec / P))
            if k < 1:                                                    # 루프가 짧으면 무늬를 길게 늘려서 속도를 지킴
                k = 1
                P = int(max(P, v_px * sec))
            Q = int(max(96, side * 2.4))
            layers = []
            for sy, sx, mult in ((0.34 * hp, 0.11 * hp, 1.0), (0.17 * hp, 0.07 * hp, 1.6)):
                t1 = _torus_noise(rng, P, Q, sy, sx, cv2)
                t2 = _torus_noise(rng, P, Q, sy, sx, cv2)
                kk = max(1, int(round(k * mult))) if P > 0 else k
                layers.append({"t1": t1, "t2": t2, "w1": _torus_noise(rng, P, Q, 0.55 * hp, 0.45 * hp, cv2), "w2": _torus_noise(rng, P, Q, 0.55 * hp, 0.45 * hp, cv2), "k": kk, "off": float(rng.uniform(0, P)), "mix": int(rng.randint(1, 3)), "ph": float(rng.uniform(0, 6.28))})
            yy, xx = np.mgrid[ry0:ry1, rx0:rx1].astype(np.float32)
            hf = np.clip((oy - yy) / hp, 0.0, 1.0)                       # 0 = 입구, 1 = 맨 위
            item = {"box": (rx0, ry0, rx1, ry1), "ox": ox, "oy": oy, "hp": hp, "hw0": hw0, "hw1": hw1, "lean": lean,
                    "yy": yy, "xx": xx, "hf": hf, "P": P, "Q": Q, "layers": layers,
                    "m1": int(rng.randint(1, 3)), "m2": int(rng.randint(2, 4)), "m3": int(rng.randint(1, 3)),
                    "ph1": float(rng.uniform(0, 6.28)), "ph2": float(rng.uniform(0, 6.28)), "ph3": float(rng.uniform(0, 6.28)),
                    "amount": float(amount), "kind": p.get("kind", "steam"), "patch": None}
            if clean and bg is not None:
                item["patch"] = self._clean_patch(bg, item, y1)
            self.items.append(item)
        self.sec = sec

    def _clean_patch(self, bg, it, box_bottom):
        """그림에 이미 그려진 김(주변보다 밝고 흐릿한 줄기)을 찾아 지운 조각과 그 가중치를 만든다. 못 찾으면 None."""
        cv2 = self.cv2
        x0, y0, x1, y1 = it["box"]
        reg = np.clip(np.asarray(bg[y0:y1, x0:x1], np.float32), 0, 1)
        if reg.size == 0:
            return None
        luma = reg.mean(axis=2)
        mx, mn = reg.max(axis=2), reg.min(axis=2)
        sat = (mx - mn) / (mx + 1e-3)
        k = int(max(9, it["hw1"] * 1.2)) | 1
        opened = cv2.morphologyEx(luma, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
        top = luma - opened
        # 입구(상자) 바로 위부터 위쪽 기둥 안에서만, 주변보다 밝고 색이 옅은 부분
        hf, xx = it["hf"], it["xx"]
        col = np.exp(-(((xx - it["ox"]) / (it["hw1"] * 1.8)) ** 2))
        zone = (hf > 0.04) & (col > 0.15)
        m = ((top > 0.035) & (sat < 0.55) & zone).astype(np.uint8)
        frac = float(m.mean())
        if frac < 0.004:
            return None
        m = cv2.dilate(m, np.ones((7, 7), np.uint8))
        u8 = (reg * 255).astype(np.uint8)
        fixed = cv2.inpaint(u8, m * 255, 6, cv2.INPAINT_TELEA).astype(np.float32) / 255.0
        w = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 3.0)[..., None]
        return {"img": fixed, "w": np.clip(w * 1.4, 0, 1)}

    def apply(self, out, f):
        cv2 = self.cv2
        t = (f % self.N) / float(self.N)                                 # 0 이상 1 미만 — N 프레임 뒤에 정확히 처음으로 돌아옴
        tp = 2 * np.pi * t
        for it in self.items:
            x0, y0, x1, y1 = it["box"]
            hf, xx, yy = it["hf"], it["xx"], it["yy"]
            hw1, hp = it["hw1"], it["hp"]
            reg = out[y0:y1, x0:x1]
            if it["patch"] is not None:                                  # 멈춰 있던 김 자국을 먼저 지움
                reg[...] = reg * (1 - it["patch"]["w"]) + it["patch"]["img"] * it["patch"]["w"]
            g = hf ** 1.25                                               # 위로 갈수록 크게 굽이침
            sway = (0.55 * hw1 * np.sin(tp * it["m1"] + it["ph1"] + 2.6 * hf) + 0.35 * hw1 * np.sin(tp * it["m2"] + it["ph2"] - 4.1 * hf)) * g \
                + it["lean"] * hw1 * 1.1 * hf ** 1.6                      # 바람에 한쪽으로 기울며 올라감
            cx = it["ox"] + sway
            hw = it["hw0"] + (hw1 - it["hw0"]) * hf ** 0.7
            dx = (xx - cx) / np.maximum(hw, 1.0)
            lat = np.exp(-dx * dx * 1.2)
            env = _smooth(hf / 0.07) * (1.0 - _smooth((hf - 0.10) / 0.90)) ** 1.6      # 입구에서 서서히 생겼다가 위에서 사라짐
            wob = 0.30 * hw1 * np.sin(tp * it["m3"] + it["ph3"] + 7.0 * hf)         # 무늬 자체도 굽이쳐서 곧은 줄로 보이지 않게
            dens = np.zeros_like(hf)
            P, Q = it["P"], it["Q"]
            for ly in it["layers"]:
                s = ly["k"] * P * t + ly["off"]                          # 무늬를 정수 칸만큼 올려 보냄
                my = np.mod(yy - y0 + s, P).astype(np.float32)
                mx = np.mod((xx - cx + wob) * 0.8 + Q / 2.0, Q).astype(np.float32)
                ph = tp * ly["mix"] + ly["ph"]                           # 두 무늬를 섞는 비율도 정수 번 반복 → 김 모양이 서서히 변함
                wy = np.mod(yy - y0 + max(1, (ly["k"] + 1) // 2) * P * t + ly["off"], P).astype(np.float32)     # 소용돌이 치듯 굽이치게 하는 변위 무늬 (절반 속도로 올라감)
                wx = np.mod((xx - cx) * 0.8 + Q / 2.0, Q).astype(np.float32)
                ux = cv2.remap(ly["w1"], wx, wy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP) * (0.55 * hw1) * (0.3 + hf)
                uy = cv2.remap(ly["w2"], wx, wy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP) * (0.25 * hp) * (0.3 + hf)
                mx2 = np.mod(mx + ux * 0.8, Q).astype(np.float32)
                my2 = np.mod(my + uy, P).astype(np.float32)
                tex = np.cos(ph) * cv2.remap(ly["t1"], mx2, my2, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP) \
                    + np.sin(ph) * cv2.remap(ly["t2"], mx2, my2, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
                ribbon = np.clip(1.0 - np.abs(tex) * 1.7, 0.0, 1.0) ** 2.2                  # 0 선 근처가 가는 리본 모양 → 연기 덩어리가 아니라 가는 김 가닥
                dens += (0.65 * ribbon + 0.35 * np.clip(0.3 + 0.7 * tex, 0.0, 1.0) ** 1.5) / len(it["layers"])
            edge = _smooth(np.minimum(xx - x0, x1 - 1 - xx) / 14.0) * _smooth(np.minimum(yy - y0, y1 - 1 - yy) / 10.0)      # 잘라낸 사각형 경계가 보이지 않게
            a = np.clip(dens * lat * env * edge * 1.35 * it["amount"], 0.0, 0.5)[..., None]
            luma = reg.mean(axis=2, keepdims=True)
            glow = cv2.GaussianBlur(luma, (0, 0), max(6.0, hw1 * 0.8))
            if glow.ndim == 2:
                glow = glow[..., None]
            lit = np.clip(0.55 + 1.8 * glow, 0.0, 1.0)                   # 주변이 밝을수록 하얗게, 어두운 방에서는 은은하게
            colr = np.array([0.95, 0.93, 0.91], np.float32)[None, None, :] * lit * 0.85 + reg * 0.15
            reg[...] = reg * (1 - a) + colr * a
        return out

    def describe(self):
        return [f"김: {len(self.items)}곳에서 천천히 피어오름 (루프당 무늬 {', '.join(str(l['k']) for it in self.items for l in it['layers'])}칸 → 이음새 없음"
                + (", 그림에 있던 김 자국 지움)" if any(it["patch"] is not None for it in self.items) else ")")]


# ---------------------------------------------------------------- 턴테이블 레코드판 회전
class RecordSpin:
    """records: [{"x0","y0","x1","y1" (0~1 비율), "kind": "record"}]. 상자에 꼭 맞는 타원(비스듬히 본 LP)을 33⅓ 회전/분으로 돌린다.
    - 가운데 라벨: 실제 라벨 크기를 그림에서 찾아(색이 다른 동그라미) 그 부분만 회전 (못 찾으면 작게)
    - 바깥 홈 부분: 검은 판은 돌려도 변화가 없으므로, 판과 함께 도는 아주 옅은 홈 결·먼지 점을 얹어 '돌고 있다'는 게 보이게 함 (반사광은 제자리)
    - exclude: 톤암 등 돌리면 안 되는 상자(픽셀) 목록 — 그 부분은 그대로 둔다
    한 루프에 정수 바퀴 → 이음새 없음. 가운데 축(스핀들)은 고정."""

    def __init__(self, records, W, H, N, fps, rpm=33.33, label=None, exclude=(), seed=3, bg=None, exclude_marks=()):
        import cv2
        self.cv2 = cv2
        self.N = N
        sec = N / float(fps)
        self.k = max(1, int(round(rpm / 60.0 * sec)))
        self.rpm = self.k * 60.0 / sec
        self.items = []
        self.labels = []
        rng = np.random.default_rng(seed)
        for p in records:
            x0, y0 = int(max(0, min(1, p["x0"])) * W), int(max(0, min(1, p["y0"])) * H)
            x1, y1 = int(max(0, min(1, p["x1"])) * W), int(max(0, min(1, p["y1"])) * H)
            if x1 - x0 < 16 or y1 - y0 < 6:
                continue
            cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
            a, b = (x1 - x0) / 2.0, (y1 - y0) / 2.0
            rx0, ry0, rx1, ry1 = max(0, x0 - 3), max(0, y0 - 3), min(W, x1 + 3), min(H, y1 + 3)
            yy, xx = np.mgrid[ry0:ry1, rx0:rx1].astype(np.float32)
            u, v = (xx - cx) / a, (yy - cy) / b
            r = np.sqrt(u * u + v * v)
            exm = np.zeros((ry1 - ry0, rx1 - rx0), np.uint8)                              # 돌리면 안 되는 곳(톤암 등) 마스크: 상자 + 직접 그린 윤곽
            for ex0, ey0, ex1, ey1 in exclude:
                exm[max(0, int(ey0) - ry0):max(0, int(ey1) - ry0), max(0, int(ex0) - rx0):max(0, int(ex1) - rx0)] = 1
            for em in exclude_marks:
                if em.get("poly"):
                    cv2.fillPoly(exm, [np.array([[q[0] * W - rx0, q[1] * H - ry0] for q in em["poly"]], np.int32)], 1)
                else:
                    exm[max(0, int(em["y0"] * H) - ry0):max(0, int(em["y1"] * H) - ry0), max(0, int(em["x0"] * W) - rx0):max(0, int(em["x1"] * W) - rx0)] = 1
            exm = cv2.dilate(exm, np.ones((7, 7), np.uint8))
            if bg is None:
                lab = None
            elif label:
                lab = (cx, cy, label * a, label * b)
            else:
                lab = self._find_label(bg, (rx0, ry0, rx1, ry1), (cx, cy, a, b))
            self.labels.append(lab)
            if lab is not None:                                                           # 판의 타원을 상자 크기가 아니라 '라벨 중심 + 라벨의 원근 비율'로 다시 계산 (상자가 커도 판 밖이 번지지 않게)
                lcx0, lcy0, la0, lb0 = lab
                a2 = max(0.93 * min(lcx0 - x0, x1 - lcx0), la0 * 1.5)
                b2 = a2 * min(max(1.7 * lb0 / la0, 0.15), b / a)               # 라벨은 가장자리가 깎여 더 납작하게 측정되므로 2배 보정 (상자 비율보다는 크지 않게)
                cx, cy, a, b = lcx0, lcy0, a2, b2
                u, v = (xx - cx) / a, (yy - cy) / b
                r = np.sqrt(u * u + v * v)
            if lab is not None:
                lcx, lcy, la, lb = lab
                lu, lv = (xx - lcx) / la, (yy - lcy) / lb
                lr = np.sqrt(lu * lu + lv * lv)
            else:
                lu = lv = lr = lsrc = None
                lcx = lcy = la = lb = 1.0
            w = (_smooth((1.0 - lr) / 0.10) * _smooth((lr - 0.10) / 0.06)) if lr is not None else np.zeros_like(r)   # 라벨 안쪽만, 가운데 축은 제외
            if lr is not None:                                                         # 가운데 축(검은 막대)은 색이 없으므로 돌리지 않음
                cs = np.asarray(bg[ry0:ry1, rx0:rx1], np.float32)
                ring = (lr > 0.30) & (lr < 0.90)
                med = np.median(cs[ring], axis=0) if ring.any() else cs.reshape(-1, 3).mean(0)
                near = (np.abs(lu) < 0.13) & (lv > -1.7) & (lv < 0.45)                          # 가운데 축(작은 막대): 중심 바로 위아래의 라벨과 색이 다른 부분
                pegm = (near & (np.abs(cs - med).max(-1) > 0.10)).astype(np.uint8)
                pegm = np.maximum(cv2.dilate(pegm, np.ones((5, 5), np.uint8)), exm)               # 톤암이 라벨 위에 걸쳐 있으면 그 부분도 라벨 색으로 메운 그림을 돌림 (회전하면서 톤암이 복사되어 2개로 보이지 않게)
                w = w * (1.0 - cv2.GaussianBlur(pegm.astype(np.float32), (0, 0), 1.5))        # 축 자리는 돌리지 않고, 돌리는 그림에서는 라벨 색으로 메움
                lsrc = cv2.inpaint((np.clip(cs, 0, 1) * 255).astype(np.uint8), pegm, 5, cv2.INPAINT_TELEA).astype(np.float32) / 255.0
            labr = float(la / a) if lab is not None else 0.0
            grv = _smooth((r - labr - 0.03) / 0.05) * _smooth((0.96 - r) / 0.04)          # 바깥 홈 고리
            keep = np.ones(r.shape, np.float32)
            keep[exm > 0] = 0                                                           # 톤암 등은 돌리지 않음
            if p.get("poly"):                                                           # 직접 그린 판 윤곽 밖은 건드리지 않음
                keep = keep * poly_mask(p["poly"], (rx0, ry0, rx1, ry1), W, H, feather=0)
            keep = cv2.GaussianBlur(keep, (0, 0), 2.5)
            w = w * keep
            grv = grv * keep
            self.items.append({"box": (rx0, ry0, rx1, ry1), "u": u, "v": v, "cx": cx, "cy": cy, "a": a, "b": b,
                               "lu": lu, "lv": lv, "lc": (lcx, lcy, la, lb), "lsrc": lsrc,
                               "w": w[..., None].astype(np.float32), "g": grv.astype(np.float32),
                               "off": float(rng.uniform(0, 6.28))})

    def _find_label(self, bg, box, disc):
        """상자 안에서 '색이 있는 동그란 덩어리'(= 라벨)를 찾아 (중심x, 중심y, 가로반지름, 세로반지름) 로. 검은 판은 색이 없으므로 구분됨.
        못 찾으면 None → 라벨은 돌리지 않고 홈 결만 돌림 (엉뚱한 곳을 돌려 '작은 원반'이 생기는 것보다 안전)."""
        import cv2
        if bg is None:
            return None
        x0, y0, x1, y1 = box
        cx, cy, a, b = disc
        crop = np.asarray(bg[y0:y1, x0:x1], dtype=np.float32)
        sat = crop.max(-1) - crop.min(-1)
        lum = crop.mean(-1)
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        r = np.sqrt(((xx - cx) / a) ** 2 + ((yy - cy) / b) ** 2)
        for th in (0.30, 0.22, 0.16):                                                  # 진한 색부터 시도: 옅은 색까지 한꺼번에 잡으면 주변(톤암·나무)이 섞여 라벨이 실제보다 크게 잡힘
            m = ((sat > th) & (lum > 0.10) & (r < 0.7)).astype(np.uint8)
            m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
            n, lab, st, cen = cv2.connectedComponentsWithStats(m, connectivity=8)
            keep = np.zeros(m.shape, bool)
            cands = [i for i in range(1, n) if st[i][4] >= 8 and np.hypot((cen[i][0] + x0 - cx) / a, (cen[i][1] + y0 - cy) / b) < 0.5]
            if not cands:
                continue
            main = max(cands, key=lambda i: st[i][4])                                  # 가장 큰 색 덩어리 = 라벨 (톤암·나무 같은 옆 조각은 따로 떨어져 있어 제외)
            mx, my, mw, mh = st[main][:4]
            for i in cands:                                                            # 가운데 축에 갈라진 라벨 반쪽만 합침: 큰 덩어리 주변(25% 확장) 안에 있는 조각
                x_, y_, w_, h_ = st[i][:4]
                if x_ >= mx - 0.25 * mw and y_ >= my - 0.25 * mh and x_ + w_ <= mx + 1.25 * mw and y_ + h_ <= my + 1.25 * mh:
                    keep |= (lab == i)
            if keep.sum() < 30:
                continue
            ys, xs = np.nonzero(keep)
            lx0, lx1 = np.percentile(xs, [0.5, 99.5]) + x0
            ly0, ly1 = np.percentile(ys, [3.0, 97.0]) + y0                          # 세로는 위아래 튀는 조각(톤암 그림자 등)을 덜 받도록 안쪽 백분위
            la, lb = (lx1 - lx0) / 2.0 + 1.0, (ly1 - ly0) / 2.0 * 1.05 + 1.0
            if la > 0.5 * a or la < 0.07 * a:
                continue
            lb = float(np.clip(lb, 0.30 * la * b / a, 0.85 * la * b / a))                # 비스듬히 본 정도는 판 전체와 같아야 함 (상자 비율보다 둥글 수 없음)
            return ((lx0 + lx1) / 2.0, (ly0 + ly1) / 2.0, float(la) * 1.08, float(lb) * 1.08)   # 색이 옅은 라벨 가장자리까지 돌리도록 8% 크게
        return None

    def apply(self, out, f):
        cv2 = self.cv2
        th = -2 * np.pi * self.k * (f % self.N) / self.N                              # 위에서 볼 때 시계 방향
        c, s = np.cos(th), np.sin(th)
        for it in self.items:
            x0, y0, x1, y1 = it["box"]
            reg = out[y0:y1, x0:x1]
            us = it["u"] * c + it["v"] * s
            vs = -it["u"] * s + it["v"] * c
            if it["lu"] is not None:
                lcx, lcy, la, lb = it["lc"]
                lus = it["lu"] * c + it["lv"] * s
                lvs = -it["lu"] * s + it["lv"] * c
                warped = cv2.remap(it["lsrc"], (lcx + la * lus - x0).astype(np.float32),
                                   (lcy + lb * lvs - y0).astype(np.float32), cv2.INTER_LINEAR,
                                   borderMode=cv2.BORDER_REPLICATE)
                reg[...] = reg * (1 - it["w"]) + warped * it["w"]
            t = _groove_pattern(us, vs, it["off"])                                     # 판과 함께 도는 홈 결
            reg[...] = reg * (1 + (it["g"] * t)[..., None])
        return out


def _groove_pattern(us, vs, off):
    """회전한 판 좌표(us,vs)에서 본 홈 결: 나선형 홈 광택(돌면 나선이 감기듯 움직임) + 부채꼴 광택 + 먼지 점. 판과 함께 도는 무늬."""
    r = np.sqrt(us * us + vs * vs)
    ang = np.arctan2(vs, us)
    spiral = np.cos(r * 38.0 - ang * 3.0 + off) * 0.55                                  # 나선: 판이 돌면 가닥이 눈에 띄게 돎
    fan = np.cos(3 * ang + off) * 0.45 + np.cos(7 * ang + 2.1 * off) * 0.25
    spec = (np.sin(ang * 41 + off * 3.0) * np.sin(r * 53 + off) > 0.90).astype(np.float32) * 1.0   # 먼지 점
    return (spiral + fan + spec) * 0.17


# ---------------------------------------------------------------- 톤암(바늘 달린 팔) 오르내림
class TonearmBob:
    """arms: [{"x0","y0","x1","y1" (0~1 비율), "kind": "tonearm"}] 톤암 전체를 감싼 상자.
    레코드가 한 바퀴 돌 때마다 레코드판의 미세한 휘어짐·편심 때문에 바늘 쪽이 살짝 오르내린다 (축 쪽은 거의 고정, 바늘 쪽이 가장 크게).
    records(RecordSpin 항목)가 있으면 레코드 회전과 같은 주기(정수 바퀴)로, 축 위치는 레코드 중심에서 먼 쪽 끝으로 본다."""

    def __init__(self, arms, W, H, N, fps, k=1, record_centers=None, amount=0.7, record_axes=None):
        import cv2
        self.cv2 = cv2
        self.N = N
        self.k = max(1, int(k))
        self.items = []
        rc = record_centers[0] if record_centers else None
        self.ends = []                                  # [(뿌리 좌표, 바늘 좌표)] — 확인용 표시에 씀
        for p in arms:
            x0, y0 = int(max(0, min(1, p["x0"])) * W), int(max(0, min(1, p["y0"])) * H)
            x1, y1 = int(max(0, min(1, p["x1"])) * W), int(max(0, min(1, p["y1"])) * H)
            if x1 - x0 < 12 or y1 - y0 < 4:
                continue
            polyp = p.get("poly")
            if polyp:                               # 직접 그린 톤암 윤곽: 꼭짓점 중 레코드 중심에서 가장 먼 것 = 축, 가장 가까운 것 = 바늘 쪽
                ends = [(q[0] * W, q[1] * H) for q in polyp]
            else:
                ends = [(x0, y0), (x1, y1), (x0, y1), (x1, y0)]
            if polyp and len(ends) >= 3:             # 윤곽의 가장 긴 방향(주축)의 양 끝 = 뿌리·바늘 후보
                P = np.array(ends, np.float64)
                mu = P.mean(0)
                vals, vecs = np.linalg.eigh(np.cov((P - mu).T))
                ax_ = vecs[:, int(np.argmax(vals))]
                pr = (P - mu) @ ax_
                ends = [tuple(P[int(np.argmin(pr))]), tuple(P[int(np.argmax(pr))])]
            if rc is not None:                      # 레코드 중심(타원 비율 반영)에서 가까운 끝 = 바늘 쪽, 먼 끝 = 뿌리(축)
                ra, rb = (record_axes if record_axes else (1.0, 1.0))
                d = [np.hypot((ex - rc[0]) / ra, (ey - rc[1]) / rb) for ex, ey in ends]
                pivot, tip = ends[int(np.argmax(d))], ends[int(np.argmin(d))]
            else:
                pivot, tip = ends[0], ends[1]
            self.ends.append((pivot, tip))
            L = float(np.hypot(tip[0] - pivot[0], tip[1] - pivot[1]))
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            ax, ay = (tip[0] - pivot[0]) / L, (tip[1] - pivot[1]) / L
            t = np.clip(((xx - pivot[0]) * ax + (yy - pivot[1]) * ay) / L, 0, 1)          # 0=축 … 1=바늘
            dist = np.abs((xx - pivot[0]) * (-ay) + (yy - pivot[1]) * ax)                  # 팔 선에서 떨어진 거리
            half = max(6.0, 0.05 * L)                                                                    # 팔 선 가까이만 (뒤 책장 등은 움직이지 않게)
            w = _smooth(1 - dist / half) * _smooth(np.minimum(xx - x0, x1 - 1 - xx) / 6.0 + 0.0) * _smooth(np.minimum(yy - y0, y1 - 1 - yy) / 6.0 + 0.0)
            if polyp:                                                                                    # 윤곽을 그렸으면 팔 모양 그대로(약간 여유) 안쪽만: 팔이 통째로 같이 움직여 두 개로 보이지 않음
                pm = poly_mask(polyp, (x0, y0, x1, y1), W, H, feather=0)
                pm = cv2.GaussianBlur(cv2.dilate(pm, np.ones((5, 5), np.uint8)), (0, 0), 1.6)
                w = np.clip(pm * 1.0, 0, 1)
            self.items.append({"box": (x0, y0, x1, y1), "t": t.astype(np.float32), "w": w.astype(np.float32),
                               "X": xx - x0, "Y": yy - y0, "amp": max(1.4, (0.010 if polyp else 0.007) * L) * float(amount) * H / 1080.0})

    def apply(self, out, f):
        cv2 = self.cv2
        ph = 2 * np.pi * self.k * (f % self.N) / self.N
        sig = np.sin(ph) + 0.35 * np.sin(2 * ph + 0.9) + 0.12 * np.sin(5 * ph)             # 한 바퀴에 한 번 크게 + 잔 떨림
        for it in self.items:
            x0, y0, x1, y1 = it["box"]
            reg = out[y0:y1, x0:x1]
            dy = it["amp"] * sig * (it["t"] ** 2.0) * it["w"]                              # 바늘 쪽일수록 많이 움직임
            warped = cv2.remap(reg, it["X"].astype(np.float32), (it["Y"] + dy).astype(np.float32), cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_REPLICATE)
            reg[...] = warped
        return out
