"""실내 장면 AI 움직임 (v11.22): 벽난로 불·촛불·자는 반려동물을 Wan 2.2 가 만든 '진짜 영상 움직임'으로.

수식으로 흉내 낸 움직임(interior.py)보다 자연스러운 불꽃·숨쉬기를 얻기 위해, Wan 이 만든 클립에서
- 불꽃·촛불 영역: Wan 픽셀을 그대로 확대해 합성 (불꽃은 모양이 계속 바뀌므로 픽셀을 가져옴)
- 반려동물 영역: Wan 의 '움직임(흐름)'만 가져와 원본 고해상도 사진을 그 만큼만 움직임 (털 디테일·얼굴 유지)
나머지 방·창·가구는 건드리지 않아 원본 그대로 선명하다.

- 클립 여러 개(서로 다른 시드)를 이어 붙이면 반복 주기가 길어진다. 각 클립은 첫 프레임 = 끝 프레임 → 루프 이음새 없음
- Wan 과 원본의 색이 조금 다르면 영역 평균 색으로 맞추고, 거의 안 움직인 곳은 원본의 선명한 디테일을 되돌린다
"""

import numpy as np

WAN_FPS = 16


def _smooth(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


class _Region:
    """한 영역: kind 'paste' (Wan 픽셀) | 'flow' (Wan 흐름으로 원본을 움직임)."""

    def __init__(self, kind, box, weight, name):
        self.m = 1
        self.kind, self.box, self.weight, self.name = kind, box, weight[..., None].astype(np.float32), name
        self.data = []          # 클립마다: paste → (K+1,bh,bw,3) float16 / flow → (K+1,bh,bw,2) float16
        self.keep = []          # paste: (K+1,bh,bw,1)
        self.detail = None
        self.sig = []           # paste: 클립마다 프레임별 평균 밝기


class WanRoom:
    def __init__(self, bg, clips, N, fps, fire=None, flames=(), pets=(), max_flow=9.0, fire_speed=0.6):
        import cv2
        self.cv2 = cv2
        self.bg = bg
        self.H, self.W = bg.shape[:2]
        self.N, self.fps = N, fps
        self.clips = []
        for frames in clips:
            F = np.stack([np.asarray(f, dtype=np.float32) / 255.0 for f in frames])
            ramp = np.linspace(0, 1, len(F), dtype=np.float32)[:, None, None, None]
            F += ramp * (F[:1] - F[-1:])                      # 끝 프레임 = 첫 프레임 (루프 이음새 0)
            self.clips.append(np.clip(F, 0, 1))
        self.Ks = [len(c) - 1 for c in self.clips]
        self.total = float(sum(self.Ks))
        # 재생 속도: 클립을 '통째로 m 번' 재생해야 루프가 이음새 없이 이어진다. 불꽃·촛불은 느리게(목표 fire_speed 배속), 숨쉬기는 원래 속도로
        natural = self.total / float(WAN_FPS)
        loop_sec = N / float(fps)
        self.m_slow = max(1, int(round(fire_speed * loop_sec / natural)))
        self.m_pet = max(1, int(round(1.0 * loop_sec / natural)))
        self.speed_slow = self.m_slow * natural / loop_sec
        self.speed_pet = self.m_pet * natural / loop_sec
        self.regions = []
        h, w = self.clips[0].shape[1:3]
        self.sx, self.sy = w / float(self.W), h / float(self.H)
        if fire is not None:
            x0, y0, x1, y1 = [int(v) for v in fire["box"]]
            pad = int(24 * self.H / 1080.0)
            box = (max(0, x0 - pad), max(0, y0 - pad), min(self.W, x1 + pad), min(self.H, y1 + pad))
            wgt = cv2.GaussianBlur(cv2.dilate(fire["mask"][box[1]:box[3], box[0]:box[2]], np.ones((13, 13), np.uint8)),
                                   (0, 0), 6 * self.H / 1080.0)
            self._add_paste(box, np.clip(wgt * 1.4, 0, 1), "fire")
        for i, c in enumerate(flames):
            x0, y0, x1, y1 = c["box"]
            bh, bw = y1 - y0, x1 - x0
            yy, xx = np.mgrid[0:bh, 0:bw].astype(np.float32)
            edge = np.minimum(np.minimum(xx, bw - 1 - xx), np.minimum(yy, bh - 1 - yy)) / max(4.0, 0.35 * min(bh, bw))
            self._add_paste((x0, y0, x1, y1), _smooth(edge), f"candle{i}")
        for i, p in enumerate(pets):
            x0, y0, x1, y1 = p["box"]
            bh, bw = y1 - y0, x1 - x0
            yy, xx = np.mgrid[0:bh, 0:bw].astype(np.float32)
            wx = _smooth(np.minimum(xx, bw - 1 - xx) / (0.18 * bw))
            wy = _smooth(yy / (0.25 * bh))
            self._add_flow((x0, y0, x1, y1), (wx * wy), f"pet{i}", max_flow * self.H / 1080.0)

    # ---------------------------------------------------------------- 준비
    def _crop_wan(self, F, box):
        x0, y0, x1, y1 = box
        wx0, wy0 = int(x0 * self.sx), int(y0 * self.sy)
        wx1, wy1 = max(wx0 + 2, int(np.ceil(x1 * self.sx))), max(wy0 + 2, int(np.ceil(y1 * self.sy)))
        return F[:, wy0:wy1, wx0:wx1]

    def _add_paste(self, box, weight, name):
        cv2 = self.cv2
        x0, y0, x1, y1 = box
        bh, bw = y1 - y0, x1 - x0
        r = _Region("paste", box, weight, name)
        orig = self.bg[y0:y1, x0:x1]
        gain = None
        for ci, F in enumerate(self.clips):
            crop = self._crop_wan(F, box)
            up = np.stack([cv2.resize(f, (bw, bh), interpolation=cv2.INTER_CUBIC) for f in crop]).astype(np.float32)
            if gain is None:                                   # Wan 과 원본의 색 차이를 영역 평균으로 맞춤 (첫 클립 기준)
                wsum = r.weight.sum() + 1e-6
                om = (orig * r.weight).sum((0, 1)) / wsum
                wm = (up[0] * r.weight).sum((0, 1)) / wsum
                gain = np.clip(om / (wm + 1e-4), 0.75, 1.35).astype(np.float32)
            up = np.clip(up * gain, 0, 1)
            if r.detail is None:
                r.detail = (orig - up[0]).astype(np.float32)   # 원본만의 선명한 디테일·색
            change = np.abs(up - up[0]).mean(-1)
            keep = np.stack([np.clip(1.0 - cv2.GaussianBlur(c, (0, 0), 2) * 6.0, 0, 1) for c in change])[..., None]
            r.data.append(up.astype(np.float16))
            r.keep.append(keep.astype(np.float16))
            lum = (up * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1)
            r.sig.append((lum * r.weight[..., 0]).sum((1, 2)) / (r.weight.sum() + 1e-6))
        r.m = self.m_slow
        self.regions.append(r)

    def _add_flow(self, box, weight, name, max_px):
        cv2 = self.cv2
        x0, y0, x1, y1 = box
        bh, bw = y1 - y0, x1 - x0
        r = _Region("flow", box, weight, name)
        r.max_px = max_px
        for F in self.clips:
            crop = self._crop_wan(F, box)
            gray = [cv2.cvtColor((f * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY) for f in crop]
            flows = []
            for g in gray:
                fl = cv2.calcOpticalFlowFarneback(g, gray[0], None, 0.5, 3, 15, 3, 5, 1.2, 0)     # 프레임 k 의 점이 첫 프레임 어디서 왔나
                fl = cv2.GaussianBlur(fl, (0, 0), 2.0)
                full = cv2.resize(fl, (bw, bh), interpolation=cv2.INTER_LINEAR)
                full[..., 0] /= self.sx
                full[..., 1] /= self.sy                                                        # 확대한 만큼 픽셀 이동량도 키움
                flows.append(full)
            r.data.append(np.stack(flows).astype(np.float16))
        yy, xx = np.mgrid[0:bh, 0:bw].astype(np.float32)
        r.X, r.Y = xx, yy
        r.m = self.m_pet
        self.regions.append(r)

    # ---------------------------------------------------------------- 시간
    def _locate(self, f, m=1):
        """루프 프레임 f → (클립 번호, 클립 안 프레임 위치(실수)). m = 루프 동안 전체 클립을 재생하는 횟수."""
        p = ((f * m) % self.N) / float(self.N) * self.total
        for ci, K in enumerate(self.Ks):
            if p < K or ci == len(self.Ks) - 1:
                return ci, min(p, K - 1e-6)
            p -= K
        return 0, 0.0

    def _blend(self, arr, ci, pos):
        k = int(pos)
        t = pos - k
        a = arr[ci][k].astype(np.float32)
        if t < 1e-3:
            return a
        return a * (1 - t) + arr[ci][min(k + 1, len(arr[ci]) - 1)].astype(np.float32) * t

    def signal(self, name):
        """영역 이름(fire / candle0 ...)의 밝기 변화를 루프 프레임 수 N 짜리 신호로 (평균 0, 표준편차 1). 방 안 불빛 일렁임에 씀."""
        r = next((x for x in self.regions if x.name == name and x.kind == "paste"), None)
        if r is None:
            return None
        s = np.array([self._blend_sig(r, f) for f in range(self.N)], np.float32)
        s -= s.mean()
        return s / (s.std() + 1e-6)

    def _blend_sig(self, r, f):
        ci, pos = self._locate(f, r.m)
        k = int(pos)
        t = pos - k
        a = r.sig[ci][k]
        return a if t < 1e-3 else a * (1 - t) + r.sig[ci][min(k + 1, len(r.sig[ci]) - 1)] * t

    # ---------------------------------------------------------------- 한 프레임
    def apply(self, out, f):
        cv2 = self.cv2
        for r in self.regions:
            ci, pos = self._locate(f, r.m)
            x0, y0, x1, y1 = r.box
            reg = out[y0:y1, x0:x1]
            if r.kind == "paste":
                cur = self._blend(r.data, ci, pos)
                keep = self._blend(r.keep, ci, pos)
                wan = np.clip(cur + r.detail * keep, 0, 1)
                reg[...] = reg * (1 - r.weight) + wan * r.weight
            else:
                fl = self._blend(r.data, ci, pos) * r.weight
                mag = np.sqrt((fl ** 2).sum(-1, keepdims=True))
                fl = fl * np.minimum(1.0, r.max_px / (mag + 1e-6))       # Wan 이 동물을 크게 움직여도 숨쉬는 정도만
                reg[...] = cv2.remap(reg, (r.X + fl[..., 0]).astype(np.float32), (r.Y + fl[..., 1]).astype(np.float32),
                                     cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        return out
