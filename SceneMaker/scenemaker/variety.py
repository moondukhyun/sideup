"""영상마다 배경이 겹치지 않게: 자동 다양화 + 사용 기록(중복 경고).

- 자동 다양화: 같은 씬이라도 시간대·계절·비의 양·구도를 시드마다 다르게 고르고,
  빗줄기 합성 값(양·각도·안개)도 조금씩 흔든다.
- 사용 기록: 영상에 쓴 배경의 지문(dHash + 색 분포)을 used_backgrounds.json 에 저장하고,
  새 배경이 기존 것과 비슷하면 경고한다.
"""

import json
import random
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

from .config import ROOT

# ---------- 자동 다양화 ----------
AXES = {
    "time": ["early morning", "late morning", "midday", "afternoon", "late afternoon", "dusk"],
    # 단풍은 AI 가 조화처럼 그리는 경향이 있어 제외 (2026-09-29)
    "season": ["late spring", "early summer", "midsummer monsoon season", "late summer"],
    # v11.21: 'rain/drizzle/downpour' 단어를 쓰면 AI 가 빗줄기를 이미지에 그려 넣어 영상에서 고정된 줄로 남는다.
    #         비는 영상 단계에서 움직이는 빗줄기로 따로 만들므로, 이미지는 '젖은 느낌'만 묘사한다.
    "rain": ["damp misty air, wet surfaces", "wet glistening surfaces, soft overcast", "soaked dark wet surfaces",
             "freshly wet leaves and stones", "glossy wet leaves, cloudy sky"],
    "camera": ["wide view", "eye-level view", "slightly low angle", "view from a sheltered spot",
               "looking down a path", "close view of the foreground"],
}
# 씬 이름에 시간이 정해진 경우 시간 축을 쓰지 않음
FIXED_TIME = {"forest_night", "night_park", "city_night"}

RAIN_JITTER = {"intensity": 0.25, "angle": 4.0, "fog": 0.06, "brightness": 0.08}


# 녹음한 빗소리 세기에 화면을 맞추기 위한 단계 (프롬프트 문구, 빗줄기 양 배율)
RAIN_LEVELS = {
    "light": ("damp misty air, slightly wet surfaces", 0.55),
    "steady": ("wet glistening surfaces, overcast sky", 1.0),
    "heavy": ("soaked dark wet surfaces, dark heavy overcast sky", 1.6),
}


# 씬별로 계절 후보를 고정 (가을 씬에 여름이 섞여 '초록 나무에 주황 덩어리를 붙인' 그림이 되던 문제 방지)
SEASON_OVERRIDE = {
    "autumn_forest_path": ["mid autumn", "late autumn"],
    "autumn_temple": ["mid autumn", "late autumn"],
}


def diversify(scene_name, seed, rain_level=None):
    """시드로 결정되는 다양화 문구와 선택값 (같은 시드 = 같은 결과).
    rain_level 을 주면 비의 세기는 고정 (녹음한 빗소리에 맞춤)."""
    rng = random.Random(f"{scene_name}:{seed}")
    picks = {}
    for axis, options in AXES.items():
        if axis == "time" and scene_name in FIXED_TIME:
            continue
        if axis == "season" and scene_name in SEASON_OVERRIDE:
            options = SEASON_OVERRIDE[scene_name]
        choice = rng.choice(options)
        if axis == "rain" and rain_level:
            choice = RAIN_LEVELS[rain_level][0]
        picks[axis] = choice
    text = ", ".join(picks.values())
    return text, picks


def jitter_rain(base, seed, rain_level=None):
    """빗줄기 설정을 ±범위 안에서 흔든 dict (씬 기본값 기준). rain_level 이면 양을 그 단계로."""
    rng = random.Random(f"rain:{seed}")
    out = {}
    if rain_level:
        base = {**base, "intensity": base.get("intensity", 1.0) * RAIN_LEVELS[rain_level][1]}
    for k, amp in RAIN_JITTER.items():
        if k in base and base[k] is not None:
            v = base[k] + rng.uniform(-amp, amp) * (base[k] if k == "intensity" else 1)
            out[k] = round(max(0.0, v), 3)
    return out


# ---------- 사용 기록 ----------
REGISTRY = ROOT / "used_backgrounds.json"
SIMILAR = 60      # dHash(256비트) 거리: 이하이면 '비슷'
VERY_SIMILAR = 35  # 이하이면 '거의 같음'


def fingerprint(img):
    img = img.convert("RGB")
    g = np.asarray(img.convert("L").resize((17, 16), Image.BILINEAR), dtype=np.int16)
    dhash = (g[:, 1:] > g[:, :-1]).flatten()
    small = np.asarray(img.resize((8, 8), Image.BILINEAR), dtype=np.float32) / 255.0
    return {"dhash": "".join("1" if b else "0" for b in dhash), "colors": small.round(3).flatten().tolist()}


def _distance(a, b):
    ham = sum(x != y for x, y in zip(a["dhash"], b["dhash"]))
    col = float(np.abs(np.array(a["colors"]) - np.array(b["colors"])).mean())
    # 색 분포 차이를 비트 거리 단위로 환산해 더함 (색이 크게 다르면 구도가 비슷해도 다른 영상)
    return ham + col * 200


def load_registry():
    if REGISTRY.exists():
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    return []


def save_registry(entries):
    REGISTRY.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")


def find_similar(img, limit=3):
    """사용 기록에서 비슷한 배경 (거리 오름차순)."""
    fp = fingerprint(img)
    scored = sorted(((_distance(fp, e["fp"]), e) for e in load_registry()), key=lambda x: x[0])
    return [(round(d, 1), e) for d, e in scored[:limit] if d <= SIMILAR]


def warn_similar(img, label=""):
    hits = find_similar(img)
    for d, e in hits:
        level = "거의 같음" if d <= VERY_SIMILAR else "비슷함"
        print(f"  ⚠ {label} 이전에 사용한 배경과 {level} (거리 {d}): {e['path']} [{e.get('note', '')}]")
    return hits


def mark_used(path, note=""):
    path = Path(path).resolve()
    entries = [e for e in load_registry() if e["path"] != str(path)]
    entries.append({"path": str(path), "note": note, "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "fp": fingerprint(Image.open(path))})
    save_registry(entries)
    return len(entries)
