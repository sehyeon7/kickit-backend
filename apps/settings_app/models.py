from django.db import models

# Create your models here.
from django.contrib.auth.models import User

class NotificationType(models.Model):
    """
    알림 타입 모델
    - In_app: 앱 내 알림만 허용
    - Push & In_app: 푸시 및 앱 내 알림 허용
    """
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class NotificationCategory(models.Model):
    """
    알림 카테고리 모델
    - Liked: 좋아요 알림
    - Commented: 댓글 알림
    - Mentioned: 멘션 알림
    """
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class UserSetting(models.Model):
    """
    - 닉네임 변경: 사실상 Profile에 nickname 필드를 두었으므로,
    여기서 직접 관리하지 않고 profile.nickname을 변경하면 됨.
    - 비밀번호 변경: User model 내장 메서드
    - 회원탈퇴: User.is_active=False or 삭제
    - 알림 설정:
    - notification_type: 알림 타입 (In_app, Push & In_app)
    - notification_categories: 사용자가 활성화한 알림 카테고리
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    notification_type = models.ForeignKey(NotificationType, on_delete=models.SET_NULL, null=True, blank=True)
    notification_categories = models.ManyToManyField(NotificationCategory, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Settings"