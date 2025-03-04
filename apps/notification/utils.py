from django.conf import settings
from apps.notification.models import Notification
from apps.settings_app.models import NotificationType
from django.contrib.auth.models import User
from apps.settings_app.models import UserSetting
import requests
from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message, Notification, send
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import requests
import json
import os
import boto3
from botocore.exceptions import ClientError
from django.conf import settings

FIREBASE_SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]
FIREBASE_CREDENTIALS_PATH = settings.FIREBASE_CREDENTIALS_PATH

FCM_API_URL = f"https://fcm.googleapis.com/v1/projects/{settings.FIREBASE_PROJECT_ID}/messages:send"

def get_firebase_credentials_json():
    """
    AWS Secrets Manager에서 Firebase 자격 증명(Plaintext JSON)을 불러와 문자열로 반환
    """
    secret_name = os.getenv("FIREBASE_SECRET_NAME")
    region_name = "ap-northeast-2"

    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=region_name)
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        # 로그/예외처리
        raise e

    # Plaintext JSON이 SecretString에 들어있다고 가정
    return get_secret_value_response['SecretString']

def get_fcm_access_token():
    """
    Firebase Cloud Messaging HTTP v1 API를 사용하기 위한 OAuth 2.0 액세스 토큰 발급
    (Secrets Manager 등에서 JSON을 로드한 뒤 in-memory로 자격증명을 생성)
    """
    # 1) Secrets Manager(또는 다른 안전한 방법)로부터 credentials JSON 불러오기
    cred_json_str = get_firebase_credentials_json()  # 아래 예시 함수로부터 가져온 문자열
    cred_json_dict = json.loads(cred_json_str)

    credentials = service_account.Credentials.from_service_account_file(
        cred_json_dict,
        scopes=FIREBASE_SCOPES
    )

    credentials.refresh(Request())  # 토큰 갱신
    return credentials.token

def send_notification(user, title, message, post_id=None):
    """
    user의 알림 설정(UserSetting)을 확인해, In-app 알림 / Push 알림을 보낸다.
    """
    # 1) In-app 알림 생성
    Notification.objects.create(
        user=user,
        title=title,
        message=message,
        post_id=post_id,
    )
    # 2) user.setting.notification_type 확인
    user_setting = UserSetting.objects.filter(user=user).first()
    if not user_setting or user_setting.notification_type == NotificationType.IN_APP:
        # 설정이 없는 경우 -> In-app만
        return

    if user_setting.notification_type == NotificationType.PUSH_IN_APP:
        # 실제로는 FCM, APNs, SMS 등 Push 로직 필요
        send_fcm_push_notification(user, message)

def handle_comment_notification(comment, post, parent_comment):
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
                title="새로운 대댓글이 달렸습니다!",
                message=f"{comment_author.profile.nickname}: {comment.content}",
                post_id=post.id,
                comment_id=comment.id
            )
    else:
        post_author = post.author
        user_setting = UserSetting.objects.filter(user=post_author).first()
        if user_setting and user_setting.notification_categories.filter(name="Commented").exists():
            send_notification(
                user=post_author,
                title="새로운 댓글이 달렸습니다!",
                message=f"{comment_author.profile.nickname}: {comment.content}",
                post_id=post.id,
                comment_id=comment.id
            )

def handle_like_notification(user, post_or_comment, is_post=True):
    """
    - 글 좋아요: 게시글 작성자에게 알림
    - 댓글 좋아요: 댓글 작성자에게 알림
    """
    target_author = post_or_comment.author
    user_setting = UserSetting.objects.filter(user=target_author).first()
    if not user_setting or not user_setting.notification_categories.filter(name="Liked").exists():
        return

    if is_post:
        title = "당신의 글이 좋아요를 받았습니다!"
        message = f"'{post_or_comment.content}'"
        post_id = post_or_comment.id 
    else:
        title = "당신의 댓글이 좋아요를 받았습니다!"
        message = f"'{post_or_comment.content}'"
        post_id = post_or_comment.post.id  

    send_notification(target_author, title, message, post_id)

def handle_mention_notification(comment, mention_usernames):
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
                    title=f"'{comment_author.profile.nickname}'님이 당신을 댓글에서 언급했습니다.",
                    message=f"{comment.content}",
                    post_id=comment.post.id,
                    comment_id=comment.id
                )
        except User.DoesNotExist:
            continue  # 존재하지 않는 유저는 무시

def send_fcm_push_notification(user, title, message, post_id=None):
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
                "post_id": str(post_id) if post_id else "",
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