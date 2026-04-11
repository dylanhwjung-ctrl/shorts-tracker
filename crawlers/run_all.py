"""
전체 크롤러 실행 진입점 — GitHub Actions에서 호출
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlers import reddit_crawler, ruliweb_crawler, channel_crawler


def main():
    print("=" * 50)
    print("전체 크롤링 시작")
    print("=" * 50)

    # ── 게임 카테고리 ──────────────────────────────
    print("\n[1/3] Reddit 게임 감상/토론")
    reddit_crawler.run(
        category="gaming",
        subcategory="게임 감상/토론",
        subreddits=[
            "patientgamers",
            "truegaming",
        ],
        min_score=100,
    )

    print("\n[2/3] Reddit 게임 IP 덕질")
    reddit_crawler.run(
        category="gaming",
        subcategory="게임 IP 덕질",
        subreddits=[
            "reddeadredemption",
            "thelastofus",
            "darkestdungeon",
            "residentevil",
            "detroitbecomehuman",
        ],
        min_score=100,
    )

    print("\n[3/4] 루리웹 게임 뉴스 (PC)")
    ruliweb_crawler.run(
        category="gaming",
        subcategory="게임 뉴스",
        urls=["https://bbs.ruliweb.com/pc/board/300007"],
        board_name="루리웹_PC게임",
        min_hit=50,
    )

    print("\n[4/4] 루리웹 게임 뉴스 (PS)")
    ruliweb_crawler.run(
        category="gaming",
        subcategory="게임 뉴스",
        urls=["https://bbs.ruliweb.com/ps/board/300001"],
        board_name="루리웹_PS게임",
        min_hit=50,
    )

    # ── 공학/과학 카테고리 ─────────────────────────
    print("\n[4/8] Reddit 산업/중장비")
    reddit_crawler.run(
        category="engineering",
        subcategory="산업/중장비",
        subreddits=[
            "MachinePorn",
            "InfrastructurePorn",
            "oddlysatisfying",
        ],
        min_score=300,
    )

    print("\n[5/8] Reddit 공학/기계")
    reddit_crawler.run(
        category="engineering",
        subcategory="공학/기계",
        subreddits=[
            "engineering",
            "mechanical_gifs",
        ],
        min_score=200,
    )

    print("\n[6/8] Reddit + 루리웹 밀리터리")
    reddit_crawler.run(
        category="engineering",
        subcategory="밀리터리",
        subreddits=[
            "military",
            "aviation",
        ],
        min_score=300,
    )
    ruliweb_crawler.run(
        category="engineering",
        subcategory="밀리터리",
        urls=["https://bbs.ruliweb.com/hobby/board/300143"],
        board_name="루리웹_밀리터리",
        min_hit=50,
    )

    print("\n[7/8] Reddit 소방/안전")
    reddit_crawler.run(
        category="engineering",
        subcategory="소방/안전",
        subreddits=[
            "Firefighting",
            "CERT",
        ],
        min_score=50,
    )

    print("\n[8/8] Reddit 과학/자연")
    reddit_crawler.run(
        category="engineering",
        subcategory="과학/자연",
        subreddits=[
            "interestingasfuck",
            "Damnthatsinteresting",
            "educationalgifs",
            "todayilearned",
        ],
        min_score=500,
    )

    # ── MLB 야구 ───────────────────────────────────────
    print("\n[MLB] Reddit r/baseball")
    reddit_crawler.run(
        category="baseball",
        subcategory="MLB 뉴스/토론",
        subreddits=["baseball"],
        min_score=500,
    )

    # ── 해외 채널 트래커 ───────────────────────────────
    print("\n[채널] 해외 채널 통계 갱신")
    channel_crawler.run(category="engineering", mode="update")

    print("\n" + "=" * 50)
    print("전체 크롤링 완료!")
    print("=" * 50)


if __name__ == "__main__":
    main()
