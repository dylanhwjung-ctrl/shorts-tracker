"""
인벤 크롤러 — 이슈 게시판 스크래핑
"""
import time
import httpx
import sys
import os
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.client import get_client

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.inven.co.kr",
}

DEFAULT_URLS = [
    "https://www.inven.co.kr/board/issue",
]

BASE_URL = "https://www.inven.co.kr"


def fetch_posts(url: str, min_recommend: int = 5) -> list[dict]:
    try:
        r = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
        r.raise_for_status()
    except Exception as e:
        print(f"  [오류] 인벤 요청 실패: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    results = []

    # 인벤 게시판 테이블 구조
    for row in soup.select("table#new_board_list tr, .board-list tr"):
        try:
            title_tag = row.select_one("td.tit a, .subject a")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            if not title:
                continue

            href = title_tag.get("href", "")
            if href.startswith("//"):
                href = "https:" + href
            elif not href.startswith("http"):
                href = BASE_URL + href

            # 추천수
            recommend = 0
            rec_tag = row.select_one("td.recom, .recommend")
            if rec_tag:
                try:
                    recommend = int(rec_tag.get_text(strip=True).replace(",", ""))
                except ValueError:
                    pass

            # 댓글수
            comments = 0
            cmt_tag = row.select_one(".comment-count, .num")
            if cmt_tag:
                try:
                    comments = int(cmt_tag.get_text(strip=True).replace(",", ""))
                except ValueError:
                    pass

            if recommend < min_recommend:
                continue

            results.append({
                "title": title,
                "url": href,
                "score": recommend,
                "comment_count": comments,
            })
        except Exception:
            continue

    return results


def save_posts(posts: list[dict], category: str) -> int:
    if not posts:
        return 0
    client = get_client()
    rows = [{
        "source": "inven",
        "board_name": "인벤_이슈",
        "title": p["title"],
        "url": p["url"],
        "score": p["score"],
        "comment_count": p["comment_count"],
        "category": category,
    } for p in posts]

    client.table("posts").upsert(rows, on_conflict="url").execute()
    return len(rows)


def run(category: str = "gaming", urls: list = None, min_recommend: int = 5):
    if urls is None:
        urls = DEFAULT_URLS

    total = 0
    for url in urls:
        print(f"  인벤 [{url}] 크롤링 중...")
        posts = fetch_posts(url, min_recommend)
        saved = save_posts(posts, category)
        total += saved
        print(f"  → {saved}개 저장 완료")
        time.sleep(2)

    print(f"인벤 크롤링 완료: 총 {total}개 저장")
    return total


if __name__ == "__main__":
    run()
