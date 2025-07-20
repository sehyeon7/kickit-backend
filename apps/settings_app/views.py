from django.shortcuts import render

# Create your views here.
from rest_framework import generics, permissions, status, views
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import get_object_or_404
from django.contrib.auth import logout
from .supabase_utils import upload_image_to_supabase
from django.db import models
from apps.board.pagination import PostCursorPagination
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.db.models import F, Value
from django.db.models.functions import Replace

from .models import UserSetting, NotificationType, NotificationCategory, ContactUs, ReportReason, Report
from .serializers import (
    UserSettingSerializer,
    PasswordChangeSerializer, UserDeactivateSerializer,
    ScrappedPostsSerializer, EmailUpdateSerializer,
    NotificationTypeSerializer, NotificationCategorySerializer, ContactUsSerializer, ProfileUpdateSerializer,
    MyCommentSerializer
)
from apps.board.serializers import PostSerializer, CommentSerializer
from django.contrib.auth.models import User
from apps.account.models import UserProfile
from apps.board.models import PostLike, Post, Comment
from apps.notification.models import Notification
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from apps.meetup.serializers import MeetingDetailSerializer
from apps.meetup.models import Meeting
from apps.meetup.pagination import MeetingCursorPagination

from django.utils import timezone
from rest_framework.generics import ListAPIView


class UserSettingDetailView(generics.RetrieveUpdateAPIView):
    """
    GET/PUT: 알림 설정 조회/변경
    """
    serializer_class = UserSettingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        setting, _ = UserSetting.objects.get_or_create(user=self.request.user)
        return setting
    
    def patch(self, request, *args, **kwargs):
        """
        - `notification_type`: ID 배열로 업데이트 (예: { "notification_type": [1] })
        - `notification_categories`: ID 배열로 업데이트 (예: { "notification_categories": [1, 2, 3] })
        """
        data = request.data
        user_setting = self.get_object()

        # notification_type 업데이트
        if "notification_type" in data:
            notification_type_ids = data.get("notification_type", [])
            if not isinstance(notification_type_ids, list):
                return Response({"error": "notification_type must be an array containing a single ID."}, status=status.HTTP_400_BAD_REQUEST)

            valid_types = NotificationType.objects.filter(id__in=notification_type_ids)
            if len(valid_types) != len(notification_type_ids):
                return Response({"error": "Some notification_type IDs are invalid."}, status=status.HTTP_400_BAD_REQUEST)
            user_setting.notification_type.set(valid_types)

        # notification_categories 업데이트
        if "notification_categories" in data:
            category_ids = data.get("notification_categories", [])
            if not isinstance(category_ids, list):
                return Response({"error": "notification_categories must be an array of IDs."}, status=status.HTTP_400_BAD_REQUEST)

            valid_categories = NotificationCategory.objects.filter(id__in=category_ids)
            if len(valid_categories) != len(category_ids):
                return Response({"error": "Some notification_categories IDs are invalid."}, status=status.HTTP_400_BAD_REQUEST)

            user_setting.notification_categories.set(valid_categories)

        user_setting.save()

        return Response(UserSettingSerializer(user_setting).data, status=status.HTTP_200_OK)

class NotificationTypeListView(generics.ListAPIView):
    """
    GET: 알림 타입 목록 조회
    """
    serializer_class = NotificationTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return NotificationType.objects.all()
    
class NotificationCategoryListView(generics.ListAPIView):
    """
    GET: 알림 카테고리 목록 조회
    """
    serializer_class = NotificationCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return NotificationCategory.objects.all()
    
class ProfileUpdateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        serializer = ProfileUpdateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        profile = user.profile

        nickname = serializer.validated_data.get("nickname", None)
        image = serializer.validated_data.get("image", None)
        introduce = serializer.validated_data.get("introduce")

        # 닉네임 변경
        if nickname:
            old_nickname = profile.nickname
            profile.nickname = nickname

            # 게시글 및 댓글 반영
            Post.objects.filter(author=user).update(author_nickname=nickname)
            Comment.objects.filter(author=user).update(author_nickname=nickname)
            Notification.objects.filter(message__icontains=old_nickname).update(
                message=Replace(F('message'), Value(old_nickname), Value(nickname))
            )

        # 이미지 변경
        if image:
            uploaded_url = upload_image_to_supabase(image)
            if not uploaded_url:
                return Response({"error": "Image upload failed."}, status=500)
            profile.profile_image = uploaded_url
        
        if introduce is not None:
            profile.introduce = introduce

        profile.save()

        return Response({
            "detail": "Profile has been updated.",
            "profile_image": profile.profile_image if image else None,
            "introduce": profile.introduce
        }, status=200)

# class NicknameUpdateView(views.APIView):
#     """
#     POST: 닉네임 변경
#     """
#     permission_classes = [permissions.IsAuthenticated]

#     def post(self, request):
#         serializer = NicknameUpdateSerializer(data=request.data, context = {"request": request})
#         serializer.is_valid(raise_exception=True)

#         nickname = serializer.validated_data['nickname']
#         user = request.user
#         profile = user.profile

#         old_nickname = profile.nickname

#         profile.nickname = nickname
#         profile.save()

#         # 게시글(`Post`)의 작성자 닉네임 업데이트
#         Post.objects.filter(author=user).update(author_nickname=nickname)

#         # 댓글(`Comment`)의 작성자 닉네임 업데이트
#         Comment.objects.filter(author=user).update(author_nickname=nickname)

#         # 알림(`Notification`)에서 유저가 포함된 메시지 업데이트
#         Notification.objects.filter(message__icontains=old_nickname).update(
#             message=Replace(
#                 F('message'),
#                 Value(old_nickname),
#                 Value(nickname)
#             )
#         )


#         return Response({"detail": f"Nickname has been changed to {nickname}."}, status=status.HTTP_200_OK)

