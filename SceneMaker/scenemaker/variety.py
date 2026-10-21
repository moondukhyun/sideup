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
# v11.22: 실내 장면은 '한낮·여름' 같은 자연 풍경 문구가 섞이면 안 되므로 전용 축을 쓴다
INTERIOR_SCENES = {"candle_single", "candle_many", "cozy_parlor", "candle_rain_window", "living_fireplace_storm",
                   "living_fireplace_candles", "hearth_dog_cat", "candle_nook",
                   "living_fireplace_big_window", "living_fireplace_two_windows", "living_one_window_rain",
                   "living_fireplace_panorama", "bedroom_window_candles_cat", "study_candles_big_window",
                   "cabin_fireplace_window", "living_turntable_fireplace", "turntable_candles_windowless",
                   "turntable_window_rain"}
# 반려견이 나오는 장면: 작고 예쁜 강아지 품종을 매번 다르게 (큰 개는 몸이 합쳐지거나 머리가 2개로 그려지는 오류가 더 잦음)
PET_SCENES = {"living_fireplace_storm", "living_fireplace_big_window", "living_fireplace_two_windows", "living_one_window_rain",
              "living_fireplace_panorama", "bedroom_window_candles_cat", "study_candles_big_window", "cabin_fireplace_window",
              "living_fireplace_candles", "hearth_dog_cat", "living_turntable_fireplace", "turntable_window_rain"}
PET_BREEDS = ["a small fluffy white Maltese", "a tiny cute Pomeranian", "a small cream toy poodle puppy", "a small cute Shih Tzu",
              "a small cute Pembroke corgi puppy", "a small tan Cavalier King Charles spaniel", "a small cute Bichon Frise"]

INTERIOR_AXES = {
    "time": ["late at night", "deep midnight", "quiet night", "before dawn"],
    "mood": ["warm amber glow", "soft golden glow", "dim warm light with deep shadows", "gentle warm candlelit atmosphere"],
    "camera": ["wide view of the room", "eye-level view", "slightly low angle", "view from the doorway",
               "close view of the foreground"],
}

# v11.23: 같은 장면이라도 이미지마다 창밖 풍경·방 분위기·소품이 확 달라지게 하는 추가 축
WINDOW_INTERIOR = {"living_fireplace_storm", "living_fireplace_big_window", "living_fireplace_two_windows", "living_one_window_rain",
                   "living_fireplace_panorama", "bedroom_window_candles_cat", "study_candles_big_window", "cabin_fireplace_window",
                   "living_turntable_fireplace", "turntable_window_rain", "candle_rain_window"}
DECOR_SCENES = PET_SCENES | {"living_fireplace_candles", "turntable_candles_windowless", "turntable_window_rain", "cozy_parlor"}

OUTSIDE_VIEWS = [
    "outside the window a lush dense pine forest with every tree trunk, branch and needle sharply detailed, layered misty hills behind",
    "outside the window a beautiful birch and maple forest with finely detailed trunks and leaves, soft mist between the trees",
    "outside the window a quiet garden with a stone path, detailed shrubs and tall trees, a small pond and soft garden lanterns",
    "outside the window a calm lake and distant forested mountains in the blue night haze, finely detailed shoreline trees",
    "outside the window a wide meadow with tall grass and a line of detailed cypress and oak trees under a deep blue night sky",
    "outside the window a bamboo grove with tall slender stalks and fine bamboo leaves, glowing softly in the night",
    "outside the window a Korean village garden with a traditional stone wall, persimmon trees and distant dark mountain ridges",
    "outside the window a sparkling city skyline with detailed buildings and warm lights far below, out of focus",
    "outside the window a rocky mountain valley with tall conifers and a faint river, rich detailed foliage in the blue night light",
]
ROOM_STYLES = [
    "Scandinavian style room with pale oak floors, white plaster walls and soft wool textiles",
    "rustic log cabin style with warm honey-colored timber walls and a woven jute rug",
    "vintage 1970s style room with walnut paneling, a patterned wool rug and brass fixtures",
    "English country cottage style with floral cushions, painted wooden beams and a worn leather armchair",
    "Korean modern warm hanok-inspired interior with soft wood tones, paper lantern lamps and a cotton floor cushion",
    "mid-century modern room with teak furniture, a sheepskin rug and a sculptural floor lamp",
    "cozy bohemian style room with layered kilim rugs, many green houseplants and a macrame wall hanging",
    "elegant classic study style room with dark green walls, built-in bookshelves and a velvet sofa",
]
PROPS = [
    "a stack of books with plain covers, a steaming ceramic teacup and a small brass clock",
    "a potted fern, a woven basket with a knitted blanket and a framed forest painting",
    "a glass vase of dried flowers, a pile of cushions and an antique wooden globe",
    "a leather-bound journal with a fountain pen, a small wooden stool and a hanging plant",
    "a ceramic teapot on a tray, a folded plaid blanket and a small framed family photograph",
    "a row of old vinyl record sleeves, a monstera plant and a rattan chair",
    "a pair of reading glasses on an open book, a wool throw and a decorative lantern",
    "a bowl of fresh fruit, a wooden bookshelf with ceramic ornaments and a tall indoor plant",
]
FIREPLACES = [
    "a rough natural stone fireplace", "a red brick fireplace with a thick wooden mantel", "a whitewashed brick fireplace with a rustic beam mantel",
    "a black cast-iron wood stove with a glass door", "a marble fireplace surround with a carved mantel", "a handmade ceramic tile fireplace",
    "a curved plaster arch fireplace with a wooden shelf", "a river-stone floor-to-ceiling chimney fireplace"]
