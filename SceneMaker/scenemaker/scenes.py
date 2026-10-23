"""somnia-forest 씬 프리셋: SD 프롬프트 + 빗줄기 오버레이 기본값."""

import random
from dataclasses import dataclass, field

STYLE = (
    "cinematic photograph, photorealistic, highly detailed, soft diffused light, "
    "muted desaturated green and teal tones, calm peaceful sleepy atmosphere, "
    "depth of field, film grain, 35mm"
)

# AI 티를 줄인 자연스러운 사진 톤 — 완벽하지 않되, 색은 생생하고 질감은 선명하게
QWEN_REALISM = ("unedited real photograph taken with a full-frame camera and a 35mm lens, natural muted true-to-life colors, "
                "realistic scale and proportions, an ordinary real place, empty scenery, calm still air, no stylization")
QWEN_NEGATIVE = ("person, people, human, man, woman, figure, fantasy, painting, illustration, digital art, CGI, 3d render, concept art, "
                 "oversaturated, neon, glowing light beams, magical, surreal, jungle, falling rain, rain streaks, heavy downpour, storm, "
                 "hdr, over-sharpened, plastic")

NATURAL_STYLE = (
    "natural candid photograph, realistic unedited look, true-to-life rich colors, "
    "natural fine detail and texture, natural lighting, real place, imperfect natural composition"
)
NATURAL_NEGATIVE = (
    "hyperrealistic, 8k, cinematic, dramatic lighting, perfect, symmetrical, oversharpened, HDR, "
    "glossy, plastic, CGI, perfectly round droplets, washed out, faded, dull colors, flat, soft focus"
)
NATURAL_COMFY = {"cfg": 3.5, "checkpoint": "RealVisXL_V5.0_fp16.safetensors"}
NATURAL_POST = {"grain": 0.012, "saturation": 1.04}     # 흐림(soften) 없음, 채도 살짝 보강

# v11.21: 빗줄기·떨어지는 빗방울이 이미지에 그려지면 영상에서 고정된 줄로 남는다 → 이미지에는 비를 그리지 않는다
NO_RAIN_NEGATIVE = (
    "rain streaks, falling rain, rain lines, diagonal rain lines, raindrops in the air, visible rain, "
    "heavy rain, downpour, drizzle, streaks of water in the air, motion blur streaks"
)

NEGATIVE = (
    NO_RAIN_NEGATIVE + ", "
    "people, person, human, animal, text, watermark, logo, signature, frame, border, "
    "cartoon, anime, illustration, painting, 3d render, oversaturated, harsh light, "
    "lowres, blurry, jpeg artifacts, deformed, bad composition, sunny, bright blue sky"
)

# v11.22: 아늑한 실내 (촛불·벽난로·창밖 폭우·반려동물). 실내 불빛이 비 오는 날 색보정으로 차갑게 변하지 않게 grade 를 낮춘다
INTERIOR_STYLE = (
    "cozy interior photograph, warm low-key lighting, soft golden glow, deep soft shadows, realistic, "
    "natural fine detail, shallow depth of field, film grain, 35mm, all objects plain with no writing, labels or logos, sharp focus, highly detailed, crisp, every window has perfectly dry, smooth, crystal clear glass, calm still air outside the window"
)
INTERIOR_NEGATIVE = (
    "bright daylight, overexposed, harsh flash, cold fluorescent light, messy clutter, cartoon, illustration, 3d render, "
    "oversaturated, text, watermark, melted wax, floating candles, extra limbs, deformed animal, people"
)
INTERIOR_RAIN = {"sway": False, "wet": 0.0, "wet_ground": 0.0, "water_rain": 0.0, "splashes": False, "wan_ok": False,
                 "grade": 0.3, "darken": 0.0, "bloom": 1.3, "fog": 0.0,
                 "veil": 0.0}                    # 창밖 먼 비 '장막'(1초마다 위에서 아래로 훑는 검은·뿌연 띠)을 모든 실내 창 장면에서 끔

# 원시림·판타지 숲 방지 (실제 한국 산은 가는 참나무·소나무 + 낙엽 흙길)
FOREST_NEGATIVE = (
    "moss, mossy, ferns, primeval forest, ancient forest, rainforest, jungle, fantasy, fairy tale, "
    "overgrown, giant trees, redwood, twisted roots, dry ground, dusty, barren, leafless trees"
)

# 가을 전용 스타일 (2026-10-01 Cowork 요청): NATURAL_* 를 쓰지 않는다.
# 'true-to-life rich colors' / 'dull colors, washed out, faded' 가 단풍을 형광·인조 잎처럼 키우던 원인.
# 비 오는 날 실제 단풍은 젖어서 어둡고 차분 → muted 를 긍정문으로 명시.
AUTUMN_STYLE = (
    "natural candid photograph, unedited, overcast soft diffused light, wet leaves darkened by rain, "
    "muted autumn colors, natural fine detail"
)
AUTUMN_NEGATIVE = (
    "plastic leaves, fake foliage, artificial plant, neon colors, oversaturated, uniform color, "
    "flat colored blobs, postcard, tourism photo, HDR, glossy, sunny, golden hour, perfect leaves, "
    "people, text, watermark, cartoon, illustration, painting, 3d render"
)
AUTUMN_POST = {"autumn_mute": 1.0, "saturation": 0.95, "grain": 0.012}
AUTUMN_COMFY = {"upscale_blend": 0.45}       # GAN 업스케일 질감 완화 (기본 0.25)

# 한옥 LoRA (학습 후 ComfyUI/models/loras 에 생기면 자동 적용). 트리거 단어(파일명)는 프롬프트에 자동 추가
# "A|B" = 설치된 것 중 앞쪽 우선 (한국 풍경 LoRA 가 있으면 그것, 없으면 한옥 LoRA)
# 씬별로 비교해 더 나은 쪽을 사용 (2026-09-28 v1/v3 비교):
#   한국 풍경 v3(somnia_korea) — 한옥 마당·초가집·장독대에서 더 사실적
#   한옥 v1(somnia_hanok_v1)  — 처마·한옥 카페에서 더 깔끔
KOREA_LORA = "somnia_korea.safetensors:0.8|somnia_hanok_v1.safetensors:0.8"
HANOK_LORA = "somnia_hanok_v1.safetensors:0.8|somnia_korea.safetensors:0.8"
HANOK_BASE = "Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors"

# 한옥이 일본/중국식으로 섞이는 것을 막는 네거티브
HANOK_NEGATIVE = (
    "japanese, japan, tatami, shoji, torii, pagoda, chinese, china, red lacquer, "
    "modern apartment, aluminum window frame, modern building, skyscraper, tower, city skyline, "
    "air conditioner, power lines"
)


import re

# 프롬프트의 비 표현 → '젖은 흐린 날' 표현 (Z-Image 처럼 네거티브 프롬프트가 안 먹는 모델에서도 빗줄기가 안 그려지게)
_DRY_RULES = [
    (r"dark stormy night outside", "a deep blue night outside"),
    (r"torrential rain", "very dark stormy overcast"),
    (r"heavy summer thunderstorm", "dark stormy summer evening"),
    (r"rain dripping from", "wet"),
    (r"raindrop ripples on the water surface", "calm water surface"),
    (r"raindrop ripples on the water", "calm water surface"),
    (r"raindrops on the lids", "wet lids"),
    (r"rain on the glass", "clear window glass"),
    (r"water droplets on the window glass", "clear window glass"),
    (r"rain-soaked", "soaked"),
    (r"darkened by rain", "darkened by moisture"),
    (r"\bin (?:the |a )?(?:[a-z]+ ){0,3}rain\b", "on a wet overcast day"),
    (r"\bthunderstorm\b", "overcast evening"),
    (r"\bstormy\b", "overcast"),
    (r"\bstorm\b", "overcast"),
    (r"\brainy\b", "wet overcast"),
    (r"\b(?:light |steady |heavy |gentle )?(?:rain|drizzle|downpour)\b", "wet air"),
]


CAMPFIRE_RAIN = {"free_fire": True, "brightness": 0.45, "wet": 0.0, "wan_hint": "the lake surface moves very slightly in the breeze, the campfire flames flicker, no rain"}
CAMPFIRE_NEGATIVE = ("steam, vapor, steam rising from the kettle or the mug, wisps of smoke above the kettle, mist above the kettle, people, person, human, man, woman, figure, rain, raindrops, rain streaks, wet ground, puddles, snow, fog bank, "
                     "jungle, rainforest, fantasy, fairy tale, painting, illustration, 3d render, oversaturated, neon, glowing magical light, "
                     "cartoon flames, fireworks, sparks flying everywhere, huge bonfire tower, bonfire pile, house, cabin, buildings, text, logo, watermark")


def dry_prompt(text):
    """프롬프트에서 비·빗줄기를 암시하는 표현을 젖은 표면·흐린 날 표현으로 바꾼다."""
    for pat, rep_ in _DRY_RULES:
        text = re.sub(pat, rep_, text, flags=re.I)
    return text


@dataclass
class Scene:
    name: str
    title: str
    prompt: str
    variations: list = field(default_factory=list)
    rain: dict = field(default_factory=dict)
    negative: str = ""        # 씬 전용 네거티브 (NEGATIVE 뒤에 추가)
    lora: str = ""            # "파일명:강도" — ComfyUI 에 설치돼 있을 때만 적용
    style: str = ""           # 비우면 STYLE, 지정하면 대체 (예: NATURAL_STYLE)
    comfy: dict = field(default_factory=dict)   # 씬별 생성 설정 덮어쓰기 (cfg, checkpoint 등)
    post: dict = field(default_factory=dict)    # 후처리: grain, soften, saturation
    animals: bool = False     # 반려동물이 나오는 씬: 기본 네거티브의 'animal' 을 뺀다

    def build_prompt(self, rng: random.Random, extra: str = "", variant=None):
        parts = [self.prompt]
        if self.variations:
            # variant 를 주면 번호 순서대로 구도를 고른다 → 한 번에 여러 장을 만들 때 구도가 서로 겹치지 않음
            parts.append(self.variations[variant % len(self.variations)] if variant is not None else rng.choice(self.variations))
        if extra:
            parts.append(extra)
        parts.append(self.style or STYLE)
        base_neg = NEGATIVE.replace("people, person, human, animal, ", "people, person, human, ") if self.animals else NEGATIVE
        negative = f"{base_neg}, {self.negative}" if self.negative else base_neg
        return dry_prompt(", ".join(parts)), negative


