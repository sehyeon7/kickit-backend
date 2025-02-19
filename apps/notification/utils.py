from django.conf import settings
from apps.notification.models import Notification
from apps.settings_app.models import NotificationType

def send_notification(user, message, post_id=None, comment_id=None):
    """
    user의 알림 설정(UserSetting)을 확인해, In-app 알림 / Push 알림을 보낸다.
    """
    # 1) In-app 알림 생성
    Notification.objects.create(
        user=user,
        message=message,
        post_id=post_id,
        comment_id=comment_id,
    )
    # 2) user.setting.notification_type 확인
    user_setting = getattr(user, 'setting', None)
    if not user_setting:
        # 설정이 없는 경우 -> In-app만
        return

    if user_setting.notification_type == NotificationType.PUSH_IN_APP:
        # 실제로는 FCM, APNs, SMS 등 Push 로직 필요
        push_send_demo(user, message)

def push_send_demo(user, message, post_id=None, comment_id=None):
    """
    실제 프로젝트에서는 FCM 토큰 / APNs 토큰 등을 보관해야 하고,
    그 토큰으로 외부 Push 서버에 요청을 보내야 한다.
    여기서는 예시로 print()로 대신함.
    """
    # 예시: print()로 표시
    # 푸시 로직(FCM/APNs/WebPush 등) - 여기서는 데모
    print(f"[푸시 알림] {user.username} => {message} (post_id={post_id}, comment_id={comment_id})")