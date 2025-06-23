from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from rest_framework import status
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q
from .models import Meeting
from .serializers import MeetingDetailSerializer
from .pagination import MeetingCursorPagination

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
        queryset = Meeting.objects.filter(start_time__gte=timezone.now())

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
            queryset = queryset.filter(creator__profile__school_id=school_id)

        return queryset.order_by("-like_count", "start_time")

class JoinMeetingView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, meeting_id):
        meeting = get_object_or_404(Meeting, id=meeting_id)
        user = request.user

        if meeting.participants.filter(id=user.id).exists():
            return Response({"error": "You have already joined this event."}, status=status.HTTP_400_BAD_REQUEST)

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

        meeting.participants.add(user)
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