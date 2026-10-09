// 사용법: ANTHROPIC_API_KEY=... node newsdesk/run.mjs [개수]
// 결과: newsdesk/out/YYYY-MM-DD/*.md  (초안 전용 — 사람이 검수·녹음·편집 후 직접 업로드)
import { mkdirSync, writeFileSync } from 'node:fs';
import { FEEDS, fetchFeed, pickTopics } from './lib.mjs';

const KEY = process.env.ANTHROPIC_API_KEY;
if (!KEY) throw new Error('ANTHROPIC_API_KEY 환경변수가 필요합니다.');
const MODEL = process.env.CLAUDE_MODEL || 'claude-haiku-4-5-20251001';
const COUNT = Number(process.argv[2] || 3);

const SYSTEM = `너는 유튜브 채널 "somnia-forest"(빗소리 수면/휴식 채널)의 편집 보조다.
컨셉: "빗소리와 함께 듣는 차분한 오늘의 이슈 브리핑".
엄격한 규칙:
1. 아래 제공된 제목/출처 외의 사실(수치, 인명, 인용, 원인)을 절대 지어내지 마라. 모르면 "[확인 필요]"로 표시.
2. 기사 문장을 그대로 옮기지 말고 짧은 요약과 채널만의 관점(차분한 해설, 생활에 주는 의미)으로 써라. 출처를 명시하라.
3. 자극적 낚시·공포 조장·정치적 편향 금지. 톤은 낮고 편안하게.
4. 마지막에 사람이 반드시 검증할 항목 체크리스트를 넣어라.
출력은 마크다운, 한국어.`;

const userPrompt = (t) => `주제: ${t.title}
출처: ${t.source || '미상'} / 링크: ${t.link}
발행: ${t.pubDate || '미상'} / 검색량: ${t.traffic || '미상'}

다음을 작성:
## 제목 후보 5개 (40자 이내, 낚시 금지)
## 썸네일 문구 3개 (8자 이내) + 이미지 방향
## 대본 (약 600자, 도입→핵심 3포인트→차분한 마무리, 출처 언급 포함)
## 설명란 (타임라인, 출처 링크, 'AI 보조 제작·검수됨' 고지 포함)
## 태그 15개
## 검증 체크리스트`;

async function draft(t) {
  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-api-key': KEY, 'anthropic-version': '2023-06-01' },
    body: JSON.stringify({ model: MODEL, max_tokens: 2000, system: SYSTEM, messages: [{ role: 'user', content: userPrompt(t) }] }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.error?.message || `HTTP ${res.status}`);
  return data.content.map((c) => c.text ?? '').join('');
}

const items = (await Promise.all(Object.values(FEEDS).map((u) => fetchFeed(u).catch(() => [])))).flat();
const topics = pickTopics(items, COUNT);
if (!topics.length) throw new Error('수집된 주제가 없습니다(네트워크/피드 확인).');

const dir = new URL(`./out/${new Date().toISOString().slice(0, 10)}/`, import.meta.url);
mkdirSync(dir, { recursive: true });
for (const [i, t] of topics.entries()) {
  const body = await draft(t);
  const file = new URL(`${i + 1}.md`, dir);
  writeFileSync(file, `# ${t.title}\n\n> 출처: ${t.source} ${t.link}\n> 상태: 초안 (미검수)\n\n${body}\n`);
  console.log('저장:', file.pathname);
}
