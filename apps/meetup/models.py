# Create your models here.
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from apps.account.models import Language, Nationality, School

class RLG(models.TextChoices):
    SEOUL = "Seoul"
    BUSAN = "Busan"
    DAEGU = "Daegu"
    INCHEON = "Incheon"
    GWANGJU = "Gwangju"
    DAEJEON = "Daejeon"
    ULSAN = "Ulsan"
    SEJONG = "Sejong"
    GYEONGGI = "Gyeonggi"
    GANGWON = "Gangwon"
    CHUNGBUK = "Chungbuk"
    CHUNGNAM = "Chungnam"
    JEONBUK = "Jeonbuk"
    JEONNAM = "Jeonnam"
    GYEONGBUK = "Gyeongbuk"
    GYEONGNAM = "Gyeongnam"
    JEJU = "Jeju"

class MeetingCategory(models.IntegerChoices):
    EVENT = 0, "Event"
    ACADEMIC = 1, "Academic"

class Meeting(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_meetings")
    title = models.CharField(max_length=255)
    description = models.TextField()
    start_time = models.DateTimeField()
    capacity = models.PositiveIntegerField()
    category_id = models.IntegerField(choices=MeetingCategory.choices)
    like_count = models.PositiveIntegerField(default=0)

    lat = models.FloatField()
    lng = models.FloatField()
    location_name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    rlg = models.CharField(choices=RLG.choices, max_length=20)

    thumbnails = models.JSONField(default=list)
    languages = models.ManyToManyField(Language)
    nationalities = models.ManyToManyField(Nationality)
    school_ids = models.ManyToManyField(School, blank=True)
    participants = models.ManyToManyField(User, related_name="joined_meetings", blank=True)
    is_closed_manual = models.BooleanField(default=False)
    liked_users = models.ManyToManyField(User, related_name="liked_meetings", blank=True)

    def is_closed(self):
        return self.participants.count() >= self.capacity or self.is_closed_manual

    def is_ended(self):
        return self.start_time < timezone.now()


class MeetingNotice(models.Model):
    meeting = models.ForeignKey("Meeting", on_delete=models.CASCADE, related_name="notices")
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class MeetingSearchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="meeting_search_histories")
    keyword = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

class MeetingQnA(models.Model):
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name="qnas")
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class MeetingQnAComment(models.Model):
    qna = models.ForeignKey(MeetingQnA, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)