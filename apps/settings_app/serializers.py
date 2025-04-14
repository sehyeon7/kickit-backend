from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserSetting
from apps.account.models import UserProfile
from apps.settings_app.models import NotificationType, NotificationCategory
from django.core.validators import validate_email
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers
from .models import ContactUs

def validate_image_extension(image):
    """
    허용된 이미지 확장자만 업로드 가능하도록 검증
    """
    valid_extensions = ["jpg", "jpeg", "png"]
    file_ext = image.name.split(".")[-1].lower()
    
    if file_ext not in valid_extensions:
        raise ValidationError("Unsupported file format. Only jpg, jpeg, and png are allowed.")

    return image

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
    - `notification_type`: 배열로 반환 (최대 1개)
    - `notification_categories`: 배열 유지
    """
    notification_type = serializers.SerializerMethodField()
    notification_categories = serializers.SerializerMethodField()

    class Meta:
        model = UserSetting
        fields = ['notification_type', 'notification_categories']

    def get_notification_type(self, obj):
        """
        단일 notification_type을 배열로 감싸서 반환
        """
        return list(obj.notification_type.values_list("id", flat=True))

    def get_notification_categories(self, obj):
        """
        notification_categories를 ID 배열로 반환
        """
        return list(obj.notification_categories.values_list("id", flat=True))


class NicknameUpdateSerializer(serializers.Serializer):
    """
    닉네임 변경 시 이용
    """
    nickname = serializers.CharField(
        min_length=3,  
        max_length=20, 
        allow_blank=False,
        error_messages={
            "min_length": "Nickname must be at least 3 characters long.",
            "max_length": "Nickname must be no more than 20 characters.",
            "blank": "Nickname cannot be blank."
        }
    )

    def validate_nickname(self, value):
        """
        닉네임이 이미 존재하는 경우 예외 처리
        """
        request = self.context.get("request")  # 현재 요청 객체 가져오기
        if not request or not request.user:
            raise serializers.ValidationError("Request information is missing.")

        user = request.user

        # 닉네임이 다른 사용자의 닉네임과 중복되는 경우 예외 처리
        if UserProfile.objects.filter(nickname=value).exclude(user=user).exists():
            raise serializers.ValidationError("This nickname is already taken.")
        
        return value

class EmailUpdateSerializer(serializers.Serializer):
    """
    이메일 변경 시 이용
    """
    email = serializers.CharField(
        required=True,
        error_messages={
            "blank": "Email is a required field.",
        }
    )

    def validate_email(self, value):
        """
        이메일 형식 및 중복 체크
        """
        try:
            validate_email(value)  # 이메일 형식 검증
        except ValidationError:
            raise serializers.ValidationError("Please enter a valid email address.")

        # 이미 존재하는 이메일인지 확인 (자기 자신 제외)
        if User.objects.filter(email=value).exclude(id=self.context["request"].user.id).exists():
            raise serializers.ValidationError("This email is already in use.")

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
    password = serializers.CharField(write_only=True, required=True)

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
    image = serializers.ImageField(validators=[validate_image_extension]) 

class UserSerializer(serializers.ModelSerializer):
    """문의한 유저 정보를 포함하는 Serializer"""
    class Meta:
        model = User
        fields = ["id", "username"]  # 필요한 필드 추가 가능

class ContactUsSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = ContactUs
        fields = ['id', 'user', 'email', 'title', 'details', 'created_at', 'is_resolved']
        read_only_fields = ['id', 'created_at', 'is_resolved']