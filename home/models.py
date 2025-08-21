from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date
from .constants import (
    MAX_WORKOUT_MINUTES, MIN_WORKOUT_MINUTES, MAX_SETS, MIN_SETS,
    MAX_REPS, MIN_REPS, MAX_WEIGHT_KG, MIN_WEIGHT_KG, BMI_MIN, BMI_MAX,
    MIN_HEIGHT_CM, MAX_HEIGHT_CM, MIN_BODY_WEIGHT_KG, MAX_BODY_WEIGHT_KG,
    MIN_AGE, MAX_AGE, MIN_REST_SECONDS, MAX_REST_SECONDS,
    MAX_EXERCISE_NAME_LENGTH, MAX_NOTES_LENGTH, MAX_TITLE_LENGTH,
    WORKOUT_STATUS_PLANNED, WORKOUT_STATUS_COMPLETED, WORKOUT_STATUS_MISSED,
    CATEGORY_STRENGTH, CATEGORY_CARDIO, CATEGORY_FLEXIBILITY, CATEGORY_OTHER
)

def get_today():
    """Return today's date.
    
    Returns:
        date: Current date object.
    """
    return date.today()


class TimestampedModel(models.Model):
    """Abstract base model that provides timestamp fields.
    
    This model provides created_at and updated_at fields that are
    automatically managed by Django. All models that need timestamp
    tracking should inherit from this base class.
    
    Attributes:
        created_at (DateTimeField): Timestamp when the record was created.
        updated_at (DateTimeField): Timestamp when the record was last updated.
    """
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the record was created")
    updated_at = models.DateTimeField(auto_now=True, help_text="Timestamp when the record was last updated")
    
    class Meta:
        abstract = True


class RestTimer(models.Model):
    """Model representing a user's rest timer configuration.
    
    This model stores custom rest timer settings that users can create
    and reuse during their workouts. Each timer has a name and duration.
    
    Attributes:
        user (ForeignKey): The user who owns this rest timer.
        name (CharField): Display name for the rest timer.
        duration (PositiveIntegerField): Rest duration in seconds.
        is_default (BooleanField): Whether this is the user's default timer.
    """
    # ForeignKey enables multiple rest timers per user with CASCADE deletion
    # related_name allows reverse lookup from User to rest_timers
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rest_timers')
    
    # CharField with max_length for efficient indexing and consistent timer naming
    # Reusing MAX_EXERCISE_NAME_LENGTH constant for consistency across models
    name = models.CharField(max_length=MAX_EXERCISE_NAME_LENGTH)
    
    # PositiveIntegerField ensures only positive values for rest duration
    # Storing in seconds provides precise timing control for workout rest periods
    duration = models.PositiveIntegerField(
        help_text="Rest time in seconds",
        # Using DecimalField constraints through validation in forms
    )
    
    # BooleanField to identify user's preferred default timer
    # default=False ensures new timers don't automatically become default
    is_default = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['name']
        unique_together = ['user', 'name']
        
    def __str__(self):
        """Return string representation of the rest timer.
        
        Returns:
            str: Formatted string with username, timer name, and duration.
        """
        return f"{self.user.username} - {self.name} ({self.duration}s)"

class Profile(models.Model):
    """Extended user profile model for gym tracker application.
    
    This model extends Django's built-in User model with additional
    fitness-related information. Each user has exactly one profile.
    
    Attributes:
        user (OneToOneField): Link to Django's User model.
        dob (DateField): User's date of birth for age calculations.
        workout_info (JSONField): Flexible storage for workout data.
        
    Data Type Choices:
        - OneToOneField ensures each User has exactly one Profile
        - DateField for birth date enables age-based fitness calculations
        - JSONField allows flexible, schema-less data storage for evolving requirements
    """
    # Using OneToOneField to ensure each User has exactly one Profile
    # CASCADE delete ensures Profile is removed when User is deleted
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # DateField chosen over DateTimeField as we only need birth date, not time
    # Default function allows dynamic date setting for new profiles
    dob = models.DateField(
        verbose_name="Date of Birth", 
        default=get_today,
        help_text="Used for age-based fitness calculations and recommendations"
    )
    
    # JSONField provides flexibility for storing varied workout data structures
    # Using JSONField instead of separate models for flexibility in storing
    # varied workout data structures (sets, reps, weights, etc.)
    # Default dict() prevents null values and ensures consistent data structure
    workout_info = models.JSONField(
        default=dict, 
        blank=True, 
        db_default={},
        help_text="Stores workout logs and exercise data in flexible JSON format"
    )

    def __str__(self):
        """Return string representation of the user profile.
        
        Returns:
            str: User's full name or username if name is not available.
        """
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}"
        return self.user.username