SCENES = {
    s.name: s
    for s in [
        # ---------- 한국 씬 (채널 인기 주제) ----------
        Scene(
            "hanok_courtyard",
            "한옥 마당 빗소리",
            "traditional Korean hanok house courtyard (madang) in the rain, dark grey giwa clay roof tiles "
            "with gently upturned curved eaves, wooden pillars on stone foundations, "
            "hanji paper lattice doors (changhoji), wet packed-earth courtyard with puddles, "
            "low stone and clay wall topped with roof tiles, plain courtyard without fruit trees, Joseon dynasty architecture",
            [
                "onggi earthenware jars on a stone platform (jangdokdae), overcast grey sky",
                "view from the wooden maru veranda looking out at the courtyard",
                "evening, warm light glowing through the hanji paper doors",
                "a few low green shrubs by the stone wall, lush green summer",
            ],
            {"intensity": 1.0, "angle": 4.0, "fog": 0.08},
            negative=HANOK_NEGATIVE,
            lora=KOREA_LORA,
            comfy={"checkpoint": HANOK_BASE, "family": "zimage"},   # 한옥 건축 = Z-Image (SDXL 선택 시 LoRA 기준 모델)
        ),
        Scene(
            "hanok_eaves",
            "한옥 처마 끝 빗물",
            "close view under the eaves of a Korean hanok, rain dripping from dark giwa roof tile edges, "
            "curved wooden rafters (seokkarae), wooden maru floor, a plain flat stepping stone at the edge of the veranda with nothing on it, "
            "green garden beyond, Joseon dynasty architecture",
            [
                "soft grey rainy afternoon light",
                "twilight, warm lamp light inside the room behind hanji doors",
                "misty mountains in the distance",
            ],
            {"intensity": 0.9, "angle": 2.0, "fog": 0.05, "brightness": 0.5},
            negative=HANOK_NEGATIVE,
            lora=HANOK_LORA,
            comfy={"checkpoint": HANOK_BASE, "family": "zimage"},   # 한옥 건축 = Z-Image (SDXL 선택 시 LoRA 기준 모델)
        ),
        Scene(
            "hanok_cafe",
            "한옥 카페 창가",
            "inside a cozy Korean hanok cafe on a rainy day, looking out a large window with wooden lattice frame, "
            "exposed wooden ceiling beams, cup of tea and a book on a low wooden table, "
            "rain on the glass, green garden and tiled roofs outside",
            [
                "warm amber interior light, cool grey outside",
                "night, soft pendant lamp, city lights far away",
            ],
            {"intensity": 0.7, "brightness": 0.3, "fog": 0.0, "splashes": False, "darken": 0.03, "window": True},
            negative=HANOK_NEGATIVE,
            lora=HANOK_LORA,
            comfy={"checkpoint": HANOK_BASE, "family": "zimage"},   # 한옥 건축 = Z-Image (SDXL 선택 시 LoRA 기준 모델)
        ),
        Scene(
            "thatched_house",
            "초가집 빗소리",
            "old Korean thatched roof farmhouse in the summer rain, thick rounded rice straw roof with no tiles, "
            "the straw is made of countless individual weathered bundles with visible straw strands and darker aged patches, "
            "rough mud and clay walls with fine cracks and uneven plaster, weathered wooden door frames with visible wood grain, "
            "dirt yard with puddles, brushwood fence, green hills behind, natural uneven realistic details like a real documentary photograph",
            [
                "onggi earthenware jars beside the house",
                "view from the narrow wooden veranda under the straw eaves",
                "a big old tree beside the house, overcast",
                "a rice paddy in front of the house: rice plants growing in neat evenly spaced rows, each plant a clump of thin arching green leaf blades, shallow water between the rows",
            ],
            {"intensity": 1.0, "angle": 4.0, "fog": 0.1},
            negative=HANOK_NEGATIVE,
            lora=KOREA_LORA,
            comfy={"checkpoint": HANOK_BASE, "family": "zimage"},   # v11.22: SDXL 은 짚·벽 질감이 번져 AI 티가 남 → 한옥 장면처럼 Z-Image
        ),
        Scene(
            "jangdokdae",
            "장독대 빗소리",
            "many Korean onggi earthenware jars on a stone platform in the rain, wet glossy dark brown jars, "
            "raindrops on the lids, stone wall topped with roof tiles behind, green garden, "
            "each jar has its own slightly different shape, size and glaze with natural scratches and uneven color, "
            "real documentary photograph with natural fine texture",
            [
                "hanok eaves visible at the top",
                "green ivy on the stone wall behind the jars",
                "close view of a few jars, shallow depth of field",
            ],
            {"intensity": 0.9, "angle": 3.0, "fog": 0.05},
            negative=HANOK_NEGATIVE,
            lora=KOREA_LORA,
            comfy={"checkpoint": HANOK_BASE, "family": "zimage"},   # v11.22: Z-Image (한옥 장면과 동일)
        ),
        Scene(
            "country_house",
            "여름 시골집 마루",
            "old Korean countryside house in summer, view from a worn wooden maru floor, sharp focus and crisp fine detail, "
            "weathered wood grain, cracked clay plaster walls, corrugated tin or slate roof edge, vegetable garden and green hills, "
            "a small round Korean wooden table (soban) and an old electric fan, nostalgic rural Korea, "
            "real documentary photograph with natural uneven details",
            [
                "a rice paddy in front of the house: rice plants growing in neat evenly spaced rows, each plant a clump of thin arching "
                "green leaf blades, shallow water between the rows reflecting the overcast sky, overcast",
                "late afternoon, soft light, cicada summer mood, a rice paddy with rows of individual rice plants in the distance",
                "a traditional Korean flat square floor cushion (bangseok) of quilted cotton fabric with a plain muted pattern lying flat on the wooden floor",
                "a bamboo hand fan and sliced watermelon on a small round wooden table (soban) on the maru floor",
            ],
            {"intensity": 1.0, "angle": 5.0, "fog": 0.1},
            negative=HANOK_NEGATIVE + ", western sofa cushion, decorative throw pillow, plush pillow, blurry house, soft focus, painted look",
            comfy={"family": "zimage"},   # v11.22: SDXL 은 집이 흐리고 논이 AI 같음 → Z-Image
        ),
        Scene(
            "cafe_window",
            "조용한 카페 창가에서 보는 비",
            "inside a quiet cozy small Korean cafe on a rainy day, view from a wooden table next to a large clean "
            "glass window, a ceramic cup of coffee and a small plant on the table, warm soft interior light, "
            "outside the window a rainy street, completely out of focus, soft blurry bokeh shapes and muted colors, "
            "shallow depth of field, grey rainy daylight, no people, clear glass without water drops",
            [
                "late afternoon, warm pendant lamp inside, cool grey outside",
                "evening, street lights starting to glow outside",
                "wooden window frame, a few books on the windowsill",
                "blurry street lights and car lights outside",
            ],
            {"intensity": 0.7, "brightness": 0.35, "fog": 0.0, "splashes": False, "darken": 0.0, "window": True},
            negative="people, person, customers, text, signage, logo, water droplets on glass",
        ),
        Scene(
            "night_park",
            "가로등 아래 밤 공원",
            "empty city park at night in the rain, warm street lamps glowing, wet paved path reflecting lights, "
            "wooden bench under trees, quiet and calm",
            [
                "light fog around the lamps",
                "autumn leaves on the wet ground",
                "green summer trees, puddles",
            ],
            {"intensity": 1.1, "angle": 6.0, "brightness": 0.6, "fog": 0.12, "darken": 0.05},
        ),
        Scene(
            "city_night",
            "도심 밤거리 빗소리",
            "quiet city street at night in the rain, wet asphalt reflecting colorful lights, "
            "small shops with warm lit windows and plain fabric awnings, softly glowing colored light strips and round lamps, "
            "no signboards and no writing anywhere, every storefront and wall is smooth and blank, parked cars, no people",
            [
                "narrow alley, shallow depth of field, distant lights as soft bokeh",
                "view from a high window, city lights blurred by rain",
            ],
            {"intensity": 1.0, "angle": 5.0, "brightness": 0.6, "fog": 0.08, "darken": 0.04},
            negative="readable text, letters, hangul, kanji, chinese characters, typography, signage text, signboard, billboard, banner, neon sign with letters, logo, poster with text",
        ),
        Scene(
            "bamboo_garden",
            "대나무 정원 물소리",
            "tranquil bamboo garden in gentle rain, stone water basin with bamboo spout (tsukubai), "
            "moss covered stones, tall green bamboo grove, wet stone path",
            [
                "soft misty morning light",
                "small wooden pavilion in the background",
            ],
            {"intensity": 0.6, "angle": 2.0, "fog": 0.12, "brightness": 0.45, "stream": 1.0, "wet": 0.9,
             "wan_hint": "water pours continuously from the bamboo spout into the stone basin, ripples spreading across the water"},
        ),
        Scene(
            "hydrangea_garden",
            "빗물 머금은 수국 정원",
            "garden full of blooming blue and purple hydrangeas in the rain, water droplets on petals and leaves, "
            "stone path, lush green, soft overcast light",
            [
                "old stone wall and a wooden gate",
                "close up hydrangeas, shallow depth of field",
            ],
            {"intensity": 0.8, "angle": 3.0, "fog": 0.06},
        ),
        Scene(
            "rain_leaves",
            "나뭇잎에 내리는 비",
            "branches of a leafy tree in a backyard on a rainy day, photographed with a telephoto lens from several meters away, "
            "dense foliage with hundreds of small leaves, each leaf only about the size of a thumb, leaves of many different sizes, "
            "shades of green and slight yellowing at the edges, at different angles and depths, overlapping each other with soft shadows, "
            "fine natural leaf texture with visible veins, some leaves with small insect holes, brown spots and torn edges, "
            "wet but without large water droplets, distant leaves softly out of focus, "
            "real documentary photograph, not a close-up of a single leaf",
            [
                "zelkova tree branches, small serrated leaves",
                "cherry tree branches with small green leaves",
                "a hornbeam or oak tree with many small oval leaves",
                "grape vine on an old wooden trellis, leaves partly hidden behind the wooden slats",
                "dense shrubs and small-leaved tree branches along a stone wall",
            ],
            {"intensity": 0.9, "angle": 3.0, "brightness": 0.45, "fog": 0.0, "splashes": False,
             "darken": 0.04},
            negative="fruit, berries, flowers, macro close-up, one huge leaf filling the frame, giant leaves, maple leaves, "
                     "all leaves identical, perfectly uniform leaves, plastic looking leaves, painted look",
            comfy={"family": "zimage"},   # v11.22: SDXL 은 잎이 크고 매끈해 AI 티 → Z-Image
        ),
        Scene(
            "autumn_forest_path",
            "단풍 든 동네 뒷산 숲길",
            "ordinary hiking trail on a small Korean mountain in late autumn rain, mixed oak, maple and ginkgo trees, "
            "leaves only partially turned, gradual color change within each tree from green to yellow to orange and "
            "deep red, outer and upper branches turned first, wet leaves darkened by rain, muted autumn colors, "
            "some brown dry leaf edges, small holes and imperfections in leaves, fallen wet leaves stuck to the dark "
            "soil path",
            [
                "light mist between the trees",
                "a wooden bench with wet fallen leaves",
                "stone steps covered with fallen leaves",
                "a rope railing along the trail",
            ],
            {"intensity": 1.0, "angle": 5.0, "fog": 0.12, "brightness": 0.5, "dof": 1.0, "foliage": "autumn"},
            negative=AUTUMN_NEGATIVE,
            style=AUTUMN_STYLE,
            comfy=dict(AUTUMN_COMFY),
            post=dict(AUTUMN_POST),
        ),
        Scene(
            "autumn_temple",
            "비 오는 가을 산사",
            "quiet Korean mountain temple courtyard in late autumn rain, dark tiled roof and wooden pillars, "
            "old stone steps and a stone wall, mixed maple and ginkgo trees around, leaves only partially turned, "
            "gradual color change from green to yellow to orange and deep red, wet leaves darkened by rain, "
            "muted autumn colors, some brown dry leaf edges, fallen wet leaves on the stone steps",
            [
                "light mist hanging over the mountain behind",
                "view up the stone steps toward the temple gate",
                "a small stone pagoda beside the path",
            ],
            {"intensity": 1.0, "angle": 4.0, "fog": 0.12, "brightness": 0.5, "dof": 1.0, "foliage": "autumn"},
            negative=AUTUMN_NEGATIVE + ", " + HANOK_NEGATIVE,
            style=AUTUMN_STYLE,
            comfy=dict(AUTUMN_COMFY),
            post=dict(AUTUMN_POST),
        ),
        # ---------- 숲 씬 ----------
        Scene(
            "forest_night",
            "비 내리는 저녁 숲",
            "ordinary Korean mountain forest in the evening rain in summer, slender pine and oak trees with green leaves, "
            "wet dark soil hiking trail, wet dark tree trunks, light mist between the trees, everything wet",
            [
                "blue hour, dim light",
                "a trail street lamp glowing faintly in the distance",
                "wooden trail stairs and a rope railing",
            ],
            {"intensity": 1.3, "brightness": 0.45, "darken": 0.12, "fog": 0.18, "lightning": 0},
            negative=FOREST_NEGATIVE,
        ),
        Scene(
            "forest_path",
            "동네 뒷산 숲길의 잔잔한 비",
            "ordinary hiking trail on a small Korean mountain on a rainy summer day, leafy oak branches "
            "in the foreground with clearly visible individual green leaves, full green canopy, "
            "wet dark soil path with small puddles, low green shrubs, everything wet, overcast sky",
            [
                "wooden trail stairs and a rope railing along the path",
                "a wooden bench beside the trail",
                "early morning, soft grey light, light mist in the distance",
                "narrow path between young green trees",
            ],
            {"intensity": 0.9, "angle": 5.0, "fog": 0.1},
            negative=FOREST_NEGATIVE,
        ),
        Scene(
            "cabin_window",
            "휴양림 산장 창가",
            "view from inside a cozy lived-in wooden cabin at a Korean recreational forest looking out a large window with a "
            "thick wooden frame at a misty mountain slope with layers of slender pine and oak trees fading into mist, "
            "clear clean window glass, on the deep wooden windowsill a ceramic mug, a small potted plant, a few worn books "
            "and a small oil lamp, a knitted wool blanket draped over a wooden chair, rough wooden plank walls and ceiling beams "
            "with natural grain and knots, a small framed picture and a bunch of dried herbs on the wall, warm lamp light inside, "
            "rich natural details like a real documentary photograph, empty cabin without people",
            [
                "grey rainy afternoon, soft light, a reading nook with a cushion and a book on the windowsill",
                "evening, warm lamp inside, dark blue misty forest outside",
                "summer, fresh green leaves outside, a straw hat hanging by the window",
                "two windows side by side with simple linen curtains, a small wooden table with a teapot and cups",
                "wide view of the cabin room with the window, a wooden chair, a small shelf and hanging lanterns",
            ],
            {"intensity": 0.8, "brightness": 0.35, "fog": 0.0, "splashes": False, "darken": 0.05, "window": True},
            negative=FOREST_NEGATIVE + ", luxury, bare empty walls, minimalist, plain empty room, modern apartment",
            comfy={"family": "zimage"},   # v11.22: 너무 단순·밋밋 → 소품·질감을 풍부하게, Z-Image
        ),
        Scene(
            "tent",
            "비 오는 캠핑장 텐트",
            "a dome tent under a tarp at a Korean mountain campground on a rainy day, "
            "camping chair and a small lantern, wet ground, overcast, "
            "real documentary photograph, ordinary Korean mountain scenery: rounded ridges covered with dense mixed oak, pine and other deciduous trees, individual tree crowns of different heights, shapes, greens and textures, ridgelines layered one behind another fading into mist and low clouds, natural irregular details, no fantasy, no alpine peaks",
            [
                "dusk, lantern glowing warmly under the tarp",
                "daytime, grey rainy light, light mist on the mountain",
                "view from inside the tent through the open door at the forested mountain slope",
                "tent seen from the side with a wooden deck and a camping chair, ordinary Korean forest behind",
                "wide view of the whole campground with several tents, wet gravel paths, forested hills behind",
            ],
            {"intensity": 1.0, "brightness": 0.45, "darken": 0.08, "fog": 0.1},
            negative=FOREST_NEGATIVE + ", glamping, fairy lights, bonfire",
            comfy={"family": "zimage"},   # v11.22
        ),
        Scene(
            "tent_view_mountains",
            "텐트 안에서 보는 비 오는 산",
            "view from inside a dome tent looking out through the open tent door at a rainy Korean mountain landscape, "
            "the dark tent fabric frames the opening, a sleeping bag and a small lantern at the edge of the frame, wet wooden camping deck outside, "
            "real documentary photograph, ordinary Korean mountain scenery: rounded ridges covered with dense mixed oak, pine and other deciduous trees, individual tree crowns of different heights, shapes, greens and textures, ridgelines layered one behind another fading into mist and low clouds, natural irregular details, no fantasy, no alpine peaks",
            [
                "grey rainy afternoon, soft diffused light, low clouds on the ridges",
                "early morning, pale light, thick mist between the ridges",
                "late afternoon, soft light, the nearest slope with slender pines in front",
                "dusk, lantern glowing warmly inside the tent, dark blue mist outside",
                "wide opening of the tent with the whole valley and layered ridges visible",
            ],
            {"intensity": 1.0, "brightness": 0.45, "darken": 0.06, "fog": 0.12},
            negative=FOREST_NEGATIVE + ", glamping, fairy lights, bonfire, people, snowy peaks, canada, norway",
        ),
        Scene(
            "tent_view_stream",
            "텐트 안에서 보는 개울",
            "view from inside a dome tent looking out through the open tent door at a small mountain stream just below the camp, "
            "dark wet grey granite rocks and clear water flowing between them, green trees on the bank and forested hills beyond, "
            "the tent fabric frames the opening, a sleeping bag at the edge of the frame, "
            "real documentary photograph, ordinary Korean mountain scenery: rounded ridges covered with dense mixed oak, pine and other deciduous trees, individual tree crowns of different heights, shapes, greens and textures, ridgelines layered one behind another fading into mist and low clouds, natural irregular details, no fantasy, no alpine peaks",
            [
                "grey rainy afternoon, the stream runs through rounded boulders",
                "early morning, pale light, mist rising from the stream",
                "a small cascade over the rocks, the sound of running water, overcast",
                "wide shallow stream with pebbles and a gravel bank, a few camping chairs under a tarp at the side",
                "dusk, a lantern glowing inside the tent, the stream faintly reflecting the grey sky",
            ],
            {"intensity": 0.9, "angle": 4.0, "fog": 0.1, "splashes": False, "wet": 1.0, "water_rain": 1.0},
            negative=FOREST_NEGATIVE + ", glamping, fairy lights, bonfire, people, dry rocks, sunlit rocks, bright sunlight, blue sky, canada, norway",
        ),
        Scene(
            "tent_view_valley",
            "텐트 안에서 보는 계곡 숲",
            "view from inside a tent through the open door at a wide Korean mountain valley in the rain, a river winding through the valley floor, "
            "forested slopes on both sides, the tent fabric frames the opening, wet grass and gravel just outside, "
            "real documentary photograph, ordinary Korean mountain scenery: rounded ridges covered with dense mixed oak, pine and other deciduous trees, individual tree crowns of different heights, shapes, greens and textures, ridgelines layered one behind another fading into mist and low clouds, natural irregular details, no fantasy, no alpine peaks",
            [
                "grey rainy afternoon, the river visible far below between the trees",
                "early morning, mist filling the valley",
                "summer, fresh green forest, soft light, the river reflecting the grey sky",
                "dusk, blue mist in the valley, a small lantern glowing at the tent entrance",
            ],
            {"intensity": 1.0, "brightness": 0.45, "darken": 0.06, "fog": 0.14, "splashes": False, "water_rain": 0.6},
            negative=FOREST_NEGATIVE + ", glamping, fairy lights, bonfire, people, snowy peaks, canada, norway",
        ),
        Scene(
            "tent_meadow",
            "고원 초원 위 텐트",
            "a dome tent pitched on a wide open highland meadow of short wet grass in Korea on a rainy day, a camping chair beside it, a few scattered trees and gentle rolling hills around, low grey clouds, "
            "real documentary photograph, ordinary Korean mountain scenery, individual trees of different heights and greens, natural irregular details, no fantasy, no alpine peaks",
            [
                "wide view with the tent small in the meadow and the rolling hills behind",
                "the tent on the left third, a broad grey sky and layered hills on the right",
                "a closer view of the tent door and chair, the meadow stretching behind",
                "early morning, thin mist lying over the meadow",
                "dusk, a lantern glowing inside the tent, the meadow dark blue",
            ],
            {"intensity": 1.0, "brightness": 0.45, "darken": 0.06, "fog": 0.12},
            negative=FOREST_NEGATIVE + ", glamping, fairy lights, bonfire, people, snowy peaks, canada, norway",
        ),
        Scene(
            "tent_pine_grove",
            "잣나무·소나무 숲 속 텐트",
            "a tent pitched in a quiet grove of tall straight Korean pine trees on a rainy day, a soft carpet of pine needles on the ground, a tarp stretched in front of the tent and a small lantern, "
            "real documentary photograph, ordinary Korean mountain scenery, individual trees of different heights and greens, natural irregular details, no fantasy, no alpine peaks",
            [
                "wide view between the tall pine trunks with the tent in the middle distance",
                "the tent seen from the side with the tarp, trunks receding behind",
                "a close view of the tent door and the tarp, dripping pine branches above",
                "early morning, light mist between the trunks",
                "dusk, the lantern glowing warmly under the tarp",
            ],
            {"intensity": 1.0, "brightness": 0.42, "darken": 0.08, "fog": 0.1},
            negative=FOREST_NEGATIVE + ", glamping, fairy lights, bonfire, people, snowy peaks, canada, norway",
        ),
        Scene(
            "tent_lakeside",
            "호숫가 비 오는 텐트",
            "a tent pitched on a gravel shore of a calm mountain lake in Korea on a rainy day, a camping chair and a small lantern, forested hills reflected in the water, low clouds on the hills, "
            "real documentary photograph, ordinary Korean mountain scenery: rounded ridges covered with dense mixed oak, pine and other deciduous trees, individual tree crowns of different heights, shapes, greens and textures, ridgelines layered one behind another fading into mist and low clouds, natural irregular details, no fantasy, no alpine peaks",
            [
                "wide view of the tent on the shore with the lake and hills behind",
                "the tent on the right, the wide lake and layered hills on the left",
                "a closer view of the tent door and the chair with the lake softly behind",
                "early morning, mist over the lake",
                "dusk, a lantern glowing inside the tent, the lake dim and still",
            ],
            {"intensity": 1.0, "brightness": 0.45, "darken": 0.06, "fog": 0.14, "splashes": False, "water_rain": 1.0},
            negative=FOREST_NEGATIVE + ", glamping, fairy lights, bonfire, people, snowy peaks, canada, norway",
        ),
        Scene(
            "tent_car_camp",
            "차박 캠핑 (SUV + 타프)",
            "a beautiful car camping site in Korean nature on a rainy day with a stunning view, a stylish vehicle parked beside a handsome tent or covered lounge, "
            "a stylish camp table with beautiful props and comfortable chairs placed fully under the shelter roof, clearly protected from the rain, the wet ground and puddles only outside the shelter, "
            "tasteful warm lantern light, natural unposed composition, sharp focus, "
            "real documentary photograph, ordinary Korean mountain scenery: rounded ridges covered with dense mixed oak, pine and other deciduous trees, individual tree crowns of different heights, shapes, greens and textures, ridgelines layered one behind another fading into mist and low clouds, natural irregular details, no fantasy, no alpine peaks",
            [
                "wide view: the car and its shelter in the left third, a broad open mountain view in the right two thirds",
                "wide view: the car and its shelter in the right third, a broad open mountain view in the left two thirds",
                "a view from under the shelter roof out at the rainy forest, the table with dishes and the chairs in front, dry under the roof",
                "a closer view of the covered camp kitchen beside the open car with a lantern glowing, rain-wet trees behind",
                "dusk, a lantern and a string of small warm lights glowing under the shelter roof, the mountains in blue mist behind",
            ],
            {"intensity": 1.0, "brightness": 0.45, "darken": 0.08, "fog": 0.1},
            negative=FOREST_NEGATIVE + ", glamping, fairy lights, bonfire, people, snowy peaks, canada, norway, table in the open rain, dishes outside the tarp, no roof over the table",
        ),
        Scene(
            "tent_interior_view",
            "아늑하게 꾸민 텐트 안 + 바깥 멋진 풍경 (비)",
            "a beautifully decorated cozy tent interior seen from inside, the wide tent door open and framing a stunning view of Korean nature outside on a rainy day, "
            "warm tasteful lantern light inside the tent, the tent fabric frames the opening, the floor inside is dry, just outside the door a small wooden deck or gravel and grass ground is clearly visible below the door opening with the view beyond it, wet ground only outside, no people, natural unposed composition, sharp focus, "
            "real documentary photograph, ordinary Korean mountain scenery: rounded ridges covered with dense mixed oak, pine and other deciduous trees, individual tree crowns of different heights, shapes, greens and textures, ridgelines layered one behind another fading into mist and low clouds, natural irregular details, no fantasy, no alpine peaks",
            [
                "wide view from deep inside the tent: the cozy interior in the foreground and the big open door showing the whole view",
                "a view from the bed looking out through the open tent door, lanterns glowing at both sides of the opening",
                "a close view of the lantern-lit table inside the tent with the rainy view softly visible through the door",
                "early morning, soft pale light, mist over the view, the lanterns still glowing inside",
                "dusk, the lanterns glowing warmly inside, the view outside in deep blue mist",
            ],
            {"intensity": 1.0, "brightness": 0.45, "darken": 0.06, "fog": 0.12, "interior": 0.4, "water_rain": 1.6, "water_boost": 2.0, "wet": 0.8, "wet_streams": 0.0, "veil": 0.0, "splash_gain": 0.3, "flicker": 0.3},
            negative=FOREST_NEGATIVE + ", glamping resort, hotel, fairy lights, bonfire, people, snowy peaks, canada, norway, rain inside the tent, wet floor inside",
        ),
        Scene(
            "tent_by_stream",
            "개울가 캠핑장 텐트",
            "a dome tent pitched on a gravel bank beside a clear mountain stream at a Korean campground on a rainy day, "
            "a tarp stretched in front of the tent, a camping chair and a small lantern, dark wet rocks in the stream, "
            "real documentary photograph, ordinary Korean mountain scenery: rounded ridges covered with dense mixed oak, pine and other deciduous trees, individual tree crowns of different heights, shapes, greens and textures, ridgelines layered one behind another fading into mist and low clouds, natural irregular details, no fantasy, no alpine peaks",
            [
                "grey rainy afternoon, view of the tent from across the stream",
                "early morning mist over the stream and the tent",
                "dusk, lantern glowing warmly under the tarp",
                "close view of the tent door and tarp with the stream behind",
            ],
            {"intensity": 1.0, "brightness": 0.45, "darken": 0.07, "fog": 0.12, "splashes": False, "wet": 1.0, "water_rain": 0.8},
            negative=FOREST_NEGATIVE + ", glamping, fairy lights, bonfire, people, canada, norway",
        ),

        Scene(
            "forest_lake",
            "산속 저수지의 비",
            "quiet mountain reservoir in Korea on a rainy day, green forested hills around the water, "
            "raindrop ripples on the water surface, low clouds on the hills, overcast",
            [
                "a wooden deck walkway along the shore",
                "early morning, pale light, mist over the water",
                "summer, lush green hills",
            ],
            {"intensity": 1.1, "fog": 0.18, "splashes": False, "water_rain": 1.0},
            negative=FOREST_NEGATIVE + ", alpine, snowy peaks, canada, norway",
        ),
        Scene(
            "valley_stream",
            "계곡에 내리는 비",
            "small mountain stream in a Korean valley on a rainy summer day, clear water flowing over "
            "dark rain-soaked grey granite rocks glistening wet, green trees on both sides, "
            "overcast grey light, raindrop ripples on the water",
            [
                "small waterfall between the rocks",
                "wide shallow stream, pebbles",
                "light mist in the distance",
            ],
            {"intensity": 0.9, "angle": 4.0, "fog": 0.08, "splashes": False, "wet": 1.0, "water_rain": 1.0},
            negative=FOREST_NEGATIVE + ", dry rocks, sunlit rocks, bright sunlight, dappled sunlight, blue sky",
        ),
        Scene(
            "temple_path",
            "산사로 가는 돌계단",
            "old worn granite stone steps going up a quiet Korean mountain path on a rainy day, "
            "low rough stone retaining walls, slender pine and oak trees, wet steps with a few fallen leaves, "
            "no buildings",
            [
                "soft grey light, tranquil",
                "summer, green trees, light mist",
                "colorful paper lotus lanterns hanging along the path",
            ],
            {"intensity": 0.9, "angle": 3.0, "fog": 0.12},
            negative=FOREST_NEGATIVE + ", " + HANOK_NEGATIVE + ", building, pavilion, fortress, castle, arch, "
                     "stone lanterns, torii, shrine",
        ),
        Scene(
            "thunder_forest",
            "천둥 치는 폭우의 산",
            "Korean mountain forest in a heavy summer thunderstorm, torrential rain, slender trees swaying, "
            "dark storm clouds over the hills, muddy water running down the dirt trail",
            ["late afternoon, very dark sky", "twilight, dark grey clouds"],
            {"intensity": 1.8, "angle": 14.0, "speed": 1.2, "brightness": 0.55,
             "darken": 0.15, "fog": 0.2, "lightning": 2},
            negative=FOREST_NEGATIVE,
        ),
        # ---------- 아늑한 실내 (v11.22): 촛불·벽난로·반려동물·창밖 폭우 ----------
        Scene(
            "candle_single",
            "촛불 하나 켜진 어두운 방",
            "one single large thick pillar candle with a big tall bright steady flame, clearly visible and prominent in the frame, standing on a wooden table in a dark cozy windowless room with solid plain walls and no windows, "
            "soft melted wax at the top of the candle, the candle is the only light source, warm golden glow falling on a few charming small objects nearby "
            "(a small closed book, dried flowers in a tiny vase), deep soft darkness around, "
            "empty room without people, calm sleepy atmosphere",
            [
                "the big candle stands in a heavy brass holder, the room clearly visible behind it",
                "an old wooden desk beside a stack of well-worn books",
                "a bedside table with the soft edge of a knitted blanket",
                "a rustic wooden shelf with a few small trinkets",
                "a round wooden stool beside an old armchair, a folded wool blanket",
                "a small wooden nightstand with an old alarm clock and a glass of water, a pillow edge visible",
                "a low wooden table with an open journal and a pen",
                "a window-less reading corner with a stack of old books and a small clay plant pot",
            ],
            {"intensity": 0.0, "fog": 0.0, "splashes": False, "interior": 1.0, "big_flame": True, **INTERIOR_RAIN},
            style=INTERIOR_STYLE, negative=INTERIOR_NEGATIVE, comfy={"family": "zimage"}, post=NATURAL_POST,
        ),
        Scene(
            "candle_bookshelf",
            "오래된 책이 가득한 책장 + 촛불 방",
            "a dark cozy windowless room with solid plain walls and no windows, one tall wooden bookshelf filled with many old worn books of different sizes and faded leather and cloth spines standing in neat rows, "
            "a large thick lit candle with a big bright steady flame in the foreground on a wooden table, the candle is the only light source, warm golden glow falling on the book spines, "
            "a few small charming objects nearby, deep soft darkness around, empty room without people, calm sleepy atmosphere",
            [
                "wide view of the whole bookshelf wall with the candle on a reading table in front",
                "the candle slightly left of center with the tall bookshelf behind it on the right",
                "the candle slightly right of center with the tall bookshelf behind it on the left",
                "a closer view of the candle with the old book spines glowing softly behind it",
                "a corner of the room with two bookshelves meeting and a small reading table with the candle",
                "a low angle view along a row of old books with the candle glowing in the foreground",
            ],
            {"intensity": 0.0, "fog": 0.0, "splashes": False, "interior": 1.0, "big_flame": True, **INTERIOR_RAIN},
            style=INTERIOR_STYLE, negative=INTERIOR_NEGATIVE + ", readable text on book covers, titles, logos, empty shelves, modern shelves", comfy={"family": "zimage"}, post=NATURAL_POST,
        ),
        Scene(
            "candle_bookshelf_rain_window",
            "오래된 책장 + 큰 촛불 + 비 오는 창",
            "a dark cozy room with one tall wooden bookshelf filled with many old worn books of different sizes and faded spines standing in neat rows, "
            "next to it a large window with clean clear window glass and a dark rainy night outside, "
            "a large thick lit candle with a big bright steady flame in the foreground on a wooden reading table, the candle is the main light source, "
            "warm golden glow falling on the book spines and the window frame, a few small cozy objects nearby, empty room without people, calm sleepy atmosphere",
            [
                "wide view with the bookshelf on the left, the rainy window on the right and the candle on the table in front",
                "wide view with the bookshelf on the right, the rainy window on the left and the candle on the table in front",
                "a closer view of the candle with the old books glowing behind it and the window softly visible beside",
                "the window seat beside the bookshelf, the candle on a small tray, the rainy window behind",
                "a corner of the room where the bookshelf meets a tall window, the candle on a desk",
                "a low angle across the table with the candle in the foreground, the bookshelf and the rainy window behind",
            ],
            {"intensity": 1.0, "brightness": 0.3, "speed": 0.55, "veil": 0.0, "window": True, "interior": 1.0, "big_flame": True, **INTERIOR_RAIN},
            style=INTERIOR_STYLE, negative=INTERIOR_NEGATIVE + ", readable text on book covers, titles, logos, empty shelves, modern shelves", comfy={"family": "zimage"}, post=NATURAL_POST,
        ),
        Scene(
            "candle_many",
            "촛불 여러 개 아기자기한 방",
            "a dark cozy windowless room with solid plain walls and no windows, lit only by many small lit candles of different heights with bright steady flames, "
            "candles on a wooden shelf, a small table and a mantel, lots of charming little decorations "
            "(tiny ceramic figurines, glass jars, little framed pictures, dried flowers, stacked books, a knitted blanket), "
            "warm golden glow, deep soft shadows, empty room without people, calm sleepy atmosphere",
            [
                "an old wooden mantel shelf with candles in brass and glass holders",
                "a round wooden table covered with candles and small trinkets",
                "a bookshelf corner with candles between the books",
                "candles in glass lanterns on a low wooden chest against a plain wall",
            ],
            {"intensity": 0.0, "fog": 0.0, "splashes": False, "interior": 1.0, **INTERIOR_RAIN},
            style=INTERIOR_STYLE, negative=INTERIOR_NEGATIVE, comfy={"family": "zimage"}, post=NATURAL_POST,
        ),
        Scene(
            "cozy_parlor",
            "아늑한 응접실 · 창밖 비 · 촛불 하나",
            "a cozy old-fashioned parlor living room at night, a comfortable armchair and a small sofa with a knitted blanket, "
            "a round rug, bookshelves full of books and charming little knick-knacks, a table lamp with a dim warm shade, "
            "exactly one single lit candle with a small bright steady flame on a side table, patterned wallpaper, dark wooden furniture, "
            "a large window with dark night outside and clean clear glass, empty room without people",
            [
                "wide view of the whole room",
                "view from the armchair toward the window, the candle on a side table",
                "a small round table with a teapot and cups in the foreground",
                "a large bay window with heavy curtains pulled back, the candle on a windowsill",
                "a fireplace-less corner with a grandfather clock and a bookshelf, the candle on a small table",
                "a wide wooden window with a deep sill and a sleeping view of the dark garden",
            ],
            {"intensity": 1.2, "brightness": 0.42, "window": True, "interior": 1.0, "fire_sound": False,
             **INTERIOR_RAIN},
            style=INTERIOR_STYLE, negative=INTERIOR_NEGATIVE, comfy={"family": "zimage"}, post=NATURAL_POST,
        ),
        Scene(
            "candle_rain_window",
            "창가 큰 촛불 하나 · 창밖 폭우",
            "one single large thick pillar candle with a big tall bright steady flame, clearly visible and prominent, on a wooden desk right beside a large dark window, "
            "clean clear window glass with a dark stormy night outside, a few small cozy objects (an open book), "
            "the candle is the main light source, warm golden glow on the desk, empty room without people",
            [
                "the window has a wooden frame and a deep sill",
                "close view of the candle with the window blurred behind it",
                "a knitted blanket on a chair next to the desk",
                "a small round table by the window with a teapot, the candle in a glass holder",
                "a wide window with simple curtains, the candle on the sill",
                "an old writing desk with a leather notebook and fountain pen beside the window",
                "a cozy window seat with a cushion, the candle on a small tray",
            ],
            {"intensity": 1.0, "brightness": 0.3, "speed": 0.55, "veil": 0.0, "window": True, "interior": 1.0, "big_flame": True, **INTERIOR_RAIN},
            style=INTERIOR_STYLE, negative=INTERIOR_NEGATIVE, comfy={"family": "zimage"}, post=NATURAL_POST,
        ),
        Scene(
            "living_fireplace_storm",
            "3면 창 폭우 + 벽난로 거실 + 반려견",
            "a spacious cozy living room at night, a wide bay window made of three large window panes with clean clear glass "
            "showing a dark stormy night outside, a stone fireplace with a bright roaring wood fire with tall lively flames filling the firebox and glowing embers on the hearth, "
            "a comfortable bed with soft blankets and pillows in the room, a dog sleeping curled up peacefully "
            "with eyes closed on the rug on the floor, a few candles with bright steady flames on the mantel, "
            "wooden ceiling beams, charming small decorations, warm firelight, empty room without people",
            [
                "wide view of the whole room",
                "a small cat is also sleeping curled up on the bed",
                "exactly one single cat with one head lying down fully asleep curled up in a ball with eyes closed on an armchair near the fireplace",
                "exactly one single cat with one head lying down fully asleep curled up in a ball with eyes closed on the rug next to the dog",
                "view from the bed toward the fireplace and the three windows",
            ],
            {"intensity": 1.9, "brightness": 0.45, "window": True, "interior": 1.0, "fire": 1.0, "fire_sound": True,
             **INTERIOR_RAIN},
            style=INTERIOR_STYLE, negative=INTERIOR_NEGATIVE, comfy={"family": "zimage"}, post=NATURAL_POST, animals=True,
        ),
        Scene(
            "candle_nook",
            "창문 없는 작은 방 · 책 읽는 구석 촛불",
            "a small windowless room, solid plain walls with no windows at all, a cozy reading nook with an armchair, a small side table and a bookshelf, lit only by three or four candles with bright steady flames, lots of charming little decorations (small figurines, dried flowers, ceramic cups, stacked books), warm golden glow, deep soft shadows, empty room without people, calm sleepy atmosphere",
            [
                "an old wooden bookshelf behind the armchair",
                "a knitted blanket over the armchair and a cup of tea on the table",
                "a small round rug and a stack of old books beside the candles",
            ],
            {"intensity": 0.0, "fog": 0.0, "splashes": False, "interior": 1.0, **INTERIOR_RAIN},
            style=INTERIOR_STYLE, negative=INTERIOR_NEGATIVE, comfy={"family": "zimage"}, post=NATURAL_POST,
        ),
        Scene(
            "candle_closeup",
            "큰 촛불 클로즈업 · 컴컴한 방 소품 배경",
            "an extreme close-up photograph of one single large lit candle filling the center of the frame, a tall bright steady flame with a white-yellow core and a warm orange glow, "
            "soft melted wax at the candle top and a few slow wax drips on the side, the candle is the only light source in a completely dark room, "
            "warm golden light gently falling on a few nearby objects, deep soft darkness all around with a few props faintly visible and softly out of focus in the background, "
            "sharp focus on the flame and the wax, windowless room, empty room without people, calm sleepy atmosphere",
            [
                "the candle in the center of the frame, props softly blurred behind it",
                "the candle slightly left of center with the dark room and its objects visible on the right",
                "the candle slightly right of center with the dark room and its objects visible on the left",
                "a slightly lower angle looking up at the tall flame against the dark",
                "a closer view with the flame very large and the background almost dark",
                "a wider view where the candle is large in the foreground and the dim room shows behind it",
            ],
            {"intensity": 0.0, "fog": 0.0, "splashes": False, "interior": 1.0, "big_flame": True, **INTERIOR_RAIN},
            style=INTERIOR_STYLE, negative=INTERIOR_NEGATIVE, comfy={"family": "zimage"}, post=NATURAL_POST,
        ),
        Scene(
            "campfire_lake",
            "산속 호숫가 모닥불",
            "a calm mountain lake in Korea with a small gravel shore, a campfire burning on the shore in the foreground, the lake reflecting the last light of the sky and the hills, "
            "a real wood campfire with tall lively orange flames and glowing embers on a ring of stones, small split logs stacked in the fire, warm firelight lighting the ground and nearby objects, "
            "real documentary photograph of a Korean mountain campsite, ordinary Korean mountain scenery: rounded ridges covered with mixed oak, pine and other deciduous trees, individual tree crowns of different heights and greens, ridgelines layered one behind another fading into soft haze, natural irregular details, no fantasy, no alpine peaks, dry clear air with no precipitation, empty campsite without people",
            [
                "wide view of the whole lake with the campfire in the lower foreground",
                "the campfire slightly left of center, the lake and hills on the right",
                "the campfire slightly right of center, the lake and hills on the left",
                "a closer low view of the flames with the lake softly visible behind",
                "blue hour, the fire is the main light and the lake is dim and still",
            ],
            {"intensity": 0.0, "fog": 0.0, "splashes": False, "interior": 1.0, "fire": 1.0, "water_rain": 0.0, **CAMPFIRE_RAIN},
            style=NATURAL_STYLE, negative=CAMPFIRE_NEGATIVE, comfy={"family": "zimage"}, post=NATURAL_POST,
        ),
        Scene(
            "campfire_kettle_lake",
            "호숫가 모닥불 · 커피 주전자",
            "a dark blackened metal camping kettle with a handle hanging over the campfire on a small iron tripod, coffee brewing inside it, a camping mug on a flat rock nearby, a calm mountain lake in Korea behind, "
            "a real wood campfire with tall lively orange flames and glowing embers on a ring of stones, small split logs stacked in the fire, warm firelight lighting the ground and nearby objects, "
            "real documentary photograph of a Korean mountain campsite, ordinary Korean mountain scenery: rounded ridges covered with mixed oak, pine and other deciduous trees, individual tree crowns of different heights and greens, ridgelines layered one behind another fading into soft haze, natural irregular details, no fantasy, no alpine peaks, dry clear air with no precipitation, empty campsite without people",
            [
                "the kettle hanging above the flames in the center, the lake softly behind",
                "the kettle over the fire slightly left of center with the lake on the right",
                "the kettle sitting on a grill grate over the fire, a mug and a coffee dripper beside it on a stone",
                "a closer view of the kettle and flames, the lake dim behind",
                "wide view with the kettle fire at the shore and the hills reflected in the water",
            ],
            {"intensity": 0.0, "fog": 0.0, "splashes": False, "interior": 1.0, "fire": 1.0, "water_rain": 0.0, **CAMPFIRE_RAIN},
            style=NATURAL_STYLE, negative=CAMPFIRE_NEGATIVE, comfy={"family": "zimage"}, post=NATURAL_POST,
        ),
        Scene(
            "campfire_tent_lake",
            "호숫가 텐트 + 모닥불",
            "a dome tent pitched on a grassy lakeshore with a soft warm glow from inside, a campfire burning in front of the tent, a folding camp chair and a stack of firewood, a calm mountain lake in Korea behind, "
            "a real wood campfire with tall lively orange flames and glowing embers on a ring of stones, small split logs stacked in the fire, warm firelight lighting the ground and nearby objects, "
            "real documentary photograph of a Korean mountain campsite, ordinary Korean mountain scenery: rounded ridges covered with mixed oak, pine and other deciduous trees, individual tree crowns of different heights and greens, ridgelines layered one behind another fading into soft haze, natural irregular details, no fantasy, no alpine peaks, dry clear air with no precipitation, empty campsite without people",
            [
                "wide view: tent on the left, campfire in the middle, the lake and hills behind",
                "wide view: tent on the right, campfire in the middle, the lake and hills behind",
                "the campfire in the foreground with the glowing tent and the lake behind",
                "a low angle across the flames toward the tent and the dim lake",
                "blue hour, a few first stars, the tent glowing, the fire is the brightest light",
            ],
            {"intensity": 0.0, "fog": 0.0, "splashes": False, "interior": 1.0, "fire": 1.0, "water_rain": 0.0, **CAMPFIRE_RAIN},
            style=NATURAL_STYLE, negative=CAMPFIRE_NEGATIVE, comfy={"family": "zimage"}, post=NATURAL_POST,
        ),
        Scene(
            "campfire_tent_kettle",
            "텐트 앞 모닥불 + 커피 주전자",
            "a dome tent with a soft warm glow from inside, in front of it a campfire with a blackened camping kettle on a grill grate over the flames and a mug of hot coffee on a log, a calm mountain lake in Korea behind, "
            "a real wood campfire with tall lively orange flames and glowing embers on a ring of stones, small split logs stacked in the fire, warm firelight lighting the ground and nearby objects, "
            "real documentary photograph of a Korean mountain campsite, ordinary Korean mountain scenery: rounded ridges covered with mixed oak, pine and other deciduous trees, individual tree crowns of different heights and greens, ridgelines layered one behind another fading into soft haze, natural irregular details, no fantasy, no alpine peaks, dry clear air with no precipitation, empty campsite without people",
            [
                "the kettle on the fire in the center, the tent and the lake behind it",
                "kettle and fire on the left, tent on the right, the lake behind",
                "kettle and fire on the right, tent on the left, the lake behind",
                "a close view of the kettle over the fire, the glowing tent softly blurred behind",
                "wide dusk view with a coffee pot on the fire and the lake reflecting the sky",
            ],
            {"intensity": 0.0, "fog": 0.0, "splashes": False, "interior": 1.0, "fire": 1.0, "water_rain": 0.0, **CAMPFIRE_RAIN},
            style=NATURAL_STYLE, negative=CAMPFIRE_NEGATIVE, comfy={"family": "zimage"}, post=NATURAL_POST,
        ),
        Scene(
            "campfire_car_camp",
            "차박 캠핑 · 차 앞 큰 장작불",
            "a beautiful car camping site in Korean nature with a stunning view, a stylish vehicle parked beside a handsome tent or covered lounge with a stylish table and comfortable chairs under its roof, and out in the open in front of it a big campfire burning on a ring of stones, tasteful warm lantern light, natural unposed composition, sharp focus, "
            "a real wood campfire with tall lively orange flames and glowing embers on a ring of stones, small split logs stacked in the fire, warm firelight lighting the ground and nearby objects, real documentary photograph of a Korean mountain campsite, ordinary Korean mountain scenery: rounded ridges covered with mixed oak, pine and other deciduous trees, individual tree crowns of different heights and greens, ridgelines layered one behind another fading into soft haze, natural irregular details, no fantasy, no alpine peaks, dry clear air with no precipitation, empty campsite without people",
            [
                "wide view: the car and its shelter on the left, the big campfire in the middle foreground, the mountains behind",
                "wide view: the car and its shelter on the right, the big campfire in the middle foreground, the mountains behind",
                "a closer view of the big campfire with the car and its glowing lantern softly behind it",
                "the campfire in the foreground, a kettle on a grill over the flames, the car and the shelter behind",
                "blue hour dusk view across the fire toward the car, the shelter and the dim mountains",
            ],
            {"intensity": 0.0, "fog": 0.0, "splashes": False, "interior": 1.0, "fire": 1.0, "water_rain": 0.0, **CAMPFIRE_RAIN},
            style=NATURAL_STYLE, negative=CAMPFIRE_NEGATIVE + ", people", comfy={"family": "zimage"}, post=NATURAL_POST,
        ),
        Scene(
            "campfire_forest",
            "숲속 캠핑 모닥불",
            "a campfire in a clearing of a Korean mountain forest, tall pine and oak trees around, a simple tent and a camp lantern at the edge of the firelight, logs for sitting around the fire, "
            "a real wood campfire with tall lively orange flames and glowing embers on a ring of stones, small split logs stacked in the fire, warm firelight lighting the ground and nearby objects, "
            "real documentary photograph of a Korean mountain campsite, ordinary Korean mountain scenery: rounded ridges covered with mixed oak, pine and other deciduous trees, individual tree crowns of different heights and greens, ridgelines layered one behind another fading into soft haze, natural irregular details, no fantasy, no alpine peaks, dry clear air with no precipitation, empty campsite without people",
            [
                "wide view of the clearing with the campfire in the center",
                "the campfire in the foreground, the tent softly visible behind",
                "a closer view of the flames and the logs, the dark forest behind",
                "deep night, the fire is the only light, trees faintly lit at the edge of the glow",
                "the kettle hanging over the fire on a tripod, the dark forest behind",
            ],
            {"intensity": 0.0, "fog": 0.0, "splashes": False, "interior": 1.0, "fire": 1.0, "water_rain": 0.0, **CAMPFIRE_RAIN},
            style=NATURAL_STYLE, negative=CAMPFIRE_NEGATIVE, comfy={"family": "zimage"}, post=NATURAL_POST,
        ),
        Scene(
            "campfire_only",
            "모닥불만 크게",
            "a close view of a single large campfire burning on a ring of stones beside a calm mountain lake, the fire fills the center of the frame, only the fire and the dim shore are visible, dark soft background, "
            "a real wood campfire with tall lively orange flames and glowing embers on a ring of stones, small split logs stacked in the fire, warm firelight lighting the ground and nearby objects, "
            "real documentary photograph of a Korean mountain campsite, ordinary Korean mountain scenery: rounded ridges covered with mixed oak, pine and other deciduous trees, individual tree crowns of different heights and greens, ridgelines layered one behind another fading into soft haze, natural irregular details, no fantasy, no alpine peaks, dry clear air with no precipitation, empty campsite without people",
            [
                "the fire in the center of the frame, the dim lake softly blurred behind",
                "the fire slightly left of center, the dark lake on the right",
                "the fire slightly right of center, the dark lake on the left",
                "a lower angle with tall flames against the dark",
                "a wider view showing the fire ring and the whole dim shore",
            ],
            {"intensity": 0.0, "fog": 0.0, "splashes": False, "interior": 1.0, "fire": 1.0, "water_rain": 0.0, **CAMPFIRE_RAIN},
            style=NATURAL_STYLE, negative=CAMPFIRE_NEGATIVE, comfy={"family": "zimage"}, post=NATURAL_POST,
        ),
        Scene(
            "living_coffee_fireplace_rain",
            "벽난로 + 비 오는 창 + 따뜻한 커피잔",
            "a cozy living room at night, a large window with clean clear glass and a dark blue rainy night outside, a stone fireplace with a bright wood fire with lively flames, a hot coffee in a ceramic cup on a saucer resting on a wooden side table in the foreground, the cup is full of dark coffee, "
            "a sofa with knitted blankets, a few candles with bright steady flames, warm firelight, sharp focus on the cup, empty room without people, no steam and no smoke above the cup",
            [
                "the coffee cup large in the foreground, the fireplace and the rainy window softly visible behind",
                "the coffee cup in the lower left foreground, the fireplace in the middle and the window on the right",
                "the coffee cup in the lower right foreground, the fireplace in the middle and the window on the left",
                "a wide view of the room with the cup on a low table in front of the sofa",
            ],
            {"intensity": 2.0, "brightness": 0.45, "window": True, "interior": 1.0, "fire": 1.0, **INTERIOR_RAIN},
            style=INTERIOR_STYLE, negative=INTERIOR_NEGATIVE + ", steam, smoke, mist, fog above the cup, text, logo", comfy={"family": "zimage"}, post=NATURAL_POST,
        ),
        Scene(
            "living_tea_fireplace_rain",
            "벽난로 + 비 오는 창 + 찻잔",
            "a cozy living room at night, a large window with clean clear glass and a dark blue rainy night outside, a stone fireplace with a bright wood fire with lively flames, a hot tea in a delicate white porcelain teacup with a saucer and a small teapot on a wooden tray on a low table in the foreground, the cup is full of golden tea, "
            "a sofa with knitted blankets, a few candles with bright steady flames, warm firelight, sharp focus on the cup, empty room without people, no steam and no smoke above the cup",
            [
                "the teacup large in the foreground, the fireplace and the rainy window softly visible behind",
                "the teacup on the left foreground, the fireplace in the middle and the window on the right",
                "the teacup on the right foreground, the fireplace in the middle and the window on the left",
                "a wide view of the room with the tea tray on the low table in front of the sofa",
            ],
            {"intensity": 2.0, "brightness": 0.45, "window": True, "interior": 1.0, "fire": 1.0, **INTERIOR_RAIN},
            style=INTERIOR_STYLE, negative=INTERIOR_NEGATIVE + ", steam, smoke, mist, fog above the cup, text, logo", comfy={"family": "zimage"}, post=NATURAL_POST,
        ),
        Scene(
            "living_fireplace_big_window",
            "아주 큰 통창 하나 + 벽난로 거실 · 폭우",
            "a cozy living room at night with one huge floor-to-ceiling window taking up most of the wall with clean clear glass and a dark stormy night outside, a stone fireplace with a bright roaring wood fire with tall lively flames filling the firebox, a sofa with knitted blankets, exactly one single small cute adorable dog with one head sleeping curled up peacefully with eyes closed on a soft rug, a few candles with bright steady flames, charming small decorations, warm firelight, empty room without people",
            [
                "wide view showing the whole window wall",
                "view from the sofa toward the huge window and the fireplace",
                "exactly one single cat with one head lying down fully asleep curled up in a ball with eyes closed on the sofa",
            ],
            {"intensity": 2.0, "brightness": 0.45, "window": True, "interior": 1.0, "fire": 1.0, "fire_sound": True, **INTERIOR_RAIN},
            style=INTERIOR_STYLE, negative=INTERIOR_NEGATIVE, comfy={"family": "zimage"}, post=NATURAL_POST, animals=True,
        ),
        Scene(
            "living_fireplace_two_windows",
            "큰 창 2개 + 벽난로 거실 · 폭우",
            "a cozy living room at night with two large tall windows side by side with clean clear glass and a dark stormy night outside, a stone fireplace with a bright roaring wood fire with tall lively flames filling the firebox between a sofa and an armchair, exactly one single small cute adorable dog with one head sleeping curled up peacefully with eyes closed on the rug, candles with bright steady flames on the mantel, charming small decorations, warm firelight, empty room without people",
            [
                "wide view of the room",
                "exactly one single cat with one head lying down fully asleep curled up in a ball with eyes closed on the armchair",
                "close view of the fireplace with a window beside it",
            ],
            {"intensity": 1.8, "brightness": 0.45, "window": True, "interior": 1.0, "fire": 1.0, "fire_sound": True, **INTERIOR_RAIN},
            style=INTERIOR_STYLE, negative=INTERIOR_NEGATIVE, comfy={"family": "zimage"}, post=NATURAL_POST, animals=True,
        ),
        Scene(
            "living_one_window_rain",
            "창문 하나 있는 아늑한 방 · 폭우",
            "a small cozy room at night with a single window with clean clear glass and a dark stormy night outside, a comfortable bed with soft blankets, a warm bedside lamp and a few candles with bright steady flames, exactly one single small cute adorable dog with one head sleeping curled up peacefully with eyes closed on the floor rug, charming small decorations, warm dim light, empty room without people",
            [
                "the window is above the bed",
                "the window is large with a wide wooden sill",
                "exactly one single cat with one head lying down fully asleep curled up in a ball with eyes closed at the foot of the bed",
            ],
            {"intensity": 1.7, "brightness": 0.45, "window": True, "interior": 1.0, **INTERIOR_RAIN},
            style=INTERIOR_STYLE, negative=INTERIOR_NEGATIVE, comfy={"family": "zimage"}, post=NATURAL_POST, animals=True,
        ),
        Scene(
            "living_fireplace_panorama",
            "전면 통유리 창 + 벽난로 + 침대 · 폭우",
            "a spacious modern cabin living room at night with an entire wall of floor-to-ceiling glass windows with clean clear glass and a dark stormy night outside, a stone fireplace with a bright roaring wood fire with tall lively flames filling the firebox, a large bed with soft blankets near the glass wall, exactly one single small cute adorable dog with one head sleeping curled up peacefully with eyes closed on a rug, candles with bright steady flames, wooden ceiling beams, warm firelight, empty room without people",
            [
                "wide view of the whole glass wall",
                "view from the bed toward the fireplace and the glass wall",
                "exactly one single cat with one head lying down fully asleep curled up in a ball with eyes closed on the bed",
            ],
            {"intensity": 2.0, "brightness": 0.45, "window": True, "interior": 1.0, "fire": 1.0, "fire_sound": True, **INTERIOR_RAIN},
            style=INTERIOR_STYLE, negative=INTERIOR_NEGATIVE, comfy={"family": "zimage"}, post=NATURAL_POST, animals=True,
        ),
        Scene(
            "bedroom_window_candles_cat",
            "침실 큰 창 + 촛불 + 자는 고양이 · 폭우",
            "a cozy bedroom at night with a large window with clean clear glass and a dark stormy night outside, a bed with soft blankets, several candles with bright steady flames on a dresser and a nightstand, exactly one single cat with one head sleeping curled up peacefully on the bed, charming small decorations, warm golden glow, empty room without people",
            [
                "the window is wide with a wooden frame",
                "two tall windows on either side of the bed",
                "exactly one single small cute adorable dog with one head is also sleeping on the floor rug",
            ],
            {"intensity": 1.8, "brightness": 0.45, "window": True, "interior": 1.0, **INTERIOR_RAIN},
            style=INTERIOR_STYLE, negative=INTERIOR_NEGATIVE, comfy={"family": "zimage"}, post=NATURAL_POST, animals=True,
        ),
        Scene(
            "study_candles_big_window",
            "서재 큰 창 + 촛불 여러 개 · 폭우",
            "a cozy old study room at night with a big window with clean clear glass and a dark stormy night outside, a wooden desk with an open book, bookshelves, many small candles with bright steady flames on the desk and shelves, an armchair with a knitted blanket, charming small decorations, warm golden glow, empty room without people",
            [
                "wide view of the study",
                "close view of the desk with candles and the window behind",
                "exactly one single cat with one head lying down fully asleep curled up in a ball with eyes closed on the armchair",
            ],
            {"intensity": 1.8, "brightness": 0.45, "window": True, "interior": 1.0, **INTERIOR_RAIN},
            style=INTERIOR_STYLE, negative=INTERIOR_NEGATIVE, comfy={"family": "zimage"}, post=NATURAL_POST, animals=True,
        ),
        Scene(
            "cabin_fireplace_window",
            "통나무집 벽난로 + 큰 창 · 폭우",
            "a rustic log cabin interior at night with a large window with clean clear glass and a dark stormy night outside, a rough stone fireplace with a bright roaring wood fire with tall lively flames filling the firebox, a wool blanket on a wooden bench, exactly one single small cute adorable dog with one head sleeping curled up peacefully with eyes closed on a sheepskin rug, a few candles with bright steady flames, warm firelight, empty room without people",
            [
                "wide view of the cabin room",
                "the window is beside the fireplace",
                "exactly one single cat with one head lying down fully asleep curled up in a ball with eyes closed on the bench",
            ],
            {"intensity": 1.9, "brightness": 0.45, "window": True, "interior": 1.0, "fire": 1.0, "fire_sound": True, **INTERIOR_RAIN},
            style=INTERIOR_STYLE, negative=INTERIOR_NEGATIVE, comfy={"family": "zimage"}, post=NATURAL_POST, animals=True,
        ),
        Scene(
            "living_turntable_fireplace",
            "클래식 턴테이블 + 벽난로 거실 · 폭우",
            "a cozy living room at night with three lit candles with bright flames on the window sill, room layout: the turntable cabinet stands against the left wall, the stone fireplace is on the right wall, and the window is on the far back wall between them, so the window is never behind or next to the turntable, with a classic vintage wooden record player turntable on a low wooden cabinet, "
            "a black vinyl record playing on the platter with its colorful center label clearly visible, the tonearm lying across the record with the needle resting on the record grooves, tonearm over the record, needle on the record, record is playing, the turntable has no dust cover or lid at all and its body is completely plain and smooth with no lettering, no brand name and no logo, the turntable cabinet stands against a solid wall clearly away from the window, "
            "shelves of vinyl records and a pair of old speakers, a stone fireplace with a bright roaring wood fire with tall lively flames filling the firebox, "
            "one large window on the far back wall with clean clear glass and a dark stormy night outside, "
            "exactly one single small cute adorable dog with one head sleeping curled up peacefully with eyes closed on a rug, warm firelight, empty room without people, no cat",
            [
                "wide medium shot with balanced layout: three lit candles clearly visible on the window sill, the turntable on a cabinet in the left third of the frame with the tonearm lying across the playing record and the red center label, the stone fireplace with a bright roaring fire in the right third, the window with raindrops on the back wall, three lit candles on the window sill, the sleeping dog on the rug in the center foreground, the whole room visible and balanced, whole scene in sharp focus",
                "medium shot: the turntable stands large three lit candles clearly visible on the window sill, in the left foreground filling about a third of the frame, the tonearm clearly visible lying across the playing record, while the window, the fireplace, the lit candles and the sleeping dog are all visible in the room behind it, whole scene in sharp focus",
                "medium shot from a slightly higher angle: three lit candles clearly visible on the window sill, the turntable large in the foreground with the tonearm over the record and the red label sharp, the fireplace fire, the window and the sleeping dog on the rug clearly visible behind, whole scene in sharp focus",
                "close view of the turntable and records with the fireplace glowing behind",
                "exactly one single cat with one head lying down fully asleep curled up in a ball with eyes closed on an armchair, not sitting",
            ],
            {"intensity": 1.8, "brightness": 0.45, "window": True, "interior": 1.0, "fire": 1.0, "fire_sound": True,
             "vinyl_sound": True, **INTERIOR_RAIN},
            style=INTERIOR_STYLE, negative=INTERIOR_NEGATIVE, comfy={"family": "zimage"}, post=NATURAL_POST, animals=True,
        ),
        Scene(
            "turntable_candles_windowless",
            "창문 없는 어두운 방 · 턴테이블 + 촛불",
            "a dark cozy windowless room with solid plain walls and no windows, a classic vintage wooden record player turntable on a wooden table, "
            "a black vinyl record on the platter with its colorful center label clearly visible and the tonearm resting on it, "
            "lit only by several candles with bright steady flames, shelves of vinyl records and charming little decorations, "
            "warm golden glow, deep soft shadows, empty room without people",
            [
                "close view of the turntable with candles beside it",
                "an armchair and a stack of records beside the turntable",
                "wide view of the room with record shelves on the wall",
            ],
            {"intensity": 0.0, "fog": 0.0, "splashes": False, "interior": 1.0, "vinyl_sound": True, **INTERIOR_RAIN},
            style=INTERIOR_STYLE, negative=INTERIOR_NEGATIVE, comfy={"family": "zimage"}, post=NATURAL_POST,
        ),
        Scene(
            "turntable_window_rain",
            "창가 클래식 턴테이블 + 큰 창 폭우 + 촛불",
            "a classic vintage wooden record player turntable on a wooden cabinet beside a large window with clean clear glass and a dark stormy night outside, "
            "a black vinyl record on the platter with its colorful center label clearly visible and the tonearm resting on it, "
            "a few candles with bright steady flames, shelves of vinyl records, a knitted blanket on an armchair, warm golden glow, empty room without people",
            [
                "close view of the turntable with the rainy window behind",
                "wide view of the cozy corner with the window and records",
                "exactly one single cat with one head lying down fully asleep curled up in a ball with eyes closed on the armchair",
            ],
            {"intensity": 1.8, "brightness": 0.45, "window": True, "interior": 1.0, "vinyl_sound": True, **INTERIOR_RAIN},
            style=INTERIOR_STYLE, negative=INTERIOR_NEGATIVE, comfy={"family": "zimage"}, post=NATURAL_POST, animals=True,
        ),
        Scene(
            "living_fireplace_candles",
            "벽난로 + 촛불 여러 개 거실 + 반려견",
            "a cozy living room at night lit by a crackling wood fire in a stone fireplace and many lit candles with bright steady flames "
            "on the mantel, side tables and shelves, a big window with clean clear glass and a dark night outside, "
            "a sofa with knitted blankets, exactly one single small cute adorable dog with one head sleeping curled up peacefully with eyes closed on a soft rug in front of the fire, "
            "charming little decorations, warm golden light, empty room without people",
            [
                "wide view of the room",
                "exactly one single cat with one head lying down fully asleep curled up in a ball with eyes closed on the sofa",
                "exactly one single cat with one head lying down fully asleep curled up in a ball with eyes closed on the hearth rug beside the dog",
                "close view of the fireplace and the sleeping dog on the rug",
            ],
            {"intensity": 1.3, "brightness": 0.42, "window": True, "interior": 1.0, "fire": 1.0, "fire_sound": True,
             **INTERIOR_RAIN},
            style=INTERIOR_STYLE, negative=INTERIOR_NEGATIVE, comfy={"family": "zimage"}, post=NATURAL_POST, animals=True,
        ),
        Scene(
            "hearth_dog_cat",
            "벽난로 앞에서 자는 반려견·반려묘",
            "exactly one single small cute adorable dog with one head and exactly one single cat with one head sleeping peacefully curled up with eyes closed on a soft rug in front of a stone fireplace with a "
            "crackling wood fire, warm firelight on their fur, a cozy dark living room around them, a few candles on the mantel, "
            "a window with clean clear glass and dark night outside, charming little decorations, empty room without people",
            [
                "low angle view close to the floor",
                "a knitted blanket on the rug under them",
                "an armchair and a stack of books beside the hearth",
            ],
            {"intensity": 1.0, "brightness": 0.42, "window": True, "interior": 1.0, "fire": 1.0, "fire_sound": True,
             **INTERIOR_RAIN},
            style=INTERIOR_STYLE, negative=INTERIOR_NEGATIVE, comfy={"family": "zimage"}, post=NATURAL_POST, animals=True,
        ),
    ]
}


