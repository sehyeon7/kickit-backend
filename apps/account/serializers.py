from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, School, Department, AdmissionYear
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_str, force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ['id', 'name']

class DepartmentSerializer(serializers.ModelSerializer):
    school_id = serializers.IntegerField(source='school.id', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)

    class Meta:
        model = Department
        fields = ['id', 'name', 'school_id', 'school_name']

class AdmissionYearSerializer(serializers.Serializer):
    class Meta:
        model = AdmissionYear
        fields = ['id', 'year']


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
    department_name = serializers.CharField(source='department.name', read_only=True)
    admission_year = serializers.CharField(source='admission_year.year', read_only=True)
    profile_image = serializers.URLField(required=False) 
    class Meta:
        model = UserProfile
        fields = [
            'user', 'nickname',
            'school', 'school_name',
            'department', 'department_name', 'profile_image', 'admission_year'
        ]
        read_only_fields = ['user', 'school_name', 'department_name']

class UserSignupSerializer(serializers.Serializer):
    """
    통합 회원가입 Serializer (일반 + Google 로그인)
    """
    email = serializers.EmailField()
    nickname = serializers.CharField(max_length=50)
    school = serializers.IntegerField()
    department = serializers.IntegerField()
    admission_year = serializers.IntegerField()
    password = serializers.CharField(write_only=True, required=False)  # 일반 회원가입 용
    google_sub = serializers.CharField(write_only=True, required=False)  # 구글 로그인 용

class GoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField(write_only=True)

    # 검증 후 반환할 값들 (ex: nickname 필요 여부 등)
    email = serializers.EmailField(read_only=True)
    is_new_user = serializers.BooleanField(read_only=True)

    def validate(self, data):
        id_token = data.get('id_token')
        if not id_token:
            raise serializers.ValidationError("Google ID Token이 필요합니다.")
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
            "min_length": "닉네임은 최소 3자 이상이어야 합니다.",
            "max_length": "닉네임은 최대 20자 이하로 설정해주세요.",
            "blank": "닉네임은 공백일 수 없습니다."
        }
    )


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['school', 'admission_year', 'department']

class PasswordResetRequestSerializer(serializers.Serializer):
    """
    비밀번호 재설정 요청 Serializer (이메일 입력)
    """
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("해당 이메일의 계정이 존재하지 않습니다.")
        return value

class PasswordResetRequestSerializer(serializers.Serializer):
    """
    비밀번호 재설정 요청 Serializer (이메일 입력)
    """
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("해당 이메일의 계정이 존재하지 않습니다.")
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
            raise serializers.ValidationError("비밀번호는 최소 8자 이상이어야 합니다.")
        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError("비밀번호에는 숫자가 포함되어야 합니다.")
        if not any(char.isalpha() for char in value):
            raise serializers.ValidationError("비밀번호에는 영문자가 포함되어야 합니다.")
        return value