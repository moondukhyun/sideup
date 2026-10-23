"""깊이 지도 기반 날씨 디테일: 땅 물 튀김, 물웅덩이 물결, 모서리에서 맺혀 떨어지는 물방울.

깊이 지도(Depth Anything V2, 가까울수록 1)에서
- 땅(ground): 아래로 갈수록 가까워지는 면 (길·풀·의자 윗면 등 수평면)
- 물웅덩이(puddle): 땅 중에서 질감이 매끈한 곳 (젖은 길·고인 물)
- 물방울 맺힘점(drip): 물체의 아래 모서리 — 바로 아래가 훨씬 먼 곳 (의자 앞 모서리, 가지·잎 아래)
를 찾고, 루프 N 프레임 안에서 정확히 반복되는 이벤트로 그린다.
"""

import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .config import ROOT


# ---------- 깊이 지도 ----------
def depth_map(image_path, out_path, cfg):
    """sd-scripts venv(torch+transformers)로 깊이 지도 생성 (결과 캐시)."""
    out_path = Path(out_path)
    if out_path.exists() and out_path.stat().st_mtime >= Path(image_path).stat().st_mtime:
        return out_path
    py = Path(cfg["lora"]["sd_scripts"]) / "venv" / "Scripts" / "python.exe"
    if not py.exists():
        print(f"  ! 깊이 지도 모델 없음 — config.toml [lora] sd_scripts 확인 (찾는 위치: {py}) → 깊이 필요한 효과는 추정 깊이로 대체")
        return None
    import os
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([str(py), str(ROOT / "scripts" / "depth_map.py"), str(image_path), str(out_path)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    if r.returncode != 0 or not out_path.exists():
        print(f"  ! 깊이 지도 실패 — 디테일 없이 진행 ({r.stderr.strip()[-200:]})")
        return None
    return out_path


# ---------- 마스크 ----------
def _smooth(a, radius):
    img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    return np.asarray(img.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32) / 255.0


def build_maps(bg, depth, seed=7, max_drips=14):
    """bg: PIL RGB (W,H), depth: PIL L 같은 크기 → 작은 해상도에서 마스크·맺힘점 계산 후 원래 좌표로."""
    W, H = bg.size
    sw, sh = 480, max(8, round(480 * H / W))
    d = np.asarray(depth.convert("L").resize((sw, sh), Image.BILINEAR), dtype=np.float32) / 255.0
    lum = np.asarray(bg.convert("L").resize((sw, sh), Image.BILINEAR), dtype=np.float32) / 255.0
    k = 3
    gy = np.zeros_like(d)
    gy[:-k] = d[k:] - d[:-k]                                  # 아래로 갈수록 가까워짐 → 양수

    rgb_s = np.asarray(bg.convert("RGB").resize((sw, sh), Image.BILINEAR), dtype=np.float32) / 255.0
    not_green = np.clip(1 - (rgb_s[..., 1] - np.maximum(rgb_s[..., 0], rgb_s[..., 2])) * 12, 0, 1)
    flat = np.clip((gy + 0.002) / 0.012, 0, 1)                # 아래로 갈수록 가까워지는 면 (완만해도 포함)
    ground = flat * not_green * np.clip((d - 0.15) / 0.2, 0, 1)
    # 열림 연산(최소→최대 필터): 폭이 좁은 난간·기둥 제거, 넓은 바닥만 남김
    gimg = Image.fromarray((np.clip(ground, 0, 1) * 255).astype(np.uint8))
    gimg = gimg.filter(ImageFilter.MinFilter(7)).filter(ImageFilter.MaxFilter(7))
    ground = _smooth(np.asarray(gimg, dtype=np.float32) / 255.0, 2)
    # 매끈한 곳 = 국소 분산 작음 → 젖은 길·물웅덩이
    mean = _smooth(lum, 2)
    var = _smooth((lum - mean) ** 2 * 40, 2)
    puddle = ground * np.clip(1.0 - var / 0.25, 0, 1) * np.clip((d - 0.35) / 0.2, 0, 1)
    puddle *= np.clip((0.9 - d) / 0.1, 0, 1)                  # 가장 가까운 물체(의자 윗면 등)는 제외
    pimg = Image.fromarray((np.clip(puddle, 0, 1) * 255).astype(np.uint8))
    puddle = np.asarray(pimg.filter(ImageFilter.MinFilter(15)).filter(ImageFilter.MaxFilter(15)),
                        dtype=np.float32) / 255.0                # 넓은 바닥에만 물웅덩이 (난간 제외)

    # 물방울 맺힘점: 바로 아래가 훨씬 먼 곳 (물체 아래 모서리)
    drop = np.zeros_like(d)
    drop[:-4] = d[:-4] - d[4:]
    rgb = np.asarray(bg.convert("RGB").resize((sw, sh), Image.BILINEAR), dtype=np.float32) / 255.0
    green = (rgb[..., 1] - np.maximum(rgb[..., 0], rgb[..., 2])) > 0.03
    green = _smooth(green.astype(np.float32), 2) > 0.2          # 잎·풀 근처 제외 (물방울은 의자·처마 모서리에만)
    cand = (drop > 0.12) & (d > 0.45) & ~green
    ys, xs = np.nonzero(cand)
    rng = np.random.default_rng(seed)
    drips = []
    if len(xs):
        order = rng.permutation(len(xs))
        taken = np.zeros((sh, sw), bool)
        for i in order:
            y, x = ys[i], xs[i]
            if taken[max(0, y - 6):y + 7, max(0, x - 6):x + 7].any():
                continue
            taken[y, x] = True
            fall = 0
            while y + fall + 1 < sh and d[y + fall + 1] [x] < d[y, x] - 0.05 and fall < sh * 0.25:
                fall += 1
            drips.append((x / sw * W, (y + 1) / sh * H, float(d[y, x]), max(fall, 6) / sh * H))
            if len(drips) >= max_drips:
                break
    leaf_cand = (drop > 0.05) & (d > 0.25) & green
    lys, lxs = np.nonzero(leaf_cand)
    trickles = []
    if len(lxs):
        taken = np.zeros((sh, sw), bool)
        for i in rng.permutation(len(lxs)):
            y, x = lys[i], lxs[i]
            if taken[max(0, y - 8):y + 9, max(0, x - 8):x + 9].any():
                continue
            taken[y, x] = True
            trickles.append((x / sw * W, (y + 1) / sh * H, float(d[y, x])))
            if len(trickles) >= 45:
                break
    up = lambda a: np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR),
                              dtype=np.float32) / 255.0
    depth_full = np.asarray(depth.convert("L").resize((W, H), Image.BILINEAR), dtype=np.float32) / 255.0
    return {"ground": up(ground), "puddle": up(puddle), "depth": depth_full, "drips": drips,
            "trickles": trickles}


