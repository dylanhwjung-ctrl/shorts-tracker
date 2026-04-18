# CLAUDE.md — Shorts Trend Tracker 프로젝트 하네스

> **이 파일은 AI 에이전트(Claude)가 작업 맥락을 잃지 않도록 설계된 핵심 지침서입니다.**
> 새 대화를 시작해도 이 파일을 읽으면 프로젝트 전체 상황을 즉시 파악합니다.

---

## 프로젝트 개요

**프로젝트명:** Shorts Trend Tracker  
**목적:** 유튜브 쇼츠 콘텐츠 기획자가 온라인 커뮤니티 화제글과 유튜브 급상승 영상을 한 눈에 보고 소재를 발굴하는 웹 대시보드  
**작업 폴더:** `tracker/` — 데스크톱 `E:\tracker` / 맥 `~/tracker` (Synology junction으로 양쪽 기기 공유)  
**사용자 레벨:** 코딩 완전 초보자 (명령어 한 줄씩 안내 필요)

---

## 확정된 기술 스택

| 역할 | 기술 | 버전 | 비고 |
|------|------|------|------|
| 언어 | Python | 3.11+ | |
| UI/대시보드 | Streamlit | latest | Streamlit Community Cloud 무료 배포 |
| 데이터베이스 | Supabase | - | PostgreSQL, 무료 티어 500MB |
| 자동화/스케줄링 | GitHub Actions | - | 크론 잡, 무료 2000분/월 |
| Reddit 크롤링 | PRAW | latest | 공식 API |
| 웹 스크래핑 | httpx + BeautifulSoup4 | latest | 인벤, FM코리아 (루리웹은 2026-04-17 제거) |
| 디시인사이드 | 비공식 모바일 API | - | 우선순위 낮음, 나중에 추가 |
| YouTube | google-api-python-client | latest | 공식 Data API v3 |
| AI 판단 | Anthropic Claude API (Haiku) | latest | 쇼츠 소재 적합성 판단 |
| DB 클라이언트 | supabase-py | latest | |
| 환경변수 관리 | python-dotenv | latest | |

---

## 디렉토리 구조

```
tracker/                         # 데스크톱 E:\tracker / 맥 ~/tracker (junction)
├── CLAUDE.md                    # 이 파일 (하네스)
├── .env                         # API 키 모음 (절대 GitHub에 올리지 말 것!)
├── .gitignore                   # .env 등 민감 파일 제외 설정
├── requirements.txt             # Python 패키지 목록
├── streamlit_app.py             # 메인 대시보드 진입점
│
├── config/
│   └── category_profiles/       # 카테고리 프로필 폴더
│       ├── gaming.yaml          # 게임 카테고리 프로필
│       ├── movies.yaml          # 영화 카테고리 프로필
│       └── it_gadgets.yaml      # IT기기 카테고리 프로필
│
├── crawlers/                    # 각 소스별 크롤러 모듈
│   ├── __init__.py
│   ├── reddit_crawler.py
│   ├── ruliweb_crawler.py       # 2026-04-17 비활성 (run_all.py에서 미호출)
│   ├── inven_crawler.py
│   ├── fmkorea_crawler.py
│   ├── dcinside_crawler.py      # 나중에 추가
│   └── youtube_crawler.py
│
├── database/                    # DB 연동 모듈
│   ├── __init__.py
│   ├── client.py                # Supabase 연결
│   ├── models.py                # 테이블 스키마 정의
│   └── garbage_collector.py    # 7일 이상 오래된 데이터 자동 삭제
│
├── ai/                          # AI 판단 모듈
│   ├── __init__.py
│   └── shorts_evaluator.py     # Claude API로 쇼츠 소재 적합성 판단
│
├── ui/                          # Streamlit UI 컴포넌트
│   ├── __init__.py
│   ├── community_tab.py
│   └── youtube_tab.py
│
└── .github/
    └── workflows/
        ├── crawl_schedule.yml   # 크롤링 자동 실행 (6시간마다)
        └── garbage_collect.yml  # 가비지 컬렉션 (매일 새벽 3시)
```

---

## 데이터베이스 스키마 (Supabase)

### 테이블 1: `posts` (커뮤니티 게시글)
```sql
CREATE TABLE posts (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source        TEXT NOT NULL,        -- 'reddit', 'ruliweb', 'inven', 'fmkorea', 'dcinside'
  board_name    TEXT,                 -- 게시판 이름 (예: '게임게시판', 'r/gaming')
  title         TEXT NOT NULL,        -- 게시글 제목
  url           TEXT UNIQUE NOT NULL, -- 원문 링크 (중복 방지)
  score         INTEGER DEFAULT 0,    -- 추천수/좋아요
  comment_count INTEGER DEFAULT 0,    -- 댓글수
  category      TEXT NOT NULL,        -- 'gaming', 'movies', 'it_gadgets'
  ai_score      SMALLINT,             -- AI 쇼츠 적합도 점수 (1~10)
  ai_reason     TEXT,                 -- AI 판단 이유
  collected_at  TIMESTAMPTZ DEFAULT NOW(),
  original_at   TIMESTAMPTZ           -- 원본 게시글 작성 시간
);

-- 7일 지난 데이터 자동 삭제를 위한 인덱스
CREATE INDEX idx_posts_collected_at ON posts (collected_at);
```

