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
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.core.mail import send_mail



from .models import UserProfile, School, Department
from .serializers import (
    UserSignupSerializer, GoogleAuthCheckSerializer, LoginSerializer, UserProfileSerializer,
    SchoolSerializer, DepartmentSerializer, GoogleLoginSerializer,
    NicknameCheckSerializer, NicknameUpdateSerializer, ProfileUpdateSerializer,
    PasswordResetRequestSerializer, PasswordResetSerializer
)

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
FRONTEND_HOST = os.getenv('FRONTEND_HOST')

class GoogleAuthCheckView(APIView):
    """
    구글 로그인 인증 + 유저 존재 여부 확인
    1) 프론트에서 Google 로그인 → ID Token 획득
    2) ID Token을 백엔드에 POST 요청 { "id_token": "..." }
    3) 서버가 ID Token 검증 → User 존재 여부 판별
    - 이미 존재하는 경우 로그인 처리 및 홈으로 이동
    - 존재하지 않는 경우 "ID Token 검증 성공" 메시지 전달
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = GoogleAuthCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        id_token_value = serializer.validated_data['id_token']

        try:
            idinfo = id_token.verify_oauth2_token(
                id_token_value, google_requests.Request(), GOOGLE_CLIENT_ID
            )
            google_sub = idinfo['sub']
            email = idinfo.get('email')

            profile = UserProfile.objects.filter(google_sub=google_sub).first()
            if profile:
                user = profile.user
                login(request, user)
                return Response({"email": email, "is_new_user": False, "user_id": user.id}, status=200)

            return Response({"email": email, "is_new_user": True, "google_sub": google_sub}, status=200)

        except ValueError:
            return Response({"error": "유효하지 않은 Google ID Token"}, status=400)

class UserSignupView(APIView):
    """
    통합 회원가입 (일반 + Google 로그인)
    1) 일반 회원가입 → email + password 필수
    2) Google 로그인 회원가입 → email + google_sub 필수
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        email = data["email"]
        nickname = data["nickname"]
        school_id = data["school"]
        department_id = data["department"]
        admission_year = data["admission_year"]
        password = data.get("password", None)
        google_sub = data.get("google_sub", None)

        if User.objects.filter(email=email).exists():
            return Response({"error": "이미 가입된 이메일입니다."}, status=400)

        user = User.objects.create(username=email, email=email)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()

        UserProfile.objects.create(
            user=user, google_sub=google_sub, nickname=nickname,
            school_id=school_id, department_id=department_id,
            admission_year=admission_year
        )
        login(request, user)
        return Response({"success": "회원가입 완료", "user_id": user.id}, status=201)

class LoginView(APIView):
    """
    일반 로그인 (email + password)
    """
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        user = authenticate(username=email, password=password)
        if user:
            login(request, user)
            return Response({"success": f"로그인 성공 {email}"}, status=200)
        return Response({"error": "로그인 실패"}, status=401)

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

class PasswordResetRequestView(APIView):
    """
    비밀번호 재설정 요청 (이메일 전송)
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        user = User.objects.get(email=email)
        token = PasswordResetTokenGenerator().make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

        # 수정 필요
        reset_url = f"{FRONTEND_HOST}/password-reset/{uidb64}/{token}/"

        # 이메일 전송
        send_mail(
            subject="비밀번호 재설정 요청",
            message=f"비밀번호를 재설정하려면 다음 링크를 클릭하세요: {reset_url}",
            from_email="no-reply@example.com",
            recipient_list=[email],
            fail_silently=False,
        )

        return Response({"detail": "비밀번호 재설정 이메일이 전송되었습니다."}, status=status.HTTP_200_OK)

class PasswordResetView(APIView):
    """
    비밀번호 재설정 (새 비밀번호 설정)
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response({"detail": "비밀번호가 성공적으로 변경되었습니다."}, status=status.HTTP_200_OK)
