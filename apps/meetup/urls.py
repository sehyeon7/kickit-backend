from django.urls import path
from . import views
from .views import (
    MeetingDetailView, MeetingListView, JoinMeetingView, CreateMeetingView, ToggleMeetingCloseView, 
    MeetingParticipantsView, KickParticipantView, UpdateMeetingView, DeleteMeetingView,
    CreateMeetingNoticeView, ListMeetingNoticesView, DeleteMeetingNoticeView,
    ToggleMeetingLikeView, MeetingSearchHistoryListView, MeetingSearchHistoryDeleteView,
    CreateMeetingQnAView, CreateMeetingQnACommentView, MeetingQnAListView, MeetingSearchHistoryDeleteAllView
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
    path("search-history/", MeetingSearchHistoryListView.as_view(), name="meeting-search-history-list"),
    path("search-history/<int:history_id>/", MeetingSearchHistoryDeleteView.as_view(), name="meeting-search-history-delete"), 
    path("search-history/delete-all/", MeetingSearchHistoryDeleteAllView.as_view(), name="meeting-search-history-delete-all"),
    path("<int:meeting_id>/qna/", CreateMeetingQnAView.as_view(), name="meeting-qna-create"),
    path("qna/<int:qna_id>/comment/", CreateMeetingQnACommentView.as_view(), name="meeting-qna-comment"),
    path("<int:meeting_id>/qna/list/", MeetingQnAListView.as_view(), name="meeting-qna-list"),
]