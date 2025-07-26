from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserSetting, NotificationCategory

@receiver(post_save, sender=User)
def create_user_setting(sender, instance, created, **kwargs):
    if created:
        setting = UserSetting.objects.create(user=instance)
        default_categories = NotificationCategory.objects.filter(name__in=["Liked", "Commented"])
        setting.notification_categories.set(default_categories)