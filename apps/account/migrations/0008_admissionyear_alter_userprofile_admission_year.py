# Generated by Django 5.1.5 on 2025-03-11 07:16

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0007_userprofile_is_verified_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdmissionYear',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.CharField(max_length=20, unique=True)),
            ],
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='admission_year',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='account.admissionyear'),
        ),
    ]
