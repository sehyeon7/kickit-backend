from django.conf import settings
from apps.notification.models import Notification
from apps.settings_app.models import NotificationType
from django.contrib.auth.models import User
from apps.settings_app.models import UserSetting
import requests
from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message, Notification as FirebaseNotification, send
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import requests
import json
import os
import boto3
import base64
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.mail import send_mail

FIREBASE_SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]

FCM_API_URL = f"https://fcm.googleapis.com/v1/projects/{settings.FIREBASE_PROJECT_ID}/messages:send"

def get_firebase_credentials_json():
    """
    FIREBASE_CREDENTIALS_B64 환경 변수에 Base64 인코딩된 Firebase 자격 증명 JSON이
    저장되어 있다고 가정하고, 이를 디코딩하여 문자열(JSON)로 반환한다.
    """
    firebase_creds_b64 = os.getenv("FIREBASE_CREDENTIALS_B64")
    if not firebase_creds_b64:
        print("환경 변수 FIREBASE_CREDENTIALS_B64가 설정되어 있지 않습니다.")
        return None
    
    try:
        # Base64 -> JSON 문자열
        json_str = base64.b64decode(firebase_creds_b64).decode('utf-8')
        return json_str
    except Exception as e:
        print("Firebase 자격 증명 Base64 디코딩 실패:", e)
        return None

def get_fcm_access_token():
    """
    Firebase Cloud Messaging HTTP v1 API를 사용하기 위한 OAuth 2.0 액세스 토큰 발급
    (Secrets Manager 등에서 JSON을 로드한 뒤 in-memory로 자격증명을 생성)
    """
    # 1) Secrets Manager(또는 다른 안전한 방법)로부터 credentials JSON 불러오기
    cred_json_str = get_firebase_credentials_json()  # 아래 예시 함수로부터 가져온 문자열
    cred_json_dict = json.loads(cred_json_str)

    credentials = service_account.Credentials.from_service_account_info(
        cred_json_dict,
        scopes=FIREBASE_SCOPES
    )

    credentials.refresh(Request())  # 토큰 갱신
    return credentials.token

def send_notification(user, title, message, board_id=None, post_id=None, comment_id=None):
    """
    user의 알림 설정(UserSetting)을 확인해, In-app 알림 / Push 알림을 보낸다.
    """
    user_setting = UserSetting.objects.filter(user=user).first()
    
    # 기본값: 둘 다 보냄
    send_fcm_push_notification(
        user=user,
        title=title,
        message=message,
        board_id=board_id,
        post_id=post_id,
        comment_id=comment_id
    )

    # 1) In-app 알림 생성
    Notification.objects.create(
        user=user,
        title=title,
        message=message,
        board_id=board_id,
        post_id=post_id,
        comment_id=comment_id,
    )

def handle_comment_notification(comment, post, board, parent_comment):
    """
    - 댓글/대댓글 알림을 처리
    - 부모 댓글이 있으면 대댓글, 없으면 게시글의 댓글로 간주
    """
    comment_author = comment.author

    if parent_comment:
        parent_comment_author = parent_comment.author
        user_setting = UserSetting.objects.filter(user=parent_comment_author).first()
        if user_setting and user_setting.notification_categories.filter(name="Commented").exists():
            send_notification(
                user=parent_comment_author,
                title="New reply to your comment!",
                message=f"{comment_author.profile.nickname}: {comment.content}",
                board_id=board.id,
                post_id=post.id,
                comment_id=comment.id
            )
    else:
        post_author = post.author
        user_setting = UserSetting.objects.filter(user=post_author).first()
        if user_setting and user_setting.notification_categories.filter(name="Commented").exists():
            send_notification(
                user=post_author,
                title="New comment on your post!",
                message=f"{comment_author.profile.nickname}: {comment.content}",
                board_id=board.id,
                post_id=post.id,
                comment_id=comment.id
            )

def handle_like_notification(user, board, post_or_comment, is_post=True):
    """
    - 글 좋아요: 게시글 작성자에게 알림
    - 댓글 좋아요: 댓글 작성자에게 알림
    """
    target_author = post_or_comment.author
    user_setting = UserSetting.objects.filter(user=target_author).first()
    if not user_setting or not user_setting.notification_categories.filter(name="Liked").exists():
        return

    if is_post:
        title = "Someone liked your post!"
        message = f"'{post_or_comment.content}'"
        board_id = board.id
        post_id = post_or_comment.id 
        comment_id = None
    else:
        title = "Someone liked your comment!"
        message = f"'{post_or_comment.content}'"
        board_id = board.id
        post_id = post_or_comment.post.id  
        comment_id = post_or_comment.id

    send_notification(target_author, title, message, board_id=board_id, post_id=post_id, comment_id=comment_id)

