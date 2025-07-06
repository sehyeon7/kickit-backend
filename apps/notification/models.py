from django.db import models

# Create your models here.
from django.contrib.auth.models import User

class Notification(models.Model):
    """
    In-app 알림 저장 (유저가 알림 목록을 볼 수 있도록)
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications')
    title = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    board_id = models.IntegerField(null=True, blank=True)
    post_id = models.IntegerField(null=True, blank=True)
    comment_id = models.IntegerField(null=True, blank=True)
    meetup_id = models.IntegerField(null=True, blank=True)
    notice_id = models.IntegerField(null=True, blank=True)
    question_id = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message}"