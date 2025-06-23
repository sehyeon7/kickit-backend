from rest_framework.pagination import CursorPagination

class MeetingCursorPagination(CursorPagination):
    ordering = 'start_time'
    page_size = 10