from django.shortcuts import render

# Create your views here.
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import get_object_or_404
from django.contrib.auth import logout
from .supabase_utils import upload_image_to_supabase


from .models import UserSetting
from .serializers import (
    UserSettingSerializer, NicknameUpdateSerializer,
    PasswordChangeSerializer, UserDeactivateSerializer,
    LikedPostsSerializer, ScrappedPostsSerializer, EmailUpdateSerializer,
    ProfileImageUpdateSerializer
)
from apps.account.models import UserProfile
from apps.board.models import PostLike, Post
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

class UserSettingDetailView(generics.RetrieveUpdateAPIView):
    """
    GET/PUT: 알림 설정 조회/변경
    """
    serializer_class = UserSettingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        setting, _ = UserSetting.objects.get_or_create(user=self.request.user)
        return setting


class NicknameUpdateView(views.APIView):
    """
    POST: 닉네임 변경
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = NicknameUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        nickname = serializer.validated_data['nickname']
        profile = request.user.profile
        profile.nickname = nickname
        profile.save()

        return Response({"detail": f"닉네임이 {nickname} 으로 변경되었습니다."}, status=status.HTTP_200_OK)

class EmailUpdateView(views.APIView):
    """
    POST: 이메일 변경
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = EmailUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        request.user.email = email
        request.user.save()

        return Response({"detail": f"이메일이 {email} 으로 변경되었습니다."}, status=status.HTTP_200_OK)


class PasswordChangeView(views.APIView):
    """
    POST: 비밀번호 변경
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']

        user = request.user
        if not user.check_password(old_password):
            return Response({"error": "기존 비밀번호가 틀립니다."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        # JWT 기반에서는 `access_token`을 새로 발급해야 함.
        refresh = RefreshToken.for_user(user)
        response = Response({"detail": "비밀번호가 변경되었습니다."}, status=status.HTTP_200_OK)
        response.set_cookie('access_token', value=str(refresh.access_token), httponly=True, secure=True, samesite='None')
        response.set_cookie('refresh_token', value=str(refresh), httponly=True, secure=True, samesite='None')

        return Response({"detail": "비밀번호가 변경되었습니다."}, status=status.HTTP_200_OK)

class ProfileImageUpdateView(views.APIView):
    """
    PATCH: 프로필 이미지 변경
    - Supabase Storage에 이미지 업로드 후 URL 저장
    """
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        serializer = ProfileImageUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_profile = request.user.profile

        # Supabase에 이미지 업로드
        uploaded_url = upload_image_to_supabase(serializer.validated_data['image'])
        if not uploaded_url:
            return Response({"error": "이미지 업로드에 실패했습니다."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 기존 프로필 이미지 업데이트
        user_profile.profile_image = uploaded_url
        user_profile.save()

        return Response({"profile_image": uploaded_url}, status=status.HTTP_200_OK)


class UserDeactivateView(views.APIView):
    """
    POST: 회원탈퇴
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = UserDeactivateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        confirm = serializer.validated_data['confirm']
        if confirm:
            user = request.user
            user.is_active = False
            user.save()

            # JWT 토큰 블랙리스트 처리 (로그아웃 시와 동일)
            try:
                refresh_token = request.COOKIES.get("refresh_token")
                if refresh_token:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
            except TokenError:
                pass

            response = Response({"detail": "회원탈퇴되었습니다."}, status=status.HTTP_200_OK)
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")
            return response

        return Response({"error": "탈퇴가 취소되었습니다."}, status=status.HTTP_400_BAD_REQUEST)


class LikedPostsView(generics.ListAPIView):
    """
    GET: 내가 좋아요(추천)한 게시글 목록
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LikedPostsSerializer

    def get_queryset(self):
        return PostLike.objects.filter(user=self.request.user).select_related('post')


class ScrappedPostsView(generics.ListAPIView):
    """
    GET: 내가 스크랩한 게시글 목록
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ScrappedPostsSerializer

    def get_queryset(self):
        return self.request.user.scrapped_posts.all().order_by('-created_at')