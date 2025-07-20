from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from django.db import models
import json
from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from rest_framework import status
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q, F, Count
from .models import Meeting, MeetingNotice, MeetingSearchHistory, MeetingQnA, MeetingQnAComment
from .serializers import (
    MeetingDetailSerializer, ParticipantSerializer, MeetingNoticeListSerializer, 
    MeetingSearchHistorySerializer, MeetingQnASerializer, MeetingCreateSerializer
)
from apps.account.models import Language, Nationality, School
from django.contrib.auth.models import User
from .supabase_utils import upload_image_to_supabase, delete_image_from_supabase
from .pagination import MeetingCursorPagination

from apps.notification.utils import (
    handle_join_meeting_notification,
    handle_notice_created_notification,
    handle_question_notification,
    handle_qna_comment_notification, 
    handle_kick_participant_notification
)

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
        
        if meeting.school_ids.exists():
            if not meeting.schools.filter(id=user.profile.school_id).exists():
                return Response({"error": "You do not meet the required school criteria."}, status=403)

        meeting.participants.add(user)
        handle_join_meeting_notification(meeting, user)

        # 마지막 한 명이 참여한 경우 → 종료 상태 처리
        if meeting.participants.count() >= meeting.capacity:
            # is_closed()는 메서드이므로 모델 필드 아님 → 필요한 경우 별도 필드 추가해야 함
            pass

        return Response({"message": "Successfully joined the event."}, status=200)

class CreateMeetingView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = MeetingCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data    = serializer.validated_data
        loc     = data.pop('location')
        thumbs  = data.pop('thumbnails', [])
        langs   = data.pop('languages')
        nats    = data.pop('nationalities')
        schools = data.pop('school_ids')

        # 이벤트 생성
        meeting = Meeting.objects.create(
            title         = data['title'],
            start_time    = data['start_time'],
            capacity      = data['capacity'],
            category_id   = data['category_id'],
            description   = data['description'],
            lat           = loc['lat'],
            lng           = loc['lng'],
            location_name = loc['name'],
            address       = loc['address'],
            rlg           = loc['rlg'],
            creator       = request.user
        )

        # M2M 설정
        if langs == ['all']:
            meeting.languages.clear()
        else:
            meeting.languages.set(
                Language.objects.filter(language__in=langs)
            )
        if nats == ['all']:
            meeting.nationalities.clear()
        else:
            meeting.nationalities.set(
                Nationality.objects.filter(name__in=nats)
            )
        if schools == ['all']:
            meeting.school_ids.clear()
        else:
            meeting.school_ids.set(
                School.objects.filter(pk__in=[int(s) for s in schools])
            )

        # 썸네일 업로드
        urls = []
        for f in thumbs:
            url = upload_image_to_supabase(f)
            if url:
                urls.append(url)
        meeting.thumbnails = urls
        meeting.save()

        # 응답
        output = MeetingDetailSerializer(meeting, context={'request': request})
        return Response(output.data, status=status.HTTP_201_CREATED)


class ToggleMeetingCloseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, meeting_id):
        meeting = get_object_or_404(Meeting, id=meeting_id)
        user = request.user

        if meeting.creator != user:
            return Response({"error": "You are not the creator of this meeting."}, status=403)

        if meeting.is_ended():
            return Response({"error": "The meeting has already ended."}, status=400)

        meeting.is_closed_manual = not meeting.is_closed_manual
        meeting.save()

        return Response(status=200)

class MeetingParticipantsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, meeting_id):
        meeting = get_object_or_404(Meeting, id=meeting_id)

        creator_data = ParticipantSerializer(meeting.creator).data
        participants_data = ParticipantSerializer(
            meeting.participants.exclude(id=meeting.creator.id), many=True
        ).data

        return Response({
            "creator": creator_data,
            "participants": participants_data
        }, status=200)

class KickParticipantView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, meeting_id):
        meeting = get_object_or_404(Meeting, id=meeting_id)
        user = request.user

        if meeting.creator != user:
            return Response({"error": "You are not the creator of this meeting."}, status=403)

        if meeting.is_ended():
            return Response({"error": "The meeting has already ended."}, status=400)

        remove_user_id = request.data.get("remove_user_id")
        if not remove_user_id:
            return Response({"error": "Missing 'remove_user_id'"}, status=400)

        if int(remove_user_id) == user.id:
            return Response({"error": "You cannot remove yourself."}, status=400)

        remove_user = get_object_or_404(User, id=remove_user_id)

        if not meeting.participants.filter(id=remove_user.id).exists():
            return Response({"error": "User is not a participant."}, status=400)

        meeting.participants.remove(remove_user)
        handle_kick_participant_notification(meeting, remove_user)
        return Response(status=200)

class UpdateMeetingView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, meeting_id):
        meeting = get_object_or_404(Meeting, id=meeting_id)

        if meeting.creator != request.user:
            return Response({"error": "You are not the creator."}, status=403)

        title = request.data.get("title")
        description = request.data.get("description")
        existing_images_raw = request.data.get("existing_images")
        if isinstance(existing_images_raw, str):
            try:
                existing_images = json.loads(existing_images_raw)
            except:
                existing_images = []
        elif isinstance(existing_images_raw, list):
            existing_images = existing_images_raw
        else:
            existing_images = []

        new_files = request.FILES.getlist("new_images")
        current_images = meeting.thumbnails or []
        to_delete = set(current_images) - set(existing_images)
        for url in to_delete:
            delete_image_from_supabase(url)

        new_urls = []
        for file in new_files:
            uploaded = upload_image_to_supabase(file)
            if uploaded:
                new_urls.append(uploaded)

        meeting.title = title
        meeting.description = description
        meeting.thumbnails = existing_images + new_urls
        meeting.save()

        return Response(MeetingDetailSerializer(meeting, context={"request": request}).data, status=200)

