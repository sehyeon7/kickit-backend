from rest_framework import serializers
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from .models import Board, Post, Comment, PostLike, LikeType, CommentLike, SearchHistory
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.conf import settings

DEFAULT_DELETED_USER_IMAGE = (
    f"{settings.SUPABASE_URL}"
    f"/storage/v1/object/public/{settings.SUPABASE_BUCKET}"
    "/profile_images/deleted_user.png"
)


class BoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Board
        fields = ['id', 'name', 'description']

class CommentSerializer(serializers.ModelSerializer):
    """
    대댓글 구조를 직렬화할 때, 대댓글을 재귀적으로 보여줄 수도 있음
    (여기서는 'replies'를 별도 처리 혹은 필요시 중첩 시리얼라이저로 구성)
    """
    user_id = serializers.IntegerField(source='author.id', read_only=True)
    user_profile_image = serializers.SerializerMethodField()
    user_nickname = serializers.SerializerMethodField()
    reply_target_user_nickname = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'user_id', 'user_profile_image', 'user_nickname',
            'reply_target_user_nickname', 'content', 'created_at',
            'like_count', 'is_liked', 'replies'
        ]
        read_only_fields = ['user_id', 'user_profile_image', 'user_nickname', 'reply_target_user_nickname', 'like_count', 'is_liked']

    def get_user_profile_image(self, obj):
        user = obj.author
        profile = getattr(user, 'profile', None)
        if not user.is_active:
            return DEFAULT_DELETED_USER_IMAGE
        return profile.profile_image

    
    def get_user_nickname(self, obj):
        return obj.author_nickname
    
    def get_reply_target_user_nickname(self, obj):
        return obj.parent.author_nickname if obj.parent else None
    
    def get_like_count(self, obj):
        return obj.likes.count()
    
    def get_is_liked(self, obj):
        user = self.context.get('request').user
        if not user or not user.is_authenticated:
            return False
        return obj.likes.filter(user=user).exists()
    
    def get_replies(self, obj):
        user = self.context.get('request').user
        qs = obj.replies.all()
        if user and user.is_authenticated:
            blocked = user.profile.blocked_users.all()
            qs = qs.exclude(author__in=blocked)
            qs = qs.exclude(hidden_by=user)
        return CommentSerializer(qs, many=True, context=self.context).data
    

class PostSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    board_name = serializers.ReadOnlyField(source='board.name')
    like_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    content_images = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'board_id', 'board_name',
            'author', 'created_at', 'content',
            'content_images', 'like_count', 'comment_count', 'is_liked', 'comments'
        ]
    
    def get_content_images(self, obj):
        """ 게시글에 첨부된 이미지 반환 (없을 경우 빈 배열) """
        return obj.images if obj.images else []
    
    def get_like_count(self, obj):
        return obj.likes.count()
    
    def get_author(self, obj):
        """ 작성자 정보 반환 """
        user = obj.author
        profile = getattr(user, 'profile', None)
        # ③ 여기서도 동일하게 치환
        if user.is_active and profile and profile.profile_image:
            img = profile.profile_image
        else:
            img = DEFAULT_DELETED_USER_IMAGE
            
        return {
            "id": user.id,
            "nickname": obj.author_nickname,
            "profile_image": img
        }
    
    def get_comment_count(self, obj):
        """ 댓글 개수 반환 """
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None

        qs = obj.comments.all()

        if user:
            blocked_users = user.profile.blocked_users.all()
            qs = qs.exclude(author__in=blocked_users).exclude(hidden_by=user)

        return qs.count()
    
    def get_comments(self, obj):
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None

        # 최상위 댓글만 가져오고 필터링
        comments_qs = obj.comments.filter(parent__isnull=True).order_by('-created_at')
        if user:
            blocked_users = user.profile.blocked_users.all()
            comments_qs = comments_qs.exclude(author__in=blocked_users).exclude(hidden_by=user)

        return CommentSerializer(comments_qs, many=True, context=self.context).data
    
    def get_is_liked(self, obj):
        """ 현재 유저가 좋아요를 눌렀는지 반환 """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False
    


class PostCreateUpdateSerializer(serializers.ModelSerializer):
    """
    게시글 생성 시, 여러 이미지를 같이 업로드하도록
    - images 필드를 write_only로 구성 (multipart/form-data로 파일 전송)
    """
    board_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Post
        fields = ['board_id', 'content']  # 'images'는 정의 안함

    def validate_board_id(self, value):
        if not Board.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid board_id. Board does not exist.")
        return value

    def validate(self, data):
        content = data.get("content", "").strip()
        files = self.context['request'].FILES.getlist("images")

        if not content and not files:
            raise serializers.ValidationError("At least one of content or image must be provided for the post.")
        return data

    def create(self, validated_data):
        board_id = validated_data.pop('board_id')
        board = get_object_or_404(Board, id=board_id)
        user = self.context['request'].user

        # 이미지 수집
        images = self.context['request'].FILES.getlist("images")
        from .supabase_utils import upload_image_to_supabase

        image_urls = []
        for image_file in images:
            image_url = upload_image_to_supabase(image_file)
            print("[DEBUG] Image upload result:", image_url)
            if image_url:
                image_urls.append(image_url)

        print("[DEBUG] Uploaded image URLs:", image_urls)

        # 저장
        return Post.objects.create(
            board=board,
            author=user,
            images=image_urls,
            **validated_data
        )

class SearchHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchHistory
        fields = ['id', 'keyword']