from rest_framework import serializers
from django.shortcuts import get_object_or_404
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
        return obj.author.profile.image.url if hasattr(obj.author, 'profile') and obj.author.profile.image else None
    
    def get_user_nickname(self, obj):
        return obj.author_nickname
    
    def get_reply_target_user_nickname(self, obj):
        return obj.parent.author_nickname if obj.parent else None
    
    def get_like_count(self, obj):
        return obj.likes.count()
    
    def get_is_liked(self, obj):
        user = self.context.get('request').user
        return obj.likes.filter(id=user.id).exists() if user.is_authenticated else False
    
    def get_replies(self, obj):
        if obj.replies.exists():
            return CommentSerializer(obj.replies.all(), many=True, context=self.context).data
        return []
    

class PostSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    board_name = serializers.ReadOnlyField(source='board.name')
    like_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    content_images = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'board_id', 'board_name',
            'author', 'created_at', 'content',
            'content_images', 'like_count', 'comment_count', 'is_liked'
        ]
    
    def get_content_images(self, obj):
        """ 게시글에 첨부된 이미지 반환 (없을 경우 빈 배열) """
        return [image.image_url for image in obj.images.all()] if obj.images.exists() else []
    
    def get_like_count(self, obj):
        return obj.likes.count()
    
    def get_author(self, obj):
        """ 작성자 정보 반환 """
        profile = getattr(obj.author, 'profile', None)
        return {
            "id": obj.author.id,
            "nickname": obj.author_nickname,
            "profile_image": profile.profile_image if profile and profile.profile_image else None
        }
    
    def get_comment_count(self, obj):
        """ 댓글 개수 반환 """
        return obj.comments.count()
    
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
    board_id = serializers.IntegerField(write_only=True) # board_id 필수 입력
    images = serializers.ListField(
        child=serializers.ImageField(allow_empty_file=False),
        write_only=True,
        required=False
    )

    class Meta:
        model = Post
        fields = ['board_id', 'content', 'images']
    
    def validate_board_id(self, value):
        """
        존재하는 `board_id`인지 확인
        """
        if not Board.objects.filter(id=value).exists():
            raise serializers.ValidationError("존재하지 않는 board_id 입니다.")
        return value
    
    def validate_content(self, value):
        """
        `content` 필드가 비어있지 않은지 확인
        """
        if not value.strip():
            raise serializers.ValidationError("게시글 내용은 필수 입력 항목입니다.")
        return value

    def create(self, validated_data):
        board_id = validated_data.pop('board_id')
        images = validated_data.pop('images', [])

        board = get_object_or_404(Board, id=board_id)

        user = self.context['request'].user

        post = Post.objects.create(board=board, author=user, **validated_data)

        # Supabase Storage 업로드 후, PostImage 생성
        request = self.context.get('request')
        if images and request:
            try:
                from .supabase_utils import upload_image_to_supabase
                for image_file in images:
                    image_url = upload_image_to_supabase(image_file)
                    if image_url:
                        PostImage.objects.create(post=post, image_url=image_url)
            except Exception as e:
                raise serializers.ValidationError({"images": ["이미지 업로드 중 오류가 발생했습니다."]})
        return post
