# Generated by Django 5.1.5 on 2025-06-23 05:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('board', '0006_post_images_delete_postimage'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
    ]
