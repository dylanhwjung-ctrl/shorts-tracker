"""
Hacker News 크롤러 — 공식 Firebase API 사용 (인벤 대체)
IT·테크·스타트업 분야의 인기 글 수집
"""
import httpx
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.client import get_client

HN_API = "https://hacker-news.firebaseio.com/v0"


def fetch_top_stories(limit: int = 30, min_score: int = 100) -> list[dict]:
    try:
        # 상위 게시글 ID 목록
        r = httpx.get(f"{HN_API}/topstories.json", timeout=15)
        story_ids = r.json()[:limit * 2]   # 여유분 포함해서 가져옴
    except Exception as e:
        print(f"  [오류] HN 목록 조회 실패: {e}")
        return []

    results = []
    for sid in story_ids:
        if len(results) >= limit:
            break
        try:
            r = httpx.get(f"{HN_API}/item/{sid}.json", timeout=10)
            item = r.json()
            if not item or item.get("type") != "story":
                continue
            score = item.get("score", 0)
            if score < min_score:
                continue
            url = item.get("url") or f"https://news.ycombinator.com/item?id={sid}"
            results.append({
                "title": item.get("title", ""),
                "url": url,
                "score": score,
                "comment_count": item.get("descendants", 0),
                "original_at": datetime.fromtimestamp(
                    item.get("time", 0), tz=timezone.utc
                ).isoformat(),
            })
        except Exception:
            continue

    return results


def save_posts(posts: list[dict], category: str) -> int:
    if not posts:
        return 0
    client = get_client()
    rows = [{
        "source": "hackernews",
        "board_name": "HackerNews_Top",
        "title": p["title"],
        "url": p["url"],
        "score": p["score"],
        "comment_count": p["comment_count"],
        "category": category,
        "original_at": p.get("original_at"),
    } for p in posts]

    client.table("posts").upsert(rows, on_conflict="url").execute()
    return len(rows)


def run(category: str = "it_gadgets", min_score: int = 100):
    print(f"  Hacker News 크롤링 중...")
    posts = fetch_top_stories(limit=30, min_score=min_score)
    saved = save_posts(posts, category)
    print(f"  → {saved}개 저장 완료")
    print(f"Hacker News 크롤링 완료: 총 {saved}개 저장")
    return saved


if __name__ == "__main__":
    run()
