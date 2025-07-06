from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, School, Department, AdmissionYear, Language, Nationality
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_str, force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ['id', 'name']

# class DepartmentSerializer(serializers.ModelSerializer):
#     school_id = serializers.IntegerField(source='school.id', read_only=True)
#     school_name = serializers.CharField(source='school.name', read_only=True)

#     class Meta:
#         model = Department
#         fields = ['id', 'name', 'school_id', 'school_name']

# class AdmissionYearSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = AdmissionYear
#         fields = ['id', 'year']

class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ['id', 'language']

class NationalitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Nationality
        fields = ['id', 'name']



class UserSerializer(ModelSerializer):
    """
    간단 조회용
    """
    class Meta:
        model = User
        fields = ["id", "username"]

class UserProfileSerializer(ModelSerializer):
    user = UserSerializer(read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    # department_name = serializers.CharField(source='department.name', read_only=True)
    # admission_year = serializers.CharField(source='admission_year.year', read_only=True)
    languages = serializers.SerializerMethodField()
    nationality = serializers.CharField(source='nationality.name', read_only=True)
    profile_image = serializers.URLField(required=False)
    is_verified = serializers.BooleanField(read_only=True)
    verification_image = serializers.SerializerMethodField()
    class Meta:
        model = UserProfile
        fields = [
            'user', 'nickname',
            'school', 'school_name',
            'profile_image', 
            # 'admission_year', 
            'languages', 'nationality',
            'is_verified', 'verification_image'
        ]
        read_only_fields = ['user', 'school_name']

    def get_verification_image(self, obj):
        """
        인증 이미지를 리스트 형태로 반환
        """
        return obj.verification_image if isinstance(obj.verification_image, list) else []
    
    def get_languages(self, obj):
        return [lang.language for lang in obj.languages.all()]

class UserSignupSerializer(serializers.Serializer):
    """
    통합 회원가입 Serializer (일반 + Google 로그인)
    """
    email = serializers.EmailField()
    nickname = serializers.CharField(max_length=50)
    school = serializers.IntegerField()
    # department = serializers.IntegerField()
    # admission_year = serializers.CharField()
    password = serializers.CharField(write_only=True, required=False)  # 일반 회원가입 용
    google_sub = serializers.CharField(write_only=True, required=False)  # 구글 로그인 용
    languages = serializers.CharField()
    nationality = serializers.CharField()
    is_verified = serializers.BooleanField(default=False, read_only=True)
    verification_image = serializers.ListField(
        child=serializers.ImageField(allow_empty_file=False),
        write_only=True,
        required=False
    )

    def validate_languages(self, value):
        try:
            ids = [int(i) for i in value.split(',') if i.strip().isdigit()]
            if not ids:
                raise serializers.ValidationError("Invalid languages input.")
            return ids
        except Exception:
            raise serializers.ValidationError("Invalid languages input.")
    
    def validate_nationality(self, value):
        try:
            return int(value)
        except ValueError:
            raise serializers.ValidationError("Invalid nationality input.")

class GoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField(write_only=True)

    # 검증 후 반환할 값들 (ex: nickname 필요 여부 등)
    email = serializers.EmailField(read_only=True)
    is_new_user = serializers.BooleanField(read_only=True)

    def validate(self, data):
        id_token = data.get('id_token')
        if not id_token:
            raise serializers.ValidationError("Google ID Token is needed.")
        return data

class GoogleAuthCheckSerializer(serializers.Serializer):
    """
    구글 ID Token 검증 Serializer
    """
    id_token = serializers.CharField(write_only=True)

    # 검증 후 반환할 값들 (유저 존재 여부)
    email = serializers.EmailField(read_only=True)
    is_new_user = serializers.BooleanField(read_only=True)
    google_sub = serializers.CharField(read_only=True)

class LoginSerializer(serializers.Serializer):
    """
    일반 로그인 Serializer (email + password)
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class NicknameCheckSerializer(serializers.Serializer):
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


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['school', 'language', 'nationality']

class PasswordResetRequestSerializer(serializers.Serializer):
    """
    비밀번호 재설정 요청 Serializer (이메일 입력)
    """
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No account exists with the provided email.")
        return value

class PasswordResetRequestSerializer(serializers.Serializer):
    """
    비밀번호 재설정 요청 Serializer (이메일 입력)
    """
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No account exists with the provided email.")
        return value

class PasswordResetSerializer(serializers.Serializer):
    """
    비밀번호 재설정 Serializer (토큰 + 새 비밀번호 입력)
    """
    uidb64 = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError("Password must include at least one number.")
        if not any(char.isalpha() for char in value):
            raise serializers.ValidationError("Password must include at least one letter.")
        return value

class BlockedUserSerializer(serializers.ModelSerializer):
    nickname = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "nickname", "profile_image"]

    def get_nickname(self, obj):
        return getattr(obj.profile, 'nickname', None)

    def get_profile_image(self, obj):
        return getattr(obj.profile, 'profile_image', None)
    
class IntroduceUpdateSerializer(serializers.Serializer):
    introduce = serializers.CharField(
        max_length=200,
        required=True,
        allow_blank=True,
        error_messages={"max_length": "Introduce must be 200 characters or fewer."}
    )    

class OtherUserProfileSerializer(serializers.ModelSerializer):
    language = serializers.CharField(source='language.language', read_only=True)
    nationality = serializers.CharField(source='nationality.name', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'profile_image', 'nickname', 'introduce',
            'language', 'nationality', 'school_name'
        ]