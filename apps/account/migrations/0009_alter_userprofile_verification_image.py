# Generated by Django 5.1.5 on 2025-03-20 06:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0008_admissionyear_alter_userprofile_admission_year'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='verification_image',
            field=models.JSONField(default=list),
        ),
    ]
