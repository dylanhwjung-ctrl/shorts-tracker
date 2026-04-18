"""
사용 완료 소재 등록 CLI

사용법:
  # DB 기반 소재 (URL로 자동 추론)
  python scripts/mark_used.py \
    --url <URL> \
    --plan 07_기술/기획안/YYYY-MM-DD_소재_기획안.md \
    --script 07_기술/대본/YYYY-MM-DD_소재_대본.md

  # 직접 제안 소재
  python scripts/mark_used.py --direct \
    --title "소재 제목" \
    --category engineering \
    --subcategory "산업/중장비" \
    --plan <plan_path> --script <script_path>

옵션:
  --date YYYY-MM-DD  완료 날짜 (기본: 오늘)
  --force            중복 체크 무시
  --dry-run          저장 안 하고 추가될 JSON만 미리보기

스키마(옵션 B): {source, url, title, category, subcategory, completed_date, plan_file, script_file}
경로 규칙: plan/script는 Synology 루트(02_youtube/) 기준 상대경로. 절대경로는 거부.
"""

import sys
import io
import os
import json
import argparse
from datetime import date as date_cls
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

PROJECT_ROOT = Path(__file__).parent.parent
USED_FILE = PROJECT_ROOT / "scripts" / "used_materials.json"


def synology_root():
    """데스크톱/맥 양쪽 Synology 루트 자동 탐지"""
    candidates = [
        Path("F:/SynologyDrive/현욱/02_youtube"),
        Path.home() / "SynologyDrive" / "02_youtube",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def load_used():
    if not USED_FILE.exists():
        return {"used": []}
    with open(USED_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_used(data):
    with open(USED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def fetch_from_db(url):
    """Supabase에서 URL로 게시글 조회. 실패 시 None."""
    try:
        from dotenv import load_dotenv
        load_dotenv(PROJECT_ROOT / ".env")
        from supabase import create_client
    except ImportError:
        return None

    sb_url = os.getenv("SUPABASE_URL")
    sb_key = os.getenv("SUPABASE_ANON_KEY")
    if not sb_url or not sb_key:
        return None

    try:
        sb = create_client(sb_url, sb_key)
        res = sb.table("posts").select("title, category, subcategory").eq("url", url).execute()
        rows = res.data or []
        return rows[0] if rows else None
    except Exception as e:
        print(f"⚠️  Supabase 조회 실패: {e}")
        return None


def reject_absolute_path(path, kind):
    if Path(path).is_absolute():
        print(f"❌ --{kind}는 Synology 상대경로로 전달하세요 (예: 07_기술/기획안/2026-04-18_소재_기획안.md)", file=sys.stderr)
        print(f"   절대경로는 OS 의존이라 거부됩니다: {path}", file=sys.stderr)
        sys.exit(2)


def warn_if_file_missing(rel_path, kind):
    root = synology_root()
    if root is None:
        print(f"⚠️  Synology 루트를 찾지 못함 — {kind} 존재 확인 생략")
        return
    full = root / rel_path
    if not full.exists():
        print(f"⚠️  {kind} 파일 없음: {full}  (경로 선등록이면 무시)")


def find_duplicate(data, entry):
    for item in data.get("used", []):
        if entry["source"] == "db" and item.get("source", "db") == "db":
            if item.get("url") == entry["url"]:
                return item
        elif entry["source"] == "direct_proposal" and item.get("source") == "direct_proposal":
            if item.get("title") == entry["title"] and item.get("completed_date") == entry["completed_date"]:
                return item
    return None


def build_parser():
    p = argparse.ArgumentParser(
        description="사용 완료 소재 등록",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--url", help="원문 URL (DB 모드)")
    mode.add_argument("--direct", action="store_true", help="직접 제안 소재 플래그")

    p.add_argument("--title", help="소재 제목 (direct 필수, DB는 자동 추론 실패 시만)")
    p.add_argument("--category", help="카테고리 (engineering / gaming / ...)")
    p.add_argument("--subcategory", default="", help="서브카테고리")
    p.add_argument("--plan", required=True, help="기획안 Synology 상대경로")
    p.add_argument("--script", required=True, help="대본 Synology 상대경로")
    p.add_argument("--date", default=date_cls.today().isoformat(), help="완료 날짜 (기본: 오늘)")
    p.add_argument("--force", action="store_true", help="중복 체크 무시")
    p.add_argument("--dry-run", action="store_true", help="저장 안 하고 미리보기")
    return p


def main():
    args = build_parser().parse_args()

    reject_absolute_path(args.plan, "plan")
    reject_absolute_path(args.script, "script")

    # 1. 중복 체크 먼저 (자동 추론 전) — DB GC로 DB에선 사라졌지만 used_materials엔 남은 URL 대응
    data = load_used()
    prelim = {
        "source": "db" if args.url else "direct_proposal",
        "url": args.url,
        "title": args.title or "",
        "completed_date": args.date,
    }
    existing = find_duplicate(data, prelim)
    if existing is not None:
        print(f"⚠️  중복 발견! 기존 항목:", file=sys.stderr)
        print(json.dumps(existing, ensure_ascii=False, indent=2), file=sys.stderr)
        if not args.force:
            print(f"\n❌ 중단 (무시하고 추가하려면 --force)", file=sys.stderr)
            sys.exit(3)
        print(f"⚠️  --force로 중복 무시하고 추가\n")

    # 2. entry 완성 (DB 모드는 자동 추론)
    if args.url:
        title = args.title
        category = args.category
        subcategory = args.subcategory

        if not (title and category):
            print(f"🔍 DB에서 URL 조회 중: {args.url}")
            row = fetch_from_db(args.url)
            if row:
                title = title or row.get("title")
                category = category or row.get("category")
                if not subcategory:
                    subcategory = row.get("subcategory") or ""
                print(f"   → 추론: title={(title or '')[:40]}... | category={category} | subcategory={subcategory or '(없음)'}")
            else:
                print(f"⚠️  DB 조회 실패 또는 해당 URL 없음 — 수동 플래그 필요")

        if not title or not category:
            print(f"❌ DB 모드는 --title과 --category가 필요합니다 (자동 추론 실패)", file=sys.stderr)
            sys.exit(2)

        entry = {
            "source": "db",
            "url": args.url,
            "title": title,
            "category": category,
            "subcategory": subcategory,
            "completed_date": args.date,
            "plan_file": args.plan,
            "script_file": args.script,
        }
    else:
        if not args.title or not args.category:
            print(f"❌ --direct 모드는 --title과 --category가 필요합니다", file=sys.stderr)
            sys.exit(2)

        entry = {
            "source": "direct_proposal",
            "url": None,
            "title": args.title,
            "category": args.category,
            "subcategory": args.subcategory,
            "completed_date": args.date,
            "plan_file": args.plan,
            "script_file": args.script,
        }

    warn_if_file_missing(args.plan, "plan")
    warn_if_file_missing(args.script, "script")

    if args.dry_run:
        print("🔍 DRY-RUN — 추가될 항목:")
        print(json.dumps(entry, ensure_ascii=False, indent=2))
        return

    data.setdefault("used", []).append(entry)
    save_used(data)

    print(f"✅ 등록 완료: {entry['title']}")
    print(f"   source: {entry['source']} | date: {entry['completed_date']}")
    print(f"   plan: {entry['plan_file']}")
    print(f"   script: {entry['script_file']}")

    total = len(data["used"])
    db_count = sum(1 for x in data["used"] if x.get("source", "db") == "db")
    direct_count = sum(1 for x in data["used"] if x.get("source") == "direct_proposal")
    print(f"📊 누적: {total}개 (db: {db_count}, direct_proposal: {direct_count})")


if __name__ == "__main__":
    main()
