"""
가비지 컬렉션 — 7일 이상 오래된 데이터 자동 삭제
"""
import sys
import os
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.client import get_client


def delete_old_posts(days: int = 7) -> int:
    client = get_client()
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()

    result = client.table("posts").delete().lt("collected_at", cutoff).execute()
    count = len(result.data) if result.data else 0
    print(f"  posts 테이블: {count}개 삭제 (7일 초과)")
    return count


def delete_old_youtube(days: int = 7) -> int:
    client = get_client()
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()

    result = client.table("youtube_videos").delete().lt("collected_at", cutoff).execute()
    count = len(result.data) if result.data else 0
    print(f"  youtube_videos 테이블: {count}개 삭제 (7일 초과)")
    return count


def run():
    print("가비지 컬렉션 시작...")
    total = 0
    total += delete_old_posts()
    total += delete_old_youtube()
    print(f"가비지 컬렉션 완료: 총 {total}개 삭제")


if __name__ == "__main__":
    run()
