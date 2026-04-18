"""
쇼츠 소재 선별 자동화 스크립트

사용법:
  python select_materials.py                          # 전체 카테고리, 서브카테고리별 TOP 10
  python select_materials.py --category engineering    # 공학/과학만
  python select_materials.py --category gaming         # 게임만
  python select_materials.py --subcategory 산업/중장비  # 특정 서브카테고리만 (--category와 함께 사용)
  python select_materials.py --top 5                   # 서브카테고리별 TOP 5
  python select_materials.py --detail                  # Reddit 원문 상세 포함
  python select_materials.py --url <URL>               # 특정 Reddit URL 1건만 상세 조회

Reddit 글은 RSS 수집 시 score=0으로 저장됨.
이 스크립트는 Reddit 글에 대해 JSON API로 실시간 score를 단건 조회하여
정렬과 출력에 반영합니다 (DB는 수정하지 않음).
"""

import sys
import io
import os
import json
import time
import argparse
from pathlib import Path
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent
USED_FILE = PROJECT_ROOT / "scripts" / "used_materials.json"


def load_used_materials():
    """사용 완료 소재 로드

    returns:
        dict with keys:
          - urls: set of URLs (DB 소재 필터링용)
          - direct_proposals: list of {title, subcategory, completed_date} (참고 표시용)
    """
    if not USED_FILE.exists():
        return {"urls": set(), "direct_proposals": []}
    with open(USED_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    urls = set()
    direct_proposals = []
    for item in data.get("used", []):
        source = item.get("source", "db")  # 기본값 "db" (레거시 호환)
        if source == "db" and item.get("url"):
            urls.add(item["url"])
        elif source == "direct_proposal":
            direct_proposals.append({
                "title": item.get("title", "(제목 없음)"),
                "subcategory": item.get("subcategory", ""),
                "completed_date": item.get("completed_date", ""),
            })
    return {"urls": urls, "direct_proposals": direct_proposals}


def get_supabase_client():
    """Supabase 클라이언트 생성"""
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    return create_client(url, key)


def fetch_posts(sb, category=None, subcategory=None, limit=500):
    """DB에서 게시글 조회 (collected_at 내림차순 — score=0인 글도 최신순으로 가져옴)

    루리웹은 2026-04-17부터 크롤링 중단됨 (쇼츠 적합도 낮아 전 카테고리 제외).
    DB 잔여 데이터는 garbage_collector가 자연 소멸시킴.
    """
    query = sb.table("posts").select("*").order("collected_at", desc=True).limit(limit)
    if category:
        query = query.eq("category", category)
    if subcategory:
        query = query.eq("subcategory", subcategory)
    query = query.neq("source", "ruliweb")
    return query.execute().data


def fetch_reddit_score(url):
    """Reddit 게시글의 실시간 score + 댓글 수 (단건 조회)"""
    import httpx
    json_url = url.rstrip("/") + "/.json"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Shorts-Tracker/1.0"}
    try:
        r = httpx.get(json_url, headers=headers, follow_redirects=True, timeout=15)
        if r.status_code != 200:
            return None
        data = r.json()
        post = data[0]["data"]["children"][0]["data"]
        return {
            "score": post.get("score", 0),
            "num_comments": post.get("num_comments", 0),
        }
    except Exception:
        return None


_BOT_AUTHORS = {"AutoModerator"}
_BOT_PATTERNS = (
    "did you find this post really amazing",
    "welcome to r/",
    "this is a heavily moderated subreddit",
    "upvote this comment otherwise",
    "downvote it.",
    "please report",
    "rule breaking posts",
)


def _is_bot_comment(c_data):
    """스티키·AutoModerator·봇 템플릿 댓글 판별"""
    if c_data.get("stickied"):
        return True
    if c_data.get("author") in _BOT_AUTHORS:
        return True
    body = (c_data.get("body") or "").lower().strip()
    if not body:
        return True
    if "[deleted]" in body or "[removed]" in body or "removed by reddit" in body:
        return True
    return any(p in body for p in _BOT_PATTERNS)


def fetch_reddit_detail(url, max_comment_len=200, comment_count=5):
    """Reddit 게시글 상세 정보 (단건 조회) — score + 본문 + 댓글 (봇·스티키 필터링)"""
    import httpx
    json_url = url.rstrip("/") + "/.json"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Shorts-Tracker/1.0"}
    try:
        r = httpx.get(json_url, headers=headers, follow_redirects=True, timeout=15)
        if r.status_code != 200:
            return None
        data = r.json()
        post = data[0]["data"]["children"][0]["data"]
        comments = data[1]["data"]["children"]
        top_comments = []
        # 봇 필터링 후 원하는 개수만큼 확보하기 위해 후보를 넉넉히(최대 30개) 순회
        for c in comments[:30]:
            if c["kind"] != "t1":
                continue
            c_data = c["data"]
            if _is_bot_comment(c_data):
                continue
            top_comments.append(c_data.get("body", "")[:max_comment_len])
            if len(top_comments) >= comment_count:
                break
        return {
            "title": post.get("title", ""),
            "subreddit": post.get("subreddit", ""),
            "selftext": post.get("selftext", ""),
            "media_url": post.get("url", ""),
            "score": post.get("score", 0),
            "num_comments": post.get("num_comments", 0),
            "top_comments": top_comments,
        }
    except Exception:
        return None


def print_single_url_detail(url):
    """--url 옵션: 특정 Reddit URL 1건만 상세 조회 + 출력"""
    print(f"🔍 단건 조회: {url}")
    print()
    detail = fetch_reddit_detail(url, max_comment_len=2000, comment_count=10)
    if not detail:
        print("❌ 조회 실패 (URL이 올바른지, Reddit 게시글이 존재하는지 확인)")
        return 1

    print_separator()
    print(f"📌 r/{detail['subreddit']} — {detail['title']}")
    print_separator()
    print(f"score={detail['score']:,} | comments={detail['num_comments']:,}")
    print(f"media_url={detail['media_url']}")
    print()
    if detail['selftext']:
        print("📝 본문:")
        print(detail['selftext'])
        print()
    if detail['top_comments']:
        print(f"💬 상위 댓글 ({len(detail['top_comments'])}건):")
        for i, c in enumerate(detail['top_comments'], 1):
            print(f"  [{i}] {c}")
            print()
    return 0


def enrich_reddit_scores(by_subcat, top_n):
    """서브카테고리별 상위 후보 Reddit 글만 score 보강 (전수 조회 방지)

    전략: 각 서브카테고리에서 Reddit score=0인 글을 최대 top_n개만 보강.
    비Reddit 글(루리웹/인벤 등)은 이미 score가 있으므로 건너뜀.
    """
    total_to_enrich = 0
    for subcat, posts in by_subcat.items():
        reddit_zero = [p for p in posts if p["source"] == "reddit" and (p.get("score") or 0) == 0]
        total_to_enrich += min(len(reddit_zero), top_n)

    if total_to_enrich == 0:
        return

    print(f"🔄 Reddit score 보강 중... (서브카테고리별 최대 {top_n}건, 총 ~{total_to_enrich}건)")
    enriched = 0
    for subcat, posts in by_subcat.items():
        reddit_zero = [p for p in posts if p["source"] == "reddit" and (p.get("score") or 0) == 0]
        for p in reddit_zero[:top_n]:
            result = fetch_reddit_score(p["url"])
            if result:
                p["score"] = result["score"]
                p["comment_count"] = result["num_comments"]
                p["_enriched"] = True
                enriched += 1
            time.sleep(0.3)
    print(f"   → {enriched}건 보강 완료")
    print()


def print_separator():
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="쇼츠 소재 선별 자동화")
    parser.add_argument("--category", type=str, default=None, help="카테고리 필터 (engineering/gaming/baseball)")
    parser.add_argument("--subcategory", type=str, default=None, help="서브카테고리 필터 (--category와 함께 사용 권장)")
    parser.add_argument("--top", type=int, default=10, help="서브카테고리별 표시 개수 (기본: 10)")
    parser.add_argument("--detail", action="store_true", help="Reddit 원문 상세 포함")
    parser.add_argument("--no-enrich", action="store_true", help="Reddit score 보강 건너뛰기 (빠른 조회)")
    parser.add_argument("--url", type=str, default=None, help="특정 Reddit URL 1건만 상세 조회 (다른 옵션 무시)")
    args = parser.parse_args()

    # --url 단건 조회 분기 (다른 옵션 무시)
    if args.url:
        sys.exit(print_single_url_detail(args.url))

    # 1. 사용 완료 소재 로드
    used = load_used_materials()
    used_urls = used["urls"]
    direct_proposals = used["direct_proposals"]
    print(f"📋 사용 완료 소재(DB): {len(used_urls)}건 (URL 자동 제외)")
    if direct_proposals:
        print(f"📋 직접 제안 완료: {len(direct_proposals)}건 (참고용 — 중복 제안 방지)")
        for dp in direct_proposals:
            print(f"   • [{dp['subcategory']}] {dp['title']} ({dp['completed_date']})")
    print()

    # 2. DB 조회
    sb = get_supabase_client()
    posts = fetch_posts(sb, category=args.category, subcategory=args.subcategory)
    filter_desc = []
    if args.category:
        filter_desc.append(f"category={args.category}")
    if args.subcategory:
        filter_desc.append(f"subcategory={args.subcategory}")
    filter_str = f" ({', '.join(filter_desc)})" if filter_desc else ""
    print(f"📊 DB 조회{filter_str}: {len(posts)}건")

    # 3. 사용 완료 소재 제외
    filtered = [p for p in posts if p["url"] not in used_urls]
    excluded = len(posts) - len(filtered)
    if excluded > 0:
        print(f"🚫 사용 완료 제외: {excluded}건")
    print()

    # 4. 서브카테고리별 그룹핑 (보강 전에 먼저 그룹핑)
    by_subcat = defaultdict(list)
    for p in filtered:
        subcat = p.get("subcategory") or "미분류"
        by_subcat[subcat].append(p)

    # 5. Reddit score 보강 (서브카테고리별 상위 top_n개만)
    if not args.no_enrich:
        enrich_reddit_scores(by_subcat, args.top)

    # 6. 출력 (score 내림차순 정렬 — 보강된 실시간 score 반영)
    for subcat in sorted(by_subcat.keys()):
        sub_posts = by_subcat[subcat]
        sub_posts.sort(key=lambda x: x.get("score", 0) or 0, reverse=True)

        print_separator()
        print(f"📂 [{subcat}] — {len(sub_posts)}건 (상위 {args.top}개 표시)")
        print_separator()

        for i, p in enumerate(sub_posts[: args.top], 1):
            score = p.get("score", 0) or 0
            comments = p.get("comment_count", 0) or 0
            source = p["source"]
            enriched_tag = " 🔄" if p.get("_enriched") else ""
            print(f"  {i}. [{source}] {p['title']}")
            print(f"     score={score:,} | comments={comments:,}{enriched_tag}")
            print(f"     url={p['url']}")

            # Reddit 상세 조회 (--detail)
            if args.detail and source == "reddit":
                detail = fetch_reddit_detail(p["url"], comment_count=3)
                if detail:
                    if detail["selftext"]:
                        print(f"     📝 본문: {detail['selftext'][:150]}...")
                    for j, c in enumerate(detail["top_comments"][:3], 1):
                        print(f"     💬 TOP{j}: {c[:150]}...")
            print()

    # 7. 요약
    print_separator()
    total = sum(len(v) for v in by_subcat.values())
    print(f"✅ 총 {total}건 후보 (사용 완료 {len(used_urls)}건 제외됨)")
    print(f"📁 사용 완료 목록: {USED_FILE}")


if __name__ == "__main__":
    main()
