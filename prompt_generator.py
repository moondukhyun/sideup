"""
Daily Suno prompt generator using Claude API.
Generates 5 emotionally rich, varied prompts based on today's date and season.
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
    season  = get_season(today.month)
    day_kor = get_day_kor(today.weekday())
    date_str = today.strftime('%Y년 %m월 %d일')

    system_prompt = f"""당신은 Suno AI 음악 생성을 위한 창의적인 전문 프롬프트 작성가입니다.
오늘은 {date_str} {day_kor}이고, 계절은 {season}입니다.

"솜니아 뮤직" 유튜브 채널을 위한 음악 프롬프트를 7개 만들어주세요.

⚠️ 가장 중요한 규칙 — 매일 신선하고 독창적인 결과물을 위해:
- 절대 "emotional piano", "healing piano" 같은 뻔한 표현을 반복하지 마세요
- 각 프롬프트는 완전히 다른 장르/시대/악기 조합을 써야 합니다
- 구체적인 연도/시대 (예: "late 1980s", "early 2000s", "1970s") 를 반드시 포함
- 실제 아티스트 이름 2~3명 구체적으로 인용 (Yiruma만 반복 금지 — 다양하게)
- 예상치 못한 악기 조합 사용 (예: 하프 + 마림바, 하프시코드 + 현대 패드, 오카리나 + 스트링)
- 특정 분위기 단어를 구체적으로: "rain-soaked midnight jazz", "alpine morning mist", "firefly summer dusk"
- 오늘 날짜 {date_str}, 요일 {day_kor}, 계절 {season}의 감성을 독창적으로 반영

1~6번 공통 규칙:
- 영어로 작성
- 50-80 단어 분량
- 프롬프트 맨 끝에 반드시 "instrumental only, no vocals, no lyrics, no singing" 포함

---

1. 아침/카페 무드
   - 템포: 보통~빠름 (95-125 BPM) — 정확한 BPM 명시
   - 악기: 피아노 외에 다른 악기도 메인으로 (예: 어쿠스틱 기타, 비브라폰, 클라리넷 등 날마다 다르게)
   - 분위기: 밝고 에너지 있는 아침 — 오늘만의 특별한 표현 사용
   - 장르 예시: bossa nova, indie folk, café jazz, French chanson, Swedish pop

2. 수면/명상
   - 템포: 매우 느림 (40-60 BPM) — 정확한 BPM 명시
   - 악기: 피아노 외에 색다른 소리 사용 (예: 티베탄 볼, 바이올린 하모닉스, 플루트, 자연음 등)
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

5. 오늘의 특별 (완전히 자유로운 창의적 컨셉)
   - 템포: 완전 자유
   - 악기: 가장 독창적이고 예상치 못한 조합 — 절대 1~4번과 겹치면 안 됨
   - 오늘 {date_str} {season}에서 영감받은 독특한 음악 세계관 창조
   - 가능한 장르: flamenco, Celtic, Middle Eastern, game OST, anime, Nordic folk, tango 등 자유롭게

6. 직장 스트레스 해소
   - 템포: 느림→보통 (65-88 BPM), 감정 변화 arc 표현
   - 악기: 감정 해소에 맞는 독창적 악기 조합 (피아노 + 자연소리 외 다른 조합도 시도)
   - 분위기: 퇴근 후의 해방감, 혹은 스트레스가 서서히 풀리는 감정 여정
   - 오늘 {day_kor} 특유의 직장인 감성을 반영

---

7번째는 가사 있는 한국어 노래입니다. 형식이 다릅니다:

7. 직장 생활 노래 (한국어 가사)
   - 장르: 감성 K-pop 발라드 또는 어쿠스틱 인디 팝 (날마다 반드시 다른 서브장르)
   - 한국어 가사로 작성 (2절 구성: 1절 + 후렴 + 2절 + 후렴)
   - 실제 K-pop처럼 가사 중간에 영어 표현 1~2줄 자연스럽게 섞기 (예: "I just wanna go home", "It's okay, we'll be alright")

   ⚠️ 가사 창작 핵심 규칙:
   - 절대 가사에 요일/날짜를 직접 쓰지 말 것 ("월요일", "화요일" 등 금지)
   - 매번 완전히 다른 상황/시점/감정으로 써야 함 — 아래 주제 중 하나를 골라 깊게 파고들기:
     * 야근하다 혼자 남은 사무실, 창밖 야경
     * 점심시간 옥상에서 잠깐 숨 고르기
     * 퇴근길 지하철 안 멍하니 앉아있는 순간
     * 상사한테 혼난 날 화장실에서 눈물 참기
     * 오랜 직장 동료와 퇴근 후 마시는 맥주
     * 이직을 고민하며 밤에 혼자 이력서 쓰기
     * 첫 월급날의 설렘과 현실의 괴리
     * 번아웃이 와서 아무것도 하기 싫은 날
     * 프로젝트 마감 직전의 긴장감과 동료와의 연대
     * 퇴사 결심한 날 마지막으로 바라보는 사무실
   - 오늘의 계절 {season} 감성은 직접 언급 말고 배경/분위기로만 녹여낼 것
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

### 6. 직장 스트레스 해소 🫧
[스타일 프롬프트]

### 7. 직장 생활 노래 🎤
**제목:** [한국어 또는 한국어+영어 혼용 노래 제목 (예: "월요병 Blues", "퇴근길 After Work", "수요일의 커피 한 잔")]
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

    header = f"""# 🎵 오늘의 Suno 프롬프트
**날짜**: {date_str} {day_kor}
**계절**: {season}

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
    print(f"[INFO] Generating prompts for {today}")

    content = generate_prompts(today)
    if not content:
        print("[ERROR] Failed to generate prompts")
        content = """### 1. 아침/카페 ☕
emotional solo piano, Yiruma style, warm morning feeling, gentle arpeggios, soft and hopeful, peaceful cafe atmosphere, instrumental only, cinematic

### 2. 수면/명상 🌙
deep sleep piano, Einaudi Nuvole Bianche style, very slow and peaceful, minimal and soft, healing music, gentle breathing rhythm, instrumental only

### 3. 감성/힐링 🌿
emotional healing piano, touching and nostalgic, soft strings accompaniment, bittersweet melody, cinematic and heartfelt, instrumental only

### 4. 집중/공부 📚
lofi piano study music, calm and focused, gentle arpeggios, peaceful background, soft emotional melody, quiet concentration, instrumental only

### 5. 오늘의 특별 ✨
contemplative piano solo, introspective and deep, Ólafur Arnalds meets Yiruma, sparse notes with reverb, emotional journey, instrumental only

### 6. 직장 스트레스 해소 🫧
gentle stress-relief piano, soft and calming, slow breathing rhythm, peaceful and reassuring, work exhaustion healing, warm and comforting melody, Einaudi style, instrumental only"""

    filename = save_prompts(content, today)

    print("\n" + "="*50)
    print("오늘의 Suno 프롬프트")
    print("="*50)
    print(content)


if __name__ == '__main__':
    main()
