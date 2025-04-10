from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Organization, Room, Equipment, Booking, Building

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    role = forms.ChoiceField(choices=[
        ('STUDENT', 'Student'),
        ('FACULTY', 'Faculty'),
        ('ADMIN', 'Administrator')
    ])
    
    # Use a hidden field to store the selected organization IDs as a comma-separated string
    selected_organizations = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'role', 'selected_organizations']
    
    def __init__(self, *args, **kwargs):
        super(UserRegistrationForm, self).__init__(*args, **kwargs)
        
        # Add classes for better styling
        for field_name, field in self.fields.items():
            if field_name != 'selected_organizations':
                field.widget.attrs.update({'class': 'form-control'})

    def clean(self):
        cleaned_data = super().clean()
        # Convert the comma-separated string to a list of organization IDs
        selected_orgs = cleaned_data.get('selected_organizations', '')
        
        if selected_orgs:
            org_ids = [int(org_id) for org_id in selected_orgs.split(',') if org_id.strip()]
            cleaned_data['organization_ids'] = org_ids
        else:
            cleaned_data['organization_ids'] = []
            
        return cleaned_data

class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

class RoomFilterForm(forms.Form):
    building = forms.ModelChoiceField(queryset=None, required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    room_type = forms.ChoiceField(choices=[('', '----')] + Room.ROOM_TYPES, required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    min_capacity = forms.IntegerField(min_value=1, required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    
    def __init__(self, *args, **kwargs):
        super(RoomFilterForm, self).__init__(*args, **kwargs)
        self.fields['building'].queryset = Building.objects.all()

class EquipmentFilterForm(forms.Form):
    building = forms.ModelChoiceField(queryset=None, required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    equipment_type = forms.ChoiceField(choices=[('', '----')] + Equipment.EQUIPMENT_TYPES, required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    
    def __init__(self, *args, **kwargs):
        super(EquipmentFilterForm, self).__init__(*args, **kwargs)
        self.fields['building'].queryset = Building.objects.all()

class BookingForm(forms.ModelForm):
    equipment = forms.ModelMultipleChoiceField(queryset=None, required=False, widget=forms.CheckboxSelectMultiple())
    
    class Meta:
        model = Booking
        fields = ['title', 'description', 'organization', 'start_time', 'end_time', 'equipment']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'organization': forms.Select(attrs={'class': 'form-control'}),
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(BookingForm, self).__init__(*args, **kwargs)
        
        # Set the equipment queryset to available equipment
        self.fields['equipment'].queryset = Equipment.objects.filter(status='AVAILABLE')
        
        # Limit organization choices to the user's organizations if they're a student or faculty
        if user and hasattr(user, 'profile'):
            if user.profile.role in ['STUDENT', 'FACULTY']:
                self.fields['organization'].queryset = user.profile.organizations.all()
            elif user.profile.role == 'ADMIN':
                # Admins can book on behalf of any organization
                self.fields['organization'].queryset = Organization.objects.all()

class BookingApprovalForm(forms.Form):
    action = forms.ChoiceField(
        choices=[
            ('APPROVE', 'Approve Booking'),
            ('REJECT', 'Reject Booking')
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    rejected_reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        help_text="Required if rejecting the booking"
    )
    override_conflicts = forms.BooleanField(
        required=False, 
        initial=False,
        label="Override conflicting bookings",
        help_text="Check this to cancel conflicting bookings and approve this one instead",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        rejected_reason = cleaned_data.get('rejected_reason')
        
        if action == 'REJECT' and not rejected_reason:
            raise forms.ValidationError("You must provide a reason for rejecting the booking.")
        
        return cleaned_data
