"""대본이 기존 번역본과 겹치는지 점검: python overlap_check.py 내_대본.txt 번역본1.txt [번역본2.txt ...]

번역본 텍스트 파일은 직접 갖고 계신 전자책/문서에서 복사해 만든 것을 쓰세요 (점검용으로만, 배포 금지).
공백·문장부호를 없앤 뒤 연속 N글자(기본 12)가 같은 구간을 찾아 보여줍니다.
"""
import re
import sys


def norm(t):
    return re.sub(r"[\s\W_]+", "", t)


def overlaps(script, ref, n=12):
    s, r = norm(script), norm(ref)
    grams = {}
    for i in range(len(r) - n + 1):
        grams.setdefault(r[i:i + n], i)
    hits, i = [], 0
    while i <= len(s) - n:
        if s[i:i + n] in grams:
            j = i + n
            while j < len(s) and grams.get(s[j - n + 1:j + 1]) is not None:
                j += 1
            hits.append((i, j))
            i = j
        else:
            i += 1
    return s, hits


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    script = open(sys.argv[1], encoding="utf-8", errors="ignore").read()
    for path in sys.argv[2:]:
        ref = open(path, encoding="utf-8", errors="ignore").read()
        s, hits = overlaps(script, ref)
        same = sum(b - a for a, b in hits)
        print(f"\n[{path}] 겹치는 구간 {len(hits)}곳 · 대본의 {same / max(1, len(s)):.1%}")
        for a, b in sorted(hits, key=lambda h: h[0] - h[1])[:15]:
            print(f"  {b - a}자 연속 일치: {s[a:b][:60]}")
        print("  판단: " + ("안전 (겹침 거의 없음)" if same / max(1, len(s)) < 0.02 and all(b - a < 25 for a, b in hits)
                         else "일부 문장을 다시 쓰세요"))


if __name__ == "__main__":
    main()