def handle_mention_notification(board, comment, mention_usernames):
    """
    - 멘션된 사용자에게 알림 전송
    - 존재하지 않는 닉네임은 무시
    """
    comment_author = comment.author
    for nickname in mention_usernames:
        try:
            mentioned_user = User.objects.get(profile__nickname=nickname)
            user_setting = UserSetting.objects.filter(user=mentioned_user).first()
            if user_setting and user_setting.notification_categories.filter(name="Mentioned").exists():
                send_notification(
                    user=mentioned_user,
                    title="You were mentioned in a comment",
                    message=f"{comment_author.profile.nickname} mentioned you: {comment.content}",
                    board_id = board.id,
                    post_id=comment.post.id,
                    comment_id=comment.id
                )
        except User.DoesNotExist:
            continue  # 존재하지 않는 유저는 무시

def send_fcm_push_notification(user, title, message, board_id=None, post_id=None, comment_id=None):
    """
    특정 유저에게 FCM Push 알림을 전송하는 함수
    """
    device = FCMDevice.objects.filter(user=user).first()
    if not device:
        print(f"{user.username}의 FCM 기기가 등록되지 않음")
        return
    
    token = get_fcm_access_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "message": {
            "token": device.registration_id,
            "notification": {
                "title": title,
                "body": message
            },
            "data": {
                "board_id": str(board_id) if board_id else "",
                "post_id": str(post_id) if post_id else "",
                "comment_id": str(comment_id) if comment_id else "",
                "click_action": "FLUTTER_NOTIFICATION_CLICK"
            },
            "android": {
                "notification": {
                    "click_action": "FLUTTER_NOTIFICATION_CLICK"
                }
            },
            "apns": {
                "payload": {
                    "aps": {
                        "category": "NEW_MESSAGE_CATEGORY"
                    }
                }
            }
        }
    }
    
    response = requests.post(FCM_API_URL, headers=headers, data=json.dumps(payload))

    if response.status_code == 200:
        print(f"{user.username}에게 푸시 알림 전송 성공")
    else:
        print(f"{user.username}에게 푸시 알림 전송 실패: {response.text}")

def send_verification_notification(user, success=True):
    """
    유저 인증 성공/실패 시 In-app, Push, Email 알림 전송
    """
    title = "Squibble Account Verification"
    
    if success:
        message = f"{user.username}, your account has been successfully verified! 🎉 You now have access to all features."
    else:
        message = f"{user.username}, your account verification has been denied. Please re-upload your verification image."

    # ✅ In-app 알림 저장
    try:
        Notification.objects.create(
            user=user,
            title=title,
            message=message
        )
    except Exception as e:
        print("[ERROR] In-app 알림 생성 실패:", e)

    # ✅ Push 알림 전송 (유저의 FCM 기기 등록 여부 확인)
    try:
        send_fcm_push_notification(user, title, message)
    except Exception as e:
        print("[ERROR] 푸시 알림 실패:", e)

    # ✅ Email 알림 전송
    try:
        send_mail(
            subject=title,
            message=message,
            from_email="no-reply@squible.net",
            recipient_list=[user.email],
            fail_silently=False,  # 여전히 raise 하도록
        )
    except ConnectionRefusedError:
        print("[ERROR] 메일 서버에 연결할 수 없습니다. 이메일 전송 실패")
    except Exception as e:
        print("[ERROR] 이메일 전송 실패:", e)


def send_verification_failure_email(user):
    """
    유저 인증 실패 시 이메일 전송
    """
    subject = "Squibble Account Verification Failed"
    message = (
        f"Hello {user.profile.nickname},\n\n"
        "Unfortunately, your verification request has been denied.\n"
        "If you have any questions, please contact our support team.\n"
        "- Squibble Team"
    )


    send_mail(
        subject=subject,
        message=message,
        from_email="no-reply@squible.net",
        recipient_list=[user.email],
        fail_silently=False,
    )