class Weight(models.Model):
    """Model for tracking user's weight measurements over time.
    
    This model stores weight entries for progress tracking and BMI calculations.
    Each user can have one weight entry per date to track their fitness journey.
    
    Attributes:
        user (ForeignKey): The user who recorded this weight measurement.
        weight (DecimalField): Weight value in kilograms.
        date (DateField): Date when the weight was recorded.
        
    Inherits:
        TimestampedModel: Provides created_at and updated_at timestamps.
        
    Data Type Choices:
        - DecimalField for weight ensures precise decimal calculations without
          floating-point rounding errors common with FloatField.
        - ForeignKey allows multiple weight entries per user for progress tracking.
    """
    # ForeignKey allows multiple weight entries per user for progress tracking
    # related_name enables reverse lookup from User to weights
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='weights')
    
    # DecimalField chosen over FloatField to avoid rounding errors in weight calculations
    # Using DecimalField instead of FloatField to avoid rounding errors in weight tracking
    # max_digits=5, decimal_places=2 supports weights up to 999.99 kg with 2 decimal precision
    weight = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        help_text="Weight in kilograms (e.g., 75.50)"
    )
    
    # DateField with default function ensures proper date handling
    # Allows multiple weight entries per day if needed for detailed tracking
    date = models.DateField(
        default=get_today,
        help_text="Date when this weight measurement was taken"
    )
    
    # CharField with max_length for optional notes, null=True allows empty entries
    notes = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['user', 'date']
        
    def __str__(self):
        """Return string representation of the weight entry.
        
        Returns:
            str: Formatted string with username, weight, and date.
        """
        return f"{self.user.username} - {self.weight}kg on {self.date}"


