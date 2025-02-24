from django.urls import path
from .views import (
    RegisterView, LoginView, LogoutView,
    BlockUserView, GoogleLoginView,
    NicknameCheckView, NicknameUpdateView, ProfileUpdateView, ProfileCompletionView,
    SchoolListView, DepartmentListView
)

urlpatterns = [
    # 구글 소셜 로그인
    path('google/', GoogleLoginView.as_view(), name='google-login'),

    # 닉네임 체크 & 설정
    path('nickname/check/', NicknameCheckView.as_view(), name='nickname-check'),
    path('nickname/', NicknameUpdateView.as_view(), name='nickname-update'),

    # 학교/학번/학과 입력
    path('profile/', ProfileUpdateView.as_view(), name='profile-update'),

    # 프로필 (학교/학번/학과) 완성 권한
    path('profile/complete/', ProfileCompletionView.as_view(), name='profile-complete'),

    # 일반 회원가입/로그인
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),

    # 로그아웃
    path('logout/', LogoutView.as_view(), name='logout'),

    # 학교/학과 검색
    path('schools/', SchoolListView.as_view(), name='school-list'),
    path('departments/', DepartmentListView.as_view(), name='department-list'),

    # 유저 차단
    path('block/<int:user_id>/', BlockUserView.as_view(), name='block-user'),
]