class DeleteMeetingView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, meeting_id):
        meeting = get_object_or_404(Meeting, id=meeting_id)

        if meeting.creator != request.user:
            return Response({"error": "You are not the creator."}, status=403)

        if meeting.is_ended():
            return Response({"error": "You cannot delete a past meeting."}, status=400)

        if meeting.participants.exclude(id=request.user.id).exists():
            return Response({"error": "Other participants exist."}, status=400)
        
        for url in meeting.thumbnails:
            delete_image_from_supabase(url)

        meeting.delete()
        return Response(status=204)

class CreateMeetingNoticeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, meeting_id):
        meeting = get_object_or_404(Meeting, id=meeting_id)
        if meeting.creator != request.user:
            return Response({"error": "Only creator can write notice."}, status=403)

        content = request.data.get("content")
        notice = MeetingNotice.objects.create(meeting=meeting, author=request.user, content=content)
        handle_notice_created_notification(notice)
        return Response(status=201)

class ListMeetingNoticesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, meeting_id):
        meeting = get_object_or_404(Meeting, id=meeting_id)
        notices = meeting.notices.all().order_by('-created_at')
        return Response({
            "author": {
                "id": meeting.creator.id,
                "nickname": meeting.creator.profile.nickname,
                "profile_image": meeting.creator.profile.profile_image
            },
            "notices": MeetingNoticeListSerializer(notices, many=True).data
        }, status=200)

class DeleteMeetingNoticeView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, meeting_id, notice_id):
        meeting = get_object_or_404(Meeting, id=meeting_id)
        notice = get_object_or_404(MeetingNotice, id=notice_id, meeting=meeting)

        if notice.author != request.user:
            return Response({"error": "Only author can delete."}, status=403)

        notice.delete()
        return Response(status=204)

class ToggleMeetingLikeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, meeting_id):
        meeting = get_object_or_404(Meeting, id=meeting_id)
        user = request.user

        if hasattr(meeting, 'liked_users') and user in meeting.liked_users.all():
            meeting.liked_users.remove(user)
            meeting.like_count = F("like_count") - 1
            is_liked = False
        else:
            meeting.liked_users.add(user)
            meeting.like_count = F("like_count") + 1
            is_liked = True
        meeting.save()
        meeting.refresh_from_db()
        return Response({"is_liked": is_liked}, status=200)

class MeetingSearchHistoryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        histories = MeetingSearchHistory.objects.filter(user=request.user)
        serializer = MeetingSearchHistorySerializer(histories, many=True)
        return Response(serializer.data, status=200)

class MeetingSearchHistoryDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, history_id):
        history = get_object_or_404(MeetingSearchHistory, id=history_id, user=request.user)
        history.delete()
        return Response(status=204)

class MeetingSearchHistoryDeleteAllView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        MeetingSearchHistory.objects.filter(user=request.user).delete()
        return Response(status=204)

class CreateMeetingQnAView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, meeting_id):
        meeting = get_object_or_404(Meeting, id=meeting_id)
        user = request.user

        if not meeting.participants.filter(id=user.id).exists():
            return Response({"error": "Only participants can post Q&A."}, status=403)

        content = request.data.get("content")
        if not content:
            return Response({"error": "Missing content."}, status=400)

        qna = MeetingQnA.objects.create(meeting=meeting, author=user, content=content)
        handle_question_notification(qna)
        return Response(status=201)

class CreateMeetingQnACommentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, qna_id):
        qna = get_object_or_404(MeetingQnA, id=qna_id)
        user = request.user

        if user != qna.author and user != qna.meeting.creator:
            return Response({"error": "You are not allowed to comment."}, status=403)

        content = request.data.get("content")
        if not content:
            return Response({"error": "Missing content."}, status=400)

        comment = MeetingQnAComment.objects.create(qna=qna, author=user, content=content)
        handle_qna_comment_notification(comment)
        return Response(status=201)

class MeetingQnAListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, meeting_id):
        meeting = get_object_or_404(Meeting, id=meeting_id)
        user = request.user

        if user == meeting.creator:
            qnas = meeting.qnas.all().order_by('-created_at')
        else:
            qnas = meeting.qnas.filter(author=user).order_by('-created_at')

        serializer = MeetingQnASerializer(qnas, many=True)
        return Response(serializer.data, status=200)

class HostedUpcomingMeetingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id, is_active=True)
        meetings = Meeting.objects.filter(
            creator=user,
            start_time__gte=timezone.now()
        ).order_by('-start_time')

        serializer = MeetingDetailSerializer(meetings, many=True, context={"request": request})
        return Response(serializer.data, status=200)

class HostedPastMeetingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id, is_active=True)
        meetings = Meeting.objects.filter(
            creator=user,
            start_time__lt=timezone.now()
        ).order_by('-start_time')

        serializer = MeetingDetailSerializer(meetings, many=True, context={"request": request})
        return Response(serializer.data, status=200)