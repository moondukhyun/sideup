"""
Daily Suno prompt generator using Claude API.
Generates 7 prompts (6 instrumental + 1 Korean lyrics song) based on today's date and season.
Rotates between 3 target audiences every day: 직장인 / 취업 준비생 / 50-70대 중노년층
"""

import os
import datetime
import json
import urllib.request
import urllib.error

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
MODEL = 'claude-haiku-4-5-20251001'


def get_season(month):
    if month in (3, 4, 5):   return '봄 (Spring)'
    if month in (6, 7, 8):   return '여름 (Summer)'
    if month in (9, 10, 11): return '가을 (Autumn)'
    return '겨울 (Winter)'


def get_day_kor(weekday):
    days = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
    return days[weekday]


def get_audience_info(day):
    idx = day % 3
    if idx == 0:
        return {
            'name': '직장인',
            'cat6_title': '직장 스트레스 해소 🫧',
            'cat6_desc': (
                "- 템포: 느림→보통 (65-88 BPM), 감정이 서서히 풀리는 arc 표현\n"
                "   - 악기: 감정 해소에 맞는 독창적 조합 (피아노+자연소리 외에도 다양하게 시도)\n"
                "   - 분위기: 퇴근 후 해방감, 혹은 무거운 마음이 서서히 가벼워지는 여정\n"
                "   - 장르 예시: soft jazz, ambient pop, chillout, downtempo"
            ),
            'cat7_title': '직장 생활 노래 🎤',
            'cat7_genre': '감성 K-pop 발라드 또는 어쿠스틱 인디 팝 (날마다 다른 서브장르)',
            'cat7_style_hint': 'emotional K-pop ballad or acoustic indie pop, 25-40대 직장인 공감 감성',
            'cat7_themes': (
                "     * 야근하다 혼자 남은 사무실, 창밖 야경\n"
                "     * 점심시간 옥상에서 잠깐 숨 고르기\n"
                "     * 퇴근길 지하철 안 멍하니 앉아있는 순간\n"
                "     * 상사한테 혼난 날 화장실에서 눈물 참기\n"
                "     * 오랜 직장 동료와 퇴근 후 마시는 맥주\n"
                "     * 이직을 고민하며 밤에 혼자 이력서 쓰기\n"
                "     * 번아웃이 와서 아무것도 하기 싫은 날\n"
                "     * 프로젝트 마감 직전의 긴장감과 동료와의 연대\n"
                "     * 퇴사 결심한 날 마지막으로 바라보는 사무실"
            ),
        }
    elif idx == 1:
        return {
            'name': '취업 준비생',
            'cat6_title': '취업 준비 위로 음악 🌱',
            'cat6_desc': (
                "- 템포: 느림~보통 (60-85 BPM), 희망과 위로의 감성\n"
                "   - 악기: 따뜻하고 부드러운 조합 (어쿠스틱 기타, 우쿨렐레, 소프트 피아노 등)\n"
                "   - 분위기: 지쳐있지만 다시 일어서는 청년의 감성, 따뜻한 응원\n"
                "   - 장르 예시: hopeful indie folk, warm acoustic pop, uplifting ambient"
            ),
            'cat7_title': '취업 준비생의 노래 📝',
            'cat7_genre': '청춘 인디 팝 또는 희망 발라드 (날마다 다른 서브장르)',
            'cat7_style_hint': 'sensitive indie pop or hopeful ballad, 20대 청춘 감성, bittersweet yet hopeful',
            'cat7_themes': (
                "     * 스터디 카페에서 홀로 보내는 긴 하루\n"
                "     * 자소서 쓰다 멍하니 바라보는 빈 화면\n"
                "     * 불합격 통보 메일을 받는 순간의 먹먹함\n"
                "     * 면접 전날 밤 잠 못 이루는 긴장감\n"
                "     * 부모님께 아직 취업 못 했다고 말 못 하는 마음\n"
                "     * 합격 문자를 기다리며 핸드폰만 바라보는 오후\n"
                "     * 친구들은 다 취업했는데 나만 뒤처진 것 같은 느낌\n"
                "     * 포기하고 싶지만 다시 일어서는 작은 용기\n"
                "     * 드디어 합격! 설레고 두려운 첫 출근 전날 밤"
            ),
        }
    else:
        return {
            'name': '50-70대 중노년층',
            'cat6_title': '황혼 힐링 음악 🌅',
            'cat6_desc': (
                "- 템포: 느리고 여유로움 (55-75 BPM)\n"
                "   - 악기: 따뜻하고 클래식한 조합 (어쿠스틱 기타, 현악 앙상블, 플루트, 아코디언 등)\n"
                "   - 분위기: 지나온 삶에 대한 감사, 여유로운 황혼의 평온함\n"
                "   - 장르 예시: classic Korean ballad style, soft trot fusion, nostalgic folk, warm orchestral"
            ),
            'cat7_title': '인생 노래 🌸',
            'cat7_genre': '감성 한국 발라드 또는 소프트 트로트 퓨전 (날마다 다른 서브장르)',
            'cat7_style_hint': 'warm Korean ballad or soft trot-ballad fusion, 50-70대 중장년 공감 감성, nostalgic and heartwarming',
            'cat7_themes': (
                "     * 자녀가 모두 떠난 빈 집의 고요함과 그리움\n"
                "     * 오래된 앨범 속 젊은 날의 기억\n"
                "     * 손주와 함께 보내는 소소한 행복\n"
                "     * 정년퇴직 후 처음 맞는 여유로운 아침\n"
                "     * 오랜 친구와 만나 나누는 옛날 이야기\n"
                "     * 건강이 예전 같지 않음을 느끼는 순간의 담담함\n"
                "     * 지나온 인생을 돌아보며 느끼는 감사함\n"
                "     * 황혼의 부부가 함께 걷는 공원 산책\n"
                "     * 고향 생각, 어머니 생각이 나는 어느 날"
            ),
        }


