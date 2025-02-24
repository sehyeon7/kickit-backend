from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, School, Department

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

class UserSerializer(ModelSerializer):
    """
    간단 조회용
    """
    class Meta:
        model = User
        fields = ["id", "username", "password"]

class UserProfileSerializer(ModelSerializer):
    user = UserSerializer(read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    class Meta:
        model = UserProfile
        fields = [
            'user', 'nickname',
            'school', 'school_name',
            'department', 'department_name'
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
    admission_year = serializers.CharField(max_length=10)
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
    nickname = serializers.CharField(max_length=50)

class NicknameUpdateSerializer(serializers.Serializer):
    nickname = serializers.CharField(max_length=50)

class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['school', 'admission_year', 'department']