def opening_mask(depth, polys=None, W=None, H=None):
    """텐트 입구처럼 '안쪽 천·바닥(가까움)' 너머로 열린 바깥 풍경 영역 (0~1, H×W). polys 가 있으면(사용자가 그린 윤곽) 그것을 쓴다.
    없으면 깊이 지도로: 가까운 곳(천·바닥)과 먼 곳(숲·땅)을 나누고, 가장 큰 열린 덩어리(+비슷한 큰 덩어리)만 남긴다."""
    import cv2
    d = np.asarray(depth, dtype=np.float32)
    H, W = d.shape[:2]
    if polys:
        m = np.zeros((H, W), np.uint8)
        for poly in polys:
            cv2.fillPoly(m, [np.array([[p[0] * W, p[1] * H] for p in poly], np.int32)], 1)
        return cv2.GaussianBlur(m.astype(np.float32), (0, 0), max(2.0, 0.004 * W))
    sw = 320
    sh = max(8, int(round(H * sw / W)))
    ds = cv2.resize(d, (sw, sh), interpolation=cv2.INTER_AREA)
    hist, edges = np.histogram(ds, bins=64, range=(0, 1))
    w0 = np.cumsum(hist).astype(np.float64)
    m0 = np.cumsum(hist * (edges[:-1] + edges[1:]) / 2.0)
    tot, mt = w0[-1], m0[-1]
    best, thr = -1.0, 0.55
    for i in range(1, 63):                                           # Otsu: 가까움/멂 두 무리를 가르는 값
        a, b = w0[i], tot - w0[i]
        if a < 1 or b < 1:
            continue
        var = a * b * ((m0[i] / a) - ((mt - m0[i]) / b)) ** 2
        if var > best:
            best, thr = var, (edges[i] + edges[i + 1]) / 2.0
    thr = float(np.clip(thr, 0.45, 0.72))
    far = (ds < thr).astype(np.uint8)
    far = cv2.morphologyEx(far, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(far, connectivity=8)
    keep = np.zeros_like(far)
    if n > 1:
        areas = st[1:, cv2.CC_STAT_AREA]
        big = areas.max()
        for i in range(1, n):
            if st[i, cv2.CC_STAT_AREA] >= 0.25 * big and st[i, cv2.CC_STAT_AREA] > 0.01 * sw * sh:
                keep[lab == i] = 1
    keep = cv2.morphologyEx(keep, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    om = cv2.resize(keep.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
    return cv2.GaussianBlur(om, (0, 0), max(2.0, 0.004 * W))


def opening_mask_cool(bg, depth=None):
    """텐트 문 같은 '열린 바깥' 찾기 (색 + 깊이): 바깥(자갈·호수·산·하늘)은 푸르스름·회색이고 텐트 천·바닥은 따뜻한 베이지라는 점을 이용.
    깊이가 있으면 가장 가까운 안쪽 물건(침구·랜턴)은 뺀다. 못 찾으면 None. 반환 0~1 (H×W)."""
    import cv2
    H, W = bg.shape[:2]
    sw = 960
    s = sw / float(W)
    sh = max(8, int(round(H * s)))
    small = np.clip(cv2.resize(np.asarray(bg, np.float32), (sw, sh), interpolation=cv2.INTER_AREA), 0, 1)
    r, g, b = small[..., 0], small[..., 1], small[..., 2]
    lum = small @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    warm = cv2.GaussianBlur(r - b, (0, 0), 1.5)
    cool = ((warm < 0.045) & (lum < 0.93)).astype(np.uint8)
    if depth is not None:
        d = cv2.resize(np.asarray(depth, np.float32), (sw, sh), interpolation=cv2.INTER_AREA)
        if cool.sum() > 50:
            thr = min(0.97, float(np.percentile(d[cool > 0], 85)) + 0.06)
            cool = cool & (d < thr).astype(np.uint8)
    cool = cv2.morphologyEx(cool, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    cool = cv2.morphologyEx(cool, cv2.MORPH_CLOSE, np.ones((13, 13), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(cool, connectivity=8)
    if n <= 1:
        return None
    areas = st[1:, cv2.CC_STAT_AREA]
    big = float(areas.max())
    keep = np.zeros_like(cool)
    for i in range(1, n):
        a = float(st[i, cv2.CC_STAT_AREA])
        if a >= 0.30 * big and a >= 0.03 * sw * sh:
            keep[lab == i] = 1
    if keep.sum() < 0.04 * sw * sh:
        return None
    m = cv2.GaussianBlur(keep.astype(np.float32), (0, 0), max(1.5, 0.004 * sw))
    return np.clip(cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR), 0, 1)


def outside_maps(maps, om, depth):
    """물 튀김·물방울을 바깥(열린) 영역으로 제한하고, 바깥 땅(자갈·흙)에도 빗방울이 튀게 한다."""
    H, W = om.shape[:2]
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    low = np.clip((yy - 0.45) / 0.12, 0, 1) * np.clip((depth - 0.12) / 0.12, 0, 1) * np.clip((0.95 - depth) / 0.10, 0, 1)      # 열린 바깥 안에서는 가까운 자갈도 포함
    out = dict(maps)
    out["ground"] = np.maximum(maps["ground"] * om, om * low * 0.9)
    out["puddle"] = maps["puddle"] * om
    out["drips"] = [t for t in maps["drips"] if om[min(H - 1, int(t[1])), min(W - 1, int(t[0]))] > 0.5]
    out["trickles"] = [t for t in maps["trickles"] if om[min(H - 1, int(t[1])), min(W - 1, int(t[0]))] > 0.5]
    return out


# ---------- 이벤트 (루프 안에서 반복) ----------
class WeatherDetails:
    def __init__(self, maps, W, H, N, fps, intensity=1.0, seed=7, gain=1.0):
        self.W, self.H, self.N, self.fps = W, H, N, fps
        self.gain = float(gain)
        self.res = H / 1080.0
        rng = np.random.default_rng(seed + 11)
        self.depth = maps["depth"]
        secs = N / fps
        self.splashes = self._sample(maps["ground"], int(170 * intensity * secs * W * H / (1920 * 1080)), rng)
        self.ripples = self._sample(maps["puddle"], int(14 * intensity * secs * W * H / (1920 * 1080)), rng)
        # 물방울: 주기 = N/k (정수 k) → 루프 안에서 정확히 반복
        self.drips = []
        for (x, y, dd, fall) in maps["drips"]:
            k = int(rng.integers(1, 4))
            self.drips.append({"x": x, "y": y, "d": dd, "fall": fall, "period": N / k,
                               "phase": float(rng.uniform(0, N / k))})
        self.trickles = self._init_trickles(maps, rng)

    def _init_trickles(self, maps, rng):
        """잎 끝 물방울: 지점마다 0.5~1.5초 간격으로 불규칙하게 떨어짐 (루프 N 프레임 안에서 반복)."""
        out = []
        lo, hi = int(0.5 * self.fps), int(1.5 * self.fps)
        for (x, y, dd) in maps.get("trickles", []):
            t = float(rng.uniform(0, hi))
            events = []
            while t < self.N - lo * 0.5:
                events.append(t)
                t += float(rng.uniform(lo, hi))
            out.append({"x": x, "y": y, "d": dd, "events": np.array(events),
                        "fall": float(rng.uniform(60, 160)) * self.res,
                        "size": float(rng.uniform(0.8, 1.3))})
        return out

    def _sample(self, mask, n, rng):
        p = mask.ravel().astype(np.float64)
        if n <= 0 or p.sum() < 1e-3:
            return []
        p /= p.sum()
        idx = rng.choice(p.size, size=n, p=p)
        ys, xs = np.divmod(idx, self.W)
        births = rng.integers(0, self.N, n)
        return [(float(x) + rng.uniform(-0.5, 0.5), float(y), int(b)) for x, y, b in zip(xs, ys, births)]

    def draw(self, f):
        """바닥 물 튀김 (L, 0~255): 가까울수록 크고 뚜렷하게, 멀수록 작고 흐릿하게."""
        W, H, r0 = self.W, self.H, self.res
        near_img = Image.new("L", (W, H), 0)          # 가까운 튐 (선명)
        far_img = Image.new("L", (W, H), 0)           # 먼 튐 (흐리게)
        dn, df = ImageDraw.Draw(near_img), ImageDraw.Draw(far_img)
        for i, (x, y, b) in enumerate(self.splashes):
            age = (f - b) % self.N
            pre = self.N - age                              # 충돌 직전 프레임 수 (1, 2 = 떨어지는 중)
            if age > 5 and pre not in (1, 2):
                continue
            rng = np.random.default_rng(i * 7919 + b)
            near = float(self.depth[min(int(y), H - 1), min(int(x), W - 1)])
            # 바닥은 화면 아래쪽일수록 가까움 (앞의 나무 때문에 깊이값이 작게 나오는 경우 보정)
            near = max(near, float(np.clip((y / H - 0.35) / 0.6, 0, 1)))
            dr = dn if near > 0.55 else df
            if age > 5:
                # 땅에 닿기 직전: 위에서 내려오는 짧은 빗줄기 (한 프레임에 줄 길이만큼 이동) → 점이 '생기는' 게 아니라 '떨어지는' 것으로 보임
                L = (12 + 40 * near) * r0
                head_y = y - L * (pre - 1) * 1.15 - L * 0.1
                dr.line((x - 0.08 * L, head_y - L, x, head_y), fill=int((55 + 70 * near) * self.gain), width=max(1, round(0.7 * r0)))
                continue
            s_ = (1.5 + 10.0 * near ** 2) * r0 * rng.uniform(0.6, 1.2) * (0.55 + 0.45 * self.gain)           # 가까우면 최대 약 10px (gain 이 낮으면 더 작게)
            a = int((120 + 110 * near) * (1 - age / 6) * rng.uniform(0.6, 1.0) * self.gain)
            lw = max(1, round((0.5 + 0.8 * near) * r0))
            if age == 0:                                   # 부딪힌 순간: 납작한 밝은 점
                dr.ellipse((x - s_ * 0.35, y - s_ * 0.08, x + s_ * 0.35, y + s_ * 0.08), fill=a)
                continue
            t = min(1.0, age / 5)
            # 위로 솟는 짧은 물기둥 (가까운 것만)
            if near > 0.6 and age <= 1:
                dr.line((x, y, x, y - s_ * (0.9 - 0.3 * age)), fill=int(a * 0.8), width=lw)
            # 왕관처럼 사방으로 튀는 방울 (수·각도 제각각)
            n = int(rng.integers(2, 5))
            for ang, dd in zip(rng.uniform(0.08, 0.92, n) * np.pi, rng.uniform(0.6, 1.2, n)):
                cx = x + np.cos(ang) * s_ * dd * (0.3 + 0.9 * t)
                cy = y - np.sin(ang) * s_ * dd * (1.4 * t - 1.1 * t * t)
                dot = max(0.7, lw * 0.8 * rng.uniform(0.6, 1.1))
                dr.ellipse((cx - dot, cy - dot, cx + dot, cy + dot), fill=a)
            # 바닥에 번지는 얇은 고리 (가까운 것만, 불완전하게)
            if near > 0.45:
                rr = s_ * (0.4 + 0.8 * t)
                start = float(rng.uniform(0, 180))
                dr.arc((x - rr, y - rr * 0.22, x + rr, y + rr * 0.22), start, start + 250,
                       fill=int(a * 0.3), width=1)
        far_img = far_img.filter(ImageFilter.GaussianBlur(1.2 * r0))
        near_img = near_img.filter(ImageFilter.GaussianBlur(0.5 * r0))
        return Image.fromarray(np.maximum(np.asarray(near_img), np.asarray(far_img)))

    def apply(self, out, f):
        """물결·물방울을 '그리지' 않고 배경을 굴절시켜 표현 (out: float RGB, 제자리 수정 후 반환)."""
        import cv2
        r0 = self.res
        for i, (x, y, b) in enumerate(self.ripples):
            age = (f - b) % self.N
            if age > 17:
                continue
            rng = np.random.default_rng(i * 104729 + b)
            near = self.depth[min(int(y), self.H - 1), min(int(x), self.W - 1)]
            R = (4 + age * (1.3 + 3.0 * near)) * r0 * rng.uniform(0.8, 1.2)
            flat = (0.2 + 0.2 * near) * rng.uniform(0.85, 1.15)
            amp = (0.9 + 1.6 * near) * r0 * (1 - age / 18) ** 1.5
            pw, ph = int(R * 1.4) + 4, int(R * flat * 1.4) + 4
            x0, y0 = int(x) - pw, int(y) - ph
            x1, y1 = int(x) + pw, int(y) + ph
            if x0 < 0 or y0 < 0 or x1 >= self.W or y1 >= self.H:
                continue
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            ex, ey = (xx - x) / R, (yy - y) / (R * flat)
            rr = np.sqrt(ex * ex + ey * ey) + 1e-6
            lam = 0.35 + 0.1 * rng.random()
            theta = np.arctan2(ey, ex)                               # 테두리 세기를 방향마다 다르게 (완벽한 원 방지)
            wob = 1 + 0.35 * np.sin(theta * int(rng.integers(2, 5)) + rng.uniform(0, 6.28))
            env = np.exp(-((rr - 1.0) / 0.35) ** 2) * wob
            wave = np.sin((rr - 1.0) / lam * 2 * np.pi) * env * amp
            mx = (xx + wave * ex / rr).astype(np.float32)
            my = (yy + wave * ey / rr * flat * 1.6).astype(np.float32)
            out[y0:y1, x0:x1] = cv2.remap(out, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            glint = np.clip(wave / (amp + 1e-6), 0, 1) * env * 0.03 * (1 - age / 18)
            out[y0:y1, x0:x1] += glint[..., None].astype(np.float32)
        g = 2200 * r0 / self.fps ** 2
        for dp in self.drips:
            t = (f - dp["phase"]) % dp["period"]
            grow = dp["period"] * 0.8
            rr_ = (1.2 + 2.6 * dp["d"]) * r0
            if t < grow:
                q = t / grow
                rad, cy, stretch = rr_ * (0.5 + 0.5 * q), dp["y"] + rr_ * 0.4 * q, 1.2 + 0.5 * q
            else:
                tf = t - grow
                dy = 0.5 * g * tf * tf
                if dy > dp["fall"]:
                    continue
                rad, cy, stretch = rr_ * 0.8, dp["y"] + dy, 1.4 + min(3.0, g * tf * 0.15)
            self._bead(out, dp["x"], cy, rad, stretch)
        for tr in self.trickles:
            self._trickle(out, tr, f, g)
        return out

    def _trickle(self, out, tr, f, g):
        """이벤트마다: 잎 끝에서 물이 3프레임 동안 늘어졌다가 → 떨어지며 가늘고 긴 빛줄기로."""
        ages = (f - tr["events"]) % self.N
        w = max(1.2, (1.0 + 1.6 * tr["d"]) * self.res * tr["size"])
        for age in ages[ages < 14]:
            if age < 3:                                   # 잎 위를 미끄러져 끝에 매달려 늘어짐
                q = (age + 1) / 3
                self._streak(out, tr["x"] - 3 * w * (1 - q), tr["y"] - 8 * w * (1 - q), tr["x"],
                             tr["y"] + w * 2.5 * q, w, 0.35)
            else:                                         # 떨어짐 (중력 가속)
                tf = age - 3 + 1
                yy = tr["y"] + 0.5 * g * tf * tf + w * 3
                if yy - tr["y"] > tr["fall"]:
                    continue
                ln = max(5 * w, g * tf * 1.1)
                self._streak(out, tr["x"], yy - ln, tr["x"], yy, w * 0.9, 0.45)

    def _streak(self, out, xa, ya, xb, yb, w, glow):
        """가는 물줄기: 배경을 살짝 굴절(밝게)시키는 선."""
        x0, x1 = int(min(xa, xb) - w - 2), int(max(xa, xb) + w + 3)
        y0, y1 = int(min(ya, yb) - w - 2), int(max(ya, yb) + w + 3)
        if x0 < 0 or y0 < 0 or x1 >= self.W or y1 >= self.H:
            return
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        dx, dy = xb - xa, yb - ya
        L2 = dx * dx + dy * dy + 1e-6
        u = np.clip(((xx - xa) * dx + (yy - ya) * dy) / L2, 0, 1)
        dist = np.hypot(xx - (xa + u * dx), yy - (ya + u * dy))
        m = np.clip(1 - dist / w, 0, 1) * (0.4 + 0.6 * u)           # 아래로 갈수록 진함
        region = out[y0:y1, x0:x1]
        region += ((1.0 - region) * glow + 0.02) * m[..., None].astype(np.float32)

    def _bead(self, out, x, y, rad, stretch):
        """투명한 물방울: 뒤쪽 배경을 거꾸로·축소해 비추는 렌즈 + 아주 작은 반사광."""
        import cv2
        rx, ry = rad, rad * stretch
        x0, y0, x1, y1 = int(x - rx) - 2, int(y - ry) - 2, int(x + rx) + 3, int(y + ry) + 3
        if x0 < 0 or y0 < 0 or x1 >= self.W or y1 >= self.H or rx < 0.8:
            return
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        ex, ey = (xx - x) / rx, (yy - y) / ry
        rr = ex * ex + ey * ey
        inside = np.clip((1 - rr) * 3, 0, 1)
        mx = (x - ex * rx * 2.5).astype(np.float32)
        my = (y - ey * ry * 1.5 - ry * 2.5).astype(np.float32)
        lens = cv2.remap(out, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT) * 1.08
        region = out[y0:y1, x0:x1]
        region += (lens - region) * inside[..., None]
        hl = np.exp(-(((ex + 0.35) / 0.25) ** 2 + ((ey + 0.4) / 0.25) ** 2)) * 0.45
        region += hl[..., None].astype(np.float32)
