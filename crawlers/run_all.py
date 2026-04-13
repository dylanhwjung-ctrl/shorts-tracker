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
    print("\n[1/7] Reddit 게임 감상/토론")
    reddit_crawler.run(
        category="gaming",
        subcategory="게임 감상/토론",
        subreddits=[
            "patientgamers",
            "truegaming",
            "Games",                 # 밈 금지 규칙 → 텍스트 품질 높음 (~3.2M)
        ],
        min_score=100,
    )

    print("\n[2/7] Reddit 게임 IP 덕질")
    reddit_crawler.run(
        category="gaming",
        subcategory="게임 IP 덕질",
        subreddits=[
            "reddeadredemption",
            "thelastofus",
            "darkestdungeon",
            "residentevil",
            "detroitbecomehuman",
            "Eldenring",             # 프롬소프트 로어 분석의 성지 (~2.3M)
            "bloodborne",            # 러브크래프트적 세계관 해석 (~412K)
            "darksouls",             # 시리즈 전체 로어 통합 분석 (~586K)
            "HollowKnight",          # 인디 게임 로어의 대표 (~1.2M)
            "Fallout",               # 터미널 로그, 환경 스토리텔링 (~1.9M)
            "witcher",               # 게임+소설+드라마 통합 로어 (~1.3M)
            "metalgearsolid",        # 코지마 게임 복잡한 스토리 해석 (~271K)
        ],
        min_score=100,
    )

    print("\n[3/7] Reddit 게임 로어/세계관")
    reddit_crawler.run(
        category="gaming",
        subcategory="게임 로어/세계관",
        subreddits=[
            "teslore",               # 엘더스크롤 로어 전문 (~155K)
            "falloutlore",           # 폴아웃 로어 전문 (~197K)
            "FanTheories",           # 팬 이론 — 게임 포함 (~2.2M)
        ],
        min_score=50,
    )

    print("\n[4/7] Reddit 게임 비하인드")
    reddit_crawler.run(
        category="gaming",
        subcategory="게임 비하인드",
        subreddits=[
            "gamedev",               # 개발자 직접 참여 비하인드 스토리 (~1.9M)
            "lostmedia",             # 사라진 게임/미출시 프로토타입 (~361K)
            "TheMakingOfGames",      # 게임 제작 비하인드 전문 (~22K)
        ],
        min_score=50,
    )

    print("\n[5/7] Reddit 게임 이스터에그")
    reddit_crawler.run(
        category="gaming",
        subcategory="게임 이스터에그",
        subreddits=[
            "GamingDetails",         # 숨겨진 디테일 전문 — 게시물=쇼츠 소재 (~263K)
            "creepygaming",          # 소름끼치는 숨겨진 요소 전문 (~167K)
        ],
        min_score=50,
    )

    print("\n[6/7] 루리웹 게임 뉴스 (PC)")
    ruliweb_crawler.run(
        category="gaming",
        subcategory="게임 뉴스",
        urls=["https://bbs.ruliweb.com/pc/board/300007"],
        board_name="루리웹_PC게임",
        min_hit=50,
    )

    print("\n[7/7] 루리웹 게임 뉴스 (PS)")
    ruliweb_crawler.run(
        category="gaming",
        subcategory="게임 뉴스",
        urls=["https://bbs.ruliweb.com/ps/board/300001"],
        board_name="루리웹_PS게임",
        min_hit=50,
    )

    # ── 공학/과학 카테고리 ─────────────────────────
    print("\n[5/9] Reddit 산업/중장비")
    reddit_crawler.run(
        category="engineering",
        subcategory="산업/중장비",
        subreddits=[
            "MachinePorn",
            "InfrastructurePorn",
            "oddlysatisfying",
            "specializedtools",      # 특수 목적 도구/장비
            "EngineeringPorn",       # 제조 공정, 대형 구조물
            "ArtisanVideos",         # 장인 기술/가공 과정
            "Skookum",               # 중장비 매니아 커뮤니티
        ],
        min_score=200,
    )

    print("\n[6/9] Reddit 공학/기계")
    reddit_crawler.run(
        category="engineering",
        subcategory="공학/기계",
        subreddits=[
            "engineering",
            "mechanical_gifs",
            "CatastrophicFailure",   # 공학 실패 사례 — 내러티브 풍부
            "AskEngineers",          # 공학 Q&A, 비하인드 스토리
            "ThingsCutInHalfPorn",   # 단면도 — "내부는 이렇게 생겼다"
            "BeAmazed",              # 놀라운 공학/기술
        ],
        min_score=200,
    )

    print("\n[7/9] Reddit + 루리웹 밀리터리")
    reddit_crawler.run(
        category="engineering",
        subcategory="밀리터리",
        subreddits=[
            "military",
            "aviation",
            "CredibleDefense",       # 심층 군사 분석
            "WeirdWings",            # 특이한 항공기
            "WarplanePorn",          # 군용기 전문
        ],
        min_score=200,
    )
    ruliweb_crawler.run(
        category="engineering",
        subcategory="밀리터리",
        urls=["https://bbs.ruliweb.com/hobby/board/300143"],
        board_name="루리웹_밀리터리",
        min_hit=50,
    )

    print("\n[8/9] Reddit 소방/안전")
    reddit_crawler.run(
        category="engineering",
        subcategory="소방/안전",
        subreddits=[
            "Firefighting",
            "OSHA",                  # 안전 위반 사례 (~827K)
            "SweatyPalms",           # 아찔한 순간 — 안전 교훈
        ],
        min_score=50,
    )

    print("\n[9/9] Reddit 과학/자연")
    reddit_crawler.run(
        category="engineering",
        subcategory="과학/자연",
        subreddits=[
            "interestingasfuck",
            "Damnthatsinteresting",
            "educationalgifs",
            "todayilearned",
            "space",                 # 우주/천문
            "science",               # 논문 기반 과학
            "NatureIsFuckingLit",    # 극적 자연 현상
            "AskScience",            # 전문가 답변 Q&A
        ],
        min_score=500,
    )

    # ── MLB 야구 ───────────────────────────────────────
    print("\n[MLB 1/2] Reddit MLB 뉴스/토론")
    reddit_crawler.run(
        category="baseball",
        subcategory="MLB 뉴스/토론",
        subreddits=[
            "baseball",
            "mlb",                   # r/baseball과 겹치지 않는 콘텐츠 (~3M)
        ],
        min_score=500,
    )

    print("\n[MLB 2/2] Reddit MLB 팀 커뮤니티")
    reddit_crawler.run(
        category="baseball",
        subcategory="MLB 팀 커뮤니티",
        subreddits=[
            "NYYankees",             # MLB 팀 서브 최대, 양키스=MLB 역사 (~409K)
            "Dodgers",               # 오타니 효과 → 한국 시청자 친숙 (~347K)
        ],
        min_score=200,
    )

    # ── 해외 채널 트래커 ───────────────────────────────
    print("\n[채널] 해외 채널 통계 갱신")
    channel_crawler.run(category="engineering", mode="update")

    print("\n" + "=" * 50)
    print("전체 크롤링 완료!")
    print("=" * 50)


if __name__ == "__main__":
    main()
