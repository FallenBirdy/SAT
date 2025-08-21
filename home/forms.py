"""Forms module for gym tracker application.

This module contains all form classes with centralized validation logic
using Django validators and custom validation methods. All numeric fields
are validated for existence, type, and range using constants.
"""

from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import (
    MinValueValidator, MaxValueValidator, MinLengthValidator, MaxLengthValidator
)
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from .models import Profile, Weight, Journal, ScheduledWorkout, PersonalBest, RestTimer
from .constants import (
    MIN_BODY_WEIGHT_KG, MAX_BODY_WEIGHT_KG, MIN_HEIGHT_CM, MAX_HEIGHT_CM,
    MIN_AGE, MAX_AGE, BMI_MIN, BMI_MAX, MIN_REST_SECONDS, MAX_REST_SECONDS,
    MAX_EXERCISE_NAME_LENGTH, MAX_NOTES_LENGTH, MAX_TITLE_LENGTH,
    MIN_SETS, MAX_SETS, MIN_REPS, MAX_REPS, MAX_WEIGHT_KG, MIN_WEIGHT_KG,
    WORKOUT_STATUS_PLANNED, WORKOUT_STATUS_COMPLETED, WORKOUT_STATUS_MISSED,
    CATEGORY_STRENGTH, CATEGORY_CARDIO, CATEGORY_FLEXIBILITY, CATEGORY_OTHER
)
import re

