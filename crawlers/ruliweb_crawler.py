"""
루리웹 크롤러 — BeautifulSoup 스크래핑
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
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://bbs.ruliweb.com",
}

DEFAULT_URLS = [
    "https://bbs.ruliweb.com/news/board/1003",  # 게임뉴스
]


def fetch_posts(url: str, min_hit: int = 100) -> list[dict]:
    try:
        r = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
        r.raise_for_status()
    except Exception as e:
        print(f"  [오류] 루리웹 요청 실패: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    results = []

    for row in soup.select("tr.table_body.blocktarget"):
        try:
            title_tag = row.select_one("a.subject_link")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            href = title_tag.get("href", "")
            if not href.startswith("http"):
                href = "https://bbs.ruliweb.com" + href

            # 조회수 (루리웹 뉴스 게시판은 추천수 미표시)
            hit_tag = row.select_one("td.hit")
            hit = 0
            if hit_tag:
                try:
                    hit = int(hit_tag.get_text(strip=True).replace(",", ""))
                except ValueError:
                    pass

            if hit < min_hit:
                continue

            results.append({
                "title": title,
                "url": href,
                "score": hit,       # 조회수를 score로 사용
                "comment_count": 0,
            })
        except Exception:
            continue

    return results


def save_posts(posts: list[dict], board_name: str, category: str) -> int:
    if not posts:
        return 0
    client = get_client()
    rows = [{
        "source": "ruliweb",
        "board_name": board_name,
        "title": p["title"],
        "url": p["url"],
        "score": p["score"],
        "comment_count": p["comment_count"],
        "category": category,
    } for p in posts]

    client.table("posts").upsert(rows, on_conflict="url").execute()
    return len(rows)


def run(category: str = "gaming", urls: list = None, min_hit: int = 100):
    if urls is None:
        urls = DEFAULT_URLS

    total = 0
    for url in urls:
        board_name = "루리웹_게임뉴스"
        print(f"  루리웹 크롤링 중...")
        posts = fetch_posts(url, min_hit)
        saved = save_posts(posts, board_name, category)
        total += saved
        print(f"  → {saved}개 저장 완료")
        time.sleep(2)

    print(f"루리웹 크롤링 완료: 총 {total}개 저장")
    return total


if __name__ == "__main__":
    run()
