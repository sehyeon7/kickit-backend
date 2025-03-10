import os
import uuid
from supabase import create_client, Client
from django.conf import settings
from django.core.files.base import ContentFile

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
        # 파일 확장자 추출
        file_ext = django_file.name.split('.')[-1]
        file_name = f"{uuid.uuid4()}.{file_ext}"

        # Supabase Storage에 업로드할 경로 (예: "2025/02/19/uuid.jpg" 등)
        storage_path = f"{file_name}"

        # django_file.read() -> 바이너리로 읽어서 업로드
        file_data = django_file.read()

        # 업로드 (RFC 4648 base64 이슈 없도록 binary 전송)
        result = supabase.storage.from_(supabase_bucket).upload(
            path=storage_path,
            file=file_data
        )
        # result 예) {'Key': 'post-images/uuid.jpg', ...} 업로드 성공 여부는 result.error로 확인 가능

        if result.get('error'):
            print("Supabase upload error:", result['error'])
            return None

        # public URL 생성 (Public Bucket 이거나, signed URL 발급)
        # Public Bucket 사용 시:
        public_url = f"{supabase_url}/storage/v1/object/public/{supabase_bucket}/{storage_path}"

        # 만약 Supabase Bucket이 비공개라면, signed URL을 발급받는 로직 필요
        # public_url = supabase.storage.from_(SUPABASE_BUCKET).create_signed_url(...)

        return public_url
    except Exception as e:
        print("upload_image_to_supabase error:", e)
        return None

def delete_image_from_supabase(image_url):
    """
    - Supabase Storage에서 특정 이미지 삭제
    - image_url: 삭제할 이미지의 전체 URL
    """
    try:
        # Supabase에서 관리하는 경로만 추출 (ex: "uuid.jpg")
        file_name = image_url.split(f"{supabase_bucket}/")[-1]  # URL에서 파일명만 추출
        
        # 파일 삭제 요청
        result = supabase.storage.from_(supabase_bucket).remove([file_name])

        if result.get('error'):
            print(f"Supabase delete error: {result['error']}")
            return False  # 삭제 실패

        return True  # 삭제 성공

    except Exception as e:
        print(f"delete_image_from_supabase error: {e}")
        return False