# Generated by Django 5.1.5 on 2025-06-23 07:49

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('settings_app', '0005_remove_usersetting_notification_type_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Report',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('board_id', models.IntegerField()),
                ('post_id', models.IntegerField()),
                ('comment_id', models.IntegerField(blank=True, null=True)),
                ('reason', models.IntegerField(choices=[(0, '기타'), (1, '음란성 게시물'), (2, '욕설 및 차별/혐오표현'), (3, '상업적 광고 및 판매'), (4, '게시판 성격에 맞지 않는 게시물')], default=0)),
                ('reason_text', models.CharField(blank=True, max_length=300)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reported_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reports_received', to=settings.AUTH_USER_MODEL)),
                ('reporter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports_made', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('reporter', 'post_id', 'comment_id')},
            },
        ),
    ]
