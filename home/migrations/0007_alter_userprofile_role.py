# Generated by Django 5.1.6 on 2025-04-07 07:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0006_alter_userprofile_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='role',
            field=models.CharField(choices=[('STUDENT', 'Student'), ('FACULTY', 'Faculty'), ('ADMIN', 'Administrator')], default='STUDENT', max_length=20),
        ),
    ]
