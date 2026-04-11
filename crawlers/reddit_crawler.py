"""
Reddit 크롤러 — API 키 없이 공개 JSON 엔드포인트 사용
"""
import time
import httpx
from datetime import datetime, timezone

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.client import get_client

HEADERS = {"User-Agent": "shorts-tracker/1.0 (personal non-commercial use)"}


def fetch_subreddit_hot(subreddit: str, limit: int = 25) -> list[dict]:
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    try:
        r = httpx.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        children = r.json()["data"]["children"]
        return [c["data"] for c in children]
    except Exception as e:
        print(f"  [오류] r/{subreddit}: {e}")
        return []


def save_posts(posts: list[dict], subreddit: str, category: str, min_score: int) -> int:
    client = get_client()
    rows = []
    for p in posts:
        if p.get("score", 0) < min_score:
            continue
        if p.get("stickied"):   # 공지글 제외
            continue
        rows.append({
            "source": "reddit",
            "board_name": f"r/{subreddit}",
            "title": p["title"],
            "url": f"https://www.reddit.com{p['permalink']}",
            "score": p.get("score", 0),
            "comment_count": p.get("num_comments", 0),
            "category": category,
            "original_at": datetime.fromtimestamp(
                p["created_utc"], tz=timezone.utc
            ).isoformat(),
        })

    if not rows:
        return 0

    # url이 중복이면 점수/댓글수 업데이트 (upsert)
    client.table("posts").upsert(rows, on_conflict="url").execute()
    return len(rows)


def run(category: str = "gaming", subreddits: list = None, min_score: int = 100):
    if subreddits is None:
        subreddits = ["gaming", "Games"]

    total = 0
    for sub in subreddits:
        print(f"  r/{sub} 크롤링 중...")
        posts = fetch_subreddit_hot(sub)
        saved = save_posts(posts, sub, category, min_score)
        total += saved
        print(f"  → {saved}개 저장 완료")
        time.sleep(2)   # Reddit 요청 간격 준수

    print(f"Reddit 크롤링 완료: 총 {total}개 저장")
    return total


if __name__ == "__main__":
    run()
