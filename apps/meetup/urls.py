from django.urls import path
from . import views
from .views import (
    MeetingDetailView, MeetingListView, JoinMeetingView, CreateMeetingView, ToggleMeetingCloseView, 
    MeetingParticipantsView, KickParticipantView, UpdateMeetingView, DeleteMeetingView,
    CreateMeetingNoticeView, ListMeetingNoticesView, DeleteMeetingNoticeView,
    ToggleMeetingLikeView
)

urlpatterns = [
    path("<int:meeting_id>/", MeetingDetailView.as_view(), name="meeting-detail"),
    path('', MeetingListView.as_view(), name="meeting-list"),
    path("<int:meeting_id>/join/", JoinMeetingView.as_view(), name="meeting-join"),
    path("create/", CreateMeetingView.as_view(), name="meeting-create"),
    path("<int:meeting_id>/toggle-close/", ToggleMeetingCloseView.as_view()),
    path("<int:meeting_id>/participants/", MeetingParticipantsView.as_view()),
    path("<int:meeting_id>/kick/", KickParticipantView.as_view()),
    path("<int:meeting_id>/update/", UpdateMeetingView.as_view()),
    path("<int:meeting_id>/delete/", DeleteMeetingView.as_view()),
    path("<int:meeting_id>/notice/", CreateMeetingNoticeView.as_view()),
    path("<int:meeting_id>/notice/list/", ListMeetingNoticesView.as_view()),
    path("<int:meeting_id>/notice/<int:notice_id>/delete/", DeleteMeetingNoticeView.as_view()),
    path("<int:meeting_id>/like/", ToggleMeetingLikeView.as_view()),
]