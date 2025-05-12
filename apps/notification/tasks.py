from django.conf import settings
from celery import shared_task
from django.contrib.auth.models import User
from firebase_admin.messaging import Message, send, Notification as FirebaseNotification
from fcm_django.models import FCMDevice
import requests
import os
import json
from google.oauth2 import service_account
from google.auth.transport.requests import Request

FIREBASE_SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]

FCM_API_URL = f"https://fcm.googleapis.com/v1/projects/{settings.FIREBASE_PROJECT_ID}/messages:send"

def get_firebase_credentials_json():
    file_path = "/etc/secrets/firebase.json"
    if not os.path.exists(file_path):
        print("Firebase 자격 증명 파일이 존재하지 않습니다.")
        return None
    try:
        with open(file_path, "r") as f:
            return f.read()
    except Exception as e:
        print("Firebase 자격 증명 파일 읽기 실패:", e)
        return None
    
def get_fcm_access_token():
    """
    Firebase Cloud Messaging HTTP v1 API를 사용하기 위한 OAuth 2.0 액세스 토큰 발급
    (Secrets Manager 등에서 JSON을 로드한 뒤 in-memory로 자격증명을 생성)
    """
    # 1) Secrets Manager(또는 다른 안전한 방법)로부터 credentials JSON 불러오기
    cred_json_str = get_firebase_credentials_json()  # 아래 예시 함수로부터 가져온 문자열
    if cred_json_str is None:
        raise ValueError("Firebase 자격 증명을 불러오지 못했습니다.")
    cred_json_dict = json.loads(cred_json_str)

    credentials = service_account.Credentials.from_service_account_info(
        cred_json_dict,
        scopes=FIREBASE_SCOPES
    )

    credentials.refresh(Request())  # 토큰 갱신
    return credentials.token


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

@shared_task
def send_push_notification_async(user_id, title, message, board_id=None, post_id=None, comment_id=None):
    try:
        user = User.objects.get(id=user_id)
        send_fcm_push_notification(user, title, message, board_id, post_id, comment_id)
    except User.DoesNotExist:
        print(f"[ERROR] User {user_id} not found")