WALLS = [
    "warm beige limewash plaster walls", "deep forest green painted walls with white wainscoting", "exposed red brick walls",
    "honey-colored wooden plank walls", "soft floral wallpaper walls", "dark navy blue painted walls", "pale sage green walls with wood trim",
    "terracotta colored plaster walls", "cream colored walls with tall wood paneling", "dark chocolate brown walls"]
FLOORS = [
    "herringbone oak parquet floor", "dark walnut wide plank floor", "terracotta tile floor", "whitewashed pine plank floor",
    "polished concrete floor", "worn honey oak floor", "checkered black and white tile floor", "warm cherry wood floor"]
PALETTES = [
    "color palette of warm amber and brown", "color palette of deep green and brass gold", "color palette of navy blue and copper",
    "color palette of burgundy and cream", "color palette of earthy terracotta and olive", "color palette of muted teal and walnut",
    "color palette of soft grey and warm candle gold", "color palette of mustard yellow and chocolate"]
WINDOWS = [
    "tall arched white-framed windows", "black steel-framed windows with small square panes", "dark wooden sash windows with many panes",
    "wide French doors with glass panels", "a large picture window with a thick wooden frame", "a round-top window with white muntins"]
CURTAINS = [
    "heavy velvet curtains in a deep color tied back", "light white linen curtains", "sheer curtains with a patterned valance",
    "no curtains at all so the glass is fully visible", "thick plaid wool curtains"]
LAMPS = [
    "a floor lamp with a linen shade", "a brass table lamp with a green glass shade", "a hanging paper lantern", "a vintage glass pendant lamp",
    "an iron candelabra on the floor", "a ceramic base lamp with a pleated shade"]
CABINET_WOODS = [
    "teak", "dark walnut", "light oak", "mahogany", "painted white", "ebony black lacquered", "reclaimed pine", "cherry wood"]
CEILINGS = [
    "exposed dark wooden ceiling beams", "a plain white plaster ceiling", "a tongue-and-groove wooden ceiling", "a high vaulted ceiling with timber trusses"]
RUGS = ["a thick cream shag rug", "a worn Persian rug in deep reds", "a handwoven jute rug", "a soft grey wool rug",
        "a patterned kilim rug", "a plush sheepskin rug"]

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
    for axis, options in (INTERIOR_AXES if scene_name in INTERIOR_SCENES else AXES).items():
        if axis == "time" and scene_name in FIXED_TIME:
            continue
        if axis == "season" and scene_name in SEASON_OVERRIDE:
            options = SEASON_OVERRIDE[scene_name]
        choice = rng.choice(options)
        if axis == "rain" and rain_level:
            choice = RAIN_LEVELS[rain_level][0]
        picks[axis] = choice
    if scene_name in PET_SCENES:
        picks["pet"] = rng.choice(PET_BREEDS) + " dog sleeping peacefully"      # 작고 예쁜 강아지 품종을 매번 다르게
    if scene_name in INTERIOR_SCENES:                                          # v11.23: 창밖 풍경·방 스타일·소품·러그를 이미지마다 다르게
        if scene_name in WINDOW_INTERIOR:
            picks = {"outside": rng.choice(OUTSIDE_VIEWS), **picks}
        if scene_name in DECOR_SCENES:
            picks["style"] = rng.choice(ROOM_STYLES)
            picks["walls"] = rng.choice(WALLS)
            picks["floor"] = rng.choice(FLOORS)
            picks["ceiling"] = rng.choice(CEILINGS)
            picks["palette"] = rng.choice(PALETTES)
            picks["lamp"] = rng.choice(LAMPS)
            picks["props"] = rng.choice(PROPS)
            picks["rug"] = rng.choice(RUGS)
            picks["cabinet"] = f"furniture made of {rng.choice(CABINET_WOODS)}"
            if scene_name in WINDOW_INTERIOR:
                picks["window"] = rng.choice(WINDOWS)
                picks["curtains"] = rng.choice(CURTAINS)
            picks["fireplace"] = rng.choice(FIREPLACES)
    text = ", ".join(picks.values())
    return text, picks


def adapt_prompt(text, picks):
    """고른 벽난로 종류로 문장 속 '돌 벽난로' 표현을 바꿔서 방 분위기가 확 달라지게."""
    fp = picks.get("fireplace")
    if not fp:
        return text
    import re
    noun = fp.split(" ", 1)[1] if fp.startswith("a ") else fp
    def rep(m):
        return ("the " + noun) if m.group(1) == "the " else fp
    return re.sub(r"\b(a |the )(?:rough )?(?:natural )?stone fireplace", rep, text)
    for old in ("a rough stone fireplace", "a stone fireplace", "the stone fireplace", "a rough natural stone fireplace", "stone firep"):
        if old in text and old != "stone firep":
            text = text.replace(old, fp if not old.startswith("the ") else "the " + fp.split(" ", 1)[1], 1)
    return text


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
