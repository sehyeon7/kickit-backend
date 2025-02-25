import os
import uuid
from supabase import create_client, Client
from django.conf import settings

# 환경 변수
supabase_url = settings.SUPABASE_URL
supabase_anon_public_key = settings.SUPABASE_ANON_PUBLIC_KEY
supabase_bucket = settings.SUPABASE_BUCKET

supabase: Client = create_client(supabase_url, supabase_anon_public_key)

def upload_image_to_supabase(django_file):
    """
    - django_file : ImageField로 들어온 File 객체
    - Supabase Storage에 업로드 후, public URL 반환
    """
    try:
        file_ext = django_file.name.split('.')[-1]
        file_name = f"profile_images/{uuid.uuid4()}.{file_ext}"  # ✅ 프로필 이미지는 `profile_images/` 경로에 저장

        file_data = django_file.read()
        result = supabase.storage.from_(supabase_bucket).upload(path=file_name, file=file_data)

        if result.get('error'):
            print("Supabase upload error:", result['error'])
            return None

        # Public URL 생성
        public_url = f"{supabase_url}/storage/v1/object/public/{supabase_bucket}/{file_name}"
        return public_url
    except Exception as e:
        print("upload_image_to_supabase error:", e)
        return None
