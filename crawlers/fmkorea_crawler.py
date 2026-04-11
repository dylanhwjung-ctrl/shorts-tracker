"""
FM코리아 크롤러 — 베스트 게시글 스크래핑
"""
import time
import httpx
import sys
import os
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.client import get_client

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.fmkorea.com/",
}

BASE_URL = "https://www.fmkorea.com"
DEFAULT_URLS = ["https://www.fmkorea.com/best"]


def fetch_posts(url: str, min_recommend: int = 100) -> list[dict]:
    try:
        # 세션으로 메인 페이지 먼저 방문해 쿠키 획득 후 best 페이지 요청
        with httpx.Client(headers=HEADERS, timeout=15, follow_redirects=True) as client:
            client.get("https://www.fmkorea.com/")
            import time as _t; _t.sleep(1)
            r = client.get(url)
            r.raise_for_status()
    except Exception as e:
        print(f"  [오류] FM코리아 요청 실패: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    results = []

    import re as _re
    for li in soup.find_all("li", class_=_re.compile(r"li_best")):
        try:
            # 제목 링크: h3.title > a
            title_tag = li.select_one("h3.title a")
            if not title_tag:
                continue

            # 제목 텍스트 (span.ellipsis-target 안에 있음)
            span = title_tag.select_one("span.ellipsis-target")
            title = span.get_text(strip=True) if span else title_tag.get_text(strip=True)
            if not title:
                continue

            href = title_tag.get("href", "")
            if href.startswith("//"):
                href = "https:" + href
            elif not href.startswith("http"):
                href = BASE_URL + href

            # 추천수: a.pc_voted_count > span.count
            recommend = 0
            vote_tag = li.select_one("a.pc_voted_count span.count")
            if vote_tag:
                try:
                    recommend = int(vote_tag.get_text(strip=True).replace(",", ""))
                except ValueError:
                    pass

            if recommend < min_recommend:
                continue

            results.append({
                "title": title,
                "url": href,
                "score": recommend,
                "comment_count": 0,
            })
        except Exception:
            continue

    return results


def save_posts(posts: list[dict], category: str) -> int:
    if not posts:
        return 0
    client = get_client()
    rows = [{
        "source": "fmkorea",
        "board_name": "FM코리아_베스트",
        "title": p["title"],
        "url": p["url"],
        "score": p["score"],
        "comment_count": p["comment_count"],
        "category": category,
    } for p in posts]

    client.table("posts").upsert(rows, on_conflict="url").execute()
    return len(rows)


def run(category: str = "gaming", urls: list = None, min_recommend: int = 100):
    if urls is None:
        urls = DEFAULT_URLS

    total = 0
    for url in urls:
        print(f"  FM코리아 크롤링 중...")
        posts = fetch_posts(url, min_recommend)
        saved = save_posts(posts, category)
        total += saved
        print(f"  → {saved}개 저장 완료")
        time.sleep(2)

    print(f"FM코리아 크롤링 완료: 총 {total}개 저장")
    return total


if __name__ == "__main__":
    run()
