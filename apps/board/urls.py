from django.urls import path
from .views import (
    BoardListView,
    PostListView,
    PostListCreateView, PostDetailView,
    HidePostView,
    CommentListCreateView,
    CommentLikeToggleView,
    PostLikeToggleView, ScrapToggleView, CommentDeleteView, HideCommentView, PopularPostView,
    PostUpdateView, PostDeleteView
)

urlpatterns = [
    # Board
    path('', BoardListView.as_view(), name='board-list'),

    # 전체 게시물 + 검색
    path('posts/', PostListView.as_view(), name='all-post-list'),

    # Post
    path('<int:board_id>/posts/', PostListCreateView.as_view(), name='post-list-create'),

    # 게시글 상세 조회
    path('<int:board_id>/posts/<int:post_id>/', PostDetailView.as_view(), name='post-detail'),

    # 게시글 수정
    path('<int:board_id>/posts/<int:post_id>/update/', PostUpdateView.as_view(), name='post-update'),

    # 게시글 삭제
    path('<int:board_id>/posts/<int:post_id>/delete/', PostDeleteView.as_view(), name='post-delete'),

    # Hide / Block
    path('<int:board_id>/posts/<int:post_id>/hide/', HidePostView.as_view(), name='post-hide'),

    # Comment (일반 댓글 / 대댓글)
    path('<int:board_id>/posts/<int:post_id>/comments/', CommentListCreateView.as_view(), name='comment-list-create'),

    # Comment Like
    path('<int:board_id>/posts/<int:post_id>/comments/<int:comment_id>/like/', CommentLikeToggleView.as_view(), name='comment-like-toggle'),

    # 댓글 삭제
    path('<int:board_id>/posts/<int:post_id>/comments/<int:comment_id>/', CommentDeleteView.as_view(), name='comment-delete'),

    # Post Like
    path('<int:board_id>/posts/<int:post_id>/like/', PostLikeToggleView.as_view(), name='post-like-toggle'),

    # Scrap
    path('<int:board_id>/posts/<int:post_id>/scrap/', ScrapToggleView.as_view(), name='scrap-toggle'),

    # 댓글 숨김/숨김 해제 기능 추가
    path('<int:board_id>/posts/<int:post_id>/comments/<int:comment_id>/hide/', HideCommentView.as_view(), name='comment-hide'),

    path('<int:board_id>/posts/popular/', PopularPostView.as_view(), name='post-popular'),

]