class Journal(models.Model):
    """Model for user's fitness journal entries.
    
    This model allows users to record their thoughts, progress notes,
    and reflections about their fitness journey. Each entry has a title,
    content, and date for organization.
    
    Attributes:
        user (ForeignKey): The user who created this journal entry.
        title (CharField): Title or subject of the journal entry.
        content (TextField): Main content of the journal entry.
        date (DateField): Date associated with this journal entry.
        mood (CharField): Optional mood indicator for the entry.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='journal_entries')
    title = models.CharField(
        max_length=MAX_TITLE_LENGTH,
        help_text="Brief title describing the journal entry"
    )
    # Using TextField instead of CharField for unlimited content length
    content = models.TextField(
        help_text="Main content of your journal entry - thoughts, progress, goals, etc."
    )
    date = models.DateField(
        default=get_today,
        help_text="Date this journal entry refers to"
    )
    mood = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['user', 'date', 'title']
        
    def __str__(self):
        """Return string representation of the journal entry.
        
        Returns:
            str: Formatted string with username, title, and date.
        """
        return f"{self.user.username} - {self.title} ({self.date})"


class ScheduledWorkout(models.Model):
    """Model for user's scheduled workout sessions.
    
    This model allows users to plan future workouts and track their completion
    status. Each workout has a title, description, scheduled date, and status.
    
    Attributes:
        user (ForeignKey): The user who scheduled this workout.
        title (CharField): Title or name of the workout session.
        description (TextField): Detailed description of the workout plan.
        date (DateField): Date when the workout is scheduled.
        status (CharField): Current status of the workout (planned/completed/missed).
        notes (TextField): Additional notes about the workout.
    """
    STATUS_CHOICES = [
        (WORKOUT_STATUS_PLANNED, 'Planned'),
        (WORKOUT_STATUS_COMPLETED, 'Completed'),
        (WORKOUT_STATUS_MISSED, 'Missed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scheduled_workouts')
    title = models.CharField(
        max_length=MAX_TITLE_LENGTH,
        help_text="Name or title of the workout session"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of exercises and workout plan"
    )
    date = models.DateField(
        help_text="Date when this workout is planned to be performed"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default=WORKOUT_STATUS_PLANNED,
        help_text="Current status of the scheduled workout"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about the workout session"
    )
    
    class Meta:
        ordering = ['date']
        unique_together = ['user', 'date', 'title']
        
    def __str__(self):
        """Return string representation of the scheduled workout.
        
        Returns:
            str: Formatted string with username, title, and date.
        """
        return f"{self.user.username} - {self.title} ({self.date})"


class PersonalBest(models.Model):
    """Model for tracking user's personal best achievements.
    
    This model records the user's best performance for different exercises
    across various categories. Each personal best includes the exercise name,
    category, achieved value, unit of measurement, and date achieved.
    
    Attributes:
        user (ForeignKey): The user who achieved this personal best.
        exercise (CharField): Name of the exercise or activity.
        category (CharField): Category of the exercise (strength, cardio, etc.).
        value (DecimalField): The achieved value (weight, time, distance, etc.).
        unit (CharField): Unit of measurement for the value.
        date_achieved (DateField): Date when this personal best was achieved.
        notes (TextField): Additional notes about the achievement.
        is_current (BooleanField): Flag to mark if this is the current PR.
    """
    CATEGORY_CHOICES = (
        (CATEGORY_STRENGTH, 'Strength'),
        (CATEGORY_CARDIO, 'Cardio'),
        (CATEGORY_FLEXIBILITY, 'Flexibility & Endurance'),
        (CATEGORY_OTHER, 'Other'),
    )
    
    # ForeignKey enables multiple personal bests per user across different exercises
    # related_name allows reverse lookup from User to personal_bests
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='personal_bests')
    
    # CharField with max_length for efficient indexing and consistent exercise naming
    exercise = models.CharField(
        max_length=MAX_EXERCISE_NAME_LENGTH,
        help_text="Name of the exercise or activity"
    )
    
    # CharField with choices ensures data consistency and prevents invalid categories
    # Limited choices make queries more efficient and UI more predictable
    category = models.CharField(
        max_length=20, 
        choices=CATEGORY_CHOICES, 
        default=CATEGORY_OTHER,
        help_text="Category classification for this exercise"
    )
    
    # Using DecimalField instead of FloatField for precise measurement tracking
    # max_digits=10 supports large values, decimal_places=2 for precise measurements
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="The achieved value (weight, time, distance, etc.)"
    )
    
    # CharField for unit allows flexible measurement types (kg, lbs, seconds, etc.)
    unit = models.CharField(
        max_length=20,
        help_text="Unit of measurement (kg, lbs, seconds, minutes, km, etc.)"
    )
    
    # DateField with default function for automatic date setting on new records
    date_achieved = models.DateField(
        default=get_today,
        help_text="Date when this personal best was achieved"
    )
    
    # TextField allows unlimited text for detailed achievement descriptions
    # blank=True makes notes optional for user convenience
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about the achievement or conditions"
    )
    
    # BooleanField to track current vs historical personal records
    is_current = models.BooleanField(
        default=True,
        help_text="Flag to mark if this is the current personal record"
    )
    
    class Meta:
        ordering = ['-date_achieved']
        unique_together = ['user', 'exercise', 'is_current']
        
    def __str__(self):
        """Return string representation of the personal best.
        
        Returns:
            str: Formatted string with username, exercise, value, and unit.
        """
        return f"{self.user.username} - {self.exercise}: {self.value} {self.unit}"


class ProgressPhoto(models.Model):
    """Model for storing user's progress photos.
    
    This model allows users to upload and track their physical progress
    through photos over time. Each photo can include optional weight data
    and notes for comprehensive progress tracking.
    
    Attributes:
        user (ForeignKey): The user who uploaded this progress photo.
        image (ImageField): The uploaded progress photo file.
        date (DateField): Date when the photo was taken.
        notes (TextField): Optional notes about the photo or progress.
        weight (DecimalField): Optional weight measurement at time of photo.
    """
    # ForeignKey enables multiple progress photos per user with CASCADE deletion
    # related_name allows reverse lookup from User to progress_photos
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress_photos')
    
    # ImageField with upload_to pattern organizes files by year/month for better file management
    # Automatic file handling and validation for image formats
    image = models.ImageField(
        upload_to='progress_photos/%Y/%m/',
        help_text="Upload your progress photo"
    )
    
    # DateField with default function for automatic date setting on new records
    date = models.DateField(
        default=get_today,
        help_text="Date when this photo was taken"
    )
    
    # TextField allows unlimited text for detailed progress descriptions
    # blank=True makes notes optional for user convenience
    notes = models.TextField(
        blank=True,
        help_text="Optional notes about your progress or this photo"
    )
    
    # Using DecimalField instead of FloatField for consistent weight tracking
    # null=True and blank=True make weight optional since not all photos need weight data
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True, 
        blank=True, 
        help_text="Your weight in kilograms when this photo was taken"
    )
    
    class Meta:
        ordering = ['-date']
        unique_together = ['user', 'date']
        
    def __str__(self):
        """Return string representation of the progress photo.
        
        Returns:
            str: Formatted string with username and photo date.
        """
        return f"{self.user.username} - Photo on {self.date}"


class AICoachQuestion(models.Model):
    """Model for storing AI coach questions and answers.
    
    This model facilitates the AI coaching feature by storing user questions
    and AI-generated responses. It tracks when questions are asked and answered
    to provide a comprehensive coaching history.
    
    Attributes:
        user (ForeignKey): The user who asked the question.
        question (TextField): The question asked by the user.
        answer (TextField): The AI-generated answer to the question.
        created_at (DateTimeField): Timestamp when the question was created.
        answered_at (DateTimeField): Timestamp when the question was answered.
        is_answered (BooleanField): Flag indicating if question has been answered.
    """
    # ForeignKey enables multiple AI coach interactions per user
    # related_name allows reverse lookup from User to ai_coach_questions
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_coach_questions')
    
    # TextField allows unlimited text length for complex fitness questions
    # No max_length restriction ensures users can ask detailed questions
    question = models.TextField(
        help_text="Your question for the AI fitness coach"
    )
    
    # DateTimeField with default=timezone.now for automatic timestamp creation
    # Records when the question was first asked
    created_at = models.DateTimeField(
        default=timezone.now,
        help_text="Timestamp when this question was created"
    )
    
    # TextField for AI responses with blank=True and null=True for pending answers
    # Allows storage of lengthy, detailed AI-generated coaching responses
    answer = models.TextField(
        blank=True, 
        null=True,
        help_text="AI-generated response to your question"
    )
    
    # DateTimeField with null=True for precise timestamp when answer is provided
    # More precise than DateField since AI responses happen in real-time
    answered_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Timestamp when this question was answered"
    )
    
    # BooleanField for quick status checking without needing to check answer field
    # default=False ensures new questions start as unanswered
    is_answered = models.BooleanField(
        default=False,
        help_text="Whether this question has been answered by the AI coach"
    )
    
    class Meta:
        ordering = ['-id']
        
    def __str__(self):
        """Return string representation of the AI coach question.
        
        Returns:
            str: Formatted string with username and truncated question.
        """
        return f"{self.user.username} - {self.question[:50]}..."

