from django.shortcuts import render

# Create your views here.
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import get_object_or_404
from django.contrib.auth import logout


from .models import UserSetting
from .serializers import (
    UserSettingSerializer, NicknameUpdateSerializer,
    PasswordChangeSerializer, UserDeactivateSerializer,
    LikedPostsSerializer, ScrappedPostsSerializer, EmailUpdateSerializer
)
from apps.account.models import UserProfile
from apps.board.models import PostLike, Post

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
        profile = request.user.profile
        profile.email = email
        profile.save()

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
        # 비밀번호 바꾸면 세션 인증 갱신 필요 (DRF Token/JWT라면 별도 로직)
        update_session_auth_hash(request, user)

        return Response({"detail": "비밀번호가 변경되었습니다."}, status=status.HTTP_200_OK)


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

            logout(request)

            return Response({"detail": "회원탈퇴되었습니다."}, status=status.HTTP_200_OK)
        return Response({"error": "탈퇴가 취소되었습니다."}, status=status.HTTP_400_BAD_REQUEST)


class LikedPostsView(views.APIView):
    """
    GET: 내가 좋아요(추천)한 게시글 목록
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        likes = PostLike.objects.filter(user=request.user)
        data = []
        for l in likes:
            data.append({
                "post_id": l.post.id,
                "title": l.post.title,
                "board_name": l.post.board.name,
                "created_at": l.post.created_at
            })
        serializer = LikedPostsSerializer(data=data, many=True)
        serializer.is_valid()
        return Response(serializer.data, status=status.HTTP_200_OK)


class ScrappedPostsView(views.APIView):
    """
    GET: 내가 스크랩한 게시글 목록
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        posts = request.user.scrapped_posts.all().order_by('-created_at')
        data = []
        for p in posts:
            data.append({
                "post_id": p.id,
                "title": p.title,
                "board_name": p.board.name,
                "created_at": p.created_at
            })
        serializer = ScrappedPostsSerializer(data=data, many=True)
        serializer.is_valid()
        return Response(serializer.data, status=status.HTTP_200_OK)