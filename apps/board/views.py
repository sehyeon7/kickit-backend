from django.shortcuts import render

# Create your views here.
import re
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.exceptions import ValidationError, PermissionDenied


from .models import Board, Post, Comment, PostLike, CommentLike
from .serializers import (
    BoardSerializer, PostSerializer, CommentSerializer, PostLikeSerializer, PostCreateUpdateSerializer, PostImageSerializer
)

from apps.notification.utils import send_notification
from django.contrib.auth.models import User

class BoardListView(generics.ListAPIView):
    """
    게시판(Board) 목록 조회
    """
    queryset = Board.objects.all()
    serializer_class = BoardSerializer
    permission_classes = [permissions.AllowAny]


class PostListView(generics.ListAPIView):
    """
    전체 게시물 목록
    - 검색 기능 (search 파라미터로 제목/본문 검색)
    - 숨긴 글(hidden_by)에 포함된 게시글은 제외
    """
    serializer_class = PostSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user = self.request.user
        search = self.request.query_params.get('search', '')

        queryset = Post.objects.all().order_by('-created_at')
        if search:
            queryset = queryset.filter(
                Q(content__icontains=search)
            )

        # 로그인 유저라면, 숨긴 글 제외
        if user.is_authenticated:
            queryset = queryset.exclude(hidden_by=user)

            # 차단한 유저의 글도 필터링
            blocked_users = user.profile.blocked_users.all()
            queryset = queryset.exclude(author__in=blocked_users)

        return queryset

class PostListCreateView(generics.ListCreateAPIView):
    """
    특정 Board에 속한 Post 목록 조회 & 작성
    - GET: PostSerializer (읽기 전용)
    - POST: PostCreateSerializer (이미지 업로드 포함)
    """
    queryset = Post.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PostCreateUpdateSerializer
        return PostSerializer

    def get_queryset(self):
        """
        특정 Board에 속한 게시글 목록 조회
        - 숨긴 게시글 제외
        - 차단한 사용자 게시글 제외
        """
        board_id = self.kwargs['board_id']
        get_object_or_404(Board, id=board_id)

        user = self.request.user
        queryset = Post.objects.filter(board_id=board_id).order_by('-created_at')
        if user.is_authenticated:
            queryset = queryset.exclude(hidden_by=user)
            blocked_users = user.profile.blocked_users.all()
            queryset = queryset.exclude(author__in=blocked_users)
        return queryset
    
    def perform_create(self, serializer):
        """
        게시글 생성 시 board_id와 작성자를 자동으로 추가
        """
        board_id = self.kwargs['board_id']
        board = get_object_or_404(Board, id=board_id)
        serializer.save(board=board, author=self.request.user)


class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    특정 Post 상세/수정/삭제
    /board/<board_id>/posts/<post_id>/
    """
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        board_id = self.kwargs['board_id']
        get_object_or_404(Board, id=board_id)
        return Post.objects.filter(board_id=board_id)
    
    def get_object(self):
        """
        게시글이 실제 존재하는지 확인
        """
        board_id = self.kwargs.get("board_id")
        post_id = self.kwargs.get("pk")
        board = get_object_or_404(Board, id=board_id)
        post = get_object_or_404(Post, id=post_id, board=board)
        return post

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return PostCreateUpdateSerializer
        return PostSerializer

    def perform_update(self, serializer):
        post = self.get_object()
        if post.author != self.request.user:
            raise PermissionDenied("본인이 작성한 글만 수정할 수 있습니다.")
        
        if 'board_id' not in self.request.data:
            raise ValidationError({"board_id": ["이 필드는 필수입니다."]})
        if 'content' not in self.request.data:
            raise ValidationError({"content": ["이 필드는 필수입니다."]})
        
        serializer.save()
    
    def perform_destroy(self, instance):
        if instance.author != self.request.user:
            raise PermissionDenied("본인이 작성한 글만 삭제할 수 있습니다.")
        instance.delete()

class HidePostView(generics.GenericAPIView):
    """
    POST /board/<board_id>/posts/<post_id>/hide/
    => 로그인 유저가 해당 글 숨김/숨김 해제
    => 누구나 어떤 글이든 숨길 수 있음 (자기 글 포함)
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, board_id, post_id):
        board = get_object_or_404(Board, id=board_id)
        post = get_object_or_404(Post, id=post_id, board_id=board_id)
        user = request.user

        if user in post.hidden_by.all():
            # 이미 숨김 중 => 숨김 해제
            post.hidden_by.remove(user)
            return Response({"detail": "해당 글 숨김 해제"}, status=status.HTTP_200_OK)
        else:
            # 숨김
            post.hidden_by.add(user)
            return Response({"detail": "해당 글 숨김 처리"}, status=status.HTTP_200_OK)

