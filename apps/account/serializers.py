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

class RegisterSerializer(serializers.ModelSerializer):
    """
    회원가입 시 username, password, school, department 등을 입력받는다.
    phone_number 등 추가로 원하는 필드를 입력받을 수 있음.
    """
    school = serializers.IntegerField(required=False, write_only=True)
    department = serializers.IntegerField(required=False, write_only=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'email', 'school', 'department']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def create(self, validated_data):
        school_id = validated_data.pop('school', None)
        department_id = validated_data.pop('department', None)

        user = User(
            username=validated_data['username'],
            email=validated_data.get('email', '')
        )
        user.set_password(validated_data['password'])
        user.save()

        profile = UserProfile.objects.create(user=user)
        if school_id:
            profile.school_id = school_id
        if department_id:
            profile.department_id = department_id
        profile.save()

        return user

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

class NicknameCheckSerializer(serializers.Serializer):
    nickname = serializers.CharField(max_length=50)

class NicknameUpdateSerializer(serializers.Serializer):
    nickname = serializers.CharField(max_length=50)

class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['school', 'admission_year', 'department']

class ProfileCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['school', 'admission_year', 'department']  # 필요한 필드만