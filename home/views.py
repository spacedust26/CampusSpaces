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
    """
    User registration page - admin only access.
    Allows administrators to create new user accounts.
    """
    # Check if user is authenticated
    if not request.user.is_authenticated:
        messages.error(request, 'You must be logged in as an admin to register new users.')
        return redirect('index')
    
    # Check if user is an admin
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'ADMIN':
        messages.error(request, 'Only administrators can register new users.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # Save the user but don't commit yet
            user = form.save(commit=False)
            
            # Get the password for sending in email
            raw_password = form.cleaned_data.get('password1')
            
            # Save the user
            user.save()
            
            # Create or update the user profile
            if hasattr(user, 'profile'):
                profile = user.profile
            else:
                profile = UserProfile(user=user)
            
            profile.role = form.cleaned_data['role']
            profile.save()
            
            # Process the selected organization IDs
            selected_org_ids = form.cleaned_data.get('organization_ids', [])
            
           
            
            if selected_org_ids:
                # Get organizations by their IDs
                for org_id in selected_org_ids:
                    try:
                        # Get the organization by ID
                        org = Organization.objects.get(id=org_id)
                        
                        # Create the UserOrganization relationship
                        user_org = UserOrganization.objects.create(
                            user=profile,
                            organization=org,
                            level=1  # Default level is 1 (Member)
                        )
                        messages.info(request, f"Created UserOrganization: {user_org.id} for {org.name}")
                    except Organization.DoesNotExist:
                        messages.warning(request, f"Organization with ID {org_id} does not exist")
                    except Exception as e:
                        messages.warning(request, f"Error adding organization {org_id}: {str(e)}")
            
            
            # Send email with login credentials
            email_subject = 'Your CampusSpaces Account Has Been Created'
            email_message = f"""
Hello {user.first_name},

An account has been created for you on CampusSpaces.

Here are your login credentials:
Email: {user.email}
Username: {user.username}
Password: {raw_password}

Please login at: {request.build_absolute_uri('/')[:-1]}

Regards,
CampusSpaces Administration
"""
            
            send_mail(
                email_subject,
                email_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            
            messages.success(request, f'User account for {user.username} created successfully. Login credentials have been sent to {user.email}.')
            return redirect('dashboard')
    else:
        form = UserRegistrationForm()
    
    # Get list of organizations for the template
    organizations = Organization.objects.all()
    
    return render(request, 'home/register.html', {
        'form': form,
        'organizations': organizations
    })

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
    if hasattr(request.user, 'profile'):
        # For faculty, show first-stage org bookings from their organizations (from students only)
        if request.user.profile.role == 'FACULTY':
            user_orgs = request.user.profile.organizations.all()
            pending_approvals = Booking.objects.filter(
                organization__in=user_orgs,
                status='PENDING'
            ).exclude(
                # Exclude bookings created by faculty members since they skip faculty approval
                user__profile__role='FACULTY'
            ).order_by('start_time')
            
        # For admin, show all bookings waiting for admin approval:
        # 1. Org bookings that passed faculty approval (FACULTY_APPROVED)
        # 3. Org bookings created by faculty (FACULTY_APPROVED, faculty self-approved)
        elif request.user.profile.role == 'ADMIN':
            pending_approvals = Booking.objects.filter(
                Q(organization__isnull=True, status='PENDING') | 
                Q(status='FACULTY_APPROVED')                      # Org bookings after faculty approval or by faculty
            ).order_by('start_time')
    
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
    
    # Check if user has a profile
    if not hasattr(request.user, 'profile'):
        messages.error(request, "Your user profile is incomplete. Please contact an administrator.")
        return redirect('view_space')
    
    # Get user's organizations
    user_organizations = request.user.profile.organizations.all()
    
    # For students, require an organization
    user_is_student = request.user.profile.role == 'STUDENT'
    if user_is_student and not user_organizations.exists():
        messages.warning(request, "As a student, you need to be part of an organization to book rooms. Please contact an administrator.")
        return redirect('view_space')
    
    if request.method == 'POST':
        form = BookingForm(request.POST, user=request.user)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user
            booking.room = room
            
            # Set initial booking status based on user role and booking type
            user_is_faculty = request.user.profile.role == 'FACULTY'
            
            # Students must book through an organization
            if user_is_student and not booking.organization:
                messages.error(request, 'As a student, you must select an organization to book a room.')
                return render(request, 'home/room_detail.html', {'room': room, 'form': form, 'user_organizations': user_organizations})
            
            # Check for conflicts before deciding approval flow
            conflicts_exist = Booking.objects.filter(
                room=room,
                status__in=['APPROVED', 'FACULTY_APPROVED'],
                start_time__lt=booking.end_time,
                end_time__gt=booking.start_time
            ).exists()
            
            if booking.organization and user_is_faculty:
                # Faculty booking for organization - skip faculty approval
                booking.status = 'FACULTY_APPROVED'
                booking.faculty_approved_by = request.user
            elif booking.organization and user_is_student and conflicts_exist:
                # Student booking with conflicts - skip faculty approval and go directly to admin
                booking.status = 'FACULTY_APPROVED'
                booking.faculty_approved_by = None  # No faculty approval happened
            else:
                # Regular flow for student organization or personal booking
                booking.status = 'PENDING'
                
            booking.save()
            
            # Add selected equipment to the booking
            equipment_list = form.cleaned_data.get('equipment')
            if equipment_list:
                for equipment in equipment_list:
                    BookingEquipment.objects.create(
                        booking=booking,
                        equipment=equipment,
                    )
            
            # Create notification for the user
            Notification.objects.create(
                user=request.user,
                title='Booking Request Submitted',
                message=f'Your booking request for {room.name} has been submitted and is pending approval.',
                notification_type='BOOKING_CREATED',
                booking=booking
            )
            
            # Create notifications based on booking type
            if booking.organization and user_is_student:
                if conflicts_exist:
                    # Notify admins directly about student booking with conflicts
                    admin_profiles = UserProfile.objects.filter(role='ADMIN')
                    
                    for profile in admin_profiles:
                        Notification.objects.create(
                            user=profile.user,
                            title='Conflicting Student Booking Request',
                            message=f'A student ({request.user.username}) has submitted a booking request for {room.name} that has scheduling conflicts and requires your immediate review.',
                            notification_type='BOOKING_FACULTY_APPROVED',  # Using this type to show in admin queue
                            booking=booking
                        )
                    
                    # Notify the student about direct admin review
                    Notification.objects.create(
                        user=request.user,
                        title='Booking Request Sent for Admin Review',
                        message=f'Your booking request for {room.name} has scheduling conflicts and has been sent directly to administrators for review, bypassing faculty approval.',
                        notification_type='BOOKING_CREATED',
                        booking=booking
                    )
                else:
                    # Regular flow - notify faculty first for non-conflicting student bookings
                    faculty_profiles = UserProfile.objects.filter(
                        role='FACULTY',
                        organizations=booking.organization
                    )
                    
                    for profile in faculty_profiles:
                        Notification.objects.create(
                            user=profile.user,
                            title='Student Organization Booking Request',
                            message=f'A student ({request.user.username}) has submitted a booking request for {room.name} for {booking.organization.name} that needs your approval first.',
                            notification_type='BOOKING_CREATED',
                            booking=booking
                        )
            else:
                # Personal booking - notify admins directly
                admin_profiles = UserProfile.objects.filter(role='ADMIN')
                
                for profile in admin_profiles:
                    Notification.objects.create(
                        user=profile.user,
                        title='Booking Request',
                        message=f'A booking request for {room.name} has been submitted by {request.user.username} and needs your approval.',
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
        'user_organizations': user_organizations,
    }
    
    return render(request, 'home/room_detail.html', context)

@login_required
def equipment_detail(request, equipment_id):
    """View details of a specific equipment"""
    equipment = get_object_or_404(Equipment, id=equipment_id, status='AVAILABLE')
    
    # Get the room associated with this equipment (if any)
    room = equipment.room
    
    context = {
        'equipment': equipment,
        'room': room,
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
    
    if booking.status in ['PENDING', 'FACULTY_APPROVED', 'APPROVED']:
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
        messages.error(request, 'You cannot cancel this booking.')
    
    return redirect('history')

@login_required
def approve_booking(request, booking_id):
    """Approve or reject a booking request"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Only process pending or faculty_approved bookings
    if booking.status not in ['PENDING', 'FACULTY_APPROVED']:
        messages.error(request, 'This booking is not awaiting approval.')
        return redirect('dashboard')
    
    # Check if user has permission to approve
    user_profile = request.user.profile
    has_permission = False
    
    # Determine appropriate permissions based on booking type and status
    if booking.organization:
        # Organization booking
        if booking.status == 'PENDING' and user_profile.role == 'FACULTY':
            # Faculty can approve first stage of student org bookings if they're in the same org
            faculty_orgs = user_profile.organizations.all()
            has_permission = booking.organization in faculty_orgs
        elif booking.status == 'FACULTY_APPROVED' and user_profile.role == 'ADMIN':
            # Admin can approve second stage (after faculty or faculty self-approval)
            has_permission = True
    else:
        # Personal booking - only admin can approve
        has_permission = user_profile.role == 'ADMIN'
    
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
                
                # Debug information
                if conflicting_bookings.exists():
                    messages.info(request, f"Found {conflicting_bookings.count()} conflicting bookings.")
                
                # Handle conflicts if they exist
                if conflicting_bookings.exists():
                    # If admin is approving, they can override conflicts
                    if user_profile.role == 'ADMIN':
                        override_conflicts = form.cleaned_data.get('override_conflicts', False)
                        
                        if not override_conflicts:
                            messages.error(request, 'There are conflicting bookings. Please use the override option to proceed or reject this booking.')
                            return redirect('booking_approval_detail', booking_id=booking.id)
                        
                        # Cancel all conflicting bookings and notify their owners
                        for conflicting_booking in conflicting_bookings:
                            # Change status to cancelled
                            conflicting_booking.status = 'CANCELLED'
                            conflicting_booking.rejected_reason = f"Automatically cancelled due to priority override by admin for {booking.title}"
                            conflicting_booking.save()
                            
                            # Create notification for the affected user
                            Notification.objects.create(
                                user=conflicting_booking.user,
                                title='Booking Cancelled Due to Override',
                                message=f'Your booking "{conflicting_booking.title}" for {conflicting_booking.room.name} on {conflicting_booking.start_time.strftime("%Y-%m-%d %H:%M")} has been cancelled due to a priority booking that required the same space. Please contact administration for more information.',
                                notification_type='BOOKING_CANCELLED',
                                booking=conflicting_booking
                            )
                            
                            # Email notification
                            email_subject = f'Important: Your Booking Has Been Cancelled'
                            email_message = f'''
                            Dear {conflicting_booking.user.get_full_name() or conflicting_booking.user.username},
                            
                            We regret to inform you that your booking "{conflicting_booking.title}" for {conflicting_booking.room.name} on {conflicting_booking.start_time.strftime("%Y-%m-%d %H:%M")} has been cancelled.
                            
                            This cancellation occurred because an administrator has approved a higher priority booking that required the same space.
                            
                            You can book another space or time through the CampusSpaces system.
                            
                            If you have any questions, please contact the administration office.
                            
                            Regards,
                            CampusSpaces System
                            '''
                            
                            send_mail(email_subject, email_message, settings.DEFAULT_FROM_EMAIL, [conflicting_booking.user.email])
                        
                        messages.success(request, f'Conflicts resolved: {conflicting_bookings.count()} conflicting booking(s) were cancelled.')
                    
                    elif user_profile.role == 'FACULTY':
                        # Faculty handling conflicts for organization bookings - check org level
                        booking_org_level = UserOrganization.objects.filter(
                            user__user=booking.user,
                            organization=booking.organization
                        ).first()
                        
                        if booking_org_level and booking_org_level.level >= 2:  # Representative or higher
                            # Allow faculty to handle conflicts for high-level organization members
                            override_conflicts = form.cleaned_data.get('override_conflicts', False)
                            
                            if not override_conflicts:
                                messages.error(request, 'There are conflicting bookings. Please use the override option to proceed or reject this booking.')
                                return redirect('booking_approval_detail', booking_id=booking.id)
                            
                            # Cancel all conflicting bookings
                            for conflicting_booking in conflicting_bookings:
                                # Skip bookings by admin
                                conflicting_user_profile = getattr(conflicting_booking.user, 'profile', None)
                                if (conflicting_user_profile and conflicting_user_profile.role == 'ADMIN'):
                                    messages.error(request, f'Cannot override booking by administrator: {conflicting_booking.title}')
                                    return redirect('booking_approval_detail', booking_id=booking.id)
                                
                                # Change status to cancelled
                                conflicting_booking.status = 'CANCELLED'
                                conflicting_booking.rejected_reason = f"Automatically cancelled due to priority override for organization {booking.organization.name}"
                                conflicting_booking.save()
                                
                                # Create notification for the affected user
                                Notification.objects.create(
                                    user=conflicting_booking.user,
                                    title='Booking Cancelled Due to Organization Priority',
                                    message=f'Your booking "{conflicting_booking.title}" for {conflicting_booking.room.name} on {conflicting_booking.start_time.strftime("%Y-%m-%d %H:%M")} has been cancelled due to a priority organization booking. Please contact the faculty for more information.',
                                    notification_type='BOOKING_CANCELLED',
                                    booking=conflicting_booking
                                )
                                email_subject = f'Important: Your Booking Has Been Cancelled'
                                email_message = f'''
                                Dear {conflicting_booking.user.get_full_name() or conflicting_booking.user.username},
                                Your booking "{conflicting_booking.title}" for {conflicting_booking.room.name} on {conflicting_booking.start_time.strftime("%Y-%m-%d %H:%M")} has been cancelled.
                                This cancellation occurred because a higher priority organization booking required the same space.
                                You can book another space or time through the CampusSpaces system.
                                If you have any questions, please contact the faculty.
                                Regards,
                                CampusSpaces System
                                '''
                                # Uncomment this in production
                                send_mail(email_subject, email_message, settings.DEFAULT_FROM_EMAIL, [conflicting_booking.user.email])
                            
                            messages.success(request, f'Conflicts resolved: {conflicting_bookings.count()} conflicting booking(s) were cancelled.')
                        else:
                            messages.error(request, 'There are booking conflicts that could not be resolved automatically. This booking cannot be approved.')
                            return redirect('booking_approval_detail', booking_id=booking.id)
                    else:
                        messages.error(request, 'You do not have permission to override conflicting bookings.')
                        return redirect('dashboard')
                
                # After handling any conflicts, process the approval based on booking type and user role
                if booking.organization and booking.status == 'PENDING' and user_profile.role == 'FACULTY':
                    # Faculty approving student's organization booking
                    booking.status = 'FACULTY_APPROVED'
                    booking.faculty_approved_by = request.user
                    booking.save()
                    
                    # Notify the user
                    Notification.objects.create(
                        user=booking.user,
                        title='Booking Approved by Faculty',
                        message=f'Your booking request for {booking.room.name} has been approved by faculty and is now awaiting final admin approval.',
                        notification_type='BOOKING_FACULTY_APPROVED',
                        booking=booking
                    )
                    
                    # Notify admins for final approval
                    admin_profiles = UserProfile.objects.filter(role='ADMIN')
                    for profile in admin_profiles:
                        Notification.objects.create(
                            user=profile.user,
                            title='Booking Needs Final Approval',
                            message=f'A booking request for {booking.room.name} by {booking.user.username} for {booking.organization.name} has been approved by faculty and needs your final approval.',
                            notification_type='BOOKING_FACULTY_APPROVED',
                            booking=booking
                        )
                    
                    messages.success(request, 'Organization booking approved by faculty. It now needs admin approval.')
                
                else:
                    # Final approval (admin approving any booking, or faculty skipping first stage)
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
                    
                    send_mail(
                        subject=f'Booking Request Approved: {booking.title}',
                        message=f'''
                            Dear {booking.user.get_full_name() or booking.user.username},

                            Your booking request "{booking.title}" for {booking.room.name} on {booking.start_time.strftime("%Y-%m-%d")} from {booking.start_time.strftime("%H:%M")} to {booking.end_time.strftime("%H:%M")} has been approved.

                            Room: {booking.room.name} ({booking.room.building.name})
                            Date: {booking.start_time.strftime("%Y-%m-%d")}
                            Time: {booking.start_time.strftime("%H:%M")} - {booking.end_time.strftime("%H:%M")}
                            {f"Organization: {booking.organization.name}" if booking.organization else ""}

                            Please ensure you comply with all room usage policies.The room booking can be overriden if a higher priority event needs the room.
                            The room will be ready for your use at the scheduled time.

                            Regards,
                            CampusSpaces System
''',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[booking.user.email],
                        fail_silently=True,
                    )
                    
                    # Notify HR personnel responsible for the room if applicable
                    if booking.room.hr_responsible:
                        # Email notification
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
                        
                        send_mail(
                            subject=email_subject,
                            message=email_message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[hr_email],
                            fail_silently=True,
                        )
                    
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
    
    # Check if this was a student booking that skipped faculty approval due to conflicts
    skipped_faculty_approval = booking.status == 'FACULTY_APPROVED' and booking.faculty_approved_by is None
    
    context = {
        'booking': booking,
        'booking_equipment': booking_equipment,
        'conflicting_bookings': conflicting_bookings,
        'form': BookingApprovalForm(),
        'skipped_faculty_approval': skipped_faculty_approval,
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