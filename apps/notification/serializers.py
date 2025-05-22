from rest_framework import serializers
from .models import Notification
from apps.board.models import Post
class NotificationSerializer(serializers.ModelSerializer):
    profile_image = serializers.SerializerMethodField()
    sender_nickname = serializers.SerializerMethodField()
    board_id = serializers.SerializerMethodField()
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'is_read', 'created_at', 'post_id', 'board_id', 'comment_id', 'profile_image', 'sender_nickname']
    
    def get_profile_image(self, obj):
        """
        알림을 보낸 주체(시스템 or 유저)의 프로필 이미지 반환
        """
        default_image_url = "https://mjkitubvbpjnzihaaxjo.supabase.co//storage/v1/object/public/kickit_bucket/profile_images/default_profile.png"

        profile = getattr(obj.sender, 'profile', None)
        return profile.profile_image if profile and profile.profile_image else default_image_url
    
    def get_board_id(self, obj):
        """
        post_id가 존재하는 경우, 해당 게시글의 board_id를 반환
        """
        if obj.post_id:
            post = Post.objects.filter(id=obj.post_id).first()
            return post.board_id if post else None
        return None
    
    def get_sender_nickname(self, obj):
        return obj.sender.profile.nickname if obj.sender else "System"