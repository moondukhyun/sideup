// somnia-forest 뉴스데스크: 트렌드 수집 + 파싱 유틸 (외부 의존성 없음, Node 18+)

export const FEEDS = {
  trends: 'https://trends.google.com/trending/rss?geo=KR',
  news: 'https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko',
};

const decode = (s) =>
  s
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, '$1')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;|&apos;/g, "'")
    .replace(/&amp;/g, '&')
    .trim();

const tag = (block, name) => {
  const m = block.match(new RegExp(`<${name}[^>]*>([\\s\\S]*?)</${name}>`));
  return m ? decode(m[1]) : '';
};

/** RSS XML -> [{title, link, pubDate, source, traffic}] */
export function parseRss(xml) {
  return [...xml.matchAll(/<item>([\s\S]*?)<\/item>/g)].map(([, b]) => ({
    title: tag(b, 'title'),
    link: tag(b, 'link'),
    pubDate: tag(b, 'pubDate'),
    source: tag(b, 'source') || tag(b, 'ht:news_item_source'),
    traffic: tag(b, 'ht:approx_traffic'),
  }));
}

/** 민감 주제는 수익화(광고 제한)·신뢰 위험이 커서 기본 제외 */
const SENSITIVE =
  /사망|숨진|참사|살인|성폭|자살|극단|테러|전쟁|총격|시신|학대|재난|추모|탄핵|대선|총선|여당|야당|정당/;

export function isSafeTopic(title) {
  return !SENSITIVE.test(title);
}

export async function fetchFeed(url) {
  const res = await fetch(url, { headers: { 'User-Agent': 'somnia-forest-newsdesk/1.0' } });
  if (!res.ok) throw new Error(`${url} -> HTTP ${res.status}`);
  return parseRss(await res.text());
}

/** 중복 제거 후 안전한 주제만 */
export function pickTopics(items, limit = 8) {
  const seen = new Set();
  return items
    .filter((i) => i.title && isSafeTopic(i.title))
    .filter((i) => {
      const k = i.title.replace(/[^\p{L}\p{N}]/gu, '').slice(0, 8);
      if (seen.has(k)) return false;
      seen.add(k);
      return true;
    })
    .slice(0, limit);
}