# 자연스러운 사진 톤을 쓰는 씬 (숲·시골·나뭇잎)
NATURAL_SCENES = ["cafe_window", "hanok_courtyard", "hanok_eaves", "hanok_cafe", "thatched_house", "jangdokdae",
                  "rain_leaves", "country_house", "forest_night", "forest_path", "cabin_window",
                  "tent", "forest_lake", "valley_stream", "temple_path", "thunder_forest",
                  "tent_view_mountains", "tent_view_stream", "tent_view_valley", "tent_by_stream",
                  "tent_meadow", "tent_pine_grove", "tent_lakeside", "tent_car_camp", "tent_interior_view"]
for _name in NATURAL_SCENES:
    _s = SCENES[_name]
    _s.style = NATURAL_STYLE
    _s.comfy = {**NATURAL_COMFY, **_s.comfy}
    _s.post = {**NATURAL_POST, **_s.post}
    _s.negative = ", ".join(x for x in (_s.negative, NATURAL_NEGATIVE) if x)

# v11.22: 사실적인 질감이 필요한 산·숲·개울 장면은 Z-Image (SDXL 은 나무·산이 AI 같고 흐림)
for _name in ("tent_view_mountains", "tent_view_stream", "tent_view_valley", "tent_by_stream", "tent_meadow", "tent_pine_grove", "tent_lakeside", "tent_car_camp", "tent_interior_view"):
    SCENES[_name].comfy = {**SCENES[_name].comfy, "family": "zimage"}
