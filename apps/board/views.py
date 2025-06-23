from django.shortcuts import render

# Create your views here.
import re
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.exceptions import ValidationError, PermissionDenied
from datetime import timedelta
from django.utils.timezone import now
from rest_framework.views import APIView
from django.db.models import Count
import json

from apps.notification.utils import handle_comment_notification, handle_like_notification, handle_mention_notification
from django.core.files.uploadedfile import InMemoryUploadedFile
from .supabase_utils import upload_image_to_supabase, delete_image_from_supabase

from .models import Board, Post, Comment, PostLike, CommentLike, SearchHistory
from apps.settings_app.models import UserSetting
from .pagination import PostCursorPagination
from .serializers import (
    BoardSerializer, PostSerializer, CommentSerializer, PostCreateUpdateSerializer, SearchHistorySerializer
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

class PopularPostView(generics.RetrieveAPIView):
    """
    특정 게시판의 인기 게시물 조회 API
    - 최근 10분 내 작성된 게시물 중 최고 좋아요 게시물 반환
    - 10분 내 게시물이 없으면 이전 인기 게시물을 유지
    """
    serializer_class = PostSerializer
    permission_classes = [permissions.AllowAny]

    def get(self, request, board_id):
        board = get_object_or_404(Board, id=board_id)
        user = request.user

        # 10분 내의 인기 게시물 찾기
        ten_minutes_ago = now() - timedelta(minutes=10)
        posts_qs = Post.objects.filter(board=board, created_at__gte=ten_minutes_ago)

        if user.is_authenticated:
            posts_qs = posts_qs.exclude(hidden_by=user)
            posts_qs = posts_qs.exclude(author__in=user.profile.blocked_users.all())
        
        recent_popular_post = (
            posts_qs
            .annotate(num_likes=Count("likes"))
            .order_by("-num_likes", "-created_at")
            .first()
        )

        # 10분 내 인기 게시물이 없으면, 이전 인기 게시물 유지
        if not recent_popular_post:
            posts_qs = Post.objects.filter(board=board)
            if user.is_authenticated:
                posts_qs = posts_qs.exclude(hidden_by=user)
                posts_qs = posts_qs.exclude(author__in=user.profile.blocked_users.all())

            recent_popular_post = (
                posts_qs
                .annotate(num_likes=Count("likes"))
                .order_by("-num_likes", "-created_at")
                .first()
            )

        if not recent_popular_post:
            return Response({"error": "There are no posts in this board."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(recent_popular_post, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class PostListView(generics.ListAPIView):
    """
    전체 게시물 목록
    - 검색 기능 (search 파라미터로 제목/본문 검색)
    - 숨긴 글(hidden_by)에 포함된 게시글은 제외
    """
    serializer_class = PostSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = PostCursorPagination

    def get_queryset(self):
        user = self.request.user
        search = self.request.query_params.get('search', '').strip()

        queryset = Post.objects.all().order_by('-created_at')

        if search:
            queryset = queryset.filter(
                Q(content__icontains=search)
            )

            # 로그인 유저의 검색어 기록 저장
            if user.is_authenticated and search:
                from .models import SearchHistory 
                # 동일 키워드가 있다면 삭제 후 재삽입 (최신순 유지를 위해)
                SearchHistory.objects.filter(user=user, keyword=search).delete()
                SearchHistory.objects.create(user=user, keyword=search)

        # 로그인 유저라면 숨긴 글 / 차단 유저 필터링
        if user.is_authenticated:
            queryset = queryset.exclude(hidden_by=user)
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
    pagination_class = PostCursorPagination

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
    
    # def perform_create(self, serializer):
    #     """
    #     게시글 생성 시 board_id와 작성자를 자동으로 추가
    #     """
    #     serializer.save()
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        post = serializer.instance
        read_serializer = PostSerializer(post, context=self.get_serializer_context())
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

class PostDetailView(generics.RetrieveAPIView):
    """
    특정 Post 상세 조회
    GET /board/<board_id>/posts/<post_id>/
    """
    serializer_class = PostSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'  # Post 모델의 기본 pk
    lookup_url_kwarg = 'post_id'  # URLConf에서의 변수명

    def get_queryset(self):
        board_id = self.kwargs['board_id']
        get_object_or_404(Board, id=board_id)
        return Post.objects.filter(board_id=board_id)

class PostUpdateView(generics.UpdateAPIView):
    """
    특정 Post 수정
    PUT /board/<board_id>/posts/<post_id>/
    PATCH /board/<board_id>/posts/<post_id>/
    """
    serializer_class = PostCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'post_id'

    def get_queryset(self):
        board_id = self.kwargs['board_id']
        get_object_or_404(Board, id=board_id)
        return Post.objects.filter(board_id=board_id, author=self.request.user)

    def perform_update(self, serializer):
        post = self.get_object()

        if 'content' not in self.request.data:
            raise ValidationError({"content": ["This field is required."]})

        # raw 에는 application/json 바디로 넘어온 list 혹은
        # form-data 에서 첫 번째 값(문자열) 등이 담김
        raw = self.request.data.get('existing_images', None)

        # 1) form-data multiple field
        if hasattr(self.request.data, 'getlist'):
            existing_images = self.request.data.getlist('existing_images')
        # 2) JSON body 로 ['url1','url2'] 그대로 넘어온 경우
        elif isinstance(raw, list):
            existing_images = raw
        # 3) JSON 문자열로 직렬화돼 넘어온 경우 ("[\"url1\",\"url2\"]")
        elif isinstance(raw, str):
            try:
                existing_images = json.loads(raw)
            except ValueError:
                existing_images = [raw]
        else:
            existing_images = []

        new_images = self.request.FILES.getlist('new_images')  # MultipartFile 리스트

        # 기존 DB의 이미지 URL 가져오기
        current_images = post.images or []

        # 삭제할 이미지 확인 후 Supabase에서 제거
        images_to_delete = set(current_images) - set(existing_images)
        for image_url in images_to_delete:
            delete_image_from_supabase(image_url)

        # 새로운 이미지 업로드 후 URL 저장
        uploaded_image_urls = []
        for image_file in new_images:
            if isinstance(image_file, InMemoryUploadedFile):
                image_url = upload_image_to_supabase(image_file)
                if image_url:
                    uploaded_image_urls.append(image_url)

        # 기존 이미지 + 새로운 이미지 합쳐서 저장
        serializer.save(images=existing_images + uploaded_image_urls)

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)       
        post = self.get_object()
        detailed_serializer = PostSerializer(post, context={'request': request})
        return Response(detailed_serializer.data)

class PostDeleteView(generics.DestroyAPIView):
    """
    특정 Post 삭제
    DELETE /board/<board_id>/posts/<post_id>/
    """
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'post_id'

    def get_queryset(self):
        board_id = self.kwargs['board_id']
        get_object_or_404(Board, id=board_id)
        return Post.objects.filter(board_id=board_id, author=self.request.user)

    def perform_destroy(self, instance):
        if instance.author != self.request.user:
            raise PermissionDenied("You can only delete your own posts.")
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

        if post.author == user:
            return Response({"error": "You cannot hide your own post."}, status=status.HTTP_400_BAD_REQUEST)

        if user in post.hidden_by.all():
            # 이미 숨김 중 => 숨김 해제
            post.hidden_by.remove(user)
            return Response({"detail": "The post is now unhidden."}, status=status.HTTP_200_OK)
        else:
            # 숨김
            post.hidden_by.add(user)
            return Response({"detail": "The post has been hidden."}, status=status.HTTP_200_OK)

class CommentListCreateView(generics.ListCreateAPIView):
    """
    Post에 달린 댓글/대댓글 목록 & 작성
    /board/<board_id>/posts/<post_id>/comments/
    """
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        post_id = self.kwargs['post_id']
        queryset = Comment.objects.filter(post_id=post_id, parent__isnull=True).order_by('-created_at')
        # parent가 없는 최상위 댓글만 조회 (대댓글은 replies 필드에서)

        if user.is_authenticated:
            # 차단한 유저의 댓글 제외
            blocked_users = user.profile.blocked_users.all()
            queryset = queryset.exclude(author__in=blocked_users)

            # 숨김 처리한 댓글 제외
            queryset = queryset.exclude(hidden_by=user)

        return queryset

    def create(self, request, *args, **kwargs):
        """ 댓글 작성 시 예외 처리를 추가하여 상세한 에러 메시지 반환 """
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "Login is required."}, status=status.HTTP_401_UNAUTHORIZED)

        post_id = kwargs.get('post_id')
        post = get_object_or_404(Post, id=post_id)

        board = post.board

        parent_id = request.data.get("parent")
        parent_comment = None

        # 부모 댓글이 있을 때만 검증 (최상위 댓글이면 검증 안 함)
        if parent_id:
            parent_comment = Comment.objects.filter(id=parent_id, post=post).first()
            if not parent_comment:
                return Response({"error": "Parent comment not found."}, status=status.HTTP_404_NOT_FOUND)

        # Mentions 데이터 검증
        mention_usernames = request.data.get("mentions", [])
        if mention_usernames and not isinstance(mention_usernames, list):
            return Response({"error": "The 'mentions' field must be a list."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(author=user, post=post, parent=parent_comment)

        handle_comment_notification(comment, post, board, parent_comment)

        handle_mention_notification(board, comment, mention_usernames)

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
            return Response({"error": "Login is required."}, status=status.HTTP_401_UNAUTHORIZED)
        comment = get_object_or_404(Comment, id=comment_id, post_id=post_id)
        post = comment.post
        board = post.board
    
        like_obj = comment.likes.filter(user=user).first()
        if like_obj:
            # 이미 좋아요 => 취소
            like_obj.delete()
            is_liked = False
        else:
            CommentLike.objects.create(comment=comment, user=user)
            handle_like_notification(user, board, comment, is_post=False)

        serializer = CommentSerializer(comment, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class CommentDeleteView(generics.DestroyAPIView):
    """
    댓글 삭제 API
    DELETE /board/<board_id>/posts/<post_id>/comments/<comment_id>/
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, board_id, post_id, comment_id):
        user = request.user
        comment = get_object_or_404(Comment, id=comment_id, post_id=post_id)

        # # 대댓글이 있는 경우 삭제 불가 (추가된 로직)
        # if comment.replies.exists():
        #     return Response({"error": "You cannot delete a comment that has replies."}, status=status.HTTP_400_BAD_REQUEST)

        # 본인 댓글이거나 관리자인 경우 삭제 가능
        if comment.author != user and not user.is_staff:
            return Response({"error": "You do not have permission to delete this comment."}, status=status.HTTP_403_FORBIDDEN)

        if comment.replies.exists():
            # 실제 삭제하지 않고 is_deleted로 표시
            comment.is_deleted = True
            comment.save()
        else:
            comment.delete()

        return Response({"detail": "The comment has been deleted."}, status=status.HTTP_204_NO_CONTENT)

class PostLikeToggleView(generics.GenericAPIView):
    """
    게시글 좋아요 토글
    POST /board/<board_id>/posts/<post_id>/like/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, board_id, post_id):
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "Login is required."}, status=status.HTTP_401_UNAUTHORIZED)
        post = get_object_or_404(Post, id=post_id)
        board = post.board
        like_obj = post.likes.filter(user=user).first()
        if like_obj:
            # 이미 좋아요 => 취소
            like_obj.delete()
            is_liked = False
        else:
            PostLike.objects.create(post=post, user=user)
            is_liked = True
            
            handle_like_notification(user, board, post, is_post=True)

        # 업데이트된 좋아요 개수
        like_count = post.likes.count()
        return Response(
            {
                "detail": "Liked" if is_liked else "Like removed",
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
            return Response({"detail": "Scrap removed."}, status=status.HTTP_200_OK)
        else:
            # 스크랩 추가
            post.scrapped_by.add(user)
            return Response({"detail": "Post scrapped."}, status=status.HTTP_200_OK)
        
class HideCommentView(generics.GenericAPIView):
    """
    POST /board/<board_id>/posts/<post_id>/comments/<comment_id>/hide/
    => 로그인 유저가 특정 댓글 숨김/숨김 해제
    => 숨김 처리된 댓글은 해당 유저에게만 보이지 않음
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, board_id, post_id, comment_id):
        user = request.user
        comment = get_object_or_404(Comment, id=comment_id, post_id=post_id)

        if comment.author == user:
            return Response({"error": "You cannot hide your own comment."}, status=status.HTTP_400_BAD_REQUEST)

        if user in comment.hidden_by.all():
            # 이미 숨김 처리된 경우 → 숨김 해제
            comment.hidden_by.remove(user)
            return Response({"detail": "The comment is now visible."}, status=status.HTTP_200_OK)
        else:
            # 숨김 처리
            comment.hidden_by.add(user)
            return Response({"detail": "The comment has been hidden."}, status=status.HTTP_200_OK)

class SearchHistoryListView(generics.ListAPIView):
    serializer_class = SearchHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SearchHistory.objects.filter(user=self.request.user)


class SearchHistoryDeleteView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = SearchHistory.objects.all()
    lookup_field = 'id'

    def get_queryset(self):
        return SearchHistory.objects.filter(user=self.request.user)

class SearchHistoryClearView(APIView):
    """
    로그인한 유저의 전체 검색 기록 삭제
    DELETE /search-history/clear/
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        user = request.user
        deleted_count, _ = SearchHistory.objects.filter(user=user).delete()
        return Response(
            {"detail": f"{deleted_count} search history items deleted."},
            status=status.HTTP_200_OK
        )
