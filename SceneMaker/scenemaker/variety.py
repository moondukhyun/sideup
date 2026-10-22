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
INTERIOR_SCENES = {"candle_closeup", "candle_single", "candle_many", "cozy_parlor", "candle_rain_window", "living_fireplace_storm",
                   "living_fireplace_candles", "hearth_dog_cat", "candle_nook",
                   "living_fireplace_big_window", "living_fireplace_two_windows", "living_one_window_rain",
                   "living_fireplace_panorama", "bedroom_window_candles_cat", "study_candles_big_window",
                   "cabin_fireplace_window", "living_turntable_fireplace", "turntable_candles_windowless",
                   "turntable_window_rain", "living_coffee_fireplace_rain", "living_tea_fireplace_rain"}
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
                   "living_turntable_fireplace", "turntable_window_rain", "candle_rain_window", "living_coffee_fireplace_rain", "living_tea_fireplace_rain"}
DECOR_SCENES = PET_SCENES | {"living_coffee_fireplace_rain", "living_tea_fireplace_rain", "living_fireplace_candles", "turntable_candles_windowless", "turntable_window_rain", "cozy_parlor"}

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
    "a stack of books with plain covers, a ceramic teacup and a small brass clock",
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

# v11.23: 자연·한옥·텐트 장면도 이미지마다 풍경 분위기가 달라지게 하는 추가 축 (장면별로 어울리는 것만)
LIGHT_VIEWS = ["soft diffused overcast light", "light mist drifting between the trees", "a faint break of warm light through the clouds",
               "calm dim natural blue-hour light", "even flat natural daylight", "crisp clear natural light"]
FOREGROUNDS = ["mossy stones in the foreground", "wet fallen leaves on the ground", "puddles reflecting the sky", "damp leaves on the ground",
               "fresh wet grass in the foreground", "smooth wet pebbles in the foreground", "ordinary grass and small stones in the foreground"]
PALETTE_NATURE = ["natural muted greens", "calm cool grey-blue tones", "natural olive and brown tones", "soft grey-green tones", "warm earthy tones", "subtle desaturated tones"]
VEGETATION = ["dominant tall pine and fir trees", "mixed oak and maple trees", "slender birch trees with white trunks", "ordinary Korean mountain forest with oak and hornbeam trees",
              "tall zelkova and elm trees", "a plain mixed forest of conifers and deciduous trees"]
CAMP_PROPS = ["a camp lantern glowing warmly", "a pair of muddy hiking boots and a backpack", "an enamel mug on a folding table",
              "a hammock and a folding camp chair", "string lights under the tarp", "a small portable stove with a kettle"]
CANDLE_HOLDERS = ["a brass candle holder", "a rustic ceramic saucer", "a clear glass jar", "a wooden plate", "an antique iron holder", "a small stone dish"]
CANDLE_SURFACES = ["a dark wooden table", "a rough stone ledge", "a linen tablecloth", "a worn wooden shelf", "an old window sill", "a smooth slate slab"]
NATURE_FOREGROUND_SCENES = {"forest_path", "valley_stream", "forest_lake", "thunder_forest", "autumn_forest_path", "autumn_temple", "temple_path",
                            "bamboo_garden", "hydrangea_garden", "tent", "tent_by_stream", "tent_view_mountains", "tent_view_stream", "tent_view_valley",
                            "country_house", "cabin_window", "hanok_courtyard", "thatched_house", "rain_leaves", "jangdokdae"}
URBAN_SCENES = {"city_night", "cafe_window", "hanok_cafe"}
AUTUMN_SCENES = {"autumn_forest_path", "autumn_temple"}
VEGETATION_SCENES = {"forest_path", "valley_stream", "forest_lake", "thunder_forest", "tent", "tent_by_stream", "tent_view_mountains",
                     "tent_view_stream", "tent_view_valley", "cabin_window"}