class EmailUpdateView(views.APIView):
    """
    POST: 이메일 변경
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = EmailUpdateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True) # 이메일 중복 검증 실행

        email = serializer.validated_data['email']
        try:
            request.user.email = email
            request.user.save()
        except Exception as e:
            return Response(
                {"error": "An error occurred while changing the email. Please contact the administrator."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({"detail": f"Email has been changed to {email}."}, status=status.HTTP_200_OK)


class PasswordChangeView(views.APIView):
    """
    POST: 비밀번호 변경
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True) # 비밀번호 강도 검사 실행

        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']

        user = request.user
        if not user.check_password(old_password):
            return Response({"error": "The current password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
        
        if old_password == new_password:
            return Response({"error": "The new password must be different from the current password."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user.set_password(new_password)
            user.save()

            # JWT 기반에서는 기존 토큰을 폐기하고 새로 발급해야 함.
            refresh = RefreshToken.for_user(user)
            response = Response({"detail": "Password has been changed successfully."}, status=status.HTTP_200_OK)
            response.set_cookie('access_token', value=str(refresh.access_token), httponly=True, secure=True, samesite='None')
            response.set_cookie('refresh_token', value=str(refresh), httponly=True, secure=True, samesite='None')

            return response

        except Exception as e:
            return Response(
                {"error": "An error occurred while changing the password. Please contact the administrator."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
# class ProfileImageUpdateView(views.APIView):
#     """
#     PATCH: 프로필 이미지 변경
#     - Supabase Storage에 이미지 업로드 후 URL 저장
#     """
#     permission_classes = [permissions.IsAuthenticated]

#     def patch(self, request):
#         serializer = ProfileImageUpdateSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         user_profile = request.user.profile

#         try:
#             # Supabase에 이미지 업로드
#             uploaded_url = upload_image_to_supabase(serializer.validated_data['image'])
#             if not uploaded_url:
#                 raise Exception("Supabase Upload Failure")

#             # 기존 프로필 이미지 업데이트
#             user_profile.profile_image = uploaded_url
#             user_profile.save()

#             return Response({"profile_image": uploaded_url}, status=status.HTTP_200_OK)
        
#         except Exception as e:
#             return Response({"error": "Failed to upload the image."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserDeactivateView(views.APIView):
    """
    POST: 회원탈퇴
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = UserDeactivateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        password = serializer.validated_data["password"]
        user = request.user

        # 비밀번호 검증
        if not user.check_password(password):
            return Response({"error": "The password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

        # 유저 비활성화 (DB에는 유지)
        user.is_active = False
        user.save()

        # 닉네임을 "탈퇴한 사용자"로 변경
        profile = getattr(user, 'profile', None)
        if profile:
            profile.nickname = "Deleted User"
            profile.save()

        # 게시글 & 댓글에서 닉네임을 "탈퇴한 사용자"로 변경
        Post.objects.filter(author=user).update(author_nickname="Deleted User")
        Comment.objects.filter(author=user).update(author_nickname="Deleted User")

        # JWT 토큰 블랙리스트 처리 (로그아웃)
        try:
            refresh_token = request.COOKIES.get("refresh_token")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except TokenError:
            pass

        # 클라이언트 쿠키 삭제 (로그아웃 처리)
        response = Response({"detail": "Your account has been deactivated."}, status=status.HTTP_200_OK)
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        
        return response


class LikedPostsView(generics.ListAPIView):
    """
    GET: 내가 좋아요(추천)한 게시글 목록
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PostSerializer
    pagination_class = PostCursorPagination

    def get_queryset(self):
        return Post.objects.filter(likes__user=self.request.user).prefetch_related("likes", "comments")

class ScrappedPostsView(generics.ListAPIView):
    """
    GET: 내가 스크랩한 게시글 목록
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ScrappedPostsSerializer

    def get_queryset(self):
        return self.request.user.scrapped_posts.all().order_by('-created_at')

class ContactUsCreateView(generics.CreateAPIView):
    """
    사용자가 문의하기 폼을 제출하면 데이터베이스에 저장하는 API
    """
    serializer_class = ContactUsSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(user=user)

class ContactUsListView(generics.ListAPIView):
    """
    관리자가 문의 내역을 확인하는 API
    """
    serializer_class = ContactUsSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = ContactUs.objects.all().order_by("-created_at")

class MyPostsView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PostSerializer
    pagination_class = PostCursorPagination

    def get_queryset(self):
        return Post.objects.filter(author=self.request.user).prefetch_related('likes', 'comments', 'board')


class MyCommentsView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PostCursorPagination
    serializer_class = MyCommentSerializer

    def get_queryset(self):
        user = self.request.user
        return Comment.objects.filter(author=user, parent__isnull=True).prefetch_related('post__board', 'likes')

class ReportPostView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        reporter = request.user

        post_id = data.get("post_id")
        board_id = data.get("board_id")
        user_id = data.get("user_id")
        reason_text = data.get("report_reason")

        post = Post.objects.filter(id=post_id).first()
        if not post:
            return Response({"error": "Post not found."}, status=404)
        if post.author == reporter:
            return Response({"error": "You cannot report your own post."}, status=400)
        if Report.objects.filter(reporter=reporter, post_id=post_id, comment_id__isnull=True).exists():
            return Response({"error": "You have already reported this post."}, status=400)

        reason_enum = ReportReason.OTHER  # 기본값
        for choice in ReportReason.choices:
            if choice[1] == reason_text:
                reason_enum = choice[0]
                break

        Report.objects.create(
            reporter=reporter,
            reported_user_id=user_id,
            board_id=board_id,
            post_id=post_id,
            reason=reason_enum,
            reason_text=reason_text,
        )
        return Response(status=200)


class ReportCommentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        reporter = request.user

        comment_id = data.get("comment_id")
        post_id = data.get("post_id")
        board_id = data.get("board_id")
        user_id = data.get("user_id")
        reason_text = data.get("reason") or ""            

        comment = Comment.objects.filter(id=comment_id, post_id=post_id).first()
        if not comment:
            return Response({"error": "Comment not found."}, status=404)
        if comment.author == reporter:
            return Response({"error": "You cannot report your own comment."}, status=400)
        if Report.objects.filter(reporter=reporter, post_id=post_id, comment_id=comment_id).exists():
            return Response({"error": "You have already reported this comment."}, status=400)

        reason_enum = ReportReason.OTHER
        for choice in ReportReason.choices:
            if choice[1] == reason_text:
                reason_enum = choice[0]
                break

        Report.objects.create(
            reporter=reporter,
            reported_user_id=user_id,
            board_id=board_id,
            post_id=post_id,
            comment_id=comment_id,
            reason=reason_enum,
            reason_text=reason_text,
        )
        return Response(status=200)

class ReportProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        reporter = request.user
        user_id = request.data.get("user_id")
        reason_text = request.data.get("report_reason")

        if not user_id or not reason_text:
            return Response({"error": "user_id and report_reason are required."}, status=400)

        if int(user_id) == reporter.id:
            return Response({"error": "You cannot report yourself."}, status=400)

        reported_user = User.objects.filter(id=user_id, is_active=True).first()
        if not reported_user:
            return Response({"error": "User not found."}, status=404)

        # 프로필 신고는 post_id = 0, comment_id = None 으로 저장
        already_reported = Report.objects.filter(
            reporter=reporter,
            post_id=0,
            comment_id__isnull=True,
            reported_user=reported_user
        ).exists()

        if already_reported:
            return Response({"error": "You have already reported this user."}, status=400)

        Report.objects.create(
            reporter=reporter,
            reported_user=reported_user,
            board_id=0,
            post_id=0,
            comment_id=None,
            reason=ReportReason.OTHER,
            reason_text=reason_text
        )
        return Response(status=200)

class ReportMeetingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        meeting_id = request.data.get("meeting_id")
        reason_text = request.data.get("report_reason")

        if meeting.creator == user:
            return Response({"error": "You cannot report your own meeting."}, status=400)

        if not meeting_id or not reason_text:
            return Response({"error": "meeting_id and report_reason are required."}, status=400)

        from apps.meetup.models import Meeting
        meeting = get_object_or_404(Meeting, id=meeting_id)

        already_reported = Report.objects.filter(
            reporter=user,
            meeting_id=meeting_id
        ).exists()
        if already_reported:
            return Response({"error": "You have already reported this meeting."}, status=400)

        reason_enum = ReportReason.OTHER
        for choice in ReportReason.choices:
            if choice[1] == reason_text:
                reason_enum = choice[0]
                break

        Report.objects.create(
            reporter=user,
            reported_user=meeting.creator,
            board_id=0, post_id=0, comment_id=None,
            meeting_id=meeting_id,
            reason=reason_enum,
            reason_text=reason_text
        )

        return Response(status=200)

class MeetupNotificationSettingView(APIView):
    """
    GET/PUT: 이벤트 알림 수신 설정 조회 및 수정
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        setting, _ = UserSetting.objects.get_or_create(user=request.user)
        return Response({"meetup_notification": setting.meetup_notification}, status=200)

    def put(self, request):
        value = request.data.get("meetup_notification")

        if not isinstance(value, bool):
            return Response({"error": "Invalid value. Expected boolean."}, status=400)

        setting, _ = UserSetting.objects.get_or_create(user=request.user)
        setting.meetup_notification = value
        setting.save()

        return Response({"meetup_notification": setting.meetup_notification}, status=200)

class LikedMeetingsView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MeetingDetailSerializer
    pagination_class = MeetingCursorPagination

    def get_queryset(self):
        return Meeting.objects.filter(
            liked_users=self.request.user
        ).order_by("-start_time")

class UpcomingMeetingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        meetings = Meeting.objects.filter(
            participants=request.user,
            start_time__gte=timezone.now()
        ).order_by("-start_time")
        serializer = MeetingDetailSerializer(meetings, many=True, context={"request": request})
        return Response(serializer.data, status=200)
    
class PastMeetingsView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MeetingDetailSerializer
    pagination_class = MeetingCursorPagination

    def get_queryset(self):
        return Meeting.objects.filter(
            participants=self.request.user,
            start_time__lt=timezone.now()
        ).order_by("-start_time")