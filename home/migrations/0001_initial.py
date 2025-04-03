# Generated by Django 5.1.6 on 2025-04-03 03:41

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Building',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('location', models.CharField(blank=True, max_length=255, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='HRPersonnel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('email', models.EmailField(max_length=254)),
                ('phone', models.CharField(max_length=15)),
                ('hr_type', models.CharField(choices=[('TECHNICIAN', 'Technician'), ('CLEANER', 'Cleaner'), ('SECURITY', 'Security'), ('OTHER', 'Other')], max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('type', models.CharField(choices=[('CLUB', 'Club'), ('DEPARTMENT', 'Department'), ('ADMIN', 'Administration')], max_length=20)),
                ('description', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Booking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True, null=True)),
                ('start_time', models.DateTimeField()),
                ('end_time', models.DateTimeField()),
                ('status', models.CharField(choices=[('PENDING', 'Pending Approval'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('CANCELLED', 'Cancelled'), ('COMPLETED', 'Completed')], default='PENDING', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('rejected_reason', models.TextField(blank=True, null=True)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_bookings', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('organization', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='home.organization')),
            ],
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('message', models.TextField()),
                ('notification_type', models.CharField(choices=[('BOOKING_CREATED', 'Booking Created'), ('BOOKING_APPROVED', 'Booking Approved'), ('BOOKING_REJECTED', 'Booking Rejected'), ('BOOKING_CANCELLED', 'Booking Cancelled'), ('CONFLICT', 'Booking Conflict'), ('HR_TASK', 'HR Task Notification')], max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('read', models.BooleanField(default=False)),
                ('booking', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='home.booking')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Room',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True, null=True)),
                ('image_url', models.URLField(blank=True, null=True)),
                ('status', models.CharField(choices=[('AVAILABLE', 'Available'), ('MAINTENANCE', 'Under Maintenance'), ('RESERVED', 'Reserved')], default='AVAILABLE', max_length=20)),
                ('room_type', models.CharField(choices=[('CLASSROOM', 'Classroom'), ('LECTURE_HALL', 'Lecture Hall'), ('SEMINAR_ROOM', 'Seminar Room'), ('LAB', 'Laboratory'), ('CONFERENCE_ROOM', 'Conference Room')], max_length=20)),
                ('capacity', models.IntegerField()),
                ('floor', models.IntegerField()),
                ('room_number', models.CharField(max_length=20)),
                ('building', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='home.building')),
                ('hr_responsible', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='home.hrpersonnel')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Equipment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True, null=True)),
                ('image_url', models.URLField(blank=True, null=True)),
                ('status', models.CharField(choices=[('AVAILABLE', 'Available'), ('MAINTENANCE', 'Under Maintenance'), ('RESERVED', 'Reserved')], default='AVAILABLE', max_length=20)),
                ('equipment_type', models.CharField(choices=[('PROJECTOR', 'Projector'), ('PC', 'Computer'), ('MICROPHONE', 'Microphone'), ('SPEAKER', 'Speaker'), ('OTHER', 'Other')], max_length=20)),
                ('model_number', models.CharField(blank=True, max_length=50, null=True)),
                ('quantity', models.IntegerField(default=1)),
                ('building', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='home.building')),
                ('hr_responsible', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='home.hrpersonnel')),
                ('rooms', models.ManyToManyField(blank=True, related_name='equipment', to='home.room')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='booking',
            name='room',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='home.room'),
        ),
        migrations.CreateModel(
            name='UserOrganization',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('level', models.IntegerField(choices=[(1, 'Member'), (2, 'Representative'), (3, 'Leader')], default=1)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='home.organization')),
            ],
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('STUDENT', 'Student'), ('FACULTY', 'Faculty'), ('ADMIN', 'Administrator')], max_length=20)),
                ('phone', models.CharField(blank=True, max_length=15, null=True)),
                ('organizations', models.ManyToManyField(through='home.UserOrganization', to='home.organization')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='userorganization',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='home.userprofile'),
        ),
        migrations.CreateModel(
            name='BookingEquipment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField(default=1)),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='booking_equipment', to='home.booking')),
                ('equipment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='home.equipment')),
            ],
            options={
                'unique_together': {('booking', 'equipment')},
            },
        ),
        migrations.AlterUniqueTogether(
            name='userorganization',
            unique_together={('user', 'organization')},
        ),
    ]
