from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.core.mail import send_mail
from django.utils.safestring import mark_safe
from django.contrib import messages
from .models import UserProfile
from apps.notification.utils import send_verification_notification, send_verification_failure_email

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_verified', 'verification_image_preview', 'confirm_button', 'deny_button')
    list_filter = ('is_verified',)
    search_fields = ('user__username', 'school__name', 'department__name')

    def verification_image_preview(self, obj):
        """ 인증 이미지 미리보기 (작은 썸네일) """
        if obj.verification_image:
            return format_html('<img src="{}" width="50" height="50" style="border-radius:5px;" />', obj.verification_image)
        return "이미지 없음"

    verification_image_preview.short_description = "인증 이미지"

    def confirm_button(self, obj):
        """ 유저 인증 승인 버튼 """
        if not obj.is_verified:
            url = reverse('admin:confirm_verification', args=[obj.id])
            return format_html('<a class="button" href="{}" style="color:green;">✔ 승인</a>', url)
        return "승인됨"

    confirm_button.short_description = "인증 승인"

    def deny_button(self, obj):
        """ 유저 인증 거절 버튼 """
        if obj.is_verified:
            return "이미 승인됨"
        url = reverse('admin:deny_verification', args=[obj.id])
        return format_html('<a class="button" href="{}" style="color:red;">✖ 거절</a>', url)

    deny_button.short_description = "인증 거절"
# ✅ 인증 승인 뷰
def confirm_verification(request, user_id):
    user_profile = get_object_or_404(UserProfile, id=user_id)
    user_profile.is_verified = True
    user_profile.save()

    # 알림 전송
    send_verification_notification(user_profile.user, success=True)

    messages.success(request, f"{user_profile.user.username} 님의 인증을 승인했습니다.")
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/'))


# ✅ 인증 거절 뷰
def deny_verification(request, user_id):
    user_profile = get_object_or_404(UserProfile, id=user_id)

    # 알림 전송
    send_verification_failure_email(user_profile.user)

    messages.error(request, f"{user_profile.user.username} 님의 인증을 거절했습니다.")
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/'))

original_get_urls = admin.site.get_urls

# ✅ 커스텀 URL 추가
def get_admin_urls():
    custom_urls = [
        path('account/userprofile/confirm/<int:user_id>/', admin.site.admin_view(confirm_verification), name='confirm_verification'),
        path('account/userprofile/deny/<int:user_id>/', admin.site.admin_view(deny_verification), name='deny_verification'),
    ]
    return custom_urls + original_get_urls()

admin.site.get_urls = get_admin_urls