### 테이블 2: `youtube_videos` (유튜브 급상승 영상)
```sql
CREATE TABLE youtube_videos (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id       TEXT NOT NULL,        -- 유튜브 영상 ID
  title          TEXT NOT NULL,
  channel_name   TEXT,
  country        TEXT NOT NULL,        -- 'KR', 'JP', 'US'
  period         TEXT NOT NULL,        -- 'daily', 'weekly'
  views          BIGINT DEFAULT 0,
  view_increase  BIGINT DEFAULT 0,     -- 기간 내 조회수 증가량
  category       TEXT NOT NULL,
  collected_date DATE DEFAULT CURRENT_DATE,
  collected_at   TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (video_id, period, collected_date)
);
```

### 테이블 3: `category_profiles` (카테고리 프로필 메타데이터)
```sql
CREATE TABLE category_profiles (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug         TEXT UNIQUE NOT NULL,  -- 'gaming', 'movies', 'it_gadgets'
  display_name TEXT NOT NULL,         -- '게임', '영화', 'IT기기'
  is_active    BOOLEAN DEFAULT TRUE,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 카테고리 프로필 구조 (YAML)

각 카테고리는 `config/category_profiles/` 폴더 안에 **YAML 파일 하나**로 정의됩니다.
카테고리를 바꾸면 [타겟 게시판 URL + 필터링 조건 + AI 프롬프트]가 통째로 교체됩니다.

**예시: `gaming.yaml`**
```yaml
slug: gaming
display_name: 게임
sources:
  reddit:
    subreddits: [gaming, Games, GlobalOffensive, leagueoflegends]
    min_score: 500
    min_comments: 50
  inven:
    urls:
      - https://www.inven.co.kr/board/issue
    min_recommend: 5
  fmkorea:
    urls:
      - https://www.fmkorea.com/best
    categories: [게임]
    min_recommend: 100
  youtube:
    countries: [KR, JP, US]
    keywords: [게임, gaming, ゲーム]

ai_prompt: |
  당신은 유튜브 쇼츠 전문 기획자입니다.
  아래 게시글이 '게임' 분야의 유튜브 쇼츠(60초 이내 세로 영상) 소재로 적합한지 평가하세요.
  
  평가 기준:
  1. 시각적으로 표현 가능한가? (게임플레이, 이벤트, 반응 등)
  2. 60초 이내로 핵심을 전달할 수 있는가?
  3. 한국 시청자가 흥미를 느낄 만한가?
  4. 논란/분쟁 소지가 없는가?
  
  결과를 JSON으로 반환하세요:
  {"score": 1~10, "reason": "한 줄 이유", "shorts_angle": "쇼츠로 만든다면 어떤 각도로?"}
```

---

## 가비지 컬렉션 정책

- **posts 테이블:** `collected_at` 기준 **7일 초과** 데이터 자동 삭제
- **youtube_videos 테이블:** `collected_at` 기준 **7일 초과** 데이터 자동 삭제
- **실행 주기:** 매일 새벽 3시 (GitHub Actions `garbage_collect.yml`)

---

## 프로젝트 마일스톤

| 단계 | 내용 | 상태 |
|------|------|------|
| M1 | 개발 환경 + DB 세팅 | ✅ 완료 |
| M2 | 크롤러 구축 + GitHub Actions 자동화 | 진행 중 |
| M3 | 카테고리 프로필 시스템 + AI 판단 연동 | 대기 |
| M4 | Streamlit 대시보드 UI + 배포 | 대기 |

## 크롤러 현황

| 소스 | 파일 | 상태 |
|------|------|------|
| Reddit | crawlers/reddit_crawler.py | ✅ 작동 (공개 JSON API) |
| 루리웹 | crawlers/ruliweb_crawler.py | ⏸ 2026-04-17 비활성 (쇼츠 적합도 낮음) |
| Hacker News | crawlers/hackernews_crawler.py | ✅ 작동 (공식 API) |
| YouTube | crawlers/youtube_crawler.py | ✅ 작동 |
| FM코리아 | crawlers/fmkorea_crawler.py | ⏸ 보류 — 430 봇 차단, Playwright 필요 |
| 디시인사이드 | crawlers/dcinside_crawler.py | ⏸ 보류 — 차단 심함 |

---

## AI 에이전트 필수 행동 지침

> **이 섹션은 Claude가 반드시 준수해야 할 규칙입니다.**

1. **한 번에 하나씩:** 여러 작업을 동시에 지시하지 말 것. 한 단계 완료 후 사용자의 확인을 받고 다음 단계로 진행할 것.

2. **복붙 가능한 명령어:** 모든 터미널 명령어는 그대로 복사-붙여넣기 할 수 있는 정확한 형태로 제공할 것. "설치하세요" 같은 모호한 표현 금지.

3. **에러 대응:** 에러 발생 시 "에러 메시지 전체를 복사해서 저에게 붙여넣어 주세요"라고 안내할 것.

4. **파일 경로 명시:** 파일은 기본적으로 `tracker/파일명` 상대 경로로 명시. OS별 실행 커맨드나 절대경로가 필요한 경우(복붙용 터미널 명령 등)만 데스크톱 `E:\tracker\...` / 맥 `~/tracker/...` 양쪽 병기.

5. **단계 확인:** 각 마일스톤의 하위 작업 완료 시 "✅ 완료! 다음은 [다음 작업]입니다. 진행할까요?" 형태로 확인 후 진행.

6. **보안 주의:** `.env` 파일에 API 키를 저장하며, 절대 GitHub에 `.env`를 올리지 않도록 항상 경고할 것.

7. **컨텍스트 복구:** 새 대화 시작 시 반드시 이 CLAUDE.md를 먼저 읽고 현재 단계를 파악한 후 작업 시작.
