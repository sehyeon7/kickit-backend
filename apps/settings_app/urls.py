from django.urls import path
from .views import (
    UserSettingDetailView,
    NicknameUpdateView, PasswordChangeView, UserDeactivateView,
    LikedPostsView, ScrappedPostsView, EmailUpdateView
)

urlpatterns = [
    path('user/', UserSettingDetailView.as_view(), name='user-setting-detail'),
    path('nickname/', NicknameUpdateView.as_view(), name='nickname-update'),
    path('email/', EmailUpdateView.as_view(), name='email-update'),
    path('password/', PasswordChangeView.as_view(), name='password-change'),
    path('deactivate/', UserDeactivateView.as_view(), name='user-deactivate'),
    path('liked-posts/', LikedPostsView.as_view(), name='liked-posts'),
    path('scrapped-posts/', ScrappedPostsView.as_view(), name='scrapped-posts'),
]