class RegisterForm(forms.ModelForm):
    """Form for user registration with comprehensive validation.
    
    This form handles user account creation and profile setup with
    centralized validation for all input fields including existence,
    type, and range checks.
    
    Attributes:
        username (CharField): Username with length validation.
        email (EmailField): Optional email address.
        first_name (CharField): User's first name.
        last_name (CharField): User's last name.
        password1 (CharField): Password with strength requirements.
        password2 (CharField): Password confirmation field.
        dob (DateField): Date of birth with age validation.
    """
    username = forms.CharField(
        max_length=150,
        validators=[MinLengthValidator(3)],
        help_text="Username must be 3-150 characters long"
    )
    email = forms.EmailField(
        required=False,
        help_text="Optional email address for account recovery"
    )
    first_name = forms.CharField(
        max_length=30,
        validators=[MinLengthValidator(1)],
        help_text="Your first name"
    )
    last_name = forms.CharField(
        max_length=30,
        validators=[MinLengthValidator(1)],
        help_text="Your last name"
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput,
        validators=[MinLengthValidator(8)],
        label="Password",
        help_text="Password must be at least 8 characters long"
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirm Password",
        help_text="Re-enter your password for confirmation"
    )
    dob = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text="Your date of birth for age-based recommendations"
    )

    class Meta:
        model = Profile
        fields = ['dob']

    def clean_username(self):
        """Validate username for uniqueness and format.
        
        Returns:
            str: Cleaned username.
            
        Raises:
            ValidationError: If username is invalid or already exists.
        """
        username = self.cleaned_data.get('username')
        if not username:
            raise ValidationError("Username is required.")
            
        # Check for alphanumeric characters and underscores only
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError("Username can only contain letters, numbers, and underscores.")
            
        # Check uniqueness
        if User.objects.filter(username=username).exists():
            raise ValidationError("This username is already taken.")
            
        return username

    def clean_dob(self):
        """Validate date of birth for age requirements.
        
        Returns:
            date: Cleaned date of birth.
            
        Raises:
            ValidationError: If age is outside valid range.
        """
        dob = self.cleaned_data.get('dob')
        if not dob:
            raise ValidationError("Date of birth is required.")
            
        # Calculate age
        today = date.today()
        age = today.year - dob.year
        if today.month < dob.month or (today.month == dob.month and today.day < dob.day):
            age -= 1
            
        # Validate age range using constants
        if age < MIN_AGE:
            raise ValidationError(f"You must be at least {MIN_AGE} years old to register.")
        if age > MAX_AGE:
            raise ValidationError(f"Age cannot exceed {MAX_AGE} years.")
            
        # Check for future dates
        if dob > today:
            raise ValidationError("Date of birth cannot be in the future.")
            
        return dob

    def clean_password1(self):
        """Validate password strength.
        
        Returns:
            str: Cleaned password.
            
        Raises:
            ValidationError: If password doesn't meet requirements.
        """
        password = self.cleaned_data.get('password1')
        if not password:
            raise ValidationError("Password is required.")
            
        # Check for at least one digit and one letter
        if not re.search(r'[0-9]', password):
            raise ValidationError("Password must contain at least one digit.")
        if not re.search(r'[a-zA-Z]', password):
            raise ValidationError("Password must contain at least one letter.")
            
        return password

    def clean(self):
        """Validate form data and check password confirmation.
        
        Returns:
            dict: Cleaned form data.
            
        Raises:
            ValidationError: If passwords don't match.
        """
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            self.add_error('password2', "Passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        """Save user and profile with validated data.
        
        Args:
            commit (bool): Whether to save to database immediately.
            
        Returns:
            Profile: Created user profile instance.
        """
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data.get('email', ''),
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            password=self.cleaned_data['password1']
        )

        profile, created = Profile.objects.get_or_create(
            user=user,
            defaults={'dob': self.cleaned_data['dob']}
        )

        return profile


class WeightForm(forms.ModelForm):
    """Form for recording weight measurements with validation.
    
    This form handles weight entry with comprehensive validation
    for existence, type, and range checks using constants.
    
    Attributes:
        weight (DecimalField): Weight value with range validation.
        date (DateField): Date of measurement with validation.
        notes (CharField): Optional notes about the measurement.
    """
    
    class Meta:
        model = Weight
        fields = ['weight', 'date', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3})
        }
    
    def __init__(self, *args, **kwargs):
        """Initialize form with field validators.
        
        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)
        self.fields['weight'].validators = [
            MinValueValidator(MIN_BODY_WEIGHT_KG, f"Weight must be at least {MIN_BODY_WEIGHT_KG} kg"),
            MaxValueValidator(MAX_BODY_WEIGHT_KG, f"Weight cannot exceed {MAX_BODY_WEIGHT_KG} kg")
        ]
        self.fields['weight'].help_text = f"Enter weight in kilograms ({MIN_BODY_WEIGHT_KG}-{MAX_BODY_WEIGHT_KG} kg)"
        self.fields['notes'].validators = [MaxLengthValidator(MAX_NOTES_LENGTH)]
    
    def clean_weight(self):
        """Validate weight input for existence, type, and range.
        
        Returns:
            Decimal: Cleaned weight value.
            
        Raises:
            ValidationError: If weight is invalid.
        """
        weight = self.cleaned_data.get('weight')
        if weight is None:
            raise ValidationError("Weight is required.")
            
        try:
            weight_decimal = Decimal(str(weight))
        except (InvalidOperation, ValueError):
            raise ValidationError("Weight must be a valid number.")
            
        if weight_decimal <= 0:
            raise ValidationError("Weight must be a positive number.")
            
        return weight_decimal
    
    def clean_date(self):
        """Validate measurement date.
        
        Returns:
            date: Cleaned date value.
            
        Raises:
            ValidationError: If date is invalid.
        """
        measurement_date = self.cleaned_data.get('date')
        if not measurement_date:
            raise ValidationError("Measurement date is required.")
            
        if measurement_date > date.today():
            raise ValidationError("Measurement date cannot be in the future.")
            
        # Check if date is too far in the past (more than 10 years)
        ten_years_ago = date.today() - timedelta(days=3650)
        if measurement_date < ten_years_ago:
            raise ValidationError("Measurement date cannot be more than 10 years ago.")
            
        return measurement_date


