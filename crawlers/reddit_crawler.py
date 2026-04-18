"""
Reddit 크롤러 — hot.json 사용 (인증 불필요, score/댓글 수 포함)

서브레딧당 1회 호출로 title/url/score/num_comments/selftext 한 번에 수집.
2026-04-17 RSS → JSON 전환. RSS는 score 정보가 없어 min_score 필터가 죽은 상태였음.
호출 빈도는 RSS 때와 동일(서브레딧당 1회). 개별 글 URL 반복 호출이 아니라 차단 위험 낮음.
JSON 실패 시 RSS로 자동 폴백.
"""
import time
import httpx
import xml.etree.ElementTree as ET

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.client import get_client

HEADERS = {"User-Agent": "shorts-tracker/1.0 (personal non-commercial use)"}
NS = {"atom": "http://www.w3.org/2005/Atom"}


def fetch_subreddit_hot_json(subreddit: str, limit: int = 25) -> list[dict] | None:
    """hot.json에서 게시물 파싱 (score, num_comments, selftext 포함)

    반환: 성공 시 list[dict], 실패(차단/네트워크 오류) 시 None
    """
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    try:
        r = httpx.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 429:
            print(f"  [경고] r/{subreddit}: Rate limit (429)")
            return None
        r.raise_for_status()
        data = r.json()
        children = data.get("data", {}).get("children", [])

        posts = []
        for c in children:
            d = c.get("data", {})
            # AutoModerator, 공지(stickied/pinned) 제외
            if "AutoModerator" in (d.get("author") or ""):
                continue
            if d.get("stickied") or d.get("pinned"):
                continue

            # created_utc → ISO 형식 변환
            from datetime import datetime, timezone
            created = d.get("created_utc")
            published_iso = None
            if created:
                published_iso = datetime.fromtimestamp(created, tz=timezone.utc).isoformat()

            posts.append({
                "title": d.get("title", ""),
                "url": f"https://www.reddit.com{d.get('permalink', '')}",
                "published": published_iso,
                "score": int(d.get("score", 0) or 0),
                "num_comments": int(d.get("num_comments", 0) or 0),
                "selftext": d.get("selftext", "") or "",
            })
        return posts
    except Exception as e:
        print(f"  [JSON 오류] r/{subreddit}: {e}")
        return None


def fetch_subreddit_hot_rss(subreddit: str) -> list[dict]:
    """RSS 피드 파싱 (폴백 전용, score/num_comments=0)"""
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
                "score": 0,
                "num_comments": 0,
                "selftext": "",
            })
        return posts
    except Exception as e:
        print(f"  [RSS 폴백 오류] r/{subreddit}: {e}")
        return []


def fetch_subreddit_hot(subreddit: str) -> list[dict]:
    """hot 게시물 수집 (JSON 우선, 실패 시 RSS 폴백)"""
    posts = fetch_subreddit_hot_json(subreddit)
    if posts is None:
        print(f"  → RSS 폴백으로 재시도")
        posts = fetch_subreddit_hot_rss(subreddit)
    return posts


def save_posts(posts: list[dict], subreddit: str, category: str, subcategory: str = None) -> int:
    if not posts:
        return 0
    client = get_client()
    rows = []
    for p in posts:
        row = {
            "source": "reddit",
            "board_name": f"r/{subreddit}",
            "title": p["title"],
            "url": p["url"],
            "score": p.get("score", 0),
            "comment_count": p.get("num_comments", 0),
            "category": category,
        }
        if p.get("published"):
            row["original_at"] = p["published"]
        if subcategory:
            row["subcategory"] = subcategory
        rows.append(row)

    client.table("posts").upsert(rows, on_conflict="url").execute()
    return len(rows)


def run(category: str = "gaming", subreddits: list = None, min_score: int = 0, subcategory: str = None):
    if subreddits is None:
        subreddits = ["gaming", "Games"]

    total_fetched = 0
    total_saved = 0
    for sub in subreddits:
        print(f"  r/{sub} 크롤링 중...")
        posts = fetch_subreddit_hot(sub)
        total_fetched += len(posts)

        # min_score 필터
        if min_score > 0:
            filtered = [p for p in posts if p.get("score", 0) >= min_score]
        else:
            filtered = posts

        saved = save_posts(filtered, sub, category, subcategory)
        total_saved += saved
        print(f"  → 조회 {len(posts)}건 / min_score≥{min_score} 통과 {saved}건 저장")
        time.sleep(2)

    print(f"Reddit 크롤링 완료: {category}/{subcategory} - 조회 {total_fetched}, 저장 {total_saved}")
    return total_saved


if __name__ == "__main__":
    run()
