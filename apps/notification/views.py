from django.shortcuts import render

# Create your views here.
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Notification
from .serializers import NotificationSerializer, MeetupNotificationSerializer
from rest_framework import status


class NotificationListView(generics.ListAPIView):
    """
    로그인된 사용자의 알림 목록 조회 (최근순)
    GET /notifications/
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')


class NotificationDetailView(generics.RetrieveUpdateAPIView):
    """
    특정 알림 상세 조회, 읽음 처리
    GET /notifications/<pk>/
    PATCH /notifications/<pk>/ -> { "is_read": true }
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # 내 알림만 접근 가능
        return Notification.objects.filter(user=self.request.user)

    def patch(self, request, *args, **kwargs):
        notification = self.get_object()

        notification.is_read = True
        notification.save()
        return Response({"detail": "The notification has been marked as read."}, status=status.HTTP_200_OK)

class NotificationMarkAllReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        notifications = Notification.objects.filter(user=request.user, is_read=False)

        if not notifications.exists():
            return Response({"detail": "There are no unread notifications."}, status=status.HTTP_200_OK)
        
        notifications.update(is_read=True)
        return Response({"detail": "All notifications have been marked as read."})

class MeetupNotificationListView(generics.ListAPIView):
    serializer_class = MeetupNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user,
            meetup_id__isnull=False
        ).order_by("-created_at")


class MeetupNotificationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            notification = Notification.objects.get(id=pk, user=request.user, meetup_id__isnull=False)
        except Notification.DoesNotExist:
            return Response({"error": "Notification not found."}, status=404)

        notification.is_read = True
        notification.save()
        return Response(status=200)

class MeetupNotificationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            notification = Notification.objects.get(
                id=pk,
                user=request.user,
                meetup_id__isnull=False
            )
        except Notification.DoesNotExist:
            return Response({"error": "Notification not found."}, status=404)

        is_read = request.data.get("is_read")
        if not isinstance(is_read, bool):
            return Response({"error": "is_read must be a boolean."}, status=400)

        notification.is_read = is_read
        notification.save()
        return Response(status=200)


class MeetupNotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(
            user=request.user,
            meetup_id__isnull=False,
            is_read=False
        ).update(is_read=True)
        return Response(status=200)
