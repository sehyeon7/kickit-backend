from django.urls import path
from . import views
from .views import MeetingDetailView, MeetingListView, JoinMeetingView, CreateMeetingView, ToggleMeetingCloseView, MeetingParticipantsView, KickParticipantView

urlpatterns = [
    path("<int:meeting_id>/", MeetingDetailView.as_view(), name="meeting-detail"),
    path('', MeetingListView.as_view(), name="meeting-list"),
    path("<int:meeting_id>/join/", JoinMeetingView.as_view(), name="meeting-join"),
    path("create/", CreateMeetingView.as_view(), name="meeting-create"),
    path("<int:meeting_id>/toggle-close/", ToggleMeetingCloseView.as_view()),
    path("<int:meeting_id>/participants/", MeetingParticipantsView.as_view()),
    path("<int:meeting_id>/kick/", KickParticipantView.as_view()),
]