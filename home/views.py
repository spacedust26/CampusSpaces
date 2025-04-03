from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse

from .models import (
    Organization, UserProfile, UserOrganization, Building,
    HRPersonnel, Room, Equipment, Booking, BookingEquipment, Notification
)
from .forms import (
    UserRegistrationForm, LoginForm, RoomFilterForm, EquipmentFilterForm,
    BookingForm, BookingApprovalForm
)

def index(request):
    """Landing page with login form"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(email=email, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm()
    
    return render(request, 'home/index.html', {'form': form})

def register(request):
    """User registration page"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registration successful! You can now log in.')
            return redirect('index')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'home/register.html', {'form': form})

@login_required
def user_logout(request):
    """Log out the user"""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('index')

@login_required
def dashboard(request):
    """User dashboard showing upcoming bookings and notifications"""
    # Get user's upcoming bookings
    upcoming_bookings = Booking.objects.filter(
        user=request.user,
        end_time__gte=timezone.now(),
        status='APPROVED'
    ).order_by('start_time')[:5]
    
    # Get pending bookings that need approval (for faculty and admin)
    pending_approvals = []
    if hasattr(request.user, 'profile') and request.user.profile.role in ['FACULTY', 'ADMIN']:
        # For faculty, show bookings from their organizations
        if request.user.profile.role == 'FACULTY':
            user_orgs = request.user.profile.organizations.all()
            pending_approvals = Booking.objects.filter(
                organization__in=user_orgs,
                status='PENDING'
            ).order_by('start_time')
        # For admin, show all pending bookings
        elif request.user.profile.role == 'ADMIN':
            pending_approvals = Booking.objects.filter(status='PENDING').order_by('start_time')
    
    # Get recent notifications
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    context = {
        'upcoming_bookings': upcoming_bookings,
        'pending_approvals': pending_approvals,
        'notifications': notifications,
    }
    
    return render(request, 'home/dashboard.html', context)

@login_required
def view_space(request):
    """View and filter available rooms"""
    form = RoomFilterForm(request.GET or None)
    rooms = Room.objects.filter(status='AVAILABLE')
    
    if form.is_valid():
        building = form.cleaned_data.get('building')
        room_type = form.cleaned_data.get('room_type')
        min_capacity = form.cleaned_data.get('min_capacity')
        date = form.cleaned_data.get('date')
        
        if building:
            rooms = rooms.filter(building=building)
        
        if room_type:
            rooms = rooms.filter(room_type=room_type)
        
        if min_capacity:
            rooms = rooms.filter(capacity__gte=min_capacity)
        
        # Filter out rooms with approved bookings on the selected date
        if date:
            # Convert date to datetime range for the whole day
            start_of_day = timezone.make_aware(timezone.datetime.combine(date, timezone.datetime.min.time()))
            end_of_day = timezone.make_aware(timezone.datetime.combine(date, timezone.datetime.max.time()))
            
            # Get rooms with approved bookings on this date
            booked_rooms = Booking.objects.filter(
                status='APPROVED',
                start_time__lt=end_of_day,
                end_time__gt=start_of_day
            ).values_list('room_id', flat=True)
            
            # Exclude these rooms
            rooms = rooms.exclude(id__in=booked_rooms)
    
    context = {
        'form': form,
        'rooms': rooms,
    }
    
    return render(request, 'home/view_space.html', context)

@login_required
def view_equipment(request):
    """View and filter available equipment"""
    form = EquipmentFilterForm(request.GET or None)
    equipment = Equipment.objects.filter(status='AVAILABLE')
    
    if form.is_valid():
        building = form.cleaned_data.get('building')
        equipment_type = form.cleaned_data.get('equipment_type')
        date = form.cleaned_data.get('date')
        
        if building:
            equipment = equipment.filter(building=building)
        
        if equipment_type:
            equipment = equipment.filter(equipment_type=equipment_type)
        
        # Filter out equipment with approved bookings on the selected date
        if date:
            # Convert date to datetime range for the whole day
            start_of_day = timezone.make_aware(timezone.datetime.combine(date, timezone.datetime.min.time()))
            end_of_day = timezone.make_aware(timezone.datetime.combine(date, timezone.datetime.max.time()))
            
            # Get equipment with approved bookings on this date
            booked_equipment = BookingEquipment.objects.filter(
                booking__status='APPROVED',
                booking__start_time__lt=end_of_day,
                booking__end_time__gt=start_of_day
            ).values_list('equipment_id', flat=True)
            
            # Exclude these equipment
            equipment = equipment.exclude(id__in=booked_equipment)
    
    context = {
        'form': form,
        'equipment': equipment,
    }
    
    return render(request, 'home/view_equipment.html', context)