for _name in ("tent", "tent_view_mountains", "tent_view_stream", "tent_view_valley", "tent_car_camp", "tent_interior_view"):      # v11.23: 텐트 안에서 바깥을 보는 장면 — 비는 열린 바깥에만, 바깥 땅에는 빗방울이 튀게
    SCENES[_name].rain = {**SCENES[_name].rain, "outside_only": True, "splashes": True,
                          **({"veil": 0.0, "splash_gain": 0.6, "wet_streams": 0.0} if _name in ("tent_view_mountains", "tent_view_stream", "tent_view_valley") else {})}


# v11.20: 물·안개가 거의 없는 씬은 Wan(AI 물 움직임)을 기본으로 건너뜀 (실행해도 '움직임 없음'이라 시간만 2~15분 낭비)
for _name in ("forest_path", "autumn_forest_path", "autumn_temple", "rain_leaves", "cafe_window", "cabin_window",
              "hanok_cafe", "city_night", "night_park", "temple_path", "tent", "country_house", "tent_view_mountains"):
    SCENES[_name].rain["wan_ok"] = False


def get_scene(name):
    try:
        return SCENES[name]
    except KeyError:
        raise SystemExit(f"알 수 없는 씬: {name!r}. 사용 가능: {', '.join(SCENES)}")
