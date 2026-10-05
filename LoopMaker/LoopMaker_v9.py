# -*- coding: utf-8 -*-
"""
LoopMaker v10 — 무한루프 영상 + 유튜브 패키지 + 숏폼 생성기
Somnia Forest 전용 도구
(파일명은 하위 호환을 위해 LoopMaker_v9.py 그대로 유지 — 바탕화면 바로가기/배치파일 안 깨짐)

v11.19 신규 (2026-10-05): 🌙 이야기 서재 + 잠자리 창작 스타일 (구독자 피드백 반영)
 - 셜록 홈즈 외에 잠자기 좋은 이야기를 골라 듣기: 연재형 4종(전래동화·세계 명작 동화·포근한 고전 소설·한국 고전/근대 문학,
   서재마다 목록/진행상태 파일이 따로 있어 영상마다 이어서) + 창작형 5종(새 옛이야기·숲과 호수 산책·밤 여행·작은 가게·수면 명상)
 - 기본 선택을 잠자리용(전래동화)으로 변경, 셜록 홈즈는 '명작 추리 연재(긴장감 있음)'로 남겨 둠 — 기존 진행상태 파일 그대로 호환

v11.18 신규 (2026-09-30): 🌧 AI 배경 탭 — E:/SceneMaker 연결
 - AI 배경 이미지 생성(ComfyUI, 꺼져 있으면 자동으로 켬) → 목록·미리보기로 고르기
 - 빗줄기·물 효과 루프 영상(1440p, 40GB 이하) → 완성되면 유튜브 패키지 탭에 자동 입력
 - 바탕화면 'AI 배경 만들기' 아이콘: LoopMaker_v9.py --scene 으로 이 탭부터 열림

v11 신규 (2026-09-26): 🌙 스토리 내레이션 탭
 - Claude 미스터리 작가 에이전트가 영상 장면에 맞춘 잠자리 미스터리 이야기를 창작
   (바이블 설계 → 장별 집필, 긴 이야기도 설정이 흔들리지 않게)
 - 남성 3 / 여성 3 AI 성우 선택 + 미리 듣기 + 6명 비교 듣기 (edge-tts, 최초 1회 자동 설치)
 - 문장 단위 녹음 + 문장/문단 쉼 + 빗소리 더킹 믹싱 + 유튜브용 SRT 자막 자동 생성

v10 신규 (2026-09-06 종합 점검):
 1. 루프 경계 끊김/튐 버그 3종 근본 수정 (concat-copy, 크로스페이드 수렴 지점,
    변수 이름 충돌로 품질 기준 선택이 무력화되던 버그) — 합성 영상으로 실측 검증
 2. 2초~5분 다중 길이 후보 탐색 + 빗줄기 등 순간 노이즈에 강한 매칭 + 필요시
    서로 다른 두 구간 이어붙이기(동일 수렴 버그 포함 수정)
 3. 렌더링 속도 개선(4K 소스 기준 약 5시간 → 65분) + 비트레이트 상한 도입
    (무제한 화질모드가 165GB까지 치솟던 문제 → 예측 가능한 크기로)
 4. 고정 주제 목록(TOPICS) 제거 → Claude Code CLI 연동 자동 분석(영상 내용 파악
    + 실시간 웹 검색 + 주제/썸네일 3종/설명 도입부 자동 생성, 전부 수정 가능)
 5. 유튜브 설명란: 한글 우선 순서, 문장 단위 줄바꿈 가독성 개선, 글자수 확인
 6. 숏폼 텍스트 잘림 버그 수정 + 항상 간결한 주제만 사용하도록 개선
 7. 인트로 자막 신규: 영상 맨 앞부분에만 한 번(반복 없음) 한글+영문 자막을
    서서히 표시 — 화면에서 직접 확인/수정 가능, 검증 후 원본 자동 교체(중복 방지)
 8. "단위 반복" 모드가 실제로는 아무 동작도 안 하던 버그 수정(이제 진짜로
    탐색·스무딩을 건너뛰고 지정한 길이를 그대로 사용)
 9. 스레드 안전성 버그 다수 수정 (백그라운드 스레드에서 tkinter 변수 접근)

v7 신규 (유튜브 패키지 탭):
 1. 완성 영상에서 썸네일 3종 자동 생성 (프레임 3곳 추출 + 인기 텍스트 오버레이)
    → 유튜브 A/B 테스트 안전 조합(제목 2 + 썸네일 3)에 맞춤
 2. 주제별 SEO 템플릿: 영어 우선 제목 2종 / 이중언어 설명 / 태그(500자 이내 자동 검증)
 3. 루프 제작 완료 시 패키지 탭에 영상 경로 자동 입력
 4. 결과물: 영상이름_youtube 폴더에 thumb_1~3.png, 제목.txt, 설명.txt, 태그.txt

v6.1: 연속 작업 버튼 복구 버그 수정 / v6: 오디오 페이드 자동 제거 + 평탄화
v5: 실제 프레임 기반 모션 보간 (잔상 저감)

필요: Python 3.8+, numpy, Pillow(pip install pillow), ffmpeg/ffprobe (PATH 등록)
"""

import os
import sys
import math
import shutil
import tempfile
import threading
import subprocess
import struct
import time
import queue
import re
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import numpy as np
except ImportError:
    import tkinter.messagebox as mb
    _r = tk.Tk(); _r.withdraw()
    mb.showerror("numpy 필요", "numpy가 설치되어 있지 않습니다.\n\n명령 프롬프트에서:\npip install numpy")
    sys.exit(1)

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"

# Windows에서 콘솔창 안 뜨게
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

DUR_PRESETS = [
    ("3분 (테스트)", 180),
    ("10분", 600),
    ("30분", 1800),
    ("1시간", 3600),
    ("2시간", 7200),
    ("3시간", 10800),
    ("5시간", 18000),
    ("8시간", 28800),
    ("10시간", 36000),
    ("12시간", 43200),
]

SMOOTH_PRESETS = {
    # 이름: (보간배수, trim시작, trim끝)  → 중간 모프 프레임 수 = trim끝 - trim시작
    "표준 (3프레임)": (4, 5, 8),
    "강 (5프레임)": (6, 7, 12),
}
CROSSFADE_PRESETS = {
    "크로스페이드 0.15초 (권장)": 0.15,
    "크로스페이드 0.5초": 0.5,
    "크로스페이드 1.0초 (느린 장면)": 1.0,
    "크로스페이드 1.5초 (매우 느린 장면)": 1.5,
}
ALL_SMOOTH = {**SMOOTH_PRESETS, **{k: None for k in CROSSFADE_PRESETS}}


# ==================== 한글 주제 → 영어 자동 변환 (v8.4) ====================
KO_EN_TOPIC = [
    ("천둥번개", "Thunderstorm"), ("눈내리는", "Snowfall"), ("통나무집", "Log Cabin"),
    ("파도소리", "Ocean Waves"), ("시냇물", "Stream"), ("호숫가", "Lakeside"),
    ("빗소리", "Rain"), ("벽난로", "Fireplace"), ("모닥불", "Campfire"), ("불멍", "Campfire"),
    ("밤바다", "Night Ocean"), ("바닷가", "Beach"), ("소나기", "Rain Shower"),
    ("가랑비", "Light Rain"), ("이슬비", "Drizzle"), ("비오는", "Rainy"),
    ("대나무", "Bamboo"), ("나뭇잎", "Leaves"), ("숲속", "Forest"),
    ("폭우", "Heavy Rain"), ("장마", "Monsoon Rain"), ("천둥", "Thunder"),
    ("폭풍", "Storm"), ("태풍", "Typhoon"), ("해변", "Beach"), ("파도", "Waves"),
    ("바다", "Ocean"), ("창문", "Window"), ("지붕", "Rooftop"), ("우산", "Umbrella"),
    ("텐트", "Tent"), ("캠핑", "Camping"), ("도시", "City"), ("골목", "Alley"),
    ("카페", "Cafe"), ("기차", "Train"), ("호수", "Lake"), ("계곡", "Mountain Stream"),
    ("폭포", "Waterfall"), ("강가", "Riverside"), ("겨울", "Winter"),
    ("새벽", "Dawn"), ("아침", "Morning"), ("저녁", "Evening"), ("정원", "Garden"),
    ("사찰", "Temple"), ("한옥", "Hanok"), ("숙면", "Deep Sleep"), ("수면", "Sleep"),
    ("명상", "Meditation"), ("힐링", "Healing"), ("숲", "Forest"), ("눈", "Snow"),
    ("밤", "Night"),
]

def ko_to_en_topic(kr):
    """한글 주제에서 키워드를 찾아 자연스러운 영어 주제로 조합"""
    if not kr:
        return ""
    used = [False] * len(kr)
    hits = []
    for key, en in sorted(KO_EN_TOPIC, key=lambda x: -len(x[0])):
        start = 0
        while True:
            i = kr.find(key, start)
            if i < 0:
                break
            if not any(used[i:i + len(key)]):
                hits.append((i, en))
                for j in range(i, i + len(key)):
                    used[j] = True
            start = i + len(key)
    hits.sort()
    out = []
    for _, en in hits:
        if not out or out[-1] != en:
            out.append(en)
    return " ".join(out)


# ==================== v9.6: Claude Code 자동 장면 분석 ====================
CLAUDE_ANALYSIS_PROMPT = """다음 이미지 파일들을 Read 도구로 열어서 봐줘 (같은 영상에서 뽑은 서로 다른 장면들이야):
{frames}

이 영상은 유튜브 수면/힐링 ASMR 채널(빗소리·자연의 소리 계열, 10시간 루프 영상)에 올릴 배경 영상이야.

1. 이미지를 보고 실제로 어떤 장면인지 정확히 파악해줘 (예: 숲, 호수, 통나무집, 벽난로, 창문, 도시, 바다,
   폭포, 정원 등 — 실제로 보이는 것만, 없는 걸 지어내지 말 것. 예: 불이 안 보이면 벽난로라고 하지 말 것)
2. 웹 검색을 해서 이 장면과 가장 잘 맞으면서 실제로 유튜브에서 검색량/조회수가 높은
   한글 키워드와 영문 키워드를 각각 하나씩 찾아줘 (수면/ASMR/빗소리 채널 기준).
3. 그 키워드를 바탕으로 서로 다른 썸네일 문구 3세트(A/B 테스트용)를 만들어줘.
   ★ 2026년 유튜브 썸네일 고성과 공식: 메인 문구는 언어별 3~5단어(한글은 3~5어절)를
   절대 넘기지 말 것 — 짧고 강렬할수록 클릭률이 높다(완전한 문장 금지, 설명은 제목이
   담당). 예: "잠이 솔솔" / "SO SLEEPY" (좋음) vs "잠이 솔솔 오는 편안한 빗소리입니다"
   (나쁨 — 너무 김). 각 세트는 메인 문구(짧게)와 부제목(메인보다 살짝 길어도 됨)으로
   구성하고, 각각 "한글 / ENGLISH" 형식으로 합쳐서 하나의 문자열로 만들어줘.
4. 유튜브 설명란에 쓸 실제 장면 묘사 문장을 한글/영문 한 줄씩 만들어줘 (과장 없이 실제 보이는 그대로,
   태그란 등에 재사용되는 짧은 문장 — 아래 5번의 긴 설명문과는 다른 용도).
5. 유튜브 설명란 맨 위에 들어갈 도입부를 한글 3~4문장, 영문 3~4문장으로 각각 써줘.
   단순히 "비가 내린다" 수준이 아니라, 이미지에서 실제로 보이는 구체적인 디테일(예: 어떤 식물/지형인지,
   빛이 어떤지, 빗방울이 잎에 맺히는 모습 등)과 그게 만들어내는 분위기·감정을 자연스럽게 녹여서,
   매번 다른 영상마다 겹치지 않고 그 영상만의 느낌이 드러나게 써줘. 문체는 따뜻하고 편안하게,
   광고 카피처럼 뻔한 상투어(그저 "완벽한 수면", "지금 바로" 같은 문구 남발)는 피해줘.
   이 문단 뒤에는 프로그램이 자동으로 타임라인/구독 안내/링크를 붙이니 그런 내용은 넣지 마.

다른 설명 없이, 아래 JSON 형식으로만 답해줘 (마크다운 코드블록 없이 순수 JSON만):
{{
  "topic_en": "영문 주제 (예: Cabin Porch Rain)",
  "topic_kr": "한글 주제 (예: 오두막 처마 빗소리)",
  "scene_en": "실제 장면을 묘사하는 영문 한 문장",
  "scene_kr": "실제 장면을 묘사하는 한글 한 문장",
  "description_en": "설명란 도입부 영문 3~4문장",
  "description_kr": "설명란 도입부 한글 3~4문장",
  "extra_tags": ["관련 태그", "..."],
  "thumbnails": [
    {{"main": "한글 / ENGLISH", "sub": "한글 / English"}},
    {{"main": "...", "sub": "..."}},
    {{"main": "...", "sub": "..."}}
  ]
}}"""


def call_claude_scene_analysis(video_path, log_fn, timeout=150):
    """v9.6: 영상에서 프레임 3장을 뽑아 Claude Code(CLI, claude -p)를 통해
    실제 장면 분석 + 웹 검색까지 시켜서 주제/썸네일 3종을 JSON으로 받아온다.
    별도 API 키 없이, 이 컴퓨터에 로그인된 Claude Code를 그대로 재사용한다."""
    tmp = tempfile.mkdtemp(prefix="claude_scene_")
    try:
        r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=nw=1:nk=1", video_path],
                           capture_output=True, creationflags=CREATE_NO_WINDOW)
        dur = float((r.stdout or b"").decode().strip() or 0)
        if dur <= 0:
            raise RuntimeError("영상 길이를 읽을 수 없습니다")

        frame_paths = []
        for i, pos in enumerate((0.15, 0.5, 0.85)):
            t = dur * pos
            fp = os.path.join(tmp, f"scene_{i}.png")
            subprocess.run([FFMPEG, "-v", "error", "-ss", f"{t:.2f}", "-i", video_path,
                            "-frames:v", "1", "-y", fp],
                           capture_output=True, creationflags=CREATE_NO_WINDOW)
            if os.path.exists(fp):
                frame_paths.append(fp)
        if not frame_paths:
            raise RuntimeError("프레임 추출 실패")

        prompt = CLAUDE_ANALYSIS_PROMPT.format(frames="\n".join(frame_paths))

        # v9.6 버그 수정: 윈도우에서 "claude"는 실제로 claude.cmd(배치 파일)라서
        # shutil.which로 확장자까지 포함해 정확히 찾아줘야 함 — 확장자 없이 그냥
        # "claude"만 넘기면 CreateProcess가 PATHEXT를 검색해주지 않아 항상
        # FileNotFoundError가 난다.
        claude_exe = shutil.which("claude")
        if not claude_exe:
            raise FileNotFoundError("claude 명령을 찾을 수 없습니다")

        # v9.6 버그 수정: 프롬프트를 커맨드라인 인자로 넘기면 claude.cmd(배치 파일)를
        # 거치는 과정에서 줄바꿈이 깨져 뒷부분(이미지 경로 등)이 유실됨 — 표준입력(stdin)
        # 으로 넘기면 줄바꿈이 그대로 보존된다 (실측으로 확인함).
        log_fn(f"  🤖 Claude Code 호출 중... (이미지 분석 + 웹 검색, 최대 {timeout}초 대기)")
        r = subprocess.run(
            [claude_exe, "-p", "--allowedTools", "Read", "WebSearch"],
            input=prompt, capture_output=True, timeout=timeout, creationflags=CREATE_NO_WINDOW,
            encoding="utf-8", errors="replace")
        if r.returncode != 0:
            raise RuntimeError("claude 실행 실패 (Claude Code가 설치·로그인되어 있는지 확인해주세요):\n"
                                + (r.stderr or "")[-500:])
        out = (r.stdout or "").strip()
        m = re.search(r"\{.*\}", out, re.DOTALL)
        if not m:
            raise RuntimeError("Claude 응답에서 JSON을 찾지 못했습니다:\n" + out[:300])
        data = json.loads(m.group(0))
        for key in ("topic_en", "topic_kr"):
            if not data.get(key):
                raise RuntimeError(f"Claude 응답에 '{key}' 값이 없습니다")
        return data
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ==================== 유튜브 SEO 주제 템플릿 (v7) ====================
BLOG_URL = "https://100years-checkup.tistory.com"
APP_URL = "https://seaheal.app"

COMMON_TAGS = ["rain sounds", "rain sounds for sleeping", "asmr", "sleep sounds",
               "relaxing rain", "white noise", "rain asmr", "deep sleep",
               "study sounds", "insomnia relief", "빗소리", "수면유도",
               "asmr 빗소리", "백색소음", "숙면"]

# =====================================================================
# v9.6: 고정 주제 목록(TOPICS)을 제거함 — 영상마다 항상 다른 새 주제를 쓰기 때문에
# 미리 정해둔 9개 주제 중 고르는 방식은 실사용에 맞지 않는다는 피드백에 따라,
# 이제 모든 패키지 생성은 (Claude 자동 분석이든 수동 입력이든) 그때그때 입력된
# en/kr/scene_en/scene_kr/extra_tags 값으로 그 자리에서 조립한다.
# =====================================================================


def find_font(size, korean=False):
    """v9.7: YTPackage와 Pipeline(인트로 자막) 둘 다 쓰는 폰트 탐색 로직 — 중복 방지를
    위해 모듈 레벨 함수로 뺌."""
    if korean:
        cands = [r"C:\Windows\Fonts\malgunbd.ttf", r"C:\Windows\Fonts\malgun.ttf",
                 "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
                 "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc",
                 "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"]
    else:
        cands = [r"C:\Windows\Fonts\impact.ttf", r"C:\Windows\Fonts\arialbd.ttf",
                 r"C:\Windows\Fonts\malgunbd.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    for c in cands:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
    return ImageFont.load_default()


SHORTS_SEC = 55          # v11.18: 숏폼 길이 30초 → 55초 (유튜브 숏폼 60초 이내)


def caption_free_start(total_sec, cap_sec=30.0, need_sec=SHORTS_SEC):
    """인트로 자막(맨 앞 cap_sec초 + 페이드)이 끝난 뒤, 자막이 전혀 없는 구간의
    시작 시각(초). 숏폼 영상·숏폼 커버·롱폼 썸네일은 여기서부터 뽑는다.
    영상이 너무 짧아(테스트용 등) 그럴 여유가 없으면 0을 돌려준다."""
    start = max(40.0, float(cap_sec) + 10.0)
    if total_sec < start + need_sec + 5.0:
        return 0.0
    return start


# ==================== v11: 🌙 내레이션 이야기 정보 (패키지 연동) ====================
STORY_SUMMARY_MAX = 50
STORY_TAGS = ["sleep story", "bedtime story", "mystery sleep story", "rain sleep story",
              "잠자리 이야기", "수면 동화", "미스터리 이야기", "잠 오는 이야기"]


def fit_summary(text, limit=STORY_SUMMARY_MAX):
    """요약을 공백 포함 limit자 이내로 — 넘치면 어절 단위로 자르고 …"""
    t = " ".join((text or "").split()).strip()
    if len(t) <= limit:
        return t
    cut = t[:limit - 1]
    if " " in cut[limit // 2:]:
        cut = cut[:cut.rfind(" ")]
    return cut.rstrip(" ,.·") + "…"


def story_info_path_for(video):
    """영상 경로 → 짝이 되는 story_info.json 경로 (없으면 None)
    - 영상이름_내레이션_성우.mp4 → 영상이름_story/story_info.json
    - 영상이름.mp4 → 영상이름_story/story_info.json"""
    if not video:
        return None
    root = os.path.splitext(video)[0]
    cands = []
    if "_내레이션_" in os.path.basename(root):
        cands.append(root[:root.rfind("_내레이션_")] + "_story")
    cands.append(root + "_story")
    for d in cands:
        f = os.path.join(d, "story_info.json")
        if os.path.exists(f):
            return f
    return None


def load_story_info(video):
    f = story_info_path_for(video)
    if not f:
        return None
    try:
        with open(f, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _sec_hms(t):
    t = int(max(0, t))
    return f"{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}"


def narr_thumb_subtitle(story):
    """내레이션 이야기 정보 → 썸네일 부제목 (이야기 없으면 None)"""
    t = ((story or {}).get("title") or "").strip()
    if not t:
        return None
    n = len((story or {}).get("episodes") or [])
    return f"잠들기 좋은 이야기 (제목: {t}" + (f" 외 {n - 1}편" if n >= 2 else "") + ")"


def shorts_start_for(video, total_sec, cap_sec=30.0):
    """v11.14: 숏폼 시작 지점 — 내레이션 영상이면 '이야기가 시작되는 순간'부터
    (제목 카드는 가로 화면용이라 세로로 자르면 잘리므로 그 직후부터), 아니면 기존대로 자막 없는 구간."""
    info = load_story_info(video)
    if info and info.get("start_sec") is not None:
        st = max(0.0, float(info["start_sec"]) - 0.5)
        if total_sec >= st + SHORTS_SEC + 2:
            return st, "이야기가 시작되는 부분부터 (내레이션 첫머리)"
    st = caption_free_start(total_sec, cap_sec)
    return st, (f"인트로 자막이 없는 {st:.0f}초 지점부터" if st > 0
                else "영상 맨 앞부터 (영상이 짧아 자막 구간을 피할 수 없음)")


class YTPackage:
    """완성 영상 → 썸네일 3종 + 제목/설명/태그 파일 생성 (v7)"""

    def __init__(self, log_fn):
        self.log = log_fn

    def _run(self, cmd):
        return subprocess.run(cmd, capture_output=True, creationflags=CREATE_NO_WINDOW)

    def _dur_label(self, seconds):
        h = seconds / 3600
        if h >= 1:
            n = int(round(h))
            return (f"{n} Hours" if n > 1 else "1 Hour"), f"{n}시간"
        m = int(seconds // 60)
        if m >= 1:
            return f"{m} Minutes", f"{m}분"
        return f"{int(seconds)} Seconds", f"{int(seconds)}초"

    def _find_font(self, size, korean=False):
        return find_font(size, korean)

    def _vignette_mask(self, w, h, strength=60):
        """가장자리를 살짝 어둡게 눌러 시선을 가운데로 모으는 비네트 알파 마스크."""
        ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
        cx, cy = w / 2.0, h / 2.0
        dist = np.sqrt(((xs - cx) / (w / 2.0)) ** 2 + ((ys - cy) / (h / 2.0)) ** 2)
        alpha = np.clip((dist - 0.55) / 0.55, 0.0, 1.0) * strength
        return Image.fromarray(alpha.astype(np.uint8), mode="L")

    def _band_gradient_mask(self, w, h, band_top, band_h, max_alpha=165):
        """텍스트가 들어갈 구간만 부드럽게 어둡게(그라데이션) — 사진 위에서도
        글자 대비가 확실히 살도록. 중앙이 가장 어둡고 위아래로 옅어짐."""
        ys = np.arange(h, dtype=np.float32)
        center = band_top + band_h / 2.0
        half = band_h / 2.0 + band_h * 0.45 + 40
        dist = np.abs(ys - center)
        alpha = np.clip(1.0 - dist / max(half, 1.0), 0.0, 1.0) ** 1.2 * max_alpha
        mask = np.tile(alpha[:, None], (1, w)).astype(np.uint8)
        return Image.fromarray(mask, mode="L")

    def _make_thumb(self, video, t, text, subtext, dur_text, out_png, tmp,
                    pos_mode="상단"):
        frame = os.path.join(tmp, "thumb_src.png")
        r = self._run([FFMPEG, "-v", "error", "-ss", f"{t:.2f}", "-i", video,
                       "-frames:v", "1", "-y", frame])
        if r.returncode != 0 or not os.path.exists(frame):
            raise RuntimeError("썸네일 프레임 추출 실패")

        img = Image.open(frame).convert("RGB")
        tw, th = 1280, 720
        scale = max(tw / img.width, th / img.height)
        img = img.resize((int(img.width * scale + 0.5), int(img.height * scale + 0.5)),
                         Image.LANCZOS)
        left = (img.width - tw) // 2
        top = (img.height - th) // 2
        img = img.crop((left, top, left + tw, top + th))

        # ★ v9.8 디자인 개선: 2026년 유튜브 썸네일 트렌드(고대비, 배경 정리로
        # 시선 집중) 반영 — 비네트로 가장자리를 정리하고, 사진 그대로 위에
        # 글자를 얹으면 배경에 따라 잘 안 보일 수 있어서 텍스트 구간에만
        # 부드러운 그라데이션을 깔아 대비를 확실히 살린다.
        vign = self._vignette_mask(tw, th, strength=55)
        black_full = Image.new("RGB", (tw, th), (0, 0, 0))
        img = Image.composite(black_full, img, vign)
        draw = ImageDraw.Draw(img)

        def draw_outlined(txt, x, y, font, stroke, fill=(255, 255, 255),
                          shadow=True, anchor=None):
            if shadow:
                off = max(2, stroke // 2 + 2)
                draw.text((x + off, y + off), txt, font=font, fill=(0, 0, 0),
                          stroke_width=stroke, stroke_fill=(0, 0, 0), anchor=anchor)
            draw.text((x, y), txt, font=font, fill=fill,
                      stroke_width=stroke, stroke_fill=(10, 10, 10), anchor=anchor)

        # ── 1) 먼저 크기 측정 (메인 + 부제목 블록 높이 계산) ──
        #    v8.2: 글자 수에 맞춰 화면 폭을 최대로 채우는 크기로 자동 확대/축소
        main_size, font, main_bbox = 260, None, None
        if text.strip():
            has_kr = bool(re.search(r"[가-힣]", text))
            font = self._find_font(main_size, has_kr)
            while main_size > 40:
                main_bbox = draw.textbbox((0, 0), text, font=font, stroke_width=8)
                if main_bbox[2] - main_bbox[0] <= tw * 0.9:
                    break
                main_size -= 8
                font = self._find_font(main_size, has_kr)
            main_bbox = draw.textbbox((0, 0), text, font=font, stroke_width=8)

        sub_size, sfont, sub_bbox = 0, None, None
        if subtext.strip():
            sub_size = max(28, (main_size if text.strip() else 100) // 2)
            has_kr = bool(re.search(r"[가-힣]", subtext))
            sfont = self._find_font(sub_size, has_kr)
            while sub_size > 22:
                sub_bbox = draw.textbbox((0, 0), subtext, font=sfont, stroke_width=5)
                if sub_bbox[2] - sub_bbox[0] <= tw * 0.85:
                    break
                sub_size -= 4
                sfont = self._find_font(sub_size, has_kr)
            sub_bbox = draw.textbbox((0, 0), subtext, font=sfont, stroke_width=5)

        gap = 18
        block_h = 0
        if main_bbox:
            block_h += (main_bbox[3] - main_bbox[1])
        if sub_bbox:
            block_h += gap + (sub_bbox[3] - sub_bbox[1])

        # ── 2) 위치 모드에 따라 블록 시작 y 결정 ──
        # ★ v9.8 버그 수정: '상단' 여백이 너무 좁아서(0.07) 왼쪽 위 브랜드 배지와
        # 제목 글자가 거의 붙어(심하면 겹쳐) 보였다. 배지 아래로 확실히 떨어지도록
        # 여백을 넉넉히 늘림.
        if pos_mode == "중앙":
            y = max(int(th * 0.06), (th - block_h) // 2)
        elif pos_mode == "하단":
            y = max(int(th * 0.06), int(th * 0.90) - block_h)
        else:  # 상단 (기본)
            y = int(th * 0.17)

        # ★ v9.8: 텍스트가 들어갈 구간에 그라데이션을 깔아 대비를 확실히 살림
        # (밝은 배경 사진 위에서도 흰 글자가 묻히지 않게)
        if block_h > 0:
            band = self._band_gradient_mask(tw, th, y, block_h)
            img.paste(Image.new("RGB", (tw, th), (0, 0, 0)), (0, 0), band)

        # ── 3) 그리기 ──
        if main_bbox:
            tx = (tw - (main_bbox[2] - main_bbox[0])) // 2 - main_bbox[0]
            draw_outlined(text, tx, y - main_bbox[1], font, stroke=8)
            y += (main_bbox[3] - main_bbox[1]) + gap
        if sub_bbox:
            sx = (tw - (sub_bbox[2] - sub_bbox[0])) // 2 - sub_bbox[0]
            draw_outlined(subtext, sx, y - sub_bbox[1], sfont, stroke=5,
                          fill=(255, 200, 60))   # v9.8: 더 진한 골드 — 메인과 대비 강화

        # ★ v9.8: 채널 브랜드/길이 표시를 맨글씨 대신 반투명 배지(badge)로 — 어떤
        # 배경 사진 위에서도 항상 또렷하게 보이도록. RGB 이미지에는 반투명 색을
        # 직접 그릴 수 없어서, 별도 RGBA 오버레이에 배지 배경만 그린 뒤 합성한다.
        badges = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        bdraw = ImageDraw.Draw(badges)

        bfont = self._find_font(30, False)
        bb = draw.textbbox((0, 0), "Somnia Forest", font=bfont, stroke_width=2)
        bpad_x, bpad_y = 16, 10
        badge = (16, 16, 16 + (bb[2] - bb[0]) + bpad_x * 2, 16 + (bb[3] - bb[1]) + bpad_y * 2)
        bdraw.rounded_rectangle(badge, radius=10, fill=(10, 10, 10, 160))

        dur_text = dur_text.strip()
        dbadge = None
        if dur_text:
            dsize = max(34, min(64, (main_size if text.strip() else 150) // 4))
            dfont = self._find_font(dsize, False)
            dbb = draw.textbbox((0, 0), dur_text, font=dfont, stroke_width=3)
            dpad_x, dpad_y = 14, 8
            dw, dh = (dbb[2] - dbb[0]) + dpad_x * 2, (dbb[3] - dbb[1]) + dpad_y * 2
            dbadge = (tw - 16 - dw, th - 16 - dh, tw - 16, th - 16)
            bdraw.rounded_rectangle(dbadge, radius=10, fill=(10, 10, 10, 160))

        img = Image.alpha_composite(img.convert("RGBA"), badges).convert("RGB")
        draw = ImageDraw.Draw(img)

        draw.text((badge[0] + bpad_x, badge[1] + bpad_y - bb[1]), "Somnia Forest",
                  font=bfont, fill=(240, 240, 240), stroke_width=2, stroke_fill=(0, 0, 0))
        if dur_text and dbadge:
            draw.text((dbadge[0] + dpad_x, dbadge[1] + dpad_y - dbb[1]), dur_text,
                      font=dfont, fill=(255, 210, 90), stroke_width=3, stroke_fill=(0, 0, 0))

        img.save(out_png, "PNG")

    # ---------- 숏폼(Shorts) 생성 (v8) ----------
    def _make_shorts(self, video, main_text, sub_text, dur_en, dur_kr, out_path, tmp,
                     length=SHORTS_SEC, crop_mode="중앙", start=0.0, cover_path=None):
        """루프 영상의 start초 지점부터 length초를 9:16 세로(1080x1920)로 크롭하고
        숏폼 텍스트 오버레이. start는 인트로 자막이 끝난 뒤 구간을 쓰기 위한 것이고,
        cover_path를 주면 같은 구간에서 숏폼 커버 이미지(PNG)도 한 장 만든다."""
        W, H = 1080, 1920
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(ov)

        def draw_outlined(txt, x, y, font, stroke, fill=(255, 255, 255),
                          anchor=None):
            off = max(2, stroke // 2 + 2)
            draw.text((x + off, y + off), txt, font=font, fill=(0, 0, 0, 200),
                      stroke_width=stroke, stroke_fill=(0, 0, 0, 220), anchor=anchor)
            draw.text((x, y), txt, font=font, fill=fill,
                      stroke_width=stroke, stroke_fill=(10, 10, 10, 255), anchor=anchor)

        def fit_font(txt, start, max_w, stroke, min_size=36):
            has_kr = bool(re.search(r"[가-힣]", txt))
            size = start
            f = self._find_font(size, has_kr)
            while size > min_size:
                bb = draw.textbbox((0, 0), txt, font=f, stroke_width=stroke)
                if bb[2] - bb[0] <= max_w:
                    break
                size -= 6
                f = self._find_font(size, has_kr)
            bb = draw.textbbox((0, 0), txt, font=f, stroke_width=stroke)
            # ★ v10 안전장치: 예상보다 훨씬 긴 문구(예: 장면 설명 문장)가 실수로
            # 들어와도 최소 크기에서까지 폭을 넘치면 화면 밖으로 잘려 보이던 문제.
            # 최소 크기에서도 넘치면 글자 수를 줄여가며 말줄임표(…)로 강제로 맞춘다
            # — 숏폼은 화면이 좁아 긴 자막이 절대 들어가면 안 되기 때문.
            base = txt
            while (bb[2] - bb[0]) > max_w and len(base) > 1:
                base = base[:-1].rstrip()
                txt = base + "…"
                bb = draw.textbbox((0, 0), txt, font=f, stroke_width=stroke)
            return txt, f, bb, size

        # 채널 브랜드 (왼쪽 위 — 숏폼 UI 안전영역 안)
        bfont = self._find_font(44, False)
        draw_outlined("Somnia Forest", 40, 90, bfont, stroke=4, fill=(235, 235, 235))

        # 메인 텍스트: 상단 시작 (v8.3: 긴 문구는 2줄 자동 분할 → 최대 크기)
        def split_two(txt):
            # 1순위: | 또는 / 구분자(한/영 병기 문구가 보통 이 형식), 2순위: 가운데에 가장 가까운 공백/가운뎃점
            for sep in ("|", "ㅣ", " / "):
                if sep in txt:
                    a, b = txt.split(sep, 1)
                    if a.strip() and b.strip():
                        return a.strip(), b.strip()
            mid = len(txt) // 2
            cands = [i for i, c in enumerate(txt) if c in " ·"]
            if not cands:
                return None
            k = min(cands, key=lambda i: abs(i - mid))
            a, b = txt[:k].strip(" ·"), txt[k:].strip(" ·")
            return (a, b) if a and b else None

        y = int(H * 0.12)
        main_size = 120
        if main_text.strip():
            main_text, f, bb, main_size = fit_font(main_text, 220, W * 0.94, 8)
            two = split_two(main_text) if main_size < 100 else None
            if two:
                # 두 줄 각각 최대로 키우고, 통일감을 위해 작은 쪽 크기로 맞춤
                two0, f1, bb1, s1 = fit_font(two[0], 200, W * 0.94, 8)
                two1, f2, bb2, s2 = fit_font(two[1], 200, W * 0.94, 8)
                size = min(s1, s2)
                main_size = size
                for line in (two0, two1):
                    line, lf, lbb, _ = fit_font(line, size, W * 0.94, 8, min_size=size)
                    x = (W - (lbb[2] - lbb[0])) // 2 - lbb[0]
                    draw_outlined(line, x, y - lbb[1], lf, stroke=8)
                    y += (lbb[3] - lbb[1]) + 14
                y += 6
            else:
                x = (W - (bb[2] - bb[0])) // 2 - bb[0]
                draw_outlined(main_text, x, y - bb[1], f, stroke=8)
                y += (bb[3] - bb[1]) + 20
        if sub_text.strip():
            # ★ v9.7 버그 수정: 부제목은 최소 크기까지 줄여도 한 줄에 안 들어가면
            # 그대로 화면 밖으로 잘려나가고 있었음(메인 문구와 달리 2줄 분할이
            # 없었음). 최소 크기에서도 넘치면 "한글 / 영문" 구분자 기준으로
            # 2줄로 나눠서 각 줄을 최대 크기로 채운다. (fit_font 자체도 v10에서
            # 말줄임표 강제 축소가 추가돼 이중으로 안전함)
            sub_max_w = W * 0.88
            sub_text, f, bb, sub_size = fit_font(sub_text, max(40, main_size // 2), sub_max_w, 5)
            overflow = (bb[2] - bb[0]) > sub_max_w
            two_s = split_two(sub_text) if overflow else None
            if two_s:
                s1 = fit_font(two_s[0], max(40, main_size // 2), sub_max_w, 5)[3]
                s2 = fit_font(two_s[1], max(40, main_size // 2), sub_max_w, 5)[3]
                size = min(s1, s2)
                for line in two_s:
                    line, lf, lbb, _ = fit_font(line, size, sub_max_w, 5, min_size=size)
                    x = (W - (lbb[2] - lbb[0])) // 2 - lbb[0]
                    draw_outlined(line, x, y - lbb[1], lf, stroke=5, fill=(255, 200, 60))
                    y += (lbb[3] - lbb[1]) + 10
            else:
                x = (W - (bb[2] - bb[0])) // 2 - bb[0]
                draw_outlined(sub_text, x, y - bb[1], f, stroke=5, fill=(255, 200, 60))

        cover_ov_png = None
        if cover_path:
            # 커버 이미지에는 본편 유도 문구(CTA)를 넣지 않는다 — 브랜드+제목만
            cover_ov_png = os.path.join(tmp, "shorts_cover_overlay.png")
            ov.save(cover_ov_png, "PNG")

        # 본편 유도 문구 (영어 + 한글 2줄): 하단, 숏폼 UI가 가리는 최하단 15%는 피함
        if dur_en.strip():
            # v10: 끝의 ▶/👆 기호는 쓰는 폰트에 글리프가 없어 네모(▯)로 깨져 보였다 → 제거
            cta_en = "Full video on the channel"
            cta_kr = "롱폼 영상은 채널에서"
            cy = int(H * 0.74)
            cta_en, f, bb, _ = fit_font(cta_en, 56, W * 0.85, 5)
            x = (W - (bb[2] - bb[0])) // 2 - bb[0]
            draw_outlined(cta_en, x, cy - bb[1], f, stroke=5, fill=(180, 225, 255))
            cy += (bb[3] - bb[1]) + 16
            cta_kr, f, bb, _ = fit_font(cta_kr, 50, W * 0.85, 5)
            x = (W - (bb[2] - bb[0])) // 2 - bb[0]
            draw_outlined(cta_kr, x, cy - bb[1], f, stroke=5, fill=(255, 200, 60))

        ov_png = os.path.join(tmp, "shorts_overlay.png")
        ov.save(ov_png, "PNG")

        # 9:16 크롭 (위치 선택) → 1080x1920 → 오버레이 → SHORTS_SEC초 (끝 1.5초는 소리·화면 페이드아웃)
        crop_x = {"왼쪽": "0", "오른쪽": "iw-ow"}.get(crop_mode, "(iw-ow)/2")
        crop_scale = f"crop=trunc(ih*9/16/2)*2:ih:{crop_x}:0,scale=1080:1920"
        r = self._run([
            FFMPEG, "-v", "error", "-ss", f"{start:.3f}", "-t", str(length),
            "-i", video, "-i", ov_png,
            "-filter_complex",
            (f"[0:v]{crop_scale},format=yuv420p[v];"
             f"[v][1:v]overlay=0:0:format=auto,format=yuv420p,"
             f"fade=t=out:st={max(0.0, length - 1.5):.2f}:d=1.5[out]"),
            "-map", "[out]", "-map", "0:a?",
            "-af", f"afade=t=out:st={max(0.0, length - 1.5):.2f}:d=1.5",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", "-y", out_path])
        if r.returncode != 0:
            raise RuntimeError("숏폼 생성 실패:\n" + r.stderr.decode("utf-8", "ignore")[-400:])

        if cover_path:
            t_cover = start + min(4.0, length / 2.0)
            r = self._run([
                FFMPEG, "-v", "error", "-ss", f"{t_cover:.3f}", "-i", video,
                "-i", cover_ov_png,
                "-filter_complex",
                (f"[0:v]{crop_scale},format=rgba[v];"
                 "[v][1:v]overlay=0:0:format=auto,format=rgb24[out]"),
                "-map", "[out]", "-frames:v", "1", "-y", cover_path])
            if r.returncode != 0:
                raise RuntimeError("숏폼 커버 이미지 생성 실패:\n"
                                   + r.stderr.decode("utf-8", "ignore")[-400:])

    def _write_shorts_txt(self, pkg, thumb_text, dur_en, channel_url):
        s_title = f"{thumb_text} 🌧️ Relaxing Rain #shorts" if not dur_en.strip() else \
                  f"{thumb_text} 🌧️ {dur_en} of Pure Rain #shorts"
        s_tags = "#shorts #rainsounds #asmr #sleep #빗소리 #relaxing #deepsleep"
        ch = (channel_url or "").strip()
        with open(os.path.join(pkg, "숏폼_제목설명태그.txt"), "w", encoding="utf-8") as f:
            f.write("━━━━━ ① 제목 (제목란에 복사) ━━━━━\n")
            f.write(f"{s_title}\n({len(s_title)}자)\n\n")
            f.write("━━━━━ ② 설명 (설명란에 아래 전체 복사) ━━━━━\n")
            f.write("Full video → " + (ch if ch else "(채널 주소)") + "\n")
            f.write("롱폼 영상 → " + (ch if ch else "(채널 주소)") + " 🌧️\n")
            f.write(s_tags + "\n\n")
            f.write("━━━━━ ③ 태그 안내 ━━━━━\n")
            f.write("숏폼은 태그 입력란이 노출에 거의 영향이 없어요.\n")
            f.write("위 설명에 포함된 #해시태그가 숏폼의 태그 역할을 합니다. (별도 태그 불필요)\n\n")
            f.write("━━━━━ ④ 업로드 후 꼭 하세요 (클릭 유도 3종 세트) ━━━━━\n")
            f.write("1. [가장 중요] 숏폼 업로드 화면 → '관련 동영상' → 롱폼 본편 영상 선택\n")
            f.write("   → 숏폼 화면에 본편으로 가는 공식 링크 버튼이 생깁니다\n")
            f.write("2. 위의 ② 설명을 설명란에 붙여넣기 (채널 링크 포함)\n")
            f.write("3. 본편 링크를 고정 댓글로 달기" + (f": {ch}" if ch else "") + "\n")

    def create_shorts(self, video, thumb_text, sub_text="", shorts_crop="중앙",
                      channel_url="", out_dir=None, cap_sec=30.0):
        """숏폼 전용 생성: shorts_55s.mp4 + shorts_thumb.png(커버) + 숏폼_제목설명태그.txt.
        인트로 자막이 들어간 맨 앞 구간을 피해, 자막이 없는 구간에서 뽑는다."""
        if not HAS_PIL:
            raise RuntimeError("Pillow가 필요합니다: pip install pillow")
        r = self._run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                       "-of", "default=nw=1:nk=1", video])
        seconds = float(r.stdout.decode().strip() or 0)
        if seconds <= 0:
            raise RuntimeError("영상 길이를 읽을 수 없습니다")
        dur_en, dur_kr = self._dur_label(seconds)
        base = os.path.splitext(os.path.basename(video))[0]
        pkg = out_dir or os.path.join(os.path.dirname(video), base + "_youtube")
        os.makedirs(pkg, exist_ok=True)
        tmp = tempfile.mkdtemp(prefix="ytpkg_")
        try:
            start, where = shorts_start_for(video, seconds, cap_sec)
            self.log(f"📱 55초 숏폼 생성 중... (9:16 {shorts_crop} 크롭 + 한/영 텍스트, {where})")
            shorts_mp4 = os.path.join(pkg, "shorts_55s.mp4")
            cover_png = os.path.join(pkg, "shorts_thumb.png")
            self._make_shorts(video, thumb_text, sub_text, dur_en, dur_kr,
                              shorts_mp4, tmp, length=SHORTS_SEC, crop_mode=shorts_crop,
                              start=start, cover_path=cover_png)
            self._write_shorts_txt(pkg, thumb_text, dur_en, channel_url)
            self.log(f"\n🎉 숏폼 생성 완료!\n📁 {pkg}\n"
                     "   shorts_55s.mp4 · shorts_thumb.png(숏폼 커버) · 숏폼_제목설명태그.txt")
            return pkg
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def _build_tags(self, extra):
        tags, total = [], 0
        for t in extra + COMMON_TAGS:
            add = len(t) + (1 if tags else 0)      # 쉼표 포함 길이
            if total + add > 500:
                break
            if t not in tags:
                tags.append(t)
                total += add
        return ", ".join(tags), total

    def _readable_paragraphs(self, text):
        """v9.7: 여러 문장이 한 줄에 붙어 있으면 유튜브 설명란에서 읽기 힘들어서,
        문장부호(.!?) 기준으로 문장마다 줄을 나눠 가독성을 높인다."""
        text = (text or "").strip()
        if not text:
            return text
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return "\n\n".join(s.strip() for s in sentences if s.strip())

    def _build_description(self, scene_en, scene_kr, dur_en, dur_kr, seconds,
                           desc_en=None, desc_kr=None, story=None):
        """v9.7: Claude 자동 분석이 만들어준 영상별 도입부(desc_en/desc_kr)가 있으면
        그걸 쓰고, 없으면(수동 입력 모드) 기존의 단순 템플릿 문장으로 대체한다.
        이전엔 항상 템플릿 한 문장만 써서 어떤 영상이든 설명이 거의 똑같아 보였음."""
        h = max(1, int(round(seconds / 3600)))
        mid = f"{h // 2:02d}:00:00" if h >= 2 else "00:30:00"
        end = f"{h:02d}:00:00"
        intro_en = (desc_en or "").strip() or (
            f"{dur_en} of {scene_en}. Fall asleep fast, stay asleep, and wake up refreshed. "
            "Perfect for deep sleep, studying, reading, meditation, or simply relaxing on a rainy day."
        )
        intro_kr = (desc_kr or "").strip() or (
            f"{dur_kr} 동안 이어지는 {scene_kr}. 불면증 완화, 공부, 독서, 명상에 활용해보세요."
        )
        # v9.7: 여러 문장이 한 덩어리로 붙어 있으면 읽기 힘드므로, 문장 단위로
        # 줄을 나눠 가독성을 높인다.
        intro_en = self._readable_paragraphs(intro_en)
        intro_kr = self._readable_paragraphs(intro_kr)
        # v11: 🌙 내레이션 이야기가 있으면 설명란 맨 앞 도입부 바로 아래에 이야기 제목 +
        # 50자 이내 요약을 넣고, 타임라인에도 이야기 시작/끝 지점을 표시한다.
        story_block, story_tl = "", ""
        if story and (story.get("title") or story.get("summary")):
            st = (story.get("title") or "").strip()
            sm = fit_summary(story.get("summary") or "")
            story_block = ("📖 오늘 밤 빗소리와 함께 들려드릴 이야기\n"
                           + (f"「{st}」\n" if st else "") + (f"{sm}\n" if sm else "")
                           + "Tonight's bedtime mystery story, softly narrated over the rain.\n\n")
            eps = story.get("episodes") or []
            if len(eps) >= 2:
                for k, ep in enumerate(eps, 1):
                    story_tl += f"{_sec_hms(ep['start_sec'])} — 🌙 {k}편 「{ep['title']}」\n"
                story_block = story_block.replace(
                    "Tonight's bedtime mystery story", f"{len(eps)} bedtime mystery stories")
                story_block = story_block.replace(
                    "📖 오늘 밤 빗소리와 함께 들려드릴 이야기\n",
                    f"📖 오늘 밤 빗소리와 함께 들려드릴 이야기 (총 {len(eps)}편)\n")
            elif story.get("start_sec") is not None:
                story_tl += f"{_sec_hms(story['start_sec'])} — 🌙 이야기 시작 · Story begins\n"
            if story.get("end_sec"):
                story_tl += f"{_sec_hms(story['end_sec'])} — 이야기 끝, 빗소리만 · Rain only\n"
        # v11.8: 타임라인은 시간순으로 정렬 (여러 편 이야기 시작 시각이 섞여도 순서가 맞게)
        tl = [("00:00:00", "비 시작 · Rain begins"), (mid, "깊은 수면 구간 · Deepest sleep zone"),
              (end, "끝 · End")]
        for ln in story_tl.splitlines():
            if " — " in ln:
                a_, b_ = ln.split(" — ", 1)
                tl.append((a_.strip(), b_.strip()))
        tl.sort(key=lambda x: x[0])
        timeline = "\n".join(f"{a_} — {b_}" for a_, b_ in tl)
        # v9.7: 사용자 요청으로 한글이 먼저, 영문이 뒤에 나오도록 전체 순서를 뒤집음
        # (도입부·타임라인·링크 안내·구독 문구 전부 동일하게 적용)
        return f"""🌙 {intro_kr}

{story_block}🌧️ {intro_en}

이 영상은 광고 없이 끊김 없이 10시간 내내 이어집니다.
No ads in the middle of your sleep — this is one continuous, seamless loop.

🎧 헤드폰으로 작은 소리로 들으시면 가장 좋아요.
Best experienced with headphones at low volume.

⏱ 타임라인 · TIMELINE
{timeline}

──────────────────
🌿 무료 자연의 소리 앱 (Free nature sound app):
{APP_URL}

💚 건강 블로그 (Health & longevity blog):
{BLOG_URL}

🔔 구독하시면 매주 새로운 빗소리를 만나실 수 있어요.
Subscribe for new rain & nature sounds every week!
──────────────────

#빗소리 #수면 #asmr #rainsounds #sleep
"""

    def create(self, video, en, kr, thumb_text, sub_text="", pos_mode="상단",
               out_dir=None, make_shorts=False, shorts_crop="중앙", channel_url="",
               extra_tags=None, scene_en=None, scene_kr=None, desc_en=None, desc_kr=None,
               thumb_variants=None, cap_sec=30.0, story=None):
        """v9.6: 고정 TOPICS 없이, 매번 en/kr(+선택: scene_en/scene_kr/extra_tags)로
        그 자리에서 제목·설명·태그 스캐폴드를 조립한다 (Claude 자동 분석 결과든 수동
        입력이든 동일한 경로로 처리)."""
        if not HAS_PIL:
            raise RuntimeError("Pillow가 필요합니다: pip install pillow")
        en, kr = (en or "").strip(), (kr or "").strip()
        if not en or not kr:
            raise RuntimeError("영어 주제와 한글 주제를 모두 입력해주세요")
        user_tags = [t.strip() for t in (extra_tags or []) if t.strip()]
        if not thumb_text.strip():
            thumb_text = en.upper()
        scene_en = (scene_en or f"{en.lower()} — a calm, immersive natural soundscape").strip()
        scene_kr = (scene_kr or kr).strip()
        titles = [
            f"{en} {{DUR}} 🌧️ Deep Sleep, Study, Insomnia Relief | {kr}",
            f"{en} Sounds {{DUR}} — Fall Asleep Fast, Relax, Focus | ASMR {kr}",
        ]
        extra_tags_all = user_tags + [en.lower(), f"{en.lower()} sounds", kr]
        # v11: 🌙 내레이션 이야기가 있으면 제목 부제목으로 이야기 제목을 붙인다.
        # 유튜브 제목 100자 제한을 넘으면 앞쪽 수식어를 짧은 버전으로 바꿔 맞춘다.
        story_title = ((story or {}).get("title") or "").strip()
        n_eps = len((story or {}).get("episodes") or [])
        if story_title:
            sub = f" — 🌙 「{story_title}」" + (f" 외 {n_eps - 1}편" if n_eps >= 2 else "")
            titles = [
                (f"{en} {{DUR}} 🌧️ Deep Sleep, Study, Insomnia Relief | {kr}{sub}",
                 f"{en} {{DUR}} 🌧️ Sleep Story | {kr}{sub}"),
                (f"{en} Sounds {{DUR}} — Fall Asleep Fast, Relax, Focus | ASMR {kr}{sub}",
                 f"{en} {{DUR}} — Mystery Sleep Story & Rain | {kr}{sub}"),
            ]
            extra_tags_all = user_tags + [en.lower(), kr] + STORY_TAGS + [f"{en.lower()} sounds"]

        r = self._run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                       "-of", "default=nw=1:nk=1", video])
        seconds = float(r.stdout.decode().strip() or 0)
        if seconds <= 0:
            raise RuntimeError("영상 길이를 읽을 수 없습니다")
        dur_en, dur_kr = self._dur_label(seconds)

        base = os.path.splitext(os.path.basename(video))[0]
        pkg = out_dir or os.path.join(os.path.dirname(video), base + "_youtube")
        os.makedirs(pkg, exist_ok=True)
        tmp = tempfile.mkdtemp(prefix="ytpkg_")
        try:
            # 썸네일 3종 (A/B 테스트용) — 각각 다른 텍스트 (없으면 1번 문구 공용)
            self.log("① 썸네일 3종 생성 중...")
            variants = list(thumb_variants or [(thumb_text, sub_text)] * 3)
            while len(variants) < 3:
                variants.append((thumb_text, sub_text))
            free_from = caption_free_start(seconds, cap_sec, need_sec=5.0)
            for i, (pos, (mt, st)) in enumerate(zip((0.2, 0.5, 0.8), variants), 1):
                t = min(max(seconds * pos, free_from), max(0.0, seconds - 1))
                mt = (mt or "").strip() or thumb_text
                out_png = os.path.join(pkg, f"thumb_{i}.png")
                self._make_thumb(video, t, mt, (st or "").strip(), dur_en, out_png, tmp,
                                 pos_mode=pos_mode)
                label = mt if len(mt) <= 24 else mt[:24] + "…"
                self.log(f"  ✅ thumb_{i}.png — \"{label}\"")

            # 제목 2종
            self.log("② 제목 2종 생성 중...")
            titles_out = []
            for t in titles:
                if isinstance(t, tuple):
                    full, short = t[0].format(DUR=dur_en), t[1].format(DUR=dur_en)
                    titles_out.append(full if len(full) <= 100 else short)
                else:
                    titles_out.append(t.format(DUR=dur_en))
            if story_title:
                self.log(f"  🌙 부제목에 이야기 제목 추가: 「{story_title}」")
            with open(os.path.join(pkg, "제목.txt"), "w", encoding="utf-8") as f:
                f.write("[A/B 테스트: 제목 2개 + 썸네일 3개 조합이 안전합니다]\n\n")
                for i, t in enumerate(titles_out, 1):
                    mark = "✅" if len(t) <= 100 else "⚠️ 100자 초과 — 줄여서 사용하세요"
                    f.write(f"제목 {i} ({len(t)}자 {mark}):\n{t}\n\n")

            # 설명
            self.log("③ 설명 생성 중...")
            desc = self._build_description(scene_en, scene_kr, dur_en, dur_kr, seconds,
                                           desc_en=desc_en, desc_kr=desc_kr, story=story)
            if story and story.get("summary"):
                self.log(f"  📖 설명란에 이야기 요약 추가: {fit_summary(story['summary'])}")
            with open(os.path.join(pkg, "설명.txt"), "w", encoding="utf-8") as f:
                f.write(desc)

            # 태그 (500자 이내 자동 검증)
            self.log("④ 태그 생성 중...")
            tags, total = self._build_tags(extra_tags_all)
            with open(os.path.join(pkg, "태그.txt"), "w", encoding="utf-8") as f:
                f.write(f"[총 {total}자 / 500자 제한 통과 — 쉼표 포함 전체를 복사해서 붙여넣으세요]\n\n")
                f.write(tags + "\n")

            shorts_note = ""
            if make_shorts:
                # v9.7: 숏폼은 화면이 좁아 롱폼용 긴 썸네일 문구를 그대로 쓰면 잘리기
                # 쉬우므로, 짧은 주제(en/kr)만으로 간결하게 다시 조합해서 쓴다.
                shorts_main = f"{kr} / {en}"
                s_start, s_where = shorts_start_for(video, seconds, cap_sec)
                self.log(f"⑤ 55초 숏폼(Shorts) 생성 중... (9:16 {shorts_crop} 크롭 + 간결한 한/영 문구, {s_where})")
                shorts_mp4 = os.path.join(pkg, "shorts_55s.mp4")
                self._make_shorts(video, shorts_main, narr_thumb_subtitle(story) or "", dur_en, dur_kr,
                                  shorts_mp4, tmp, length=SHORTS_SEC, crop_mode=shorts_crop,
                                  start=s_start,
                                  cover_path=os.path.join(pkg, "shorts_thumb.png"))
                self._write_shorts_txt(pkg, shorts_main, dur_en, channel_url)
                self.log("  ✅ shorts_55s.mp4 + shorts_thumb.png + 숏폼_제목설명태그.txt (클릭 유도 가이드 포함)")
                shorts_note = " · shorts_55s.mp4 · shorts_thumb.png · 숏폼_제목설명태그.txt"

            self.log(f"\n🎉 유튜브 패키지 완성!\n📁 {pkg}\n"
                     f"   thumb_1~3.png · 제목.txt · 설명.txt · 태그.txt ({total}자)"
                     + shorts_note)
            return pkg
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class AudioCleaner:
    """v9: 녹음 파일에서 균일한 빗소리 구간만 추출 (통계적 스펙트럼 이상 감지)
    - 파일 전체의 스펙트럼 중앙값 = '빗소리 기준 지문'
    - 기준에서 벗어나는 순간(새/차/천둥/목소리/충격음)을 감지해 제거
    - 남은 구간을 50ms 크로스페이드로 이어붙여 매끄러운 순수 빗소리 생성"""

    SENS = {"민감 (많이 제거)": 3.5, "표준": 4.5, "둔감 (적게 제거)": 6.0}
    DECLICK = {"약하게": 2.4, "표준": 1.7, "강하게": 1.3, "매우 강하게": 1.15}

    def __init__(self, log_fn, stop_flag=None):
        self.log = log_fn
        self.stop_flag = stop_flag

    def _check_stop(self):
        if self.stop_flag is not None and self.stop_flag.is_set():
            raise InterruptedError("중단됨")

    def _probe(self, path, entries, stream="a:0"):
        r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", stream,
                            "-show_entries", entries, "-of", "default=nw=1:nk=1", path],
                           capture_output=True, creationflags=CREATE_NO_WINDOW)
        return r.stdout.decode().strip()

    def _suppress_transients(self, pcm16, sr, ch, thresh, passes=1):
        """뚝뚝/충격음 억제: STFT에서 각 주파수의 시간축 중앙값(=지속 빗소리 기준)을 구하고,
        순간적으로 그보다 훨씬 튀는 성분(빗방울 충격)만 기준 수준으로 눌러줌.
        지속되는 '쏴아아' 빗소리는 중앙값 그 자체라서 손상 없음. passes회 반복 적용."""
        cur = pcm16
        for _ in range(max(1, passes)):
            cur = self._suppress_once(cur, sr, ch, thresh)
        return cur

    def _suppress_once(self, pcm16, sr, ch, thresh):
        win, hop = 1024, 512
        hann = np.hanning(win).astype(np.float32)
        x = pcm16.astype(np.float32)
        n = len(x)
        med_ctx = 41                    # 시간축 중앙값 창 (~0.48초, 촘촘한 뚝뚝에도 안정)
        chunk_fr = 5000                 # 청크당 프레임 (~58초)
        out = np.zeros_like(x)
        wsum = np.zeros(n, dtype=np.float32)
        total_fr = max(1, (n - win) // hop)

        for c0 in range(0, total_fr, chunk_fr):
            self._check_stop()
            c1 = min(total_fr, c0 + chunk_fr)
            # 문맥 여유 포함 프레임 범위
            f0 = max(0, c0 - med_ctx)
            f1 = min(total_fr, c1 + med_ctx)
            idx = np.arange(f0, f1)
            starts = idx * hop
            frames = np.stack([x[s:s + win] for s in starts])          # (F, win, ch)
            if ch == 1 and frames.ndim == 2:
                frames = frames[:, :, None]
            spec = np.fft.rfft(frames * hann[None, :, None], axis=1)   # (F, 513, ch)
            mag_mono = np.abs(spec).mean(axis=2).astype(np.float32)    # (F, 513)

            # 주파수별 시간축 이동 중앙값 (bin 그룹 단위로 메모리 절약)
            F, B = mag_mono.shape
            med = np.empty_like(mag_mono)
            half = med_ctx // 2
            padded = np.pad(mag_mono, ((half, half), (0, 0)), mode="edge")
            sw = np.lib.stride_tricks.sliding_window_view(padded, med_ctx, axis=0)
            for g in range(0, B, 64):
                med[:, g:g + 64] = np.median(sw[:, g:g + 64, :], axis=2)

            gain = np.minimum(1.0, (med * thresh) / (mag_mono + 1e-9)).astype(np.float32)
            spec *= gain[:, :, None]
            rec = np.fft.irfft(spec, win, axis=1).real.astype(np.float32) * hann[None, :, None]

            # 청크 코어 구간만 누적 (문맥 여유 프레임 제외)
            for k, fi in enumerate(idx):
                if fi < c0 or fi >= c1:
                    continue
                s = fi * hop
                e = min(n, s + win)
                out[s:e] += rec[k, :e - s]
                wsum[s:e] += (hann[:e - s] ** 2)

        out /= np.maximum(wsum[:, None] if out.ndim == 2 else wsum, 1e-6)
        return np.clip(out, -32768, 32767).astype(np.int16)

    def clean(self, audio_path, out_path, sensitivity="표준", rumble=False, declick=None,
              normalize=None):
        z_thr = self.SENS.get(sensitivity, 4.5)

        sr = int(self._probe(audio_path, "stream=sample_rate") or 0)
        ch = int(self._probe(audio_path, "stream=channels") or 0)
        dur = float(self._probe(audio_path, "format=duration", "a:0") or 0)
        if not sr or not ch or dur <= 3:
            raise RuntimeError("오디오 정보를 읽을 수 없습니다 (3초 이상 필요)")
        if dur > 7200:
            raise RuntimeError("2시간 이하 파일만 지원합니다")
        self.log(f"  원본: {sr}Hz {ch}ch {dur/60:.1f}분")

        # ── ① 원본 해상도 디코드 ──
        r = subprocess.run([FFMPEG, "-v", "error", "-i", audio_path,
                            "-f", "s16le", "-c:a", "pcm_s16le", "-"],
                           capture_output=True, creationflags=CREATE_NO_WINDOW)
        pcm = np.frombuffer(r.stdout, dtype=np.int16).reshape(-1, ch)
        if len(pcm) < sr * 3:
            raise RuntimeError("디코드 실패")

        # ── ② 뚝뚝 억제를 먼저 적용 (구간 분석이 뚝뚝을 잡음으로 오인하지 않도록) ──
        if declick:
            passes = {"약하게": 1, "표준": 1, "강하게": 2, "매우 강하게": 3}.get(declick, 1)
            self.log(f"  ① 우산 빗방울 '뚝뚝' 충격음 억제 중... (강도: {declick}, {passes}회)")
            pcm = self._suppress_transients(pcm, sr, ch,
                                            self.DECLICK.get(declick, 1.7), passes=passes)

        # ── ③ (억제 후 소리로) 분석용 8kHz 모노 생성 ──
        self._check_stop()
        self.log("  ② 빗소리 기준 지문 계산 중...")
        r = subprocess.run([FFMPEG, "-v", "error",
                            "-f", "s16le", "-ar", str(sr), "-ac", str(ch), "-i", "-",
                            "-ac", "1", "-ar", "8000", "-f", "f32le", "-"],
                           input=pcm.tobytes(),
                           capture_output=True, creationflags=CREATE_NO_WINDOW)
        mono = np.frombuffer(r.stdout, dtype=np.float32)

        win, hop = 512, 256
        n_fr = (len(mono) - win) // hop
        hann = np.hanning(win).astype(np.float32)
        n_bins = win // 2 + 1
        edges = np.unique(np.geomspace(2, n_bins - 1, 17).astype(int))
        n_band = len(edges) - 1
        band_log = np.empty((n_fr, n_band), dtype=np.float32)
        rms = np.empty(n_fr, dtype=np.float32)
        tonal = np.empty(n_fr, dtype=np.float32)
        hi_lo = int(2000 / 8000 * win)

        B = 4096
        for s0 in range(0, n_fr, B):
            self._check_stop()
            idx = np.arange(s0, min(s0 + B, n_fr))
            frames = np.stack([mono[i * hop:i * hop + win] for i in idx]) * hann
            spec = np.abs(np.fft.rfft(frames, axis=1)) ** 2 + 1e-12
            for b in range(n_band):
                band_log[idx, b] = np.log10(spec[:, edges[b]:edges[b + 1]].mean(axis=1))
            rms[idx] = np.sqrt(frames.astype(np.float64).__pow__(2).mean(axis=1) + 1e-12)
            hi = spec[:, hi_lo:]
            tonal[idx] = hi.max(axis=1) / (np.median(hi, axis=1) + 1e-12)

        med = np.median(band_log, axis=0)
        mad = np.median(np.abs(band_log - med), axis=0) + 1e-6
        spec_z = (np.abs(band_log - med) / mad).mean(axis=1)
        r_med = np.median(rms); r_mad = np.median(np.abs(rms - r_med)) + 1e-9
        rms_z = np.abs(rms - r_med) / r_mad
        bad = (spec_z > z_thr) | (rms_z > z_thr * 1.4) | (tonal > 60)

        pad = int(0.3 * 8000 / hop)
        bad2 = bad.copy()
        for off in range(1, pad + 1):
            bad2[off:] |= bad[:-off]
            bad2[:-off] |= bad[off:]
        good = ~bad2
        segs, i = [], 0
        min_keep = int(1.5 * 8000 / hop)
        while i < n_fr:
            if good[i]:
                j = i
                while j < n_fr and good[j]:
                    j += 1
                if j - i >= min_keep:
                    segs.append((i, j))
                i = j
            else:
                i += 1
        if not segs:
            raise RuntimeError("균일한 빗소리 구간을 찾지 못했습니다 (감도를 '둔감'으로 낮춰보세요)")

        kept_fr = sum(j - i for i, j in segs)
        removed_s = (n_fr - kept_fr) * hop / 8000
        n_events = 0
        prev = False
        for b in bad2:
            if b and not prev:
                n_events += 1
            prev = bool(b)
        self.log(f"  ③ 이상 구간 {n_events}곳 감지 → {removed_s:.1f}초 제거 "
                 f"(유지 {kept_fr / n_fr * 100:.0f}%)")
        if kept_fr / n_fr < 0.2:
            self.log("  ⚠️ 유지 비율 20% 미만 — 감도를 '둔감'으로 낮추는 것을 권장합니다")

        # ── ④ 원본 해상도로 잘라 크로스페이드 결합 ──
        self._check_stop()
        self.log("  ④ 순수 빗소리 결합 중... (50ms 크로스페이드)")
        pcmf = pcm.astype(np.float32)
        scale = sr / 8000.0
        xf = int(sr * 0.05)
        pieces = []
        for i, j in segs:
            a = int(i * hop * scale)
            b = min(len(pcmf), int(j * hop * scale))
            if b - a > xf * 2:
                pieces.append(pcmf[a:b].copy())
        out = pieces[0]
        fade_in = np.linspace(0, 1, xf, dtype=np.float32)[:, None]
        for p in pieces[1:]:
            self._check_stop()
            tail = out[-xf:] * (1 - fade_in)
            head = p[:xf] * fade_in
            out = np.concatenate([out[:-xf], tail + head, p[xf:]])
        out16 = np.clip(out, -32768, 32767).astype(np.int16)

        # ── ⑤ 음량 정규화 (선택: 피크를 목표 dB로 끌어올림, 클리핑 방지) ──
        norm_note = ""
        if normalize:
            target_db = {"적당히 (-3dB)": -3.0, "크게 (-1.5dB)": -1.5,
                         "최대 (-0.5dB)": -0.5}.get(normalize, -3.0)
            peak = float(np.abs(out16).max()) / 32768.0
            if peak > 1e-4:
                target_lin = 10 ** (target_db / 20.0)
                gain = target_lin / peak
                gain = min(gain, 60.0)          # 과증폭 상한 (무음에 가까운 경우 방지)
                cur_db = 20 * np.log10(peak)
                out_f = out16.astype(np.float32) * gain
                out16 = np.clip(out_f, -32768, 32767).astype(np.int16)
                self.log(f"  ⑤ 음량 정규화: 피크 {cur_db:+.1f}dB → {target_db:+.1f}dB "
                         f"({gain:.1f}배 증폭)")
                norm_note = f", 음량 {target_db:+.0f}dB"

        # ── ⑥ 저장 (+선택: 80Hz 하이패스 럼블 제거) ──
        cmd = [FFMPEG, "-v", "error", "-f", "s16le", "-ar", str(sr), "-ac", str(ch), "-i", "-"]
        if rumble:
            cmd += ["-af", "highpass=f=80"]
        cmd += ["-c:a", "pcm_s16le", "-y", out_path]
        r = subprocess.run(cmd, input=out16.tobytes(),
                           capture_output=True, creationflags=CREATE_NO_WINDOW)
        if r.returncode != 0:
            raise RuntimeError("저장 실패:\n" + r.stderr.decode("utf-8", "ignore")[-300:])
        final_min = len(out16) / sr / 60
        self.log(f"\n🎉 정제 완료! {dur/60:.1f}분 → {final_min:.1f}분 "
                 f"(이상 구간 {n_events}곳 제거{', 뚝뚝 억제' if declick else ''}"
                 f"{', 80Hz 럼블 컷' if rumble else ''}{norm_note})\n📁 {out_path}")
        return out_path


# =====================================================================
# v10: MP4 '인덱스 이어붙이기' — 인트로 자막을 10시간(약 50GB) 영상에도 몇 초 만에 넣기
#
# 왜 필요한가: MP4는 파일 '맨 앞'에 무언가를 끼워 넣을 수 없어서, 예전 방식은 50GB
# 영상 전체를 새 파일로 통째로 복사(하드디스크에서 약 1시간)해야 했다. 실제로 새로
# 인코딩하는 건 자막이 들어가는 맨 앞 30여 초뿐이다.
# 어떻게: 새로 인코딩한 앞부분(작은 파일)의 데이터를 원본 파일 '끝'에 덧붙이고,
# 파일의 색인(moov)만 새로 써서 재생 순서상 앞부분이 인트로가 되게 한다.
# 원본 데이터는 한 바이트도 옮기거나 다시 쓰지 않는다 → 시간·디스크 추가 사용 ≈ 0.
# 안전장치: 구조가 조금이라도 예상과 다르면 Mp4Unsupported → 기존 방식으로 대체,
# 작업 중 실패하거나 검증에 실패하면 mp4_rollback()으로 원본을 바이트 그대로 복구한다.
# =====================================================================

class Mp4Unsupported(Exception):
    """빠른 방식으로 처리할 수 없는 구조 — 호출한 쪽이 기존(느린) 방식으로 대체한다."""


_MP4_CONT = {b"moov", b"trak", b"mdia", b"minf", b"stbl", b"edts"}


class _Mp4Box:
    __slots__ = ("typ", "payload", "kids")

    def __init__(self, typ, payload=b"", kids=None):
        self.typ, self.payload, self.kids = typ, payload, kids

    def find(self, typ):
        for k in (self.kids or []):
            if k.typ == typ:
                return k
        return None

    def path(self, *types):
        b = self
        for t in types:
            b = b.find(t) if b is not None else None
        return b

    def pack(self):
        body = self.payload if self.kids is None else b"".join(k.pack() for k in self.kids)
        n = 8 + len(body)
        if n > 0xFFFFFFFF:
            return struct.pack(">I4sQ", 1, self.typ, n + 8) + body
        return struct.pack(">I4s", n, self.typ) + body


def _mp4_parse_boxes(buf, start, end):
    out, pos = [], start
    while pos + 8 <= end:
        size, typ = struct.unpack_from(">I4s", buf, pos)
        hdr = 8
        if size == 1:
            size = struct.unpack_from(">Q", buf, pos + 8)[0]
            hdr = 16
        elif size == 0:
            size = end - pos
        if size < hdr or pos + size > end:
            raise Mp4Unsupported("박스 크기가 비정상")
        if typ in _MP4_CONT:
            out.append(_Mp4Box(typ, kids=_mp4_parse_boxes(buf, pos + hdr, pos + size)))
        else:
            out.append(_Mp4Box(typ, bytes(buf[pos + hdr:pos + size])))
        pos += size
    return out


def _mp4_scan_top(f, fsize):
    pos, out = 0, []
    while pos + 8 <= fsize:
        f.seek(pos)
        h = f.read(16)
        size, typ = struct.unpack(">I4s", h[:8])
        hdr = 8
        if size == 1:
            size = struct.unpack(">Q", h[8:16])[0]
            hdr = 16
        elif size == 0:
            size = fsize - pos
        if size < hdr or pos + size > fsize:
            raise Mp4Unsupported("최상위 박스 구조 이상")
        out.append((typ, pos, size, hdr))
        pos += size
    if pos != fsize:
        raise Mp4Unsupported("파일 끝에 알 수 없는 데이터")
    return out


def _mp4_load_moov(path):
    fsize = os.path.getsize(path)
    with open(path, "rb") as f:
        top = _mp4_scan_top(f, fsize)
        moovs = [t for t in top if t[0] == b"moov"]
        if len(moovs) != 1:
            raise Mp4Unsupported("moov가 정확히 1개가 아님")
        _, pos, size, hdr = moovs[0]
        f.seek(pos + hdr)
        body = f.read(size - hdr)
    return top, moovs[0], _Mp4Box(b"moov", kids=_mp4_parse_boxes(body, 0, len(body)))


def _mp4_arr(payload, dtype, count, offset):
    return np.frombuffer(payload, dtype=dtype, count=count, offset=offset)


class _Mp4Track:
    pass


def _mp4_read_track(trak):
    t = _Mp4Track()
    t.box = trak
    mdia = trak.find(b"mdia")
    mdhd, hdlr = mdia.find(b"mdhd"), mdia.find(b"hdlr")
    stbl = mdia.path(b"minf", b"stbl")
    if mdhd is None or hdlr is None or stbl is None:
        raise Mp4Unsupported("trak 구성 이상")
    t.kind = hdlr.payload[8:12]
    if mdhd.payload[0] == 0:
        t.ts = struct.unpack_from(">I", mdhd.payload, 12)[0]
        t.mdhd_dur = struct.unpack_from(">I", mdhd.payload, 16)[0]
    else:
        t.ts = struct.unpack_from(">I", mdhd.payload, 20)[0]
        t.mdhd_dur = struct.unpack_from(">Q", mdhd.payload, 24)[0]

    allowed = {b"stsd", b"stts", b"stss", b"ctts", b"stsc", b"stsz", b"stco", b"co64",
               b"sgpd", b"sbgp"}
    bad = [k.typ for k in stbl.kids if k.typ not in allowed]
    if bad:
        raise Mp4Unsupported(f"지원하지 않는 stbl 박스: {bad}")

    stsd = stbl.find(b"stsd")
    if struct.unpack_from(">I", stsd.payload, 4)[0] != 1:
        raise Mp4Unsupported("stsd 엔트리가 1개가 아님")
    t.stsd = stsd.payload

    p = stbl.find(b"stts").payload
    n = struct.unpack_from(">I", p, 4)[0]
    a = _mp4_arr(p, ">u4", 2 * n, 8).reshape(n, 2).astype(np.int64)
    t.dur = np.repeat(a[:, 1], a[:, 0])

    p = stbl.find(b"stsz").payload
    ssz, cnt = struct.unpack_from(">II", p, 4)
    t.sizes = (np.full(cnt, ssz, dtype=np.int64) if ssz
               else _mp4_arr(p, ">u4", cnt, 12).astype(np.int64))
    t.n = cnt
    if len(t.dur) != cnt:
        raise Mp4Unsupported("stts/stsz 샘플 수 불일치")

    cb = stbl.find(b"ctts")
    t.ctts, t.ctts_ver = None, 0
    if cb is not None:
        t.ctts_ver = cb.payload[0]
        n = struct.unpack_from(">I", cb.payload, 4)[0]
        dt = ">i4" if t.ctts_ver == 1 else ">u4"
        c = np.frombuffer(cb.payload, dtype=np.dtype([("c", ">u4"), ("v", dt)]),
                          count=n, offset=8)
        t.ctts = np.repeat(c["v"].astype(np.int64), c["c"].astype(np.int64))
        if len(t.ctts) != cnt:
            raise Mp4Unsupported("ctts 샘플 수 불일치")

    t.has_stss = stbl.find(b"stss") is not None
    t.sync = np.ones(cnt, dtype=bool)
    if t.has_stss:
        p = stbl.find(b"stss").payload
        n = struct.unpack_from(">I", p, 4)[0]
        t.sync[:] = False
        t.sync[_mp4_arr(p, ">u4", n, 8).astype(np.int64) - 1] = True

    cob = stbl.find(b"stco") or stbl.find(b"co64")
    if cob is None:
        raise Mp4Unsupported("청크 오프셋 박스 없음")
    n = struct.unpack_from(">I", cob.payload, 4)[0]
    offs = _mp4_arr(cob.payload, ">u8" if cob.typ == b"co64" else ">u4", n, 8).astype(np.int64)
    p = stbl.find(b"stsc").payload
    m = struct.unpack_from(">I", p, 4)[0]
    e = _mp4_arr(p, ">u4", 3 * m, 8).reshape(m, 3).astype(np.int64)
    if np.any(e[:, 2] != 1):
        raise Mp4Unsupported("sample_description_index != 1")
    first = e[:, 0] - 1
    run = np.diff(np.append(first, n))
    if np.any(run < 0) or first[0] != 0:
        raise Mp4Unsupported("stsc 이상")
    chunk_spc = np.repeat(e[:, 1], run)
    if int(chunk_spc.sum()) != cnt:
        raise Mp4Unsupported("청크/샘플 수 불일치")
    cs = np.cumsum(t.sizes) - t.sizes
    first_of_chunk = np.cumsum(chunk_spc) - chunk_spc
    chunk_of_sample = np.repeat(np.arange(n), chunk_spc)
    t.offs = offs[chunk_of_sample] + (cs - cs[first_of_chunk][chunk_of_sample])

    t.elst = None
    ed = trak.find(b"edts")
    if ed is not None:
        el = ed.find(b"elst")
        if el is None or el.payload[0] != 0 or struct.unpack_from(">I", el.payload, 4)[0] != 1:
            raise Mp4Unsupported("elst 형태 미지원")
        t.elst = struct.unpack_from(">IiI", el.payload, 8)
    t.media_time = t.elst[1] if t.elst else 0
    t.tkhd_ver = trak.find(b"tkhd").payload[0]
    return t


def _mp4_rle(arr):
    chg = np.flatnonzero(np.diff(arr, prepend=arr[0] - 1) != 0)
    return arr[chg], np.diff(np.append(chg, len(arr)))


def _mp4_pairs(counts, vals, vdtype):
    s = np.empty(len(counts), dtype=np.dtype([("c", ">u4"), ("v", vdtype)]))
    s["c"], s["v"] = counts, vals
    return s.tobytes()


def _mp4_full(payload):
    return b"\x00\x00\x00\x00" + payload


def _mp4_build_tables(t, dur, ctts, sizes, offs, sync, boundary):
    """병합된 샘플 배열로 stbl 표 박스 payload들을 만든다 (dict: 박스타입 -> payload)"""
    n = len(dur)
    out = {}
    v, c = _mp4_rle(dur)
    out[b"stts"] = _mp4_full(struct.pack(">I", len(v)) + _mp4_pairs(c, v, ">u4"))
    if ctts is not None:
        v, c = _mp4_rle(ctts)
        out[b"ctts"] = (bytes([t.ctts_ver]) + b"\x00\x00\x00" + struct.pack(">I", len(v)) +
                        _mp4_pairs(c, v, ">i4" if t.ctts_ver == 1 else ">u4"))
    if t.has_stss:
        idx = (np.flatnonzero(sync) + 1).astype(">u4")
        out[b"stss"] = _mp4_full(struct.pack(">I", len(idx)) + idx.tobytes())
    out[b"stsz"] = _mp4_full(struct.pack(">II", 0, n) + sizes.astype(">u4").tobytes())

    newchunk = np.ones(n, dtype=bool)
    newchunk[1:] = offs[1:] != offs[:-1] + sizes[:-1]
    if 0 < boundary < n:
        newchunk[boundary] = True
    cfirst = np.flatnonzero(newchunk)
    cspc = np.diff(np.append(cfirst, n))
    coffs = offs[cfirst]
    chg = np.flatnonzero(np.diff(cspc, prepend=-1) != 0)
    ent = np.stack([chg + 1, cspc[chg], np.ones(len(chg), dtype=np.int64)], 1).astype(">u4")
    out[b"stsc"] = _mp4_full(struct.pack(">I", len(chg)) + ent.tobytes())
    if int(coffs.max()) > 0xFFFFFFFF:
        out[b"co64"] = _mp4_full(struct.pack(">I", len(coffs)) + coffs.astype(">u8").tobytes())
    else:
        out[b"stco"] = _mp4_full(struct.pack(">I", len(coffs)) + coffs.astype(">u4").tobytes())
    return out


def _mp4_is_idr(sample_bytes):
    """H.264 길이접두(4바이트) NAL 스트림에서 첫 슬라이스가 IDR(5)인지"""
    pos = 0
    while pos + 5 <= len(sample_bytes):
        ln = struct.unpack_from(">I", sample_bytes, pos)[0]
        nal = sample_bytes[pos + 4] & 0x1F
        if nal in (1, 5):
            return nal == 5
        pos += 4 + ln
    return False


def _mp4_norm_stsd(p):
    """stsd 비교용: 코덱 설정과 무관한 '측정된 비트레이트 힌트'(btrt, esds의 bitrate)를 지운다."""
    p = bytearray(p)
    i = bytes(p).find(b"btrt")
    if i >= 0 and i + 16 <= len(p):
        p[i + 4:i + 16] = b"\x00" * 12
    i = bytes(p).find(b"esds")
    if i >= 0:
        def rd_len(pos):
            n = 0
            for _ in range(4):
                b = p[pos]
                pos += 1
                n = (n << 7) | (b & 0x7F)
                if not b & 0x80:
                    break
            return n, pos
        try:
            j = i + 8
            if p[j] == 3:
                _, pos = rd_len(j + 1)
                pos += 3
                if p[pos] == 4:
                    _, pos2 = rd_len(pos + 1)
                    a = pos2 + 5
                    p[a:a + 8] = b"\x00" * 8
        except IndexError:
            pass
    return bytes(p)


def _mp4_read_at(f, off, n):
    f.seek(int(off))
    return f.read(int(n))


# ---------------------------------------------------------------------
def mp4_plan_cut(path, cap_sec):
    """원본을 분석해서 인트로가 대체할 구간(영상 s프레임, 오디오 j0/na)을 정한다."""
    top, moov_top, moov = _mp4_load_moov(path)
    traks = [_mp4_read_track(k) for k in moov.kids if k.typ == b"trak"]
    vs = [t for t in traks if t.kind == b"vide"]
    au = [t for t in traks if t.kind == b"soun"]
    if len(vs) != 1 or len(au) > 1 or len(traks) != len(vs) + len(au):
        raise Mp4Unsupported("트랙 구성이 영상1+오디오(0~1)가 아님")
    v = vs[0]
    dts = np.cumsum(v.dur) - v.dur
    ctts = v.ctts if v.ctts is not None else np.zeros(v.n, dtype=np.int64)
    pts_time = (dts + ctts - v.media_time) / v.ts
    cand = np.flatnonzero(v.sync & (pts_time >= cap_sec))
    s = None
    with open(path, "rb") as f:
        for c in cand[:20]:
            if c >= 1 and _mp4_is_idr(_mp4_read_at(f, v.offs[c], min(int(v.sizes[c]), 4096))):
                s = int(c)
                break
    if s is None:
        raise Mp4Unsupported("자막 뒤에서 IDR 키프레임을 찾지 못함")
    if v.n - s < 250:
        raise Mp4Unsupported("자막 뒤에 남는 영상이 너무 짧음")
    plan = dict(s=s, t_cut=float(pts_time[s]), has_audio=bool(au))
    if au:
        a = au[0]
        adts = np.cumsum(a.dur) - a.dur
        thr = plan["t_cut"] * a.ts + a.media_time
        j0 = int(np.searchsorted(adts, thr, side="left"))
        if j0 >= a.n - 10:
            raise Mp4Unsupported("오디오 컷 지점 이상")
        plan.update(j0=j0, frame=int(np.bincount(a.dur[:2000]).argmax()))
    return plan


def _mp4_set_dur(box, kind, d):
    p = bytearray(box.payload)
    v = p[0]
    if kind == "mdhd":
        (struct.pack_into(">I", p, 16, d) if v == 0 else struct.pack_into(">Q", p, 24, d))
    elif kind == "tkhd":
        (struct.pack_into(">I", p, 20, d) if v == 0 else struct.pack_into(">Q", p, 32, d))
    elif kind == "mvhd":
        (struct.pack_into(">I", p, 16, d) if v == 0 else struct.pack_into(">Q", p, 24, d))
    box.payload = bytes(p)


def _mp4_get(box, kind):
    p, v = box.payload, box.payload[0]
    if kind == "tkhd":
        return struct.unpack_from(">I", p, 20)[0] if v == 0 else struct.unpack_from(">Q", p, 32)[0]
    if kind == "mvhd":
        return (struct.unpack_from(">II", p, 12) if v == 0 else
                (struct.unpack_from(">I", p, 20)[0], struct.unpack_from(">Q", p, 24)[0]))


def _mp4_build_new_moov(path, intro_path, plan):
    """새 moov 바이트와 (인트로 mdat payload 위치/길이, 원본 mdat 정보)를 만든다.
    파일은 아직 안 건드림. 원본 파일의 mdat를 그대로 '연장'해서 인트로 데이터를
    이어붙이는 방식으로 계산한다 — mdat를 2개로 쪼개면(예전 방식) 일부 재생기가
    아주 큰 파일에서 재생을 못 하는 문제가 있었다(실측: 37GB 파일에서 재현됨)."""
    top, moov_top, moov = _mp4_load_moov(path)
    mdats = [t for t in top if t[0] == b"mdat"]
    if len(mdats) != 1:
        raise Mp4Unsupported("원본에 mdat가 1개가 아님(이미 다른 도구로 편집된 파일일 수 있음)")
    _, mdat_pos, mdat_size, mdat_hdr = mdats[0]
    mdat_old_payload = mdat_size - mdat_hdr
    new_total_payload = None  # 아래에서 ip_len을 구한 뒤 채움
    base_offset = mdat_pos + mdat_size   # 인트로 데이터를 원본 mdat 바로 뒤에 '이어붙임'

    itop, _, imoov = _mp4_load_moov(intro_path)
    mds = [t for t in itop if t[0] == b"mdat"]
    if len(mds) != 1:
        raise Mp4Unsupported("인트로 mdat가 1개가 아님")
    ip_start, ip_len = mds[0][1] + mds[0][3], mds[0][2] - mds[0][3]
    shift = base_offset - ip_start

    new_mdat_payload = mdat_old_payload + ip_len
    if mdat_hdr == 8 and 16 + new_mdat_payload > 0xFFFFFFFF:
        # 원본이 32비트 헤더였는데 자막을 더하면 4GB를 넘어가는 드문 경우 —
        # 헤더를 16바이트로 늘리려면 그 뒤 데이터를 전부 8바이트씩 밀어야 해서
        # 비용이 크다. 이런 경우는 기존(느린) 방식으로 대체한다.
        raise Mp4Unsupported("원본 mdat 헤더가 32비트인데 4GB를 넘게 됨")

    otr = [_mp4_read_track(k) for k in moov.kids if k.typ == b"trak"]
    itr = [_mp4_read_track(k) for k in imoov.kids if k.typ == b"trak"]
    mv_ts = _mp4_get(moov.find(b"mvhd"), "mvhd")[0]
    new_tkhd_durs = []
    for old in otr:
        it = next((x for x in itr if x.kind == old.kind), None)
        if it is None:
            raise Mp4Unsupported("인트로에 같은 종류 트랙이 없음")
        if _mp4_norm_stsd(it.stsd) != _mp4_norm_stsd(old.stsd) or it.ts != old.ts or it.media_time != old.media_time:
            raise Mp4Unsupported(f"인트로와 원본의 코덱 설정이 다름({old.kind})")
        if old.kind == b"vide":
            s = plan["s"]
            if it.n < s or not np.array_equal(it.dur[:s], old.dur[:s]):
                raise Mp4Unsupported("인트로 영상 프레임 수/타이밍이 원본과 다름")
            dur = old.dur
            ctts = (np.concatenate([it.ctts[:s], old.ctts[s:]])
                    if old.ctts is not None else None)
            if ctts is not None:
                dts = np.cumsum(dur) - dur
                if not np.array_equal(np.sort(dts + ctts), np.sort(dts + old.ctts)):
                    raise Mp4Unsupported("인트로 프레임 표시 순서가 원본과 달라 이어붙일 수 없음")
            sizes = np.concatenate([it.sizes[:s], old.sizes[s:]])
            offs = np.concatenate([it.offs[:s] + shift, old.offs[s:]])
            sync = np.concatenate([it.sync[:s], old.sync[s:]])
            boundary = s
        else:
            j0, fr = plan["j0"], plan["frame"]
            old_start = int(np.cumsum(old.dur)[j0] - old.dur[j0])
            iend = np.cumsum(it.dur)
            if iend[-1] < old_start + 2 * fr:
                raise Mp4Unsupported("인트로 오디오가 충분히 길지 않음")
            na = int(np.argmin(np.abs(iend - old_start))) + 1
            if abs(int(iend[na - 1]) - old_start) > int(1.5 * fr):
                raise Mp4Unsupported("오디오 이음 위치를 프레임 경계에 맞출 수 없음")
            plan["audio_sync_err_ms"] = (int(iend[na - 1]) - old_start) * 1000.0 / old.ts
            dur = np.concatenate([it.dur[:na], old.dur[j0:]])
            ctts = None
            sizes = np.concatenate([it.sizes[:na], old.sizes[j0:]])
            offs = np.concatenate([it.offs[:na] + shift, old.offs[j0:]])
            sync = np.ones(len(dur), dtype=bool)
            boundary = na
        tables = _mp4_build_tables(old, dur, ctts, sizes, offs, sync, boundary)
        stbl = old.box.path(b"mdia", b"minf", b"stbl")
        kids = []
        for k in stbl.kids:
            if k.typ in (b"stsd", b"sgpd"):
                kids.append(k)
            elif k.typ == b"sbgp":
                p = k.payload
                if p[0] != 0 or struct.unpack_from(">I", p, 8)[0] != 1:
                    raise Mp4Unsupported("sbgp 형태 미지원")
                kids.append(_Mp4Box(b"sbgp", p[:12] + struct.pack(">II", len(dur), struct.unpack_from(">I", p, 16)[0])))
            elif k.typ in (b"stco", b"co64"):
                key = b"co64" if b"co64" in tables else b"stco"
                kids.append(_Mp4Box(key, tables[key]))
            else:
                kids.append(_Mp4Box(k.typ, tables[k.typ]))
        stbl.kids = kids
        delta = int(dur.sum()) - int(old.dur.sum())
        _mp4_set_dur(old.box.path(b"mdia", b"mdhd"), "mdhd", old.mdhd_dur + delta)
        tk = old.box.find(b"tkhd")
        d_seg = int(round(delta * mv_ts / old.ts))
        new_tk = _mp4_get(tk, "tkhd") + d_seg
        _mp4_set_dur(tk, "tkhd", new_tk)
        new_tkhd_durs.append(new_tk)
        if old.elst is not None:
            seg, mt, rate = old.elst
            el = old.box.find(b"edts").find(b"elst")
            el.payload = (b"\x00\x00\x00\x00" + struct.pack(">I", 1) +
                          struct.pack(">IiI", seg + d_seg, mt, rate))
    _mp4_set_dur(moov.find(b"mvhd"), "mvhd", max(new_tkhd_durs))
    mdat_info = (mdat_pos, mdat_hdr, new_mdat_payload)
    return moov.pack(), ip_start, ip_len, moov_top, mdat_info


def mp4_splice(path, intro_path, plan, log=print):
    """원본 mdat를 '연장'해서 그 뒤에 인트로 데이터를 이어붙인다(mdat를 2개로 쪼개지
    않음 — 쪼개면 파일 구조상 문제는 없어도 일부 재생기, 특히 윈도우 기본 미디어
    플레이어가 몇십 GB짜리 파일에서 재생을 아예 못 하는 문제가 실측으로 확인됨).
    새 색인(moov)은 가능하면 옛 색인 자리(파일 맨 앞)에 그대로 다시 써서 재생
    프로그램 호환성을 유지한다 — 색인이 파일 끝에 있으면 첫 화면이 새까맣게
    멈춰 보이는 문제도 있었다(v10 1차 수정)."""
    E0 = os.path.getsize(path)
    new_moov, ip_start, ip_len, moov_top, mdat_info = _mp4_build_new_moov(path, intro_path, plan)
    _, old_moov_pos, old_moov_size, _ = moov_top
    mdat_pos, mdat_hdr, new_mdat_payload = mdat_info
    old_mdat_total = mdat_hdr + (new_mdat_payload - ip_len)
    if mdat_pos + old_mdat_total != E0:
        # 원본 mdat 뒤에 다른 박스가 더 있는(예상 밖의) 구조 — 안전하게 폴백
        raise Mp4Unsupported("원본 mdat 뒤에 다른 데이터가 더 있음")
    pad = old_moov_size - len(new_moov)
    fits_in_place = pad == 0 or pad >= 8

    with open(path, "rb") as f:
        f.seek(old_moov_pos)
        old_moov_bytes = f.read(old_moov_size)

    try:
        with open(path, "r+b") as f, open(intro_path, "rb") as fi:
            # 원본 mdat를 그대로 이어서 씀 — 새 헤더 없이 원시 데이터만 덧붙인다.
            f.seek(E0)
            fi.seek(ip_start)
            left = ip_len
            while left > 0:
                chunk = fi.read(min(left, 8 << 20))
                if not chunk:
                    raise RuntimeError("인트로 데이터 읽기 실패")
                f.write(chunk)
                left -= len(chunk)
            f.flush()
            os.fsync(f.fileno())

            # 원본 mdat의 크기 필드를 늘려 방금 이어붙인 데이터까지 포함시킨다.
            new_total = mdat_hdr + new_mdat_payload
            f.seek(mdat_pos)
            if mdat_hdr == 16:
                f.write(struct.pack(">I4sQ", 1, b"mdat", new_total))
            else:
                f.write(struct.pack(">I4s", new_total, b"mdat"))
            f.flush()
            os.fsync(f.fileno())

            if fits_in_place:
                f.seek(old_moov_pos)
                f.write(new_moov)
                if pad:
                    f.write(struct.pack(">I4s", pad, b"free"))
                    if pad > 8:
                        f.write(b"\x00" * (pad - 8))
                log("  🔗 색인을 원래 위치(파일 맨 앞)에 다시 써서 재생 호환성을 유지했습니다.")
            else:
                f.write(new_moov)
                f.seek(old_moov_pos + 4)
                f.write(b"free")
                log("  ℹ️ 새 색인이 이전보다 커서 파일 끝에 저장했습니다 "
                    "(초대용량 파일은 일부 플레이어에서 시작이 느릴 수 있어요).")
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        mp4_rollback(path, E0, old_moov_pos, old_moov_bytes)
        raise
    return E0, old_moov_pos, old_moov_bytes


def mp4_rollback(path, E0, old_moov_pos, old_moov_bytes):
    with open(path, "r+b") as f:
        f.seek(old_moov_pos)
        f.write(old_moov_bytes)
        f.flush()
        f.truncate(E0)
        f.flush()
        os.fsync(f.fileno())


class Pipeline:
    """영상 분석 → 루프 지점 탐색 → 모션 보간 → 장시간 합성 파이프라인"""

    def __init__(self, log_fn, stop_flag):
        self.log = log_fn
        self.stop_flag = stop_flag      # threading.Event
        self.current_proc = None
        self.proc_lock = threading.Lock()

    # ---------- 프로세스 실행 ----------
    def run(self, cmd, **kw):
        if self.stop_flag.is_set():
            raise InterruptedError("중단됨")
        with self.proc_lock:
            self.current_proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=CREATE_NO_WINDOW, **kw)
        out, err = self.current_proc.communicate()
        rc = self.current_proc.returncode
        with self.proc_lock:
            self.current_proc = None
        if self.stop_flag.is_set():
            raise InterruptedError("중단됨")
        return rc, out, err

    def kill_current(self):
        with self.proc_lock:
            p = self.current_proc
        if p and p.poll() is None:
            try:
                p.kill()
            except Exception:
                pass

    def probe(self, path, entries, stream="v:0"):
        cmd = [FFPROBE, "-v", "error", "-select_streams", stream,
               "-show_entries", entries, "-of", "default=nw=1:nk=1", path]
        rc, out, err = self.run(cmd)
        if rc != 0:
            return None
        return out.decode("utf-8", "ignore").strip()

    def _has_nvenc(self):
        """NVIDIA GPU h264_nvenc 인코더 사용 가능 여부 (있으면 자동으로 사용 — 훨씬 빠름)"""
        try:
            r = subprocess.run([FFMPEG, "-hide_banner", "-encoders"],
                               capture_output=True, creationflags=CREATE_NO_WINDOW, timeout=10)
            return b"h264_nvenc" in r.stdout
        except Exception:
            return False

    # ---------- 1단계: 영상 정보 ----------
    def get_video_info(self, path):
        fps_raw = self.probe(path, "stream=r_frame_rate")
        dur_raw = self.probe(path, "format=duration", stream="v:0")
        if not fps_raw:
            raise RuntimeError("영상 정보를 읽을 수 없습니다 (ffprobe 확인)")
        num, den = fps_raw.split("/")
        fps = float(num) / float(den)
        duration = float(dur_raw) if dur_raw else 0.0
        return fps, duration

    def get_video_size(self, path):
        wh = self.probe(path, "stream=width,height")
        if not wh:
            return None
        parts = [p for p in wh.split("\n") if p.strip()]
        if len(parts) < 2:
            return None
        return int(parts[0]), int(parts[1])

    # ---------- 2단계: 프레임 추출 (분석용 저해상도) ----------
    def extract_gray_frames(self, path, w=128, h=72, max_frames=2400):
        cmd = [FFMPEG, "-v", "error", "-i", path,
               "-vf", f"scale={w}:{h}", "-pix_fmt", "gray",
               "-frames:v", str(max_frames),
               "-f", "rawvideo", "-"]
        rc, out, err = self.run(cmd)
        if rc != 0 or not out:
            raise RuntimeError("프레임 추출 실패")
        n = len(out) // (w * h)
        arr = np.frombuffer(out[: n * w * h], dtype=np.uint8)
        frames = arr.reshape(n, h, w).astype(np.float32)
        return frames

    def extract_gray_frames_strided(self, path, want_frames, w=128, h=72, max_out=1200):
        """v9.4: 긴 구간(최대 5분)까지 후보로 분석하기 위한 서브샘플링 프레임 추출.
        want_frames(원본 기준 분석하고 싶은 총 프레임 수)이 max_out을 넘으면,
        n프레임마다 1장(step)만 뽑아 유사도 행렬(O(n^2)) 연산량을 일정하게 유지한다.
        반환: (frames, step) — step=1이면 기존과 동일(매 프레임), step>1이면
        frames[i]는 원본의 (i*step)번째 프레임이다."""
        want_frames = max(1, int(want_frames))
        step = 1 if want_frames <= max_out else math.ceil(want_frames / max_out)
        n_take = want_frames if step == 1 else max_out

        if step == 1:
            vf = f"scale={w}:{h}"
        else:
            vf = f"select='not(mod(n\\,{step}))',scale={w}:{h}"
        cmd = [FFMPEG, "-v", "error", "-i", path, "-vf", vf,
               "-vsync", "0", "-pix_fmt", "gray",
               "-frames:v", str(n_take), "-f", "rawvideo", "-"]
        rc, out, err = self.run(cmd)
        if rc != 0 or not out:
            raise RuntimeError("프레임 추출 실패")
        n = len(out) // (w * h)
        arr = np.frombuffer(out[: n * w * h], dtype=np.uint8)
        frames = arr.reshape(n, h, w).astype(np.float32)
        return frames, step

    # ---------- 3단계: 루프 지점 탐색 (v5: 7프레임 윈도우 + 움직임 가중) ----------
    def find_loop_points(self, frames, fps, step=1, tol=1.35):
        """v9.4: 2초~5분까지 여러 길이(버킷)를 모두 후보로 분석해 가장 완벽한 구간을 고르고,
        조건이 맞으면 서로 다른 두 구간을 찾아 이어붙일 수 있도록 함께 반환한다.
        frames는 실제 원본에서 매 step번째 프레임만 뽑은 것이므로(=1이면 매 프레임 그대로),
        결과 (s, e)는 항상 '원본 기준 실제 프레임 번호'로 환산해서 반환한다."""
        n = len(frames)
        W = 7                                  # 매칭 윈도우
        fps_eff = fps / step                   # 샘플 프레임 간 실효 fps
        min_len = max(int(fps_eff * 2), 8)     # 최소 루프 길이 2초
        if n < min_len + 2 * W + 4:
            raise RuntimeError("영상이 너무 짧습니다 (최소 2초 이상 필요)")

        F_raw = frames.reshape(n, -1)              # (n, D)

        # ★ v9.5: 짧은 시간창 이동평균으로 매칭용 프레임을 만든다.
        #   빗줄기·나뭇잎 사이 반짝임 같은 순간적 노이즈는 애초에 두 시점이 완전히
        #   같을 수가 없어(빗방울 위치는 항상 랜덤) 그대로 비교하면 실제로는 구도/조명/
        #   가지 배치가 잘 맞는 좋은 루프 지점도 "빗줄기가 다르다"는 이유로 점수가
        #   깎여 나쁜 지점처럼 보인다. 0.2초 남짓 이동평균을 취해 순간 노이즈는
        #   눌러주고 천천히 변하는 진짜 구조(나뭇가지 흔들림, 노출)만 남겨 매칭한다.
        smooth_win = max(1, int(round((fps / step) * 0.2)))
        if smooth_win > 1:
            pad_before = smooth_win // 2
            pad_after = smooth_win - 1 - pad_before
            Fp = np.pad(F_raw, ((pad_before, pad_after), (0, 0)), mode="edge")
            csum = np.cumsum(Fp, axis=0)
            csum = np.vstack([np.zeros((1, Fp.shape[1]), dtype=np.float32), csum])
            F = ((csum[smooth_win:] - csum[:-smooth_win]) / smooth_win).astype(np.float32)
            self.log(f"  🌧️ 순간 노이즈 완화용 {smooth_win}프레임({smooth_win/(fps/step):.2f}초) 이동평균 적용 후 매칭")
        else:
            F = F_raw

        # ★ v9.2: 불안정 구간 자동 감지 — 급격히 변하는 앞부분 건너뜀
        # 프레임간 변화량 계산 (0.5초 창 이동평균)
        diffs = np.array([np.abs(F[i+1]-F[i]).mean() for i in range(n-1)], dtype=np.float32)
        win_s = max(1, int(fps_eff * 0.5))
        smooth_d = np.convolve(diffs, np.ones(win_s)/win_s, mode='same')
        stable_thresh = np.median(smooth_d) * 1.8   # 중앙값의 1.8배 초과 = 불안정
        # 앞에서부터 연속 안정 구간 시작점 탐색 (최대 영상의 25% 까지만)
        skip_max = int(n * 0.25)
        s_start = 0
        unstable_run = 0
        for i in range(min(skip_max, len(smooth_d))):
            if smooth_d[i] > stable_thresh:
                unstable_run = i + 1
        if unstable_run > 0:
            s_start = min(unstable_run + int(fps_eff * 0.5), skip_max)
            self.log(f"  ⚡ 앞부분 불안정 구간 감지 → 프레임 {s_start}부터 탐색 "
                     f"({s_start/fps_eff:.1f}초 건너뜀)")
        else:
            self.log("  ✅ 전체 구간 안정적 — 처음부터 탐색")

        self.log("  프레임간 유사도 행렬 계산 중...")
        M = np.empty((n, n), dtype=np.float32)
        for i in range(n):
            if self.stop_flag.is_set():
                raise InterruptedError("중단됨")
            M[i] = np.abs(F - F[i]).mean(axis=1)

        Dv = F[1:] - F[:-1]
        self.log("  움직임 연속성 행렬 계산 중...")
        Mm = np.empty((n - 1, n - 1), dtype=np.float32)
        for i in range(n - 1):
            if self.stop_flag.is_set():
                raise InterruptedError("중단됨")
            Mm[i] = np.abs(Dv - Dv[i]).mean(axis=1)

        avg_motion = float(np.mean([M[i, i + 1] for i in range(n - 1)]))

        # ★ v9.4: 2초 ~ 5분(가능한 범위까지) 여러 길이를 모두 후보로 탐색.
        #   각 길이대별로 목표 길이 근방(±15%)에서만 최적점을 찾아 연산량을 억제한다.
        LENGTH_BUCKETS_SEC = [2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 300]
        s_hi = max(s_start + 1, int(n * 0.7))
        candidates = []   # (s, e, score)
        for L_sec in LENGTH_BUCKETS_SEC:
            target = int(L_sec * fps_eff)
            if target < min_len:
                target = min_len
            if s_start + target + W + 1 >= n:
                continue   # 이 길이는 소스에 안 들어감
            # ★ v9.6 버그 수정: 여기서 'tol' 이름을 재사용하면 아래 pick_longest_near_best에
            #   넘기는 함수 인자 'tol'(점수 허용오차, 예: 1.35)이 이 값(프레임 수, 예: 76)으로
            #   덮어써져서 품질 기준 선택이 사실상 무력화되고 있었다 — 항상 '그냥 가장 긴 후보'가
            #   뽑히던 진짜 원인. 이름을 분리해 서로 침범하지 않도록 한다.
            win_tol = max(W, int(target * 0.15))
            for s in range(s_start, s_hi):
                e_lo = max(s + min_len, s + target - win_tol)
                e_hi = min(n - W - 1, s + target + win_tol)
                if e_lo >= e_hi:
                    continue
                e_range = np.arange(e_lo, e_hi)
                content = np.zeros(len(e_range), dtype=np.float32)
                motion = np.zeros(len(e_range), dtype=np.float32)
                for w_ in range(W):
                    content += M[s + w_, e_range + w_]
                for w_ in range(W - 1):
                    motion += Mm[s + w_, e_range + w_]
                score = content / W + 2.5 * (motion / (W - 1))
                k = int(np.argmin(score))
                candidates.append((s, int(e_range[k]), float(score[k])))
            if self.stop_flag.is_set():
                raise InterruptedError("중단됨")

        if not candidates:
            raise RuntimeError("루프 지점을 찾지 못했습니다")

        def pick_longest_near_best(cands, tol=1.35):
            best = min(c[2] for c in cands)
            good = [c for c in cands if c[2] <= best * tol]
            return max(good, key=lambda c: c[1] - c[0]), best

        def overlaps(a, b, guard):
            return not (a[1] + guard <= b[0] or b[1] + guard <= a[0])

        # ★ v9.3/v9.4: 점수 1등만 뽑으면 우연히 매우 짧은 구간이 뽑히기 쉽고,
        #   그러면 미세한 이음새라도 훨씬 자주 반복되어 훨씬 잘 눈에 띈다.
        #   점수가 최고점 대비 크게 나쁘지 않은 후보들(허용오차 이내) 중에서는
        #   반복 주기가 가장 긴 구간을 선택해 이음새 노출 빈도를 줄인다.
        (s1, e1, sc1), best_score = pick_longest_near_best(candidates, tol=tol)
        self.log(f"  ✅ 구간 A: 프레임 {s1} → {e1} ({(e1 - s1) / fps_eff:.1f}초, 점수 {sc1:.2f}"
                 f" / 최고점 {best_score:.2f} / 일반 재생 변화량 {avg_motion * step:.2f})")

        segments = [(s1, e1)]

        # ★ v9.4: 겹치지 않는 두 번째 구간이 충분히 좋으면 함께 반환 → 이어붙여서
        #   더 길고 다채로운 루프 단위를 만든다 (품질이 못 미치면 조용히 생략).
        guard = max(W, min_len // 2)
        rest = [c for c in candidates if not overlaps((s1, e1), (c[0], c[1]), guard)]
        if rest:
            (s2, e2, sc2), best2 = pick_longest_near_best(rest)
            quality2 = sc2 / max(avg_motion, 1e-6)
            if quality2 <= 4.0 and (e2 - s2) >= min_len:
                self.log(f"  ✅ 구간 B: 프레임 {s2} → {e2} ({(e2 - s2) / fps_eff:.1f}초, 점수 {sc2:.2f}"
                         f" — A와 이어붙임")
                segments.append((s2, e2))
            else:
                self.log(f"  (두 번째 구간 후보 품질 부족 — 단일 구간만 사용)")

        # 샘플 프레임 인덱스 → 원본 실제 프레임 인덱스로 환산
        return [(s * step, e * step) for s, e in segments]

    # ---------- 4단계: 프레임 단위 트리밍 ----------
    def trim_unit(self, src, s, e, fps, out_path, scale=None):
        # ★ v9.7 성능 버그 수정: 여기서 4K 원본을 그대로 유닛으로 만들면, 최종
        # 합성 단계(assemble)가 이 4K 유닛을 '-stream_loop -1'로 수천 번 반복
        # 디코딩하게 된다 — 인코딩은 GPU(nvenc)를 쓰지만 디코딩은 CPU로 4K를
        # 그대로 풀어야 해서 10시간 렌더링이 (이전 1080p 소스 기준 20~30분 대비)
        # 4~5시간까지 늘어지는 진짜 원인이었다. 최종 해상도로 미리 축소해서
        # 유닛을 만들면, 반복되는 디코딩 자체가 1080p 기준이라 훨씬 가벼워진다.
        vf = f"trim=start_frame={s}:end_frame={e},setpts=PTS-STARTPTS"
        if scale:
            sw, sh = scale
            vf += f",scale={sw}:{sh}:flags=lanczos"
        vf += ",format=yuv420p"
        # 루프 단위 = 프레임 s ~ e-1 (재생 후 s로 점프)
        rc, _, err = self.run([
            FFMPEG, "-v", "error", "-i", src,
            "-vf", vf,
            "-an",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-y", out_path])
        if rc != 0:
            raise RuntimeError("루프 단위 생성 실패:\n" + err.decode("utf-8", "ignore")[-400:])

    def extract_frame_png(self, src, frame_idx, out_png):
        rc, _, err = self.run([
            FFMPEG, "-v", "error", "-i", src,
            "-vf", f"select='eq(n\\,{frame_idx})'", "-vsync", "0",
            "-frames:v", "1", "-y", out_png])
        if rc != 0 or not os.path.exists(out_png):
            raise RuntimeError(f"프레임 {frame_idx} 추출 실패")

    # ---------- 크로스페이드 이음새 (v9.1) ----------
    def make_crossfade(self, unit_path, fps, fade_sec, tmp):
        """루프 단위 끝과 시작을 xfade dissolve로 이어붙임 — 빗줄기 방향 불일치에 효과적

        ★ v9.3 버그 수정: 트랜지션이 끝난 뒤 원본 앞부분이 블렌딩 없이 그대로
        덧붙던 꼬리(~0.1초)를 제거함.

        ★ v9.5 근본 버그 수정: v9.3까지도 여전히, 같은 파일을 input0/input1로 두 번
        넣으면 xfade는 트랜지션이 끝나는 순간 input1을 '자기 시간 = duration(=fade_sec)'
        지점에서 샘플링한다 — 즉 진짜 '처음(t=0)'이 아니라 '처음에서 fade_sec만큼
        지난 지점'으로 수렴한다. 그 상태를 유닛의 끝으로 잘라 저장하면, 다음 루프가
        시작할 때(진짜 t=0)와 fade_sec만큼 어긋나 있어 반복마다 그만큼 뒤로 튀는
        이음새가 생긴다 (실측: 0.5초 크로스페이드는 약 0.4~0.5초, 1.5초로 늘리면
        오히려 더 크게 튀는 것으로 확인됨 — 크로스페이드를 늘릴수록 증상이 커지는
        역설이 바로 이 버그 때문).

        수정: input1을 '전체 유닛'이 아니라 '앞부분 fade_sec만'으로 제한한 head로,
        input0(재생 몸통)은 '앞부분 fade_sec를 건너뛴 나머지'인 body로 나눈다.
        이러면 body의 시작점과, 트랜지션이 끝나며 수렴하는 head의 끝점이 원본에서
        정확히 같은 시각(t=fade_sec)을 가리키게 되어 반복 경계가 완전히 맞아떨어진다.
        """
        udur = float(self.probe(unit_path, "format=duration", stream="v:0"))
        if udur <= fade_sec * 2:
            raise RuntimeError("루프 단위가 너무 짧습니다 (페이드 길이의 2배 이상 필요)")

        body = os.path.join(tmp, "xfade_body.mp4")
        rc, _, err = self.run([
            FFMPEG, "-v", "error", "-i", unit_path,
            "-vf", f"trim=start={fade_sec:.3f},setpts=PTS-STARTPTS,format=yuv420p",
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-y", body])
        if rc != 0:
            raise RuntimeError("크로스페이드 준비(body) 실패:\n" + err.decode("utf-8", "ignore")[-300:])

        head = os.path.join(tmp, "xfade_head.mp4")
        rc, _, err = self.run([
            FFMPEG, "-v", "error", "-i", unit_path,
            "-vf", f"trim=end={fade_sec:.3f},setpts=PTS-STARTPTS,format=yuv420p",
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-y", head])
        if rc != 0:
            raise RuntimeError("크로스페이드 준비(head) 실패:\n" + err.decode("utf-8", "ignore")[-300:])

        bdur = float(self.probe(body, "format=duration", stream="v:0"))
        offset = max(0.0, bdur - fade_sec - 0.05)   # xfade가 EOF 정확히 걸치지 않게 하는 안전 여유
        out_len = offset + fade_sec                 # 트랜지션이 끝나는 지점 — 여기서 정확히 잘라야 꼬리가 안 남음
        out = os.path.join(tmp, "unit_xfade.mp4")
        rc, _, err = self.run([
            FFMPEG, "-v", "error",
            "-i", body, "-i", head,
            "-filter_complex",
            f"[0:v][1:v]xfade=transition=dissolve:duration={fade_sec:.3f}:offset={offset:.3f},format=yuv420p",
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-t", f"{out_len:.4f}", "-y", out])
        if rc != 0:
            raise RuntimeError("크로스페이드 실패:\n" + err.decode("utf-8","ignore")[-300:])
        self.log(f"  ✅ 크로스페이드 {fade_sec:.1f}초 dissolve 적용 (반복 경계가 원본 기준 같은 시각으로 정확히 수렴)")
        return out

    # ---------- 4.5단계: v9.4 — 서로 다른 두 구간을 이어붙이기 (multi-segment) ----------
    def _xfade_join_cut(self, a_path, b_path, fade_sec, tmp, out_name):
        """a_path의 꼬리를 b_path의 머리와 디졸브로 잇고, 트랜지션이 끝나는 지점에서
        정확히 잘라 반환한다 (make_crossfade와 동일한 원리, 서로 다른 두 클립 버전)."""
        adur = float(self.probe(a_path, "format=duration", stream="v:0"))
        if adur <= fade_sec:
            raise RuntimeError("구간이 너무 짧아 이어붙이기용 크로스페이드를 적용할 수 없습니다")
        offset = max(0.0, adur - fade_sec - 0.05)
        out_len = offset + fade_sec
        out = os.path.join(tmp, out_name)
        rc, _, err = self.run([
            FFMPEG, "-v", "error", "-i", a_path, "-i", b_path,
            "-filter_complex",
            f"[0:v][1:v]xfade=transition=dissolve:duration={fade_sec:.3f}:offset={offset:.3f},format=yuv420p",
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-t", f"{out_len:.4f}", "-y", out])
        if rc != 0:
            raise RuntimeError("구간 이어붙이기 실패:\n" + err.decode("utf-8", "ignore")[-300:])
        return out

    def _trim_piece(self, src, tmp, out_name, start=None, end=None):
        """src의 [start, end) 구간만 잘라낸다 (start/end 중 하나는 생략 가능)."""
        out = os.path.join(tmp, out_name)
        parts = []
        if start is not None:
            parts.append(f"start={start:.3f}")
        if end is not None:
            parts.append(f"end={end:.3f}")
        rc, _, err = self.run([
            FFMPEG, "-v", "error", "-i", src,
            "-vf", f"trim={':'.join(parts)},setpts=PTS-STARTPTS,format=yuv420p",
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-y", out])
        if rc != 0:
            raise RuntimeError("구간 트림 실패:\n" + err.decode("utf-8", "ignore")[-300:])
        return out

    def build_composite_unit(self, clip_a, clip_b, fade_sec, tmp):
        """서로 다른 두 구간(clip_a, clip_b)을 A→B→(다시 A로 wrap-around) 순서로
        디졸브 크로스페이드 2번으로 이어붙여 하나의 루프 단위를 만든다.

        ★ v9.6 버그 수정: make_crossfade와 똑같은 수렴 지점 버그가 있었음 — 전환이
        상대 클립의 '전체'로 블렌딩되면 트랜지션은 그 클립의 t=0이 아니라
        t=fade_sec 지점으로 수렴한다. 그런데 마지막 wrap-around 전환(B→A)이
        clip_a '전체'를 향해 블렌딩되고 있어서, 합쳐진 유닛의 끝(A의 t=fade_sec로
        수렴)과 시작(A의 t=0)이 fade_sec만큼 어긋나 있었다 — 반복마다 그만큼
        되감기는 이음새가 생기는 원인.

        수정: 각 구간을 head(처음 fade_sec, 다음 전환의 블렌딩 대상 전용)와
        body(그 이후 나머지, 실제 재생 구간)로 나눠서, 전환이 항상 상대 구간의
        head로만 수렴하게 하고, 그 body가 정확히 그 지점부터 시작하도록 맞춘다."""
        for c, name in ((clip_a, "A"), (clip_b, "B")):
            dur = float(self.probe(c, "format=duration", stream="v:0"))
            if dur <= fade_sec * 2:
                raise RuntimeError(f"구간 {name}이 너무 짧아 이어붙이기 크로스페이드를 적용할 수 없습니다")

        a_head = self._trim_piece(clip_a, tmp, "a_head.mp4", end=fade_sec)
        a_body = self._trim_piece(clip_a, tmp, "a_body.mp4", start=fade_sec)
        b_head = self._trim_piece(clip_b, tmp, "b_head.mp4", end=fade_sec)
        b_body = self._trim_piece(clip_b, tmp, "b_body.mp4", start=fade_sec)

        self.log(f"  🔗 구간 A→B 이음새 크로스페이드 ({fade_sec:.1f}초)...")
        join_ab = self._xfade_join_cut(a_body, b_head, fade_sec, tmp, "join_ab.mp4")
        self.log(f"  🔗 구간 B→A(wrap-around) 이음새 크로스페이드 ({fade_sec:.1f}초)...")
        join_ba = self._xfade_join_cut(b_body, a_head, fade_sec, tmp, "join_ba.mp4")

        list_txt = os.path.join(tmp, "composite_list.txt")
        with open(list_txt, "w", encoding="utf-8") as f:
            for p in (join_ab, join_ba):
                f.write("file '" + p.replace("'", "'\\''") + "'\n")
        out = os.path.join(tmp, "unit_composite.mp4")
        rc, _, err = self.run([
            FFMPEG, "-v", "error", "-f", "concat", "-safe", "0", "-i", list_txt,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-y", out])
        if rc != 0:
            raise RuntimeError("구간 합치기 실패:\n" + err.decode("utf-8", "ignore")[-300:])
        self.log("  ✅ 두 구간을 하나의 루프 단위로 결합 완료")
        return out

    # ---------- 5단계: v5 모션 보간 (실제 4프레임 사용 — 잔상 개선 핵심) ----------
    def make_morph(self, src, s, e, fps, tmp, smooth):
        factor, t_start, t_end = smooth
        # ★ v5 핵심: 복제 프레임이 아닌 실제 연속 프레임 사용
        #   재생 순서: ... (e-2) (e-1) [모프] (s) (s+1) ...
        seq = [e - 2, e - 1, s, s + 1]
        for i, fi in enumerate(seq, 1):
            self.extract_frame_png(src, fi, os.path.join(tmp, f"t{i}.png"))

        morph = os.path.join(tmp, "morph.mp4")
        in_rate = fps / factor
        rc, _, err = self.run([
            FFMPEG, "-v", "error",
            "-framerate", f"{in_rate:.5f}",
            "-i", os.path.join(tmp, "t%d.png"),
            "-vf",
            (f"minterpolate=fps={fps:.5f}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=none,"
             f"trim=start_frame={t_start}:end_frame={t_end},setpts=PTS-STARTPTS,format=yuv420p"),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-y", morph])
        if rc != 0:
            raise RuntimeError("보간 실패")
        nf = self.probe(morph, "stream=nb_frames")
        need = t_end - t_start
        if not nf or int(nf) < need:
            raise RuntimeError("모프 프레임 부족")
        self.log(f"  ✅ 모션 보간 {need}프레임 생성 (실제 프레임 기반 — v5)")
        return morph

    # ---------- 6-A: 오디오 볼륨 분석 → 페이드 구간 자동 감지 (v6) ----------
    def analyze_audio_edges(self, audio_path, adur):
        """앞뒤 페이드인/아웃 구간을 RMS로 감지해 균일 볼륨 구간 [start, end]초를 반환"""
        sr = 8000
        rc, out, _ = self.run([
            FFMPEG, "-v", "error", "-i", audio_path,
            "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"])
        if rc != 0 or len(out) < sr * 2:
            self.log("  ⚠️ 볼륨 분석 실패 → 페이드 제거 없이 진행")
            return 0.0, adur
        pcm = np.frombuffer(out, dtype=np.int16).astype(np.float32)
        win = int(sr * 0.05)                       # 50ms 창
        n_win = len(pcm) // win
        if n_win < 20:
            return 0.0, adur
        rms = np.sqrt((pcm[: n_win * win].reshape(n_win, win) ** 2).mean(axis=1))

        # 몸통(가운데 60%) 기준 볼륨
        lo, hi = int(n_win * 0.2), int(n_win * 0.8)
        body = float(np.median(rms[lo:hi]))
        if body <= 1e-6:
            return 0.0, adur
        thresh = body * 0.7                        # 몸통의 70% 미만 = 페이드 구간으로 판정

        # 앞에서부터: 연속 4창(0.2초) 이상 기준을 넘는 첫 지점
        def first_stable(seq):
            run = 0
            for i, v in enumerate(seq):
                run = run + 1 if v >= thresh else 0
                if run >= 4:
                    return i - 3
            return 0

        s_idx = first_stable(rms)
        e_idx = n_win - 1 - first_stable(rms[::-1])
        start_t = s_idx * 0.05
        end_t = (e_idx + 1) * 0.05
        # 감지 결과가 이상하면(너무 짧게 남으면) 원본 그대로
        if end_t - start_t < 3.0:
            self.log("  ⚠️ 균일 구간이 너무 짧아 페이드 제거 생략")
            return 0.0, adur
        cut_front = start_t
        cut_back = adur - end_t
        if cut_front > 0.05 or cut_back > 0.05:
            self.log(f"  🔍 페이드 감지: 앞 {cut_front:.1f}초 / 뒤 {cut_back:.1f}초 자동 제거"
                     f" (균일 볼륨 구간 {end_t - start_t:.1f}초 사용)")
        else:
            self.log("  🔍 페이드 없음 (앞뒤 볼륨 균일) — 전체 사용")
        return start_t, end_t

    # ---------- 6-B: 이음새 없는 오디오 루프 (v6: 페이드 제거 + 평탄화 옵션) ----------
    def make_audio_loop(self, audio_path, tmp, flatten=False):
        dur_raw = self.probe(audio_path, "format=duration", stream="a:0")
        if not dur_raw:
            raise RuntimeError("오디오 정보를 읽을 수 없습니다")
        adur = float(dur_raw)
        if adur < 3.0:
            raise RuntimeError("오디오가 너무 짧습니다 (3초 이상 필요)")

        # ★ v6: 앞뒤 페이드 구간 자동 제거
        start_t, end_t = self.analyze_audio_edges(audio_path, adur)

        # 1단계: 균일 구간만 잘라내기 (+선택: 볼륨 평탄화)
        trimmed = os.path.join(tmp, "audio_trim.wav")
        af = f"atrim=start={start_t:.3f}:end={end_t:.3f},asetpts=PTS-STARTPTS"
        if flatten:
            af += ",dynaudnorm=f=2000:g=31:p=0.85:m=3.0"
        rc, _, err = self.run([
            FFMPEG, "-v", "error", "-i", audio_path,
            "-af", af, "-ac", "2", "-c:a", "pcm_s16le", "-y", trimmed])
        if rc != 0:
            raise RuntimeError("오디오 트리밍 실패:\n" + err.decode("utf-8", "ignore")[-400:])

        # 2단계: 몸통(1초 이후~끝) 끝에 머리(첫 1초)를 qsin 크로스페이드
        #  (같은 파일을 두 번 입력 — 단일 입력 분기 시 ffmpeg가 빈 출력을 내는 문제 회피)
        loop_wav = os.path.join(tmp, "audio_loop.wav")
        fc = ("[0:a]atrim=start=1,asetpts=PTS-STARTPTS[body];"
              "[1:a]atrim=0:1,asetpts=PTS-STARTPTS[head];"
              "[body][head]acrossfade=d=1:c1=qsin:c2=qsin")
        rc, _, err = self.run([
            FFMPEG, "-v", "error", "-i", trimmed, "-i", trimmed,
            "-filter_complex", fc,
            "-c:a", "pcm_s16le", "-y", loop_wav])
        if rc != 0:
            raise RuntimeError("오디오 루프 생성 실패:\n" + err.decode("utf-8", "ignore")[-400:])
        msg = "  ✅ 오디오 루프 단위 생성 (페이드 제거 + 1초 qsin 크로스페이드"
        msg += " + 볼륨 평탄화)" if flatten else ")"
        self.log(msg)
        return loop_wav

    # ---------- 7단계: 장시간 합성 (v9.3: 연속 단일 인코딩 — concat-copy 이음새 끊김 제거) ----------
    @staticmethod
    def _maxrate_mbps(out_w, out_h, out_fps):
        """해상도·프레임레이트 기준 유튜브 권장 비트레이트 상한(Mbps)"""
        px_ratio = (out_w * out_h) / (1920 * 1080)
        fps_factor = 1.5 if out_fps > 40 else 1.0
        return max(4, round(8 * px_ratio * fps_factor))

    @staticmethod
    def _video_encode_args(use_gpu, maxrate_mbps):
        """장시간 합성(assemble)과 인트로 자막 구간이 '똑같은' 인코더 설정을 쓰도록
        한 곳에 모아둔다 — 두 조각을 색인만으로 이어붙이려면 코덱 설정(SPS/PPS)이 같아야 한다."""
        if use_gpu:
            # v9.7 성능 수정: p5(중간 속도) → p1(최고속)로 한 번 낮췄다가(약 2배 빨라짐),
            # 웹 검색으로 최신 권장사항을 확인한 결과 "스트리밍/실사용에는 p4 미만은
            # 권장하지 않음, p4~p7 화질 차이는 크지 않음"이라는 의견이 일반적이라
            # p4로 재조정 — 실측상 p1 대비 약 1.7배 느려지지만(10시간 기준 약
            # 65분→112분) 여전히 이전 방식(5시간)보다 훨씬 빠르면서 화질 안정성은 더 높다.
            return ["-c:v", "h264_nvenc", "-preset", "p4", "-rc", "vbr", "-cq", "22", "-b:v", "0",
                    "-maxrate", f"{maxrate_mbps}M", "-bufsize", f"{maxrate_mbps * 2}M"]
        return ["-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-maxrate", f"{maxrate_mbps}M", "-bufsize", f"{maxrate_mbps * 2}M"]

    def assemble(self, unit_path, audio_loop, target_sec, out_path, tmp, fade=True, scale=None):
        """
        v9.2 이전 방식(버그): 이미 인코딩된 unit.mp4를 그대로 N번 파일로 복제해
        concat demuxer + '-c:v copy'로 이어붙임 → 매 반복 파일 경계(=루프 지점)마다
        B프레임/GOP 타이밍이 재정렬되며 정확히 루프 지점에서 튀는 현상 발생.
        (오디오도 동일 원인으로 AAC를 stream_loop -c copy 하면 priming 샘플 문제로 끊김 발생 — 동일한 종류의 버그)

        v9.3 수정: 압축된 파일을 반복 복사하지 않고, ffmpeg가 unit_path를 '-stream_loop -1'로
        계속 다시 열어 매번 새로 디코딩한 뒤 처음부터 끝까지 단 한 번만 연속으로 재인코딩한다.
        어떤 원본 영상을 넣어도 반복 경계에서 GOP/타임스탬프 불연속이 생기지 않는다.
        """
        udur_raw = self.probe(unit_path, "format=duration", stream="v:0")
        udur = float(udur_raw)
        n_rep = max(1, math.ceil(target_sec / udur))
        use_gpu = self._has_nvenc()
        self.log(f"  루프 단위 {udur:.2f}초 × 약 {n_rep}회 반복 = 목표 {target_sec/3600:.2f}시간"
                 f" ({'GPU h264_nvenc' if use_gpu else 'CPU libx264'}, 단일 연속 인코딩)")

        fd = min(3.0, max(1.0, udur / 3)) if fade else 0.0

        vf = "format=yuv420p"
        if scale:
            sw, sh = scale
            vf += f",scale={sw}:{sh}:flags=lanczos"
        if fade:
            vf += f",fade=t=in:st=0:d={fd:.2f},fade=t=out:st={max(0.0, target_sec - fd):.3f}:d={fd:.2f}"

        cmd = [FFMPEG, "-v", "error", "-stream_loop", "-1", "-i", unit_path]
        if audio_loop:
            cmd += ["-stream_loop", "-1", "-i", audio_loop]
            cmd += ["-map", "0:v", "-map", "1:a"]
        else:
            cmd += ["-map", "0:v"]
        # ★ v9.6 버그 수정: cq(품질 고정) 모드를 상한 없이 쓰면, 빗줄기/나뭇잎처럼
        # 프레임마다 디테일이 계속 바뀌는(노이즈성) 영상에서 비트레이트가 통제 불능으로
        # 커진다 (실측: 1080p60 10시간이 cq19 상한없음으로 165GB까지 나옴).
        # 해상도·프레임레이트 기준 유튜브 권장 비트레이트로 상한(maxrate)을 씌워
        # 품질은 유지하되 파일 크기를 예측 가능한 범위로 묶는다.
        # v9.7: scale 인자로 추측하는 대신 unit_path의 실제 해상도를 probe해서 정확히 맞춘다
        # (unit이 trim_unit 단계에서 이미 목표 해상도로 축소되어 들어오므로 이게 진짜 값).
        out_w, out_h = self.get_video_size(unit_path) or (scale if scale else (1920, 1080))
        fps_probe = self.probe(unit_path, "stream=r_frame_rate")
        try:
            fn, fd_ = fps_probe.split("/")
            out_fps = float(fn) / float(fd_)
        except Exception:
            out_fps = 30.0
        maxrate_mbps = self._maxrate_mbps(out_w, out_h, out_fps)
        self.log(f"  🎯 비트레이트 상한: {maxrate_mbps}Mbps ({out_w}x{out_h}@{out_fps:.0f}fps 기준, "
                 f"유튜브 권장치 — 10시간 예상 용량 약 {maxrate_mbps * 36000 / 8 / 1024:.0f}GB 이내)")
        # ★ v9.6 버그 수정: 위 비트레이트 상한 코드를 추가하면서 실수로 이 줄 자체가
        # 통째로 빠져 있었음 — '-t'(출력 길이 제한)가 없으면 '-stream_loop -1'
        # 무한 반복 입력이 끝없이 인코딩되어 디스크가 가득 찰 때까지 멈추지 않는다
        # (실측: 60초 테스트가 1GB를 넘기고도 계속 커짐 — 이게 원인이었음).
        cmd += ["-t", str(target_sec), "-vf", vf]
        cmd += self._video_encode_args(use_gpu, maxrate_mbps)
        cmd += ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
        if audio_loop:
            af = (f"afade=t=in:st=0:d={fd:.2f},"
                  f"afade=t=out:st={max(0.0, target_sec - fd):.3f}:d={fd:.2f}") if fade else None
            if af:
                cmd += ["-af", af]
            # v9.7: 유튜브 공식 권장 오디오 비트레이트(스테레오 AAC-LC 384kbps)에 맞춤
            cmd += ["-c:a", "aac", "-b:a", "384k"]
        else:
            cmd += ["-an"]
        cmd += ["-movflags", "+faststart", "-y", out_path]

        rc, _, err = self.run(cmd)
        if rc != 0:
            raise RuntimeError("최종 합성 실패:\n" + err.decode("utf-8", "ignore")[-400:])

    # ---------- v9.7/v10: 인트로 자막 (맨 앞부분에만 한 번, 루프 반복 없음) ----------
    def _render_caption_overlay(self, W, H, caption_kr, caption_en, tmp):
        """한글(위, 흰색) + 영문(아래, 노랑) 자막을 투명 PNG로 만들어 경로를 돌려준다."""
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(ov)

        def wrap(text, font, max_w):
            words = text.split(" ")
            lines, cur = [], ""
            for w in words:
                trial = (cur + " " + w).strip()
                bb = draw.textbbox((0, 0), trial, font=font)
                if bb[2] - bb[0] <= max_w or not cur:
                    cur = trial
                else:
                    lines.append(cur)
                    cur = w
            if cur:
                lines.append(cur)
            return lines

        def draw_block(lines, font, y, fill, stroke):
            for ln in lines:
                bb = draw.textbbox((0, 0), ln, font=font, stroke_width=stroke)
                x = (W - (bb[2] - bb[0])) // 2 - bb[0]
                draw.text((x, y - bb[1]), ln, font=font, fill=fill,
                          stroke_width=stroke, stroke_fill=(10, 10, 10, 255))
                y += (bb[3] - bb[1]) + int(H * 0.012)
            return y

        scale_ref = H / 1080.0
        kr_font = find_font(max(28, int(52 * scale_ref)), True)
        en_font = find_font(max(22, int(40 * scale_ref)), False)
        max_w = int(W * 0.8)
        kr_lines = wrap(caption_kr.strip(), kr_font, max_w) if caption_kr.strip() else []
        en_lines = wrap(caption_en.strip(), en_font, max_w) if caption_en.strip() else []

        lh_kr = (draw.textbbox((0, 0), "가", font=kr_font)[3] + int(H * 0.012)) if kr_lines else 0
        lh_en = (draw.textbbox((0, 0), "A", font=en_font)[3] + int(H * 0.012)) if en_lines else 0
        block_h = lh_kr * len(kr_lines) + lh_en * len(en_lines) + int(H * 0.04)
        top = (H - block_h) // 2
        pad = int(H * 0.03)
        draw.rounded_rectangle(
            [int(W * 0.05), top - pad, int(W * 0.95), top + block_h + pad],
            radius=int(H * 0.02), fill=(0, 0, 0, 140))

        y = top
        y = draw_block(kr_lines, kr_font, y, (255, 255, 255, 255), max(3, int(6 * scale_ref)))
        if kr_lines and en_lines:
            y += int(H * 0.01)
        draw_block(en_lines, en_font, y, (255, 200, 60, 255), max(2, int(5 * scale_ref)))

        ov_png = os.path.join(tmp, "intro_caption.png")
        ov.save(ov_png, "PNG")
        return ov_png

    def _render_title_card(self, W, H, title, tmp, label_kr="오늘 밤의 이야기",
                           label_en="Tonight's Bedtime Mystery"):
        """v11.5: 영상 첫 몇 초에 보여줄 이야기 제목 카드 (가운데 어두운 띠 + 금색 라벨 + 큰 제목)"""
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        bd = ImageDraw.Draw(band)
        sr = H / 1080.0
        f_lab = find_font(max(22, int(34 * sr)), True)
        f_en = find_font(max(18, int(28 * sr)), False)
        size = int(96 * sr)
        title = f"「{title.strip()}」"
        while size > int(40 * sr):
            f_title = find_font(size, True)
            bb = bd.textbbox((0, 0), title, font=f_title, stroke_width=max(2, int(4 * sr)))
            if bb[2] - bb[0] <= W * 0.86:
                break
            size -= int(4 * sr) or 2
        f_title = find_font(size, True)
        tb = bd.textbbox((0, 0), title, font=f_title, stroke_width=max(2, int(4 * sr)))
        lb = bd.textbbox((0, 0), label_kr, font=f_lab)
        eb = bd.textbbox((0, 0), label_en, font=f_en)
        gap = int(22 * sr)
        block = (lb[3] - lb[1]) + gap + (tb[3] - tb[1]) + gap + (eb[3] - eb[1])
        top = (H - block) // 2
        pad = int(60 * sr)
        # 위아래로 부드럽게 사라지는 어두운 띠
        y0, y1 = top - pad, top + block + pad
        for y in range(max(0, y0 - pad), min(H, y1 + pad)):
            if y < y0:
                a = int(150 * (y - (y0 - pad)) / pad)
            elif y > y1:
                a = int(150 * ((y1 + pad) - y) / pad)
            else:
                a = 150
            bd.line([(0, y), (W, y)], fill=(0, 0, 0, max(0, min(150, a))))
        ov = Image.alpha_composite(ov, band)
        d = ImageDraw.Draw(ov)
        y = top
        d.text(((W - (lb[2] - lb[0])) // 2 - lb[0], y - lb[1]), label_kr, font=f_lab,
               fill=(255, 205, 90, 255))
        y += (lb[3] - lb[1]) + gap
        d.text(((W - (tb[2] - tb[0])) // 2 - tb[0], y - tb[1]), title, font=f_title,
               fill=(255, 255, 255, 255), stroke_width=max(2, int(4 * sr)), stroke_fill=(10, 10, 10, 255))
        y += (tb[3] - tb[1]) + gap
        d.text(((W - (eb[2] - eb[0])) // 2 - eb[0], y - eb[1]), label_en, font=f_en,
               fill=(215, 215, 215, 255))
        out = os.path.join(tmp, "title_card.png")
        ov.save(out, "PNG")
        return out

    def _encode_caption_clip(self, video_path, ov_png, caption_sec, clip_sec, out_path,
                             delay=0.0, fade_in=1.5, fade_out=1.8):
        """영상 맨 앞 clip_sec초를 자막 오버레이(서서히 나타났다 사라짐)와 함께 새로 인코딩.
        assemble()과 '같은' 인코더 설정을 쓴다 (색인 이어붙이기 방식은 코덱 설정이 같아야 함)."""
        size = self.get_video_size(video_path)
        if not size:
            raise RuntimeError("영상 해상도를 읽을 수 없습니다")
        try:
            fn, fd_ = (self.probe(video_path, "stream=r_frame_rate") or "30/1").split("/")
            fps = float(fn) / float(fd_)
        except Exception:
            fps = 30.0
        maxrate = self._maxrate_mbps(size[0], size[1], fps)
        # v11.5: delay초 뒤에 나타나게 할 수 있음 (앞에 이야기 제목 카드가 있을 때 겹치지 않도록)
        fade_in_st = max(0.0, delay)
        fade_out_st = max(fade_in_st + fade_in, delay + caption_sec - fade_out)
        rc, _, err = self.run([
            FFMPEG, "-v", "error", "-t", f"{clip_sec:.3f}", "-i", video_path,
            "-loop", "1", "-i", ov_png,
            "-filter_complex",
            (f"[1:v]format=yuva420p,fade=t=in:st={fade_in_st:.2f}:d={fade_in}:alpha=1,"
             f"fade=t=out:st={fade_out_st:.2f}:d={fade_out}:alpha=1[ov];"
             "[0:v][ov]overlay=0:0:format=auto,format=yuv420p[v]"),
            "-map", "[v]", "-map", "0:a?", "-t", f"{clip_sec:.3f}",
            *self._video_encode_args(self._has_nvenc(), maxrate),
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-c:a", "aac", "-b:a", "384k",
            "-y", out_path])
        if rc != 0:
            raise RuntimeError("인트로 자막 구간 생성 실패:\n" + err.decode("utf-8", "ignore")[-400:])

    def _verify_spliced(self, path, orig_dur, t_cut):
        """이어붙인 결과가 정상인지 검사: 길이 + 시작/이음새/중간/끝 부분을 실제로 디코딩."""
        new_dur = float(self.probe(path, "format=duration", stream="v:0") or 0)
        if abs(new_dur - orig_dur) > 1.0:
            raise RuntimeError(f"길이가 원본과 다릅니다 ({orig_dur:.1f}초 → {new_dur:.1f}초)")
        for ss in (0.0, max(0.0, t_cut - 3.0), orig_dur * 0.5, max(0.0, orig_dur - 9.0)):
            rc, _, err = self.run([FFMPEG, "-v", "error", "-ss", f"{ss:.2f}", "-t", "6",
                                   "-i", path, "-f", "null", "-"])
            if rc != 0 or err.strip():
                raise RuntimeError(f"{ss:.0f}초 부근 재생 검사 실패: "
                                   + err.decode("utf-8", "ignore")[-200:])

    def _insert_caption_fast(self, video, caption_kr, caption_en, tmp, caption_sec,
                             delay=0.0, fade_in=1.5, fade_out=1.8, ov_png=None):
        """★ v10 빠른 방식(원본 제자리 수정): 앞부분만 새로 인코딩하고 색인만 새로 써서
        10시간(약 50GB) 영상도 수십 초 안에, 추가 디스크 사용 없이 끝낸다.
        구조가 맞지 않으면 Mp4Unsupported, 실패/검증 실패 시 원본을 바이트 그대로 복구."""
        if not HAS_PIL:
            raise RuntimeError("Pillow가 필요합니다: pip install pillow")
        size = self.get_video_size(video)
        if not size:
            raise RuntimeError("영상 해상도를 읽을 수 없습니다")
        orig_dur = float(self.probe(video, "format=duration", stream="v:0") or 0)
        if orig_dur <= 0:
            raise RuntimeError("영상 길이를 읽을 수 없습니다")
        plan = mp4_plan_cut(video, caption_sec + delay)      # 원본은 아직 건드리지 않음
        t_cut = plan["t_cut"]
        ov_png = ov_png or self._render_caption_overlay(size[0], size[1], caption_kr, caption_en, tmp)
        self.log(f"  ⚡ 빠른 방식: 맨 앞 약 {t_cut:.0f}초만 새로 인코딩합니다 "
                 f"(나머지 영상은 복사·재인코딩 없이 그대로 사용)")
        intro = os.path.join(tmp, "intro_fast.mp4")
        self._encode_caption_clip(video, ov_png, caption_sec, t_cut + 1.0, intro,
                                  delay=delay, fade_in=fade_in, fade_out=fade_out)
        self.log("  🔗 새 앞부분을 파일 끝에 붙이고 재생 순서(색인)만 새로 쓰는 중...")
        e0, moov_pos, old_moov_bytes = mp4_splice(video, intro, plan, log=self.log)   # 실패하면 스스로 원본 복구
        self.log("  🔍 결과 검증 중 (길이 + 시작·이음새·중간·끝 부분 재생 검사)...")
        try:
            self._verify_spliced(video, orig_dur, t_cut)
        except InterruptedError:
            mp4_rollback(video, e0, moov_pos, old_moov_bytes)
            raise
        except Exception as ex:
            mp4_rollback(video, e0, moov_pos, old_moov_bytes)
            raise RuntimeError(f"결과 검증 실패 — 원본을 그대로 복구했습니다 ({ex})") from ex
        self.log(f"  ✅ 인트로 자막 삽입 완료 (맨 앞 약 {t_cut:.0f}초에만, 반복되지 않음)")

    def _next_keyframe_time(self, video_path, after_sec):
        """after_sec 이후 첫 키프레임의 시각(초). 못 찾으면 None.
        v11.10: 프레임 pts가 비어 나오는 ffprobe 버전이 있어, 패킷(K 표시) 기준으로 먼저 찾고
        키프레임 간격이 길어도 찾도록 탐색 구간을 넉넉히(60초) 잡는다."""
        rc, out, _ = self.run([
            FFPROBE, "-v", "error", "-select_streams", "v:0",
            "-show_entries", "packet=pts_time,flags", "-of", "csv=p=0",
            "-read_intervals", f"{max(0.0, after_sec - 1):.3f}%+60", video_path])
        if rc == 0:
            best = None
            for ln in out.decode("utf-8", "ignore").splitlines():
                parts = ln.strip().split(",")
                if len(parts) < 2 or "K" not in parts[1]:
                    continue
                try:
                    t = float(parts[0])
                except ValueError:
                    continue
                if t >= after_sec - 1e-3 and (best is None or t < best):
                    best = t
            if best is not None:
                return best
        rc, out, _ = self.run([
            FFPROBE, "-v", "error", "-select_streams", "v:0", "-skip_frame", "nokey",
            "-show_entries", "frame=pts_time", "-of", "csv=p=0",
            "-read_intervals", f"{after_sec:.3f}%+60", video_path])
        if rc != 0:
            return None
        for tok in out.decode("utf-8", "ignore").split():
            try:
                t = float(tok.strip(","))
            except ValueError:
                continue
            if t >= after_sec - 1e-3:
                return t
        return None

    def _watch_output_growth(self, out_path, total_bytes):
        """오래 걸리는 파일 작성 중 진행률(%)·남은 시간 추정을 5%마다 로그로 알려주는 감시 스레드.
        반환된 Event를 set()하면 멈춘다."""
        stop = threading.Event()

        def loop():
            t0, last = time.time(), 0
            while not stop.wait(5.0):
                try:
                    cur = os.path.getsize(out_path)
                except OSError:
                    continue
                pct = min(99, int(cur * 100 / max(1, total_bytes)))
                if pct >= last + 5:
                    last = pct - pct % 5
                    el = time.time() - t0
                    eta = el * (100 - pct) / max(1, pct)
                    self.log(f"     … {pct}% ({cur / 1024 ** 3:.1f}/{total_bytes / 1024 ** 3:.1f}GB, "
                             f"남은 시간 약 {eta / 60:.0f}분)")
        threading.Thread(target=loop, daemon=True).start()
        return stop

    def add_intro_caption(self, video_path, caption_kr, caption_en, out_path, tmp,
                          caption_sec=30.0, delay=0.0, fade_in=1.5, fade_out=1.8, ov_png=None):
        """[기존(느린) 방식 — 빠른 방식을 쓸 수 없을 때의 대체 수단]
        맨 앞 caption_sec초만 새로 인코딩하고, 나머지는 스트림 복사로 이어붙여 새 파일을 만든다.
        (원본 크기만큼 파일 전체를 다시 써야 해서 10시간짜리는 하드디스크에서 오래 걸린다)"""
        if not HAS_PIL:
            raise RuntimeError("Pillow가 필요합니다: pip install pillow")
        size = self.get_video_size(video_path)
        if not size:
            raise RuntimeError("영상 해상도를 읽을 수 없습니다")
        # v9.7 안전장치: 자막 구간이 영상 전체 길이보다 길면(짧은 테스트 영상 등)
        # 뒷부분(remainder)이 아예 없어져서 이어붙이기가 깨진다 — 여유 2초를 두고 제한.
        total_dur = float(self.probe(video_path, "format=duration", stream="v:0") or 0)
        if total_dur > 0:
            caption_sec = min(caption_sec, max(2.0, total_dur - 2.0 - delay))

        # v9.7: 필요 공간 사전 점검 (concat demuxer의 inpoint로 원본을 직접 참조하므로
        # 중간 복사본 없이 원본 + 최종본, 최대 약 2배만 필요)
        out_dir_check = os.path.dirname(os.path.abspath(out_path)) or "."
        try:
            src_size = os.path.getsize(video_path)
            free = shutil.disk_usage(out_dir_check).free
            need = int(src_size * 1.15)
            if free < need:
                raise RuntimeError(
                    f"디스크 여유 공간이 부족합니다 (필요 약 {need/1024**3:.1f}GB, "
                    f"남은 공간 {free/1024**3:.1f}GB) — 다른 파일을 정리한 뒤 다시 시도해주세요.")
        except OSError:
            pass

        # v10: 이음새를 '정확히 30.000초'가 아니라 그 뒤 첫 키프레임에 맞춘다. 키프레임이
        # 아닌 곳에서 자르면 B프레임 순서가 꼬여 이음새에서 타임스탬프 오류(dts 역전,
        # 프레임 중복/누락)가 났다 (실측: 정렬 후 경고 0건, 프레임 수 정확).
        cut = caption_sec + delay
        clip_sec = caption_sec + delay
        kt = self._next_keyframe_time(video_path, caption_sec + delay)
        if kt is not None and (total_dur <= 0 or kt <= total_dur - 2.0):
            try:
                fn, fd_ = (self.probe(video_path, "stream=r_frame_rate") or "30/1").split("/")
                fps = float(fn) / float(fd_)
            except Exception:
                fps = 30.0
            cut = kt
            clip_sec = kt - 0.5 / fps          # 키프레임 직전 프레임까지만 (반 프레임 여유)

        ov_png = ov_png or self._render_caption_overlay(size[0], size[1], caption_kr, caption_en, tmp)
        self.log(f"  📝 인트로 자막 구간(약 {cut:.0f}초)만 새로 인코딩 중...")
        intro_clip = os.path.join(tmp, "intro_with_caption.mp4")
        self._encode_caption_clip(video_path, ov_png, caption_sec, clip_sec, intro_clip,
                                  delay=delay, fade_in=fade_in, fade_out=fade_out)

        self.log("  ⏩ 나머지 구간을 원본에서 그대로 이어붙이는 중... (영상 전체를 새 파일로 쓰는 "
                 "작업이라 시간이 오래 걸릴 수 있어요)")
        list_txt = os.path.join(tmp, "caption_concat_list.txt")
        with open(list_txt, "w", encoding="utf-8") as f:
            f.write("file '" + intro_clip.replace("'", "'\\''") + "'\n")
            abs_video = os.path.abspath(video_path)
            f.write("file '" + abs_video.replace("'", "'\\''") + "'\n")
            f.write(f"inpoint {cut:.6f}\n")
        # v10: '-movflags +faststart'를 뺐다 — 이 옵션은 파일을 다 쓴 뒤 처음부터 끝까지
        # 한 번 더 통째로 다시 쓰게 만들어(실측 약 40% 더 오래 걸림) 시간만 늘렸고,
        # 유튜브 업로드에는 필요하지 않다.
        stop_watch = self._watch_output_growth(out_path, os.path.getsize(video_path))
        try:
            rc, _, err = self.run([
                FFMPEG, "-v", "error", "-f", "concat", "-safe", "0", "-i", list_txt,
                "-c", "copy", "-y", out_path])
        finally:
            stop_watch.set()
        if rc != 0:
            raise RuntimeError("최종 합치기 실패:\n" + err.decode("utf-8", "ignore")[-400:])
        self.log(f"  ✅ 인트로 자막 삽입 완료 (맨 앞 약 {cut:.0f}초에만, 반복되지 않음)")
        return out_path

    def insert_intro_caption(self, video, caption_kr, caption_en, tmp, caption_sec=30.0,
                             delay=0.0, fade_in=1.5, fade_out=1.8, ov_png=None):
        """인트로 자막을 영상에 넣고 원본을 그 결과로 대체한다 (파일이 2벌 남지 않음).
        1순위: 빠른 제자리 방식(수십 초, 추가 디스크 0) → 안 되면 2순위: 기존 방식.
        반환: 'fast' | 'slow' | 'slow_kept'(검증 실패로 자막본을 별도 파일로만 남김)"""
        try:
            self._insert_caption_fast(video, caption_kr, caption_en, tmp, caption_sec, delay=delay, fade_in=fade_in, fade_out=fade_out, ov_png=ov_png)
            return "fast"
        except Mp4Unsupported as ex:
            self.log(f"  ℹ️ 이 영상은 빠른 방식을 쓸 수 없어 기존 방식으로 진행합니다 ({ex}) — "
                     f"시간이 더 걸릴 수 있어요")
        except PermissionError:
            raise RuntimeError("영상 파일이 다른 프로그램(영상 재생기·업로드 창 등)에서 열려 있어 "
                               "수정할 수 없습니다. 그 프로그램을 닫고 다시 시도해주세요.")
        except RuntimeError as ex:
            self.log(f"  ℹ️ 빠른 방식이 실패해 기존 방식으로 다시 시도합니다: {ex}")

        base, ext = os.path.splitext(video)
        cap_out = base + "_자막" + ext
        self.add_intro_caption(video, caption_kr, caption_en, cap_out, tmp,
                               caption_sec=caption_sec, delay=delay, fade_in=fade_in, fade_out=fade_out, ov_png=ov_png)
        # v9.7: 원본을 지우기 전에, 자막본이 실제로 정상인지(길이가 원본과 거의 같은지) 검증
        orig_dur = float(self.probe(video, "format=duration", stream="v:0") or 0)
        new_dur = float(self.probe(cap_out, "format=duration", stream="v:0") or 0)
        if os.path.exists(cap_out) and orig_dur > 0 and abs(new_dur - orig_dur) < 5.0:
            os.remove(video)
            os.replace(cap_out, video)
            self.log(f"  🗑️ 검증 완료 — 원본을 지우고 자막본으로 교체했습니다 (용량 중복 방지) → {video}")
            return "slow"
        self.log(f"  ⚠️ 자막본 길이 검증에 실패해 원본은 그대로 두고 자막본만 별도로 남겨뒀습니다: {cap_out}")
        return "slow_kept"

    # ---------- 전체 실행 ----------
    def process(self, video, audio, out_dir, target_sec, smooth_name, audio_flatten=False,
                fade=True, loop_unit="일반 (4초 이상 — 자동 최적 구간 탐색)",
                short_unit_sec=2.0):
        tmp = tempfile.mkdtemp(prefix="loopmaker_")
        base = os.path.splitext(os.path.basename(video))[0]
        hours = target_sec / 3600
        tag = f"{int(hours)}h" if hours >= 1 else f"{int(target_sec // 60)}m"
        if loop_unit.startswith("단위 반복"):
            method = f"unit{int(short_unit_sec)}s"
        else:
            method = "xfade" if smooth_name in CROSSFADE_PRESETS else "morph"
        out_path = os.path.join(out_dir, f"{base}_loop_{tag}_{method}.mp4")
        try:
            self.log("① 영상 분석 중...")
            fps, duration = self.get_video_info(video)
            dur = duration   # 하위 호환
            size = self.get_video_size(video)
            scale_to = None
            if size and size[0] > 1920:
                scale_to = (1920, round(1920 * size[1] / size[0] / 2) * 2)
                self.log(f"  {fps:.2f}fps / {duration:.1f}초 / {size[0]}x{size[1]}"
                         f" → 10시간 파일 용량 문제로 {scale_to[0]}x{scale_to[1]}로 축소해서 저장")
            else:
                self.log(f"  {fps:.2f}fps / {duration:.1f}초"
                         + (f" / {size[0]}x{size[1]}" if size else ""))

            # ★ v9.7 버그 수정: "단위 반복 (짧은 클립 그대로 이어붙이기)"를 선택해도
            # 실제로는 아무 동작도 다르지 않고 출력 파일명 접미사만 바뀌고 있었다
            # (탐색·스무딩을 전부 건너뛰고 그냥 지정한 길이를 그대로 반복해야 함).
            # 이제 진짜로 분석/스무딩을 모두 건너뛰고 처음 short_unit_sec초를 그대로 쓴다.
            if loop_unit.startswith("단위 반복"):
                self.log(f"②~⑤ 건너뜀 — '단위 반복' 모드: 지정한 {short_unit_sec:.0f}초를 "
                         f"탐색·스무딩 없이 그대로 반복합니다")
                unit = os.path.join(tmp, "unit.mp4")
                end_frame = max(1, int(short_unit_sec * fps))
                self.trim_unit(video, 0, end_frame, fps, unit, scale=scale_to)

                audio_loop = None
                if audio:
                    self.log("⑥ 오디오 루프 생성 중... (v6: 페이드 자동 제거)")
                    audio_loop = self.make_audio_loop(audio, tmp, flatten=audio_flatten)
                else:
                    self.log("⑥ 오디오 없음 → 무음 영상으로 진행")

                self.log("⑦ 장시간 영상 합성 중...")
                self.assemble(unit, audio_loop, target_sec, out_path, tmp, fade=fade)

                size_gb = os.path.getsize(out_path) / (1024 ** 3)
                self.log(f"\n🎉 완성! ({size_gb:.2f} GB)\n📁 {out_path}")
                return out_path

            # ★ v9.2: 짧은 클립(3초 미만)은 자동으로 복수 연결해서 분석
            #   2초 클립 → 4개 이어붙여 8초 소스로 → 루프 탐색 → 2초 단위 루프
            if duration < 3.0:
                n_pre = max(2, int(np.ceil(6.0 / max(duration, 0.5))))
                self.log(f"  ⚡ {duration:.1f}초 짧은 클립 감지 → {n_pre}개 이어붙여 분석 ({duration*n_pre:.1f}초)")
                pre_list = os.path.join(tmp, "pre_list.txt")
                pre_joined = os.path.join(tmp, "pre_joined.mp4")
                with open(pre_list, "w", encoding="utf-8") as f:
                    for _ in range(n_pre):
                        f.write(f"file '{video}'\n")
                rc, _, err = self.run([FFMPEG, "-v", "error",
                                       "-f", "concat", "-safe", "0", "-i", pre_list,
                                       "-c", "copy", "-y", pre_joined])
                if rc != 0:
                    raise RuntimeError("짧은 클립 이어붙이기 실패")
                analyse_src = pre_joined
            else:
                analyse_src = video

            analyse_dur = duration * n_pre if duration < 3.0 else duration
            want_sec = min(analyse_dur, 300.0)   # v9.4: 최대 5분까지 분석 대상
            want_frames = int(want_sec * fps)
            self.log(f"② 프레임 추출 중... (128x72 정밀 분석, 최대 {want_sec:.0f}초 대상)")
            frames, step = self.extract_gray_frames_strided(analyse_src, want_frames)
            if step > 1:
                self.log(f"  {len(frames)}개 샘플 프레임 추출 완료 (매 {step}프레임당 1장 — "
                         f"{step/fps*1000:.0f}ms 단위 굵은 탐색, 유효 {len(frames)*step/fps:.0f}초)")
            else:
                self.log(f"  {len(frames)}프레임 추출 완료 (매 프레임 정밀 탐색)")

            self.log("③ 최적 루프 지점 탐색 중... (v9.4: 2초~5분 다중 길이 후보 분석)")
            segments = self.find_loop_points(frames, fps, step)
            for (ss, ee) in segments:
                if ee - ss < 4 or ss + 2 > len(frames) * step or ee < 2:
                    raise RuntimeError("루프 구간이 유효하지 않습니다")

            self.log(f"④ 루프 단위 영상 생성 중... ({len(segments)}개 구간)")
            trimmed_clips = []
            for i, (ss, ee) in enumerate(segments):
                tpath = os.path.join(tmp, f"unit_raw_{i}.mp4")
                self.trim_unit(analyse_src, ss, ee, fps, tpath, scale=scale_to)
                trimmed_clips.append(tpath)
            trimmed = trimmed_clips[0]
            s, e = segments[0]

            unit = os.path.join(tmp, "unit.mp4")
            if len(segments) >= 2:
                # v9.4: 서로 다른 두 구간을 이어붙이는 경우 — 모션 보간은 두 구간이
                # 실제로 연속된 프레임이 아니므로 적용 불가, 항상 크로스페이드로 연결.
                fade_sec = CROSSFADE_PRESETS.get(smooth_name, 1.0)
                if smooth_name not in CROSSFADE_PRESETS:
                    self.log(f"⑤ 두 구간 이어붙이기 — 모션 보간은 다중 구간에 적용할 수 없어 "
                             f"크로스페이드({fade_sec:.1f}초)로 대체")
                else:
                    self.log(f"⑤ 두 구간을 크로스페이드({fade_sec:.1f}초)로 이어붙이는 중...")
                try:
                    unit = self.build_composite_unit(trimmed_clips[0], trimmed_clips[1], fade_sec, tmp)
                except InterruptedError:
                    raise
                except Exception as ex:
                    self.log(f"  ⚠️ 구간 이어붙이기 실패({ex}) → 첫 번째 구간만 사용")
                    shutil.copy(trimmed, unit)
            elif smooth_name in CROSSFADE_PRESETS:
                # 크로스페이드 방식: 빗줄기처럼 방향이 달라도 자연스럽게
                self.log(f"⑤ 크로스페이드 이음새 적용 중... ({smooth_name})")
                fade_sec = CROSSFADE_PRESETS[smooth_name]
                try:
                    unit = self.make_crossfade(trimmed, fps, fade_sec, tmp)
                except InterruptedError:
                    raise
                except Exception as ex:
                    self.log(f"  ⚠️ 크로스페이드 실패({ex}) → 하드컷으로 대체")
                    shutil.copy(trimmed, unit)
            else:
                # 기존 모션 보간 방식
                self.log("⑤ 모션 보간 중... (v5 잔상 개선 방식)")
                smooth = SMOOTH_PRESETS[smooth_name]
                try:
                    morph = self.make_morph(analyse_src, s, e, fps, tmp, smooth)
                    clist = os.path.join(tmp, "unit_list.txt")
                    with open(clist, "w", encoding="utf-8") as f:
                        f.write(f"file '{trimmed}'\nfile '{morph}'\n")
                    rc, _, err = self.run([
                        FFMPEG, "-v", "error", "-f", "concat", "-safe", "0",
                        "-i", clist, "-c", "copy", "-y", unit])
                    if rc != 0:
                        raise RuntimeError("단위 결합 실패")
                except InterruptedError:
                    raise
                except Exception as ex:
                    self.log(f"  ⚠️ 보간 실패({ex}) → 정밀 매칭 하드컷으로 대체")
                    shutil.copy(trimmed, unit)

            audio_loop = None
            if audio:
                self.log("⑥ 오디오 루프 생성 중... (v6: 페이드 자동 제거)")
                audio_loop = self.make_audio_loop(audio, tmp, flatten=audio_flatten)
            else:
                self.log("⑥ 오디오 없음 → 무음 영상으로 진행")

            self.log("⑦ 장시간 영상 합성 중...")
            # v9.7: scale은 이미 trim_unit 단계에서 적용됐으므로(성능 최적화) 여기서는
            # 다시 적용하지 않음 — unit이 이미 목표 해상도이므로 assemble()의 기본
            # 가정(scale=None → 1920x1080)이 비트레이트 상한 계산에도 정확히 맞는다.
            self.assemble(unit, audio_loop, target_sec, out_path, tmp, fade=fade)

            size_gb = os.path.getsize(out_path) / (1024 ** 3)
            self.log(f"\n🎉 완성! ({size_gb:.2f} GB)\n📁 {out_path}")
            return out_path
        except InterruptedError:
            self.log("\n⛔ 사용자에 의해 중단됨")
            if os.path.exists(out_path):
                try:
                    os.remove(out_path)
                    self.log("  미완성 출력 파일 삭제됨")
                except Exception:
                    pass
            return None
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# =====================================================================
# v11 신규: 🌙 잠자리 미스터리 스토리 내레이션
#   완성된 루프 영상 위에 AI 성우가 Claude가 창작한 잔잔한 미스터리 이야기를
#   읽어주는 트랙을 얹는다. (빗소리는 말할 때만 살짝 낮아지는 '더킹' 믹싱)
#   - 이야기: 이 PC에 로그인된 Claude Code(claude -p) 재사용 → API 키/추가 비용 없음
#   - 음성: Microsoft Edge 신경망 음성(edge-tts, 무료) — 최초 1회 자동 설치
#   - 결과: 영상이름_내레이션_성우.mp4 + 영상이름_story 폴더(대본·자막 SRT·음성)
# =====================================================================
import asyncio
import wave
import importlib
import concurrent.futures

# v11.3: 외국인 억양 문제로 다국어(Multilingual) 외국 음성은 모두 제거 — 전부 한국어 원어민 음성만 사용
# (화면 표시 이름, 성별, [무료 Edge] 음성 ID, 속도%, 피치Hz, 대체 음성, 대체 피치)
#  * 무료 Edge에는 한국어 원어민 음성이 3개(인준·현수·선희)뿐이라 ★표 성우는 무료 모드에서
#    가장 가까운 한국어 음성의 톤을 바꿔 대신 읽는다. Azure 공식 모드에서는 각자 진짜 목소리.
NARR_VOICES = [
    ("남1 · 인준 — 낮고 차분한 중저음 내레이터", "남", "ko-KR-InJoonNeural", -8, -3, None, 0),
    ("남2 · 현수 — 부드럽고 차분한 목소리 ★추천", "남", "ko-KR-HyunsuMultilingualNeural", -3, -5,
     "ko-KR-InJoonNeural", 3),
    ("남3 · 봉진 — 묵직하고 편안한 목소리 ★", "남", "ko-KR-InJoonNeural", -10, -9, None, 0),
    ("여1 · 선희 — 포근하고 다정한 이야기꾼", "여", "ko-KR-SunHiNeural", -8, -2, None, 0),
    ("여2 · 지민 — 맑고 조용한 목소리 ★", "여", "ko-KR-SunHiNeural", -8, 4, None, 0),
    ("여3 · 순복 — 할머니처럼 정겨운 이야기꾼 ★", "여", "ko-KR-SunHiNeural", -12, -8, None, 0),
]
# Azure 공식 모드: (음성 ID, 속도%, 피치Hz) — 모두 한국어 원어민 신경망 음성
NARR_AZURE = {
    NARR_VOICES[0][0]: ("ko-KR-InJoonNeural", -8, -2),
    NARR_VOICES[1][0]: ("ko-KR-HyunsuMultilingualNeural", -3, -5),   # 무료 현수 1c와 같은 목소리·설정
    NARR_VOICES[2][0]: ("ko-KR-BongJinNeural", -8, 0),
    NARR_VOICES[3][0]: ("ko-KR-SunHiNeural", -8, 0),
    NARR_VOICES[4][0]: ("ko-KR-JiMinNeural", -8, 0),
    NARR_VOICES[5][0]: ("ko-KR-SoonBokNeural", -10, 0),
}
# v11.7: 🧓 목소리 톤 — 녹음 후 음높이를 낮추고(속도는 유지) 고음을 부드럽게 깎아 잠들기 좋은 톤으로
# (음높이 배율, 추가 느리게 배율, 부드럽게 EQ 여부, 볼륨)
NARR_TONES = {
    # (음높이 배율, 느리게 배율, 부드럽게 처리 강도 0~2, 믹스 볼륨 배율, 문단 사이 쉼 초)
    "🤫 조용하고 차분하게 ★추천": (1.0, 1.0, 1, 0.75, 2.2),     # v11.9: 현수 1c 샘플 설정 (속도는 성우 설정으로)
    "🤫 더 조용히, 속삭이듯 (음높이 그대로)": (1.0, 0.90, 2, 0.6, 2.6),
    "🧓 굵고 깊은 목소리 (음높이 낮춤)": (0.89, 0.94, 1, 0.85, 2.0),
    "기본 (원래 목소리)": (1.0, 1.0, 0, 1.0, 1.6),
}


def narr_tone(tone_key):
    return NARR_TONES.get(tone_key, list(NARR_TONES.values())[0])


def narr_tone_filter(tone_key, sr=24000):
    """목소리 톤 후처리 ffmpeg 필터 (v11.8: 기본은 음높이를 건드리지 않고
    날카로운 고음·힘을 빼서 조용하고 차분하게 — 굵어지지 않게)"""
    f, slow, soft, _vol, _gap = narr_tone(tone_key)
    parts = [f"aresample={sr}"]
    if f != 1.0:
        parts += [f"asetrate={int(sr * f)}", f"aresample={sr}", f"atempo={1.0 / f:.4f}"]
    if slow != 1.0:
        parts.append(f"atempo={slow:.4f}")
    if soft >= 1:
        # 저음은 올리지 않음(굵어지지 않게) — 또렷하고 쏘는 대역(2~4kHz)·치찰음만 눌러서 힘을 뺀다
        parts += ["equalizer=f=2800:t=q:w=1.4:g=-4", "highshelf=f=5000:g=-5", "lowpass=f=9000",
                  "acompressor=threshold=-26dB:ratio=2.5:attack=15:release=250"]
    if soft >= 2:
        parts += ["equalizer=f=1200:t=q:w=1:g=-2", "highshelf=f=3500:g=-3"]
    return ",".join(parts) if len(parts) > 1 else None


TTS_CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".loopmaker_tts.json")
NARR_ENGINES = {"무료 (Edge 한국어 음성 3종)": "edge", "Azure 공식 (한국어 성우 6명 · 월 50만 자 무료)": "azure"}


def load_tts_config():
    try:
        with open(TTS_CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"engine": "edge", "azure_key": "", "azure_region": "koreacentral"}


def save_tts_config(cfg):
    with open(TTS_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


NARR_VOICE_MAP = {v[0]: v for v in NARR_VOICES}

NARR_SPEED = {
    "기본 (잠자리 속도)": 0,
    "더 느리게": -8,
    "아주 느리게": -15,
    "조금 빠르게": 8,
}
# 배경음(빗소리) 더킹: (sidechaincompress threshold, ratio)
NARR_DUCK = {
    "약하게 (빗소리 거의 그대로)": (0.03, 4.0),
    "보통 (권장)": (0.02, 6.0),
    "강하게 (목소리 또렷하게)": (0.008, 14.0),
}
NARR_LEN = [
    ("자동 (1시간 이하는 영상 길이만큼 · 5시간→2.5시간 · 10시간→3시간)", 0),
    ("1분", 60),
    ("3분", 180),
    ("10분", 600),
    ("30분", 1800),
    ("1시간 (2편)", 3600),
    ("2시간 (4편)", 7200),
    ("2시간 30분 (5편)", 9000),
    ("3시간 (6편)", 10800),
]
NARR_CHARS_PER_SEC = 6.4        # 한국어 낭독 실측치(공백 포함, v11.8 보정: 3분 테스트 실측 5.8자/초)
NARR_CHAPTER_CHARS = 1400       # 한 번의 Claude 호출로 쓰는 장(章) 분량
NARR_PARA_GAP = 1.6             # 문단 사이 쉼(초)
NARR_SAMPLE_LINE = ("비가 조용히 내리는 밤이에요. 오늘은 안개 낀 호숫가의 오래된 등대에 "
                    "매일 밤 혼자 불이 켜지는 이유에 대한 이야기를 들려드릴게요.")

NARR_FALLBACK_TITLE = "빗속의 등대지기"
NARR_FALLBACK_SUMMARY = "비 오는 밤마다 빈 등대에 켜지는 불빛, 그 비밀을 찾아간 서연의 이야기"
NARR_FALLBACK_STORY = """비가 조용히 내리는 밤이에요. 오늘은 안개 낀 호숫가의 작은 마을, 그리고 그 마을 끝에 서 있는 오래된 등대에 대한 이야기를 들려드릴게요.

그 등대에는 오래전부터 아무도 살지 않았어요. 문은 녹슨 자물쇠로 잠겨 있었고, 계단에는 먼지가 소복이 쌓여 있었지요. 그런데 이상하게도, 비가 오는 밤이면 꼭대기 창문에 작고 노란 불빛이 켜졌어요.

마을 도서관에서 일하는 서연은 그 불빛이 늘 궁금했어요. 어느 비 오는 저녁, 서연은 우산을 쓰고 호숫가 길을 천천히 걸어갔어요. 빗방울이 우산 위에서 톡, 톡, 부드러운 소리를 냈어요.

등대 앞에 도착하자, 잠겨 있던 문이 아주 조금 열려 있었어요. 안으로 들어서니 따뜻한 나무 냄새와 함께, 계단 위쪽에서 희미한 불빛이 흘러내리고 있었어요.

꼭대기 방에는 아무도 없었어요. 대신 창가의 작은 탁자 위에 등불 하나와 낡은 편지 한 장이 놓여 있었지요. 편지에는 이렇게 적혀 있었어요. 비 오는 밤, 길을 잃은 배가 없도록 누군가는 불을 켜 두어야 한단다.

서연은 편지를 조심스럽게 접어 주머니에 넣었어요. 그리고 창밖을 바라보았어요. 호수 위로 빗줄기가 은빛 실처럼 내려앉고, 먼 곳에서 작은 배 한 척이 불빛을 따라 천천히 돌아오고 있었어요.

그날 이후로 서연은 비가 오는 밤마다 등대에 올라 불을 켰어요. 누가 처음 그 불을 켰는지는 아무도 몰라요. 다만 빗소리가 들리는 밤이면, 그 작은 불빛은 오늘도 조용히 호수를 비추고 있답니다.

이제 눈을 감고, 창밖의 빗소리에 귀를 기울여 보세요. 편안한 밤 되세요."""

NARR_WRITER_PERSONA = """너는 '잠들기 전에 듣는 미스터리 이야기'를 전문으로 쓰는 세계 최고 수준의 작가다.
유튜브 수면 채널에서 빗소리와 함께 성우가 낭독할 대본을 쓴다.

[반드시 지킬 원칙]
1. 궁금증은 있지만 긴장하거나 무섭지 않은 '포근한 미스터리'. 공포, 폭력, 죽음·유혈 묘사, 비명, 갑작스러운 반전이나 놀래키는 장면은 절대 쓰지 않는다.
2. 빗소리, 촛불, 나무 냄새, 따뜻한 차처럼 오감을 부드럽게 채우는 묘사를 쓰고, 문장은 짧고 호흡은 느리게 한다.
3. 수수께끼는 따뜻하거나 신비로운 방식으로 풀리거나, 기분 좋은 여운으로 남긴다.
4. 실존 인물, 실제 사건, 기존 소설·영화·만화의 캐릭터나 줄거리는 쓰지 않는다. 완전한 창작이어야 한다.
5. 부드러운 해요체 낭독 문장으로 쓴다 (예: ~했어요, ~있었지요, ~답니다).
6. 음성 합성(TTS)용 대본이다: 괄호, 따옴표 남용, 특수기호, 이모지, 영어 약어를 쓰지 말고 숫자는 한글로 쓴다 (예: 세 시, 열두 개). 대사는 '~라고 말했어요'처럼 서술 속에 녹인다.
7. 문단은 세 문장에서 다섯 문장. 이야기 후반으로 갈수록 문장을 더 짧고 느리게 해서 듣는 사람이 자연스럽게 잠들게 한다.
8. 설명, 인사말, 메모, 제목 외의 다른 말은 출력하지 않는다. 지정된 표식 형식만 지킨다."""

# v11.4: 🔀 반전 미스터리 작가 — 비·영상 장면에 얽매이지 않는 자유 소재 + 반전 3단
NARR_TWIST_PERSONA = """너는 한 번 들으면 끝까지 멈출 수 없는 '반전 미스터리'를 쓰는 세계 최고 수준의 이야기꾼이다.
유튜브 수면 채널에서 빗소리 위에 성우가 낮고 차분하게 낭독할 대본을 쓴다.

[소재]
1. 비나 영상 속 장면에 얽매이지 않는다. 오래된 호텔의 비어 있는 객실, 매일 같은 시각에 도착하는 주인 없는 편지, 존재하지 않는 역에 서는 야간 열차, 사라진 초상화, 기억을 사고파는 골목 가게처럼 듣는 순간 궁금증이 생기는 소재를 매번 새롭게 고른다. 영상 장면은 분위기 참고용일 뿐이다.
2. 첫 두 문장 안에 '왜?', '어떻게?'가 떠오르는 훅을 던진다.

[반전 설계 — 가장 중요]
3. 반전은 정확히 세 번. 첫 번째 반전은 듣는 사람이 믿고 있던 전제를 뒤집는다. 두 번째 반전은 진실이라 여긴 첫 반전의 설명마저 다시 뒤집는다. 세 번째 반전은 결말 직전, 처음부터 조용히 깔아둔 작은 단서들로 모든 것을 한 번 더 뒤집어 '아, 그래서 그랬구나' 하는 깨달음을 준다.
4. 반전은 억지가 아니라 공정해야 한다. 각 반전의 복선을 앞부분에 자연스럽게 심어두어, 다시 들으면 단서가 보이게 한다. 초자연 현상으로 대충 설명하고 끝내지 않는다.

[수면 채널 원칙]
5. 공포, 잔혹, 유혈, 폭력, 비명, 갑자기 놀래키는 장면은 절대 쓰지 않는다. 반전은 큰 소리가 아니라 조용히 소름이 돋는 깨달음으로 전달한다.
6. 마지막 반전 뒤에는 짧고 따뜻한 여운을 남기고, 듣는 사람에게 편안히 잠들라는 조용한 인사로 끝낸다.
7. 부드러운 해요체 낭독 문장으로 쓴다 (예: ~했어요, ~였지요, ~답니다). 문장은 너무 길지 않게.
8. 실존 인물, 실제 사건, 기존 소설·영화·드라마의 캐릭터나 줄거리, 유명한 반전을 베끼지 않는다. 완전한 창작이어야 한다.
9. 음성 합성(TTS)용 대본이다: 괄호, 특수기호, 이모지, 영어 약어를 쓰지 말고 숫자는 한글로 쓴다 (예: 세 시, 열두 개). 대사는 서술 속에 녹인다.
10. 문단은 세 문장에서 다섯 문장. 설명, 메모, 제목 외의 다른 말은 출력하지 않는다. 지정된 표식 형식만 지킨다."""

# v11.19: 잠자리용 이야기를 앞쪽에 (첫 항목이 기본 선택값). 셜록 홈즈는 긴장감이 있어 뒤쪽으로.
NARR_STYLES = {
    "🌙 옛날 옛적 전래동화 (한국 설화 · 순한 톤 · 이어서 연재)": "lib:folk",
    "🧸 세계 명작 동화 (안데르센 · 그림 형제 · 이어서 연재)": "lib:world",
    "🌿 포근한 고전 소설 (버드나무에 부는 바람 · 빨강 머리 앤 · 연재)": "lib:cozyclassic",
    "🏯 한국 고전·근대 문학 (구운몽 · 메밀꽃 필 무렵 · 연재)": "lib:korean",
    "🏡 새로 지은 옛이야기 (할머니 이야기 · 창작)": "calm:oldtale",
    "🌲 숲과 호수의 밤 산책 (자연 묘사 · 창작)": "calm:forest",
    "🚂 밤 기차·바닷마을 여행 (잔잔한 여행 · 창작)": "calm:journey",
    "☕ 비 오는 날 작은 가게 이야기 (따뜻한 일상 · 창작)": "calm:shop",
    "🧘 수면 명상 (몸 이완 · 호흡 · 상상 여정)": "calm:meditation",
    "🕯️ 포근한 미스터리 (잔잔 · 영상 분위기)": "cozy",
    "🔀 반전 미스터리 (반전 3번 · 자유 소재)": "twist",
    "📚 명작 추리 연재 (셜록 홈즈부터 · 이어서 · ⚠ 긴장감 있음)": "classic",
}


def narr_persona(style):
    if is_lib_style(style):
        set_active_lib(style)
        return _lib()["persona"]
    k = calm_kind_of(style)
    if k:
        return k["persona"]
    return NARR_TWIST_PERSONA if style == "twist" else NARR_WRITER_PERSONA


NARR_FIRST_PROMPT = """{persona}

[이번 작업]
- 이야기의 배경/분위기: {scene}
- 전체 {chapters}장 중 첫 번째 장을 쓴다. 이 장의 분량은 공백 포함 약 {chars}자.
- {chapter_rule}
- 먼저 이야기 전체의 설계도(바이블)를 만든 뒤 첫 장을 쓴다. 바이블에는 {bible_items} (여섯 줄에서 열다섯 줄).
{frame_rule}
[출력 형식 — 아래 표식을 그대로 사용]
<<<TITLE>>>
이야기 제목 (한국어, 짧고 신비롭게)
<<<BIBLE>>>
바이블 내용
<<<SUMMARY>>>
유튜브 설명란용 이야기 소개 한 문장 (공백 포함 {sum_max}자 이내, 결말은 숨기고 궁금증을 자아내게)
<<<STORY>>>
첫 장 본문 (문단 사이는 빈 줄 하나)
<<<END>>>"""

NARR_NEXT_PROMPT = """{persona}

[이야기 바이블 — 설정을 절대 바꾸지 말 것]
{bible}

[바로 앞 내용의 마지막 부분]
{prev}

[이번 작업]
- 전체 {chapters}장 중 {idx}번째 장을 쓴다. 분량은 공백 포함 약 {chars}자.
- 앞 내용과 자연스럽게 이어지게 쓰고, 이미 나온 문장이나 묘사를 반복하지 않는다.
- {chapter_rule}

[출력 형식]
<<<STORY>>>
본문 (문단 사이는 빈 줄 하나)
<<<END>>>"""


NARR_TITLE_PROMPT = """{persona}

[이번 작업]
- 이야기의 배경/분위기: {scene}
{frame_rule}- 이 배경으로 쓸 수 있는 {title_kind}의 제목 후보 세 개를 만든다.
- 제목은 한국어로 짧고(열다섯 자 이내) {title_tone}, 셋의 분위기가 서로 다르게.

[출력 형식]
<<<TITLES>>>
제목1
제목2
제목3
<<<END>>>"""


# ==================== v11.11: 📚 세계 명작 낭독 (저작권 만료 작품을 새로 옮겨 쓰기) ====================
CLASSIC_LIST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "명작_목록.txt")
CLASSIC_STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "명작_진행상태.json")
CLASSIC_PART_CHARS = 1400       # 한 부분(약 4분 반)
CLASSIC_DEFAULT = """# 📚 LoopMaker 명작 연재 목록 — 위에서부터 차례대로, 영상이 바뀌어도 '이어서' 들려줘요
# 한 작품이 영상 하나에 다 안 끝나면 다음 영상에서 그 다음 부분부터 계속하고, 끝나면 아래 작품으로 넘어가요
# 형식: 작가 | 작품 | 메모(선택)   ·  맨 앞에 # 을 붙이면 건너뛰어요  ·  순서를 바꾸거나 작품을 추가해도 돼요
# ※ 저작권이 끝난 작품만 넣으세요. 기존 한국어 번역본 문장은 쓰지 않고 원작을 바탕으로 새로 옮겨 써요.
# ── 셜록 홈즈 (발표 순서) ──
코난 도일 | 주홍색 연구 | 셜록 홈즈 첫 장편 · 홈즈와 왓슨의 첫 만남
코난 도일 | 네 개의 서명 | 셜록 홈즈 장편
코난 도일 | 보헤미아 왕국의 스캔들 | 셜록 홈즈의 모험
코난 도일 | 빨간 머리 연맹 | 셜록 홈즈의 모험
코난 도일 | 신랑의 정체 | 셜록 홈즈의 모험 · 원제 A Case of Identity
코난 도일 | 보스콤 계곡의 비밀 | 셜록 홈즈의 모험
코난 도일 | 다섯 개의 오렌지 씨앗 | 셜록 홈즈의 모험
코난 도일 | 입술이 비뚤어진 사나이 | 셜록 홈즈의 모험
코난 도일 | 푸른 석류석 | 셜록 홈즈의 모험
코난 도일 | 얼룩 끈 | 셜록 홈즈의 모험
코난 도일 | 기술자의 엄지손가락 | 셜록 홈즈의 모험
코난 도일 | 독신 귀족 | 셜록 홈즈의 모험
코난 도일 | 녹주석 보관 | 셜록 홈즈의 모험 · 원제 The Beryl Coronet
코난 도일 | 너도밤나무 저택 | 셜록 홈즈의 모험
코난 도일 | 실버 블레이즈 | 셜록 홈즈의 회상록
코난 도일 | 노란 얼굴 | 셜록 홈즈의 회상록
코난 도일 | 주식 중개인의 서기 | 셜록 홈즈의 회상록
코난 도일 | 글로리아 스콧 호 | 셜록 홈즈의 회상록
코난 도일 | 머스그레이브 가의 의식 | 셜록 홈즈의 회상록
코난 도일 | 라이게이트의 지주 | 셜록 홈즈의 회상록
코난 도일 | 그리스어 통역관 | 셜록 홈즈의 회상록 · 형 마이크로프트 첫 등장
코난 도일 | 해군 조약문 | 셜록 홈즈의 회상록
코난 도일 | 바스커빌 가의 개 | 셜록 홈즈 장편
# ── 셜록 홈즈가 끝나면 ──
G. K. 체스터턴 | 푸른 십자가 | 브라운 신부 단편
모리스 르블랑 | 아르센 뤼팽 체포되다 | 괴도 뤼팽 첫 단편
오 헨리 | 크리스마스 선물 | 원제 The Gift of the Magi · 반전 결말
기 드 모파상 | 목걸이 | 반전 결말
오 헨리 | 20년 후 | 반전 결말
사키 | 열린 창 | 반전 결말
안톤 체호프 | 내기 | 반전 결말
에드거 앨런 포 | 도둑맞은 편지 | 뒤팽 탐정
오스카 와일드 | 캔터빌의 유령 | 유쾌한 유령 이야기
워싱턴 어빙 | 립 밴 윙클 |
로버트 루이스 스티븐슨 | 병 속의 악마 | 원제 The Bottle Imp
작자 미상 | 전우치전 | 한국 고전소설
작자 미상 | 박씨전 | 한국 고전소설
"""

NARR_CLASSIC_PERSONA = """너는 세계 명작을 잠자리 낭독용으로 새로 옮겨 쓰는 번역가이자 이야기꾼이다.
유튜브 수면 채널에서 빗소리 위에 성우가 낮고 차분하게 낭독할 대본을 쓴다.

[원칙]
1. 원작의 줄거리, 인물, 사건 순서, 반전, 결말을 충실히 따른다. 원작에 없는 사건이나 인물을 지어내지 않는다. 기억이 확실하지 않은 세부는 지어내지 말고 자연스럽게 생략한다.
2. 이미 나와 있는 한국어 번역본의 문장을 베끼지 않는다. 원작을 바탕으로 네가 새로 쓴 문장이어야 한다.
3. 부드러운 해요체 낭독 문장으로 쓴다 (예: ~했어요, ~였지요). 작품의 첫 장은 '오늘 들려드릴 이야기는 누구의 무슨 작품이에요' 하는 식으로 작가와 작품을 한두 문장 소개하며 시작한다.
4. 수면 채널이다: 잔인하거나 끔찍한 장면은 자세히 묘사하지 않고 한 문장으로 부드럽게 넘긴다. 대신 원작의 긴장감, 추리, 반전의 재미는 살린다.
5. 음성 합성용 대본이다: 괄호, 특수기호, 이모지, 영어 약어를 쓰지 말고 숫자는 한글로 쓴다. 외국 인명과 지명은 한글로 표기한다. 대사는 서술 속에 자연스럽게 녹인다.
6. 문단은 세 문장에서 다섯 문장. 지정된 표식 형식 외의 말은 출력하지 않는다."""

CLASSIC_FIRST_PROMPT = """{persona}

[이번 작업]
- 작품: {author}의 「{work}」 {memo}
- 먼저 원작 줄거리를 장면 순서대로 정리한 바이블(주요 인물, 장면 순서, 반전, 결말, 장별 분할 계획)을 만든다.
- 원작 분량에 맞춰 전체를 몇 장으로 나눌지 정한다: 1장에서 {max_ch}장 사이, 한 장은 공백 포함 약 {per}자. 짧은 작품을 억지로 늘리지 않는다.
- 그중 첫 번째 장을 쓴다.{one}

[출력 형식 — 아래 표식을 그대로 사용]
<<<TITLE>>>
{work}
<<<CHAPTERS>>>
숫자 하나
<<<BIBLE>>>
바이블 내용
<<<SUMMARY>>>
유튜브 설명란용 작품 소개 한 문장 (공백 포함 {sum_max}자 이내, 결말은 숨기고 궁금하게)
<<<STORY>>>
첫 장 본문 (문단 사이는 빈 줄 하나)
<<<END>>>"""


CLASSIC_PLAN_PROMPT = """{persona}

[이번 작업 — 연재 시작]
- 작품: {author}의 「{work}」 {memo}
- 이 작품을 처음부터 끝까지, 원작 줄거리를 빠짐없이 충실히 여러 부분으로 나눠 연재한다. 한 부분은 공백 포함 약 {per}자.
- 원작 분량에 맞게 전체 부분 수를 정한다: 단편은 보통 여섯에서 열 부분, 장편은 스무 부분에서 마흔 부분 (최대 {max_parts}). 줄거리를 줄이거나 늘리지 않는다.
- 바이블에는 주요 인물, 부분별 계획(각 부분에 들어갈 원작 장면을 한 줄씩, 번호를 붙여서), 반전, 결말을 적는다. 이 계획은 여러 날에 걸쳐 이어 쓸 때 기준이 된다.
- 그리고 첫 번째 부분을 쓴다. 작가와 작품을 한두 문장 소개하며 시작한다.

[출력 형식 — 아래 표식을 그대로 사용]
<<<TITLE>>>
{work}
<<<PARTS>>>
숫자 하나
<<<BIBLE>>>
바이블 내용
<<<SUMMARY>>>
유튜브 설명란용 작품 소개 한 문장 (공백 포함 {sum_max}자 이내, 결말은 숨기고 궁금하게)
<<<STORY>>>
첫 번째 부분 본문 (문단 사이는 빈 줄 하나)
<<<END>>>"""


# ==================== v11.19: 🌙 이야기 서재 + 잠자리 창작 스타일 ====================
# 구독자 피드백: "셜록 홈즈는 잠자기에는 긴장감이 있다 → 조용하고 포근한 이야기도 골라 듣고 싶다"
#  ① 이야기 서재(연재형): 목록 파일 + 진행상태 파일을 서재마다 따로 두고, 영상마다 이어서 들려줌 (명작 연재와 같은 방식)
#  ② 잠자리 창작(창작형): 매번 새로 지어내는 포근한 이야기 (영상 분위기/키워드 반영)

_LIB_DIR = os.path.dirname(os.path.abspath(__file__))

_SOFT_PERSONA_BASE = """너는 세계의 이야기를 잠자리 낭독용으로 새로 옮겨 쓰는 다정한 이야기꾼이다.
유튜브 수면 채널에서 빗소리 위에 성우가 낮고 느리게 낭독할 대본을 쓴다.

[원칙]
1. 원작의 줄거리, 인물, 사건 순서, 결말을 충실히 따른다. 원작에 없는 사건이나 인물을 지어내지 않는다. 기억이 확실하지 않은 세부는 지어내지 말고 자연스럽게 생략한다.
2. 이미 나와 있는 한국어 번역본이나 출판본의 문장을 베끼지 않는다. 원작을 바탕으로 네가 새로 쓴 문장이어야 한다.
3. 부드러운 해요체 낭독 문장으로 쓴다 (예: ~했어요, ~였지요, ~답니다). {opening}
4. 잠들기 위한 이야기다: 싸움, 죽음, 공포, 잔혹한 장면은 자세히 묘사하지 않고 한 문장으로 부드럽게 넘기거나 생략한다. 긴장감을 키우지 말고, 장면의 풍경, 소리, 냄새, 온기를 천천히 묘사한다.
5. 문장은 짧게, 호흡은 느리게 쓴다. 이야기가 진행될수록 문장을 더 짧고 잔잔하게 하고, 각 부분의 마지막 문단은 늘 고요한 장면으로 마무리한다.
6. 음성 합성용 대본이다: 괄호, 특수기호, 이모지, 영어 약어를 쓰지 말고 숫자는 한글로 쓴다. 외국 인명과 지명은 한글로 표기한다. 대사는 서술 속에 자연스럽게 녹인다.
7. 문단은 세 문장에서 다섯 문장. 지정된 표식 형식 외의 말은 출력하지 않는다."""

_OPEN_AUTHOR = "작품의 첫 장은 작가와 작품 이름을 한두 문장으로 소개하며 시작한다."
_OPEN_FOLK = ("작품의 첫 장은 '옛날 옛적에' 또는 '오늘 들려드릴 옛이야기는 이런 이야기예요'처럼 시작한다. "
              "작가가 '작자 미상'이면 작가 이름은 말하지 않고, 옛날부터 입에서 입으로 전해 내려온 이야기라고만 소개한다.")

# ---- 연재형 서재 목록 (저작권이 끝난 작품 / 작자 미상 설화만) ----
LIB_FOLK_DEFAULT = """# 🌙 옛날 옛적 전래동화 — 위에서부터 차례대로, 영상이 바뀌어도 '이어서' 들려줘요
# 형식: 작가 | 작품 | 메모(선택)   ·  맨 앞에 # 을 붙이면 건너뛰어요  ·  순서를 바꾸거나 작품을 추가해도 돼요
# ※ 무서운 장면은 순하게 다듬어 들려줘요. 줄거리는 전해 내려오는 이야기를 따르고 새로 문장을 써요.
작자 미상 | 흥부와 놀부 | 한국 전래동화 · 흥부전
작자 미상 | 선녀와 나무꾼 | 한국 전래동화
작자 미상 | 혹부리 영감 | 한국 전래동화
작자 미상 | 의좋은 형제 | 한국 전래동화
작자 미상 | 견우와 직녀 | 한국 설화 · 칠석 이야기
작자 미상 | 우렁각시 | 한국 전래동화
작자 미상 | 콩쥐팥쥐 | 한국 전래동화 · 무서운 장면은 순하게
작자 미상 | 금도끼 은도끼 | 한국 전래동화
작자 미상 | 호랑이와 곶감 | 한국 전래동화
작자 미상 | 은혜 갚은 까치 | 한국 전래동화
작자 미상 | 토끼전 | 별주부전 · 용왕과 토끼의 이야기
작자 미상 | 심청전 | 한국 고전 · 효녀 심청
작자 미상 | 바보 온달과 평강공주 | 삼국사기 설화
작자 미상 | 연오랑과 세오녀 | 삼국유사 설화
작자 미상 | 서동과 선화공주 | 삼국유사 설화
"""

LIB_WORLD_DEFAULT = """# 🧸 세계 명작 동화 — 위에서부터 차례대로, 영상이 바뀌어도 '이어서' 들려줘요
# 형식: 작가 | 작품 | 메모(선택)   ·  맨 앞에 # 을 붙이면 건너뛰어요  ·  순서를 바꾸거나 작품을 추가해도 돼요
# ※ 저작권이 끝난 작품만 넣으세요. 기존 한국어 번역본 문장은 쓰지 않고 원작을 바탕으로 새로 옮겨 써요.
한스 크리스티안 안데르센 | 미운 오리 새끼 | 안데르센 동화
한스 크리스티안 안데르센 | 엄지 공주 | 안데르센 동화
한스 크리스티안 안데르센 | 나이팅게일 | 안데르센 동화 · 황제와 꾀꼬리
한스 크리스티안 안데르센 | 벌거벗은 임금님 | 안데르센 동화
한스 크리스티안 안데르센 | 눈의 여왕 | 안데르센 동화 · 게르다와 카이
그림 형제 | 브레멘 음악대 | 그림 동화
그림 형제 | 요정과 구두장이 | 그림 동화
그림 형제 | 황금 거위 | 그림 동화
샤를 페로 | 장화 신은 고양이 | 페로 동화
샤를 페로 | 잠자는 숲속의 공주 | 페로 동화
샤를 페로 | 신데렐라 | 페로 동화
오스카 와일드 | 이기적인 거인 | 와일드 동화
오스카 와일드 | 행복한 왕자 | 와일드 동화
카를로 콜로디 | 피노키오의 모험 | 이탈리아 동화
루이스 캐럴 | 이상한 나라의 앨리스 | 영국 환상 동화
L. 프랭크 바움 | 오즈의 마법사 | 미국 환상 동화
제임스 매튜 배리 | 피터 팬 | 영국 환상 동화
"""

LIB_COZY_DEFAULT = """# 🌿 포근한 고전 소설 — 위에서부터 차례대로, 영상이 바뀌어도 '이어서' 들려줘요 (긴 이야기를 여러 날에 걸쳐)
# 형식: 작가 | 작품 | 메모(선택)   ·  맨 앞에 # 을 붙이면 건너뛰어요  ·  순서를 바꾸거나 작품을 추가해도 돼요
# ※ 저작권이 끝난 작품만 넣으세요. 기존 한국어 번역본 문장은 쓰지 않고 원작을 바탕으로 새로 옮겨 써요.
케네스 그레이엄 | 버드나무에 부는 바람 | 강가의 두더지와 물쥐 · 아주 포근한 이야기
비어트릭스 포터 | 피터 래빗 이야기 | 작은 토끼의 모험 · 짧은 이야기
프랜시스 호지슨 버넷 | 비밀의 화원 | 시골 저택의 잠긴 정원
루시 모드 몽고메리 | 빨강 머리 앤 | 초록 지붕 집의 앤
요한나 슈피리 | 하이디 | 알프스 산의 소녀
프랜시스 호지슨 버넷 | 소공녀 | 세라 크루의 이야기
루이자 메이 올콧 | 작은 아씨들 | 네 자매의 이야기
"""

LIB_KOREAN_DEFAULT = """# 🏯 한국 고전 · 근대 문학 — 위에서부터 차례대로, 영상이 바뀌어도 '이어서' 들려줘요
# 형식: 작가 | 작품 | 메모(선택)   ·  맨 앞에 # 을 붙이면 건너뛰어요  ·  순서를 바꾸거나 작품을 추가해도 돼요
# ※ 저작권이 끝난 작품만 넣으세요 (작가 사후 70년 경과). 기존 출판본 문장은 쓰지 않고 원작을 바탕으로 새로 옮겨 써요.
이효석 | 메밀꽃 필 무렵 | 달빛 아래 봉평 장터 가는 길 · 아주 고요한 이야기
김만중 | 구운몽 | 꿈속의 긴 인생 이야기
김유정 | 동백꽃 | 산골 마을의 봄
김유정 | 봄봄 | 유쾌한 시골 이야기
방정환 | 만년 샤쓰 | 어린이 동화
박지원 | 허생전 | 연암 박지원의 한문 소설
"""

# 서재 등록부: 키 → 목록 파일, 진행상태 파일, 기본 목록, 작가 페르소나
STORY_LIBS = {
    "classic": dict(label="명작 연재", list=os.path.join(_LIB_DIR, "명작_목록.txt"),
                    state=os.path.join(_LIB_DIR, "명작_진행상태.json"),
                    default=None, persona=None),        # default/persona 는 기존 CLASSIC_DEFAULT / NARR_CLASSIC_PERSONA
    "folk": dict(label="옛날 옛적 전래동화", list=os.path.join(_LIB_DIR, "전래동화_목록.txt"),
                 state=os.path.join(_LIB_DIR, "전래동화_진행상태.json"),
                 default=LIB_FOLK_DEFAULT, persona=_SOFT_PERSONA_BASE.format(opening=_OPEN_FOLK)),
    "world": dict(label="세계 명작 동화", list=os.path.join(_LIB_DIR, "세계동화_목록.txt"),
                  state=os.path.join(_LIB_DIR, "세계동화_진행상태.json"),
                  default=LIB_WORLD_DEFAULT, persona=_SOFT_PERSONA_BASE.format(opening=_OPEN_AUTHOR)),
    "cozyclassic": dict(label="포근한 고전 소설", list=os.path.join(_LIB_DIR, "포근한고전_목록.txt"),
                        state=os.path.join(_LIB_DIR, "포근한고전_진행상태.json"),
                        default=LIB_COZY_DEFAULT, persona=_SOFT_PERSONA_BASE.format(opening=_OPEN_AUTHOR)),
    "korean": dict(label="한국 고전·근대 문학", list=os.path.join(_LIB_DIR, "한국문학_목록.txt"),
                   state=os.path.join(_LIB_DIR, "한국문학_진행상태.json"),
                   default=LIB_KOREAN_DEFAULT, persona=_SOFT_PERSONA_BASE.format(opening=_OPEN_AUTHOR)),
}
_ACTIVE_LIB = "classic"


def is_lib_style(style):
    """연재형(서재) 스타일인가? 'classic'(셜록 홈즈부터)과 'lib:키' 가 해당"""
    return style == "classic" or (isinstance(style, str) and style.startswith("lib:"))


def set_active_lib(style):
    """스타일 값 → 현재 서재 선택 (목록·진행상태 파일이 이 서재의 것으로 바뀜)"""
    global _ACTIVE_LIB
    key = style[4:] if isinstance(style, str) and style.startswith("lib:") else "classic"
    _ACTIVE_LIB = key if key in STORY_LIBS else "classic"


def _lib():
    lib = dict(STORY_LIBS[_ACTIVE_LIB])
    if lib["default"] is None:                      # 기존 명작 연재(셜록 홈즈)는 원래 설정 그대로
        lib["default"] = CLASSIC_DEFAULT
        lib["persona"] = NARR_CLASSIC_PERSONA
    return lib


# ---- 창작형: 잠자리 이야기 5종 ----
_CALM_COMMON = """[잠자리 낭독 공통 원칙]
1. 긴장, 공포, 폭력, 죽음, 갑작스러운 사건, 놀라게 하는 반전은 쓰지 않는다. 갈등이 있어도 아주 작고 금방 풀리는 것만 쓴다.
2. 빗소리, 촛불, 나무 냄새, 따뜻한 차, 이불의 감촉처럼 오감을 부드럽게 채우는 묘사를 풍부하게 쓰고, 문장은 짧게, 호흡은 느리게 한다.
3. 실존 인물, 실제 사건, 기존 소설, 영화, 만화의 캐릭터나 줄거리는 쓰지 않는다. 완전한 창작이어야 한다.
4. 부드러운 해요체 낭독 문장으로 쓴다 (예: ~했어요, ~있었지요, ~답니다).
5. 음성 합성(TTS)용 대본이다: 괄호, 따옴표 남용, 특수기호, 이모지, 영어 약어를 쓰지 말고 숫자는 한글로 쓴다 (예: 세 시, 열두 개). 대사는 서술 속에 녹인다.
6. 문단은 세 문장에서 다섯 문장. 이야기가 진행될수록 문장을 더 짧고 느리게, 장면을 더 고요하게 해서 듣는 사람이 자연스럽게 잠들게 한다.
7. 설명, 인사말, 메모, 제목 외의 다른 말은 출력하지 않는다. 지정된 표식 형식만 지킨다."""

NARR_BIBLE_DEFAULT = ("주인공 이름과 성격, 장소, 핵심 수수께끼, 장별 흐름, 결말 방향을 정리하고, 반전이 있는 이야기라면 "
                      "반전 하나하나의 내용과 그 복선을 어디에 심을지도 적는다")


def _calm_kind(intro, material, bible_items, title_kind, single, first, mid, last, label):
    return dict(persona=f"{intro}\n\n{material}\n\n{_CALM_COMMON}", bible_items=bible_items,
                title_kind=title_kind, title_tone="포근하고 조용하게", single=single, first=first,
                mid=mid, last=last, label=label)


CALM_KINDS = {
    "oldtale": _calm_kind(
        "너는 할머니가 화롯가에서 들려주는 듯한 따뜻한 '새 옛이야기'를 짓는 이야기꾼이다.\n"
        "유튜브 수면 채널에서 빗소리 위에 성우가 낮고 느리게 낭독할 대본을 쓴다.",
        "[소재와 분위기]\n"
        "- 한국 옛이야기의 결을 살린 완전한 창작 이야기다. 첫 문장은 '옛날 옛적에'로 시작한다.\n"
        "- 산골 마을, 초가집, 감나무, 아궁이 불, 장터, 개울, 달빛 같은 배경을 쓴다. 착한 호랑이, 심심한 도깨비, 길 잃은 산신령의 심부름꾼처럼 "
        "무섭지 않고 정겨운 존재가 나온다.\n"
        "- 마음씨 고운 사람이 작은 친절을 베풀고 따뜻한 보답을 받는 이야기로, 결말은 늘 포근하다.",
        "주인공 이름과 성격, 마을과 계절, 작은 사건 하나, 장별 흐름, 따뜻한 결말과 교훈 한 줄을 정리한다",
        "잠자리 옛이야기", "이 한 장 안에서 '옛날 옛적에' 도입, 작은 사건, 따뜻한 해결, 잠들기 좋은 마무리 인사까지 모두 담는다.",
        "도입부다. '옛날 옛적에'로 시작해 마을과 주인공을 천천히 소개하고 작은 사건 하나를 꺼낸다. 서두르지 않는다.",
        "중간 장이다. 사건에 한 걸음 다가가되 서두르지 말고 계절과 풍경 묘사를 충분히 넣는다.",
        "마지막 장이다. 사건을 따뜻하게 마무리하고, 마지막 문단은 듣는 사람에게 편안히 잠들라는 조용한 인사로 끝낸다.",
        "새로 지은 옛이야기"),
    "forest": _calm_kind(
        "너는 밤의 숲과 호수를 천천히 걸으며 풍경을 들려주는 '자연 산책 이야기'를 쓰는 작가다.\n"
        "유튜브 수면 채널에서 빗소리 위에 성우가 낮고 느리게 낭독할 대본을 쓴다.",
        "[소재와 분위기]\n"
        "- 큰 사건 없이 조용한 산책길을 따라가는 이야기다. 숲길, 이끼, 안개 낀 호수, 반딧불이, 오래된 나무, 개울, 별빛, 작은 오두막을 쓴다.\n"
        "- 걷는 이는 한 사람(혹은 작은 동물 한 마리)이고, 만나는 것은 모두 다정하고 조용하다. 발소리, 바람, 물소리, 나뭇잎 스치는 소리를 번갈아 묘사한다.\n"
        "- 마지막에는 따뜻한 불이 켜진 오두막이나 포근한 잠자리에 도착한다.",
        "산책하는 이의 이름과 마음, 길의 순서(숲길, 호수, 언덕, 오두막), 장면마다의 소리와 빛, 도착하는 곳을 정리한다",
        "밤 숲과 호수 산책 이야기", "이 한 장 안에서 출발, 숲길, 호수, 따뜻한 도착, 잠들기 좋은 마무리 인사까지 모두 담는다.",
        "도입부다. 해 질 녘 출발하는 이와 첫 숲길의 소리와 빛을 천천히 그린다. 사건은 만들지 않는다.",
        "중간 장이다. 길을 따라 풍경이 바뀌는 모습을 소리, 냄새, 온기 중심으로 느리게 그린다. 사건은 만들지 않는다.",
        "마지막 장이다. 따뜻한 불빛이 있는 곳에 도착해 몸을 누이는 모습을 그리고, 마지막 문단은 편안히 잠들라는 조용한 인사로 끝낸다.",
        "숲과 호수 산책"),
    "journey": _calm_kind(
        "너는 느리고 조용한 여행을 그리는 '밤 여행 이야기' 작가다.\n"
        "유튜브 수면 채널에서 빗소리 위에 성우가 낮고 느리게 낭독할 대본을 쓴다.",
        "[소재와 분위기]\n"
        "- 밤 기차, 새벽 항구의 작은 배, 바닷가 마을의 버스, 산골 간이역처럼 천천히 흘러가는 여행이다. 창밖 풍경, 덜컹이는 리듬, 따뜻한 차, 담요가 중심이다.\n"
        "- 여행자는 한 사람이고, 길에서 만나는 이들은 모두 조용하고 친절하다. 일정에 쫓기거나 길을 잃어 불안해지는 장면은 쓰지 않는다.\n"
        "- 목적지는 작고 포근한 마을의 따뜻한 숙소다.",
        "여행자의 이름과 사연 한 줄, 탈것과 길의 순서, 창밖 풍경, 만나는 사람 한두 명, 도착하는 마을을 정리한다",
        "밤 여행 이야기", "이 한 장 안에서 출발, 창밖 풍경, 작은 만남, 따뜻한 도착, 잠들기 좋은 마무리 인사까지 모두 담는다.",
        "도입부다. 조용히 출발하는 여행자와 탈것의 소리와 온기를 소개한다. 사건은 만들지 않는다.",
        "중간 장이다. 창밖으로 지나가는 풍경과 작은 정거장, 친절한 사람과의 짧은 대화를 느리게 그린다.",
        "마지막 장이다. 작은 마을에 도착해 따뜻한 방에 눕는 모습을 그리고, 마지막 문단은 편안히 잠들라는 조용한 인사로 끝낸다.",
        "밤 여행"),
    "shop": _calm_kind(
        "너는 비 오는 날 작은 가게에서 일어나는 따뜻한 일상 이야기를 쓰는 작가다.\n"
        "유튜브 수면 채널에서 빗소리 위에 성우가 낮고 느리게 낭독할 대본을 쓴다.",
        "[소재와 분위기]\n"
        "- 찻집, 헌책방, 우체국, 빵집, 등대 옆 작은 가게처럼 아늑한 공간이 배경이다. 비 오는 날이라 손님이 드문드문 오고, 가게 주인은 서두르지 않는다.\n"
        "- 사건은 작고 다정하다. 오래 기다린 편지가 도착하고, 단골손님이 좋아하는 차를 기억해 내는 정도의 일이다.\n"
        "- 따뜻한 차, 갓 구운 빵, 종이 냄새, 처마 끝 빗방울 소리를 풍부하게 묘사한다.",
        "가게 주인의 이름과 성격, 가게의 모습, 오늘 찾아올 손님 한두 명, 작고 다정한 사건 하나, 마무리 풍경을 정리한다",
        "비 오는 날 작은 가게 이야기", "이 한 장 안에서 가게 소개, 손님과의 작은 사건, 따뜻한 해결, 잠들기 좋은 마무리 인사까지 모두 담는다.",
        "도입부다. 비 오는 아침 가게 문을 여는 주인과 가게의 냄새와 소리를 천천히 소개한다.",
        "중간 장이다. 조용히 찾아오는 손님과 작은 대화, 따뜻한 차 한 잔의 장면을 느리게 그린다.",
        "마지막 장이다. 작은 일이 다정하게 마무리되고 가게의 불이 하나씩 꺼지는 모습을 그린 뒤, 마지막 문단은 편안히 잠들라는 조용한 인사로 끝낸다.",
        "작은 가게 이야기"),
    "meditation": _calm_kind(
        "너는 잠들기 전 듣는 '수면 명상' 안내자다.\n"
        "유튜브 수면 채널에서 빗소리 위에 성우가 낮고 느리게 낭독할 안내 대본을 쓴다.",
        "[구성과 말투]\n"
        "- 이야기가 아니라 듣는 사람에게 직접 말하는 안내문이다. '당신'이라는 말을 가끔만 쓰고, 부드러운 권유형으로 말한다 (예: ~해 보세요, ~느껴져요).\n"
        "- 순서: 편안한 자세와 숨 고르기 → 발끝에서 머리까지 몸의 부위별 이완 → 상상 속의 고요한 장소(빗소리 들리는 오두막, 달빛 호수, 포근한 구름 등)로의 여정 → 깊은 쉼과 잠으로 들어가기.\n"
        "- 호흡 안내는 길이를 정해 느리게 한다 (예: 넷을 세며 들이쉬고, 여섯을 세며 내쉬어요). 같은 안내 문구를 조금씩 바꿔 부드럽게 반복한다.\n"
        "- 의학적 효과나 치료를 약속하지 않는다. 무리해서 숨을 참거나 몸을 억지로 움직이라는 말은 하지 않는다.",
        "안내의 순서(호흡, 몸의 부위별 이완, 상상 속 장소, 깊은 쉼), 상상 장소의 풍경, 반복해서 쓸 안내 문구를 정리한다",
        "수면 명상", "이 한 장 안에서 숨 고르기, 몸 이완, 고요한 장소로의 여정, 깊은 쉼과 잠들기 좋은 마무리 인사까지 모두 담는다.",
        "도입부다. 편안한 자세와 느린 호흡 안내로 시작해, 발끝부터 천천히 힘을 푸는 안내를 시작한다.",
        "중간 장이다. 몸의 이완을 이어가거나, 고요한 상상 속 장소로 천천히 안내한다. 같은 문구를 조금씩 바꿔 부드럽게 반복한다.",
        "마지막 장이다. 가장 깊은 쉼으로 안내하고, 점점 말수를 줄이며, 마지막 문단은 편안히 잠들라는 조용한 인사로 끝낸다.",
        "수면 명상"),
}


def calm_kind_of(style):
    return CALM_KINDS.get(style[5:]) if isinstance(style, str) and style.startswith("calm:") else None


def calm_chapter_rule(kind, i, n):
    if n == 1:
        return kind["single"]
    if i == n:
        return kind["last"]
    return kind["first"] if i == 1 else kind["mid"]


def style_label(style):
    k = calm_kind_of(style)
    if k:
        return k["label"]
    if is_lib_style(style):
        return STORY_LIBS.get(style[4:] if style.startswith("lib:") else "classic", {}).get("label", "연재")
    return {"twist": "🔀 반전 미스터리"}.get(style, "포근한 미스터리")



def _classic_items():
    lib = _lib()
    if not os.path.exists(lib["list"]):
        with open(lib["list"], "w", encoding="utf-8-sig") as f:
            f.write(lib["default"])
    with open(lib["list"], encoding="utf-8-sig") as f:
        lines = [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]
    items = []
    for ln in lines:
        p = [x.strip() for x in ln.split("|")]
        if len(p) >= 2 and p[1]:
            items.append((p[0], p[1], p[2] if len(p) > 2 else "", ln))
    return items


def load_classic_state():
    try:
        with open(_lib()["state"], encoding="utf-8") as f:
            st = json.load(f)
    except Exception:
        st = {}
    st.setdefault("done", [])
    st.setdefault("current", None)
    st.setdefault("history", [])
    return st


def save_classic_state(st):
    path = _lib()["state"]
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def classic_queue():
    """아직 시작하지 않은 작품들 (진행 중인 작품 제외) → (목록, 전체 수)"""
    items = _classic_items()
    st = load_classic_state()
    cur = (st.get("current") or {}).get("line")
    rest = [it for it in items if it[3] not in st["done"] and it[3] != cur]
    return rest, len(items)


_KOR_NUM = {"일": 1, "이": 2, "삼": 3, "사": 4, "오": 5, "육": 6, "칠": 7, "팔": 8, "구": 9}


def _kor_to_int(w):
    """'이십칠' → 27 (백 단위 미만)"""
    if w.isdigit():
        return int(w)
    n, cur = 0, 0
    for ch in w:
        if ch == "십":
            n += (cur or 1) * 10; cur = 0
        elif ch in _KOR_NUM:
            cur = _KOR_NUM[ch]
        else:
            return 0
    return n + cur


def classic_plan_count(bible):
    """바이블의 '부분별 계획'에서 가장 큰 번호 (숫자 또는 한글 수사)"""
    best = 0
    for ln in (bible or "").splitlines():
        m = re.match(r"^\s*([0-9]{1,2}|[일이삼사오육칠팔구십]{1,4})\s*[.)．]", ln)
        if m:
            best = max(best, _kor_to_int(m.group(1)))
    return best


def classic_status_text():
    st = load_classic_state()
    cur = st.get("current")
    q, n = classic_queue()
    if cur:
        s = (f"진행 중: {cur['author']}의 「{cur['title']}」 {cur['next_part'] - 1}/{cur['total_parts']}부분까지 들려줬어요 "
             f"→ 다음 영상은 {cur['next_part']}부분부터")
    else:
        s = "진행 중인 작품 없음"
    return s + f" · 완료 {len(st['done'])}편 / 전체 {n}편 · 다음 작품: " + (", ".join(f"「{w[1]}」" for w in q[:2]) or "없음")


def run_claude_text(prompt, timeout=300, allow_read=False, retries=3, log=None):
    """v11.13: 일시적인 실패(시간 초과·네트워크·잠깐의 사용량 제한)에 대비해 최대 3번 재시도"""
    last = None
    for attempt in range(retries):
        try:
            return _run_claude_once(prompt, timeout=timeout, allow_read=allow_read)
        except FileNotFoundError:
            raise
        except Exception as ex:
            last = ex
            if attempt < retries - 1:
                wait = 30 * (attempt + 1)
                if log:
                    log(f"     ↻ Claude 호출 실패 → {wait}초 뒤 다시 시도 ({attempt + 1}/{retries - 1}): {str(ex)[:150]}")
                time.sleep(wait)
    raise last


def _run_claude_once(prompt, timeout=300, allow_read=False):
    """이 PC에 로그인된 Claude Code CLI(claude -p)를 호출해 텍스트 응답을 받는다.
    (call_claude_scene_analysis와 같은 방식: 윈도우 claude.cmd 경로 탐색 + stdin 전달)"""
    exe = shutil.which("claude")
    if not exe:
        raise FileNotFoundError("claude 명령을 찾을 수 없습니다")
    cmd = [exe, "-p"]
    if allow_read:
        cmd += ["--allowedTools", "Read"]
    r = subprocess.run(cmd, input=prompt, capture_output=True, timeout=timeout,
                       creationflags=CREATE_NO_WINDOW, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        # v11.19: 로그인 만료·사용량 한도 같은 안내는 stdout 으로 나오는 경우가 많아 함께 보여준다
        detail = ((r.stderr or "").strip() + " " + (r.stdout or "").strip()).strip()[-400:]
        raise RuntimeError(f"claude 실행 실패 (코드 {r.returncode}): " + (detail or "메시지 없음 — 명령 프롬프트에서 claude 를 직접 실행해 확인하세요"))
    return (r.stdout or "").strip()


def _narr_block(text, tag):
    m = re.search(r"<<<" + tag + r">>>\s*(.*?)\s*(?=<<<[A-Z]+>>>|$)", text, re.DOTALL)
    return m.group(1).strip() if m else ""


def narr_clean_text(text):
    """TTS가 이상하게 읽을 만한 기호를 정리"""
    text = re.sub(r"[\*#_`~>\[\]{}<>|]", "", text)
    text = re.sub(r"[\U0001F300-\U0001FAFF☀-➿]", "", text)
    text = text.replace("“", "").replace("”", "").replace('"', "")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def narr_split_paragraphs(text):
    paras = [narr_clean_text(p) for p in re.split(r"\n\s*\n", text)]
    out = []
    for p in paras:
        p = " ".join(p.split())
        if not p:
            continue
        sents = [s.strip() for s in re.split(r"(?<=[.!?…。])\s+", p) if s.strip()]
        merged = []
        for s in sents:
            if merged and len(merged[-1]) < 12:
                merged[-1] = merged[-1] + " " + s
            else:
                merged.append(s)
        if merged:
            out.append(merged)
    return out


def _srt_time(t):
    t = max(0.0, t)
    h = int(t // 3600); m = int(t % 3600 // 60); s = int(t % 60); ms = int(round((t - int(t)) * 1000))
    if ms >= 1000:
        s += 1; ms -= 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


class StoryNarrator:
    SR = 24000

    def __init__(self, log_fn, stop_flag):
        self.log = log_fn
        self.stop_flag = stop_flag
        self.edge_tts = None
        self.proc = None
        self.cfg = load_tts_config()
        self.tone_key = list(NARR_TONES)[0]
        self.tone_af = narr_tone_filter(self.tone_key)

    def _check_stop(self):
        if self.stop_flag.is_set():
            raise InterruptedError("중단됨")

    # ---------- 준비 ----------
    def ensure_tts(self):
        if self.is_azure():
            return None
        if self.edge_tts:
            return self.edge_tts
        try:
            import edge_tts
            self.edge_tts = edge_tts
            return edge_tts
        except ImportError:
            pass
        self.log("  📦 음성 합성 모듈(edge-tts)을 처음 한 번만 설치합니다... (30초 정도)")
        for extra in ([], ["--user"]):
            r = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "edge-tts"] + extra,
                               capture_output=True, creationflags=CREATE_NO_WINDOW,
                               encoding="utf-8", errors="replace")
            if r.returncode == 0:
                break
        importlib.invalidate_caches()
        try:
            import edge_tts
        except ImportError:
            raise RuntimeError("edge-tts 설치 실패 — 명령 프롬프트에서 직접 설치해주세요:\n"
                               "  py -m pip install edge-tts")
        self.log("  ✅ edge-tts 설치 완료")
        self.edge_tts = edge_tts
        return edge_tts

    def _ff(self, cmd):
        self._check_stop()
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     creationflags=CREATE_NO_WINDOW)
        out, err = self.proc.communicate()
        rc = self.proc.returncode
        self.proc = None
        self._check_stop()
        return rc, out, err

    def kill(self):
        p = self.proc
        if p and p.poll() is None:
            try:
                p.kill()
            except Exception:
                pass

    def probe_duration(self, path):
        r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=nw=1:nk=1", path],
                           capture_output=True, creationflags=CREATE_NO_WINDOW)
        try:
            return float((r.stdout or b"").decode().strip())
        except ValueError:
            return 0.0

    def has_audio(self, path):
        r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "a",
                            "-show_entries", "stream=index", "-of", "csv=p=0", path],
                           capture_output=True, creationflags=CREATE_NO_WINDOW)
        return bool((r.stdout or b"").strip())

    # ---------- 음성 ----------
    def is_azure(self):
        return self.cfg.get("engine") == "azure" and bool(self.cfg.get("azure_key"))

    def voice_spec(self, label, speed_key):
        v = NARR_VOICE_MAP.get(label, NARR_VOICES[0])
        adj = NARR_SPEED.get(speed_key, 0)
        if self.is_azure():
            az = NARR_AZURE.get(v[0], ("ko-KR-SunHiNeural", -8, 0))
            return {"label": v[0], "engine": "azure", "voice": az[0],
                    "rate": max(-50, min(50, az[1] + adj)), "pitch": az[2],
                    "fb_voice": "ko-KR-InJoonNeural" if v[1] == "남" else "ko-KR-SunHiNeural", "fb_pitch": 0}
        return {"label": v[0], "engine": "edge", "voice": v[2], "rate": max(-50, min(50, v[3] + adj)),
                "pitch": v[4], "fb_voice": v[5], "fb_pitch": v[6]}

    def _azure_once(self, sents, voice, rate, pitch, out_mp3):
        import urllib.request, urllib.error, html as _html
        region = (self.cfg.get("azure_region") or "koreacentral").strip()
        brk = "<break time='650ms'/>"
        body = brk.join(_html.escape(s) for s in sents)
        ssml = ("<speak version='1.0' xml:lang='ko-KR' xmlns='http://www.w3.org/2001/10/synthesis'>"
                f"<voice name='{voice}'><prosody rate='{rate:+d}%' pitch='{pitch:+d}Hz'>{body}</prosody>"
                "</voice></speak>")
        req = urllib.request.Request(
            f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
            data=ssml.encode("utf-8"), method="POST",
            headers={"Ocp-Apim-Subscription-Key": self.cfg.get("azure_key", "").strip(),
                     "Content-Type": "application/ssml+xml",
                     "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3",
                     "User-Agent": "LoopMaker"})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                data = r.read()
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise PermissionError("Azure 키 또는 지역(region)이 올바르지 않습니다")
            if e.code == 429:
                raise TimeoutError("Azure 무료 요청 한도(분당 횟수) — 잠시 쉬었다 다시 시도")
            raise RuntimeError(f"Azure 오류 {e.code}: {e.read()[:200]!r}")
        with open(out_mp3, "wb") as f:
            f.write(data)

    def _tts_once(self, sents, voice, rate, pitch, out_mp3, engine="edge"):
        """문단(문장 목록) 하나를 한 번에 합성 — 문장끼리 억양이 자연스럽게 이어진다"""
        if isinstance(sents, str):
            sents = [sents]
        last = None
        tries = 6 if engine == "azure" else 3
        for attempt in range(tries):
            try:
                if os.path.exists(out_mp3):
                    os.remove(out_mp3)
                if engine == "azure":
                    self._azure_once(sents, voice, rate, pitch, out_mp3)
                else:
                    edge_tts = self.ensure_tts()

                    async def go():
                        c = edge_tts.Communicate(" ".join(sents), voice,
                                                 rate=f"{rate:+d}%", pitch=f"{pitch:+d}Hz")
                        await c.save(out_mp3)
                    asyncio.run(go())
                if os.path.exists(out_mp3) and os.path.getsize(out_mp3) > 600:
                    return
                last = RuntimeError("음성 데이터가 비어 있음")
            except PermissionError:
                raise
            except TimeoutError as ex:
                last = ex
                time.sleep(8 + 4 * attempt)
                continue
            except Exception as ex:
                last = ex
            time.sleep(1.2 * (attempt + 1))
        raise RuntimeError(f"음성 합성 실패 ({voice}): {last}")

    def resolve_voice(self, spec, tmp):
        """선택한 음성이 실제로 동작하는지 짧게 확인하고, 안 되면 대체 음성으로 전환"""
        test = os.path.join(tmp, "_voice_test.mp3")
        try:
            self._tts_once(["안녕하세요."], spec["voice"], spec["rate"], spec["pitch"], test, spec["engine"])
            return spec
        except PermissionError:
            raise
        except Exception as ex:
            if not spec["fb_voice"] or spec["fb_voice"] == spec["voice"]:
                raise
            self.log(f"  ⚠️ {spec['voice']} 음성을 쓸 수 없어 {spec['fb_voice']}(으)로 전환합니다 ({ex})")
            spec = dict(spec, voice=spec["fb_voice"], pitch=spec["fb_pitch"], fb_voice=None)
            self._tts_once(["안녕하세요."], spec["voice"], spec["rate"], spec["pitch"], test, spec["engine"])
            return spec

    def preview(self, label, speed_key, out_mp3, text=NARR_SAMPLE_LINE, tone=None):
        spec = self.voice_spec(label, speed_key)
        tmp = tempfile.mkdtemp(prefix="narr_prev_")
        if tone:
            self.tone_key = tone
            self.tone_af = narr_tone_filter(tone)
        try:
            spec = self.resolve_voice(spec, tmp)
            sents = [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
            raw = os.path.join(tmp, "raw.mp3")
            self._tts_once(sents, spec["voice"], spec["rate"], spec["pitch"], raw, spec["engine"])
            if self.tone_af:
                rc, _, err = self._ff([FFMPEG, "-v", "error", "-y", "-i", raw, "-af", self.tone_af,
                                       "-c:a", "libmp3lame", "-q:a", "2", out_mp3])
                if rc != 0:
                    raise RuntimeError("목소리 톤 처리 실패: " + err.decode("utf-8", "ignore")[-200:])
            else:
                shutil.copyfile(raw, out_mp3)
            return spec
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def _mp3_to_pcm(self, mp3, wav):
        af = ["-af", self.tone_af] if self.tone_af else []
        rc, _, err = self._ff([FFMPEG, "-v", "error", "-y", "-i", mp3, *af, "-ac", "1",
                               "-ar", str(self.SR), "-sample_fmt", "s16", wav])
        if rc != 0:
            raise RuntimeError("음성 변환 실패: " + err.decode("utf-8", "ignore")[-300:])
        with wave.open(wav, "rb") as w:
            data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        nz = np.nonzero(np.abs(data) > 300)[0]
        if len(nz):
            a = max(0, nz[0] - int(0.03 * self.SR)); b = min(len(data), nz[-1] + int(0.15 * self.SR))
            data = data[a:b]
        # v11.9: 조각 앞뒤를 아주 짧게(30ms) 페이드 — 이어붙인 곳에서 '뚝' 소리가 나지 않게
        n = min(len(data) // 4, int(0.03 * self.SR))
        if n > 1:
            data = data.astype(np.float32)
            ramp = np.linspace(0.0, 1.0, n, dtype=np.float32)
            data[:n] *= ramp
            data[-n:] *= ramp[::-1]
            data = data.astype(np.int16)
        return data

    def synthesize(self, paragraphs, spec, tmp):
        """문단 단위로 합성(자연스러운 억양) → 문단 사이 쉼을 넣어 이어붙임 → (wav, 자막 구간)
        자막은 문단 안에서 문장 길이 비율로 시간을 나눠 문장 단위로 만든다."""
        total = len(paragraphs)
        eng = "Azure" if spec["engine"] == "azure" else "무료 Edge"
        self.log(f"  🎙 음성 녹음 중... 문단 {total}개 ({eng} · {spec['voice']}, 속도 {spec['rate']:+d}%)")
        results = {}
        done = [0]

        def work(pi):
            self._check_stop()
            mp3 = os.path.join(tmp, f"p_{pi:04d}.mp3")
            self._tts_once(paragraphs[pi], spec["voice"], spec["rate"], spec["pitch"], mp3, spec["engine"])
            return pi, mp3

        workers = 1 if spec["engine"] == "azure" else 4   # Azure 무료는 분당 요청 수 제한이 있어 순차 처리
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            for pi, mp3 in ex.map(work, range(total)):
                results[pi] = mp3
                done[0] += 1
                if done[0] % 5 == 0 or done[0] == total:
                    self.log(f"     ... {done[0]}/{total} 문단 완료")

        out = os.path.join(tmp, "narration.wav")
        wout = wave.open(out, "wb")
        wout.setnchannels(1); wout.setsampwidth(2); wout.setframerate(self.SR)
        segs, t = [], 0.0
        self.para_starts = []
        pgap = np.zeros(int(narr_tone(self.tone_key)[4] * self.SR), dtype=np.int16)
        epgap = np.zeros(int(5.0 * self.SR), dtype=np.int16)      # 편과 편 사이 긴 쉼
        ep_breaks = getattr(self, "ep_breaks", set())
        for pi, sents in enumerate(paragraphs):
            self._check_stop()
            pcm = self._mp3_to_pcm(results[pi], os.path.join(tmp, "_one.wav"))
            d = len(pcm) / self.SR
            self.para_starts.append(t)
            weights = [len(s) + 6 for s in sents]
            wsum = float(sum(weights)); a = t
            for s, w in zip(sents, weights):
                b = a + d * w / wsum
                segs.append((a, b, s)); a = b
            gap = epgap if (pi + 1) in ep_breaks else pgap
            wout.writeframes(pcm.tobytes()); t += d
            wout.writeframes(gap.tobytes()); t += len(gap) / self.SR
            try:
                os.remove(results[pi])      # 장편은 조각 파일이 많아서 바로바로 정리
            except OSError:
                pass
        wout.close()
        return out, segs, t

    # ---------- 이야기 ----------
    def _grab_frame(self, video, tmp):
        dur = self.probe_duration(video)
        fp = os.path.join(tmp, "scene.png")
        subprocess.run([FFMPEG, "-v", "error", "-ss", f"{max(0.0, dur * 0.4):.2f}", "-i", video,
                        "-frames:v", "1", "-y", fp], capture_output=True, creationflags=CREATE_NO_WINDOW)
        return fp if os.path.exists(fp) else None

    def suggest_titles(self, video, hint, tmp, style="twist"):
        """루프 제작 전에 이야기 제목 후보 3개를 미리 받아온다"""
        if is_lib_style(style):
            set_active_lib(style)
            cur = load_classic_state().get("current")
            q, _n = classic_queue()
            names = ([f"{cur['title']} (이어서)"] if cur else []) + [w[1] for w in q[:3]]
            return names[:3] or ["(목록의 작품을 모두 들려줬어요)"]
        if style == "twist":
            frame = None
            scene = hint or "자유 소재 (비·영상 장면과 무관해도 됨 — 듣자마자 궁금해지는 반전 미스터리)"
        else:
            frame = None if hint else self._grab_frame(video, tmp)
            scene = hint or "첨부 이미지 속 장면 (직접 보고 분위기를 파악할 것)"
        frame_rule = (f"- 먼저 Read 도구로 이 이미지를 열어 보고 장면의 날씨·장소·빛을 파악하라: {frame}\n"
                      if frame else "")
        ck = calm_kind_of(style)
        out = run_claude_text(NARR_TITLE_PROMPT.format(persona=narr_persona(style), scene=scene,
                                                       frame_rule=frame_rule,
                                                       title_kind=ck["title_kind"] if ck else "잠자리 미스터리 이야기",
                                                       title_tone=ck["title_tone"] if ck else "신비롭게"),
                              timeout=180, allow_read=bool(frame))
        block = _narr_block(out, "TITLES").replace("<<<END>>>", "")
        titles = []
        for ln in block.splitlines():
            t = re.sub(r"^\s*((\d+[.)]|[-*·•]|제목\s*\d*\s*[:：])\s*)+", "", ln).strip().strip("「」\"'")
            if t and t not in titles:
                titles.append(t)
        if not titles:
            raise RuntimeError("Claude 응답에서 제목을 찾지 못했습니다:\n" + out[:200])
        return titles[:3]

    def write_story(self, video, hint, target_sec, tmp, fixed_title="", style="twist",
                    final_greeting=True, avoid=None, ep_label=""):
        target_chars = max(250, int(target_sec * NARR_CHARS_PER_SEC * narr_tone(self.tone_key)[1]))
        chapters = max(1, math.ceil(target_chars / NARR_CHAPTER_CHARS))
        per = int(target_chars / chapters)
        persona = narr_persona(style)
        calm = calm_kind_of(style)
        if style == "twist":
            frame = None      # 반전 미스터리는 영상 장면에 얽매이지 않는 자유 소재
            scene = (f"{hint} (이 키워드를 출발점으로 삼되 자유롭게 확장)" if hint else
                     "자유 소재 — 비나 영상 장면과 무관해도 된다. 매번 새롭고 궁금증을 부르는 설정을 고른다")
        else:
            frame = None if hint else self._grab_frame(video, tmp)
            scene = hint or "첨부 이미지 속 장면 (직접 보고 분위기를 파악할 것)"
        frame_rule = (f"- 이야기를 쓰기 전에 Read 도구로 이 이미지를 먼저 열어 보고, 그 장면의 날씨·장소·빛을 이야기 배경으로 삼아라: {frame}\n"
                      if frame else "")
        fixed_title = (fixed_title or "").strip().strip("「」")
        if avoid:
            frame_rule += ("- 오늘 밤 앞서 들려준 이야기들과 소재·장소·반전이 절대 겹치지 않게 완전히 다른 이야기를 쓴다: "
                           + ", ".join(f"「{a}」" for a in avoid) + "\n")
        if fixed_title:
            frame_rule += (f"- 이야기 제목은 반드시 「{fixed_title}」이다. TITLE에는 이 제목을 그대로 쓰고, "
                           f"제목이 약속하는 수수께끼와 분위기에 딱 맞는 이야기를 쓴다.\n")

        def twist_rule(i):
            where = {j: min(chapters, max(1, math.ceil(j * chapters / 3))) for j in (1, 2, 3)}
            mine = [j for j in (1, 2, 3) if where[j] == i]
            parts = []
            if i == 1:
                parts.append("첫 두 문장에 강한 궁금증 훅을 던지고, 세 반전의 복선을 이 장 곳곳에 자연스럽게 심는다")
            if mine:
                parts.append("와 ".join({1: "첫 번째 반전", 2: "두 번째 반전", 3: "세 번째 반전"}[j] for j in mine)
                             + "을 이 장에서 조용히 터뜨린다 (바이블의 반전 설계대로)")
            else:
                parts.append("다음 반전을 향해 긴장감을 조용히 쌓고, 새로운 단서를 하나 더 흘린다")
            if i == chapters:
                parts.append("마지막 장이다. 세 번째 반전 뒤 짧은 여운을 남기고, 편안히 잠들라는 조용한 인사로 끝낸다")
            if chapters == 1:
                parts = ["분량이 짧으니 훅, 첫 번째 반전, 두 번째 반전, 세 번째 반전, 여운과 잠 인사까지 이 한 장에 압축해서 모두 담는다. 복선은 앞부분에 짧게 심는다"]
            return ". ".join(parts) + "."

        def rule(i):
            r = rule0(i)
            if not final_greeting:
                for a_, b_ in (("편안히 잠들라는 조용한 인사로 끝낸다", "조용한 여운으로 끝낸다 (잠 인사는 하지 않는다 — 곧 다음 이야기가 이어진다)"),
                               ("듣는 사람에게 편안히 잠들라는 조용한 인사로 끝낸다", "잔잔한 여운으로 끝낸다 (잠 인사는 하지 않는다)"),
                               ("여운과 잠 인사까지", "여운까지"),
                               ("잠들기 좋은 마무리 인사까지", "잔잔한 여운까지")):
                    r = r.replace(a_, b_)
            return r

        def rule0(i):
            if calm:
                return calm_chapter_rule(calm, i, chapters)
            if style == "twist":
                return twist_rule(i)
            if chapters == 1:
                return "이 한 장 안에서 도입, 수수께끼, 부드러운 해결, 잠들기 좋은 마무리 인사까지 모두 담는다."
            if i == chapters:
                return "마지막 장이다. 수수께끼를 따뜻하게 마무리하고, 마지막 문단은 듣는 사람에게 편안히 잠들라는 조용한 인사로 끝낸다."
            if i == 1:
                return "도입부다. 장소와 인물을 천천히 소개하고 작은 수수께끼 하나를 던진다. 아직 풀지 않는다."
            return "중간 장이다. 수수께끼에 한 걸음 다가가되 서두르지 말고, 잔잔한 장면 묘사를 충분히 넣는다."

        self.log(f"  🕯️ {ep_label}{style_label(style)} 작가 에이전트가 이야기를 쓰는 중... "
                 f"(약 {target_chars:,}자, {chapters}장)")
        prompt = NARR_FIRST_PROMPT.format(persona=persona, scene=scene, chapters=chapters,
                                          chars=per, chapter_rule=rule(1), frame_rule=frame_rule,
                                          sum_max=STORY_SUMMARY_MAX,
                                          bible_items=calm["bible_items"] if calm else NARR_BIBLE_DEFAULT)
        out = run_claude_text(prompt, timeout=300, allow_read=bool(frame))
        title = _narr_block(out, "TITLE").splitlines()[0].strip() if _narr_block(out, "TITLE") else "잠들기 전 미스터리"
        if fixed_title:
            title = fixed_title
        bible = _narr_block(out, "BIBLE")
        self.summary = fit_summary(_narr_block(out, "SUMMARY").replace("\n", " "))
        story = _narr_block(out, "STORY").replace("<<<END>>>", "").strip()
        if len(story) < 80:
            raise RuntimeError("Claude 응답에서 이야기 본문을 찾지 못했습니다:\n" + out[:300])
        parts = [story]
        self.log(f"     1/{chapters}장 완료 — 「{title}」 ({len(story):,}자)")
        for i in range(2, chapters + 1):
            self._check_stop()
            prompt = NARR_NEXT_PROMPT.format(persona=persona, bible=bible or title,
                                             prev=parts[-1][-700:], chapters=chapters, idx=i,
                                             chars=per, chapter_rule=rule(i))
            o = run_claude_text(prompt, timeout=300)
            s = _narr_block(o, "STORY").replace("<<<END>>>", "").strip() or o.strip()
            parts.append(s)
            self.log(f"     {i}/{chapters}장 완료 ({len(s):,}자)")
        return title, bible, "\n\n".join(parts)

    def write_classics(self, target_sec):
        """v11.12 📚 명작 연재: 진행 상태를 이어받아 목표 길이만큼 '다음 부분'들을 쓴다.
        한 작품이 끝나면 목록의 다음 작품을 시작. 상태는 영상이 성공적으로 완성된 뒤에만 저장
        (self.classic_state_pending) → 실패해도 이야기가 건너뛰어지지 않는다."""
        import copy
        st = copy.deepcopy(load_classic_state())
        lib = _lib()
        target_chars = int(target_sec * NARR_CHARS_PER_SEC * narr_tone(self.tone_key)[1])
        self.log(f"  📚 {lib['label']}: {classic_status_text()}\n     이번 영상 목표 약 {target_chars:,}자 "
                 f"(약 {math.ceil(target_chars / CLASSIC_PART_CHARS)}부분 · Claude를 그만큼 호출해요)")
        segs = []          # (line, title, part_idx, total_parts, text, started_here)
        total = 0
        first_resume = True
        while total < target_chars * 0.9:
            self._check_stop()
            cur = st.get("current")
            try:
                if not cur:
                    items = _classic_items()
                    rest = [it for it in items if it[3] not in st["done"]]
                    if not rest:
                        self.log(f"  📚 목록의 작품을 모두 들려줬어요! '{os.path.basename(lib['list'])}'에 새 작품을 추가해주세요")
                        break
                    author, title, memo, line = rest[0]
                    self.log(f"  📖 새 작품 연재 시작: {author}의 「{title}」 — 줄거리 설계 + 1부분 쓰는 중...")
                    out = run_claude_text(log=self.log, prompt=CLASSIC_PLAN_PROMPT.format(
                        persona=lib["persona"], author=author, work=title,
                        memo=f"({memo})" if memo else "", per=CLASSIC_PART_CHARS, max_parts=60,
                        sum_max=STORY_SUMMARY_MAX), timeout=400)
                    try:
                        parts_n = max(1, min(60, int(re.findall(r"\d+", _narr_block(out, "PARTS"))[0])))
                    except Exception:
                        parts_n = 8
                    # ★ v11.13 버그 수정: Claude가 PARTS 숫자와 실제 부분별 계획 개수를 다르게 적는 경우
                    #   (예: 숫자 8, 계획 28줄) 작품이 중간에 '완결' 처리되던 문제 → 계획 줄 수를 우선
                    plan_n = classic_plan_count(_narr_block(out, "BIBLE"))
                    if plan_n > parts_n:
                        parts_n = min(60, plan_n)
                    text = _narr_block(out, "STORY").replace("<<<END>>>", "").strip()
                    if len(text) < 80:
                        raise RuntimeError("Claude 응답에서 대본을 찾지 못했습니다:\n" + out[:300])
                    cur = {"line": line, "author": author, "title": title, "memo": memo,
                           "bible": _narr_block(out, "BIBLE"), "total_parts": parts_n, "next_part": 2,
                           "summary": fit_summary(_narr_block(out, "SUMMARY").replace("\n", " ")),
                           "tail": text[-700:], "videos": 0}
                    st["current"] = cur
                    # ★ v11.14: 한 영상 안에서 완결되는 작품도 요약을 잃지 않도록 시작할 때 바로 기록
                    st["history"] = [h for h in st.get("history", []) if h.get("line") != line] + \
                                    [{"line": line, "summary": cur["summary"]}]
                    segs.append((line, title, 1, parts_n, text, True))
                    self.log(f"     「{title}」 전체 {parts_n}부분으로 연재 · 1/{parts_n} 완료 ({len(text):,}자)")
                else:
                    i, n = cur["next_part"], cur["total_parts"]
                    rule = "바이블의 부분별 계획에서 이 번호에 해당하는 원작 장면을 앞 내용에 이어서 쓴다."
                    if first_resume and not segs:
                        rule += (" 이번 영상은 지난번에 이어지는 부분이다. 맨 앞에 '지난 이야기에서는' 하고 "
                                 "앞 내용을 두세 문장으로 부드럽게 정리한 뒤 이어서 들려준다.")
                    if i >= n:
                        rule += " 이 작품의 마지막 부분이다. 원작의 결말까지 충실히 쓰고 짧고 조용한 여운으로 끝낸다. 잠 인사는 하지 않는다."
                    out = run_claude_text(log=self.log, prompt=NARR_NEXT_PROMPT.format(
                        persona=lib["persona"],
                        bible=f"작품: {cur['author']}의 「{cur['title']}」 (전체 {n}부분)\n{cur['bible']}",
                        prev=cur.get("tail", ""), chapters=n, idx=i, chars=CLASSIC_PART_CHARS,
                        chapter_rule=rule), timeout=300)
                    text = _narr_block(out, "STORY").replace("<<<END>>>", "").strip() or out.strip()
                    segs.append((cur["line"], cur["title"], i, n, text, False))
                    cur["next_part"] = i + 1
                    cur["tail"] = text[-700:]
                    self.log(f"     「{cur['title']}」 {i}/{n}부분 완료 ({len(text):,}자)")
                first_resume = False
                total += len(segs[-1][4])
                if cur["next_part"] > cur["total_parts"]:
                    st["done"].append(cur["line"])
                    st["current"] = None
                    self.log(f"  ✅ 「{cur['title']}」 연재 완결!")
            except InterruptedError:
                raise
            except Exception as ex:
                if not segs:
                    raise
                self.log(f"  ⚠️ 이어 쓰는 중 멈췄어요 ({ex}) → 여기까지 쓴 {len(segs)}부분만 녹음하고, 다음 영상은 그 뒤부터 이어가요")
                break
        if not segs:
            raise RuntimeError(f"쓸 작품이 없어요 ({os.path.basename(lib['list'])} 확인)")
        # 작품별로 묶어서 편(EP) 표시 — 제목 카드·타임라인·유튜브 제목에 쓰임
        groups = []
        for line, title, idx, n, text, started in segs:
            if groups and groups[-1]["line"] == line:
                g = groups[-1]; g["texts"].append(text); g["last"] = idx
            else:
                groups.append({"line": line, "title": title, "first": idx, "last": idx, "n": n, "texts": [text]})
        labels, parts_out = [], []
        vids = st.setdefault("video_count", {})
        for k, g in enumerate(groups):
            whole = g["first"] == 1 and g["last"] >= g["n"]
            vids[g["line"]] = vids.get(g["line"], 0) + 1
            label = g["title"] if whole else f"{g['title']} {vids[g['line']]}부"
            labels.append(label)
            lead = "" if k == 0 else "이제 이어서 다음 이야기를 들려드릴게요.\n\n"
            parts_out.append(f"[[EP:{label}]]\n\n{lead}" + "\n\n".join(g["texts"]))
        last = groups[-1]
        if last["last"] < last["n"]:
            parts_out.append(f"오늘 밤 「{last['title']}」 이야기는 여기까지예요. 다음 이야기는 다음 시간에 이어서 들려드릴게요. "
                             "빗소리를 들으며 편안히 잠드세요.")
        else:
            parts_out.append("오늘 밤 이야기는 여기까지예요. 빗소리를 들으며 편안히 잠드세요.")
        # 요약: 첫 작품의 소개문
        first_line = groups[0]["line"]
        summ = ""
        c = st.get("current")
        if c and c["line"] == first_line:
            summ = c.get("summary", "")
        else:
            summ = next((h.get("summary", "") for h in st.get("history", []) if h.get("line") == first_line), "")
        if st.get("current"):
            st["history"] = [h for h in st["history"] if h.get("line") != st["current"]["line"]] + \
                            [{"line": st["current"]["line"], "summary": st["current"].get("summary", "")}]
        self.summary = summ
        st["history"] = st.get("history", [])[-50:]
        self.classic_state_pending = st
        self.log(f"  ✅ 이번 영상 대본 완성 (약 {total:,}자): " + ", ".join(f"「{l}」" for l in labels))
        return labels[0], "\n\n".join(f"■ {g['title']}" for g in groups), "\n\n".join(parts_out), labels

    def write_long_story(self, video, hint, target_sec, tmp, fixed_title="", style="twist", on_progress=None):
        """v11.8: 40분이 넘으면 한 이야기를 억지로 늘리지 않고, 편당 30~40분짜리
        완결 이야기(각자 반전 3번) 여러 편을 이어서 들려준다. → (대표 제목, 바이블 모음, 본문, 편 목록)"""
        if is_lib_style(style):
            set_active_lib(style)
            return self.write_classics(target_sec)      # 서재 연재 (제목은 작품명 — 제목 칸 입력은 무시)
        EP_SEC = 35 * 60
        if target_sec <= 40 * 60:
            title, bible, text = self.write_story(video, hint, target_sec, tmp, fixed_title=fixed_title, style=style)
            return title, bible, text, [title]
        n = max(2, math.ceil(target_sec / EP_SEC))
        per = target_sec / n
        self.log(f"  📚 장편 모드: {target_sec/3600:.1f}시간 분량 → {n}편 × 약 {per/60:.0f}분" + (" (각 편마다 반전 3번)" if style == "twist" else "") + "\n"
                 f"     (Claude가 약 {math.ceil(per * NARR_CHARS_PER_SEC / NARR_CHAPTER_CHARS) * n}번 나눠서 써요 — 시간이 꽤 걸려요)")
        titles, bibles, texts = [], [], []
        first_summary = ""
        for k in range(1, n + 1):
            self._check_stop()
            try:
                t_, b_, x_ = self.write_story(video, hint, per, tmp, fixed_title=fixed_title if k == 1 else "",
                                              style=style, final_greeting=(k == n), avoid=titles,
                                              ep_label=f"[{k}/{n}편] ")
            except InterruptedError:
                raise
            except Exception as ex:
                if not titles:
                    raise
                # 중간에 Claude 사용량 한도 등으로 멈추면, 이미 완성된 편까지만 사용 (처음부터 날리지 않음)
                self.log(f"  ⚠️ {k}편 창작 중 멈췄어요 ({ex})\n     → 완성된 {len(titles)}편까지만 녹음합니다")
                texts[-1] = texts[-1] + "\n\n오늘 밤 이야기는 여기까지예요. 빗소리를 들으며 편안히 잠드세요."
                break
            if k == 1:
                first_summary = self.summary
            titles.append(t_); bibles.append(f"■ {k}편 「{t_}」\n{b_}"); texts.append(x_)
            if on_progress:
                on_progress(k, n, t_)
        self.summary = first_summary
        parts = []
        ordinal = ["첫", "두", "세", "네", "다섯", "여섯", "일곱", "여덟", "아홉", "열"]
        for k, (t_, x_) in enumerate(zip(titles, texts)):
            if k == 0:
                parts.append(f"[[EP:{t_}]]\n\n{x_}")
            else:
                o = ordinal[k] if k < len(ordinal) else f"{k + 1}"
                parts.append(f"[[EP:{t_}]]\n\n이제 {o} 번째 이야기를 들려드릴게요. 제목은 {t_}이에요.\n\n{x_}")
        return titles[0], "\n\n".join(bibles), "\n\n".join(parts), titles

    # ---------- 믹싱 ----------
    def mix(self, video, narr_wav, narr_len, start_sec, duck_key, vdur, out_path, vin=None):
        """v11.6: 입력 0 = 영상(원본 또는 제목카드 앞부분+나머지를 이어붙인 concat 목록),
        입력 1 = 원본 영상의 빗소리, 입력 2 = 내레이션. 결과 파일을 한 번에 새로 써서
        재생기 호환성을 확보한다 (예전: 믹싱 후 제자리 수정 → 일부 재생기에서 재생 안 됨)."""
        vin = vin or ["-i", video]
        thr, ratio = NARR_DUCK.get(duck_key, NARR_DUCK["보통 (권장)"])
        ms = int(start_sec * 1000)
        voice = (f"[2:a]highpass=f=70,lowpass=f=11000,"
                 f"acompressor=threshold=-22dB:ratio=3:attack=10:release=200,"
                 f"loudnorm=I=-19:TP=-2:LRA=9,aresample=48000,"
                 f"aformat=sample_fmts=fltp:channel_layouts=stereo,"
                 f"aecho=0.85:0.6:40:0.08,volume={1.4 * narr_tone(self.tone_key)[3]:.2f},adelay={ms}|{ms}")
        avail = vdur - 1.0
        if start_sec + narr_len > avail:
            self.log(f"  ⚠️ 이야기가 영상보다 길어서 끝부분을 부드럽게 줄였어요 (영상 {vdur:.0f}초 / 이야기 {narr_len:.0f}초)")
            voice += f",atrim=0:{avail:.2f},afade=t=out:st={max(0.0, avail - 4):.2f}:d=4"
        # ★ v11.6 버그 수정: 내레이션이 끝난 뒤에도 빗소리가 끝까지 이어지도록 무음으로 채운다
        #   (sidechaincompress는 짧은 입력이 끝나면 같이 멈춰서, 이야기가 끝나는 순간
        #    영상 소리 전체가 끊기던 문제)
        voice += ",apad"
        if self.has_audio(video):
            fc = (f"{voice}[vv];[vv]asplit=2[sc][vm];"
                  f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[bg];"
                  f"[bg][sc]sidechaincompress=threshold={thr}:ratio={ratio}:attack=150:release=1500[bgd];"
                  f"[bgd][vm]amix=inputs=2:duration=first:dropout_transition=0,volume=2,"
                  f"alimiter=limit=0.95[aout]")
        else:
            self.log("  ℹ️ 영상에 소리가 없어 내레이션만 넣습니다")
            fc = f"{voice}[aout]"
        cmd = [FFMPEG, "-v", "error", "-y", *vin, "-i", video, "-i", narr_wav,
               "-filter_complex", fc, "-map", "0:v:0", "-map", "[aout]",
               "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{vdur:.3f}", out_path]
        self.log("  🎚 빗소리와 내레이션 믹싱 중... (영상은 재인코딩 없이 그대로 복사)")
        rc, _, err = self._ff(cmd)
        if rc != 0:
            raise RuntimeError("믹싱 실패: " + err.decode("utf-8", "ignore")[-500:])

    # ---------- 전체 실행 ----------
    def run(self, video, voice_label, speed_key, duck_key, len_sec, start_sec, hint, story_file,
            story_title="", on_title=None, style="twist", title_sec=5.0, tone=None, ext_audio=""):
        t0 = time.time()
        ext_audio = (ext_audio or "").strip()
        if ext_audio and not os.path.exists(ext_audio):
            raise RuntimeError(f"외부 음성 파일을 찾을 수 없습니다: {ext_audio}")
        vdur = self.probe_duration(video)
        if vdur <= 0:
            raise RuntimeError("영상 길이를 읽을 수 없습니다")
        base = os.path.splitext(video)[0]
        story_dir = base + "_story"
        os.makedirs(story_dir, exist_ok=True)
        tmp = tempfile.mkdtemp(prefix="narr_")
        self.summary = ""
        self.classic_state_pending = None
        # v11.13: 진행 로그를 story 폴더에도 저장 (문제가 생겼을 때 원인 확인용)
        _orig_log = self.log
        _logf = os.path.join(story_dir, "작업기록.txt")

        def _log2(m, _o=_orig_log, _f=_logf):
            _o(m)
            try:
                with open(_f, "a", encoding="utf-8") as fh:
                    fh.write(time.strftime("[%H:%M:%S] ") + str(m) + "\n")
            except OSError:
                pass
        self.log = _log2
        if tone:
            self.tone_key = tone
            self.tone_af = narr_tone_filter(tone)
            self.log(f"  🤫 목소리 톤: {tone}")
        try:
            if ext_audio:
                # v11.10: Vrew 등에서 만든 음성 파일을 그대로 사용 — AI 녹음(TTS)은 건너뜀
                self.log(f"  🎙 외부 음성 파일 사용: {os.path.basename(ext_audio)} (AI 녹음은 건너뜁니다)")
                spec = {"label": "외부음성 — " + os.path.splitext(os.path.basename(ext_audio))[0][:20],
                        "voice": "external", "engine": "external", "rate": 0, "pitch": 0}
            else:
                self.ensure_tts()
                spec = self.resolve_voice(self.voice_spec(voice_label, speed_key), tmp)
            if len_sec > 0:
                target = len_sec
            elif vdur <= 3600:
                target = vdur - start_sec - 20          # 1시간 이하: 영상 길이만큼
            else:
                target = min(3 * 3600.0, vdur * 0.5)    # 5시간 → 2.5시간, 10시간 → 3시간
            target = max(30.0, min(target, vdur - start_sec - 5))

            # 1) 이야기 준비
            if story_file and os.path.exists(story_file):
                with open(story_file, encoding="utf-8-sig") as f:
                    raw = f.read()
                lines = raw.strip().splitlines()
                title = lines[0].replace("제목:", "").strip() if lines and lines[0].startswith("제목:") else "직접 입력한 이야기"
                text = "\n".join(lines[1:]) if lines and lines[0].startswith("제목:") else raw
                self.log(f"  📄 저장된 이야기 파일 사용: {os.path.basename(story_file)}")
                # 같은 폴더의 story_info.json에서 요약을 이어받고, 없으면 첫 문장으로 대신
                try:
                    with open(os.path.join(os.path.dirname(story_file), "story_info.json"),
                              encoding="utf-8") as fh:
                        self.summary = json.load(fh).get("summary", "")
                except Exception:
                    first = re.split(r"(?<=[.!?…])\s+", " ".join(text.split()))[0] if text.strip() else ""
                    self.summary = fit_summary(first)
            elif ext_audio:
                title = story_title or os.path.splitext(os.path.basename(ext_audio))[0]
                text = ""
                self.log("  ℹ️ 이야기 파일이 없어서 제목만 사용해요 (요약·자막을 넣으려면 '이야기 파일'에 대본을 지정하세요)")
            else:
                try:
                    if story_title:
                        self.log(f"  📌 정해둔 제목으로 씁니다: 「{story_title}」")
                    title, bible, text, _eps = self.write_long_story(video, hint, target, tmp,
                                                                     fixed_title=story_title, style=style)
                    if bible:
                        with open(os.path.join(story_dir, "이야기_설정(바이블).txt"), "w", encoding="utf-8") as f:
                            f.write(bible)
                except (FileNotFoundError, subprocess.TimeoutExpired, RuntimeError) as ex:
                    self.log(f"  ⚠️ Claude 이야기 창작 실패 → 내장 샘플 이야기로 목소리 테스트를 진행합니다\n     ({ex})")
                    title, text = NARR_FALLBACK_TITLE, NARR_FALLBACK_STORY
                    self.summary = NARR_FALLBACK_SUMMARY
            if on_title:
                on_title(title)
            story_txt = os.path.join(story_dir, "이야기_대본.txt")
            with open(story_txt, "w", encoding="utf-8") as f:
                f.write(f"제목: {title}\n\n{text}\n")

            # 편 표시([[EP:제목]])를 기준으로 문단을 나누고, 각 편이 시작되는 문단 번호를 기억
            paragraphs, ep_starts = [], []
            chunks = re.split(r"\[\[EP:(.*?)\]\]", text)
            if len(chunks) == 1:
                paragraphs = narr_split_paragraphs(text)
            else:
                paragraphs = narr_split_paragraphs(chunks[0])
                for i in range(1, len(chunks), 2):
                    ep_starts.append((len(paragraphs), chunks[i].strip()))
                    paragraphs += narr_split_paragraphs(chunks[i + 1])
            self.ep_breaks = {pi for pi, _ in ep_starts if pi > 0}
            if not paragraphs and not ext_audio:
                raise RuntimeError("읽을 문장이 없습니다")

            # 2) 녹음 (외부 음성 파일이면 변환만)
            if ext_audio:
                narr_wav = os.path.join(tmp, "external.wav")
                rc, _, err = self._ff([FFMPEG, "-v", "error", "-y", "-i", ext_audio, "-vn", "-ac", "1",
                                       "-ar", str(self.SR), "-sample_fmt", "s16", narr_wav])
                if rc != 0:
                    raise RuntimeError("외부 음성 파일을 읽지 못했습니다: " + err.decode("utf-8", "ignore")[-300:])
                narr_len = self.probe_duration(narr_wav)
                segs, self.para_starts, ep_starts = [], [0.0], []
                if not self.summary and text.strip():
                    self.summary = fit_summary(re.split(r"(?<=[.!?…])\s+", " ".join(text.split()))[0])
            else:
                narr_wav, segs, narr_len = self.synthesize(paragraphs, spec, tmp)
            episodes = [{"title": t_, "start_sec": round(start_sec + self.para_starts[pi], 1)}
                        for pi, t_ in ep_starts if pi < len(self.para_starts)]
            chars = sum(len(s) for p in paragraphs for s in p)
            self.log(f"  ✅ 녹음 완료 — {narr_len/60:.1f}분 (초당 {chars/max(1, narr_len):.1f}자)")
            short = spec["label"].split("—")[0].replace("·", "").replace(" ", "")
            keep_wav = os.path.join(story_dir, f"내레이션_{short}.wav")
            shutil.copyfile(narr_wav, keep_wav)

            # 3) 자막(SRT) — 유튜브 자막으로 바로 업로드 가능
            srt = os.path.join(story_dir, f"자막_{short}.srt")
            if not segs:
                srt = "(외부 음성은 자막 자동 생성 안 함 — Vrew에서 자막 파일(SRT)을 따로 내보내 쓰세요)"
            else:
              with open(srt, "w", encoding="utf-8") as f:
                for i, (a, b, s) in enumerate(segs, 1):
                    if start_sec + a >= vdur - 1:
                        break
                    f.write(f"{i}\n{_srt_time(start_sec + a)} --> {_srt_time(min(vdur - 1, start_sec + b))}\n{s}\n\n")

            # 4) 믹싱
            out_path = f"{base}_내레이션_{short}.mp4"
            # 4-1) v11.6: 이야기 제목 카드 — 앞부분(첫 키프레임까지)만 새로 인코딩하고,
            #      믹싱할 때 나머지 영상과 이어붙여 '한 번에' 새 파일로 쓴다.
            card_ok = False
            vin = None
            if title_sec and title_sec > 0 and HAS_PIL:
                self.log(f"  🎬 영상 첫 {title_sec:.0f}초에 이야기 제목 「{title}」 넣는 중...")
                try:
                    pipe = Pipeline(self.log, self.stop_flag)
                    wh = pipe.get_video_size(video)
                    if not wh:
                        raise RuntimeError("영상 해상도를 읽을 수 없습니다")
                    card = pipe._render_title_card(
                        wh[0], wh[1], title, tmp,
                        label_kr=("오늘 밤의 이야기" if len(ep_starts) < 2 else f"오늘 밤의 이야기 · 총 {len(ep_starts)}편"))
                    shutil.copyfile(card, os.path.join(story_dir, "제목카드.png"))
                    kt = pipe._next_keyframe_time(video, title_sec)
                    if kt is None or kt > vdur - 2.0:
                        raise RuntimeError("제목 뒤 이어붙일 키프레임을 찾지 못했습니다")
                    try:
                        fn, fd_ = (pipe.probe(video, "stream=r_frame_rate") or "30/1").split("/")
                        fps = float(fn) / float(fd_)
                    except Exception:
                        fps = 30.0
                    intro = os.path.join(tmp, "title_intro.mp4")
                    pipe._encode_caption_clip(video, card, title_sec, kt - 0.5 / fps, intro,
                                              fade_in=0.8, fade_out=1.0)
                    lst = os.path.join(tmp, "title_concat.txt")
                    with open(lst, "w", encoding="utf-8") as f:
                        f.write("file '" + intro.replace("'", "'\\''") + "'\n")
                        f.write("file '" + os.path.abspath(video).replace("'", "'\\''") + "'\n")
                        f.write(f"inpoint {kt:.6f}\n")
                    vin = ["-f", "concat", "-safe", "0", "-i", lst]
                    card_ok = True
                except InterruptedError:
                    raise
                except Exception as ex:
                    self.log(f"  ⚠️ 제목 카드는 건너뛰고 계속 진행합니다: {ex}")

            self.mix(video, narr_wav, narr_len, start_sec, duck_key, vdur, out_path, vin=vin)
            ndur = self.probe_duration(out_path)
            if abs(ndur - vdur) > 2.0:
                raise RuntimeError(f"완성 영상 길이가 원본과 다릅니다 (원본 {vdur:.0f}초 / 결과 {ndur:.0f}초)")

            # 5) 유튜브 패키지 연동용 이야기 정보 (제목 부제목 + 설명란 요약 + 타임라인)
            info = {"title": title, "summary": fit_summary(self.summary),
                    "start_sec": round(start_sec, 1),
                    "end_sec": round(min(vdur - 1, start_sec + narr_len), 1),
                    "voice": spec["label"], "video": os.path.basename(out_path),
                    "title_card_sec": float(title_sec) if card_ok else 0.0,
                    "episodes": episodes}
            with open(os.path.join(story_dir, "story_info.json"), "w", encoding="utf-8") as f:
                json.dump(info, f, ensure_ascii=False, indent=2)
            self.log(f"  📖 이야기 요약({len(info['summary'])}자): {info['summary']}")
            self.log(f"\n🎉 완성! ({(time.time() - t0)/60:.1f}분 소요)\n"
                     f"   🎬 영상: {out_path}\n"
                     f"   📄 대본: {story_txt}\n"
                     f"   💬 자막: {srt}  ← 유튜브 [자막] 메뉴에 그대로 업로드\n"
                     f"   🔁 다른 성우로 비교하려면 '이야기 파일'에 위 대본을 넣고 성우만 바꿔 다시 실행하세요")
            if getattr(self, "classic_state_pending", None):
                save_classic_state(self.classic_state_pending)
                self.log(f"  📚 연재 진행 상태 저장 — {classic_status_text()}")
            self.log("  💡 [유튜브 패키지] 탭에 이 영상과 이야기 제목·요약이 자동으로 들어갔어요")
            return out_path
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ==================== v11.18: 🌧 AI 배경 탭 (SceneMaker 연결) ====================
# E:\SceneMaker 를 그대로 불러 쓴다 (코드를 복사하지 않음 → SceneMaker 를 고치면 여기도 바로 반영).
# ① AI 배경 이미지 생성(ComfyUI) → ② 목록에서 골라 미리보기 → ③ 빗줄기·물 효과 루프 영상
# → 완성 영상은 [📦 유튜브 패키지]·[🌙 스토리 내레이션] 탭에 자동 입력.
SCENEMAKER_DIR = r"E:\SceneMaker"
SCENEMAKER_OUT = os.path.join(SCENEMAKER_DIR, "output")
COMFY_START_BAT = os.path.join(SCENEMAKER_DIR, "scripts", "start_comfyui.bat")
COMFY_URL = "http://127.0.0.1:8188"
SM_TAB_CFG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scenemaker_tab.json")
SM_DURATIONS = [("3분 (테스트)", "3m"), ("1시간", "1h"), ("3시간", "3h"), ("5시간", "5h"),
                ("8시간", "8h"), ("10시간", "10h"), ("3분 + 10시간", "3m,10h"),
                ("전부 (3분·1·3·5·8·10시간)", "all")]
SM_RAIN = [("자동 (씬 기본값)", ""), ("가랑비", "light"), ("보통 비", "steady"), ("폭우", "heavy")]
SM_MODELS = [("자동 (씬 기본값)", ""), ("Z-Image Turbo (사실적)", "zimage"), ("SDXL (+한국 풍경 LoRA)", "sdxl")]
SM_IMG_EXT = (".png", ".jpg", ".jpeg", ".webp")


def sm_python():
    """SceneMaker 를 돌릴 파이썬 — py -3.14 (numpy·opencv 설치됨), 없으면 지금 파이썬."""
    return ["py", "-3.14"] if shutil.which("py") else [sys.executable]


def comfy_alive(timeout=1.5):
    import urllib.request
    try:
        with urllib.request.urlopen(COMFY_URL + "/system_stats", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def sm_recent_jobs(limit=60):
    """SceneMaker 결과 폴더에서 배경 이미지가 있는 작업을 최신순으로."""
    try:
        names = sorted(os.listdir(SCENEMAKER_OUT), reverse=True)
    except OSError:
        return []
    out = []
    for n in names:
        bg = os.path.join(SCENEMAKER_OUT, n, "background.png")
        if n.startswith("_") or not os.path.isfile(bg):
            continue
        out.append(bg)
        if len(out) >= limit:
            break
    return out


def sm_job_label(bg):
    """'09-29 20:04  cafe_window  🎬' — 이미 영상을 만든 배경은 🎬 표시."""
    job = os.path.dirname(bg)
    name = os.path.basename(job)
    m = re.match(r"(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})\d{2}_(.+?)(?:_\d+)?$", name)
    label = f"{m.group(2)}-{m.group(3)} {m.group(4)}:{m.group(5)}  {m.group(6)}" if m else name
    try:
        if any(f.startswith("final_") and f.endswith(".mp4") for f in os.listdir(job)):
            label += "  🎬"
    except OSError:
        pass
    return label


class SceneTabMixin:
    """App 에 섞어 쓰는 AI 배경 탭. 백그라운드 스레드는 tk 를 만지지 않고 log_q 로만 알린다."""

    # ---------- 설정 ----------
    def _sm_load_cfg(self):
        try:
            with open(SM_TAB_CFG, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _sm_save_cfg(self):
        cfg = dict(scene=self.sm_scene_var.get(), count=self._sm_count(), rain=self.sm_rain_var.get(),
                   model=self.sm_model_var.get(), audio=self.sm_audio_var.get(),
                   duration=self.sm_dur_var.get(), motion=self.sm_motion_var.get(),
                   details=self.sm_details_var.get(), wan=self.sm_wan_var.get())
        try:
            with open(SM_TAB_CFG, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=1)
        except OSError:
            pass

    def _sm_init_vars(self):
        cfg = self._sm_load_cfg()
        self.sm_scene_var = tk.StringVar(value=cfg.get("scene", ""))
        self.sm_count_var = tk.StringVar(value=str(cfg.get("count", 2)))
        self.sm_rain_var = tk.StringVar(value=cfg.get("rain", SM_RAIN[0][0]))
        self.sm_model_var = tk.StringVar(value=cfg.get("model", SM_MODELS[0][0]))
        self.sm_extra_var = tk.StringVar()
        self.sm_image_var = tk.StringVar()
        self.sm_audio_var = tk.StringVar(value=cfg.get("audio", ""))
        self.sm_dur_var = tk.StringVar(value=cfg.get("duration", SM_DURATIONS[0][0]))
        self.sm_motion_var = tk.BooleanVar(value=cfg.get("motion", True))
        self.sm_details_var = tk.BooleanVar(value=cfg.get("details", True))
        self.sm_wan_var = tk.BooleanVar(value=cfg.get("wan", False))
        self.sm_comfy_var = tk.StringVar(value="ComfyUI 확인 중…")
        self.sm_proc = None
        self.sm_stop_flag = threading.Event()
        self.sm_items = []          # 목록에 보이는 배경 이미지 경로
        self._sm_thumb = None

    def _sm_count(self):
        try:
            return max(1, min(8, int(self.sm_count_var.get())))
        except (ValueError, tk.TclError):
            return 2

    # ---------- 화면 ----------
    def _build_scene_tab(self, nb, pad):
        tab = ttk.Frame(nb)
        nb.add(tab, text="  🌧 AI 배경  ")
        self.sm_tab = tab

        top = ttk.Frame(tab); top.pack(fill="x", **pad)
        self.sm_comfy_lbl = ttk.Label(top, textvariable=self.sm_comfy_var)
        self.sm_comfy_lbl.pack(side="left")
        self.sm_comfy_btn = ttk.Button(top, text="ComfyUI 켜기", command=self.sm_start_comfy)
        self.sm_comfy_btn.pack(side="left", padx=8)
        ttk.Button(top, text="📂 결과 폴더", command=self.sm_open_out).pack(side="right")

        g = ttk.LabelFrame(tab, text=" ① AI 배경 이미지 만들기 ")
        g.pack(fill="x", padx=10, pady=(2, 0))
        r1 = ttk.Frame(g); r1.pack(fill="x", padx=8, pady=(4, 2))
        ttk.Label(r1, text="장면:").pack(side="left")
        self.sm_scene_cb = ttk.Combobox(r1, textvariable=self.sm_scene_var, width=32, state="readonly")
        self.sm_scene_cb.pack(side="left", padx=4)
        ttk.Label(r1, text="장수:").pack(side="left", padx=(10, 0))
        ttk.Spinbox(r1, from_=1, to=8, width=4, textvariable=self.sm_count_var).pack(side="left", padx=4)
        r2 = ttk.Frame(g); r2.pack(fill="x", padx=8, pady=2)
        ttk.Label(r2, text="비:").pack(side="left")
        ttk.Combobox(r2, textvariable=self.sm_rain_var, width=16, state="readonly",
                     values=[n for n, _ in SM_RAIN]).pack(side="left", padx=4)
        ttk.Label(r2, text="모델:").pack(side="left", padx=(10, 0))
        ttk.Combobox(r2, textvariable=self.sm_model_var, width=24, state="readonly",
                     values=[n for n, _ in SM_MODELS]).pack(side="left", padx=4)
        r3 = ttk.Frame(g); r3.pack(fill="x", padx=8, pady=2)
        ttk.Label(r3, text="추가 묘사 (영어, 선택):").pack(side="left")
        ttk.Entry(r3, textvariable=self.sm_extra_var, width=44).pack(side="left", padx=4)
        r4 = ttk.Frame(g); r4.pack(fill="x", padx=8, pady=(2, 6))
        self.sm_img_btn = ttk.Button(r4, text="🖼 배경 만들기", command=self.sm_make_images)
        self.sm_img_btn.pack(side="left")
        ttk.Label(r4, text="장당 약 40초 · 시간대·계절·구도는 매번 자동으로 달라져요",
                  foreground="#666666").pack(side="left", padx=8)

        s = ttk.LabelFrame(tab, text=" ② 배경 고르기 (🎬 = 이미 영상을 만든 배경) ")
        s.pack(fill="x", padx=10, pady=(4, 0))
        body = ttk.Frame(s); body.pack(fill="x", padx=8, pady=(4, 2))
        lf = ttk.Frame(body); lf.pack(side="left", fill="y")
        self.sm_list = tk.Listbox(lf, height=8, width=34, exportselection=False, font=("Malgun Gothic", 9))
        sb = ttk.Scrollbar(lf, orient="vertical", command=self.sm_list.yview)
        self.sm_list.configure(yscrollcommand=sb.set)
        self.sm_list.pack(side="left", fill="y")
        sb.pack(side="left", fill="y")
        self.sm_list.bind("<<ListboxSelect>>", self._sm_on_select)
        self.sm_list.bind("<Double-Button-1>", lambda e: self.sm_open_image())
        self.sm_preview = tk.Label(body, text="배경을 고르면\n여기에 미리보기", width=40, height=9,
                                   background="#222222", foreground="#aaaaaa")
        self.sm_preview.pack(side="left", padx=(8, 0))
        sbtn = ttk.Frame(s); sbtn.pack(fill="x", padx=8, pady=(2, 6))
        ttk.Button(sbtn, text="🔄 새로고침", command=self.sm_refresh_list).pack(side="left")
        ttk.Button(sbtn, text="📂 내 사진 쓰기", command=self.sm_pick_image).pack(side="left", padx=6)
        ttk.Button(sbtn, text="🔍 크게 보기", command=self.sm_open_image).pack(side="left")

        v = ttk.LabelFrame(tab, text=" ③ 빗소리 루프 영상 만들기 ")
        v.pack(fill="x", padx=10, pady=(4, 0))
        v1 = ttk.Frame(v); v1.pack(fill="x", padx=8, pady=(4, 2))
        ttk.Label(v1, text="⏱ 길이:").pack(side="left")
        ttk.Combobox(v1, textvariable=self.sm_dur_var, width=26, state="readonly",
                     values=[n for n, _ in SM_DURATIONS]).pack(side="left", padx=4)
        ttk.Label(v1, text="1440p · 40GB 이하 자동", foreground="#666666").pack(side="left", padx=6)
        v2 = ttk.Frame(v); v2.pack(fill="x", padx=8, pady=2)
        ttk.Label(v2, text="🎵 빗소리:").pack(side="left")
        ttk.Entry(v2, textvariable=self.sm_audio_var, width=46).pack(side="left", padx=4)
        ttk.Button(v2, text="찾기", command=self.sm_pick_audio).pack(side="left")
        v3 = ttk.Frame(v); v3.pack(fill="x", padx=8, pady=2)
        ttk.Checkbutton(v3, text="잎 흔들림·물 일렁임", variable=self.sm_motion_var).pack(side="left")
        ttk.Checkbutton(v3, text="물 튀김·물결·물방울", variable=self.sm_details_var).pack(side="left", padx=10)
        v3b = ttk.Frame(v); v3b.pack(fill="x", padx=8, pady=2)
        ttk.Checkbutton(v3b, text="💧 물·안개 AI 움직임 (Wan 2.2 · 시험 기능 · 약 10분 더 걸림)",
                        variable=self.sm_wan_var).pack(side="left")
        v4 =ttk.Frame(v); v4.pack(fill="x", padx=8, pady=(2, 6))
        self.sm_vid_btn = ttk.Button(v4, text="🎬 영상 만들기", command=self.sm_make_video)
        self.sm_vid_btn.pack(side="left")
        self.sm_stop_btn = ttk.Button(v4, text="⏹ 중단", command=self.sm_stop, state="disabled")
        self.sm_stop_btn.pack(side="left", padx=6)
        ttk.Label(v4, text="완성되면 [📦 유튜브 패키지] 탭에 자동 입력",
                  foreground="#666666").pack(side="left", padx=4)

        self.sm_refresh_list()
        threading.Thread(target=self._sm_load_scenes, daemon=True).start()
        self.after(500, self._sm_comfy_tick)

    # ---------- 씬 목록 / ComfyUI 상태 ----------
    def _sm_load_scenes(self):
        code = ("import json; from scenemaker.scenes import SCENES; "
                "print(json.dumps([[k, v.title] for k, v in SCENES.items()], ensure_ascii=False))")
        try:
            r = subprocess.run(sm_python() + ["-c", code], cwd=SCENEMAKER_DIR, capture_output=True,
                               timeout=60, creationflags=CREATE_NO_WINDOW,
                               env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            items = json.loads(r.stdout.decode("utf-8", "replace").strip().splitlines()[-1])
            self.log_q.put(("__SM_SCENES__", [f"{k} — {t}" for k, t in items]))
        except Exception as ex:
            self.log(f"⚠️ SceneMaker 장면 목록을 못 읽었어요 ({SCENEMAKER_DIR}): {ex}")

    def _sm_comfy_tick(self):
        def check():
            self.log_q.put(("__SM_COMFY__", comfy_alive()))
        threading.Thread(target=check, daemon=True).start()
        self.after(10000, self._sm_comfy_tick)

    def sm_start_comfy(self, quiet=False):
        if comfy_alive(0.5):
            if not quiet:
                self.log("ComfyUI 는 이미 켜져 있어요")
            return
        if not os.path.isfile(COMFY_START_BAT):
            self.log(f"❌ ComfyUI 실행 파일이 없어요: {COMFY_START_BAT}")
            return
        # 별도 창(최소화)으로 켠다 — 이미지 만드는 동안 그 창은 닫지 마세요
        # start 의 첫 따옴표 인자는 창 제목 — 따옴표가 없으면 제목을 명령으로 알고 실패함
        subprocess.Popen(f'start "ComfyUI" /min "{COMFY_START_BAT}"', shell=True,
                         cwd=os.path.dirname(COMFY_START_BAT), creationflags=CREATE_NO_WINDOW)
        self.sm_comfy_var.set("ComfyUI 켜는 중… (30초~1분)")
        self.log("🟡 ComfyUI 를 켜고 있어요 (작업표시줄에 최소화된 창 — 닫지 마세요)")

    def sm_open_out(self):
        if os.path.isdir(SCENEMAKER_OUT):
            os.startfile(SCENEMAKER_OUT)

    # ---------- 배경 목록 ----------
    def sm_refresh_list(self, select=None):
        keep = [p for p in self.sm_items if not p.startswith(SCENEMAKER_OUT)]   # 직접 고른 사진은 유지
        self.sm_items = keep + [p for p in sm_recent_jobs() if p not in keep]
        self.sm_list.delete(0, "end")
        for p in self.sm_items:
            self.sm_list.insert("end", sm_job_label(p) if p.startswith(SCENEMAKER_OUT)
                                else f"📷 {os.path.basename(p)}")
        target = select or self.sm_image_var.get()
        if target in self.sm_items:
            i = self.sm_items.index(target)
            self.sm_list.selection_clear(0, "end")
            self.sm_list.selection_set(i)
            self.sm_list.see(i)
            self._sm_show(target)

    def _sm_on_select(self, _=None):
        sel = self.sm_list.curselection()
        if sel:
            self._sm_show(self.sm_items[sel[0]])

    def _sm_show(self, path):
        self.sm_image_var.set(path)
        if not HAS_PIL:
            self.sm_preview.configure(text=os.path.basename(path))
            return
        try:
            from PIL import ImageTk
            im = Image.open(path)
            im.draft("RGB", (640, 360))
            im = im.convert("RGB")
            im.thumbnail((288, 162))
            self._sm_thumb = ImageTk.PhotoImage(im)
            self.sm_preview.configure(image=self._sm_thumb, text="", width=288, height=162)
        except Exception as ex:
            self.sm_preview.configure(image="", text=f"미리보기 실패\n{ex}")

    def sm_pick_image(self):
        p = filedialog.askopenfilename(filetypes=[("이미지", "*.png *.jpg *.jpeg *.webp"), ("모든 파일", "*.*")])
        if p:
            p = os.path.normpath(p)
            if p not in self.sm_items:
                self.sm_items.insert(0, p)
            self.sm_refresh_list(select=p)

    def sm_open_image(self):
        p = self.sm_image_var.get()
        if p and os.path.isfile(p):
            os.startfile(p)

    def sm_pick_audio(self):
        cur = self.sm_audio_var.get()
        p = filedialog.askopenfilename(initialdir=os.path.dirname(cur) if cur else None,
                                       filetypes=[("오디오", "*.wav *.mp3 *.m4a *.flac"), ("모든 파일", "*.*")])
        if p:
            self.sm_audio_var.set(os.path.normpath(p))

    # ---------- 실행 ----------
    def _sm_buttons(self, running):
        st = "disabled" if running else "normal"
        self.sm_img_btn.configure(state=st)
        self.sm_vid_btn.configure(state=st)
        self.sm_stop_btn.configure(state="normal" if running else "disabled")

    def _sm_scene_name(self):
        return self.sm_scene_var.get().split(" — ")[0].strip()

    def sm_make_images(self):
        scene = self._sm_scene_name()
        if not scene:
            messagebox.showwarning("확인", "만들 장면을 골라주세요")
            return
        args = ["image", "--scene", scene, "--count", str(self._sm_count())]
        rain = dict(SM_RAIN).get(self.sm_rain_var.get(), "")
        model = dict(SM_MODELS).get(self.sm_model_var.get(), "")
        if rain:
            args += ["--rain", rain]
        if model:
            args += ["--model", model]
        extra = self.sm_extra_var.get().strip()
        if extra:
            args += ["--extra", extra]
        self._sm_save_cfg()
        self._sm_run("image", args, need_comfy=True)

    def sm_make_video(self):
        img = self.sm_image_var.get()
        if not img or not os.path.isfile(img):
            messagebox.showwarning("확인", "② 에서 배경을 먼저 골라주세요")
            return
        audio = self.sm_audio_var.get().strip()
        if not audio:
            if not messagebox.askyesno("빗소리 없음", "빗소리 파일 없이 화면만 만들까요?\n"
                                                     "(보통은 직접 녹음한 빗소리를 넣어요)"):
                return
        elif not os.path.isfile(audio):
            messagebox.showwarning("확인", f"빗소리 파일을 찾을 수 없어요:\n{audio}")
            return
        dur = dict(SM_DURATIONS).get(self.sm_dur_var.get(), "3m")
        args = ["loop", img, "--duration", dur]
        if audio:
            args += ["--audio", audio]
        if not os.path.isfile(os.path.join(os.path.dirname(img), "meta.json")):
            scene = self._sm_scene_name()      # 직접 고른 사진 → 빗줄기 느낌은 고른 장면을 따름
            if scene:
                args += ["--scene", scene]
        if not self.sm_motion_var.get():
            args.append("--no-motion")
        if not self.sm_details_var.get():
            args.append("--no-details")
        wan = self.sm_wan_var.get()
        if wan:
            args.append("--wan")
        self._sm_save_cfg()
        self._sm_run("video", args, need_comfy=wan)

    def _sm_run(self, kind, args, need_comfy=False):
        if self.sm_proc and self.sm_proc.poll() is None:
            messagebox.showinfo("진행 중", "SceneMaker 작업이 아직 진행 중이에요")
            return
        cmd = sm_python() + ["-u", "-m", "scenemaker"] + args
        self.sm_stop_flag.clear()
        self._sm_buttons(True)
        self.log(f"\n🌧 SceneMaker: {' '.join(args[:1])} 시작")
        if need_comfy and not comfy_alive(0.5):
            self.sm_start_comfy(quiet=True)

        def work():
            found, job, rc = [], None, -1
            try:
                if need_comfy:
                    t0 = time.time()
                    while not comfy_alive(1.0):
                        if self.sm_stop_flag.is_set():
                            return
                        if time.time() - t0 > 240:
                            self.log("❌ ComfyUI 가 4분 안에 켜지지 않았어요 — ComfyUI 창의 오류를 확인해주세요")
                            return
                        time.sleep(2)
                env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
                self.sm_proc = subprocess.Popen(cmd, cwd=SCENEMAKER_DIR, stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT, env=env,
                                                creationflags=CREATE_NO_WINDOW)
                buf = b""
                while True:
                    chunk = self.sm_proc.stdout.read1(4096)
                    if not chunk:
                        break
                    buf += chunk
                    parts = re.split(rb"[\r\n]", buf)
                    buf = parts.pop()
                    for raw in parts:
                        line = raw.decode("utf-8", "replace").rstrip()
                        if not line:
                            continue
                        self.log("  " + line.strip())
                        m = re.search(r"->\s+(.+?background\.png)", line)
                        if m:
                            found.append(os.path.normpath(os.path.join(SCENEMAKER_DIR, m.group(1).strip())))
                        m = re.search(r"미리보기:\s+(.+?)[\\/]preview\.png", line)
                        if m:
                            job = os.path.normpath(os.path.join(SCENEMAKER_DIR, m.group(1).strip()))
                        m = re.search(r"->\s+(final_\S+\.mp4)", line)
                        if m and job:
                            found.append(os.path.join(job, m.group(1)))
                rc = self.sm_proc.wait()
            except Exception as ex:
                self.log(f"❌ SceneMaker 실행 오류: {ex}")
            finally:
                self.log_q.put(("__SM_DONE__", kind, found, rc, self.sm_stop_flag.is_set()))

        threading.Thread(target=work, daemon=True).start()

    def sm_stop(self):
        self.sm_stop_flag.set()
        p = self.sm_proc
        if p and p.poll() is None:
            # py 런처 → python → ffmpeg 까지 한꺼번에 종료
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True,
                           creationflags=CREATE_NO_WINDOW)
        self.log("⏹ SceneMaker 중단 요청")

    # ---------- _poll_log 에서 호출 (메인 스레드) ----------
    def _sm_handle(self, msg):
        tag = msg[0]
        if tag == "__SM_SCENES__":
            self.sm_scene_cb.configure(values=msg[1])
            names = [s.split(" — ")[0] for s in msg[1]]
            if self._sm_scene_name() not in names and msg[1]:
                self.sm_scene_var.set(msg[1][0])
            elif self._sm_scene_name():
                self.sm_scene_var.set(msg[1][names.index(self._sm_scene_name())])
        elif tag == "__SM_COMFY__":
            self.sm_comfy_var.set("🟢 ComfyUI 켜짐 (배경 만들기 가능)" if msg[1]
                                  else "⚪ ComfyUI 꺼짐 — 배경 만들기를 누르면 자동으로 켜요")
            self.sm_comfy_btn.configure(state="disabled" if msg[1] else "normal")
        elif tag == "__SM_DONE__":
            _, kind, found, rc, stopped = msg
            self._sm_buttons(False)
            if stopped:
                self.log("⏹ SceneMaker 작업을 멈췄어요")
            elif rc != 0:
                self.log(f"❌ SceneMaker 가 오류로 끝났어요 (코드 {rc}) — 위 로그를 확인해주세요")
            if kind == "image" and found:
                self.sm_refresh_list(select=found[0])
                self.log(f"✅ 배경 {len(found)}장 완성 — ② 목록에서 골라 ③ 영상 만들기")
            elif kind == "video":
                self.sm_refresh_list()
                videos = [p for p in found if os.path.isfile(p)]
                if videos and rc == 0:
                    main = videos[-1]
                    self.pkg_video_var.set(main)
                    self.narr_video_var.set(main)
                    self._reset_claude_scene_data()
                    self.last_output = main
                    self.log(f"✅ 영상 완성: {main}\n   → [📦 유튜브 패키지] 탭에 입력했어요")


class App(SceneTabMixin, tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LoopMaker v11.19 — 루프 + 🌧 AI 배경 + 🌙 스토리 내레이션 + 유튜브 패키지 + 숏폼 + 오디오 정제 (Somnia Forest)")
        # v9.7: 유튜브 패키지 탭에 인트로 자막 UI가 추가되면서 탭 내용이 커졌는데
        # 창 크기가 고정(resizable False)이라 진행 로그 칸이 밀려서 작아 보이던
        # 문제 수정 — 창을 더 크게 잡고, 필요하면 사용자가 직접 늘릴 수 있게 함.
        self.geometry("700x1000")
        self.minsize(660, 760)
        self.resizable(True, True)

        self.video_var = tk.StringVar()
        self.audio_var = tk.StringVar()
        self.outdir_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Videos"))
        self.dur_var = tk.StringVar(value="10시간")
        # v9.3: 기본값을 크로스페이드로 변경 — 모션 보간(minterpolate)은 빗방울처럼
        # 조밀하고 불규칙한 움직임에서 프레임을 잘못 추정해 뭉개지는 경우가 많음.
        # 크로스페이드(디졸브)는 어떤 영상이든 실패 없이 안전하게 이음새를 감춰줌.
        # v9.6: 실사용 비교 테스트 결과 0.5초보다 0.15초가 나뭇잎/물결처럼 계속
        # 움직이는 배경에서 이중노출(흔들림)이 훨씬 덜해 기본값을 0.15초로 낮춤.
        self.smooth_var = tk.StringVar(value="크로스페이드 0.15초 (권장)")
        self.flatten_var = tk.BooleanVar(value=False)
        self.fade_var = tk.BooleanVar(value=True)
        self.loop_unit_var = tk.StringVar(value="일반 (4초 이상 — 자동 최적 구간 탐색)")
        self.short_unit_sec = tk.DoubleVar(value=2.0)

        # 오디오 정제 탭 변수
        self.clean_in_var = tk.StringVar()
        self.seg_var = tk.BooleanVar(value=True)
        self.sens_var = tk.StringVar(value="표준")
        self.declick_var = tk.BooleanVar(value=True)
        self.declick_str_var = tk.StringVar(value="표준")
        self.rumble_var = tk.BooleanVar(value=False)
        self.normalize_var = tk.BooleanVar(value=False)
        self.norm_level_var = tk.StringVar(value="적당히 (-3dB)")

        # 유튜브 패키지 탭 변수 (v9.6: 고정 주제 목록 제거 — 항상 새로 입력/자동분석)
        self.pkg_video_var = tk.StringVar()
        # v11: 🌙 내레이션 이야기 (영상 선택 시 story_info.json에서 자동으로 채워짐, 수정 가능)
        self.story_title_var = tk.StringVar()
        self.story_summary_var = tk.StringVar()
        self.story_meta = {}
        self.thumb_text_var = tk.StringVar()
        self.sub_text_var = tk.StringVar(value="Deep Sleep · Relaxation · ASMR")
        self.thumb2_var = tk.StringVar()
        self.sub2_var = tk.StringVar(value="Fall Asleep Fast · ASMR")
        self.thumb3_var = tk.StringVar()
        self.sub3_var = tk.StringVar(value="Relax · Study · Sleep")
        self.text_pos_var = tk.StringVar(value="상단")
        self.pkg_outdir_var = tk.StringVar()
        self.shorts_var = tk.BooleanVar(value=True)
        self.shorts_crop_var = tk.StringVar(value="중앙")
        # v9.7: 기본값으로 채널 주소를 미리 채워둠 — 지우면 얼마든지 다른 주소로 바꿀 수 있음
        self.channel_url_var = tk.StringVar(value="https://www.youtube.com/@somnia-forest")
        self.custom_en_var = tk.StringVar()
        self.custom_kr_var = tk.StringVar()
        # Claude 자동 분석이 채워주는 장면 묘사 문장/설명란 도입부 — 화면에는 안 보이는 보조값
        self.scene_en_var = tk.StringVar()
        self.scene_kr_var = tk.StringVar()
        self.desc_en_var = tk.StringVar()
        self.desc_kr_var = tk.StringVar()
        # v9.7: 인트로 자막 문구 — 자동 분석으로 채워지지만 화면에 노출되어 직접 수정 가능
        self.caption_kr_var = tk.StringVar()
        self.caption_en_var = tk.StringVar()
        self.caption_sec_var = tk.DoubleVar(value=30.0)
        self.skip_caption_var = tk.BooleanVar(value=False)
        self._last_auto_en = ""
        self._last_auto_thumb = ""
        self.custom_kr_var.trace_add("write", self._auto_translate_topic)
        self.custom_kr_var.trace_add("write", self._auto_fill_thumb)
        self.custom_en_var.trace_add("write", self._auto_fill_thumb)
        self.custom_tags_var = tk.StringVar()
        self.claude_status_var = tk.StringVar(value="")

        # v11: 스토리 내레이션 탭 변수
        self.narr_video_var = tk.StringVar()
        self.narr_hint_var = tk.StringVar()
        self.narr_story_var = tk.StringVar()
        self.narr_ext_audio_var = tk.StringVar()     # v11.10: Vrew 등 외부 음성 파일
        self.narr_voice_var = tk.StringVar(value=NARR_VOICES[1][0])   # v11.9: 기본 성우 = 현수 (1c 설정)
        self.narr_speed_var = tk.StringVar(value="기본 (잠자리 속도)")
        self.narr_duck_var = tk.StringVar(value="보통 (권장)")
        self.narr_len_var = tk.StringVar(value=NARR_LEN[0][0])
        self.narr_start_var = tk.DoubleVar(value=6.0)
        self.narr_title_sec_var = tk.DoubleVar(value=5.0)   # v11.5: 영상 첫 부분 이야기 제목 표시 시간
        self.narr_stop_flag = threading.Event()
        self.narrator = None
        # v11.1: 루프 제작이 끝나면 바로 이어서 이야기 내레이션까지 자동으로 넣기
        self.auto_narr_var = tk.BooleanVar(value=True)
        # v11.3: 음성 엔진 (무료 Edge / Azure 공식) — 키는 이 PC의 사용자 폴더에만 저장
        _cfg = load_tts_config()
        self.tts_engine_var = tk.StringVar(value=next((k for k, v in NARR_ENGINES.items()
                                                       if v == _cfg.get("engine", "edge")),
                                                      list(NARR_ENGINES)[0]))
        self.azure_key_var = tk.StringVar(value=_cfg.get("azure_key", ""))
        self.azure_region_var = tk.StringVar(value=_cfg.get("azure_region", "koreacentral"))
        # v11.2: 이야기 제목 (비우면 Claude가 지음 / ✨ 버튼으로 후보 3개 미리 받기 / 완성 후 실제 제목 표시)
        self.narr_title_var = tk.StringVar()
        self.narr_style_var = tk.StringVar(value=list(NARR_STYLES)[0])
        self.narr_tone_var = tk.StringVar(value=list(NARR_TONES)[0])

        self.stop_flag = threading.Event()
        self.pipeline = None
        self.worker = None
        self.log_q = queue.Queue()
        self.last_output = None
        self._sm_init_vars()

        self._build_ui()
        # v11.18: 바탕화면 'AI 배경 만들기' 아이콘 → AI 배경 탭으로 바로 열고 ComfyUI 켜기
        if "--scene" in sys.argv:
            self.nb.select(self.sm_tab)
            self.after(300, lambda: self.sm_start_comfy(quiet=True))
        self.after(100, self._poll_log)

    def _build_ui(self):
        pad = dict(padx=10, pady=4)
        nb = ttk.Notebook(self)
        nb.pack(fill="x", padx=8, pady=(8, 0))
        self.nb = nb

        # ===== 탭 1: 루프 제작 =====
        tab1 = ttk.Frame(nb)
        nb.add(tab1, text="  🔁 루프 영상 제작  ")

        frm = ttk.Frame(tab1); frm.pack(fill="x", **pad)
        ttk.Label(frm, text="🎬 원본 영상 (10초 Veo 클립 등)").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.video_var, width=58).grid(row=1, column=0, sticky="w")
        ttk.Button(frm, text="찾기", command=self.pick_video).grid(row=1, column=1, padx=6)

        ttk.Label(frm, text="🎵 오디오 (선택 — WAV/MP3/M4A/AAC/FLAC)").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(frm, textvariable=self.audio_var, width=58).grid(row=3, column=0, sticky="w")
        ttk.Button(frm, text="찾기", command=self.pick_audio).grid(row=3, column=1, padx=6)

        ttk.Label(frm, text="📁 저장 폴더").grid(row=4, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(frm, textvariable=self.outdir_var, width=58).grid(row=5, column=0, sticky="w")
        ttk.Button(frm, text="찾기", command=self.pick_outdir).grid(row=5, column=1, padx=6)

        opt = ttk.Frame(tab1); opt.pack(fill="x", **pad)
        ttk.Label(opt, text="⏱ 길이:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(opt, textvariable=self.dur_var, width=14, state="readonly",
                     values=[n for n, _ in DUR_PRESETS]).grid(row=0, column=1, padx=6)
        ttk.Label(opt, text="✨ 부드러움:").grid(row=0, column=2, padx=(20, 0))
        ttk.Combobox(opt, textvariable=self.smooth_var, width=22, state="readonly",
                     values=list(ALL_SMOOTH.keys())).grid(row=0, column=3, padx=6)
        ttk.Checkbutton(opt, text="🔊 오디오 볼륨 평탄화 (음량 기복이 큰 소스에 사용 — 페이드 자동 제거는 항상 적용)",
                        variable=self.flatten_var).grid(row=1, column=0, columnspan=4,
                                                        sticky="w", pady=(6, 0))
        ttk.Checkbutton(opt, text="🌅 시작 페이드인 / 끝 페이드아웃 (3초 — 영상·소리 모두, 중간 루프는 영향 없음)",
                        variable=self.fade_var).grid(row=2, column=0, columnspan=4,
                                                     sticky="w", pady=(2, 0))

        # 루프 단위 선택
        urow = ttk.LabelFrame(tab1, text="🔁 루프 단위 설정")
        urow.pack(fill="x", padx=10, pady=(4, 0))

        modes = [
            ("일반 (4초 이상 — 자동 최적 구간 탐색)",
             "일반 (4초 이상 — 자동 최적 구간 탐색)"),
            ("단위 반복 (짧은 클립 그대로 이어붙이기)",
             "단위 반복 (짧은 클립 그대로 이어붙이기)"),
        ]
        for label, val in modes:
            ttk.Radiobutton(urow, text=label, variable=self.loop_unit_var,
                            value=val, command=self._on_unit_change).pack(anchor="w", padx=8)

        self._unit_detail = ttk.Frame(urow)
        self._unit_detail.pack(fill="x", padx=24, pady=(0, 4))
        ttk.Label(self._unit_detail,
                  text="반복 단위 길이 (초) — 영상이 이 길이로 정확히 잘려 반복됩니다:").pack(side="left")
        for sec in (2.0, 3.0, 4.0, 5.0):
            ttk.Radiobutton(self._unit_detail, text=f"{sec:.0f}초",
                            variable=self.short_unit_sec, value=sec).pack(side="left", padx=4)
        self._unit_detail.pack_forget()   # 처음엔 숨김

        # v11.1: 🌙 루프 완성 후 이야기 내레이션 자동 추가
        nrow = ttk.LabelFrame(tab1, text="🌙 이야기 내레이션")
        nrow.pack(fill="x", padx=10, pady=(4, 0))
        ttk.Checkbutton(nrow, text="루프 완성 후 미스터리 이야기 내레이션 자동 추가",
                        variable=self.auto_narr_var).pack(anchor="w", padx=8, pady=(2, 0))
        nr2 = ttk.Frame(nrow); nr2.pack(fill="x", padx=24, pady=(2, 4))
        ttk.Label(nr2, text="성우:").pack(side="left")
        ttk.Combobox(nr2, textvariable=self.narr_voice_var, width=44, state="readonly",
                     values=[v[0] for v in NARR_VOICES]).pack(side="left", padx=4)
        ttk.Label(nr2, text="(속도·길이 등은 [🌙 스토리 내레이션] 탭 설정)",
                  foreground="#666666").pack(side="left", padx=4)
        nrt = ttk.Frame(nrow); nrt.pack(fill="x", padx=24, pady=(0, 2))
        ttk.Label(nrt, text="목소리 톤:").pack(side="left")
        ttk.Combobox(nrt, textvariable=self.narr_tone_var, width=40, state="readonly",
                     values=list(NARR_TONES)).pack(side="left", padx=4)
        nrs = ttk.Frame(nrow); nrs.pack(fill="x", padx=24, pady=(0, 2))
        ttk.Label(nrs, text="이야기 스타일:").pack(side="left")
        ttk.Combobox(nrs, textvariable=self.narr_style_var, width=56, state="readonly",
                     values=list(NARR_STYLES)).pack(side="left", padx=4)
        nr3 = ttk.Frame(nrow); nr3.pack(fill="x", padx=24, pady=(0, 2))
        ttk.Label(nr3, text="📖 이야기 제목:").pack(side="left")
        self.narr_title_cb1 = ttk.Combobox(nr3, textvariable=self.narr_title_var, width=34,
                                           font=("Malgun Gothic", 10))
        self.narr_title_cb1.pack(side="left", padx=4)
        self.narr_title_btn1 = ttk.Button(nr3, text="✨ 제목 후보 받기", command=self.narr_suggest_titles)
        self.narr_title_btn1.pack(side="left", padx=4)
        self.narr_title_status = tk.StringVar(value="비워두면 Claude가 영상 장면을 보고 직접 지어요")
        ttk.Label(nrow, textvariable=self.narr_title_status, foreground="#666666"
                  ).pack(anchor="w", padx=24, pady=(0, 4))

        btns = ttk.Frame(tab1); btns.pack(fill="x", **pad)
        self.start_btn = ttk.Button(btns, text="▶ 루프 영상 만들기", command=self.start)
        self.start_btn.pack(side="left", padx=4)
        self.stop_btn = ttk.Button(btns, text="⏹ 중단", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", padx=4)

        # ===== 탭 (v11.18): 🌧 AI 배경 — SceneMaker 연결 =====
        self._build_scene_tab(nb, pad)

        # ===== 탭 2: 유튜브 패키지 =====
        tab2 = ttk.Frame(nb)
        nb.add(tab2, text="  📦 유튜브 패키지  ")

        pfrm = ttk.Frame(tab2); pfrm.pack(fill="x", **pad)
        ttk.Label(pfrm, text="🎬 완성된 루프 영상 (루프 제작을 마치면 자동 입력됩니다)"
                  ).grid(row=0, column=0, sticky="w")
        ttk.Entry(pfrm, textvariable=self.pkg_video_var, width=58).grid(row=1, column=0, sticky="w")
        ttk.Button(pfrm, text="찾기", command=self.pick_pkg_video).grid(row=1, column=1, padx=6)

        ttk.Label(pfrm, text="🏷 영상 주제 (영상마다 새로 입력 — 아래 버튼으로 자동 분석도 가능)"
                  ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))
        arow = ttk.Frame(pfrm); arow.grid(row=3, column=0, columnspan=2, sticky="w", pady=(2, 0))
        self.claude_btn = ttk.Button(arow, text="🤖 Claude로 자동 분석 (내용 파악 + 실시간 검색 + 주제·썸네일 자동 생성)",
                                     command=self.run_claude_analysis)
        self.claude_btn.pack(side="left")
        ttk.Label(arow, textvariable=self.claude_status_var, foreground="#0a6").pack(side="left", padx=8)

        self.custom_frame = ttk.LabelFrame(pfrm, text="✏️ 주제 (자동 분석 결과가 채워짐 — 마음에 안 들면 직접 수정)")
        crow = ttk.Frame(self.custom_frame); crow.pack(fill="x", padx=8, pady=(4, 2))
        ttk.Label(crow, text="영어 주제:").pack(side="left")
        ttk.Entry(crow, textvariable=self.custom_en_var, width=22,
                  font=("Malgun Gothic", 10)).pack(side="left", padx=(4, 14))
        ttk.Label(crow, text="한글 주제:").pack(side="left")
        ttk.Entry(crow, textvariable=self.custom_kr_var, width=18,
                  font=("Malgun Gothic", 10)).pack(side="left", padx=4)

        crow2 = ttk.Frame(self.custom_frame); crow2.pack(fill="x", padx=8, pady=(2, 6))
        ttk.Label(crow2, text="추가 태그(쉼표 구분, 선택):").pack(side="left")
        ttk.Entry(crow2, textvariable=self.custom_tags_var, width=42,
                  font=("Malgun Gothic", 10)).pack(side="left", padx=4)
        ttk.Label(crow2, text="예) thunder, 천둥소리", foreground="#666666").pack(side="left", padx=6)
        self.custom_frame.grid(row=4, column=0, columnspan=2, sticky="we", pady=(6, 0))

        ttk.Label(pfrm, text="✏️ 썸네일 텍스트 3벌 (A/B 테스트용 — 각각 다른 문구로 thumb_1·2·3 생성 / 왼쪽=메인, 오른쪽=부제목)"
                  ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(10, 0))
        trow = ttk.Frame(pfrm); trow.grid(row=6, column=0, columnspan=2, sticky="w")
        for i, (mv, sv) in enumerate([(self.thumb_text_var, self.sub_text_var),
                                      (self.thumb2_var, self.sub2_var),
                                      (self.thumb3_var, self.sub3_var)], 1):
            ttk.Label(trow, text=f"썸네일{i}").grid(row=i, column=0, sticky="w", pady=1)
            ttk.Entry(trow, textvariable=mv, width=32,
                      font=("Malgun Gothic", 10)).grid(row=i, column=1, padx=(4, 8), pady=1)
            ttk.Entry(trow, textvariable=sv, width=30,
                      font=("Malgun Gothic", 9)).grid(row=i, column=2, pady=1)
        self.thumb_sug = ttk.Label(pfrm, text="비운 칸은 썸네일1 문구를 대신 사용 · 부제목 비우면 생략",
                                   foreground="#666666")
        self.thumb_sug.grid(row=7, column=0, columnspan=2, sticky="w")
        self.sub_sug = ttk.Label(pfrm, text="", foreground="#666666")
        self.sub_sug.grid(row=10, column=0, columnspan=2, sticky="w")

        posrow = ttk.Frame(pfrm); posrow.grid(row=11, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Label(posrow, text="위치 텍스트:").pack(side="left")
        ttk.Combobox(posrow, textvariable=self.text_pos_var, width=8, state="readonly",
                     values=["상단", "중앙", "하단"]).pack(side="left", padx=6)
        ttk.Label(posrow, text="(배경 장면을 가리지 않는 쪽으로 선택하세요)",
                  foreground="#666666").pack(side="left")

        ttk.Label(pfrm, text="자동 삽입: 왼쪽 위 Somnia Forest / 오른쪽 아래 영상 길이(10 Hours 등, 메인의 1/3 크기)",
                  foreground="#666666").grid(row=12, column=0, columnspan=2, sticky="w", pady=(6, 0))

        ttk.Label(pfrm, text="패키지 저장 폴더 (비우면 영상 옆에 영상이름_youtube 폴더 자동 생성)"
                  ).grid(row=13, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Entry(pfrm, textvariable=self.pkg_outdir_var, width=58).grid(row=14, column=0, sticky="w")
        ttk.Button(pfrm, text="찾기", command=self.pick_pkg_outdir).grid(row=14, column=1, padx=6)

        srow = ttk.Frame(pfrm); srow.grid(row=15, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Checkbutton(srow, text="55초 숏폼도 함께 생성", variable=self.shorts_var).pack(side="left")
        ttk.Label(srow, text="  크롭 위치:").pack(side="left")
        ttk.Combobox(srow, textvariable=self.shorts_crop_var, width=6, state="readonly",
                     values=["왼쪽", "중앙", "오른쪽"]).pack(side="left", padx=4)

        ttk.Label(pfrm, text="내 유튜브 채널 주소 (숏폼 설명, 고정댓글용)"
                  ).grid(row=16, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Entry(pfrm, textvariable=self.channel_url_var, width=66).grid(row=17, column=0,
                                                                          columnspan=2, sticky="w")

        cap_frame = ttk.LabelFrame(pfrm, text="인트로 자막 (영상 맨 앞부분에만 한 번 나왔다 사라짐, 자동 채워짐, 수정 가능)")
        caprow0 = ttk.Frame(cap_frame); caprow0.pack(fill="x", padx=8, pady=(4, 0))
        ttk.Checkbutton(caprow0, text="자막 넣지 않음 (체크하면 롱폼 패키지 생성 시 자막을 건너뜁니다)",
                        variable=self.skip_caption_var).pack(side="left")
        caprow1 = ttk.Frame(cap_frame); caprow1.pack(fill="x", padx=8, pady=(4, 2))
        ttk.Label(caprow1, text="한글:").pack(side="left")
        ttk.Entry(caprow1, textvariable=self.caption_kr_var, width=70,
                  font=("Malgun Gothic", 10)).pack(side="left", padx=4, fill="x", expand=True)
        caprow2 = ttk.Frame(cap_frame); caprow2.pack(fill="x", padx=8, pady=(2, 2))
        ttk.Label(caprow2, text="영문:").pack(side="left")
        ttk.Entry(caprow2, textvariable=self.caption_en_var, width=70,
                  font=("Malgun Gothic", 10)).pack(side="left", padx=4, fill="x", expand=True)
        caprow3 = ttk.Frame(cap_frame); caprow3.pack(fill="x", padx=8, pady=(2, 6))
        ttk.Label(caprow3, text="표시 시간(초):").pack(side="left")
        ttk.Spinbox(caprow3, from_=6, to=45, increment=1, textvariable=self.caption_sec_var,
                    width=5).pack(side="left", padx=4)
        self.caption_btn = ttk.Button(caprow3, text="지금 영상에 바로 자막 삽입 (검증 후 원본 교체)",
                                      command=self.run_add_caption)
        self.caption_btn.pack(side="left", padx=12)
        ttk.Label(cap_frame, text="롱폼 패키지 생성을 누르면(체크 없을 시) 자동으로 자막을 넣고, 검증 후 원본을 자막본으로 교체합니다",
                  foreground="#666666").pack(anchor="w", padx=8, pady=(0, 4))
        cap_frame.grid(row=18, column=0, columnspan=2, sticky="we", pady=(8, 0))

        st_frame = ttk.LabelFrame(pfrm, text="🌙 내레이션 이야기 (내레이션 영상을 고르면 자동 채움 · 비우면 생략)")
        strow1 = ttk.Frame(st_frame); strow1.pack(fill="x", padx=8, pady=(4, 2))
        ttk.Label(strow1, text="이야기 제목 (제목 부제목):").pack(side="left")
        ttk.Entry(strow1, textvariable=self.story_title_var, width=40,
                  font=("Malgun Gothic", 10)).pack(side="left", padx=4, fill="x", expand=True)
        strow2 = ttk.Frame(st_frame); strow2.pack(fill="x", padx=8, pady=(2, 6))
        ttk.Label(strow2, text="설명란 요약:").pack(side="left")
        ttk.Entry(strow2, textvariable=self.story_summary_var, width=48,
                  font=("Malgun Gothic", 10)).pack(side="left", padx=4, fill="x", expand=True)
        self.story_cnt_lbl = ttk.Label(strow2, text="0/50자", foreground="#666666")
        self.story_cnt_lbl.pack(side="left", padx=4)
        st_frame.grid(row=19, column=0, columnspan=2, sticky="we", pady=(8, 0))
        self.story_summary_var.trace_add("write", self._update_story_count)
        self.pkg_video_var.trace_add("write", self._load_story_for_pkg)

        pbtns = ttk.Frame(tab2); pbtns.pack(fill="x", **pad)
        self.pkg_btn = ttk.Button(pbtns, text="롱폼 패키지 생성 (썸네일 3종 + 제목 + 설명 + 태그)",
                                  command=lambda: self.make_package("long"))
        self.pkg_btn.pack(side="left", padx=4)
        self.shorts_btn = ttk.Button(pbtns, text="숏폼만 생성 (세로 영상 + 숏폼제목)",
                                     command=lambda: self.make_package("shorts"))
        self.shorts_btn.pack(side="left", padx=4)

        ttk.Label(tab2, text="생성물: 영상이름_youtube 폴더 -> thumb_1~3.png(A/B용), 제목.txt(2종), 설명.txt, 태그.txt(500자 검증)",
                  foreground="#666666", wraplength=600, justify="left").pack(anchor="w", padx=12, pady=(2, 6))

        tab3 = ttk.Frame(nb)
        nb.add(tab3, text="  오디오 정제  ")

        cfrm = ttk.Frame(tab3); cfrm.pack(fill="x", **pad)
        ttk.Label(cfrm, text="녹음 파일 (WAV/MP3 - 우산 녹음, 현장 녹음 등)"
                  ).grid(row=0, column=0, sticky="w")
        ttk.Entry(cfrm, textvariable=self.clean_in_var, width=58).grid(row=1, column=0, sticky="w")
        ttk.Button(cfrm, text="찾기", command=self.pick_clean_in).grid(row=1, column=1, padx=6)

        o1 = ttk.Frame(cfrm); o1.grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))
        ttk.Checkbutton(o1, text="이상 구간 자동 제거 (새, 차, 천둥, 쿵 등 일시적 잡음 구간을 잘라냄)",
                        variable=self.seg_var).pack(side="left")
        ttk.Label(o1, text="  감도:").pack(side="left")
        ttk.Combobox(o1, textvariable=self.sens_var, width=14, state="readonly",
                     values=list(AudioCleaner.SENS.keys())).pack(side="left", padx=4)

        o2 = ttk.Frame(cfrm); o2.grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Checkbutton(o2, text="우산 빗방울 뚝뚝 충격음 억제 (녹음 내내 섞인 타격음을 눌러줌)",
                        variable=self.declick_var).pack(side="left")
        ttk.Label(o2, text="  강도:").pack(side="left")
        ttk.Combobox(o2, textvariable=self.declick_str_var, width=8, state="readonly",
                     values=list(AudioCleaner.DECLICK.keys())).pack(side="left", padx=4)

        ttk.Checkbutton(cfrm, text="저음 럼블 제거 (80Hz 미만 - 바람, 차량 진동, 핸들링 노이즈)",
                        variable=self.rumble_var).grid(row=4, column=0, columnspan=2,
                                                       sticky="w", pady=(4, 0))

        o3 = ttk.Frame(cfrm); o3.grid(row=5, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Checkbutton(o3, text="음량 키우기 (녹음이 작을 때 - 찌그러짐 없이 최대로)",
                        variable=self.normalize_var).pack(side="left")
        ttk.Label(o3, text="  목표:").pack(side="left")
        ttk.Combobox(o3, textvariable=self.norm_level_var, width=16, state="readonly",
                     values=["적당히 (-3dB)", "크게 (-1.5dB)", "최대 (-0.5dB)"]).pack(side="left", padx=4)

        ttk.Label(cfrm, text="결과: 원본과 같은 폴더에 '파일이름_정제.wav' 로 저장됩니다",
                  foreground="#666666").grid(row=6, column=0, columnspan=2, sticky="w", pady=(10, 0))

        cbtns = ttk.Frame(tab3); cbtns.pack(fill="x", **pad)
        self.clean_btn = ttk.Button(cbtns, text="🎧 순수 빗소리 추출 시작", command=self.run_clean)
        self.clean_btn.pack(side="left", padx=4)

        # ===== 탭 4 (v11): 🌙 스토리 내레이션 =====
        tab4 = ttk.Frame(nb)
        nb.add(tab4, text="  🌙 스토리 내레이션  ")

        nfrm = ttk.Frame(tab4); nfrm.pack(fill="x", **pad)
        ttk.Label(nfrm, text="🎬 루프 완성 영상  (처음엔 [루프 영상 제작] 탭에서 '3분 (테스트)'로 만들어 시험해보세요)",
                  wraplength=620, justify="left").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Entry(nfrm, textvariable=self.narr_video_var, width=58).grid(row=1, column=0, sticky="w")
        ttk.Button(nfrm, text="찾기", command=self.pick_narr_video).grid(row=1, column=1, padx=6)

        ttk.Label(nfrm, text="🕯️ 이야기 소재·키워드 (선택 — 예: 야간열차, 오래된 호텔 / 비우면 Claude가 자유롭게 정해요)"
                  ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Entry(nfrm, textvariable=self.narr_hint_var, width=58).grid(row=3, column=0, sticky="w")
        tr = ttk.Frame(nfrm); tr.grid(row=6, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Label(tr, text="📖 이야기 제목:").pack(side="left")
        self.narr_title_cb4 = ttk.Combobox(tr, textvariable=self.narr_title_var, width=34,
                                           font=("Malgun Gothic", 10))
        self.narr_title_cb4.pack(side="left", padx=4)
        self.narr_title_btn4 = ttk.Button(tr, text="✨ 제목 후보 받기", command=self.narr_suggest_titles)
        self.narr_title_btn4.pack(side="left", padx=4)
        ttk.Label(nfrm, textvariable=self.narr_title_status, foreground="#666666"
                  ).grid(row=7, column=0, columnspan=2, sticky="w")
        sr = ttk.Frame(nfrm); sr.grid(row=8, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Label(sr, text="🔀 이야기 스타일:").pack(side="left")
        ttk.Combobox(sr, textvariable=self.narr_style_var, width=56, state="readonly",
                     values=list(NARR_STYLES)).pack(side="left", padx=4)
        ttk.Button(sr, text="📚 연재 목록 열기", command=self.open_classic_list).pack(side="left", padx=4)

        ttk.Label(nfrm, text="📄 이야기 파일 (선택 — 이미 만든 대본을 다른 성우로 다시 녹음할 때)"
                  ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Entry(nfrm, textvariable=self.narr_story_var, width=58).grid(row=5, column=0, sticky="w")
        ttk.Button(nfrm, text="찾기", command=self.pick_narr_story).grid(row=5, column=1, padx=6)
        ttk.Label(nfrm, text="🎙 외부 음성 파일 (선택 — Vrew 등에서 만든 mp3/wav · 넣으면 AI 녹음을 건너뛰어요)"
                  ).grid(row=9, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Entry(nfrm, textvariable=self.narr_ext_audio_var, width=58).grid(row=10, column=0, sticky="w")
        ttk.Button(nfrm, text="찾기", command=self.pick_narr_ext_audio).grid(row=10, column=1, padx=6)

        vfrm = ttk.Frame(tab4); vfrm.pack(fill="x", padx=10, pady=(6, 2))
        mbox = ttk.LabelFrame(vfrm, text=" 🎙 남성 성우 ")
        fbox = ttk.LabelFrame(vfrm, text=" 🎙 여성 성우 ")
        mbox.pack(side="left", fill="both", expand=True, padx=(0, 4))
        fbox.pack(side="left", fill="both", expand=True, padx=(4, 0))
        for v in NARR_VOICES:
            box = mbox if v[1] == "남" else fbox
            ttk.Radiobutton(box, text=v[0], value=v[0], variable=self.narr_voice_var
                            ).pack(anchor="w", padx=6, pady=2)

        efrm = ttk.LabelFrame(tab4, text=" 🔊 음성 엔진 ")
        efrm.pack(fill="x", padx=10, pady=(4, 2))
        er1 = ttk.Frame(efrm); er1.pack(fill="x", padx=8, pady=(4, 2))
        ecb = ttk.Combobox(er1, textvariable=self.tts_engine_var, width=44, state="readonly",
                           values=list(NARR_ENGINES.keys()))
        ecb.pack(side="left")
        ecb.bind("<<ComboboxSelected>>", lambda e: self.save_tts_settings(quiet=True))
        er2 = ttk.Frame(efrm); er2.pack(fill="x", padx=8, pady=(2, 2))
        ttk.Label(er2, text="Azure 키:").pack(side="left")
        ttk.Entry(er2, textvariable=self.azure_key_var, width=34, show="•").pack(side="left", padx=4)
        ttk.Label(er2, text="지역:").pack(side="left")
        ttk.Entry(er2, textvariable=self.azure_region_var, width=13).pack(side="left", padx=4)
        ttk.Button(er2, text="저장", command=self.save_tts_settings).pack(side="left", padx=4)
        ttk.Label(efrm, text="★ 성우(봉진·지민·순복)는 Azure 모드에서 진짜 각자 목소리 / 무료 모드에선 인준·선희 톤을 바꿔 대신 읽어요.\n"
                             "  키는 이 PC의 사용자 폴더(.loopmaker_tts.json)에만 저장돼요.",
                  foreground="#666666", wraplength=620, justify="left").pack(anchor="w", padx=8, pady=(0, 4))

        pfrm = ttk.Frame(tab4); pfrm.pack(fill="x", padx=10, pady=(2, 2))
        self.narr_prev_btn = ttk.Button(pfrm, text="▶ 선택한 성우 미리 듣기", command=self.narr_preview)
        self.narr_prev_btn.pack(side="left", padx=2)
        self.narr_all_btn = ttk.Button(pfrm, text="🎧 6명 모두 비교 듣기", command=self.narr_preview_all)
        self.narr_all_btn.pack(side="left", padx=6)

        ofrm = ttk.Frame(tab4); ofrm.pack(fill="x", padx=10, pady=(4, 0))
        ttk.Label(ofrm, text="읽기 속도").grid(row=0, column=0, sticky="w")
        ttk.Combobox(ofrm, textvariable=self.narr_speed_var, width=16, state="readonly",
                     values=list(NARR_SPEED.keys())).grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(ofrm, text="말할 때 빗소리 줄이기").grid(row=0, column=2, sticky="w", padx=(12, 0))
        ttk.Combobox(ofrm, textvariable=self.narr_duck_var, width=22, state="readonly",
                     values=list(NARR_DUCK.keys())).grid(row=0, column=3, sticky="w", padx=4)
        ttk.Label(ofrm, text="이야기 길이").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Combobox(ofrm, textvariable=self.narr_len_var, width=30, state="readonly",
                     values=[n for n, _ in NARR_LEN]).grid(row=1, column=1, columnspan=2, sticky="w",
                                                            padx=4, pady=(4, 0))
        sf = ttk.Frame(ofrm); sf.grid(row=1, column=3, sticky="w", pady=(4, 0))
        ttk.Label(sf, text="시작 전 빗소리만(초)").pack(side="left")
        ttk.Spinbox(sf, from_=0, to=120, increment=1, width=5,
                    textvariable=self.narr_start_var).pack(side="left", padx=4)
        tnf = ttk.Frame(ofrm); tnf.grid(row=3, column=0, columnspan=4, sticky="w", pady=(4, 0))
        ttk.Label(tnf, text="🧓 목소리 톤").pack(side="left")
        ttk.Combobox(tnf, textvariable=self.narr_tone_var, width=40, state="readonly",
                     values=list(NARR_TONES)).pack(side="left", padx=4)
        tf = ttk.Frame(ofrm); tf.grid(row=2, column=0, columnspan=4, sticky="w", pady=(4, 0))
        ttk.Label(tf, text="🎬 영상 첫 부분에 이야기 제목 표시(초, 0=표시 안 함)").pack(side="left")
        ttk.Spinbox(tf, from_=0, to=15, increment=1, width=5,
                    textvariable=self.narr_title_sec_var).pack(side="left", padx=4)

        nbtns = ttk.Frame(tab4); nbtns.pack(fill="x", padx=10, pady=(8, 2))
        self.narr_btn = ttk.Button(nbtns, text="🌙 이야기 만들고 녹음해서 영상에 넣기", command=self.run_narration)
        self.narr_btn.pack(side="left", padx=2)
        self.narr_script_btn = ttk.Button(nbtns, text="📝 대본만 만들기 (Vrew용)", command=self.run_script_only)
        self.narr_script_btn.pack(side="left", padx=6)
        self.narr_stop_btn = ttk.Button(nbtns, text="⏹ 중지", command=self.stop_narration, state="disabled")
        self.narr_stop_btn.pack(side="left", padx=6)

        ttk.Label(tab4, text="결과: 영상이름_내레이션_성우.mp4  +  영상이름_story 폴더 (이야기_대본.txt, 자막.srt, 내레이션.wav)\n"
                             "* 다국어 성우는 한국어를 읽지만 억양이 살짝 다를 수 있어요 — 꼭 미리 들어보고 고르세요",
                  foreground="#666666", wraplength=620, justify="left").pack(anchor="w", padx=12, pady=(2, 6))

        # ===== 공통 영역: 진행 로그 (모든 탭이 함께 사용) =====
        logf = ttk.LabelFrame(self, text=" 진행 상황 ")
        logf.pack(fill="both", expand=True, padx=10, pady=(8, 10))
        self.log_box = tk.Text(logf, height=16, wrap="word", state="disabled",
                               font=("Consolas", 9), background="#1e1e1e",
                               foreground="#e6e6e6", insertbackground="#e6e6e6",
                               relief="flat", padx=6, pady=4)
        logsb = ttk.Scrollbar(logf, orient="vertical", command=self.log_box.yview)
        self.log_box.configure(yscrollcommand=logsb.set)
        logsb.pack(side="right", fill="y")
        self.log_box.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)

        self._install_edit_support()

    # ---------- v11: 🌙 스토리 내레이션 ----------
    def _update_story_count(self, *_):
        n = len(self.story_summary_var.get().strip())
        self.story_cnt_lbl.configure(text=f"{n}/{STORY_SUMMARY_MAX}자" + (" ⚠️ 초과분은 자동으로 줄여요" if n > STORY_SUMMARY_MAX else ""),
                                     foreground="#c0392b" if n > STORY_SUMMARY_MAX else "#666666")

    def _load_story_for_pkg(self, *_):
        """유튜브 패키지 탭 영상이 바뀌면 짝이 되는 이야기 정보를 자동으로 채운다
        (메인 스레드의 trace에서만 호출됨)"""
        info = load_story_info(self.pkg_video_var.get().strip()) or {}
        self.story_meta = info
        self.story_title_var.set(info.get("title", ""))
        self.story_summary_var.set(info.get("summary", ""))
        if info:
            self.log(f"🌙 이 영상의 이야기를 찾았어요: 「{info.get('title', '')}」 — 제목 부제목·설명란에 들어갑니다")

    def pick_narr_video(self):
        p = filedialog.askopenfilename(filetypes=[("영상", "*.mp4 *.mov *.mkv"), ("모든 파일", "*.*")])
        if p:
            self.narr_video_var.set(p)

    def run_script_only(self):
        """📝 녹음 없이 대본만 만들어 C:\\LoopMaker\\대본 폴더에 저장 (Vrew 등에 붙여넣기용)"""
        style = NARR_STYLES.get(self.narr_style_var.get(), "classic")
        len_sec = dict(NARR_LEN).get(self.narr_len_var.get(), 0)
        video = self.narr_video_var.get().strip()
        hint = self.narr_hint_var.get().strip()
        title_fixed = self.narr_title_var.get().strip()
        tone = self.narr_tone_var.get()
        self._narr_buttons(True)
        self.narr_stop_flag.clear()
        self.log("\n📝 대본만 만들기 시작 (녹음은 하지 않아요)")

        def work():
            tmp = tempfile.mkdtemp(prefix="script_")
            try:
                nar = StoryNarrator(self.log, self.narr_stop_flag)
                nar.tone_key = tone
                target = len_sec
                if target <= 0:
                    vdur = nar.probe_duration(video) if video and os.path.exists(video) else 0
                    target = (vdur - 26) if 0 < vdur <= 3600 else (min(3 * 3600.0, vdur * 0.5) if vdur else 3600.0)
                    self.log(f"  ℹ️ 길이 자동: 약 {target/60:.0f}분 분량")
                vid = video if video and os.path.exists(video) else ""
                title, bible, text, eps = nar.write_long_story(vid, hint, target, tmp,
                                                               fixed_title=title_fixed, style=style)
                d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "대본")
                os.makedirs(d, exist_ok=True)
                safe = re.sub(r'[\\/:*?"<>|]', "", title)[:30]
                path = os.path.join(d, time.strftime("%m%d_%H%M_") + safe + ".txt")
                clean = re.sub(r"\[\[EP:.*?\]\]\n*", "", text)       # Vrew에 붙여넣을 순수 낭독문
                with open(path, "w", encoding="utf-8") as f:
                    f.write(f"제목: {title}\n\n{clean}\n")
                with open(path[:-4] + "_설정.txt", "w", encoding="utf-8") as f:
                    f.write(bible)
                info = {"title": title, "summary": fit_summary(nar.summary), "episodes_titles": eps}
                with open(os.path.join(d, "story_info.json"), "w", encoding="utf-8") as f:
                    json.dump(info, f, ensure_ascii=False, indent=2)
                if getattr(nar, "classic_state_pending", None):
                    save_classic_state(nar.classic_state_pending)
                    self.log(f"  📚 연재 진행 상태 저장 — {classic_status_text()}")
                self.log(f"\n✅ 대본 완성: {path}\n   ({len(clean):,}자 · Vrew에는 '제목:' 줄을 빼고 붙여넣으세요)\n"
                         f"   → Vrew에서 mp3로 내보낸 뒤, 이 파일을 [이야기 파일]에, mp3를 [외부 음성 파일]에 넣으면 돼요")
                self._open_path(path)
            except InterruptedError:
                self.log("\n⏹ 중지되었습니다")
            except Exception as ex:
                self.log(f"\n❌ 대본 만들기 실패: {ex}")
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
                self.log_q.put("__NARR_DONE__")

        threading.Thread(target=work, daemon=True).start()

    def open_classic_list(self):
        try:
            style = NARR_STYLES.get(self.narr_style_var.get(), "classic")
            if not is_lib_style(style):
                self.log("ℹ️ 이 스타일은 매번 새로 지어내는 이야기라 연재 목록이 없어요 "
                         "(영상 분위기·키워드 칸에 원하는 소재를 적으면 반영돼요)")
                return
            set_active_lib(style)
            classic_queue()          # 없으면 기본 목록을 만들어 줌
            self.log("📚 " + classic_status_text())
            self._open_path(_lib()["list"])
        except Exception as ex:
            self.log(f"❌ 명작 목록을 열지 못했어요: {ex}")

    def pick_narr_ext_audio(self):
        p = filedialog.askopenfilename(filetypes=[("음성", "*.mp3 *.wav *.m4a *.aac *.flac"), ("모든 파일", "*.*")])
        if p:
            self.narr_ext_audio_var.set(p)

    def pick_narr_story(self):
        p = filedialog.askopenfilename(filetypes=[("텍스트", "*.txt"), ("모든 파일", "*.*")])
        if p:
            self.narr_story_var.set(p)

    @staticmethod
    def _open_path(path):
        try:
            if os.name == "nt":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass

    def _narr_title_sec(self):
        try:
            return max(0.0, min(15.0, float(self.narr_title_sec_var.get())))
        except (tk.TclError, ValueError):
            return 5.0

    def _caption_delay_for(self, video):
        """이야기 제목 카드가 있는 영상이면 인트로 자막이 제목과 겹치지 않게 그 뒤에 나오도록"""
        sec = float((load_story_info(video) or {}).get("title_card_sec") or 0)
        if sec > 0:
            self.log(f"  ℹ️ 앞 {sec:.0f}초의 이야기 제목이 끝난 뒤에 인트로 자막이 나오도록 조정합니다")
            return sec + 0.5
        return 0.0

    def save_tts_settings(self, quiet=False):
        eng = NARR_ENGINES.get(self.tts_engine_var.get(), "edge")
        key = self.azure_key_var.get().strip()
        if eng == "azure" and not key:
            if not quiet:
                messagebox.showwarning("확인", "Azure 모드를 쓰려면 Azure Speech 키를 입력해주세요")
            self.log("⚠️ Azure 키가 없어 무료 Edge 음성으로 녹음됩니다 (키 입력 후 [저장])")
        try:
            save_tts_config({"engine": eng, "azure_key": key,
                             "azure_region": self.azure_region_var.get().strip() or "koreacentral"})
            if not quiet or eng == "edge" or key:
                self.log(f"🔊 음성 엔진 저장: {self.tts_engine_var.get()}")
        except Exception as ex:
            self.log(f"❌ 음성 설정 저장 실패: {ex}")

    def narr_suggest_titles(self):
        """✨ 제목 후보 3개를 Claude에게 미리 받아 콤보박스에 채운다"""
        video = self.narr_video_var.get().strip() or self.video_var.get().strip()
        hint = self.narr_hint_var.get().strip()
        style = NARR_STYLES.get(self.narr_style_var.get(), "twist")
        if (style == "cozy" or style.startswith("calm:")) and not hint and (not video or not os.path.exists(video)):
            messagebox.showwarning("확인", "원본 영상을 먼저 선택하거나, [🌙 스토리 내레이션] 탭에 분위기·키워드를 적어주세요")
            return
        for b in (self.narr_title_btn1, self.narr_title_btn4):
            b.configure(state="disabled")
        self.narr_title_status.set("⏳ Claude가 장면을 보고 제목을 짓는 중... (30초~1분)")
        self.log("\n✨ 이야기 제목 후보를 받는 중...")

        def work():
            tmp = tempfile.mkdtemp(prefix="narr_title_")
            try:
                titles = StoryNarrator(self.log, threading.Event()).suggest_titles(video, hint, tmp, style=style)
                self.log("  ✅ 제목 후보: " + " / ".join(f"「{t}」" for t in titles))
                self.log_q.put(("__NARR_TITLES__", titles))
            except FileNotFoundError:
                self.log("  ❌ 'claude' 명령을 찾을 수 없습니다 — 제목 칸에 직접 입력해주세요")
                self.log_q.put(("__NARR_TITLE_STATUS__", "❌ Claude 연결 실패 — 직접 입력하거나 비워두세요"))
            except Exception as ex:
                self.log(f"  ❌ 제목 후보 받기 실패: {ex}")
                self.log_q.put(("__NARR_TITLE_STATUS__", "❌ 실패 — 직접 입력하거나 비워두세요"))
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
                self.log_q.put(("__NARR_TITLE_BTN__", None))

        threading.Thread(target=work, daemon=True).start()

    def _narr_on_title(self, title):
        """백그라운드 스레드에서 실제로 쓰인 제목을 알려오면 큐로 화면에 반영"""
        self.log_q.put(("__NARR_TITLE_USED__", title))

    def _narr_buttons(self, busy):
        st = "disabled" if busy else "normal"
        for b in (self.narr_btn, self.narr_prev_btn, self.narr_all_btn, self.narr_script_btn):
            b.configure(state=st)
        self.narr_stop_btn.configure(state="normal" if busy else "disabled")

    def narr_preview(self):
        label, speed = self.narr_voice_var.get(), self.narr_speed_var.get()
        tone = self.narr_tone_var.get()
        self._narr_buttons(True)
        self.narr_stop_flag.clear()
        self.log(f"\n▶ 미리 듣기 준비 중: {label}")

        def work():
            try:
                nar = StoryNarrator(self.log, self.narr_stop_flag)
                d = os.path.join(tempfile.gettempdir(), "LoopMaker_성우샘플")
                os.makedirs(d, exist_ok=True)
                out = os.path.join(d, label.split("—")[0].replace("·", "").replace(" ", "") + ".mp3")
                spec = nar.preview(label, speed, out, tone=tone)
                self.log(f"  ✅ 재생합니다 ({spec['voice']})")
                self._open_path(out)
            except Exception as ex:
                self.log(f"  ❌ 미리 듣기 실패: {ex}")
            finally:
                self.log_q.put("__NARR_DONE__")

        threading.Thread(target=work, daemon=True).start()

    def narr_preview_all(self):
        speed = self.narr_speed_var.get()
        tone = self.narr_tone_var.get()
        self._narr_buttons(True)
        self.narr_stop_flag.clear()
        self.log("\n🎧 성우 6명 샘플을 만드는 중... (완료되면 폴더가 열려요)")

        def work():
            try:
                nar = StoryNarrator(self.log, self.narr_stop_flag)
                d = os.path.join(tempfile.gettempdir(), "LoopMaker_성우샘플")
                os.makedirs(d, exist_ok=True)
                for i, v in enumerate(NARR_VOICES, 1):
                    name = f"{i}_" + v[0].split("—")[0].replace("·", "").replace(" ", "") + ".mp3"
                    try:
                        spec = nar.preview(v[0], speed, os.path.join(d, name), tone=tone)
                        self.log(f"  ✅ {name}  ({spec['voice']})")
                    except Exception as ex:
                        self.log(f"  ❌ {name}: {ex}")
                self._open_path(d)
            except Exception as ex:
                self.log(f"  ❌ 샘플 생성 실패: {ex}")
            finally:
                self.log_q.put("__NARR_DONE__")

        threading.Thread(target=work, daemon=True).start()

    def run_narration(self):
        video = self.narr_video_var.get().strip()
        if not video or not os.path.exists(video):
            messagebox.showwarning("확인", "내레이션을 넣을 루프 영상을 선택해주세요\n"
                                         "(먼저 [루프 영상 제작] 탭에서 '3분 (테스트)'로 만들어 보세요)")
            return
        try:
            start_sec = float(self.narr_start_var.get())
        except (tk.TclError, ValueError):
            start_sec = 6.0
        args = dict(video=video, voice_label=self.narr_voice_var.get(), speed_key=self.narr_speed_var.get(),
                    duck_key=self.narr_duck_var.get(), len_sec=dict(NARR_LEN).get(self.narr_len_var.get(), 0),
                    start_sec=max(0.0, start_sec), hint=self.narr_hint_var.get().strip(),
                    story_file=self.narr_story_var.get().strip(),
                    ext_audio=self.narr_ext_audio_var.get().strip(),
                    story_title=self.narr_title_var.get().strip(), on_title=self._narr_on_title,
                    style=NARR_STYLES.get(self.narr_style_var.get(), "twist"),
                    title_sec=self._narr_title_sec(), tone=self.narr_tone_var.get())
        self._narr_buttons(True)
        self.narr_stop_flag.clear()
        self.log(f"\n🌙 스토리 내레이션 시작 — 성우: {args['voice_label']}")
        self.narrator = StoryNarrator(self.log, self.narr_stop_flag)

        def work():
            try:
                out = self.narrator.run(**args)
                if out:
                    self.log_q.put(("__NARR_RESULT__", out))
            except InterruptedError:
                self.log("\n⏹ 중지되었습니다")
            except Exception as ex:
                self.log(f"\n❌ 내레이션 오류: {ex}")
            finally:
                self.log_q.put("__NARR_DONE__")

        threading.Thread(target=work, daemon=True).start()

    def stop_narration(self):
        self.narr_stop_flag.set()
        if getattr(self, "narrator", None):
            self.narrator.kill()
        self.log("  ⏹ 중지 요청됨 — 진행 중인 단계가 끝나는 대로 멈춥니다")

    # ---------- 파일 선택 ----------
    def pick_video(self):
        p = filedialog.askopenfilename(filetypes=[("영상", "*.mp4 *.mov *.mkv *.webm"), ("모든 파일", "*.*")])
        if p:
            self.video_var.set(p)
            # 새 영상이면 이전 이야기 제목이 딸려가지 않도록 비움
            self.narr_title_var.set("")
            for cb in (self.narr_title_cb1, self.narr_title_cb4):
                cb.configure(values=[])
            self.narr_title_status.set("비워두면 Claude가 영상 장면을 보고 직접 지어요")

    def pick_audio(self):
        p = filedialog.askopenfilename(filetypes=[("오디오", "*.wav *.mp3 *.m4a *.aac *.flac"), ("모든 파일", "*.*")])
        if p:
            self.audio_var.set(p)

    def pick_outdir(self):
        p = filedialog.askdirectory()
        if p:
            self.outdir_var.set(p)

    def pick_pkg_video(self):
        p = filedialog.askopenfilename(filetypes=[("영상", "*.mp4 *.mov *.mkv"), ("모든 파일", "*.*")])
        if p:
            self.pkg_video_var.set(p)
            self._reset_claude_scene_data()

    def _reset_claude_scene_data(self):
        """v9.7: 새 영상을 선택하면 이전 영상의 Claude 자동 분석 결과(장면 묘사/설명란
        도입부)가 그대로 남아 다른 영상 설명에 잘못 쓰이지 않도록 비워준다."""
        self.scene_en_var.set("")
        self.scene_kr_var.set("")
        self.desc_en_var.set("")
        self.desc_kr_var.set("")
        self.caption_kr_var.set("")
        self.caption_en_var.set("")

    def pick_clean_in(self):
        p = filedialog.askopenfilename(filetypes=[("오디오", "*.wav *.mp3 *.m4a *.aac *.flac"),
                                                  ("모든 파일", "*.*")])
        if p:
            self.clean_in_var.set(p)

    def run_clean(self):
        path = self.clean_in_var.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showwarning("확인", "녹음 파일을 선택해주세요")
            return
        if not any([self.seg_var.get(), self.declick_var.get(),
                    self.rumble_var.get(), self.normalize_var.get()]):
            messagebox.showwarning("확인", "적용할 정제 옵션을 하나 이상 선택해주세요")
            return
        base, _ = os.path.splitext(path)
        out_path = base + "_정제.wav"
        sens = self.sens_var.get() if self.seg_var.get() else "둔감 (적게 제거)"
        # 구간 제거 끄면 감도를 사실상 무효화하기 위해 매우 높은 임계 사용
        declick = self.declick_str_var.get() if self.declick_var.get() else None
        rumble = self.rumble_var.get()
        seg_on = self.seg_var.get()
        normalize = self.norm_level_var.get() if self.normalize_var.get() else None

        self.clean_btn.configure(state="disabled")
        self.log("\n🎧 순수 빗소리 추출 시작...\n")

        def work():
            try:
                cleaner = AudioCleaner(self.log, self.stop_flag)
                if not seg_on:
                    cleaner.SENS = dict(cleaner.SENS)
                    cleaner.SENS[sens] = 999.0    # 구간 제거 비활성화
                cleaner.clean(path, out_path, sens, rumble=rumble, declick=declick,
                              normalize=normalize)
                # ★ v9.7 버그 수정: 백그라운드 스레드에서 tkinter StringVar.set()을
                # 직접 호출하면 "main thread is not in main loop" 오류가 날 수 있음 —
                # 큐에 담아 _poll_log(메인 스레드)가 대신 반영하게 한다.
                self.log_q.put(("__AUDIO_VAR_SET__", out_path))
                self.log("\n💡 [루프 영상 제작] 탭 오디오 칸에 정제본이 자동 입력되었습니다.")
            except Exception as ex:
                self.log(f"\n❌ 정제 오류: {ex}")
            finally:
                self.log_q.put("__CLEAN_DONE__")

        threading.Thread(target=work, daemon=True).start()

    def pick_pkg_outdir(self):
        p = filedialog.askdirectory()
        if p:
            self.pkg_outdir_var.set(p)

    # ---------- v9.6: Claude 자동 분석 ----------
    def run_claude_analysis(self):
        video = self.pkg_video_var.get().strip()
        if not video or not os.path.exists(video):
            messagebox.showwarning("확인", "먼저 완성된 루프 영상을 선택해주세요")
            return

        self.claude_btn.configure(state="disabled")
        self.claude_status_var.set("⏳ 분석 중... (최대 2분 정도 걸릴 수 있어요)")
        self.log("\n🤖 Claude 자동 분석 시작 (영상 내용 파악 + 실시간 검색)...")

        def work():
            try:
                data = call_claude_scene_analysis(video, self.log)
                # ★ v9.6 버그 수정: 백그라운드 스레드에서 tkinter StringVar.set()을 직접
                # 호출하면 "main thread is not in main loop" 오류가 남 (tkinter는
                # 메인 스레드에서만 건드릴 수 있음). self.log()처럼 큐에 담아서
                # _poll_log(메인 스레드, self.after로 주기 실행)가 대신 반영하게 한다.
                self.log_q.put(("__CLAUDE_RESULT__", data))
                self.log(f"  ✅ 자동 분석 완료 — 주제: {data.get('topic_kr')} / {data.get('topic_en')}"
                         f"\n     (마음에 안 들면 위 칸에서 바로 수정하시면 됩니다)")
                self.log_q.put("__CLAUDE_STATUS__:✅ 분석 완료 — 아래 칸에서 확인/수정하세요")
            except subprocess.TimeoutExpired:
                self.log("\n❌ Claude 분석 시간 초과 — 네트워크 상태를 확인하고 다시 시도해주세요")
                self.log_q.put("__CLAUDE_STATUS__:❌ 시간 초과 — 다시 시도해주세요")
            except FileNotFoundError:
                self.log("\n❌ 'claude' 명령을 찾을 수 없습니다 — Claude Code가 설치되어 PATH에 있는지 확인해주세요")
                self.log_q.put("__CLAUDE_STATUS__:❌ claude 명령을 찾을 수 없음")
            except Exception as ex:
                self.log(f"\n❌ 자동 분석 오류: {ex}")
                self.log_q.put("__CLAUDE_STATUS__:❌ 분석 실패 — 로그 확인 또는 직접 입력")
            finally:
                self.log_q.put("__CLAUDE_DONE__")

        threading.Thread(target=work, daemon=True).start()

    def _apply_claude_result(self, data):
        """Claude 자동 분석 결과를 화면에 반영 — 반드시 메인 스레드(_poll_log)에서만 호출."""
        self.custom_en_var.set(data.get("topic_en", ""))
        self.custom_kr_var.set(data.get("topic_kr", ""))
        self.scene_en_var.set(data.get("scene_en", ""))
        self.scene_kr_var.set(data.get("scene_kr", ""))
        self.desc_en_var.set(data.get("description_en", ""))
        self.desc_kr_var.set(data.get("description_kr", ""))
        self.caption_kr_var.set(data.get("scene_kr", ""))
        self.caption_en_var.set(data.get("scene_en", ""))
        self.custom_tags_var.set(", ".join(data.get("extra_tags", []) or []))

        thumbs = data.get("thumbnails", []) or []
        thumb_vars = [(self.thumb_text_var, self.sub_text_var),
                      (self.thumb2_var, self.sub2_var),
                      (self.thumb3_var, self.sub3_var)]
        for (mv, sv), th in zip(thumb_vars, thumbs):
            if th.get("main"):
                mv.set(th["main"])
            if th.get("sub"):
                sv.set(th["sub"])

    # ---------- v9.7: 인트로 자막 삽입 ----------
    def run_add_caption(self):
        video = self.pkg_video_var.get().strip()
        if not video or not os.path.exists(video):
            messagebox.showwarning("확인", "완성된 루프 영상을 선택해주세요")
            return
        cap_kr = self.caption_kr_var.get().strip()
        cap_en = self.caption_en_var.get().strip()
        if not cap_kr and not cap_en:
            messagebox.showwarning("확인", "자막으로 넣을 한글 또는 영문 문구를 입력해주세요\n"
                                          "(위의 'Claude로 자동 분석'을 먼저 실행하면 자동으로 채워집니다)")
            return
        try:
            cap_sec = float(self.caption_sec_var.get())
        except Exception:
            cap_sec = 14.0

        self.caption_btn.configure(state="disabled")
        self.log(f"\n📝 인트로 자막 삽입 시작...\n📁 대상: {video}")

        def work():
            try:
                tmp = tempfile.mkdtemp(prefix="caption_")
                pipe = Pipeline(self.log, threading.Event())
                try:
                    # v10: 빠른 제자리 방식 우선, 안 되면 기존 방식 + 검증 후 원본 교체
                    how = pipe.insert_intro_caption(video, cap_kr, cap_en, tmp,
                                                    caption_sec=cap_sec,
                                                    delay=self._caption_delay_for(video))
                    if how == "slow_kept":
                        self.log("\n⚠️ 자막본 검증에 실패해 원본은 그대로 두었습니다 (위 로그의 자막본 파일 참고)")
                    else:
                        self.log(f"\n🎉 완료! 자막이 들어간 영상으로 교체되었습니다 "
                                 f"(파일이 2벌 남지 않음)\n📁 {video}")
                finally:
                    shutil.rmtree(tmp, ignore_errors=True)
            except Exception as ex:
                self.log(f"\n❌ 자막 삽입 오류: {ex}")
            finally:
                self.log_q.put("__CAPTION_DONE__")

        threading.Thread(target=work, daemon=True).start()

    def _auto_translate_topic(self, *_):
        """한글 주제를 입력하면 영어 칸을 자동으로 채움 (사용자가 직접 쓴 영어는 보존)"""
        kr = self.custom_kr_var.get().strip()
        en_now = self.custom_en_var.get().strip()
        if not kr:
            return
        auto = ko_to_en_topic(kr)
        if auto and (not en_now or en_now == self._last_auto_en):
            self.custom_en_var.set(auto)
            self._last_auto_en = auto

    def _auto_fill_thumb(self, *_):
        """썸네일 1=한글ㅣ영어, 2=영어, 3=한글 자동 배치 (수정한 칸은 보존)"""
        en = self.custom_en_var.get().strip()
        kr = self.custom_kr_var.get().strip()
        if not (en or kr):
            return
        autos = [
            (self.thumb_text_var, (f"{kr}ㅣ{en.upper()}" if en and kr else (en.upper() or kr))),
            (self.thumb2_var, en.upper()),
            (self.thumb3_var, kr),
        ]
        if not hasattr(self, "_last_autos"):
            self._last_autos = ["", "", ""]
        for idx, (var, auto) in enumerate(autos):
            now = var.get().strip()
            if auto and (not now or now == self._last_autos[idx]):
                var.set(auto)
                self._last_autos[idx] = auto

    def _on_unit_change(self, *_):
        if self.loop_unit_var.get().startswith("단위 반복"):
            self._unit_detail.pack(fill="x", padx=24, pady=(0, 4))
        else:
            self._unit_detail.pack_forget()

    # ---------- 로그 ----------
    def log(self, msg):
        self.log_q.put(msg)

    # ---------- 입력란 편집 지원 (v8.4): 한글 상태에서도 Ctrl+C/V/X/A + 우클릭 메뉴 ----------
    def _install_edit_support(self):
        for cls in ("TEntry", "Entry", "TCombobox"):
            self.bind_class(cls, "<Control-KeyPress>", self._ctrl_edit_key, add="+")
            self.bind_class(cls, "<Button-3>", self._show_edit_menu, add="+")

        self._edit_menu = tk.Menu(self, tearoff=0)
        self._edit_menu.add_command(label="잘라내기 (Ctrl+X)", command=lambda: self._edit_do("cut"))
        self._edit_menu.add_command(label="복사 (Ctrl+C)", command=lambda: self._edit_do("copy"))
        self._edit_menu.add_command(label="붙여넣기 (Ctrl+V)", command=lambda: self._edit_do("paste"))
        self._edit_menu.add_separator()
        self._edit_menu.add_command(label="전체 선택 (Ctrl+A)", command=lambda: self._edit_do("all"))
        self._menu_widget = None

    # ---------- v10 재구성: 원본에 정확한 코드가 없어 동일 목적(입력칸 우클릭/단축키
    # 편집 지원)으로 새로 작성한 부분 ----------
    def _ctrl_edit_key(self, event):
        w = event.widget
        key = event.keysym.lower()
        # ★ v11.16: 한글 입력 상태에서는 Ctrl+V가 'v'가 아니라 'ㅍ' 등으로 들어와 붙여넣기가
        #   안 되던 문제 → 자판 위치(키코드)로도 판별 (Windows: A=65, C=67, V=86, X=88)
        kc = {65: "a", 67: "c", 86: "v", 88: "x"}.get(getattr(event, "keycode", 0))
        if kc and key not in ("a", "c", "v", "x"):
            key = kc
        if key == "c":
            return self._edit_do("copy", w)
        if key == "x":
            return self._edit_do("cut", w)
        if key == "v":
            return self._edit_do("paste", w)
        if key == "a":
            return self._edit_do("all", w)

    def _show_edit_menu(self, event):
        w = event.widget
        try:
            w.focus_set()
        except Exception:
            pass
        self._menu_widget = w
        try:
            self._edit_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._edit_menu.grab_release()

    def _edit_do(self, action, widget=None):
        w = widget or self._menu_widget or self.focus_get()
        if w is None:
            return
        try:
            if action == "copy":
                w.event_generate("<<Copy>>")
            elif action == "cut":
                w.event_generate("<<Cut>>")
            elif action == "paste":
                w.event_generate("<<Paste>>")
            elif action == "all":
                if hasattr(w, "select_range"):
                    w.select_range(0, "end")
                    w.icursor("end")
        except Exception:
            pass
        return "break"

    def _poll_log(self):
        try:
            while True:
                msg = self.log_q.get_nowait()
                if isinstance(msg, tuple) and str(msg[0]).startswith("__SM_"):
                    self._sm_handle(msg)
                    continue
                if msg == "__DONE__":
                    # 작업 완료 → 버튼 상태 복구 (연속 작업 가능)
                    self.start_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
                    if self.last_output:
                        self.pkg_video_var.set(self.last_output)
                        if "_내레이션_" not in os.path.basename(self.last_output):
                            self.narr_video_var.set(self.last_output)
                        self._reset_claude_scene_data()
                    continue
                if isinstance(msg, tuple) and msg[0] == "__NARR_TITLES__":
                    for cb in (self.narr_title_cb1, self.narr_title_cb4):
                        cb.configure(values=msg[1])
                    self.narr_title_var.set(msg[1][0])
                    self.narr_title_status.set("▼ 눌러서 다른 후보 선택 · 직접 고쳐 써도 돼요 · 이 제목으로 이야기를 써요")
                    continue
                if isinstance(msg, tuple) and msg[0] == "__NARR_TITLE_STATUS__":
                    self.narr_title_status.set(msg[1])
                    continue
                if isinstance(msg, tuple) and msg[0] == "__NARR_TITLE_BTN__":
                    for b in (self.narr_title_btn1, self.narr_title_btn4):
                        b.configure(state="normal")
                    continue
                if isinstance(msg, tuple) and msg[0] == "__NARR_TITLE_USED__":
                    self.narr_title_var.set(msg[1])
                    self.narr_title_status.set(f"✅ 이번 영상 이야기: 「{msg[1]}」 (다음 영상 전에 비우면 새로 지어요)")
                    continue
                if isinstance(msg, tuple) and msg[0] == "__NARR_RESULT__":
                    self.pkg_video_var.set(msg[1])
                    self._reset_claude_scene_data()
                    continue
                if msg == "__NARR_DONE__":
                    self._narr_buttons(False)
                    continue
                if msg == "__CLEAN_DONE__":
                    self.clean_btn.configure(state="normal")
                    continue
                if isinstance(msg, tuple) and msg[0] == "__AUDIO_VAR_SET__":
                    self.audio_var.set(msg[1])
                    continue
                if msg == "__PKG_DONE__":
                    self.pkg_btn.configure(state="normal")
                    self.shorts_btn.configure(state="normal")
                    continue
                if msg == "__CLAUDE_DONE__":
                    self.claude_btn.configure(state="normal")
                    continue
                if msg == "__CAPTION_DONE__":
                    self.caption_btn.configure(state="normal")
                    continue
                if isinstance(msg, str) and msg.startswith("__CLAUDE_STATUS__:"):
                    self.claude_status_var.set(msg[len("__CLAUDE_STATUS__:"):])
                    continue
                if isinstance(msg, tuple) and msg[0] == "__CLAUDE_RESULT__":
                    self._apply_claude_result(msg[1])
                    continue
                self.log_box.configure(state="normal")
                self.log_box.insert("end", msg + "\n")
                self.log_box.see("end")
                self.log_box.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._poll_log)

    # ---------- 루프 제작 실행 ----------
    def start(self):
        video = self.video_var.get().strip()
        audio = self.audio_var.get().strip() or None
        if not video or not os.path.exists(video):
            messagebox.showwarning("확인", "루프로 만들 영상을 선택해주세요")
            return
        out_dir = self.outdir_var.get().strip() or os.path.join(os.path.expanduser("~"), "Videos")
        os.makedirs(out_dir, exist_ok=True)
        target_sec = dict(DUR_PRESETS).get(self.dur_var.get(), 36000)
        smooth_name = self.smooth_var.get()
        audio_flatten = self.flatten_var.get()
        fade = self.fade_var.get()
        loop_unit = self.loop_unit_var.get()
        short_unit_sec = self.short_unit_sec.get()
        narr_args = None
        if self.auto_narr_var.get():
            try:
                n_start = float(self.narr_start_var.get())
            except (tk.TclError, ValueError):
                n_start = 6.0
            narr_args = dict(voice_label=self.narr_voice_var.get(), speed_key=self.narr_speed_var.get(),
                             duck_key=self.narr_duck_var.get(),
                             len_sec=dict(NARR_LEN).get(self.narr_len_var.get(), 0),
                             start_sec=max(0.0, n_start), hint=self.narr_hint_var.get().strip(),
                             story_file=self.narr_story_var.get().strip(),
                             ext_audio=self.narr_ext_audio_var.get().strip(),
                             story_title=self.narr_title_var.get().strip(),
                             on_title=self._narr_on_title,
                             style=NARR_STYLES.get(self.narr_style_var.get(), "twist"),
                             title_sec=self._narr_title_sec(), tone=self.narr_tone_var.get())

        self.stop_flag.clear()
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        self.log("🚀 LoopMaker v11.19 시작\n")

        self.pipeline = Pipeline(self.log, self.stop_flag)

        def work():
            try:
                out = self.pipeline.process(video, audio, out_dir, target_sec,
                                            smooth_name, audio_flatten, fade=fade,
                                            loop_unit=loop_unit,
                                            short_unit_sec=short_unit_sec)
                if out:
                    self.last_output = out
                    if narr_args:
                        self.log(f"\n🌙 이어서 이야기 내레이션을 넣습니다 — 성우: {narr_args['voice_label']}")
                        try:
                            self.narrator = StoryNarrator(self.log, self.stop_flag)
                            nout = self.narrator.run(video=out, **narr_args)
                            if nout:
                                self.last_output = nout
                        except InterruptedError:
                            raise
                        except Exception as nex:
                            self.log(f"\n❌ 내레이션 추가 실패 (루프 영상은 정상 완성됨: {out})\n   원인: {nex}\n"
                                     f"   → [🌙 스토리 내레이션] 탭에서 다시 시도할 수 있어요")
                    self.log("\n💡 [유튜브 패키지] 탭에서 썸네일·제목·설명·태그를 바로 만들 수 있어요!")
            except Exception as ex:
                self.log(f"\n❌ 오류: {ex}")
            finally:
                self.log_q.put("__DONE__")

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    # ---------- 유튜브 패키지 실행 ----------
    def make_package(self, mode="long"):
        video = self.pkg_video_var.get().strip()
        if not video or not os.path.exists(video):
            messagebox.showwarning("확인", "완성된 루프 영상을 선택해주세요")
            return
        if not HAS_PIL:
            messagebox.showerror("Pillow 필요",
                                 "썸네일 생성에 Pillow가 필요합니다.\n\n명령 프롬프트에서:\npip install pillow")
            return
        thumb_text = self.thumb_text_var.get().strip()
        sub_text = self.sub_text_var.get().strip()
        pos_mode = self.text_pos_var.get()
        out_dir = self.pkg_outdir_var.get().strip() or None
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        make_shorts = self.shorts_var.get()
        shorts_crop = self.shorts_crop_var.get()
        channel_url = self.channel_url_var.get().strip()
        if mode == "shorts":
            # ★ v9.7 버그 수정 + v10 강화: 숏폼은 화면이 좁아서 롱폼용 썸네일 문구나
            # Claude가 자동으로 채운 부제목(장면 설명처럼 길어질 수 있고, 입력창이
            # 좁아 화면엔 짧게 보여도 실제 값은 훨씬 길 수 있음)을 그대로 쓰면 화면
            # 밖으로 넘치거나 잘리기 쉬웠다. 숏폼에는 항상 짧은 주제(en/kr)만
            # 간결하게 다시 조합해서 쓰고, 부제목(sub_text)은 조건 없이 무조건
            # 비워서 긴 문구가 절대 들어가지 않게 한다(본편 유도 문구가 이미 화면
            # 하단에 따로 나가므로 중복도 피함).
            en = self.custom_en_var.get().strip(); kr = self.custom_kr_var.get().strip()
            if en or kr:
                thumb_text = (f"{kr} / {en}" if en and kr else (en.upper() or kr))
            elif not thumb_text.strip():
                messagebox.showwarning("확인", "숏폼에 넣을 썸네일 메인 텍스트를 입력해주세요")
                return
            sub_text = ""
        en = kr = tags_csv = None
        if mode == "long":
            en = self.custom_en_var.get().strip()
            kr = self.custom_kr_var.get().strip()
            tags_csv = self.custom_tags_var.get().strip()
            if kr and not en:
                en = ko_to_en_topic(kr) or kr
            if not thumb_text.strip() and en:
                thumb_text = (f'{kr}ㅣ{en.upper()}' if kr else en.upper())
            if not en or not kr:
                messagebox.showwarning("확인", "영어 주제와 한글 주제를 모두 입력해주세요 (또는 위 'Claude로 자동 분석' 사용)\n예) 영어: Thunderstorm / 한글: 천둥 빗소리")
                self.pkg_btn.configure(state="normal")
                return

        # ★ v9.7 버그 수정: tkinter 변수는 메인 스레드에서만 안전하게 읽을 수 있다
        # (백그라운드 스레드에서 .get()을 부르면 "main thread is not in main loop"
        # 오류가 남 — thumb2/sub2/thumb3/sub3/scene/desc/caption 등 여러 값을
        # work() 스레드 안에서 뒤늦게 읽던 게 원인). 스레드를 시작하기 전, 필요한
        # 값을 전부 여기(메인 스레드)에서 미리 꺼내 일반 변수로 넘긴다.
        thumb2, sub2 = self.thumb2_var.get(), self.sub2_var.get()
        thumb3, sub3 = self.thumb3_var.get(), self.sub3_var.get()
        scene_en = self.scene_en_var.get().strip() or None
        scene_kr = self.scene_kr_var.get().strip() or None
        desc_en = self.desc_en_var.get().strip() or None
        desc_kr = self.desc_kr_var.get().strip() or None
        cap_kr = self.caption_kr_var.get().strip()
        cap_en = self.caption_en_var.get().strip()
        skip_caption = self.skip_caption_var.get()
        story = None
        st_title = self.story_title_var.get().strip()
        st_sum = self.story_summary_var.get().strip()
        if st_title or st_sum:
            story = dict(self.story_meta or {}, title=st_title, summary=st_sum)
        # v11.15: 내레이션 영상이면 롱폼 썸네일 3종 + 숏폼 영상·커버의 부제목을 항상
        #         "잠들기 좋은 이야기 (제목: ○○)" 로 통일
        story_sub = narr_thumb_subtitle(story)
        if story_sub:
            sub_text = sub2 = sub3 = story_sub
            self.log(f"🌙 내레이션 영상 — 썸네일·숏폼 부제목: {story_sub}")
            # ★ v11.17: 내레이션 영상은 제목 카드 + 이야기가 이미 있으므로 인트로 자막을 넣지 않는다
            #   ('자막 넣지 않음' 체크를 깜빡해도 영상에 긴 자막이 새겨지지 않도록 자동으로 건너뜀)
            if not skip_caption:
                skip_caption = True
                self.log("🌙 내레이션 영상이라 인트로 자막은 자동으로 넣지 않아요")
        try:
            cap_sec = float(self.caption_sec_var.get())
        except Exception:
            cap_sec = 30.0

        self.pkg_btn.configure(state="disabled")
        self.shorts_btn.configure(state="disabled")
        self.log("\n📦 숏폼 생성 시작...\n" if mode == "shorts"
                 else "\n📦 롱폼 패키지 생성 시작...\n")

        def work():
            try:
                if mode == "shorts":
                    YTPackage(self.log).create_shorts(
                        video, thumb_text, sub_text, shorts_crop=shorts_crop,
                        channel_url=channel_url, out_dir=out_dir, cap_sec=cap_sec)
                else:
                    tv = [(thumb_text, sub_text), (thumb2, sub2), (thumb3, sub3)]
                    extra_tags = [t.strip() for t in tags_csv.split(",") if t.strip()]
                    YTPackage(self.log).create(video, en, kr, thumb_text, sub_text, pos_mode,
                                               out_dir=out_dir, make_shorts=False,
                                               shorts_crop=shorts_crop, channel_url=channel_url,
                                               extra_tags=extra_tags,
                                               scene_en=scene_en, scene_kr=scene_kr,
                                               desc_en=desc_en, desc_kr=desc_kr,
                                               thumb_variants=tv, cap_sec=cap_sec, story=story)

                    # v9.7: 체크박스가 없으면 패키지 생성에 자막 삽입까지 자동으로 포함.
                    # 여기서 실패해도 위의 썸네일/제목/설명/태그는 이미 성공했으므로,
                    # 별도 try/except로 감싸서 "패키지 오류"로 뭉뚱그려지지 않게 한다.
                    if not skip_caption and (cap_kr or cap_en):
                        self.log("\n📝 인트로 자막 자동 삽입 중... (체크박스로 끌 수 있어요)")
                        cap_tmp = tempfile.mkdtemp(prefix="caption_")
                        pipe = Pipeline(self.log, threading.Event())
                        try:
                            # v10: 빠른 제자리 방식 우선(10시간 영상도 수십 초, 추가 디스크 0),
                            # 안 되면 기존 방식 + 검증 후 원본 교체 (파일이 2벌 남지 않음).
                            pipe.insert_intro_caption(video, cap_kr, cap_en, cap_tmp,
                                                      caption_sec=cap_sec,
                                                      delay=self._caption_delay_for(video))
                        except Exception as cap_ex:
                            self.log(f"\n⚠️ 자막 삽입은 실패했지만 패키지(썸네일/제목/설명/태그)는 "
                                     f"정상 완료됐습니다: {cap_ex}")
                        finally:
                            shutil.rmtree(cap_tmp, ignore_errors=True)
            except Exception as ex:
                self.log(f"\n❌ 패키지 오류: {ex}")
            finally:
                self.log_q.put("__PKG_DONE__")

        threading.Thread(target=work, daemon=True).start()

    def stop(self):
        self.stop_flag.set()
        if self.pipeline:
            self.pipeline.kill_current()
        if self.narrator:
            self.narrator.kill()
        self.log("⏹ 중단 요청됨... 정리 중")


if __name__ == "__main__":
    App().mainloop()
