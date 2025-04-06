from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Booking, BookingEquipment, UserProfile, Organization, Room, Equipment, Building

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
            UserProfile.objects.create(
                user=user,
                role=self.cleaned_data['role'],
                phone=self.cleaned_data['phone']
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
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        required=False
    )
    equipment = forms.ModelMultipleChoiceField(
        queryset=Equipment.objects.filter(status='AVAILABLE'),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )
    
    class Meta:
        model = Booking
        fields = ['title', 'description', 'organization', 'start_time', 'end_time']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user and hasattr(user, 'profile'):
            # Filter organizations based on user's membership
            self.fields['organization'].queryset = user.profile.organizations.all()


    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time:
            if start_time >= end_time:
                raise forms.ValidationError("End time must be after start time.")
            
            # Check if booking duration is valid (e.g., hourly slots)
            # duration = end_time - start_time
            # if duration.total_seconds() % 3600 != 0:  # 3600 seconds = 1 hour
            #     raise forms.ValidationError("Booking must be in hourly slots.")
        
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
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        rejected_reason = cleaned_data.get('rejected_reason')
        
        if action == 'REJECT' and not rejected_reason:
            raise forms.ValidationError("Please provide a reason for rejection.")
        
        return cleaned_data
