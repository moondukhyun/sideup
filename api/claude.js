// 환경변수 (Vercel > Settings > Environment Variables)
//   ANTHROPIC_API_KEY  (필수)
//   ALLOWED_ORIGINS    쉼표 구분 허용 도메인. 예: https://sideup.vercel.app,https://내블로그.tistory.com
//   API_ACCESS_TOKEN   (선택) 설정하면 요청 헤더 x-access-token 이 일치해야 함
const MODEL = 'claude-haiku-4-5-20251001';
const MAX_TOKENS_CAP = 1500;
const MAX_MESSAGES = 20;
const MAX_CHARS = 20000;

const allowedOrigins = () =>
  (process.env.ALLOWED_ORIGINS || '').split(',').map((s) => s.trim()).filter(Boolean);

function validMessages(m) {
  if (!Array.isArray(m) || m.length === 0 || m.length > MAX_MESSAGES) return false;
  let chars = 0;
  for (const x of m) {
    if (!x || !['user', 'assistant'].includes(x.role) || typeof x.content !== 'string') return false;
    chars += x.content.length;
  }
  return chars <= MAX_CHARS;
}

export default async function handler(req, res) {
  const origin = req.headers.origin;
  const allowed = allowedOrigins();
  const originOk = origin && allowed.includes(origin);

  // 허용된 도메인에만 CORS 헤더를 내려줌 (와일드카드 금지)
  if (originOk) {
    res.setHeader('Access-Control-Allow-Origin', origin);
    res.setHeader('Vary', 'Origin');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, x-access-token');
  }

  if (req.method === 'OPTIONS') return res.status(originOk ? 204 : 403).end();
  if (req.method !== 'POST') return res.status(405).json({ error: { message: 'Method not allowed' } });

  // 브라우저 요청은 허용 도메인만 통과 (Origin 없는 서버 간 호출은 토큰으로만 허용)
  if (origin && !originOk) return res.status(403).json({ error: { message: 'Origin not allowed' } });

  const token = process.env.API_ACCESS_TOKEN;
  if (token && req.headers['x-access-token'] !== token) {
    return res.status(401).json({ error: { message: 'Unauthorized' } });
  }
  if (!origin && !token) {
    return res.status(403).json({ error: { message: 'Forbidden' } });
  }

  if (!process.env.ANTHROPIC_API_KEY) {
    return res.status(500).json({ error: { message: 'Server not configured' } });
  }

  const body = req.body || {};
  if (!validMessages(body.messages)) {
    return res.status(400).json({ error: { message: 'Invalid messages' } });
  }
  const maxTokens = Math.min(Math.max(parseInt(body.max_tokens, 10) || 1000, 1), MAX_TOKENS_CAP);

  try {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': process.env.ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01',
      },
      // 모델은 서버에서 고정 (클라이언트가 비싼 모델을 고르지 못하게)
      body: JSON.stringify({ model: MODEL, max_tokens: maxTokens, messages: body.messages }),
    });
    const data = await response.json();
    return res.status(response.status).json(data);
  } catch (e) {
    // 내부 오류 상세는 노출하지 않음
    console.error('claude proxy error:', e);
    return res.status(502).json({ error: { message: 'Upstream request failed' } });
  }
}
