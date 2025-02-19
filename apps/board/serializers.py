from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Board, Post, Comment, PostLike, LikeType, PostImage, CommentLike

class BoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Board
        fields = ['id', 'name', 'description']

class PostImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostImage
        fields = ['id', 'image_url', 'uploaded_at']

class CommentSerializer(serializers.ModelSerializer):
    """
    대댓글 구조를 직렬화할 때, 대댓글을 재귀적으로 보여줄 수도 있음
    (여기서는 'replies'를 별도 처리 혹은 필요시 중첩 시리얼라이저로 구성)
    """
    author_username = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'post', 'author_username', 'parent',
            'content', 'created_at', 'replies', 'is_reply', 'like_count'
        ]
        read_only_fields = ['post', 'author_username', 'is_reply', 'like_count']

    def get_replies(self, obj):
        # 자식 댓글(대댓글) 목록을 직렬화
        if obj.replies.exists():
            return CommentSerializer(obj.replies.all(), many=True).data
        return None
    
    def get_like_count(self, obj):
        return obj.likes.count()
    
    def get_author_username(self, obj):
        return obj.author.profile.display_name if hasattr(obj.author, 'profile') else "알 수 없음"

class CommentLikeSerializer(serializers.ModelSerializer):
    comment_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = CommentLike
        fields = ['id', 'comment_id', 'created_at']
        read_only_fields = ['created_at']

    def create(self, validated_data):
        user = self.context['request'].user
        comment_id = validated_data['comment_id']
        obj, created = CommentLike.objects.get_or_create(
            user=user, comment_id=comment_id
        )
        return obj


class PostSerializer(serializers.ModelSerializer):
    author_username = serializers.SerializerMethodField()
    board_name = serializers.ReadOnlyField(source='board.name')
    like_count = serializers.SerializerMethodField()
    images = PostImageSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)  # 글에 달린 댓글/대댓글

    class Meta:
        model = Post
        fields = [
            'id', 'board', 'board_name', 'author_username',
            'title', 'content', 'created_at',
            'like_count',
            'scrapped_by', 'images', 'comments'
        ]
        read_only_fields = ['author_username', 'board_name', 'scrapped_by', 'images', 'comments']
    
    def get_like_count(self, obj):
        return obj.likes.count()
    
    def get_author_username(self, obj):
        return obj.author.profile.display_name if hasattr(obj.author, 'profile') else "알 수 없음"

class PostCreateUpdateSerializer(serializers.ModelSerializer):
    """
    게시글 생성 시, 여러 이미지를 같이 업로드하도록
    - images 필드를 write_only로 구성 (multipart/form-data로 파일 전송)
    """
    images = serializers.ListField(
        child=serializers.ImageField(allow_empty_file=False),
        write_only=True,
        required=False
    )

    class Meta:
        model = Post
        fields = ['board', 'title', 'content', 'images', 'link_url']

    def create(self, validated_data):
        images = validated_data.pop('images', [])
        post = Post.objects.create(**validated_data)

        # Supabase Storage 업로드 후, PostImage 생성
        request = self.context.get('request')
        if images and request:
            from .supabase_utils import upload_image_to_supabase
            for image_file in images:
                image_url = upload_image_to_supabase(image_file)
                if image_url:
                    PostImage.objects.create(post=post, image_url=image_url)
        return post

class PostLikeSerializer(serializers.ModelSerializer):
    post_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = PostLike
        fields = ['id', 'post_id', 'created_at']
        read_only_fields = ['created_at']

    def create(self, validated_data):
        user = self.context['request'].user
        post_id = validated_data['post_id']
        obj, created = PostLike.objects.get_or_create(
            user=user, post_id=post_id
        )
        return obj