TENT_SCENES = {"tent", "tent_by_stream", "tent_view_mountains", "tent_view_stream", "tent_view_valley", "tent_meadow", "tent_pine_grove", "tent_lakeside", "tent_car_camp"}
NATURE_FOREGROUND_SCENES |= TENT_SCENES
TERRAIN_FREE = {"tent", "tent_view_mountains", "tent_car_camp"}          # 풍경이 장면에 고정되지 않은 장면만 지형을 바꿈 (초원·솔숲·호수·개울 장면은 그대로)
TENT_EXTERIOR = {"tent", "tent_by_stream", "tent_meadow", "tent_pine_grove", "tent_lakeside"}          # 텐트를 밖에서 보는 장면
TENT_INSIDE = {"tent_view_mountains", "tent_view_stream", "tent_view_valley"}                          # 텐트 안에서 바깥을 보는 장면
# v11.24: 산속 캠핑 장면이 비슷비슷하다는 의견 → 지형·텐트·터·차양·안쪽 소품을 이미지마다 크게 바꿈
_TER_TAIL = ", individual tree crowns of different heights and greens, natural irregular details, no fantasy, no alpine peaks"
TERRAINS = [
    "ordinary Korean mountain scenery: rounded ridges covered with dense mixed oak, pine and other deciduous trees, ridgelines layered one behind another fading into mist and low clouds" + _TER_TAIL,
    "ordinary Korean mountain scenery: a broad open highland meadow of short grass with a few scattered trees, gentle rolling hills and a wide soft sky" + _TER_TAIL,
    "ordinary Korean mountain scenery: steep slopes of straight Korean red pines with pale granite boulders and rock outcrops among them" + _TER_TAIL,
    "ordinary Korean mountain scenery: a plantation of tall straight Korean pine trees with a clean forest floor and soft light between the trunks" + _TER_TAIL,
    "ordinary Korean mountain scenery: a deciduous forest of zelkova, maple and hornbeam with lighter green undergrowth and a narrow dirt track" + _TER_TAIL,
    "ordinary Korean mountain scenery: a wide valley with a small river and farm terraces far below, forested ridges receding into haze" + _TER_TAIL,
    "ordinary Korean mountain scenery: a granite ridgeline with sparse pines and bare rock slabs, low clouds drifting across the ridges" + _TER_TAIL,
    "ordinary Korean mountain scenery: a forest edge opening to a grassy clearing with birch and oak trees and a dry stream bed at the side" + _TER_TAIL,
    "ordinary Korean mountain scenery: terraced mountain slopes of oak forest with a few distant village roofs in the haze" + _TER_TAIL,
    "ordinary Korean mountain scenery: a mountain pass with rows of forested ridges, the nearest covered with tall pines" + _TER_TAIL,
]
TENT_KINDS = ["an olive green dome tent", "a beige canvas bell tent", "a grey-blue tunnel tent", "a sand-colored dome tent", "a dark green cabin tent",
              "a charcoal grey dome tent", "a khaki A-frame tent", "a cream colored cotton tent with a wooden pole frame"]
TENT_SITES = ["a wooden deck platform", "a flat gravel pad", "short natural grass", "a forest floor with pine needles", "flat rock slabs and gravel", "packed dirt with small stones"]
TENT_SHELTERS = ["a tarp stretched over the tent door", "the tent door extended into a small porch with poles", "a camp kitchen table with a gas stove beside it",
                 "a hammock between two trees next to the tent", "no tarp, just the tent and a camping chair", "a small folding table with an enamel mug and a lantern"]
TENT_INNER = ["a rolled sleeping bag and a lantern at the edge of the frame", "a folded wool blanket and a small lantern at the edge of the frame",
              "a pair of boots by the door and a headlamp", "a thermos and a mug on the tent floor", "a small book and a lantern near the door", "a sleeping mat and a backpack at the edge of the frame"]

CAMP_FRAMING = ["wide view", "eye-level view", "slightly low angle", "view slightly from the side", "closer view of the camp"]

CLOSEUP_CANDLES = [
    "a thick ivory pillar candle", "a tall hand-poured golden beeswax candle", "a thick white church candle with soft melted edges",
    "a chunky cream pillar candle with long wax drips", "a wide short candle in a clear glass jar", "an old thick candle burnt down in a brass dish",
    "a hand-dipped tapered candle in a heavy brass candlestick", "a rustic uneven handmade candle with a thick wick", "a smooth white candle on a small ceramic plate"]