@login_required
def room_detail(request, room_id):
    """View details of a specific room and book it"""
    room = get_object_or_404(Room, id=room_id, status='AVAILABLE')
    
    if request.method == 'POST':
        form = BookingForm(request.POST, user=request.user)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user
            booking.room = room
            booking.status = 'PENDING'
            booking.save()
            
            # Add selected equipment to the booking
            equipment_list = form.cleaned_data.get('equipment')
            if equipment_list:
                for equipment in equipment_list:
                    BookingEquipment.objects.create(
                        booking=booking,
                        equipment=equipment,
                        quantity=1  # Default quantity
                    )
            
            # Create notification for the user
            Notification.objects.create(
                user=request.user,
                title='Booking Request Submitted',
                message=f'Your booking request for {room.name} has been submitted and is pending approval.',
                notification_type='BOOKING_CREATED',
                booking=booking
            )
            
            # If the booking has an organization, notify faculty members
            if booking.organization:
                # Get faculty members of the organization
                faculty_profiles = UserProfile.objects.filter(
                    role='FACULTY',
                    organizations=booking.organization
                )
                
                for profile in faculty_profiles:
                    Notification.objects.create(
                        user=profile.user,
                        title='New Booking Request',
                        message=f'A new booking request for {room.name} has been submitted by {request.user.username} and needs your approval.',
                        notification_type='BOOKING_CREATED',
                        booking=booking
                    )
            
            messages.success(request, 'Booking request submitted successfully!')
            return redirect('dashboard')
    else:
        form = BookingForm(user=request.user)
    
    # Get available time slots for the room
    approved_bookings = Booking.objects.filter(
        room=room,
        status='APPROVED',
        end_time__gte=timezone.now()
    ).order_by('start_time')
    
    context = {
        'room': room,
        'form': form,
        'approved_bookings': approved_bookings,
    }
    
    return render(request, 'home/room_detail.html', context)

@login_required
def equipment_detail(request, equipment_id):
    """View details of a specific equipment"""
    equipment = get_object_or_404(Equipment, id=equipment_id, status='AVAILABLE')
    
    # Get rooms that have this equipment
    rooms_with_equipment = equipment.rooms.all()
    
    context = {
        'equipment': equipment,
        'rooms_with_equipment': rooms_with_equipment,
    }
    
    return render(request, 'home/equipment_detail.html', context)

@login_required
def booking_cart(request):
    """View and manage pending booking requests"""
    pending_bookings = Booking.objects.filter(
        user=request.user,
        status='PENDING'
    ).order_by('start_time')
    
    context = {
        'pending_bookings': pending_bookings,
    }
    
    return render(request, 'home/booking_cart.html', context)

@login_required
def history(request):
    """View booking history"""
    # Get all bookings for the user
    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'bookings': bookings,
    }
    
    return render(request, 'home/history.html', context)

