from django.db import models
from django.contrib.auth.models import User

class Building(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Room(models.Model):
    building = models.ForeignKey(Building, related_name='rooms', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    capacity = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    available_from = models.TimeField()
    available_to = models.TimeField()
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.building.name}"

    def is_room_available(self, requested_time):
        """Check if room is available at a specific time."""
        return self.is_available and self.available_from <= requested_time <= self.available_to


class Booking(models.Model):
    room = models.ForeignKey(Room, related_name='bookings', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='bookings', on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    reason = models.TextField()
    status = models.CharField(
        max_length=20, choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Cancelled', 'Cancelled')],
        default='Pending'
    )

    def __str__(self):
        return f"Booking by {self.user.username} for {self.room.name}"

    def is_overlapping(self):
        """Check if the booking times overlap with any existing booking."""
        overlapping_bookings = Booking.objects.filter(
            room=self.room,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time
        )
        return overlapping_bookings.exists()


class RoomAmenity(models.Model):
    room = models.ForeignKey(Room, related_name='amenities', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Amenity: {self.name} for {self.room.name}"


class Cancellation(models.Model):
    booking = models.ForeignKey(Booking, related_name='cancellations', on_delete=models.CASCADE)
    cancelled_by = models.ForeignKey(User, related_name='cancelled_bookings', on_delete=models.CASCADE)
    cancellation_reason = models.TextField()
    cancellation_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cancellation for {self.booking.room.name} by {self.cancelled_by.username}"