CLOSEUP_BACKDROPS = [
    "behind it an old wooden bookshelf with worn book spines faintly visible", "behind it a tall antique clock and a brass lamp dimly visible",
    "behind it a stone fireplace with a dark mantel and framed pictures faintly visible", "behind it a hanging dried flower bundle and a woven basket dimly visible",
    "behind it a vintage record player and a stack of records faintly visible", "behind it a dark armchair with a knitted blanket and a small side table",
    "behind it an old wooden chest and a framed painting dimly visible", "behind it a shelf of ceramic jars and a teapot faintly glowing in the candlelight",
    "behind it a dark window with thick velvet curtains and a potted plant", "behind it a rustic wooden door and an iron lantern dimly visible",
    "behind it a writing desk with a leather journal and a fountain pen faintly visible", "behind it a rough plaster wall with a small mirror reflecting a tiny glow"]
CLOSEUP_SURFACES = ["on a dark wooden table", "on a rough stone ledge", "on a worn linen cloth", "on an old wooden shelf", "on a slate slab", "on a polished walnut desk"]
CLOSEUP_GLOWS = ["warm golden glow", "deep amber glow", "soft orange glow", "gentle honey-colored glow", "warm candlelit glow with deep shadows"]

# 씬 이름에 시간이 정해진 경우 시간 축을 쓰지 않음
# v11.24: 모닥불 캠핑 장면 — 비 없는 저녁·밤. 호수·텐트·장작·소품·계절을 이미지마다 다르게
CAMPFIRE_SCENES = {"campfire_lake", "campfire_kettle_lake", "campfire_tent_lake", "campfire_tent_kettle", "campfire_forest", "campfire_only"}
CAMPFIRE_AXES = {
    "time": ["dusk just after sunset", "blue hour twilight", "late evening with a last glow in the sky", "deep blue night with a few stars", "calm early night"],
    "season": ["late spring", "early summer", "late summer", "early autumn with a few yellowing leaves"],
    "air": ["clear still air", "faint thin mist low over the water", "calm clear air, the sky with soft thin clouds"],
}
CAMPFIRE_PITS = ["a ring of rounded grey river stones", "a ring of rough dark granite stones", "a simple black iron fire pit ring", "a shallow pit with a few flat stones around it"]
CAMPFIRE_WOODS = ["split pine logs with a few thin branches", "stacked oak logs crossing each other", "small split firewood in a neat teepee", "a mix of thick logs and thin kindling"]
CAMPFIRE_GROUND = ["fine gravel and pebbles", "short natural grass", "flat dry sand and small stones", "packed dirt with a few pine needles"]
CAMPFIRE_EXTRAS = ["a folding wooden camp chair beside the fire", "a canvas backpack leaning on a log", "a steel camping mug on a flat rock", "a stack of firewood under a small tarp",
                   "a hanging camp lantern on a pole (unlit)", "a blanket folded over a log seat", "an enamel cooking pot beside the fire", "nothing else, only the fire and the nature"]
