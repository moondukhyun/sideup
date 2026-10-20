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
def find_lights(bg, max_candles=24, exclude=None, fire_box=None, candle_pts=None):
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
        bx0, bx1 = max(0, int(x - 0.35 * w)), min(sw, int(x + w + 0.35 * w))
        by0, by1 = max(0, int(y - 0.35 * h)), min(sh, int(y + h + 0.08 * h))
        orange = ((r > 0.45) & ((r - b) > 0.18) & (lum > 0.28)).astype(np.uint8)
        box = np.zeros_like(orange)
        box[by0:by1, bx0:bx1] = 1
        body = (orange & box)
        body = cv2.morphologyEx(body, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        n2, lab2, st2, _ = cv2.connectedComponentsWithStats(body, connectivity=8)
        core_lab = set(np.unique(lab2[lab == pick]).tolist()) - {0}
        sel = np.isin(lab2, list(core_lab)).astype(np.uint8) if core_lab else (lab == pick).astype(np.uint8)
        sel = np.maximum(sel, (lab == pick).astype(np.uint8))
        ys, xs = np.nonzero(sel)
        fire_zone = cv2.dilate(sel, np.ones((25, 25), np.uint8))
        hotness = np.clip((lum - 0.48) / 0.32, 0, 1) * np.clip((g - 0.30) / 0.25, 0, 1)      # 밝고 노란 불꽃 부분만 (뒷벽·장작·벽돌은 제외)
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
                "amp": (0.045 * fw + 0.5 * res) * self.strength, "sway": sway, "sig": self.candle_sigs[i],
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
        if self.fx is not None and self.procedural:
            fx = self.fx
            x0, y0, x1, y1 = fx["box"]
            P, k = self.fP, self.fk
            shift = int(round(k * P * f / self.N)) % P
            rows = slice(shift, shift + fx["bh"])                  # 무늬가 '위로' 올라감 (이전에는 아래로 흘러내려 불꽃이 부자연스러웠음)
            n1, n2, n3 = self.fn1[rows], self.fn2[rows], self.fn3[rows]
            fs = float(self.fire_sig[f])
            ax = fx["ax"] * (1.0 + 0.12 * fs) * self.fire_strength
            dx = (0.70 * n1 + 0.30 * n2) * ax * fx["topw"]
            dy = 0.25 * n1 * ax * 0.4 * fx["topw"]                                              # 위아래는 아주 조금만
            warped = cv2.remap(fx["src"], (fx["X"] + dx).astype(np.float32), (fx["Y"] + dy).astype(np.float32),
                               cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            m = fx["mask"]
            dg = (0.09 * n3[..., None] + 0.05 * fs) * self.fire_strength                      # 불꽃 밝기가 천천히 오르내림
            flame = np.clip(warped * (1.0 + dg * np.array([1.0, 0.80, 0.45], np.float32)), 0, 1)   # 밝아져도 푸르스름해지지 않게 따뜻한 색 쪽으로만
            reg = out[y0:y1, x0:x1]
            reg[...] = reg * (1 - m) + flame * m
            self._draw_embers(out, f)
        # 2) 촛불 불꽃 흔들림 + 번쩍임
        for c in (self.flames if self.procedural else ()):
            x0, y0, x1, y1 = c["box"]
            reg = out[y0:y1, x0:x1]
            s = float(c["sway"][f])
            dx = s * c["amp"] * c["above2"]
            warped = cv2.remap(reg, (c["xx"] + dx).astype(np.float32), c["yy"].astype(np.float32), cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_REPLICATE)
            w = c["win"][..., None]
            reg[...] = reg * (1 - w) + warped * w
            b = float(c["sig"][f])
            reg += (c["core"][..., None] * (0.05 * b * st) + c["halo"][..., None] * (0.035 * b * st)) * WARM
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
            amp = (0.040 if kind == "dog" else 0.034) * float(p.get("amount", 1.0))      # 잠든 개·고양이의 갈비뼈·배가 눈에 보일 만큼 오르내림
            yy, xx = np.mgrid[0:y1 - y0, 0:x1 - x0].astype(np.float32)
            bw, bh = x1 - x0, y1 - y0
            wx = _smooth(np.minimum(xx, bw - 1 - xx) / (0.20 * bw))
            wy = _smooth(yy / (0.30 * bh))
            yb = bh - 1.0
            self.items.append({
                "box": (x0, y0, x1, y1), "X": xx, "Y": yy, "w": (wx * wy).astype(np.float32), "yb": yb, "xc": bw / 2.0,
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
            dy = (it["yb"] - it["Y"]) * a * it["w"]                   # 위쪽일수록 많이 움직임 (바닥 접촉면은 고정)
            dx = (it["X"] - it["xc"]) * a * 0.55 * it["w"]
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


# ---------------------------------------------------------------- 턴테이블 레코드판 회전
class RecordSpin:
    """records: [{"x0","y0","x1","y1" (0~1 비율), "kind": "record"}]. 상자에 꼭 맞는 타원(비스듬히 본 LP)의 '가운데 라벨'을
    33⅓ 회전/분으로 돌린다. 실제 LP 는 홈 위 반사광이 제자리에 있고 라벨 무늬만 도는 것처럼 보이므로 바깥 홈 부분은 그대로 둔다.
    한 루프에 정수 바퀴 → 이음새 없음. 가운데 축(스핀들)은 고정."""

    def __init__(self, records, W, H, N, fps, rpm=33.33, label=0.36):
        import cv2
        self.cv2 = cv2
        self.N = N
        sec = N / float(fps)
        self.k = max(1, int(round(rpm / 60.0 * sec)))
        self.rpm = self.k * 60.0 / sec
        self.items = []
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
            w = _smooth((label - r) / 0.06) * _smooth((r - 0.045) / 0.035)             # 라벨 안쪽만, 가운데 축은 제외
            self.items.append({"box": (rx0, ry0, rx1, ry1), "u": u, "v": v, "cx": cx, "cy": cy, "a": a, "b": b,
                               "w": w[..., None].astype(np.float32)})

    def apply(self, out, f):
        cv2 = self.cv2
        th = -2 * np.pi * self.k * (f % self.N) / self.N                              # 위에서 볼 때 시계 방향
        c, s = np.cos(th), np.sin(th)
        for it in self.items:
            x0, y0, x1, y1 = it["box"]
            reg = out[y0:y1, x0:x1]
            us = it["u"] * c + it["v"] * s
            vs = -it["u"] * s + it["v"] * c
            warped = cv2.remap(reg, (it["cx"] + it["a"] * us - x0).astype(np.float32),
                               (it["cy"] + it["b"] * vs - y0).astype(np.float32), cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_REPLICATE)
            reg[...] = reg * (1 - it["w"]) + warped * it["w"]
        return out


# ---------------------------------------------------------------- 톤암(바늘 달린 팔) 오르내림
class TonearmBob:
    """arms: [{"x0","y0","x1","y1" (0~1 비율), "kind": "tonearm"}] 톤암 전체를 감싼 상자.
    레코드가 한 바퀴 돌 때마다 레코드판의 미세한 휘어짐·편심 때문에 바늘 쪽이 살짝 오르내린다 (축 쪽은 거의 고정, 바늘 쪽이 가장 크게).
    records(RecordSpin 항목)가 있으면 레코드 회전과 같은 주기(정수 바퀴)로, 축 위치는 레코드 중심에서 먼 쪽 끝으로 본다."""

    def __init__(self, arms, W, H, N, fps, k=1, record_centers=None, amount=1.0):
        import cv2
        self.cv2 = cv2
        self.N = N
        self.k = max(1, int(k))
        self.items = []
        rc = record_centers[0] if record_centers else None
        for p in arms:
            x0, y0 = int(max(0, min(1, p["x0"])) * W), int(max(0, min(1, p["y0"])) * H)
            x1, y1 = int(max(0, min(1, p["x1"])) * W), int(max(0, min(1, p["y1"])) * H)
            if x1 - x0 < 12 or y1 - y0 < 4:
                continue
            ends = [(x0, y0), (x1, y1), (x0, y1), (x1, y0)]
            if rc is not None:                      # 레코드 중심에서 가장 먼 모서리 = 축(피벗), 가장 가까운 모서리 = 바늘 쪽
                d = [np.hypot(ex - rc[0], ey - rc[1]) for ex, ey in ends]
                pivot, tip = ends[int(np.argmax(d))], ends[int(np.argmin(d))]
            else:
                pivot, tip = ends[0], ends[1]
            L = float(np.hypot(tip[0] - pivot[0], tip[1] - pivot[1]))
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            ax, ay = (tip[0] - pivot[0]) / L, (tip[1] - pivot[1]) / L
            t = np.clip(((xx - pivot[0]) * ax + (yy - pivot[1]) * ay) / L, 0, 1)          # 0=축 … 1=바늘
            dist = np.abs((xx - pivot[0]) * (-ay) + (yy - pivot[1]) * ax)                  # 팔 선에서 떨어진 거리
            half = max(10.0, 0.09 * L * 1.6)
            w = _smooth(1 - dist / half) * _smooth(np.minimum(xx - x0, x1 - 1 - xx) / 6.0 + 0.0) * _smooth(np.minimum(yy - y0, y1 - 1 - yy) / 6.0 + 0.0)
            self.items.append({"box": (x0, y0, x1, y1), "t": t.astype(np.float32), "w": w.astype(np.float32),
                               "X": xx - x0, "Y": yy - y0, "amp": max(1.8, 0.011 * L) * float(amount) * H / 1080.0})

    def apply(self, out, f):
        cv2 = self.cv2
        ph = 2 * np.pi * self.k * (f % self.N) / self.N
        sig = np.sin(ph) + 0.35 * np.sin(2 * ph + 0.9) + 0.12 * np.sin(5 * ph)             # 한 바퀴에 한 번 크게 + 잔 떨림
        for it in self.items:
            x0, y0, x1, y1 = it["box"]
            reg = out[y0:y1, x0:x1]
            dy = it["amp"] * sig * (it["t"] ** 1.3) * it["w"]                              # 바늘 쪽일수록 많이 움직임
            warped = cv2.remap(reg, it["X"].astype(np.float32), (it["Y"] + dy).astype(np.float32), cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_REPLICATE)
            reg[...] = warped
        return out
