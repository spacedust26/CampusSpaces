from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.

class Organization(models.Model):
    """Organization model for clubs, departments, etc."""
    ORGANIZATION_TYPES = [
        ('CLUB', 'Club'),
        ('DEPARTMENT', 'Department'),
        ('ADMIN', 'Administration'),
    ]
    
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=ORGANIZATION_TYPES)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name

class UserProfile(models.Model):
    """Extended user profile with role information"""
    ROLES = [
        ('STUDENT', 'Student'),
        ('FACULTY', 'Faculty'),
        ('ADMIN', 'Administrator'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLES)
    phone = models.CharField(max_length=15, blank=True, null=True)
    organizations = models.ManyToManyField(Organization, through='UserOrganization')
    
    def __str__(self):
        return f"{self.user.username} - {self.role}"

class UserOrganization(models.Model):
    """Relationship between users and organizations with hierarchy level"""
    LEVELS = [
        (1, 'Member'),
        (2, 'Representative'),
        (3, 'Leader'),
    ]
    
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    level = models.IntegerField(choices=LEVELS, default=1)
    
    class Meta:
        unique_together = ('user', 'organization')
    
    def __str__(self):
        return f"{self.user.user.username} - {self.organization.name} - {self.get_level_display()}"

class Building(models.Model):
    """Building model"""
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return self.name

class HRPersonnel(models.Model):
    """HR Personnel model for technicians, cleaners, etc."""
    HR_TYPES = [
        ('TECHNICIAN', 'Technician'),
        ('CLEANER', 'Cleaner'),
        ('SECURITY', 'Security'),
        ('OTHER', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    hr_type = models.CharField(max_length=20, choices=HR_TYPES)
    
    def __str__(self):
        return f"{self.name} - {self.get_hr_type_display()}"

class Resource(models.Model):
    """Abstract base class for resources"""
    RESOURCE_STATUS = [
        ('AVAILABLE', 'Available'),
        ('MAINTENANCE', 'Under Maintenance'),
        ('RESERVED', 'Reserved'),
    ]
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=RESOURCE_STATUS, default='AVAILABLE')
    hr_responsible = models.ForeignKey(HRPersonnel, on_delete=models.SET_NULL, null=True, blank=True)
    building = models.ForeignKey(Building, on_delete=models.CASCADE)
    
    class Meta:
        abstract = True

class Room(Resource):
    """Room model for classrooms, lecture halls, etc."""
    ROOM_TYPES = [
        ('CLASSROOM', 'Classroom'),
        ('LECTURE_HALL', 'Lecture Hall'),
        ('SEMINAR_ROOM', 'Seminar Room'),
        ('LAB', 'Laboratory'),
        ('CONFERENCE_ROOM', 'Conference Room'),
    ]
    
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES)
    capacity = models.IntegerField()
    floor = models.IntegerField()
    room_number = models.CharField(max_length=20)
    
    def __str__(self):
        return f"{self.name} - {self.building.name} - {self.room_number}"

class Equipment(Resource):
    """Equipment model for projectors, PCs, etc."""
    EQUIPMENT_TYPES = [
        ('PROJECTOR', 'Projector'),
        ('PC', 'Computer'),
        ('MICROPHONE', 'Microphone'),
        ('SPEAKER', 'Speaker'),
        ('OTHER', 'Other'),
    ]
    
    equipment_type = models.CharField(max_length=20, choices=EQUIPMENT_TYPES)
    model_number = models.CharField(max_length=50, blank=True, null=True)
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, related_name='equipment', null=True, blank=True)
    serial_number = models.CharField(max_length=100, blank=True, null=True, help_text='Unique identifier for this physical equipment')
    
    def __str__(self):
        room_info = f" - {self.room.room_number}" if self.room else ""
        return f"{self.name} - {self.get_equipment_type_display()}{room_info}"

class Booking(models.Model):
    """Booking model for room and equipment reservations"""
    BOOKING_STATUS = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=BOOKING_STATUS, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_bookings')
    rejected_reason = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.title} - {self.room.name} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"
    
    def is_conflicting(self):
        """Check if this booking conflicts with any existing approved bookings"""
        conflicting_bookings = Booking.objects.filter(
            room=self.room,
            status='APPROVED',
            start_time__lt=self.end_time,
            end_time__gt=self.start_time
        ).exclude(id=self.id)
        
        return conflicting_bookings.exists()

class BookingEquipment(models.Model):
    """Many-to-many relationship between bookings and equipment"""
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='booking_equipment')
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('booking', 'equipment')
    
    def __str__(self):
        room_info = f" ({self.equipment.room.room_number})" if self.equipment.room else ""
        return f"{self.booking.title} - {self.equipment.name}{room_info}"

class Notification(models.Model):
    """Notification model for system notifications"""
    NOTIFICATION_TYPES = [
        ('BOOKING_CREATED', 'Booking Created'),
        ('BOOKING_APPROVED', 'Booking Approved'),
        ('BOOKING_REJECTED', 'Booking Rejected'),
        ('BOOKING_CANCELLED', 'Booking Cancelled'),
        ('CONFLICT', 'Booking Conflict'),
        ('HR_TASK', 'HR Task Notification'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=100)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
