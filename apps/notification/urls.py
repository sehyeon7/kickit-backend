from django.urls import path
from .views import (
    NotificationListView,
    NotificationDetailView,
    NotificationMarkAllReadView,
    MeetupNotificationListView,
    MeetupNotificationDetailView,
    MeetupNotificationMarkAllReadView,
)

urlpatterns = [
    path('', NotificationListView.as_view(), name='notification-list'),
    path('<int:pk>/', NotificationDetailView.as_view(), name='notification-detail'),
    path('mark-all-read/', NotificationMarkAllReadView.as_view(), name='notification-mark-all-read'),
    path('meetup/', MeetupNotificationListView.as_view(), name='meetup-notification-list'),
    path('meetup/<int:pk>/', MeetupNotificationDetailView.as_view(), name='meetup-notification-detail'),
    path('meetup/mark-all-read/', MeetupNotificationMarkAllReadView.as_view(), name='meetup-notification-mark-all-read'),
]