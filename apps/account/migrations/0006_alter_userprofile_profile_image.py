# Generated by Django 5.1.5 on 2025-03-07 02:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0005_userprofile_fcm_token'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='profile_image',
            field=models.URLField(blank=True, default='https://mjkitubvbpjnzihaaxjo.supabase.co//storage/v1/object/public/kickit_bucket/profile_images/default_profile.png', max_length=500, null=True),
        ),
    ]
