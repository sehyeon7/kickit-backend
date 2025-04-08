from django.contrib import admin
from .models import ContactUs

# Register your models here.
class ContactUsAdmin(admin.ModelAdmin):
    list_display = ('email', 'title', 'created_at', 'is_resolved')
    list_display_links = ('title',)  # title 클릭 시 상세보기 가능
    list_filter = ('is_resolved', 'created_at')
    search_fields = ('email', 'title', 'details')

    readonly_fields = ('user', 'email', 'title', 'details', 'created_at')  # 읽기 전용 필드 지정
    fields = ('user', 'email', 'title', 'details', 'created_at', 'is_resolved')  # 상세 페이지에 표시될 순서