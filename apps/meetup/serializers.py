from rest_framework import serializers
from .models import Meeting, MeetingNotice, MeetingSearchHistory, MeetingQnA, MeetingQnAComment

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