@login_required
def cancel_booking(request, booking_id):
    """Cancel a booking"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    if booking.status in ['PENDING', 'APPROVED']:
        booking.status = 'CANCELLED'
        booking.save()
        
        # Create notification for the user
        Notification.objects.create(
            user=request.user,
            title='Booking Cancelled',
            message=f'Your booking for {booking.room.name} has been cancelled.',
            notification_type='BOOKING_CANCELLED',
            booking=booking
        )
        
        messages.success(request, 'Booking cancelled successfully!')
    else:
        messages.error(request, 'This booking cannot be cancelled.')
    
    return redirect('history')

@login_required
def approve_booking(request, booking_id):
    """Approve or reject a booking request"""
    booking = get_object_or_404(Booking, id=booking_id, status='PENDING')
    
    # Check if user has permission to approve (faculty for their org or admin)
    user_profile = request.user.profile
    has_permission = False
    
    if user_profile.role == 'ADMIN':
        has_permission = True
    elif user_profile.role == 'FACULTY' and booking.organization:
        # Check if faculty is part of the organization
        faculty_orgs = user_profile.organizations.all()
        has_permission = booking.organization in faculty_orgs
    
    if not has_permission:
        messages.error(request, 'You do not have permission to approve this booking.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = BookingApprovalForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            
            if action == 'APPROVE':
                # Check for conflicts
                conflicting_bookings = Booking.objects.filter(
                    room=booking.room,
                    status='APPROVED',
                    start_time__lt=booking.end_time,
                    end_time__gt=booking.start_time
                ).exclude(id=booking.id)
                
                if conflicting_bookings.exists():
                    # Handle conflict based on seniority
                    conflict_resolved = False
                    
                    # If admin is approving, they can override conflicts
                    if user_profile.role == 'ADMIN':
                        conflict_resolved = True
                    else:
                        # Check organization level/seniority
                        # This is a simplified version - in a real system, you'd have more complex logic
                        booking_org_level = UserOrganization.objects.filter(
                            user__user=booking.user,
                            organization=booking.organization
                        ).first()
                        
                        if booking_org_level and booking_org_level.level >= 2:  # Representative or higher
                            conflict_resolved = True
                    
                    if not conflict_resolved:
                        messages.error(request, 'There is a booking conflict that could not be resolved automatically.')
                        return redirect('booking_approval_detail', booking_id=booking.id)
                
                # Approve the booking
                booking.status = 'APPROVED'
                booking.approved_by = request.user
                booking.save()
                
                # Notify the user
                Notification.objects.create(
                    user=booking.user,
                    title='Booking Approved',
                    message=f'Your booking request for {booking.room.name} has been approved.',
                    notification_type='BOOKING_APPROVED',
                    booking=booking
                )
                
                # Notify HR personnel responsible for the room
                if booking.room.hr_responsible:
                    # In a real system, you'd send an email here
                    # For now, we'll just create a notification
                    hr_email = booking.room.hr_responsible.email
                    hr_name = booking.room.hr_responsible.name
                    email_subject = f'Room Booking Notification: {booking.room.name}'
                    email_message = f'''
                    Dear {hr_name},
                    
                    This is to inform you that room {booking.room.name} has been booked for the following period:
                    
                    Event: {booking.title}
                    Date: {booking.start_time.strftime('%Y-%m-%d')}
                    Time: {booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}
                    Booked by: {booking.user.get_full_name() or booking.user.username}
                    
                    Please ensure the room is prepared accordingly.
                    
                    Regards,
                    CampusSpaces System
                    '''
                    
                    # In a production environment, uncomment this to send actual emails
                    # send_mail(email_subject, email_message, settings.DEFAULT_FROM_EMAIL, [hr_email])
                
                messages.success(request, 'Booking approved successfully!')
            
            elif action == 'REJECT':
                booking.status = 'REJECTED'
                booking.rejected_reason = form.cleaned_data['rejected_reason']
                booking.save()
                
                # Notify the user
                Notification.objects.create(
                    user=booking.user,
                    title='Booking Rejected',
                    message=f'Your booking request for {booking.room.name} has been rejected. Reason: {booking.rejected_reason}',
                    notification_type='BOOKING_REJECTED',
                    booking=booking
                )
                
                messages.success(request, 'Booking rejected successfully!')
            
            return redirect('dashboard')
    else:
        form = BookingApprovalForm()
    
    context = {
        'booking': booking,
        'form': form,
    }
    
    return render(request, 'home/booking_approval.html', context)

@login_required
def booking_approval_detail(request, booking_id):
    """View details of a booking that needs approval"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Get equipment associated with this booking
    booking_equipment = BookingEquipment.objects.filter(booking=booking)
    
    # Check for conflicts
    conflicting_bookings = Booking.objects.filter(
        room=booking.room,
        status='APPROVED',
        start_time__lt=booking.end_time,
        end_time__gt=booking.start_time
    ).exclude(id=booking.id)
    
    context = {
        'booking': booking,
        'booking_equipment': booking_equipment,
        'conflicting_bookings': conflicting_bookings,
        'form': BookingApprovalForm(),
    }
    
    return render(request, 'home/booking_approval_detail.html', context)

@login_required
def notifications(request):
    """View all notifications"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Mark all as read
    unread_notifications = notifications.filter(read=False)
    unread_notifications.update(read=True)
    
    context = {
        'notifications': notifications,
    }
    
    return render(request, 'home/notifications.html', context)

@login_required
def mark_notification_read(request, notification_id):
    """Mark a notification as read via AJAX"""
    if request.method == 'POST' and request.is_ajax():
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.read = True
        notification.save()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})