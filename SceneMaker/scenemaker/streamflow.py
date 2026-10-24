"""흐르는 물줄기 (v11.21): 대롱·처마·작은 폭포처럼 정지 이미지에 '멈춰 있는' 가늘고 밝은 세로 물줄기를 찾아 실제로 흐르게 한다.

- find_streams(): 주변보다 밝고(국소 대비) 색이 옅고 초록이 아니며 가늘고 세로로 긴 덩어리 = 물줄기
- StreamFlow:     물줄기 영역에 박혀 있는 정지 줄무늬를 세로로 풀어 지우고, 위→아래로 빠르게 흘러내리는 줄무늬를
                  입힌다 (줄무늬 주기 P 를 루프 동안 정수 번 이동 → N 프레임 뒤 정확히 제자리, 이음새 없음)
"""

import numpy as np

LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def find_streams(bg, min_len=0.05):
    """bg: float RGB (H,W,3). 물줄기 마스크 + 박스 + 맨 아래 좌표. 없으면 None."""
    import cv2
    H, W = bg.shape[:2]
    sw = 960
    s = sw / float(W)
    sh = max(8, int(round(H * s)))
    small = cv2.resize(bg, (sw, sh), interpolation=cv2.INTER_AREA)
    lum = small @ LUMA
    sat = small.max(-1) - small.min(-1)
    # 가는 선(릿지) 검출: 왼쪽·오른쪽 이웃보다 '모두' 밝아야 함 → 어두운 물체 옆의 밝은 띠(한쪽만 밝은 경계)는 제외
    line = np.full_like(lum, -1.0)
    for ws in (5, 7, 9):
        left, right = np.roll(lum, ws, 1), np.roll(lum, -ws, 1)
        line = np.maximum(line, np.minimum(lum - left, lum - right))
    bright = np.clip((line - 0.04) / 0.08, 0, 1)
    lowsat = np.clip(1 - (sat - 0.18) / 0.22, 0, 1)                      # 물은 색이 옅음
    notgreen = np.clip(1 - (small[..., 1] - np.maximum(small[..., 0], small[..., 2])) * 10, 0, 1)
    cand = ((bright * lowsat * notgreen) > 0.30).astype(np.uint8)
    cand = cv2.morphologyEx(cand, cv2.MORPH_CLOSE, np.ones((21, 3), np.uint8))   # 세로로 끊긴 곳 이어 붙임
    cand = cv2.morphologyEx(cand, cv2.MORPH_OPEN, np.ones((9, 1), np.uint8))     # 짧은 조각 제거
    n, lab, stats, _ = cv2.connectedComponentsWithStats(cand, connectivity=8)
    dens = cv2.blur(cand.astype(np.float32), (81, 81))                     # 주변에 비슷한 후보가 얼마나 많은지 (기와 결·돌 하이라이트 = 많음)
    found = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if h >= min_len * sh and w <= 0.07 * sw and h >= 3.0 * w and area >= 0.2 * w * h:
            sel = lab == i
            contrast = float(line[sel].mean())                              # 양쪽보다 얼마나 밝은가
            level = float(lum[sel].mean())
            clutter = float(dens[sel].mean()) * 81 * 81 / max(1.0, float(area))   # 이웃 후보 면적 / 자기 면적
            if contrast < 0.10 or level < 0.55 or clutter > 6.0:            # 진짜 물줄기: 아주 밝고 대비가 강한 외톨이 선
                continue
            found.append((contrast * h, i, x, y, w, h))
    if not found:
        return None
    found.sort(reverse=True)                                              # 대비 x 길이가 큰 것부터 최대 3개
    keep = np.zeros((sh, sw), np.uint8)
    boxes, bottoms = [], []
    for _, i, x, y, w, h in found[:3]:
        keep[lab == i] = 255
        ys, xs = np.nonzero(lab == i)
        low = ys >= ys.max() - 2
        boxes.append((x / s, y / s, w / s, h / s))
        bottoms.append((float(xs[low].mean()) / s, float(ys.max()) / s))
    keep = cv2.dilate(keep, np.ones((3, 5), np.uint8))                    # 폭 여유 (원래 물줄기 굵기를 거의 유지)
    m = cv2.GaussianBlur(keep.astype(np.float32) / 255.0, (0, 0), 1.5)
    mask = np.clip(cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR), 0, 1)
    return {"mask": mask, "boxes": boxes, "bottoms": bottoms}


