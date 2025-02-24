from django.urls import path
from .views import (
    UserSignupView, GoogleAuthCheckView, LoginView, LogoutView,
    BlockUserView,
    NicknameCheckView, NicknameUpdateView, ProfileUpdateView,
    SchoolListView, DepartmentListView
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


    # 닉네임 체크 & 설정
    path('nickname/check/', NicknameCheckView.as_view(), name='nickname-check'),
    path('nickname/', NicknameUpdateView.as_view(), name='nickname-update'),

    # 학교/학번/학과 입력
    path('profile/', ProfileUpdateView.as_view(), name='profile-update'),

    # 학교/학과 검색
    path('schools/', SchoolListView.as_view(), name='school-list'),
    path('departments/', DepartmentListView.as_view(), name='department-list'),

    # 유저 차단
    path('block/<int:user_id>/', BlockUserView.as_view(), name='block-user'),
]