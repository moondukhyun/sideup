"""장면용 환경음 합성 (v11.22): 벽난로 타닥거리는 소리 · 창문에 부딪히는 빗소리.

모든 소리는 '원형(circular)'으로 만들어서 끝과 처음이 정확히 이어진다 → 몇 시간을 반복해도 이음새가 없다.
(녹음한 빗소리가 있으면 그걸 쓰고, 벽난로 소리만 얹는 것도 가능 — cli 의 --audio 와 함께 자동 섞음)
numpy 와 표준 wave 모듈만 사용.
"""

import wave

import numpy as np

SR = 44100


def _band(x, sr, lo, hi, slope=2.0):
    """원형 FFT 밴드패스 (부드러운 경사). lo/hi = Hz."""
    n = len(x)
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / sr)
    f[0] = 1e-3
    g = (1.0 / (1.0 + (lo / f) ** slope)) * (1.0 / (1.0 + (f / hi) ** slope))
    return np.fft.irfft(spec * g, n)


def _slow_noise(rng, n, sr, hz, lo=0.5, hi=1.0):
    """초당 hz 번 정도 천천히 변하는 0~1 곡선 (원형)."""
    w = rng.normal(0, 1, n)
    w = _band(w, sr, hz * 0.2, hz, slope=3.0)
    w = (w - w.min()) / (w.max() - w.min() + 1e-9)
    return lo + (hi - lo) * w


def _place(buf, start, burst):
    n = len(buf)
    e = start + len(burst)
    if e <= n:
        buf[start:e] += burst
    else:
        k = n - start
        buf[start:] += burst[:k]
        buf[:e - n] += burst[k:]


def fire_crackle(seconds=90.0, sr=SR, seed=5):
    """모닥불·벽난로: 낮은 불 울림 + 작은 타닥 소리 + 가끔 크게 '탁' 터지는 소리."""
    n = int(seconds * sr)
    chans = []
    for ch in range(2):
        r = np.random.default_rng(seed * 7 + ch * 101)
        roar = _band(r.normal(0, 1, n), sr, 45, 420, 2.0) * _slow_noise(r, n, sr, 0.35, 0.45, 1.0)
        roar = roar / (np.std(roar) + 1e-9) * 0.32
        hiss = _band(r.normal(0, 1, n), sr, 2500, 9000, 2.0)
        ticks = np.zeros(n)
        count = int(seconds * 15)                                   # 작은 타닥 (초당 약 15번)
        starts = r.integers(0, n, count)
        for s in starts:
            ln = int(sr * r.uniform(0.0008, 0.006))
            tau = r.uniform(0.0006, 0.0025) * sr
            burst = r.normal(0, 1, ln) * np.exp(-np.arange(ln) / tau) * r.lognormal(-0.6, 0.8)
            _place(ticks, int(s), burst)
        pops = np.zeros(n)
        count = int(seconds * 0.8)                                  # 크게 탁 (초당 약 0.8번)
        for s in r.integers(0, n, count):
            ln = int(sr * r.uniform(0.012, 0.045))
            tau = r.uniform(0.004, 0.012) * sr
            body = _band(r.normal(0, 1, ln + 400), sr, 250, 3500, 1.5)[200:200 + ln]
            burst = body * np.exp(-np.arange(ln) / tau) * r.uniform(1.2, 3.2)
            _place(pops, int(s), burst)
        ticks = _band(ticks, sr, 1200, 8000, 1.5)
        ticks = ticks / (np.std(ticks) + 1e-9) * 0.30
        pops = pops / (np.std(pops) + 1e-9) * 0.16
        hiss = hiss / (np.std(hiss) + 1e-9) * 0.05 * _slow_noise(r, n, sr, 0.5, 0.4, 1.0)
        chans.append(roar + ticks + pops + hiss)
    return _norm(np.stack(chans, 1), -23.0)


def rain_window(seconds=90.0, sr=SR, seed=9, heavy=1.0):
    """창문·지붕에 떨어지는 빗소리: 부드러운 빗소리 바탕 + 유리에 톡톡 부딪히는 소리 + 먼 지붕 울림 + 바람에 세기 변화."""
    n = int(seconds * sr)
    chans = []
    for ch in range(2):
        r = np.random.default_rng(seed * 13 + ch * 57)
        wash = _band(r.normal(0, 1, n), sr, 500, 9500, 1.3)
        wash = wash / (np.std(wash) + 1e-9) * 0.40
        low = _band(r.normal(0, 1, n), sr, 70, 380, 2.0)
        low = low / (np.std(low) + 1e-9) * 0.22
        taps = np.zeros(n)
        count = int(seconds * 520 * heavy)
        for s in r.integers(0, n, count):
            ln = int(sr * r.uniform(0.0006, 0.003))
            tau = r.uniform(0.0004, 0.0014) * sr
            burst = r.normal(0, 1, ln) * np.exp(-np.arange(ln) / tau) * r.lognormal(-0.8, 0.7)
            _place(taps, int(s), burst)
        taps = _band(taps, sr, 1800, 9000, 1.4)
        taps = taps / (np.std(taps) + 1e-9) * 0.34
        plinks = np.zeros(n)
        for s in r.integers(0, n, int(seconds * 22 * heavy)):
            ln = int(sr * r.uniform(0.012, 0.03))
            tau = r.uniform(0.004, 0.010) * sr
            f0 = r.uniform(700, 2400)
            t = np.arange(ln) / sr
            burst = np.sin(2 * np.pi * f0 * t * (1 + 0.15 * np.exp(-t * 80))) * np.exp(-np.arange(ln) / tau) * r.uniform(0.15, 0.5)
            _place(plinks, int(s), burst)
        gust = _slow_noise(r, n, sr, 0.12, 0.72, 1.0)
        mix = (wash + low) * gust + taps * (0.6 + 0.4 * gust) + plinks * 0.5
        chans.append(mix)
    return _norm(np.stack(chans, 1), -21.0)


def _norm(x, rms_db):
    rms = np.sqrt(np.mean(x ** 2)) + 1e-9
    x = x * (10 ** (rms_db / 20.0) / rms)
    return 0.85 * np.tanh(x / 0.85)            # 갑자기 큰 '탁' 소리가 터져도 찌그러지지 않게 부드럽게 눌러 줌


def write_wav(path, x, sr=SR):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(pcm.shape[1])
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return path


def make(path, kind="fire", seconds=90.0, seed=5, heavy=1.0):
    """kind: fire | rain | fire+rain.  path: 저장할 wav."""
    parts = []
    if "fire" in kind:
        parts.append(fire_crackle(seconds, seed=seed))
    if "rain" in kind:
        parts.append(rain_window(seconds, seed=seed + 4, heavy=heavy))
    if not parts:
        raise ValueError(f"알 수 없는 소리 종류: {kind}")
    x = parts[0] if len(parts) == 1 else _norm(sum(parts), -20.0)
    return write_wav(path, x)