class StreamFlow:
    def __init__(self, bg, info, N, fps, strength=1.0, seed=7):
        import cv2
        self.cv2 = cv2
        H, W = bg.shape[:2]
        self.H, self.W, self.N, self.fps = H, W, N, fps
        self.strength = float(strength)
        res = H / 1080.0
        self.mask = info["mask"]
        ys, xs = np.nonzero(self.mask > 0.04)
        pad = int(14 * res) + 4
        self.y0, self.y1 = max(0, int(ys.min()) - pad), min(H, int(ys.max()) + pad)
        self.x0, self.x1 = max(0, int(xs.min()) - pad), min(W, int(xs.max()) + pad)
        h, w = self.y1 - self.y0, self.x1 - self.x0
        region = bg[self.y0:self.y1, self.x0:self.x1]
        # 정지 이미지에 박힌 물줄기 줄무늬를 세로로 풀어 흐리게 → 움직이는 줄무늬가 그 위에 입혀져도 겹쳐 보이지 않음
        self.smooth = cv2.GaussianBlur(region, (0, 0), sigmaX=1.2 * res, sigmaY=22 * res)
        # 위아래로 정확히 이어지는(주기 P) 세로 줄무늬 무늬
        rng = np.random.default_rng(seed + 401)
        self.P = max(32, int(120 * res))
        base = rng.normal(0, 1, (self.P, w)).astype(np.float32)
        tiled = cv2.GaussianBlur(np.tile(base, (3, 1)), (0, 0), sigmaX=0.9 * res, sigmaY=6.5 * res)
        pat = tiled[self.P:2 * self.P]
        pat = pat / (float(pat.std()) + 1e-6)
        self.Rt = np.tile(pat, ((h + 2 * self.P) // self.P + 2, 1)).astype(np.float32)
        # 속도: 약 480px/s (1080p) — 루프 N 프레임 동안 정확히 k 주기를 이동하도록 양자화 (v = k*P/N)
        v_target = 480.0 * res / fps
        self.k = max(1, int(round(v_target * N / self.P)))
        self.speed_px_per_frame = self.k * self.P / N
        self.reg_mask = self.mask[self.y0:self.y1, self.x0:self.x1][..., None].astype(np.float32)

    def apply(self, out, f):
        """out: float RGB (H,W,3) 0..1 제자리 수정 후 반환."""
        s = int(round(self.k * self.P * f / self.N)) % self.P
        h = self.y1 - self.y0
        patt = self.Rt[self.P - s:self.P - s + h, :self.x1 - self.x0][..., None]        # 아래로 흘러내리는 줄무늬
        m = self.reg_mask
        a = np.clip(m * 0.9, 0, 1) * min(1.0, self.strength)
        reg = out[self.y0:self.y1, self.x0:self.x1]
        cur = reg * (1 - a) + self.smooth * a
        mod = 1.0 + 0.24 * self.strength * patt * m
        glint = 0.08 * self.strength * np.clip(patt - 0.6, 0, None) * m
        out[self.y0:self.y1, self.x0:self.x1] = np.clip(cur * mod + glint, 0, 1)
        return out


class RiverFlow:
    """v11.44: 직접 표시한 계곡·개울 물이 정해진 방향으로 흐르게 한다.

    표시한 영역 안의 물결 무늬(흐름 방향으로 길쭉한 줄무늬)를 흐름 방향으로 굴려 보내며,
    줄무늬 주기 P 를 루프 동안 정수 번 이동하므로 N 프레임 뒤 정확히 제자리 → 이음새 없음.
    가까운(화면 아래) 물일수록 일렁임이 크다. 프레임마다 새 배열만 만들어 스레드에 안전.
    """

    DIRS = {"l": (-1, 0), "r": (1, 0), "d": (0, 1), "u": (0, -1)}

    def __init__(self, bg, zones, N, fps, strength=1.0, seed=7, speed=1.0):
        import cv2
        self.cv2 = cv2
        H, W = bg.shape[:2]
        self.H, self.W, self.N, self.fps = H, W, N, fps
        self.strength = float(strength)
        res = H / 1080.0
        self.items = []
        self.mask = np.zeros((H, W), np.float32)
        for zi, (d, zone) in enumerate(zones):
            m = cv2.GaussianBlur(zone.astype(np.float32), (0, 0), 3.0 * res + 1.0)
            ys, xs = np.nonzero(m > 0.02)
            if len(ys) < 40:
                continue
            pad = int(10 * res) + 3
            y0, y1 = max(0, int(ys.min()) - pad), min(H, int(ys.max()) + pad)
            x0, x1 = max(0, int(xs.min()) - pad), min(W, int(xs.max()) + pad)
            h, w = y1 - y0, x1 - x0
            horiz = d in ("l", "r")
            P = max(48, int(110 * res))
            rng = np.random.default_rng(seed + 977 + zi)
            pats = []
            for sa, sc in ((10.0, 2.2), (16.0, 3.4), (7.0, 1.6)):                  # 흐름 방향으로 길쭉한 줄무늬 3겹
                shape = (h, P) if horiz else (P, w)
                base = rng.normal(0, 1, shape).astype(np.float32)
                tiled = np.tile(base, (1, 3) if horiz else (3, 1))
                sx, sy = (sa, sc) if horiz else (sc, sa)
                tiled = cv2.GaussianBlur(tiled, (0, 0), sigmaX=sx * res, sigmaY=sy * res)
                pat = tiled[:, P:2 * P] if horiz else tiled[P:2 * P, :]
                pat = pat / (float(pat.std()) + 1e-6)
                reps = ((w if horiz else h) + 2 * P) // P + 2
                pats.append(np.tile(pat, (1, reps) if horiz else (reps, 1)).astype(np.float32))
            v_px = 130.0 * res * float(speed) / fps                                  # 먼 개울이 천천히 흐르는 정도
            k = max(1, int(round(v_px * N / P)))
            near = (0.45 + 1.1 * (np.arange(y0, y1, dtype=np.float32) / H))[:, None]     # 아래(가까움)일수록 크게 일렁
            self.items.append({"d": d, "box": (x0, y0, x1, y1), "P": P, "k": k, "pats": pats,
                               "m": m[y0:y1, x0:x1, None].astype(np.float32), "near": near,
                               "gx": np.tile(np.arange(w, dtype=np.float32), (h, 1)),                 # 잘라낸 조각 안의 좌표 (remap 은 조각 기준)
                               "gy": np.tile(np.arange(h, dtype=np.float32)[:, None], (1, w))})
            self.mask = np.maximum(self.mask, m)

    def apply(self, out, f):
        cv2 = self.cv2
        res = self.H / 1080.0
        for it in self.items:
            x0, y0, x1, y1 = it["box"]
            h, w = y1 - y0, x1 - x0
            P = it["P"]
            s = int(round(it["k"] * P * f / self.N)) % P
            horiz = it["d"] in ("l", "r")
            sign = 1 if it["d"] in ("r", "d") else -1

            def cut(pat):
                o = (P - s) if sign > 0 else s
                return (pat[:, o:o + w] if horiz else pat[o:o + h, :])
            p1, p2, p3 = (cut(p) for p in it["pats"])
            amp = 1.8 * res * self.strength
            along = amp * p1 * it["near"]
            cross = 0.6 * amp * p2 * it["near"]
            if horiz:
                mx, my = it["gx"] + along, it["gy"] + cross
            else:
                mx, my = it["gx"] + cross, it["gy"] + along
            reg = np.ascontiguousarray(out[y0:y1, x0:x1])
            warped = cv2.remap(reg, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            mod = 1.0 + 0.10 * self.strength * p3[..., None]
            glint = 0.06 * self.strength * np.clip(p2 - 0.8, 0, None)[..., None]
            a = it["m"] * min(1.0, 0.95 * self.strength)
            out[y0:y1, x0:x1] = np.clip(reg * (1 - a) + (warped * mod + glint) * a, 0, 1)
        return out
