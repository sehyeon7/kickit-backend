from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserSetting
from apps.account.models import UserProfile

class UserSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSetting
        fields = [
            'notification_type',
            'notify_when_post_liked',
            'notify_when_commented',
            'notify_when_mentioned'
        ]

class NicknameUpdateSerializer(serializers.Serializer):
    """
    닉네임 변경 시 이용
    """
    nickname = serializers.CharField(required=True, max_length=50)

class EmailUpdateSerializer(serializers.Serializer):
    """
    이메일 변경 시 이용
    """
    email = serializers.CharField(required=True, max_length=50)

class PasswordChangeSerializer(serializers.Serializer):
    """
    비밀번호 변경
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

class UserDeactivateSerializer(serializers.Serializer):
    """
    회원 탈퇴(또는 비활성화)
    """
    confirm = serializers.BooleanField()

class LikedPostsSerializer(serializers.Serializer):
    """
    내가 좋아요한 게시글
    """
    post_id = serializers.IntegerField()
    title = serializers.CharField()
    board_name = serializers.CharField()
    created_at = serializers.DateTimeField()

class ScrappedPostsSerializer(serializers.Serializer):
    """
    내가 스크랩한 게시글
    """
    post_id = serializers.IntegerField()
    title = serializers.CharField()
    board_name = serializers.CharField()
    created_at = serializers.DateTimeField()

class ProfileImageUpdateSerializer(serializers.Serializer):
    """
    프로필 이미지 변경 Serializer
    """
    image = serializers.ImageField()