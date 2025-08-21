"""Constants for the gym tracker application.

This module contains all constant values used throughout the application
to avoid magic numbers and ensure consistency.
"""

# Workout-related constants
MAX_WORKOUT_MINUTES = 300  # 5 hours maximum workout duration
MIN_WORKOUT_MINUTES = 1    # Minimum 1 minute workout
MAX_SETS = 50              # Maximum sets per exercise
MIN_SETS = 1               # Minimum sets per exercise
MAX_REPS = 1000            # Maximum reps per set
MIN_REPS = 1               # Minimum reps per set
MAX_WEIGHT_KG = 1000       # Maximum weight in kilograms
MIN_WEIGHT_KG = 0.1        # Minimum weight in kilograms

# BMI and health-related constants
BMI_MIN = 10.0             # Minimum realistic BMI
BMI_MAX = 60.0             # Maximum realistic BMI
MIN_HEIGHT_CM = 50         # Minimum height in centimeters
MAX_HEIGHT_CM = 300        # Maximum height in centimeters
MIN_BODY_WEIGHT_KG = 20    # Minimum body weight in kilograms
MAX_BODY_WEIGHT_KG = 500   # Maximum body weight in kilograms

# Age-related constants
MIN_AGE = 13               # Minimum age for gym membership
MAX_AGE = 120              # Maximum realistic age

# Rest timer constants
MIN_REST_SECONDS = 10      # Minimum rest time in seconds
MAX_REST_SECONDS = 3600    # Maximum rest time (1 hour)
DEFAULT_REST_SECONDS = 90  # Default rest time

# String length constants
MAX_EXERCISE_NAME_LENGTH = 100
MAX_NOTES_LENGTH = 500
MAX_TITLE_LENGTH = 200
MAX_USERNAME_LENGTH = 150

# Progress tracking constants
MAX_PROGRESS_PHOTOS = 100  # Maximum photos per user
MAX_JOURNAL_ENTRIES_PER_DAY = 5  # Maximum journal entries per day

# Calorie estimation constants
CALORIE_ESTIMATE_PER_WORKOUT = 300  # Average calories burned per workout

# Workout status choices
WORKOUT_STATUS_PLANNED = 'planned'
WORKOUT_STATUS_COMPLETED = 'completed'
WORKOUT_STATUS_MISSED = 'missed'

# Personal best categories
CATEGORY_STRENGTH = 'strength'
CATEGORY_CARDIO = 'cardio'
CATEGORY_FLEXIBILITY = 'flexibility'
CATEGORY_OTHER = 'other'

# File upload constants
MAX_IMAGE_SIZE_MB = 10     # Maximum image size in MB
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif']

# API rate limiting
MAX_API_REQUESTS_PER_MINUTE = 60
MAX_WORKOUT_LOGS_PER_DAY = 10

# Calculation constants
CALORIES_PER_WORKOUT_ESTIMATE = 400  # Default calorie estimate per workout
STREAK_RESET_DAYS = 2      # Days without workout before streak resets