from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from django.db import models
from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from rest_framework import status
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q, F, Count
from .models import Meeting
from .serializers import MeetingDetailSerializer
from .pagination import MeetingCursorPagination
from apps.account.models import Language, Nationality, School

class MeetingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, meeting_id):
        meeting = get_object_or_404(Meeting, id=meeting_id)
        serializer = MeetingDetailSerializer(meeting, context={"request": request})
        return Response(serializer.data, status=200)

class MeetingListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MeetingDetailSerializer
    pagination_class = MeetingCursorPagination

    def get_queryset(self):
        queryset = Meeting.objects.annotate(
            num_participants=models.Count("participants")
        ).filter(
            start_time__gte=timezone.now(),
            num_participants__lt=F("capacity")
        )

        rlg = self.request.query_params.get("rlg")
        if rlg:
            queryset = queryset.filter(rlg=rlg)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(location_name__icontains=search) |
                Q(description__icontains=search)
            )

        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        if start_date and end_date:
            queryset = queryset.filter(start_time__range=[start_date, end_date])

        category_id = self.request.query_params.get("category_id")
        if category_id is not None:
            queryset = queryset.filter(category_id=category_id)

        language = self.request.query_params.get("language")
        if language:
            queryset = queryset.filter(languages__language=language)

        nationality = self.request.query_params.get("nationality")
        if nationality:
            queryset = queryset.filter(nationalities__name=nationality)

        school_id = self.request.query_params.get("school_id")
        if school_id:
            queryset = queryset.filter(
                Q(schools__id=school_id) | Q(schools__isnull=True)
            )

        return queryset.order_by("-like_count", "start_time")

class JoinMeetingView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, meeting_id):
        meeting = get_object_or_404(Meeting, id=meeting_id)
        user = request.user

        if meeting.participants.filter(id=user.id).exists():
            # 시작 시간이 지나면 취소 불가
            if meeting.is_ended():
                return Response({"error": "You cannot leave the event after it has started."}, status=403)
            meeting.participants.remove(user)
            return Response({"message": "Successfully left the event."}, status=200)

        if meeting.is_closed():
            return Response({"error": "The event is full."}, status=status.HTTP_400_BAD_REQUEST)

        # 조건 검사
        if meeting.languages.exists():
            user_language_ids = user.profile.languages.values_list('id', flat=True)
            if not meeting.languages.filter(id__in=user_language_ids).exists():
                return Response(
                    {"error": "You do not meet the required language criteria."},
                    status=status.HTTP_403_FORBIDDEN
                )

        if meeting.nationalities.exists():
            user_nationality_ids = user.profile.nationalities.values_list('id', flat=True)
            if not meeting.nationalities.filter(id__in=user_nationality_ids).exists():
                return Response(
                    {"error": "You do not meet the required nationality criteria."},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        if meeting.schools.exists():
            if not meeting.schools.filter(id=user.profile.school_id).exists():
                return Response({"error": "You do not meet the required school criteria."}, status=403)

        meeting.participants.add(user)

        # 마지막 한 명이 참여한 경우 → 종료 상태 처리
        if meeting.participants.count() >= meeting.capacity:
            # is_closed()는 메서드이므로 모델 필드 아님 → 필요한 경우 별도 필드 추가해야 함
            pass

        return Response({"message": "Successfully joined the event."}, status=200)

class CreateMeetingView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MeetingDetailSerializer

    def perform_create(self, serializer):
        start_time = serializer.validated_data.get("start_time")
        if start_time and start_time < timezone.now():
            raise serializers.ValidationError({"error": "The event start time must be in the future."})
        
        meeting = serializer.save(creator=self.request.user)
        meeting.participants.add(self.request.user)

        data = self.request.data

        # languages 처리
        if data.getlist("languages") == ["all"]:
            meeting.languages.clear()
        else:
            lang_ids = Language.objects.filter(id__in=data.getlist("languages"))
            meeting.languages.set(lang_ids)

        # nationalities 처리
        if data.getlist("nationalities") == ["all"]:
            meeting.nationalities.clear()
        else:
            nat_ids = Nationality.objects.filter(id__in=data.getlist("nationalities"))
            meeting.nationalities.set(nat_ids)

        # schools 처리
        if data.getlist("school_ids") == ["all"]:
            meeting.schools.clear()
        else:
            school_ids = School.objects.filter(id__in=data.getlist("school_ids"))
            meeting.schools.set(school_ids)