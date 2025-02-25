from django.urls import path
from .views import (
    BoardListView,
    PostListView,
    PostListCreateView, PostDetailView,
    HidePostView, BlockAuthorFromPostView,
    CommentListCreateView, ReplyListCreateView,
    CommentLikeToggleView,
    PostLikeToggleView, ScrapToggleView
)

urlpatterns = [
    # Board
    path('', BoardListView.as_view(), name='board-list'),

    # 전체 게시물 + 검색
    path('posts/', PostListView.as_view(), name='all-post-list'),

    # Post
    path('<int:board_id>/posts/', PostListCreateView.as_view(), name='post-list-create'),
    path('<int:board_id>/posts/<int:pk>/', PostDetailView.as_view(), name='post-detail'),

    # Hide / Block
    path('<int:board_id>/posts/<int:post_id>/hide/', HidePostView.as_view(), name='post-hide'),
    path('<int:board_id>/posts/<int:post_id>/block-author/', BlockAuthorFromPostView.as_view(), name='block-author'),

    # Comment (일반 댓글 / 대댓글)
    path('<int:board_id>/posts/<int:post_id>/comments/', CommentListCreateView.as_view(), name='comment-list-create'),
    path('<int:board_id>/posts/<int:post_id>/comments/<int:comment_id>/replies/', ReplyListCreateView.as_view(), name='reply-list-create'),

    # Comment Like
    path('<int:board_id>/posts/<int:post_id>/comments/<int:comment_id>/like/', CommentLikeToggleView.as_view(), name='comment-like-toggle'),

    # Post Like
    path('<int:board_id>/posts/<int:post_id>/like/', PostLikeToggleView.as_view(), name='post-like-toggle'),

    # Scrap
    path('<int:board_id>/posts/<int:post_id>/scrap/', ScrapToggleView.as_view(), name='scrap-toggle'),
]