from rest_framework.pagination import CursorPagination

class PostCursorPagination(CursorPagination):
    """
    게시글 목록을 무한 스크롤 방식으로 제공하는 커서 페이지네이션
    """
    page_size = 7  # 한 페이지에서 불러올 게시글 개수
    ordering = "-created_at"  # 최신순 정렬