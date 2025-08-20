from django.db import models
from django.contrib.auth.models import User
from datetime import date

def get_today():
    return date.today()


class RestTimer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rest_timers')
    name = models.CharField(max_length=100)
    duration = models.PositiveIntegerField(help_text="Rest time in seconds")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        unique_together = ['user', 'name']
        
    def __str__(self):
        return f"{self.user.username} - {self.name} ({self.duration}s)"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    dob = models.DateField(verbose_name="Date of Birth", default=get_today)
    workout_info = models.JSONField(default=dict, blank=True, db_default={})



    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"


class Weight(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='weights')
    weight = models.FloatField(help_text="Weight in kilograms")
    date = models.DateField(default=get_today)
    notes = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['user', 'date']
    
    def __str__(self):
        return f"{self.user.username} - {self.weight}kg on {self.date}"


class Journal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='journals')
    title = models.CharField(max_length=200)
    content = models.TextField()
    date = models.DateField(default=get_today)
    mood = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['user', 'date', 'title']
        
    def __str__(self):
        return f"{self.user.username} - {self.title} ({self.date})"


class ScheduledWorkout(models.Model):
    STATUS_CHOICES = (
        ('planned', 'Planned'),
        ('completed', 'Completed'),
        ('missed', 'Missed'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='planned')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['date']
        unique_together = ['user', 'date', 'title']


class PersonalBest(models.Model):
    CATEGORY_CHOICES = (
        ('strength', 'Strength'),
        ('cardio', 'Cardio'),
        ('flexibility', 'Flexibility & Endurance'),
        ('other', 'Other'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exercise = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    value = models.FloatField()  # Weight, time, distance, etc.
    unit = models.CharField(max_length=20)  # kg, lbs, seconds, minutes, km, etc.
    date_achieved = models.DateField(default=get_today)
    notes = models.TextField(blank=True)
    is_current = models.BooleanField(default=True)  # Flag to mark if this is the current PR
    
    class Meta:
        ordering = ['-date_achieved']
        unique_together = ['user', 'exercise', 'is_current']


class ProgressPhoto(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress_photos')
    image = models.ImageField(upload_to='progress_photos/%Y/%m/')
    date = models.DateField(default=get_today)
    notes = models.TextField(blank=True)
    weight = models.FloatField(null=True, blank=True, help_text="Weight in kilograms")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
        
    def __str__(self):
        return f"{self.user.username} - Photo on {self.date}"


class AICoachQuestion(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_coach_questions')
    question = models.TextField()
    answer = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.user.username} - {self.question[:50]}..."

