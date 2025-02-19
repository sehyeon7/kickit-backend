from django.db import models

# Create your models here.
from django.contrib.auth.models import User

class NotificationType(models.TextChoices):
    IN_APP = 'in_app', 'In-app only'
    PUSH_IN_APP = 'push_in_app', 'Push & In-app'

class UserSetting(models.Model):
    """
    - 닉네임 변경: 사실상 Profile에 nickname 필드를 두었으므로,
    여기서 직접 관리하지 않고 profile.nickname을 변경하면 됨.
    - 비밀번호 변경: User model 내장 메서드
    - 회원탈퇴: User.is_active=False or 삭제
    - 알림 설정:
    1) notification_type (in_app / push_in_app)
    2) when_post_liked
    3) when_commented
    4) when_mentioned
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices, default=NotificationType.IN_APP)
    notify_when_post_liked = models.BooleanField(default=False)
    notify_when_commented = models.BooleanField(default=False)
    notify_when_mentioned = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s Settings"