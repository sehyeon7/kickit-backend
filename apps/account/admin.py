from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import UserProfile
from apps.notification.utils import send_verification_notification, send_verification_failure_email

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'is_verified', 'verification_image_preview', 'confirm_button', 'deny_button')
    list_filter = ('is_verified',)
    search_fields = ('user__username', 'school__name', 'department__name')
    readonly_fields = ('display_verification_images',)

    def user_link(self, obj):
        url = reverse('admin:account_userprofile_change', args=[obj.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_link.short_description = "USER"

    def verification_image_preview(self, obj):
        if obj.verification_image and isinstance(obj.verification_image, list) and len(obj.verification_image) > 0:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius:5px;" />',
                obj.verification_image[0]
            )
        return "이미지 없음"
    verification_image_preview.short_description = "인증 이미지"

    def confirm_button(self, obj):
        if not obj.is_verified:
            url = reverse('admin:confirm_verification', args=[obj.id])
            return format_html('<a class="button" href="{}" style="color:green;">✔ 승인</a>', url)
        return "승인됨"
    confirm_button.short_description = "인증 승인"

    def deny_button(self, obj):
        if obj.is_verified:
            return "이미 승인됨"
        url = reverse('admin:deny_verification', args=[obj.id])
        return format_html('<a class="button" href="{}" style="color:red;">✖ 거절</a>', url)
    deny_button.short_description = "인증 거절"

    def display_verification_images(self, obj):
        if obj.verification_image and isinstance(obj.verification_image, list):
            return format_html(''.join(
                f'<img src="{img}" style="max-width:400px; margin:10px 0;" /><br/>' for img in obj.verification_image
            ))
        return "이미지 없음"
    display_verification_images.short_description = "전체 인증 이미지"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('confirm/<int:user_id>/', self.admin_site.admin_view(self.confirm_verification), name='confirm_verification'),
            path('deny/<int:user_id>/', self.admin_site.admin_view(self.deny_verification), name='deny_verification'),
        ]
        return custom_urls + urls

    def confirm_verification(self, request, user_id):
        profile = get_object_or_404(UserProfile, id=user_id)
        profile.is_verified = True
        profile.save()

        try:
            send_verification_notification(profile.user, success=True)
            self.message_user(request, f"{profile.user.username} 님의 인증을 승인했습니다.", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"알림 전송 실패: {e}", messages.ERROR)

        return redirect(f'../../{user_id}/change/')

    def deny_verification(self, request, user_id):
        profile = get_object_or_404(UserProfile, id=user_id)
        try:
            send_verification_failure_email(profile.user)
            self.message_user(request, f"{profile.user.username} 님의 인증을 거절했습니다.", messages.WARNING)
        except Exception as e:
            self.message_user(request, f"알림 전송 실패: {e}", messages.ERROR)

        return redirect(f'../../{user_id}/change/')