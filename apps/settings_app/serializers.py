from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserSetting
from apps.account.models import UserProfile
from apps.settings_app.models import NotificationType, NotificationCategory
from django.core.validators import validate_email
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

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
    nickname = serializers.CharField(
        min_length=3,  
        max_length=20, 
        allow_blank=False,
        error_messages={
            "min_length": "닉네임은 최소 3자 이상이어야 합니다.",
            "max_length": "닉네임은 최대 20자 이하로 설정해주세요.",
            "blank": "닉네임은 공백일 수 없습니다."
        }
    )

    def validate_nickname(self, value):
        """
        닉네임이 이미 존재하는 경우 예외 처리
        """
        request = self.context.get("request")  # 현재 요청 객체 가져오기
        if not request or not request.user:
            raise serializers.ValidationError("요청 정보가 없습니다.")

        user = request.user

        # 닉네임이 다른 사용자의 닉네임과 중복되는 경우 예외 처리
        if UserProfile.objects.filter(nickname=value).exclude(user=user).exists():
            raise serializers.ValidationError("이미 존재하는 닉네임입니다.")
        
        return value

class EmailUpdateSerializer(serializers.Serializer):
    """
    이메일 변경 시 이용
    """
    email = serializers.CharField(
        required=True,
        error_messages={
            "blank": "이메일은 필수 입력 항목입니다.",
        }
    )

    def validate_email(self, value):
        """
        이메일 형식 및 중복 체크
        """
        try:
            validate_email(value)  # 이메일 형식 검증
        except ValidationError:
            raise serializers.ValidationError("유효한 이메일 주소를 입력해주세요.")

        # 이미 존재하는 이메일인지 확인 (자기 자신 제외)
        if User.objects.filter(email=value).exclude(id=self.context["request"].user.id).exists():
            raise serializers.ValidationError("이미 사용 중인 이메일입니다.")

        return value

class PasswordChangeSerializer(serializers.Serializer):
    """
    비밀번호 변경
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_new_password(self, value):
        """
        새 비밀번호 검증 (강도 검사)
        """
        try:
            validate_password(value)  # Django 내장 비밀번호 유효성 검사 실행
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        
        return value

class UserDeactivateSerializer(serializers.Serializer):
    """
    회원 탈퇴(또는 비활성화)
    """
    confirm = serializers.BooleanField()

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