def call_claude(prompt_text):
    if not ANTHROPIC_API_KEY:
        print("[ERROR] ANTHROPIC_API_KEY not set")
        return None

    payload = json.dumps({
        "model": MODEL,
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": prompt_text}]
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=payload,
        headers={
            'x-api-key': ANTHROPIC_API_KEY,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data['content'][0]['text']
    except urllib.error.HTTPError as e:
        print(f"[ERROR] API call failed: {e.code} {e.read().decode()[:200]}")
        return None
    except Exception as e:
        print(f"[ERROR] {e}")
        return None


def generate_prompts(today):
    season   = get_season(today.month)
    day_kor  = get_day_kor(today.weekday())
    date_str = today.strftime('%Y년 %m월 %d일')
    audience = get_audience_info(today.day)

    system_prompt = f"""당신은 Suno AI 음악 생성을 위한 창의적인 전문 프롬프트 작성가입니다.
오늘은 {date_str} {day_kor}이고, 계절은 {season}입니다.
오늘의 타겟 청취자: {audience['name']}

"솜니아 뮤직" 유튜브 채널을 위한 음악 프롬프트를 7개 만들어주세요.

⚠️ 가장 중요한 규칙 — 매일 신선하고 독창적인 결과물을 위해:
- 절대 "emotional piano", "healing piano" 같은 뻔한 표현을 반복하지 마세요
- 각 프롬프트는 완전히 다른 장르/시대/악기 조합을 써야 합니다
- 구체적인 연도/시대 (예: "late 1980s", "early 2000s", "1970s") 를 반드시 포함
- 실제 아티스트 이름 2~3명 구체적으로 인용 (Yiruma만 반복 금지 — 다양하게)
- 예상치 못한 악기 조합 사용 (예: 하프 + 마림바, 하프시코드 + 현대 패드, 오카리나 + 스트링)
- 특정 분위기 단어를 구체적으로: "rain-soaked midnight jazz", "alpine morning mist", "firefly summer dusk"
- 오늘 날짜 {date_str}, 계절 {season}, 타겟({audience['name']})의 감성을 반영

1~6번 공통 규칙:
- 영어로 작성
- 50-80 단어 분량
- 프롬프트 맨 끝에 반드시 "instrumental only, no vocals, no lyrics, no singing" 포함

---

1. 아침/카페 무드
   - 템포: 보통~빠름 (95-125 BPM) — 정확한 BPM 명시
   - 악기: 피아노 외에 다른 악기도 메인으로 (어쿠스틱 기타, 비브라폰, 클라리넷 등 날마다 다르게)
   - 분위기: 밝고 에너지 있는 아침 — 오늘만의 특별한 표현 사용
   - 장르 예시: bossa nova, indie folk, café jazz, French chanson, Swedish pop

2. 수면/명상
   - 템포: 매우 느림 (40-60 BPM) — 정확한 BPM 명시
   - 악기: 피아노 외에 색다른 소리 사용 (티베탄 볼, 바이올린 하모닉스, 플루트, 자연음 등)
   - 분위기: 깊은 수면/명상 유도 — 색다른 표현
   - 장르 예시: dark ambient, drone, new age, binaural

3. 감성/힐링 (오늘 계절 반영)
   - 템포: 느림 (58-78 BPM) — 정확한 BPM 명시
   - 악기: 현악기 다양화 (비올라, 첼로, 하프 등) + 오늘 계절 {season} 느낌의 음색
   - 분위기: 시네마틱하고 감동적 — 오늘의 계절/날씨 느낌을 구체적으로
   - 장르 예시: neo-classical, cinematic orchestral, contemporary classical

4. 집중/공부 로파이
   - 템포: 보통 (78-92 BPM) — 정확한 BPM 명시
   - 악기: 로파이 질감의 다양한 악기 (재즈 피아노, 빈티지 신스, 물소리, 타자기 소리 등)
   - 분위기: 집중, 빈티지, 아날로그 — 날마다 다른 시대/장소 설정
   - 장르 예시: lo-fi hip hop, jazz-hop, chill beats, vaporwave ambient

5. 오늘의 특별 ✨ (완전히 자유로운 창의적 컨셉)
   - 템포: 완전 자유
   - 악기: 가장 독창적이고 예상치 못한 조합 — 절대 1~4번과 겹치면 안 됨
   - 오늘 {date_str} {season}에서 영감받은 독특한 음악 세계관 창조
   - 가능한 장르: flamenco, Celtic, Middle Eastern, game OST, anime, Nordic folk, tango 등 자유롭게

6. {audience['cat6_title']} — 오늘의 타겟: {audience['name']}
   {audience['cat6_desc']}

---

7번째는 가사 있는 한국어 노래입니다. 형식이 다릅니다:

7. {audience['cat7_title']} — 오늘의 타겟: {audience['name']}
   - 장르: {audience['cat7_genre']}
   - 스타일 힌트: {audience['cat7_style_hint']}
   - 한국어 가사로 작성 (2절 구성: 1절 + 후렴 + 2절 + 후렴)
   - 실제 K-pop처럼 가사 중간에 영어 표현 1~2줄 자연스럽게 섞기 (예: "I just wanna go home", "It's okay, we'll be alright")

   ⚠️ 가사 창작 핵심 규칙:
   - 절대 가사에 요일/날짜를 직접 쓰지 말 것 ("월요일", "화요일" 등 금지)
   - 매번 완전히 다른 상황/시점/감정 — 아래 주제 중 하나를 골라 깊게 파고들기:
{audience['cat7_themes']}
   - 오늘의 계절 {season} 감성은 직접 언급 말고 배경/분위기로만 자연스럽게 녹여낼 것
     (예: 여름이면 "에어컨 바람", 겨울이면 "차가운 복도", 봄이면 "열린 창문 너머")
   - 스타일 설명은 영어로, 가사는 한국어로
   - 제목은 구체적인 장면/감정을 담아 창의적으로 (요일 포함 금지)

다음 형식으로 출력해주세요:

### 1. 아침/카페 ☕
[스타일 프롬프트]

### 2. 수면/명상 🌙
[스타일 프롬프트]

### 3. 감성/힐링 🌿
[스타일 프롬프트]

### 4. 집중/공부 📚
[스타일 프롬프트]

### 5. 오늘의 특별 ✨
[스타일 프롬프트]

### 6. {audience['cat6_title']}
[스타일 프롬프트]

### 7. {audience['cat7_title']}
**제목:** [창의적인 노래 제목 (한국어 또는 한국어+영어 혼용, 요일 금지)]
**스타일:** [영어로 장르/분위기 설명]
**가사:**
[한국어 가사]"""

    return call_claude(system_prompt)


def save_prompts(content, today, output_dir='prompts'):
    os.makedirs(output_dir, exist_ok=True)

    filename = os.path.join(output_dir, f"{today.strftime('%Y-%m-%d')}_prompts.md")
    date_str  = today.strftime('%Y년 %m월 %d일')
    day_kor   = get_day_kor(today.weekday())
    season    = get_season(today.month)
    audience  = get_audience_info(today.day)

    header = f"""# 🎵 오늘의 Suno 프롬프트
**날짜**: {date_str} {day_kor}
**계절**: {season}
**오늘의 타겟**: {audience['name']}

> 아래 프롬프트를 복사해서 Suno AI (https://suno.com) 에 붙여넣으세요.

---

"""
    full_content = header + content

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(full_content)

    latest = os.path.join(output_dir, 'latest.md')
    with open(latest, 'w', encoding='utf-8') as f:
        f.write(full_content)

    print(f"[OK] Prompts saved to {filename}")
    print(f"[OK] Latest prompts: {latest}")
    return filename


def main():
    today = datetime.date.today()
    audience = get_audience_info(today.day)
    print(f"[INFO] Generating prompts for {today} | 타겟: {audience['name']}")

    content = generate_prompts(today)
    if not content:
        print("[ERROR] Failed to generate prompts")
        return

    save_prompts(content, today)

    print("\n" + "="*50)
    print(f"오늘의 Suno 프롬프트 | 타겟: {audience['name']}")
    print("="*50)
    print(content)


if __name__ == '__main__':
    main()
