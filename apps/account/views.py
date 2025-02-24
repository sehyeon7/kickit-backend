import os
from rest_framework.views import APIView
from django.contrib.auth import login
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import status, generics, permissions
from django.contrib.auth import authenticate, logout
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.db.models import Q

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from .models import UserProfile, School, Department
from .serializers import (
    RegisterSerializer, UserProfileSerializer,
    SchoolSerializer, DepartmentSerializer, GoogleLoginSerializer,
    NicknameCheckSerializer, NicknameUpdateSerializer, ProfileUpdateSerializer, ProfileCompletionSerializer
)

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')

class GoogleLoginView(APIView):
    """
    1) 프론트엔드에서 Google 로그인 → ID Token 획득
    2) 이 endpoint에 POST로 { "id_token": "..." } 전송
    3) 서버가 ID Token 검증 → User 생성/조회
    4) DRF 세션/토큰 로그인 or JWT 발급(상황에 따라)
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        id_token_value = serializer.validated_data['id_token']

        try:
            # 구글 ID Token 검증
            idinfo = id_token.verify_oauth2_token(
                id_token_value,
                google_requests.Request(),
                GOOGLE_CLIENT_ID
            )
            # idinfo 예: {'iss': 'accounts.google.com', 'sub': '1234567890', 'email': '...' ...}

            # sub: 구글 계정 고유 ID
            google_sub = idinfo['sub']
            email = idinfo.get('email')

            # 유저가 이미 존재하는지 확인
            profile = UserProfile.objects.filter(google_sub=google_sub).first()
            if profile:
                # 이미 가입된 유저
                user = profile.user
                is_new_user = False
            else:
                # 새 유저 생성
                username = f"google_{google_sub}"  # 고유 username 만들기
                user = User.objects.create(
                    username=username,
                    email=email
                )
                # 비밀번호는 사용 안 함(소셜 로그인 전용), 더미값 지정 가능
                user.set_unusable_password()
                user.save()

                profile = UserProfile.objects.create(
                    user=user,
                    google_sub=google_sub
                )
                is_new_user = True

            # Django 세션 로그인(혹은 JWT 토큰 발급)
            login(request, user)  # 세션 기반이라면

            return Response({
                "email": email,
                "is_new_user": is_new_user
            }, status=status.HTTP_200_OK)

        except ValueError:
            # ID Token이 유효하지 않은 경우
            return Response({"error": "유효하지 않은 Google ID Token"}, status=status.HTTP_400_BAD_REQUEST)

class NicknameCheckView(APIView):
    """
    닉네임 중복 확인
    POST로 { "nickname": "..." } 전달 → 중복 여부 응답
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = NicknameCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nickname = serializer.validated_data['nickname']

        # Profile 중 동일 닉네임이 있는지 검사
        exists = UserProfile.objects.filter(nickname__iexact=nickname).exists()
        if exists:
            return Response({"available": False}, status=200)
        return Response({"available": True}, status=200)

class NicknameUpdateView(APIView):
    """
    로그인된 사용자(소셜 가입 후) → 닉네임 설정
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = NicknameUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nickname = serializer.validated_data['nickname']

        # 중복 체크
        exists = UserProfile.objects.filter(nickname__iexact=nickname).exclude(user=request.user).exists()
        if exists:
            return Response({"error": "이미 사용 중인 닉네임입니다."}, status=400)

        profile = request.user.profile
        profile.nickname = nickname
        profile.save()

        return Response({"detail": "닉네임이 설정되었습니다.", "nickname": nickname}, status=200)



class RegisterView(generics.CreateAPIView):
    """
    username, password, email, school, department를 받아 회원가입
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer


class LoginView(APIView):
    """
    username, password로 로그인
    """
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)

        if user:
            if not user.is_active:
                return Response({"error": "비활성화된 계정입니다. (탈퇴 처리됨)"}, status=status.HTTP_403_FORBIDDEN)
            
            return Response({"success": f"로그인 성공 {username}"}, status=status.HTTP_200_OK)
        return Response({"error": "로그인 실패"}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(APIView):
    """
    로그아웃
    - 세션 인증 기준 (Django default)
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)  # Django의 logout
        return Response({"detail": "로그아웃 되었습니다."}, status=status.HTTP_200_OK)


class SchoolListView(generics.ListAPIView):
    """
    /accounts/schools/
    => 전체 학교 목록을 반환
    """
    queryset = School.objects.all().order_by('name')
    serializer_class = SchoolSerializer


class DepartmentListView(generics.ListAPIView):
    """
    /accounts/departments/?school_id=?
    => 특정 학교에 속한 학과 리스트만 반환
    """
    serializer_class = DepartmentSerializer

    def get_queryset(self):
        school_id = self.request.query_params.get('school_id')
        if not school_id:
            raise ValidationError({"error": "school_id query parameter is required"})
        
        return Department.objects.filter(school_id=school_id).order_by('name')

class ProfileUpdateView(generics.UpdateAPIView):
    """
    PATCH /accounts/profile/
    body: {
      "school": <school_id>,
      "admission_year": "2023",
      "department": <department_id>
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProfileUpdateSerializer

    def get_object(self):
        return self.request.user.profile

    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)


class BlockUserView(APIView):
    """
    특정 사용자를 차단/차단해제
    POST /accounts/block/<user_id>/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id):
        target_user = get_object_or_404(User, id=user_id)
        if target_user == request.user:
            return Response({"error": "자기 자신은 차단할 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        profile = request.user.profile
        if target_user in profile.blocked_users.all():
            # 이미 차단 중이라면 => 차단 해제
            profile.blocked_users.remove(target_user)
            return Response({"detail": f"{target_user.username} 차단 해제"}, status=status.HTTP_200_OK)
        else:
            # 차단
            profile.blocked_users.add(target_user)
            return Response({"detail": f"{target_user.username} 차단 완료"}, status=status.HTTP_200_OK)

class ProfileCompletionView(generics.UpdateAPIView):
    """
    PATCH /accounts/profile/complete/
    body: {
      "school": "ABC University",
      "admission_year": "2023",
      "department": "Computer Science"
    }
    => 저장 후 is_profile_complete = True
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProfileCompletionSerializer

    def get_object(self):
        return self.request.user.profile

    def perform_update(self, serializer):
        profile = serializer.save()
        # 필수 필드가 모두 채워졌다면 is_profile_complete = True
        if profile.school and profile.admission_year and profile.department:
            profile.is_profile_complete = True
            profile.save()
        else:
            # 혹시라도 필수 항목이 누락된 경우는 남겨둠
            pass