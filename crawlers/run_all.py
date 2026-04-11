"""
전체 크롤러 실행 진입점 — GitHub Actions에서 호출
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlers import reddit_crawler, ruliweb_crawler, youtube_crawler, hackernews_crawler


def main():
    print("=" * 50)
    print("전체 크롤링 시작")
    print("=" * 50)

    # ── 게임 카테고리 ──────────────────────────────
    print("\n[1/7] Reddit (게임 스토리/덕질 커뮤니티)")
    reddit_crawler.run(
        category="gaming",
        subreddits=[
            "patientgamers",        # 명작 게임 감상/토론
            "truegaming",           # 게임 스토리/분석 심층 토론
            "reddeadredemption",    # 레드데드 리뎀션
            "thelastofus",          # 더 라스트 오브 어스
            "darkestdungeon",       # 다키스트 던전
            "residentevil",         # 바이오하자드
            "detroitbecomehuman",   # 디트로이트 비컴 휴먼
        ],
        min_score=100,
    )

    print("\n[2/7] 루리웹 (게임 게시판)")
    ruliweb_crawler.run(
        category="gaming",
        urls=["https://bbs.ruliweb.com/game"],
        min_hit=100,
    )

    print("\n[3/7] YouTube 급상승 (게임)")
    youtube_crawler.run(
        category="gaming",
        countries=["KR", "JP", "US"],
        period="daily",
    )

    # ── 공학/과학 카테고리 ─────────────────────────
    print("\n[4/7] Reddit (공학/과학/밀리터리)")
    reddit_crawler.run(
        category="engineering",
        subreddits=[
            "interestingasfuck",    # 산업 현장·중장비·특수 기술
            "Damnthatsinteresting", # 공학 원리·놀라운 사실
            "educationalgifs",      # 시각적 원리 설명
            "oddlysatisfying",      # 기계 공정·제조 과정
            "todayilearned",        # 몰랐던 과학/공학 사실 (TIL)
            "military",             # 군사·무기 체계·비하인드
            "engineering",          # 공학 토론
            "MachinePorn",          # 기계 내부 구조·역사 장비
            "mechanical_gifs",      # 기계 작동 원리 GIF
            "InfrastructurePorn",   # 댐·교량·철도 인프라
            "aviation",             # 항공·전투기
        ],
        min_score=500,
    )

    print("\n[5/7] Hacker News (공학/기술 심층 토론)")
    hackernews_crawler.run(
        category="engineering",
        min_score=200,
    )

    print("\n[6/7] 루리웹 (밀리터리/역사 게시판)")
    ruliweb_crawler.run(
        category="engineering",
        urls=["https://bbs.ruliweb.com/hobby/board/300143"],  # 밀리터리 게시판
        min_hit=50,
    )

    print("\n[7/7] YouTube 급상승 (과학/기술)")
    youtube_crawler.run(
        category="engineering",
        countries=["KR", "US"],
        period="daily",
    )

    print("\n" + "=" * 50)
    print("전체 크롤링 완료!")
    print("=" * 50)


if __name__ == "__main__":
    main()
