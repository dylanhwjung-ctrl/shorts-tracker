"""
전체 크롤러 실행 진입점 — GitHub Actions에서 호출
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlers import reddit_crawler, ruliweb_crawler, youtube_crawler


def main():
    print("=" * 50)
    print("전체 크롤링 시작")
    print("=" * 50)

    # ── 게임 카테고리 ──────────────────────────────
    print("\n[1/5] Reddit (게임 스토리/덕질 커뮤니티)")
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

    print("\n[2/5] 루리웹 (게임 게시판)")
    ruliweb_crawler.run(
        category="gaming",
        urls=["https://bbs.ruliweb.com/game"],
        min_hit=100,
    )

    print("\n[3/5] YouTube 급상승 (게임)")
    youtube_crawler.run(
        category="gaming",
        countries=["KR", "JP", "US"],
        period="daily",
    )

    # ── 공학/과학 카테고리 ─────────────────────────
    print("\n[4/5] Reddit (공학/과학/밀리터리)")
    reddit_crawler.run(
        category="engineering",
        subreddits=[
            "interestingasfuck",    # 흥미로운 산업/공학 영상
            "Damnthatsinteresting", # 놀라운 사실/현상
            "educationalgifs",      # 시각적 원리 설명
            "oddlysatisfying",      # 기계/공정 영상
            "todayilearned",        # 몰랐던 사실 (TIL)
            "military",             # 군사/무기 체계
            "engineering",          # 공학 토론
        ],
        min_score=500,
    )

    print("\n[5/5] YouTube 급상승 (과학/기술)")
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
