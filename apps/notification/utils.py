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
from apps.notification.tasks import send_push_notification_async, send_fcm_push_notification

def send_notification(user, title, message, board_id=None, post_id=None, comment_id=None, sender=None):
    """
    user의 알림 설정(UserSetting)을 확인해, In-app 알림 / Push 알림을 보낸다.
    """
    user_setting = UserSetting.objects.filter(user=user).first()

    if sender == user:
        return
    
    if Notification.objects.filter(
        user=user,
        sender=sender,
        post_id=post_id,
        comment_id=comment_id,
        title=title
    ).exists():
        return
    

    # 1) In-app 알림 생성
    Notification.objects.create(
        user=user,
        sender=sender,
        title=title,
        message=message,
        board_id=board_id,
        post_id=post_id,
        comment_id=comment_id,
    )

    try:
        send_push_notification_async.delay(user.id, title, message, board_id, post_id, comment_id)
    except Exception as e:
        print(f"[WARNING] Celery task enqueue 실패: {e}")

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
                sender=comment_author,
                title=f"{comment_author.profile.nickname} replied to your comment!",
                message=f"{comment.content}",
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
                sender=comment_author,
                title=f"{comment_author.profile.nickname} commented on your post!",
                message=f"{comment.content}",
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
    if user == target_author:
        return
    
    user_setting = UserSetting.objects.filter(user=target_author).first()
    if not user_setting or not user_setting.notification_categories.filter(name="Liked").exists():
        return

    if is_post:
        title = f"{user.profile.nickname} liked your post!"
        message = f"'{post_or_comment.content}'"
        board_id = board.id
        post_id = post_or_comment.id 
        comment_id = None
    else:
        title = f"{user.profile.nickname} liked your comment!"
        message = f"'{post_or_comment.content}'"
        board_id = board.id
        post_id = post_or_comment.post.id  
        comment_id = post_or_comment.id

    send_notification(
        user=target_author,
        sender=user,
        title=title,
        message=message,
        board_id=board.id,
        post_id=post_id,
        comment_id=comment_id,
    )

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
                    sender=comment_author, 
                    title=f"{comment_author.profile.nickname} mentioned you in a comment",
                    message=f"{comment.content}",
                    board_id = board.id,
                    post_id=comment.post.id,
                    comment_id=comment.id
                )
        except User.DoesNotExist:
            continue  # 존재하지 않는 유저는 무시


def send_verification_notification(user, success=True):
    """
    유저 인증 성공/실패 시 In-app, Push, Email 알림 전송
    """
    title = "Squibble Account Verification"
    
    if success:
        message = f"{user.username}, your account has been successfully verified! 🎉 You now have access to all features."

        # ✅ 인증 성공한 경우에만 In-app 알림 저장
        try:
            Notification.objects.create(
                user=user,
                title=title,
                message=message
            )
        except Exception as e:
            print("[ERROR] In-app 알림 생성 실패:", e)
    else:
        message = f"{user.username}, your account verification has been denied. Please re-upload your verification image."

    # ✅ Push 알림 전송
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

def send_meeting_notification(user, title, message, meetup_id=None, notice_id=None, question_id=None, comment_id=None, sender=None):
    """
    이벤트 관련 알림 (In-app + Push)
    """
    if sender == user:
        return

    user_setting = UserSetting.objects.filter(user=user).first()
    if not user_setting or not user_setting.meetup_notification:
        return

    # 중복 방지
    if Notification.objects.filter(
        user=user,
        sender=sender,
        title=title,
        meetup_id=meetup_id,
        notice_id=notice_id,
        question_id=question_id,
        comment_id=comment_id,
    ).exists():
        return

    Notification.objects.create(
        user=user,
        sender=sender,
        title=title,
        message=message,
        meetup_id=meetup_id,
        notice_id=notice_id,
        question_id=question_id,
        comment_id=comment_id,
    )

    try:
        send_push_notification_async.delay(user.id, title, message)
    except Exception as e:
        print(f"[WARNING] 이벤트 푸시 전송 실패: {e}")

def handle_join_meeting_notification(meeting, participant):
    """
    - 누군가 meetup에 참여하면 호스트에게 알림 전송
    - 본인이 본인 meetup에 참여 시 알림 생략
    """
    if meeting.creator == participant:
        return

    send_meeting_notification(
        user=meeting.creator,
        sender=participant,
        title="Someone Joined Your Meetup!",
        message=f"{participant.profile.nickname} has joined \"{meeting.title}\".",
        meetup_id=meeting.id
    )

def handle_notice_created_notification(notice):
    """
    - meetup 공지 생성 시, 모든 참여자에게 알림 (호스트 제외)
    """
    meeting = notice.meeting
    sender = meeting.creator
    participants = meeting.participants.exclude(id=sender.id)

    for user in participants:
        send_meeting_notification(
            user=user,
            sender=sender,
            title="New Update for Your Meetup",
            message=f"The host added a new notice to \"{meeting.title}\".",
            meetup_id=meeting.id,
            notice_id=notice.id
        )

def handle_question_notification(qna):
    """
    - 참여자가 QnA 등록 시, 호스트에게 알림
    """
    send_meeting_notification(
        user=qna.meeting.creator,
        sender=qna.author,
        title="New Question for Your Meetup",
        message=f"{qna.author.profile.nickname} asked a question in \"{qna.meeting.title}\".",
        meetup_id=qna.meeting.id,
        question_id=qna.id
    )

def handle_qna_comment_notification(comment):
    """
    - QnA 댓글 등록 시, 질문자 또는 호스트에게 알림
    """
    qna = comment.qna
    sender = comment.author
    receiver = qna.author if sender == qna.meeting.creator else qna.meeting.creator

    send_meeting_notification(
        user=receiver,
        sender=sender,
        title="New Comment in the Q&A",
        message=f"{sender.profile.nickname} commented on Q&A in \"{qna.meeting.title}\".",
        meetup_id=qna.meeting.id,
        question_id=qna.id,
        comment_id=comment.id
    )

def handle_meeting_reminder_notification(meeting):
    """
    - 24시간 전 자동 알림: 호스트 + 모든 참여자
    """
    for user in meeting.participants.all():
        send_meeting_notification(
            user=user,
            sender=None,
            title="Your Meetup Is Coming Up Soon!",
            message=f"\"{meeting.title}\" starts in 24 hours!",
            meetup_id=meeting.id
        )
    
    send_meeting_notification(
        user=meeting.creator,
        sender=None,
        title="Your Meetup Is Coming Up Soon!",
        message=f"\"{meeting.title}\" starts in 24 hours!",
        meetup_id=meeting.id
    )

def handle_kick_participant_notification(meeting, removed_user):
    """
    - 호스트가 유저를 내보내면 해당 유저에게 알림 전송
    """
    send_meeting_notification(
        user=removed_user,
        sender=meeting.creator,
        title="RSVP canceled",
        message=f"Your participation in \"{meeting.title}\" has been canceled by the host.",
        meetup_id=meeting.id
    )


