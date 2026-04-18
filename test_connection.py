from dotenv import load_dotenv
import os
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

print("Supabase 연결 테스트 중...")
client = create_client(url, key)

result = client.table("category_profiles").select("*").execute()
print("연결 성공!")
print("카테고리 목록:")
for row in result.data:
    print(f"  - {row['slug']}: {row['display_name']}")
