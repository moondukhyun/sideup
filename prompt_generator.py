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
        "max_tokens": 1024,
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

    system_prompt = f"""당신은 Suno AI 음악 생성을 위한 전문 프롬프트 작성가입니다.
오늘은 {date_str} {day_kor}이고, 계절은 {season}입니다.

"솜니아 뮤직" 유튜브 채널을 위한 음악 프롬프트를 7개 만들어주세요.

6가지 카테고리 (각각 반드시 다른 템포, 악기 구성, 분위기로 만들 것):
- 영어로 작성 (Suno AI는 영어 프롬프트가 더 좋음)
- 50-80 단어 분량
- 구체적인 악기, 감정, 분위기, 레퍼런스 아티스트 포함
- 반드시 instrumental only — 프롬프트 맨 끝에 항상 "instrumental only, no vocals, no lyrics, no singing" 을 포함할 것
- 오늘의 날짜/계절/요일 감성을 반영

1. 아침/카페 무드
   - 템포: 보통~빠름 (100-120 BPM)
   - 악기: 밝고 경쾌한 피아노 + 어쿠스틱 기타 + 가벼운 퍼커션
   - 분위기: 밝고 희망적, 에너지 있음, 햇살 느낌

2. 수면/명상
   - 템포: 매우 느림 (40-60 BPM)
   - 악기: 매우 부드러운 피아노 단음 + 깊은 패드 사운드, 퍼커션 없음
   - 분위기: 극도로 조용하고 몽환적, 거의 소리가 없는 듯한 느낌

3. 감성/힐링 (오늘 계절 반영)
   - 템포: 느림 (60-80 BPM)
   - 악기: 피아노 + 첼로/바이올린 현악기 + 약한 앰비언트
   - 분위기: 뭉클하고 애절함, 눈물 나는 감동, 시네마틱

4. 집중/공부 로파이
   - 템포: 보통 (80-90 BPM)
   - 악기: 로파이 피아노 + 바이닐 크래클 노이즈 + 재즈 드럼 브러시
   - 분위기: 집중되고 차분함, 빈티지 느낌, 카세트테이프 질감

5. 오늘의 특별 (날짜와 계절에서 영감받은 독창적인 무드)
   - 템포: 자유롭게
   - 악기: 오케스트라 또는 특이한 악기 조합 사용
   - 분위기: 위 4개와 완전히 다른 독창적인 컨셉

6. 직장 스트레스 해소
   - 템포: 느림→보통 (70-90 BPM), 점점 마음이 풀리는 느낌
   - 악기: 피아노 + 부드러운 신디사이저 패드 + 자연 소리(빗소리/새소리)
   - 분위기: 처음엔 무겁다가 점점 가벼워지는 감정 해소, 따뜻한 위로

---

7번째는 가사 있는 한국어 노래입니다. 형식이 다릅니다:

7. 직장 생활 노래 (한국어 가사)
   - 오늘의 {day_kor} / {season} 감성을 담아 직장인의 일상, 어려움, 희망을 표현
   - 장르: 감성 K-pop 발라드 또는 어쿠스틱 인디 팝
   - 한국어 가사로 작성 (2절 구성: 1절 + 후렴 + 2절 + 후렴)
   - 공감되는 직장 생활 이야기 (야근, 상사, 힘든 월요일, 퇴근 후 해방감, 동료와의 우정 등)
   - 스타일 설명은 영어로, 가사는 한국어로

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
**제목:** [한국어 노래 제목]
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
