from rest_framework import serializers
from .models import (
    Meeting, MeetingNotice, MeetingSearchHistory, MeetingQnA, MeetingQnAComment, RLG, MeetingCategory
)
from apps.account.models import Language, Nationality, School
from django.utils import timezone

class ParticipantSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(source='id')
    nickname = serializers.CharField(source='profile.nickname')
    profile_image = serializers.CharField(source='profile.profile_image')

class MeetingDetailSerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()
    is_closed = serializers.SerializerMethodField()
    is_ended = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_creator = serializers.SerializerMethodField()
    is_participant = serializers.SerializerMethodField()
    creator = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()
    languages = serializers.SlugRelatedField(slug_field="language", many=True, read_only=True)
    nationalities = serializers.SlugRelatedField(slug_field="name", many=True, read_only=True)
    school_ids = serializers.SlugRelatedField(slug_field="name", many=True, read_only=True)
    thumbnails = serializers.ListField(child=serializers.URLField(), required=False)

    class Meta:
        model = Meeting
        fields = [
            'id', 'title', 'start_time', 'location', 'capacity',
            'languages', 'nationalities', 'school_ids', 'category_id', 'description', 'thumbnails',
            'is_closed', 'is_ended', 'is_liked', 'creator', 'participants',
            'is_creator', 'is_participant', 'thumbnails'
        ]

    def get_location(self, obj):
        return {
            "lat": obj.lat,
            "lng": obj.lng,
            "name": obj.location_name,
            "address": obj.address,
            "rlg": obj.rlg,
        }

    def get_is_closed(self, obj):
        return obj.is_closed()

    def get_is_ended(self, obj):
        return obj.is_ended()

    def get_is_liked(self, obj):
        user = self.context["request"].user
        return obj.liked_users.filter(id=user.id).exists()

    def get_is_creator(self, obj):
        user = self.context['request'].user
        return obj.creator == user

    def get_is_participant(self, obj):
        return obj.participants.filter(id=self.context['request'].user.id).exists()

    def get_creator(self, obj):
        return ParticipantSerializer(obj.creator).data

    def get_participants(self, obj):
        return ParticipantSerializer(obj.participants.all(), many=True).data

class LocationSerializer(serializers.Serializer):
    lat     = serializers.FloatField()
    lng     = serializers.FloatField()
    name    = serializers.CharField(max_length=255)
    address = serializers.CharField(max_length=255)
    rlg     = serializers.ChoiceField(choices=RLG.choices)

    def validate_rlg(self, value):
        # 한국 지역만 허용
        # (RLG 가 모두 한국 지역이므로, 추가 검증 불필요할 수 있습니다)
        return value

class MeetingCreateSerializer(serializers.ModelSerializer):
    time           = serializers.DateTimeField(source='start_time')
    location       = LocationSerializer(write_only=True)
    capacity       = serializers.IntegerField(min_value=2, max_value=20)
    languages      = serializers.ListField(
                        child=serializers.CharField(),
                        help_text="['all'] 또는 언어 코드 리스트"
                    )
    nationalities  = serializers.ListField(
                        child=serializers.CharField(),
                        help_text="['all'] 또는 국가명 리스트"
                    )
    school_ids     = serializers.ListField(
                        child=serializers.CharField(),  # 문자열 'all' 허용
                        help_text="['all'] 또는 학교 PK 리스트"
                    )
    category_id    = serializers.ChoiceField(choices=MeetingCategory.choices)
    description    = serializers.CharField(max_length=2000)
    thumbnails     = serializers.ListField(
                        child=serializers.ImageField(),
                        required=False,
                        help_text="multipart 파일 필드"
                    )

    class Meta:
        model  = Meeting
        fields = [
            "title", "time", "location", "capacity",
            "languages", "nationalities", "school_ids",
            "category_id", "description", "thumbnails",
        ]

    def validate_time(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("The event start time must be in the future.")
        return value


class MeetingNoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingNotice
        fields = ['id', 'content', 'created_at']

class MeetingNoticeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingNotice
        fields = ['id', 'content', 'created_at']

class MeetingSearchHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingSearchHistory
        fields = ['id', 'keyword']

class MeetingQnACommentSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="author.id", read_only=True)
    user_nickname = serializers.CharField(source="author.profile.nickname", read_only=True)
    user_profile_image = serializers.CharField(source="author.profile.profile_image", read_only=True)

    class Meta:
        model = MeetingQnAComment
        fields = ["id", "user_id", "user_nickname", "user_profile_image", "content", "created_at"]

class MeetingQnASerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="author.id", read_only=True)
    user_nickname = serializers.CharField(source="author.profile.nickname", read_only=True)
    user_profile_image = serializers.CharField(source="author.profile.profile_image", read_only=True)
    comments = MeetingQnACommentSerializer(many=True, read_only=True)

    class Meta:
        model = MeetingQnA
        fields = ["id", "user_id", "user_nickname", "user_profile_image", "content", "created_at", "comments"]

