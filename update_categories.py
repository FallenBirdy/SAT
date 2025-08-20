from django.core.wsgi import get_wsgi_application
import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gymTracker.settings')
django.setup()

# Import models after Django setup
from home.models import PersonalBest

# Define exercise categories mapping
strength_exercises = ['bench', 'squat', 'deadlift', 'press', 'curl', 'row']
cardio_exercises = ['run', 'jog', 'sprint', 'cycle', 'bike', 'swim', 'rowing']
flexibility_exercises = ['stretch', 'yoga', 'plank', 'hold', 'bridge']

def categorize_exercise(exercise_name):
    """Categorize an exercise based on its name"""
    exercise_lower = exercise_name.lower()
    
    # Check if exercise name contains any strength-related keywords
    for keyword in strength_exercises:
        if keyword in exercise_lower:
            return 'strength'
    
    # Check if exercise name contains any cardio-related keywords
    for keyword in cardio_exercises:
        if keyword in exercise_lower:
            return 'cardio'
    
    # Check if exercise name contains any flexibility-related keywords
    for keyword in flexibility_exercises:
        if keyword in exercise_lower:
            return 'flexibility'
    
    # Default to 'other' if no match found
    return 'other'

def update_categories():
    """Update categories for all personal best records"""
    personal_bests = PersonalBest.objects.all()
    updated_count = 0
    
    for pb in personal_bests:
        new_category = categorize_exercise(pb.exercise)
        if pb.category != new_category:
            pb.category = new_category
            pb.save()
            updated_count += 1
            print(f"Updated {pb.exercise} from 'other' to '{new_category}'")
    
    print(f"\nUpdated {updated_count} records out of {personal_bests.count()}")

if __name__ == '__main__':
    print("Updating personal best categories...")
    update_categories()
    print("Done!")