CAMPFIRE_TENTS = ["an olive green dome tent", "a beige canvas bell tent", "a grey-blue dome tent", "a sand-colored tunnel tent", "a dark green cabin tent"]

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
    if scene_name in CAMPFIRE_SCENES:
        for axis, options in CAMPFIRE_AXES.items():
            picks[axis] = rng.choice(options)
        picks["pit"] = "campfire inside " + rng.choice(CAMPFIRE_PITS) + " with " + rng.choice(CAMPFIRE_WOODS)
        picks["ground"] = rng.choice(CAMPFIRE_GROUND) + " on the ground"
        picks["extra"] = rng.choice(CAMPFIRE_EXTRAS)
        if scene_name in ("campfire_tent_lake", "campfire_tent_kettle", "campfire_forest"):
            picks["tent"] = "the tent is " + rng.choice(CAMPFIRE_TENTS)
        picks["vegetation"] = rng.choice(VEGETATION)
        picks["terrain"] = rng.choice(TERRAINS)
        return ", ".join(v for k, v in picks.items() if k != "terrain"), picks
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
            if _scene_has_fireplace(scene_name):
                picks["fireplace"] = rng.choice(FIREPLACES)
    if scene_name not in INTERIOR_SCENES:                                      # v11.23: 자연·한옥·텐트 장면의 추가 변화
        if scene_name not in FIXED_TIME and scene_name not in URBAN_SCENES:
            picks["light"] = rng.choice(LIGHT_VIEWS)
        if scene_name in NATURE_FOREGROUND_SCENES:
            picks["foreground"] = rng.choice(FOREGROUNDS)
            if scene_name not in AUTUMN_SCENES:
                picks["palette"] = "color palette of " + rng.choice(PALETTE_NATURE)
        if scene_name in VEGETATION_SCENES and scene_name not in TENT_SCENES:
            picks["vegetation"] = rng.choice(VEGETATION)
        if scene_name in TENT_SCENES:
            picks["camp"] = rng.choice(CAMP_PROPS)
            if scene_name in TERRAIN_FREE:
                picks["terrain"] = rng.choice(TERRAINS)
            if scene_name in TENT_EXTERIOR:
                picks["tent"] = ("the tent is " + rng.choice(TENT_KINDS) + (" on " + rng.choice(TENT_SITES) if scene_name == "tent" else "")
                                 + (", with " + rng.choice(TENT_SHELTERS) if scene_name != "tent_pine_grove" else ""))
            elif scene_name in TENT_INSIDE:
                picks["inner"] = rng.choice(TENT_INNER)
    if scene_name == "candle_closeup":                                       # 큰 촛불 클로즈업: 양초 종류·받침·뒤에 보이는 소품·빛 색을 이미지마다 다르게
        picks["candle"] = rng.choice(CLOSEUP_CANDLES) + " " + rng.choice(CLOSEUP_SURFACES)
        picks["backdrop"] = rng.choice(CLOSEUP_BACKDROPS)
        picks["glow"] = rng.choice(CLOSEUP_GLOWS)
    if scene_name == "candle_single":
        picks["holder"] = rng.choice(CANDLE_HOLDERS) + " on " + rng.choice(CANDLE_SURFACES)
    elif scene_name in ("candle_many", "candle_nook"):                       # 촛불 여러 개: 놓인 곳·받침의 재질을 바꿔 분위기를 다르게 (개수는 건드리지 않음)
        picks["holder"] = "candles standing in " + rng.choice(["brass candle holders", "mismatched ceramic saucers", "clear glass jars",
                                                                "old iron holders", "small stone dishes", "wooden blocks"]) + " on " + rng.choice(CANDLE_SURFACES)
    text = ", ".join(v for k, v in picks.items() if k != "terrain")      # terrain 은 adapt_prompt 가 본문 문장을 바꿔 넣음
    return text, picks


def _scene_has_fireplace(scene_name):
    """장면 문장(기본·구도)에 벽난로가 들어 있는가 — 없는 장면에 벽난로를 만들어 넣지 않기 위해."""
    try:
        from .scenes import get_scene
        sc = get_scene(scene_name)
        blob = (sc.prompt + " " + " ".join(sc.variations)).lower()
        return "fireplace" in blob or "wood stove" in blob or "hearth" in blob
    except Exception:
        return False


def adapt_prompt(text, picks):
    """고른 벽난로 종류로 문장 속 '돌 벽난로' 표현을 바꿔서 방 분위기가 확 달라지게."""
    import re
    ter = picks.get("terrain")
    if ter:                                                                    # 모든 텐트·캠핑 장면에 똑같이 들어 있던 '둥근 능선' 문장을 고른 지형 문장으로 바꿔 풍경을 크게 다르게
        text = re.sub(r"ordinary Korean mountain scenery: rounded ridges.*?no alpine peaks", lambda m: ter, text, count=1, flags=re.S)
        picks = {k: v for k, v in picks.items() if k != "terrain"}
    fp = picks.get("fireplace")
    if not fp:
        return text
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