class JournalForm(forms.ModelForm):
    """Form for creating journal entries with validation.
    
    This form handles journal entry creation with validation
    for title length, content requirements, and date validation.
    
    Attributes:
        title (CharField): Journal entry title with length validation.
        content (CharField): Journal entry content with requirements.
        date (DateField): Entry date with validation.
        mood (CharField): Optional mood indicator.
    """
    
    class Meta:
        model = Journal
        fields = ['title', 'content', 'date', 'mood']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'content': forms.Textarea(attrs={'rows': 6}),
            'mood': forms.TextInput(attrs={'placeholder': 'e.g., motivated, tired, energetic'})
        }
    
    def __init__(self, *args, **kwargs):
        """Initialize form with field validators.
        
        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)
        self.fields['title'].validators = [
            MinLengthValidator(3, "Title must be at least 3 characters long"),
            MaxLengthValidator(MAX_TITLE_LENGTH, f"Title cannot exceed {MAX_TITLE_LENGTH} characters")
        ]
        self.fields['content'].validators = [
            MinLengthValidator(10, "Content must be at least 10 characters long")
        ]
        self.fields['title'].help_text = f"Brief title for your journal entry (3-{MAX_TITLE_LENGTH} characters)"
        self.fields['content'].help_text = "Share your thoughts, progress, goals, or reflections"
    
    def clean_title(self):
        """Validate journal title.
        
        Returns:
            str: Cleaned title.
            
        Raises:
            ValidationError: If title is invalid.
        """
        title = self.cleaned_data.get('title')
        if not title:
            raise ValidationError("Title is required.")
            
        title = title.strip()
        if not title:
            raise ValidationError("Title cannot be empty or only whitespace.")
            
        return title
    
    def clean_content(self):
        """Validate journal content.
        
        Returns:
            str: Cleaned content.
            
        Raises:
            ValidationError: If content is invalid.
        """
        content = self.cleaned_data.get('content')
        if not content:
            raise ValidationError("Content is required.")
            
        content = content.strip()
        if not content:
            raise ValidationError("Content cannot be empty or only whitespace.")
            
        return content


class RestTimerForm(forms.ModelForm):
    """Form for creating rest timers with validation.
    
    This form handles rest timer creation with validation
    for name uniqueness, duration range, and boolean flags.
    
    Attributes:
        name (CharField): Timer name with length validation.
        duration (IntegerField): Duration in seconds with range validation.
        is_default (BooleanField): Default timer flag.
    """
    
    class Meta:
        model = RestTimer
        fields = ['name', 'duration', 'is_default']
        widgets = {
            'duration': forms.NumberInput(attrs={'min': MIN_REST_SECONDS, 'max': MAX_REST_SECONDS})
        }
    
    def __init__(self, *args, **kwargs):
        """Initialize form with field validators.
        
        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        self.fields['name'].validators = [
            MinLengthValidator(2, "Timer name must be at least 2 characters long"),
            MaxLengthValidator(MAX_EXERCISE_NAME_LENGTH, f"Timer name cannot exceed {MAX_EXERCISE_NAME_LENGTH} characters")
        ]
        self.fields['duration'].validators = [
            MinValueValidator(MIN_REST_SECONDS, f"Duration must be at least {MIN_REST_SECONDS} seconds"),
            MaxValueValidator(MAX_REST_SECONDS, f"Duration cannot exceed {MAX_REST_SECONDS} seconds")
        ]
        self.fields['name'].help_text = "Name for your rest timer"
        self.fields['duration'].help_text = f"Rest duration in seconds ({MIN_REST_SECONDS}-{MAX_REST_SECONDS})"
        self.fields['is_default'].help_text = "Set as your default rest timer"
    
    def clean_name(self):
        """Validate timer name for uniqueness.
        
        Returns:
            str: Cleaned timer name.
            
        Raises:
            ValidationError: If name is invalid or already exists.
        """
        name = self.cleaned_data.get('name')
        if not name:
            raise ValidationError("Timer name is required.")
            
        name = name.strip()
        if not name:
            raise ValidationError("Timer name cannot be empty or only whitespace.")
            
        # Check uniqueness for the user
        if self.user:
            existing_timer = RestTimer.objects.filter(user=self.user, name=name)
            if self.instance.pk:
                existing_timer = existing_timer.exclude(pk=self.instance.pk)
            if existing_timer.exists():
                raise ValidationError("You already have a timer with this name.")
                
        return name
    
    def clean_duration(self):
        """Validate timer duration.
        
        Returns:
            int: Cleaned duration value.
            
        Raises:
            ValidationError: If duration is invalid.
        """
        duration = self.cleaned_data.get('duration')
        if duration is None:
            raise ValidationError("Duration is required.")
            
        try:
            duration_int = int(duration)
        except (ValueError, TypeError):
            raise ValidationError("Duration must be a valid number.")
            
        if duration_int <= 0:
            raise ValidationError("Duration must be a positive number.")
            
        return duration_int


