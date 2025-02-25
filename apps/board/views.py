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

class BlockAuthorFromPostView(generics.GenericAPIView):
    """
    게시글 작성자 차단
    POST /board/<board_id>/posts/<post_id>/block-author/
    => accounts.views.BlockUserView와 유사 로직
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, board_id, post_id):
        post = get_object_or_404(Post, id=post_id, board_id=board_id)
        target_user = post.author
        if target_user == request.user:
            return Response({"error": "자기 자신은 차단할 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        profile = request.user.profile
        if target_user in profile.blocked_users.all():
            # 이미 차단 중 => 해제
            profile.blocked_users.remove(target_user)
            return Response({"detail": f"{target_user.username} 차단 해제"}, status=status.HTTP_200_OK)
        else:
            profile.blocked_users.add(target_user)
            return Response({"detail": f"{target_user.username} 차단 완료"}, status=status.HTTP_200_OK)


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

    def perform_create(self, serializer):
        post_id = self.kwargs['post_id']
        comment = serializer.save(author=self.request.user, post_id=post_id)
        serializer.save(author=self.request.user, post_id=post_id)

        # 1) 본인이 작성한 글에 댓글이 달렸을 때
        post = get_object_or_404(Post, id=post_id)
        post_author = post.author
        setting = getattr(post_author, 'setting', None)
        if setting and setting.notify_when_commented:
            message = f"'{post.title}' 글에 새 댓글이 달렸습니다!"
            send_notification(post_author, message, post_id = comment.post_id, comment_id=comment.id)

        # 2) 대댓글인 경우 -> 부모 댓글 작성자에게 알림
        if comment.parent:
            parent_comment_author = comment.parent.author
            if parent_comment_author != post_author:  # 중복 알림 방지
                parent_setting = getattr(parent_comment_author, 'setting', None)
                if parent_setting and parent_setting.notify_when_commented:
                    message = f"당신의 댓글에 대댓글이 달렸습니다!"
                    send_notification(parent_comment_author, message, post_id = comment.post_id, comment_id=comment.id)

        # 3) 멘션(@username) 파싱 로직
        mention_pattern = r'@(\w+)'  # 예시: @ 뒤에 알파벳/숫자/_ 를 닉네임으로 가정
        matches = re.findall(mention_pattern, comment.content)
        for nickname in matches:
            # nickname이 실제 User의 profile.nickname과 일치하는지 확인
            try:
                # 여기서는 Profile.nickname 기준 예시. (user.username 으로 할 수도 있음)
                user_obj = User.objects.get(profile__nickname=nickname)
            except User.DoesNotExist:
                continue

            mention_setting = getattr(user_obj, 'setting', None)
            if mention_setting and mention_setting.notify_when_mentioned:
                message = f"'{self.request.user.profile.nickname or self.request.user.username}'님이 " \
                        f"댓글에서 당신을 언급했습니다: {comment.content}"
                send_notification(user_obj, message, post_id = comment.post_id, comment_id=comment.id)

        
        


class ReplyListCreateView(generics.ListCreateAPIView):
    """
    특정 댓글에 대한 대댓글 목록 & 작성
    /board/<board_id>/posts/<post_id>/comments/<comment_id>/replies/
    """
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        comment_id = self.kwargs['comment_id']
        return Comment.objects.filter(parent_id=comment_id).order_by('-created_at')

    def perform_create(self, serializer):
        post_id = self.kwargs['post_id']
        comment_id = self.kwargs['comment_id']
        serializer.save(author=self.request.user, post_id=post_id, parent_id=comment_id)

class CommentLikeToggleView(generics.GenericAPIView):
    """
    댓글 좋아요 토글
    POST /board/<board_id>/posts/<post_id>/comments/<comment_id>/like/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, board_id, post_id, comment_id):
        comment = get_object_or_404(Comment, id=comment_id, post_id=post_id)
        user = request.user
        like_obj = comment.likes.filter(user=user).first()
        if like_obj:
            # 이미 좋아요 => 취소
            like_obj.delete()
            return Response({"detail": "좋아요 취소"}, status=status.HTTP_200_OK)
        else:
            CommentLike.objects.create(comment=comment, user=user)
            return Response({"detail": "좋아요 추가"}, status=status.HTTP_201_CREATED)

class PostLikeToggleView(generics.GenericAPIView):
    """
    게시글 좋아요 토글
    POST /board/<board_id>/posts/<post_id>/like/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, board_id, post_id):
        post = get_object_or_404(Post, id=post_id)
        user = request.user
        like_obj = post.likes.filter(user=user).first()
        if like_obj:
            # 이미 좋아요 => 취소
            like_obj.delete()
            return Response({"detail": "좋아요 취소"}, status=status.HTTP_200_OK)
        else:
            PostLike.objects.create(post=post, user=user)
            # 알림 로직
            post_author = post.author
            setting = getattr(post_author, 'setting', None)
            if setting and setting.notify_when_post_liked:
                message = f"당신의 글 '{post.title}'가 좋아요를 받았습니다."
                send_notification(post_author, message, post_id=post.id)

            return Response({"detail": "좋아요 추가"}, status=status.HTTP_201_CREATED)



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