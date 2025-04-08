from django.db import models
from django.contrib.auth.models import User
from fcm_django.models import FCMDevice

# Create your models here.
class School(models.Model):
    """
    회원가입 시 사용자가 검색해서 선택할 수 있는 학교 목록
    """
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name

class Department(models.Model):
    """
    특정 학교(School)에 속하는 학과(Department)
    """
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=200)

    class Meta:
        unique_together = ('school', 'name')

    def __str__(self):
        if self.school:
            return f"{self.school.name} - {self.name}"
        return self.name 

class AdmissionYear(models.Model):
    """
    회원가입 시 사용자가 선택할 수 있는 입학 연도 목록
    """
    year = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.year


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    google_sub = models.CharField(max_length=255, blank=True, null=True, unique=True)
    school = models.ForeignKey(School, null=True, blank=True, on_delete=models.SET_NULL)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL)
    admission_year = models.ForeignKey(AdmissionYear, null=True, blank=True, on_delete=models.SET_NULL)
    nickname = models.CharField(max_length=50, blank=True)

    profile_image = models.URLField(
        max_length=500, blank=True, null=True, 
        default="https://mjkitubvbpjnzihaaxjo.supabase.co//storage/v1/object/public/kickit_bucket/profile_images/default_profile.png"
    )

    # 내가 차단한 유저 목록(M2M)
    blocked_users = models.ManyToManyField(User, related_name='blocked_by', blank=True)
    fcm_token = models.CharField(max_length=255, blank=True, null=True)

    # 유학생 인증 관련 필드
    is_verified = models.BooleanField(default=False)  # 인증 여부
    verification_image = models.JSONField(default=list)


    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    @property
    def display_nickname(self):
        return self.nickname if self.nickname else self.user.username
    
    @property
    def display_name(self):
        if not self.user.is_active:
            return "알 수 없음"
        return self.nickname or self.user.username