class PersonalBestForm(forms.ModelForm):
    """Form for recording personal bests with validation.
    
    This form handles personal best entry with validation
    for exercise names, values, units, and categories.
    
    Attributes:
        exercise (CharField): Exercise name with validation.
        category (ChoiceField): Exercise category selection.
        value (DecimalField): Achievement value with validation.
        unit (CharField): Unit of measurement.
        date_achieved (DateField): Achievement date.
        notes (CharField): Optional achievement notes.
    """
    
    class Meta:
        model = PersonalBest
        fields = ['exercise', 'category', 'value', 'unit', 'date_achieved', 'notes']
        widgets = {
            'date_achieved': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3})
        }
    
    def __init__(self, *args, **kwargs):
        """Initialize form with field validators.
        
        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)
        
        self.fields['exercise'].validators = [
            MinLengthValidator(2, "Exercise name must be at least 2 characters long"),
            MaxLengthValidator(MAX_EXERCISE_NAME_LENGTH, f"Exercise name cannot exceed {MAX_EXERCISE_NAME_LENGTH} characters")
        ]
        self.fields['value'].validators = [
            MinValueValidator(Decimal('0.01'), "Value must be greater than 0")
        ]
        self.fields['unit'].validators = [
            MinLengthValidator(1, "Unit is required"),
            MaxLengthValidator(20, "Unit cannot exceed 20 characters")
        ]
        
        self.fields['exercise'].help_text = "Name of the exercise or activity"
        self.fields['value'].help_text = "Your personal best value (weight, time, distance, etc.)"
        self.fields['unit'].help_text = "Unit of measurement (kg, lbs, minutes, km, etc.)"
    
    def clean_exercise(self):
        """Validate exercise name.
        
        Returns:
            str: Cleaned exercise name.
            
        Raises:
            ValidationError: If exercise name is invalid.
        """
        exercise = self.cleaned_data.get('exercise')
        if not exercise:
            raise ValidationError("Exercise name is required.")
            
        exercise = exercise.strip()
        if not exercise:
            raise ValidationError("Exercise name cannot be empty or only whitespace.")
            
        return exercise
    
    def clean_value(self):
        """Validate personal best value.
        
        Returns:
            Decimal: Cleaned value.
            
        Raises:
            ValidationError: If value is invalid.
        """
        value = self.cleaned_data.get('value')
        if value is None:
            raise ValidationError("Value is required.")
            
        try:
            value_decimal = Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise ValidationError("Value must be a valid number.")
            
        if value_decimal <= 0:
            raise ValidationError("Value must be greater than 0.")
            
        return value_decimal
    
    def clean_date_achieved(self):
        """Validate achievement date.
        
        Returns:
            date: Cleaned achievement date.
            
        Raises:
            ValidationError: If date is invalid.
        """
        achievement_date = self.cleaned_data.get('date_achieved')
        if not achievement_date:
            raise ValidationError("Achievement date is required.")
            
        if achievement_date > date.today():
            raise ValidationError("Achievement date cannot be in the future.")
            
        return achievement_date