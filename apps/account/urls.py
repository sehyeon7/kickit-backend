from django.urls import path
from .views import (
    UserSignupView, GoogleAuthCheckView, LoginView, LogoutView,
    BlockUserView,
    NicknameCheckView, ProfileUpdateView,
    SchoolListView,
    PasswordResetRequestView, TokenRefreshView, RegisterFCMTokenView,
    VerificationStatusView, PasswordResetView, BlockedUsersListView,
    LanguageListView, NationalityListView
)

urlpatterns = [
    # 구글 소셜 로그인 인증 및 기존 유저 여부 확인
    path('google/auth-check/', GoogleAuthCheckView.as_view(), name='google-auth-check'),

    # 통합 회원가입 (일반 + 구글)
    path('signup/', UserSignupView.as_view(), name='user-signup'),

    # 일반 로그인
    path('login/', LoginView.as_view(), name='login'),

    # 로그아웃
    path('logout/', LogoutView.as_view(), name='logout'),

    # 토큰 갱신
    path('token-refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # 닉네임 체크 & 설정
    path('nickname/check/', NicknameCheckView.as_view(), name='nickname-check'),

    # 학교/학번/학과 입력
    path('profile/', ProfileUpdateView.as_view(), name='profile-update'),

    # 학교/학과/입학연도 검색
    path('schools/', SchoolListView.as_view(), name='school-list'),
    # path('departments/', DepartmentListView.as_view(), name='department-list'),
    # path('admission_year/', AdmissionYearListView.as_view(), name='admission-year-list'),

    # 유저 차단
    path('block/<int:user_id>/', BlockUserView.as_view(), name='block-user'),
    path('blocked-users/', BlockedUsersListView.as_view(), name='blocked-users-list'),

    # 비밀번호 재설정 링크 요청
    path('password-reset/request/', PasswordResetRequestView.as_view(), name='password-reset-request'),

    # 비밀번호 최종 변경 (앱에서)
    path("password-reset/", PasswordResetView.as_view(), name="password-reset"),

    path("register-fcm-token/", RegisterFCMTokenView.as_view(), name="register-fcm-token"),

    path("verification-status/", VerificationStatusView.as_view(), name="verification-status"),

    path('languages/', LanguageListView.as_view(), name='language-list'),
    path('nationalities/', NationalityListView.as_view(), name='nationality-list'),
]