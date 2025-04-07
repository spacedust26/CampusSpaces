from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Booking, BookingEquipment, UserProfile, Organization, Room, Equipment, Building, UserOrganization
from django.utils import timezone

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    phone = forms.CharField(max_length=15, required=True)
    
    ROLES = [
        ('STUDENT', 'Student'),
        ('FACULTY', 'Faculty'),
    ]
    role = forms.ChoiceField(choices=ROLES, required=True)
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        required=False,
        help_text="Select your organization"
    )
    organization_role = forms.ChoiceField(
        choices=UserOrganization.LEVELS,
        required=False,
        help_text="Your role within the organization"
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            # Create user profile
            profile = UserProfile.objects.create(
                user=user,
                role=self.cleaned_data['role'],
                phone=self.cleaned_data['phone']
            )
            
            # Add user to selected organization if provided
            organization = self.cleaned_data.get('organization')
            organization_role = self.cleaned_data.get('organization_role')
            if organization and organization_role:
                UserOrganization.objects.create(
                    user=profile,
                    organization=organization,
                    level=organization_role
                )
        
        return user

class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

class RoomFilterForm(forms.Form):
    building = forms.ModelChoiceField(
        queryset=Building.objects.all(),
        required=False,
        empty_label="All Buildings"
    )
    room_type = forms.ChoiceField(
        choices=[('', 'All Types')] + Room.ROOM_TYPES,
        required=False
    )
    min_capacity = forms.IntegerField(required=False, min_value=1)
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True
    )

class EquipmentFilterForm(forms.Form):
    building = forms.ModelChoiceField(
        queryset=Building.objects.all(),
        required=False,
        empty_label="All Buildings"
    )
    equipment_type = forms.ChoiceField(
        choices=[('', 'All Types')] + Equipment.EQUIPMENT_TYPES,
        required=False
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True
    )

class BookingForm(forms.ModelForm):
    """Form for creating room bookings"""
    
    # Add a datetime widget with min set to current date
    start_time = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={
                'type': 'datetime-local',
                'min': timezone.now().strftime('%Y-%m-%dT%H:%M'),
                'class': 'form-control',
            }
        )
    )
    
    end_time = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={
                'type': 'datetime-local',
                'min': timezone.now().strftime('%Y-%m-%dT%H:%M'),
                'class': 'form-control'
            }
        )
    )
    
    # Equipment field for selecting multiple equipment
    equipment = forms.ModelMultipleChoiceField(
        queryset=Equipment.objects.filter(status='AVAILABLE'),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )
    
    class Meta:
        model = Booking
        fields = ['title', 'description', 'start_time', 'end_time', 'organization']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'organization': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set minimum date and time for datetime fields
        min_datetime = timezone.now().strftime('%Y-%m-%dT%H:%M')
        self.fields['start_time'].widget.attrs['min'] = min_datetime
        self.fields['end_time'].widget.attrs['min'] = min_datetime
        

        
        # Only show organizations that the user belongs to
        if user:
            if hasattr(user, 'profile'):
                self.fields['organization'].queryset = user.profile.organizations.all()
                
                # If user is not in any organization, remove the field
                if not user.profile.organizations.exists():
                    self.fields['organization'].widget = forms.HiddenInput()
                    self.fields['organization'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        # Validate that start_time is in the future
        if start_time and start_time < timezone.now():
            self.add_error('start_time', 'Booking must start in the future.')
        
        # Validate that end_time is after start_time
        if start_time and end_time and end_time <= start_time:
            self.add_error('end_time', 'End time must be after start time.')
        
        # Validate that booking duration is not too long (e.g., 8 hours max)
        if start_time and end_time:
            duration = end_time - start_time
            max_duration = timezone.timedelta(hours=8)
            if duration > max_duration:
                self.add_error('end_time', 'Booking duration cannot exceed 8 hours.')
        
        return cleaned_data

class BookingApprovalForm(forms.Form):
    ACTIONS = [
        ('APPROVE', 'Approve'),
        ('REJECT', 'Reject'),
    ]
    action = forms.ChoiceField(choices=ACTIONS)
    rejected_reason = forms.CharField(
        widget=forms.Textarea,
        required=False
    )
    override_conflicts = forms.BooleanField(
        required=False,
        label="Override conflicting bookings",
        help_text="Checking this will cancel any existing bookings that conflict with this one."
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        rejected_reason = cleaned_data.get('rejected_reason')
        
        if action == 'REJECT' and not rejected_reason:
            raise forms.ValidationError("Please provide a reason for rejection.")
        
        return cleaned_data
