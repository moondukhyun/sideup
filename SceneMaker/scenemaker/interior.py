"""아늑한 실내 장면 (v11.22): 촛불·벽난로 불꽃·방 안 불빛 일렁임·반려동물 숨쉬기.

모든 움직임은 루프 N 프레임 동안 '정수 번' 반복되는 신호로 만들어 이음새가 없다.

- find_lights():  그림에서 촛불 불꽃(작고 밝은 따뜻한 점)과 벽난로 불(크고 주황·노랑인 덩어리)을 찾는다
- Interior:       촛불 흔들림 + 벽난로 불꽃 일렁임·불티 + 불빛이 방 안 벽·가구·바닥에 일렁이며 닿는 효과
                  + 반려동물 숨쉬기 (위치는 pets.json 또는 --pet 로 지정)
"""

import numpy as np

LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
WARM = np.array([1.0, 0.70, 0.36], dtype=np.float32)         # 불빛이 닿은 곳의 색 변화 (빨강이 가장 크게)


# ---------------------------------------------------------------- 불빛 찾기
def find_lights(bg, max_candles=24):
    """bg: float RGB (H,W,3) 0..1.
    반환: {"candles": [{"x","y","w","h"}...], "fire": {"mask","box","cx","cy","base"} 또는 None}  (전체 해상도 좌표)"""
    import cv2
    H, W = bg.shape[:2]
    sw = 960
    s = sw / float(W)
    sh = max(8, int(round(H * s)))
    small = cv2.resize(bg, (sw, sh), interpolation=cv2.INTER_AREA)
    lum = small @ LUMA
    r, g, b = small[..., 0], small[..., 1], small[..., 2]
    area_px = float(sw * sh)

    # 벽난로 불: 주황·노랑이 진하고 밝은 큰 덩어리 (불꽃 본체 + 뜨거운 핵)
    local = cv2.blur(lum, (61, 61))                                  # 주변보다 확실히 밝아야 '불' (불빛 받은 벽·벽난로 틀은 제외)
    body = ((r > 0.50) & ((r - b) > 0.22) & (g < r * 1.02) & (lum > 0.33) & ((lum - local) > 0.10)).astype(np.uint8)
    body = cv2.morphologyEx(body, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    body = cv2.morphologyEx(body, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, stats, cent = cv2.connectedComponentsWithStats(body, connectivity=8)
    fire = None
    best = 0
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if a >= 0.0011 * area_px and a > best and w >= 0.025 * sw and h >= 0.03 * sh:
            best, fire = a, i
    fire_info = None
    fire_zone = np.zeros((sh, sw), np.uint8)
    if fire is not None:
        sel = (lab == fire).astype(np.uint8)
        sel = cv2.dilate(sel, np.ones((9, 9), np.uint8))
        fire_zone = sel
        ys, xs = np.nonzero(lab == fire)
        m = cv2.GaussianBlur((lab == fire).astype(np.float32), (0, 0), 2.0)
        m = np.clip(m * 1.15, 0, 1)
        fire_info = {
            "mask": np.clip(cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR), 0, 1),
            "box": (xs.min() / s, ys.min() / s, xs.max() / s, ys.max() / s),
            "cx": float(xs.mean()) / s, "cy": float(ys.mean()) / s, "base": float(ys.max()) / s,
        }

    # 촛불 불꽃: 작고 아주 밝은 따뜻한 점 (불 덩어리 안쪽은 제외). 또렷하지 않은 그림이면 기준을 한 단계 낮춰 다시 찾음
    warm_local = cv2.blur((r - b), (11, 11)) > 0.07
    candles = []
    for thr in (0.74, 0.62):
        seed = ((lum > thr) & warm_local).astype(np.uint8)
        seed[fire_zone > 0] = 0
        seed = cv2.morphologyEx(seed, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        n, lab, stats, cent = cv2.connectedComponentsWithStats(seed, connectivity=8)
        for i in range(1, n):
            x, y, w, h, a = stats[i]
            if w > 0.035 * sw or a < 5:
                continue
            h = min(h, int(max(2.6 * w, 8)))          # 불꽃 아래로 이어진 밝은 양초 몸통은 잘라냄 (불꽃은 폭의 2~3배 높이)
            if h > 0.08 * sh or a > 0.0016 * area_px:
                continue
            if h < 0.8 * w and a > 40:                # 가로로 퍼진 덩어리 = 램프 갓·창문 불빛, 불꽃 아님
                continue
            candles.append((float(lum[lab == i].max()) * min(a, 120), x, y, w, h))
        if candles:
            break
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
    def __init__(self, bg, N, fps, strength=1.0, fire_strength=1.0, pets=None, seed=7, info=None):
        import cv2
        self.cv2 = cv2
        H, W = bg.shape[:2]
        self.H, self.W, self.N, self.fps = H, W, N, fps
        self.res = H / 1080.0
        self.strength = float(strength)
        self.fire_strength = float(fire_strength)
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
        shared = _signal(rng, N, 2, 7, 3)                           # 바람이 한 번 불면 촛불이 다 같이 흔들림
        nc = max(1, len(self.candles))
        self.candle_sigs = []
        for c in self.candles:
            own = _signal(rng, N, 5, max(16, int(N * 0.30)), 6)
            sig = 0.78 * own + 0.45 * shared
            sig /= (sig.std() + 1e-6)
            self.candle_sigs.append(sig)
            cx, cy = c["x"] / W * self.lw, c["y"] / H * self.lh
            sx = (0.15 if nc <= 2 else 0.10) * self.lw * (1.0 + 0.15 * min(c["h"] / (0.05 * H), 3))
            sy = sx * 0.85
            amp = (0.16 if nc <= 2 else 0.10 if nc <= 6 else 0.07) * self.strength
            maps.append(amp * np.exp(-(((xx - cx) / sx) ** 2 + ((yy - cy) / sy) ** 2) / 2.0))
            sigs.append(sig)
        self.fire_sig = None
        if self.fire is not None:
            fs = 0.8 * _signal(rng, N, 3, max(10, int(N * 0.24)), 7) + 0.4 * shared
            fs /= (fs.std() + 1e-6)
            self.fire_sig = fs
            cx, cy = self.fire["cx"] / W * self.lw, self.fire["cy"] / H * self.lh
            sx, sy = 0.26 * self.lw, 0.22 * self.lh
            fa = 0.20 * self.fire_strength
            maps.append(fa * np.exp(-(((xx - cx) / sx) ** 2 + ((yy - cy) / sy) ** 2) / 2.0))
            sigs.append(fs)
            floor_y = min(self.fire["base"] / H * self.lh + 0.16 * self.lh, self.lh - 1)          # 앞 바닥·러그에 퍼지는 불빛
            maps.append(0.12 * self.fire_strength * np.exp(-(((xx - cx) / (0.34 * self.lw)) ** 2 +
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
            win = np.exp(-(((xx_ - c["x"]) / (1.9 * fw + 6 * res)) ** 2 + ((yy_ - c["y"]) / (1.5 * fh + 6 * res)) ** 2))
            win = win * edge                                                              # 조각 가장자리에서 변형 0 → 네모 경계가 안 보임
            above = np.clip((c["y"] + 0.5 * fh - yy_) / max(fh, 4.0), 0, 1.6)             # 불꽃 아래(심지)는 고정, 위로 갈수록 흔들림
            core = np.exp(-(((xx_ - c["x"]) / (0.9 * fw + 2)) ** 2 + ((yy_ - c["y"]) / (0.7 * fh + 2)) ** 2)) * edge
            halo = np.exp(-(((xx_ - c["x"]) / (2.0 * fw + 5 * res)) ** 2 + ((yy_ - c["y"]) / (1.7 * fh + 5 * res)) ** 2) / 2) * edge
            sway = 0.80 * _signal(rng, N, 3, 12, 4) + 0.35 * shared
            sway /= (sway.std() + 1e-6)
            self.flames.append({
                "box": (x0, y0, x1, y1), "win": win.astype(np.float32), "above2": (above ** 2).astype(np.float32),
                "core": core.astype(np.float32), "halo": halo.astype(np.float32),
                "amp": (0.30 * fw + 1.2 * res) * self.strength, "sway": sway, "sig": self.candle_sigs[i],
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
                self.fk = max(2, int(round(1.5 * bh * sec / P)))                 # 초당 불꽃 높이의 약 1.5배 속도로 타오름
                self.fn1 = _periodic_noise(rng, P, bw, 9 * res, 5 * res, cv2)
                self.fn2 = _periodic_noise(rng, P, bw, 3.0 * res, 2.2 * res, cv2)
                self.fn3 = _periodic_noise(rng, P, bw, 14 * res, 12 * res, cv2)
                reps = (bh + 2 * P) // P + 2
                self.fn1, self.fn2, self.fn3 = [np.tile(a, (reps, 1)) for a in (self.fn1, self.fn2, self.fn3)]
                m = self.fire["mask"][fy0:fy1, fx0:fx1]
                yy_, xx_ = np.mgrid[0:bh, 0:bw].astype(np.float32)
                topw = _smooth((self.fire["base"] - fy0 - yy_) / max(1.0, (self.fire["base"] - by0) * 0.9))   # 위로 갈수록 크게 일렁
                self.fx = {"box": (fx0, fy0, fx1, fy1), "mask": m[..., None].astype(np.float32), "topw": topw.astype(np.float32),
                           "ax": (0.05 * bw + 5 * res), "bh": bh, "bw": bw,
                           "X": xx_, "Y": yy_, "src": bg[fy0:fy1, fx0:fx1].copy()}
                self.ember = self._make_embers(rng, bw, bh, fx0, fy0)

    # ------------------------------------------------------------ 불티
    def _make_embers(self, rng, bw, bh, fx0, fy0):
        n = int(26 * self.strength) + 6
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
        if self.fx is not None:
            fx = self.fx
            x0, y0, x1, y1 = fx["box"]
            P, k = self.fP, self.fk
            shift = int(round(k * P * f / self.N)) % P
            rows = slice(P - shift, P - shift + fx["bh"])
            n1, n2, n3 = self.fn1[rows], self.fn2[rows], self.fn3[rows]
            fs = float(self.fire_sig[f])
            ax = fx["ax"] * (1.0 + 0.12 * fs) * self.fire_strength
            dx = (0.62 * n1 + 0.22 * n2 + 0.16 * n3) * ax * fx["topw"]
            dy = (0.40 * n1 + 0.25 * n3) * ax * 0.55 * fx["topw"] + 0.0
            mapx = (fx["X"] + dx).astype(np.float32)
            mapy = (fx["Y"] + dy + 0.06 * fx["bh"] * max(-1.0, min(1.0, fs)) * fx["topw"]).astype(np.float32)
            warped = cv2.remap(fx["src"], mapx, mapy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            m = fx["mask"]
            reg = out[y0:y1, x0:x1]
            gain = 1.0 + (0.20 * n3[..., None] + 0.12 * n2[..., None] + 0.10 * fs) * self.fire_strength
            flame = np.clip(warped * gain, 0, 1)
            # 위로 길게 솟는 혀 (불꽃이 가끔 더 높이 튐): 위쪽으로 당긴 복사본을 '밝은 쪽 우선'으로 합침
            lift = (0.05 + 0.07 * (0.5 + 0.5 * np.tanh(fs))) * fx["bh"] * self.fire_strength
            tongue = cv2.remap(warped, fx["X"].astype(np.float32), (fx["Y"] + lift * fx["topw"]).astype(np.float32),
                               cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            flame = np.maximum(flame, tongue * 0.88 * (0.55 + 0.25 * np.tanh(fs)))
            near = np.clip(cv2.GaussianBlur(m[..., 0], (0, 0), 7.0 * self.res)[..., None] * 1.2 - m, 0, 1) * 0.55   # 불꽃 둘레 번짐
            reg[...] = reg * (1 - m) + flame * m
            reg[...] = reg * (1 - near) + np.maximum(reg, flame) * near
            self._draw_embers(out, f)
        # 2) 촛불 불꽃 흔들림 + 번쩍임
        for c in self.flames:
            x0, y0, x1, y1 = c["box"]
            reg = out[y0:y1, x0:x1]
            s = float(c["sway"][f])
            dx = s * c["amp"] * c["above2"]
            warped = cv2.remap(reg, (c["xx"] + dx).astype(np.float32), c["yy"].astype(np.float32), cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_REPLICATE)
            w = c["win"][..., None]
            reg[...] = reg * (1 - w) + warped * w
            b = float(c["sig"][f])
            reg += (c["core"][..., None] * (0.07 * b * st) + c["halo"][..., None] * (0.05 * b * st)) * WARM
        # 3) 불빛이 방 안에 일렁이며 닿는 효과 (곱셈 → 질감은 그대로, 밝기만 변함)
        if self.light_maps is not None:
            lo = np.tensordot(self.light_sigs[:, f], self.light_maps, axes=(0, 0))
            L = cv2.resize(lo, (self.W, self.H), interpolation=cv2.INTER_LINEAR)
            out *= 1.0 + L[..., None] * WARM
        return out

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
            x0, y0 = int(max(0, min(1, p["x0"])) * W), int(max(0, min(1, p["y0"])) * H)
            x1, y1 = int(max(0, min(1, p["x1"])) * W), int(max(0, min(1, p["y1"])) * H)
            if x1 - x0 < 24 or y1 - y0 < 16:
                continue
            kind = p.get("kind", "dog")
            period = 4.2 if kind == "dog" else 3.0                    # 자는 개 ≈ 호흡 14/분, 고양이 ≈ 20/분
            cycles = max(1, int(round(sec / period)))
            amp = (0.020 if kind == "dog" else 0.016) * float(p.get("amount", 1.0))
            yy, xx = np.mgrid[0:y1 - y0, 0:x1 - x0].astype(np.float32)
            bw, bh = x1 - x0, y1 - y0
            wx = _smooth(np.minimum(xx, bw - 1 - xx) / (0.20 * bw))
            wy = _smooth(yy / (0.30 * bh))
            yb = bh - 1.0
            self.items.append({
                "box": (x0, y0, x1, y1), "X": xx, "Y": yy, "w": (wx * wy).astype(np.float32), "yb": yb, "xc": bw / 2.0,
                "cycles": cycles, "amp": amp, "ph": float(rng.random()), "kind": kind,
            })

    def apply(self, out, f):
        cv2 = self.cv2
        for it in self.items:
            th = 2 * np.pi * (it["cycles"] * f / self.N + it["ph"])
            b = np.sin(th) + 0.25 * np.sin(2 * th + 0.7)              # 들이쉼은 길고 내쉼은 짧게
            x0, y0, x1, y1 = it["box"]
            reg = out[y0:y1, x0:x1]
            a = it["amp"] * b
            dy = (it["yb"] - it["Y"]) * a * it["w"]                   # 위쪽일수록 많이 움직임 (바닥 접촉면은 고정)
            dx = (it["X"] - it["xc"]) * a * 0.35 * it["w"]
            warped = cv2.remap(reg, (it["X"] + dx).astype(np.float32), (it["Y"] + dy).astype(np.float32),
                               cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            reg[...] = warped
        return out
