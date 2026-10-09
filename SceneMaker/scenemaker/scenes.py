"""somnia-forest 씬 프리셋: SD 프롬프트 + 빗줄기 오버레이 기본값."""

import random
from dataclasses import dataclass, field

STYLE = (
    "cinematic photograph, photorealistic, highly detailed, soft diffused light, "
    "muted desaturated green and teal tones, calm peaceful sleepy atmosphere, "
    "depth of field, film grain, 35mm"
)

# AI 티를 줄인 자연스러운 사진 톤 — 완벽하지 않되, 색은 생생하고 질감은 선명하게
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

NEGATIVE = (
    "people, person, human, animal, text, watermark, logo, signature, frame, border, "
    "cartoon, anime, illustration, painting, 3d render, oversaturated, harsh light, "
    "lowres, blurry, jpeg artifacts, deformed, bad composition, sunny, bright blue sky"
)

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

    def build_prompt(self, rng: random.Random, extra: str = ""):
        parts = [self.prompt]
        if self.variations:
            parts.append(rng.choice(self.variations))
        if extra:
            parts.append(extra)
        parts.append(self.style or STYLE)
        negative = f"{NEGATIVE}, {self.negative}" if self.negative else NEGATIVE
        return ", ".join(parts), negative


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
            "curved wooden rafters (seokkarae), wooden maru floor, flat stepping stone with white rubber shoes, "
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
            {"intensity": 0.7, "brightness": 0.3, "fog": 0.0, "splashes": False, "darken": 0.03},
            negative=HANOK_NEGATIVE,
            lora=HANOK_LORA,
            comfy={"checkpoint": HANOK_BASE, "family": "zimage"},   # 한옥 건축 = Z-Image (SDXL 선택 시 LoRA 기준 모델)
        ),
        Scene(
            "thatched_house",
            "초가집 빗소리",
            "old Korean thatched roof farmhouse in the summer rain, thick rounded rice straw roof with no tiles, "
            "clay walls, "
            "wooden doors, dirt yard with puddles, brushwood fence, green hills behind",
            [
                "onggi earthenware jars beside the house",
                "view from the narrow wooden veranda under the straw eaves",
                "a big old tree beside the house, overcast",
                "rice paddy in front of the house",
            ],
            {"intensity": 1.0, "angle": 4.0, "fog": 0.1},
            negative=HANOK_NEGATIVE,
            lora=KOREA_LORA,
            comfy={"checkpoint": HANOK_BASE},
        ),
        Scene(
            "jangdokdae",
            "장독대 빗소리",
            "many Korean onggi earthenware jars on a stone platform in the rain, wet glossy dark brown jars, "
            "raindrops on the lids, stone wall topped with roof tiles behind, green garden",
            [
                "hanok eaves visible at the top",
                "green ivy on the stone wall behind the jars",
                "close view of a few jars, shallow depth of field",
            ],
            {"intensity": 0.9, "angle": 3.0, "fog": 0.05},
            negative=HANOK_NEGATIVE,
            lora=KOREA_LORA,
            comfy={"checkpoint": HANOK_BASE},
        ),
        Scene(
            "country_house",
            "여름 시골집 마루",
            "old Korean countryside house in summer rain, view from a worn wooden maru floor, "
            "slate or tin roof edge dripping, vegetable garden and green hills, electric fan and floor cushion, "
            "nostalgic rural Korea",
            [
                "lush green rice paddies in the distance, overcast",
                "late afternoon, soft light, cicada summer mood",
            ],
            {"intensity": 1.0, "angle": 5.0, "fog": 0.1},
            negative=HANOK_NEGATIVE,
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
            "small shops with warm lights, shop signs far away and out of focus as soft bokeh, parked cars, no people",
            [
                "narrow alley, shallow depth of field",
                "view from a high window, city lights blurred by rain",
            ],
            {"intensity": 1.0, "angle": 5.0, "brightness": 0.6, "fog": 0.08, "darken": 0.04},
            negative="readable text, letters, hangul, kanji, chinese characters, typography, signage text",
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
            {"intensity": 0.6, "angle": 2.0, "fog": 0.12, "brightness": 0.45},
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
            "branches of a leafy tree in a backyard on a rainy day, photographed from a few meters away, "
            "many small and medium green leaves at different angles and depths, natural leaf texture, "
            "a few leaves with tiny holes, wet but without large water droplets, background softly out of focus",
            [
                "zelkova tree branches, small serrated leaves",
                "cherry tree branches with small green leaves",
                "maple branches in summer, fresh green",
                "grape vine on an old wooden trellis",
                "dense shrubs and tree branches along a stone wall",
            ],
            {"intensity": 0.9, "angle": 3.0, "brightness": 0.45, "fog": 0.0, "splashes": False,
             "darken": 0.04},
            negative="fruit, berries, flowers",
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
            "view from inside a simple wooden cabin at a Korean recreational forest looking out a window "
            "at a rainy mountain slope with slender pine and oak trees, water droplets on the window glass, "
            "plain wooden window frame, a mug on the windowsill, dim indoor light",
            [
                "grey rainy afternoon, soft light",
                "evening, warm lamp inside, dark blue outside",
                "summer, fresh green leaves outside",
            ],
            {"intensity": 0.8, "brightness": 0.35, "fog": 0.0, "splashes": False, "darken": 0.05},
            negative=FOREST_NEGATIVE + ", log cabin, fireplace, candles, luxury",
        ),
        Scene(
            "tent",
            "비 오는 캠핑장 텐트",
            "a dome tent under a tarp at a Korean mountain campground on a rainy day, wooden deck camping site, "
            "camping chair and a small lantern, wet gravel, slender pine and oak trees around, overcast",
            [
                "dusk, lantern glowing warmly under the tarp",
                "daytime, grey rainy light, light mist on the mountain",
                "view from inside the tent through the open door",
            ],
            {"intensity": 1.0, "brightness": 0.45, "darken": 0.08, "fog": 0.1},
            negative=FOREST_NEGATIVE + ", glamping, fairy lights, bonfire",
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
    ]
}


# 자연스러운 사진 톤을 쓰는 씬 (숲·시골·나뭇잎)
NATURAL_SCENES = ["cafe_window", "hanok_courtyard", "hanok_eaves", "hanok_cafe", "thatched_house", "jangdokdae",
                  "rain_leaves", "country_house", "forest_night", "forest_path", "cabin_window",
                  "tent", "forest_lake", "valley_stream", "temple_path", "thunder_forest"]
for _name in NATURAL_SCENES:
    _s = SCENES[_name]
    _s.style = NATURAL_STYLE
    _s.comfy = {**NATURAL_COMFY, **_s.comfy}
    _s.post = {**NATURAL_POST, **_s.post}
    _s.negative = ", ".join(x for x in (_s.negative, NATURAL_NEGATIVE) if x)


def get_scene(name):
    try:
        return SCENES[name]
    except KeyError:
        raise SystemExit(f"알 수 없는 씬: {name!r}. 사용 가능: {', '.join(SCENES)}")
