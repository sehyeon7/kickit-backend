from django.contrib import admin
from .models import ContactUs, Report

# Register your models here.
@admin.register(ContactUs)
class ContactUsAdmin(admin.ModelAdmin):
    list_display = ('email', 'title', 'created_at', 'is_resolved')
    list_display_links = ('title',)  # title 클릭 시 상세보기 가능
    list_filter = ('is_resolved', 'created_at')
    search_fields = ('email', 'title', 'details')

    readonly_fields = ('user', 'email', 'title', 'details', 'created_at')  # 읽기 전용 필드 지정
    fields = ('user', 'email', 'title', 'details', 'created_at', 'is_resolved')  # 상세 페이지에 표시될 순서

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'reporter',
        'reported_user',
        'board_id',
        'post_id',
        'comment_id',
        'reason',
        'created_at',
    )
    list_display_links = ('id', 'post_id')  # 클릭 시 상세보기 가능
    list_filter = ('reason', 'created_at')
    search_fields = (
        'reporter__username',
        'reported_user__username',
        'reason_text',
    )

    readonly_fields = (
        'reporter',
        'reported_user',
        'board_id',
        'post_id',
        'comment_id',
        'reason',
        'reason_text',
        'created_at',
    )
    fields = (
        'reporter',
        'reported_user',
        'board_id',
        'post_id',
        'comment_id',
        'reason',
        'reason_text',
        'created_at',
    )