"""
전체 크롤러 실행 진입점 — GitHub Actions에서 호출
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlers import reddit_crawler, ruliweb_crawler, hackernews_crawler, youtube_crawler

def main():
    print("=" * 50)
    print("전체 크롤링 시작")
    print("=" * 50)

    print("\n[1/4] Reddit")
    reddit_crawler.run(
        category="gaming",
        subreddits=["gaming", "Games", "GlobalOffensive", "leagueoflegends"],
        min_score=100,
    )

    print("\n[2/4] 루리웹")
    ruliweb_crawler.run(
        category="gaming",
        urls=["https://bbs.ruliweb.com/news/board/1003"],
        min_hit=100,
    )

    print("\n[3/4] Hacker News")
    hackernews_crawler.run(
        category="it_gadgets",
        min_score=100,
    )

    print("\n[4/4] YouTube 급상승")
    youtube_crawler.run(
        category="gaming",
        countries=["KR", "JP", "US"],
        period="daily",
    )

    print("\n" + "=" * 50)
    print("전체 크롤링 완료!")
    print("=" * 50)

if __name__ == "__main__":
    main()
