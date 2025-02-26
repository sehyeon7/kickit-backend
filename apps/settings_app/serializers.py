from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserSetting
from apps.account.models import UserProfile
from apps.settings_app.models import NotificationType, NotificationCategory

class NotificationTypeSerializer(serializers.ModelSerializer):
    """
    알림 타입 Serializer
    """
    class Meta:
        model = NotificationType
        fields = ['id', 'name']

class NotificationCategorySerializer(serializers.ModelSerializer):
    """
    알림 카테고리 Serializer
    """
    class Meta:
        model = NotificationCategory
        fields = ['id', 'name']

class UserSettingSerializer(serializers.ModelSerializer):
    """
    유저 알림 설정 Serializer
    """
    notification_type = NotificationTypeSerializer()
    notification_categories = NotificationCategorySerializer(many=True)

    class Meta:
        model = UserSetting
        fields = ['notification_type', 'notification_categories']

    def update(self, instance, validated_data):
        """
        알림 설정 업데이트
        """
        notification_type_data = validated_data.pop('notification_type', None)
        notification_categories_data = validated_data.pop('notification_categories', [])

        # 알림 타입 업데이트
        if notification_type_data:
            notification_type = NotificationType.objects.get(id=notification_type_data['id'])
            instance.notification_type = notification_type

        # 알림 카테고리 업데이트
        instance.notification_categories.set([
            NotificationCategory.objects.get(id=cat['id']) for cat in notification_categories_data
        ])

        instance.save()
        return instance

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