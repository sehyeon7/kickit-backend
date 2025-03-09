import base64
import os

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Firebase 자격 증명을 Base64로 인코딩하는 명령어"

    def handle(self, *args, **options):
        # 실제 로직
        # 예: JSON 파일을 읽고 Base64로 인코딩
        file_path = 'kickit/snulife-international-fcm-key.json'
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"{file_path} 파일이 존재하지 않습니다."))
            return

        with open(file_path, 'rb') as f:
            encoded_bytes = base64.b64encode(f.read())
            encoded_str = encoded_bytes.decode('utf-8')

        # 결과 출력
        self.stdout.write(self.style.SUCCESS("아래 Base64 인코딩 결과를 EB 환경 변수에 복사하세요:"))
        self.stdout.write(encoded_str)