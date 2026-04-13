"""
Reddit 크롤러 — RSS 피드 사용 (인증 불필요)
"""
import time
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.client import get_client

HEADERS = {"User-Agent": "shorts-tracker/1.0 (personal non-commercial use)"}
NS = {"atom": "http://www.w3.org/2005/Atom"}


def fetch_subreddit_hot(subreddit: str) -> list[dict]:
    """RSS 피드에서 hot 게시물 파싱"""
    url = f"https://www.reddit.com/r/{subreddit}/hot.rss"
    try:
        r = httpx.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.text)
        entries = root.findall("atom:entry", NS)

        posts = []
        for entry in entries:
            author = entry.find("atom:author/atom:name", NS)
            author_name = author.text if author is not None else ""
            # AutoModerator 공지글 제외
            if "AutoModerator" in author_name:
                continue

            title = entry.find("atom:title", NS).text or ""
            link = entry.find("atom:link", NS).attrib.get("href", "")
            published = entry.find("atom:published", NS)
            published_text = published.text if published is not None else None

            posts.append({
                "title": title,
                "url": link,
                "published": published_text,
            })
        return posts
    except Exception as e:
        print(f"  [오류] r/{subreddit}: {e}")
        return []


def save_posts(posts: list[dict], subreddit: str, category: str, subcategory: str = None) -> int:
    client = get_client()
    rows = []
    for p in posts:
        row = {
            "source": "reddit",
            "board_name": f"r/{subreddit}",
            "title": p["title"],
            "url": p["url"],
            "score": 0,
            "comment_count": 0,
            "category": category,
        }
        if p.get("published"):
            row["original_at"] = p["published"]
        if subcategory:
            row["subcategory"] = subcategory
        rows.append(row)

    if not rows:
        return 0

    client.table("posts").upsert(rows, on_conflict="url").execute()
    return len(rows)


def run(category: str = "gaming", subreddits: list = None, min_score: int = 0, subcategory: str = None):
    if subreddits is None:
        subreddits = ["gaming", "Games"]

    total = 0
    for sub in subreddits:
        print(f"  r/{sub} 크롤링 중...")
        posts = fetch_subreddit_hot(sub)
        saved = save_posts(posts, sub, category, subcategory)
        total += saved
        print(f"  → {saved}개 저장 완료")
        time.sleep(2)

    print(f"Reddit 크롤링 완료: 총 {total}개 저장")
    return total


if __name__ == "__main__":
    run()
