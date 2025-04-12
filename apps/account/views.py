import os
import re
from rest_framework.views import APIView
from django.contrib.auth import login
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import status, generics, permissions
from django.contrib.auth import authenticate, logout
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
import random
import string
import json
from fcm_django.models import FCMDevice
from django.core.files.uploadedfile import InMemoryUploadedFile
from .supabase_utils import upload_verification_image_to_supabase

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.core.mail import send_mail
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.parsers import MultiPartParser

FRONTEND_HOST = os.getenv('FRONTEND_HOST')

from .models import UserProfile, School, Department, AdmissionYear
from apps.settings_app.models import NotificationType, UserSetting
from .serializers import (
    UserSignupSerializer, GoogleAuthCheckSerializer, LoginSerializer, UserProfileSerializer,
    SchoolSerializer, DepartmentSerializer, GoogleLoginSerializer,
    NicknameCheckSerializer, ProfileUpdateSerializer,
    PasswordResetRequestSerializer, PasswordResetSerializer, AdmissionYearSerializer, BlockedUserSerializer
)

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
FRONTEND_HOST = os.getenv('FRONTEND_HOST')

class VerificationStatusView(APIView):
    """
    유저의 인증 상태 조회 API
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_profile = request.user.profile
        return Response(
            {
                "is_verified": user_profile.is_verified,
                "verification_image_url": user_profile.verification_image,
            },
            status=status.HTTP_200_OK
        )

def validate_password(password):
    """
    비밀번호 보안 검증: 최소 8자 이상, 숫자 및 특수문자 포함
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if not re.search(r"[0-9]", password):
        raise ValueError("Password must contain at least one number.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise ValueError("Password must contain at least one special character.")
    return password

def set_token_on_response_cookie(user: User, status_code=200) -> Response:
    try:
        # 유저 정보 확인
        print(f"Generating token for user: {user.id}, email: {user.email}, is_active: {user.is_active}")
        
        # UserProfile 존재 여부 확인
        profile_exists = UserProfile.objects.filter(user=user).exists()
        print(f"UserProfile exists: {profile_exists}")

        if not profile_exists:
            return Response({"error": "UserProfile does not exist."}, status=500)
        
        # UserProfile 가져오기
        user_profile = UserProfile.objects.get(user=user)
        user_profile_serializer = UserProfileSerializer(user_profile)

        # RefreshToken 생성
        token = RefreshToken.for_user(user)
        print(f"Generated refresh token: {token}")
        
        res = Response(user_profile_serializer.data, status=status_code)
        res.set_cookie('refresh_token', value=str(token), samesite='None', httponly=True, secure=True)
        res.set_cookie('access_token', value=str(token.access_token), samesite='None', httponly=True, secure=True)
        
        return res

    except Exception as e:
        print(f"Error in set_token_on_response_cookie: {e}")
        return Response({"error": "An error occurred while generating token."}, status=500)

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
                return set_token_on_response_cookie(user) 

            return Response({"email": email, "is_new_user": True, "google_sub": google_sub}, status=200)

        except ValueError:
            return Response({"error": "Invalid Google ID Token."}, status=400)

class UserSignupView(APIView):
    """
    통합 회원가입 (일반 + Google 로그인)
    1) 일반 회원가입 → email + password 필수
    2) Google 로그인 회원가입 → email + google_sub 필수
    """
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser]

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
        is_verified = False

        verification_images = request.FILES.getlist("verification_image", [])
        if not verification_images:
            return Response({"error": "A valid verification image is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        year_obj = AdmissionYear.objects.filter(year=admission_year).first()
        if not year_obj:
            return Response({"error": "Invalid admission year."}, status=400)

        if User.objects.filter(email=email).exists():
            return Response({"error": "This email is already registered."}, status=400)
        
        # 학교 및 학과 존재 여부 확인
        school = School.objects.filter(id=school_id).first()
        department = Department.objects.filter(id=department_id).first()
        if not school or not department:
            return Response({"error": "Invalid school or department ID."}, status=400)

        # 일반 회원가입 시 패스워드 필수
        if not google_sub and not password:
            return Response({"error": "Either google_sub or password is required."}, status=400)

        # 일반 회원가입 시 비밀번호 보안 검증
        if password:
            try:
                validate_password(password)
            except ValueError as e:
                return Response({"password": [str(e)]}, status=400)
        
        
        # 파일 형식 검증 (JPG, PNG만 허용)
        allowed_extensions = ["jpg", "jpeg", "png"]
        max_size = 5 * 1024 * 1024
        
        image_urls = []
        for image_file in verification_images:
            if not isinstance(image_file, InMemoryUploadedFile):
                return Response({"error": "Invalid uploaded file."}, status=400)
            file_ext = image_file.name.split('.')[-1].lower()

            if file_ext not in allowed_extensions:
                return Response({"error": "Unsupported file format. Only JPG and PNG are allowed."}, status=status.HTTP_400_BAD_REQUEST)

            if image_file.size > max_size:
                return Response({"error": "File size cannot exceed 5MB."}, status=status.HTTP_400_BAD_REQUEST)

            # Supabase Storage에 업로드
            image_url = upload_verification_image_to_supabase(image_file)
            if not image_url:
                return Response({"error": "Image upload failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            image_urls.append(image_url)  # 업로드된 URL 저장

        user = User.objects.create(username=email, email=email)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()

        UserProfile.objects.create(
            user=user, google_sub=google_sub, nickname=nickname,
            school_id=school_id, department_id=department_id,
            admission_year=year_obj, is_verified=is_verified, verification_image=image_urls
        )

        user.refresh_from_db()
        print(f"User refreshed: {user.id}, {user.email}")

        default_type = NotificationType.objects.filter(id=1).first()
        user_setting = UserSetting.objects.create(user=user)
        if default_type:
            user_setting.notification_type.set([default_type])

        return set_token_on_response_cookie(user, status_code=status.HTTP_201_CREATED)

class LoginView(APIView):
    """
    일반 로그인 (email + password)
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        # 이메일 또는 비밀번호 미입력 시 오류 반환
        if not email or not password:
            return Response({"error": "Email and password are required."}, status=400)
        
        # 이메일 존재 여부 확인
        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"error": "No account found with this email."}, status=400)
        
        # 비활성화된 계정인지 확인
        if not user.is_active:
            return Response({"error": "This account has been deactivated. Please contact support."}, status=403)
        
        user = authenticate(username=email, password=password)
        if not user:
            if not User.objects.filter(email=email).exists():
                return Response({"error": "No account found with this email."}, status=400)
            return Response({"error": "Incorrect password."}, status=400)

        return set_token_on_response_cookie(user)

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

class LogoutView(APIView):
    """
    로그아웃
    - JWT 토큰을 블랙리스트에 등록하여 무효화
    - HTTP-Only 쿠키에서 `access_token`, `refresh_token`을 삭제
    - `refresh_token`을 요청 Body에서도 허용
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # 인증되지 않은 사용자 접근 차단
        if not request.user.is_authenticated:
            return Response(
                {"detail": "please signin"}, status=status.HTTP_401_UNAUTHORIZED
            )
        
        # 요청 Body에서 refresh_token 확인 (쿠키에 없을 경우 대비)
        refresh_token = request.data.get("refresh_token") or request.COOKIES.get("refresh_token")
        if not refresh_token:
            return Response({"error": "No Refresh token"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tokens = OutstandingToken.objects.filter(user=request.user)

            for token in tokens:
                # 각 토큰을 블랙리스트에 추가
                RefreshToken(token.token).blacklist()


            response = Response({"detail": "You have been logged out in all devices."}, status=status.HTTP_200_OK)
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")
            return response

        except TokenError:
            return Response({"error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

class TokenRefreshView(APIView):
    """
    JWT Access Token 재발급
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            return Response({"error": "No refresh_token"}, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            refresh = RefreshToken(refresh_token)
            new_access_token = str(refresh.access_token)

            response = Response({"message": "Access token has been refreshed."}, status=status.HTTP_200_OK)
            response.set_cookie('access_token', value=new_access_token, secure=True, samesite='None')
            return response

        except TokenError:
            return Response({"error": "Invalid refresh token. Please log in again."}, status=status.HTTP_401_UNAUTHORIZED)


class SchoolListView(generics.ListAPIView):
    """
    /accounts/schools/
    => 전체 학교 목록을 반환
    """
    queryset = School.objects.all().order_by('id')
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

class AdmissionYearListView(generics.ListAPIView):
    """
    /accounts/admission_year/
    => 전체 입학연도 목록을 반환
    """
    queryset = AdmissionYear.objects.all().order_by('id')
    serializer_class = AdmissionYearSerializer

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


class BlockUserView(APIView):
    """
    특정 사용자를 차단/차단해제
    POST /accounts/block/<user_id>/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id):
        target_user = get_object_or_404(User, id=user_id)
        if target_user == request.user:
            return Response({"error": "You cannot block yourself."}, status=status.HTTP_400_BAD_REQUEST)

        action = request.data.get("action")

        if action not in ["block", "unblock"]:
            return Response(
                {"error": "A valid action must be provided. ('block' or 'unblock')"},
                status=status.HTTP_400_BAD_REQUEST
            )

        profile = request.user.profile

        if action == "block":
            profile.blocked_users.add(target_user)
            return Response(
                {"message": "User has been blocked.", "blocked_user_id": target_user.id},
                status=status.HTTP_200_OK
            )
        elif action == "unblock":
            profile.blocked_users.remove(target_user)
            return Response(
                {"message": "User has been unblocked.", "blocked_user_id": target_user.id},
                status=status.HTTP_200_OK
            )

class BlockedUsersListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # 현재 로그인된 유저의 프로필
        profile = request.user.profile
        # 차단된 유저 목록 쿼리셋
        blocked_users_qs = profile.blocked_users.all().order_by('id')

        serializer = BlockedUserSerializer(blocked_users_qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class PasswordResetRequestView(APIView):
    """
    비밀번호 재설정 요청 (이메일 전송)
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "No account found with this email."}, status=status.HTTP_400_BAD_REQUEST)

        # Django 기본 비밀번호 재설정 토큰 생성
        token = PasswordResetTokenGenerator().make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

        # 비밀번호 재설정 URL 생성 (앱에서 처리 가능하도록 딥링크 포함)
        reset_link = f"{FRONTEND_HOST}/reset-password/{uidb64}/{token}/"

        try:
            # 이메일로 비밀번호 재설정 링크 전송
            send_mail(
                subject="Password Reset Request",
                message=(
                    "You requested to reset your Squibble password.\n\n"
                    "Please tap the link below on your phone to proceed:\n"
                    f"{reset_link}\n\n"
                    "⚠️ This link is intended for use on mobile devices only.\n"
                    "If you didn't request this, you can safely ignore this email."
                ),
                from_email="no-reply@squible.net",
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception:
            return Response({"error": "An error occurred while sending the email. Please try again."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"detail": "Password reset link has been sent to your email."}, status=status.HTTP_200_OK)
    
class PasswordResetView(APIView):
    """
    이메일에서 리셋 링크 클릭 후, 앱에서 비밀번호를 최종 변경
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uidb64 = serializer.validated_data["uidb64"]
        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError):
            raise ValidationError({"error": "Invalid user request."})

        # 토큰 검증
        if not PasswordResetTokenGenerator().check_token(user, token):
            raise ValidationError({"error": "Invalid reset token. Please try again."})

        # 비밀번호 변경
        user.set_password(new_password)
        user.save()

        return Response({"detail": "Password has been changed successfully."}, status=status.HTTP_200_OK)

class RegisterFCMTokenView(APIView):
    """
    앱에서 발급받은 FCM 토큰을 등록하는 API
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        user_profile = request.user.profile
        fcm_token = request.data.get("fcm_token")
        device_type = request.data.get("device_type", "").lower()

        if not fcm_token or not isinstance(fcm_token, str) or len(fcm_token.strip()) == 0:
            return Response({"error": "A valid FCM token is required."}, status=status.HTTP_400_BAD_REQUEST)

        # 기존 토큰이 있는 경우 업데이트
        device, created = FCMDevice.objects.update_or_create(
            user=user,
            defaults={"registration_id": fcm_token, "type": device_type}
        )

        return Response({"detail": "FCM token has been registered."}, status=status.HTTP_200_OK)