class CommentListCreateView(generics.ListCreateAPIView):
    """
    Post에 달린 댓글/대댓글 목록 & 작성
    /board/<board_id>/posts/<post_id>/comments/
    """
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        post_id = self.kwargs['post_id']
        return Comment.objects.filter(post_id=post_id, parent__isnull=True).order_by('-created_at')
        # parent가 없는 최상위 댓글만 조회 (대댓글은 replies 필드에서)

    def create(self, request, *args, **kwargs):
        """ 댓글 작성 시 예외 처리를 추가하여 상세한 에러 메시지 반환 """
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "로그인이 필요합니다."}, status=status.HTTP_401_UNAUTHORIZED)

        post_id = kwargs.get('post_id')
        post = get_object_or_404(Post, id=post_id)

        parent_id = request.data.get("parent")
        parent_comment = None

        # 부모 댓글이 있을 때만 검증 (최상위 댓글이면 검증 안 함)
        if parent_id:
            parent_comment = Comment.objects.filter(id=parent_id, post=post).first()
            if not parent_comment:
                return Response({"error": "부모 댓글을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        # Mentions 데이터 검증
        mention_usernames = request.data.get("mentions", [])
        if mention_usernames and not isinstance(mention_usernames, list):
            return Response({"error": "mentions 필드는 리스트 형식이어야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(author=user, post=post, parent=parent_comment)

        # 댓글/대댓글 알림 처리
        if parent_comment:
            # 대댓글: 부모 댓글 작성자에게 알림
            parent_comment_author = parent_comment.author
            if getattr(parent_comment_author, 'setting', None) and parent_comment_author.setting.notify_when_commented:
                send_notification(
                    parent_comment_author,
                    "당신의 댓글에 대댓글이 달렸습니다!",
                    post_id=comment.post_id,
                    comment_id=comment.id
                )
        else:
            # 댓글: 게시글 작성자에게 알림
            post_author = post.author
            if getattr(post_author, 'setting', None) and post_author.setting.notify_when_commented:
                send_notification(
                    post_author,
                    f"'{post.title}' 글에 새 댓글이 달렸습니다!",
                    post_id=comment.post_id,
                    comment_id=comment.id
                )

        # 3) 멘션(@username) 알림
        for nickname in mention_usernames:
            try:
                mentioned_user = User.objects.get(profile__nickname=nickname)
                if getattr(mentioned_user, 'setting', None) and mentioned_user.setting.notify_when_mentioned:
                    send_notification(
                        mentioned_user,
                        f"'{user.profile.nickname}'님이 댓글에서 당신을 언급했습니다.",
                        post_id=comment.post_id,
                        comment_id=comment.id
                    )
            except User.DoesNotExist:
                continue  # 존재하지 않는 유저는 무시

        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        
class CommentLikeToggleView(generics.GenericAPIView):
    """
    댓글 좋아요 토글
    POST /board/<board_id>/posts/<post_id>/comments/<comment_id>/like/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, board_id, post_id, comment_id):
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "로그인이 필요합니다."}, status=status.HTTP_401_UNAUTHORIZED)
        comment = get_object_or_404(Comment, id=comment_id, post_id=post_id)
    
        like_obj = comment.likes.filter(user=user).first()
        if like_obj:
            # 이미 좋아요 => 취소
            like_obj.delete()
            is_liked = False
        else:
            CommentLike.objects.create(comment=comment, user=user)
            is_liked = True
        
        # 업데이트된 좋아요 개수
        like_count = comment.likes.count()

        return Response(
            {
                "detail": "좋아요 추가" if is_liked else "좋아요 취소",
                "like_count": like_count,
                "is_liked": is_liked
            },
            status=status.HTTP_200_OK
        )

class PostLikeToggleView(generics.GenericAPIView):
    """
    게시글 좋아요 토글
    POST /board/<board_id>/posts/<post_id>/like/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, board_id, post_id):
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "로그인이 필요합니다."}, status=status.HTTP_401_UNAUTHORIZED)
        post = get_object_or_404(Post, id=post_id)
        like_obj = post.likes.filter(user=user).first()
        if like_obj:
            # 이미 좋아요 => 취소
            like_obj.delete()
            is_liked = False
        else:
            PostLike.objects.create(post=post, user=user)
            is_liked = True
            # 알림 로직
            post_author = post.author
            setting = getattr(post_author, 'setting', None)
            if setting and setting.notify_when_post_liked:
                message = f"당신의 글 '{post.title}'가 좋아요를 받았습니다."
                send_notification(post_author, message, post_id=post.id)

        # 업데이트된 좋아요 개수
        like_count = post.likes.count()
        return Response(
            {
                "detail": "좋아요 추가" if is_liked else "좋아요 취소",
                "like_count": like_count,
                "is_liked": is_liked
            },
            status=status.HTTP_200_OK
        )



class ScrapToggleView(generics.GenericAPIView):
    """
    스크랩 기능 (토글)
    /board/<board_id>/posts/<post_id>/scrap/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, board_id, post_id):
        post = get_object_or_404(Post, id=post_id, board_id=board_id)
        user = request.user

        if user in post.scrapped_by.all():
            # 이미 스크랩 되어 있으면 스크랩 해제
            post.scrapped_by.remove(user)
            return Response({"detail": "스크랩 해제"}, status=status.HTTP_200_OK)
        else:
            # 스크랩 추가
            post.scrapped_by.add(user)
            return Response({"detail": "스크랩 추가"}, status=status.HTTP_200_OK)