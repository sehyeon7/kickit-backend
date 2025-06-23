from django.urls import path
from .views import (
    UserSettingDetailView,
    PasswordChangeView, UserDeactivateView,
    LikedPostsView, ScrappedPostsView, EmailUpdateView,
    NotificationTypeListView, NotificationCategoryListView, ContactUsCreateView, ContactUsListView, ProfileUpdateView,
    MyPostsView, MyCommentsView, ReportPostView, ReportCommentView, ReportProfileView
)

urlpatterns = [
    # 유저 알림 설정 조회 및 변경
    path('user/notification/', UserSettingDetailView.as_view(), name='user-notification-setting-detail'),

    # 알림 타입 목록 조회
    path('notification-types/', NotificationTypeListView.as_view(), name='notification-type-list'),

    # 알림 카테고리 목록 조회
    path('notification-categories/', NotificationCategoryListView.as_view(), name='notification-category-list'),
    # path('nickname/', NicknameUpdateView.as_view(), name='nickname-update'),
    path('email/', EmailUpdateView.as_view(), name='email-update'),
    path('password/', PasswordChangeView.as_view(), name='password-change'),
    # path('profile-image/', ProfileImageUpdateView.as_view(), name='profile-image-update'),
    path('deactivate/', UserDeactivateView.as_view(), name='user-deactivate'),
    path('liked-posts/', LikedPostsView.as_view(), name='liked-posts'),
    path('scrapped-posts/', ScrappedPostsView.as_view(), name='scrapped-posts'),
    # 사용자가 문의 제출
    path("contact-us/", ContactUsCreateView.as_view(), name="contact-us"),

    # 관리자용 문의 목록 조회
    path("admin/contact-us/", ContactUsListView.as_view(), name="admin-contact-us"),
    path("user-profile/", ProfileUpdateView.as_view(), name="profile-update"),
    path('posts/', MyPostsView.as_view(), name='my-posts'),
    path('comments/', MyCommentsView.as_view(), name='my-comments'),

    path('report/post/', ReportPostView.as_view(), name='report-post'),
    path('report/comment/', ReportCommentView.as_view(), name='report-comment'),
    path('report/profile/', ReportProfileView.as_view(), name='report-profile'),
]