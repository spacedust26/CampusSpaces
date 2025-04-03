from django.contrib import admin
from .models import (
    Organization, UserProfile, UserOrganization, Building,
    HRPersonnel, Room, Equipment, Booking, BookingEquipment, Notification
)

# Register your models here.
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'description')
    search_fields = ('name', 'type')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email', 'phone')

@admin.register(UserOrganization)
class UserOrganizationAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization', 'level')
    list_filter = ('level', 'organization')

@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ('name', 'location')
    search_fields = ('name', 'location')

@admin.register(HRPersonnel)
class HRPersonnelAdmin(admin.ModelAdmin):
    list_display = ('name', 'hr_type', 'email', 'phone')
    list_filter = ('hr_type',)
    search_fields = ('name', 'email', 'phone')

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'building', 'room_type', 'capacity', 'status')
    list_filter = ('room_type', 'building', 'status')
    search_fields = ('name', 'room_number', 'building__name')

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'equipment_type', 'status', 'building')
    list_filter = ('equipment_type', 'status', 'building')
    search_fields = ('name', 'model_number')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'room', 'start_time', 'end_time', 'status')
    list_filter = ('status', 'room__building')
    search_fields = ('title', 'user__username', 'room__name')
    date_hierarchy = 'start_time'

@admin.register(BookingEquipment)
class BookingEquipmentAdmin(admin.ModelAdmin):
    list_display = ('booking', 'equipment')
    list_filter = ('equipment__equipment_type',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'notification_type', 'created_at', 'read')
    list_filter = ('notification_type', 'read')
    search_fields = ('title', 'message', 'user__username')
    date_hierarchy = 'created_at'
