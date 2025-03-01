from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User

class EmailAuthBackend(ModelBackend):
    """
    이메일을 username 대신 인증 필드로 사용하는 백엔드
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(email=username)  # email을 username으로 간주
            if user.check_password(password):  # 비밀번호 검증
                return user
        except User.DoesNotExist:
            return None