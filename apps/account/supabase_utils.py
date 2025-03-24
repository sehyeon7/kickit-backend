import uuid
from supabase import create_client, Client
from django.conf import settings

# 환경 변수
supabase_url = settings.SUPABASE_URL
supabase_anon_public_key = settings.SUPABASE_ANON_PUBLIC_KEY
supabase_bucket = settings.SUPABASE_BUCKET

supabase: Client = create_client(supabase_url, supabase_anon_public_key)

from sentry_sdk import capture_message, capture_exception

def upload_verification_image_to_supabase(django_file):
    """
    - 유학생 인증 사진을 Supabase Storage에 업로드 후, public URL 반환
    """
    try:
        # 파일 확장자 추출
        file_ext = django_file.name.split('.')[-1]
        file_name = f"verification/{uuid.uuid4()}.{file_ext}"

        # Supabase Storage에 업로드할 경로 (예: "verification/uuid.jpg")
        storage_path = file_name

        # 바이너리 데이터 읽기
        file_data = django_file.read()

        # 업로드 (binary 데이터 전송)
        result = supabase.storage.from_(supabase_bucket).upload(
            path=storage_path,
            file=file_data
        )

        if result.code != 200:
            error_info = result.message
            # logger.error(f"Supabase upload error: {error_info}")
            capture_message(f"Supabase upload error: {error_info}")
            return None

        # Public URL 생성
        public_url = f"{supabase_url}/storage/v1/object/public/{supabase_bucket}/{storage_path}"
        return public_url

    except Exception as e:
        # logger.exception("upload_verification_image_to_supabase error:")
        capture_exception(e)
        return None
