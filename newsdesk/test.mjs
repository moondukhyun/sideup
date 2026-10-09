import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
import { parseRss, pickTopics } from './lib.mjs';

const items = parseRss(readFileSync(new URL('./fixtures/sample.xml', import.meta.url), 'utf8'));
assert.equal(items.length, 4);
assert.equal(items[0].title, '태풍 북상 & 장마 전망');
assert.equal(items[0].source, '예시일보');
assert.equal(items[1].traffic, '2,000+');

const topics = pickTopics(items);
assert.deepEqual(topics.map((t) => t.link), ['https://example.com/1', 'https://example.com/2']); // 민감·중복 제외
console.log('OK');
