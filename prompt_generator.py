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

"솜니아 뮤직" 유튜브 채널을 위한 감성적인 피아노/힐링 음악 프롬프트를 5개 만들어주세요.

각 프롬프트는:
- 영어로 작성 (Suno AI는 영어 프롬프트가 더 좋음)
- 50-80 단어 분량
- 구체적인 악기, 감정, 분위기, 레퍼런스 아티스트 포함
- instrumental only (가사 없음)
- 오늘의 날짜/계절/요일 감성을 반영

5가지 카테고리:
1. 아침/카페 무드
2. 수면/명상
3. 감성/힐링 (오늘 계절 반영)
4. 집중/공부 로파이
5. 오늘의 특별 (날짜와 계절에서 영감받은 독창적인 무드)

다음 형식으로 출력해주세요:

### 1. 아침/카페 ☕
[프롬프트]

### 2. 수면/명상 🌙
[프롬프트]

### 3. 감성/힐링 🌿
[프롬프트]

### 4. 집중/공부 📚
[프롬프트]

### 5. 오늘의 특별 ✨
[프롬프트]"""

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
contemplative piano solo, introspective and deep, Ólafur Arnalds meets Yiruma, sparse notes with reverb, emotional journey, instrumental only"""

    filename = save_prompts(content, today)

    print("\n" + "="*50)
    print("오늘의 Suno 프롬프트")
    print("="*50)
    print(content)


if __name__ == '__main__':
    main()
