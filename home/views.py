"""Views module for the gym tracker application.

This module contains all view functions and API endpoints for handling
user interactions, data processing, and rendering templates for the
gym tracking application.

The module follows Django best practices with proper error handling,
user authentication, and comprehensive input validation.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
import json
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm
from django.contrib.auth.models import User
from django.db.models import Count
from home.models import Profile, Weight, ScheduledWorkout, PersonalBest, Journal, RestTimer, ProgressPhoto, AICoachQuestion
from django.contrib import messages
from django.contrib.auth import logout, login, authenticate
from datetime import datetime, timedelta
import csv
import os
from django.conf import settings
from django.http import FileResponse
from django.utils import timezone
from home.constants import *
from home.services import FitnessCalculationService, WorkoutAnalysisService
from decimal import Decimal


def logout_view(request):
    """Handle user logout and redirect to home page.
    
    This view logs out the current user, displays a success message,
    and redirects to the home page.
    
    Args:
        request (HttpRequest): The HTTP request object.
        
    Returns:
        HttpResponseRedirect: Redirect to home page.
    """
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('home')


@login_required
def workout_view(request):
    """Display the workout tracking page for authenticated users.
    
    This view retrieves the user's workout information from their profile
    and renders the workout template with the workout data.
    
    Args:
        request (HttpRequest): The HTTP request object with authenticated user.
        
    Returns:
        HttpResponse: Rendered workout template with user's workout data.
    """
    workout_info = Profile.objects.get(user=request.user).workout_info
    if 'workouts' not in workout_info:
        workout_info["workouts"] = []
    context = {"workout_info": workout_info["workouts"]}
    return render(request, 'home/workout.html', context=context)


@login_required
def log_workout_api(request):
    """API endpoint for logging workout entries.
    
    This view handles POST requests to create new workout entries
    for the authenticated user. It validates required fields and
    stores the workout data in the user's profile.
    
    Args:
        request (HttpRequest): The HTTP request object containing workout data.
        
    Returns:
        JsonResponse: Success/failure status with workout data or error message.
        
    Expected POST data:
        - type (str): Type of workout performed.
        - details (str): Detailed description of the workout.
        - date (str, optional): Date of workout in YYYY-MM-DD format.
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        workout_type = data.get('type')
        details = data.get('details')
        date = data.get('date')

        if not all([workout_type, details]):
            return JsonResponse({'success': False, 'error': 'Missing required fields'})

        profile = Profile.objects.get(user=request.user)
        workout_info = profile.workout_info

        if 'workouts' not in workout_info:
            workout_info['workouts'] = []

        workout_entry = {
            'type': workout_type,
            'details': details,
            'date': date or datetime.now().strftime('%Y-%m-%d')
        }

        workout_info['workouts'].append(workout_entry)

        profile.workout_info = workout_info
        profile.save()

        return JsonResponse({'success': True, 'workout': workout_entry})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def calendar_view(request):
    """Display the workout calendar page for authenticated users.
    
    This view renders the calendar template where users can view
    and manage their scheduled workouts.
    
    Args:
        request (HttpRequest): The HTTP request object with authenticated user.
        
    Returns:
        HttpResponse: Rendered calendar template with page title.
    """
    return render(request, 'home/calendar.html', {'page_title': 'Workout Calendar'})

@login_required
def scheduled_workout_api(request):
    """API endpoint for managing scheduled workouts.
    
    This view handles GET requests to retrieve all scheduled workouts
    and POST requests to create new scheduled workouts for the user.
    
    Args:
        request (HttpRequest): The HTTP request object with authenticated user.
        
    Returns:
        JsonResponse: Success/failure status with workout data or error message.
        
    GET Response:
        - success (bool): Operation success status.
        - workouts (list): List of scheduled workout objects.
        
    POST Expected data:
        - title (str): Workout title (required).
        - description (str): Workout description (optional).
        - date (str): Workout date in YYYY-MM-DD format (required).
        - status (str): Workout status, defaults to 'planned'.
        - notes (str): Additional notes (optional).
    """
    if request.method == 'GET':
        # Get all scheduled workouts for the user
        try:
            workouts = ScheduledWorkout.objects.filter(user=request.user).order_by('date')
            # Using list comprehension for efficient data transformation
            workout_data = [{
                'id': workout.id,
                'title': workout.title,
                'description': workout.description,
                'date': workout.date.strftime('%Y-%m-%d'),  # ISO format for consistency
                'status': workout.status,
                'notes': workout.notes
            } for workout in workouts]
            
            return JsonResponse({'success': True, 'workouts': workout_data})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    elif request.method == 'POST':
        data = json.loads(request.body)
        title = data.get('title')
        description = data.get('description', '')
        date_str = data.get('date')
        status = data.get('status', WORKOUT_STATUS_PLANNED)  # Using constant for default status
        notes = data.get('notes', '')
        
        if not title or not date_str:
            return JsonResponse({'success': False, 'error': 'Missing required fields'})
        
        try:
            # Using datetime.strptime for robust date parsing
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Create scheduled workout
            workout = ScheduledWorkout.objects.create(
                user=request.user,
                title=title,
                description=description,
                date=date_obj,
                status=status,
                notes=notes
            )
            
            return JsonResponse({
                'success': True,
                'workout': {
                    'id': workout.id,
                    'title': workout.title,
                    'description': workout.description,
                    'date': workout.date.strftime('%Y-%m-%d'),
                    'status': workout.status,
                    'notes': workout.notes
                }
            })
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid date format'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def scheduled_workout_detail_api(request, workout_id):
    try:
        workout = ScheduledWorkout.objects.get(id=workout_id, user=request.user)
    except ScheduledWorkout.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Workout not found'})
    
    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'workout': {
                'id': workout.id,
                'title': workout.title,
                'description': workout.description,
                'date': workout.date.strftime('%Y-%m-%d'),
                'status': workout.status,
                'notes': workout.notes
            }
        })
    
    elif request.method == 'PATCH':
        data = json.loads(request.body)
        
        # Update only the fields that are provided
        if 'title' in data:
            workout.title = data['title']
        if 'description' in data:
            workout.description = data['description']
        if 'date' in data:
            try:
                workout.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Invalid date format'})
        if 'status' in data:
            workout.status = data['status']
        if 'notes' in data:
            workout.notes = data['notes']
        
        workout.save()
        
        return JsonResponse({
            'success': True,
            'workout': {
                'id': workout.id,
                'title': workout.title,
                'description': workout.description,
                'date': workout.date.strftime('%Y-%m-%d'),
                'status': workout.status,
                'notes': workout.notes
            }
        })
    
    elif request.method == 'DELETE':
        workout.delete()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def personal_bests_view(request):
    """Display the personal bests page for authenticated users.
    
    This view renders the personal bests template where users can view
    and manage their personal best records.
    
    Args:
        request (HttpRequest): The HTTP request object with authenticated user.
        
    Returns:
        HttpResponse: Rendered personal bests template with page title.
    """
    return render(request, 'home/personal_bests.html', {'page_title': 'Personal Bests'})

@login_required
def personal_best_api(request):
    """API endpoint for managing personal best records.
    
    This view handles GET requests to retrieve current personal bests
    and POST requests to create new personal best records, with automatic
    comparison to determine if it's a new record.
    
    Args:
        request (HttpRequest): The HTTP request object with authenticated user.
        
    Returns:
        JsonResponse: Success/failure status with personal best data or error message.
        
    GET Response:
        - success (bool): Operation success status.
        - personal_bests (list): List of current personal best objects.
        
    POST Expected data:
        - exercise (str): Name of the exercise (required).
        - category (str): Category of the personal best, defaults to 'other'.
        - value (float): The personal best value (required).
        - unit (str): Unit of measurement (required).
        - date_achieved (str): Date in YYYY-MM-DD format (optional, defaults to today).
        - notes (str): Additional notes (optional).
    """
    if request.method == 'GET':
        # Get all personal bests for the user - using is_current to track active records
        try:
            prs = PersonalBest.objects.filter(user=request.user, is_current=True).order_by('exercise')
            # Using DecimalField for value to maintain precision in fitness measurements
            pr_data = [{
                'id': pr.id,
                'exercise': pr.exercise,
                'category': pr.category,
                'value': pr.value,
                'unit': pr.unit,
                'date_achieved': pr.date_achieved.strftime('%Y-%m-%d'),
                'notes': pr.notes,
                'is_current': pr.is_current
            } for pr in prs]
            
            return JsonResponse({'success': True, 'personal_bests': pr_data})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    elif request.method == 'POST':
        data = json.loads(request.body)
        exercise = data.get('exercise')
        category = data.get('category', 'other')
        value = data.get('value')
        unit = data.get('unit')
        date_str = data.get('date_achieved', datetime.now().strftime('%Y-%m-%d'))
        notes = data.get('notes', '')
        
        if not exercise or not value or not unit:
            return JsonResponse({'success': False, 'error': 'Missing required fields'})
        
        try:
            value = float(value)
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Check if this is a new PR
            existing_prs = PersonalBest.objects.filter(
                user=request.user,
                exercise=exercise,
                is_current=True
            )
            
            is_new_record = True
            if existing_prs.exists():
                current_pr = existing_prs.first()
                # Compare based on value (higher is better)
                if current_pr.value >= value:
                    is_new_record = False
                else:
                    # Mark old PR as not current
                    current_pr.is_current = False
                    current_pr.save()
            
            if is_new_record:
                # Create new PR
                pr = PersonalBest.objects.create(
                    user=request.user,
                    exercise=exercise,
                    category=category,
                    value=value,
                    unit=unit,
                    date_achieved=date_obj,
                    notes=notes,
                    is_current=True
                )
                
                return JsonResponse({
                    'success': True,
                    'is_new_record': True,
                    'personal_best': {
                        'id': pr.id,
                        'exercise': pr.exercise,
                        'category': pr.category,
                        'value': pr.value,
                        'unit': pr.unit,
                        'date_achieved': pr.date_achieved.strftime('%Y-%m-%d'),
                        'notes': pr.notes
                    }
                })
            else:
                return JsonResponse({
                    'success': True,
                    'is_new_record': False,
                    'message': 'This is not a new personal best.'
                })
                
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid value or date format'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def personal_best_detail_api(request, pr_id):
    try:
        pr = PersonalBest.objects.get(id=pr_id, user=request.user)
    except PersonalBest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Personal best not found'})
    
    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'personal_best': {
                'id': pr.id,
                'exercise': pr.exercise,
                'category': pr.category,
                'value': pr.value,
                'unit': pr.unit,
                'date_achieved': pr.date_achieved.strftime('%Y-%m-%d'),
                'notes': pr.notes,
                'is_current': pr.is_current
            }
        })
    
    elif request.method == 'DELETE':
        pr.delete()
        return JsonResponse({'success': True})
    
    elif request.method == 'PATCH':
        data = json.loads(request.body)
        
        if 'exercise' in data:
            pr.exercise = data['exercise']
        if 'value' in data:
            pr.value = float(data['value'])
        if 'unit' in data:
            pr.unit = data['unit']
        if 'date_achieved' in data:
            pr.date_achieved = datetime.strptime(data['date_achieved'], '%Y-%m-%d').date()
        if 'notes' in data:
            pr.notes = data['notes']
        
        pr.save()
        
        return JsonResponse({
            'success': True,
            'personal_best': {
                'id': pr.id,
                'exercise': pr.exercise,
                'value': pr.value,
                'unit': pr.unit,
                'date_achieved': pr.date_achieved.strftime('%Y-%m-%d'),
                'notes': pr.notes,
                'is_current': pr.is_current
            }
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def journal_view(request):
    """Display the workout journal page for authenticated users.
    
    This view renders the journal template where users can create,
    view, and manage their workout journal entries.
    
    Args:
        request (HttpRequest): The HTTP request object with authenticated user.
        
    Returns:
        HttpResponse: Rendered journal template with page title.
    """
    return render(request, 'home/journal.html', {'page_title': 'Workout Journal'})

@login_required
def journal_api(request):
    """API endpoint for managing workout journal entries.
    
    This view handles GET requests to retrieve all journal entries
    and POST requests to create new journal entries for the user.
    
    Args:
        request (HttpRequest): The HTTP request object with authenticated user.
        
    Returns:
        JsonResponse: Success/failure status with journal data or error message.
        
    GET Response:
        - success (bool): Operation success status.
        - entries (list): List of journal entry objects ordered by date (newest first).
        
    POST Expected data:
        - title (str): Journal entry title (required).
        - content (str): Journal entry content (required).
        - date (str): Entry date in YYYY-MM-DD format (optional, defaults to today).
        - mood (str): User's mood for the entry (optional).
    """
    if request.method == 'GET':
        # Get all journal entries for the user - ordered by date descending for recent first
        try:
            entries = Journal.objects.filter(user=request.user).order_by('-date')
            # Using TextField for content to allow unlimited text length for detailed entries
            entry_data = [{
                'id': entry.id,
                'title': entry.title,
                'content': entry.content,
                'date': entry.date.strftime('%Y-%m-%d'),
                'mood': entry.mood,
                'created_at': entry.created_at.strftime('%Y-%m-%d %H:%M:%S')  # Full timestamp for audit trail
            } for entry in entries]
            
            return JsonResponse({'success': True, 'entries': entry_data})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    elif request.method == 'POST':
        data = json.loads(request.body)
        title = data.get('title')
        content = data.get('content')
        date_str = data.get('date', datetime.now().strftime('%Y-%m-%d'))
        mood = data.get('mood', '')
        
        if not title or not content:
            return JsonResponse({'success': False, 'error': 'Missing required fields'})
            
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Create journal entry
            entry = Journal.objects.create(
                user=request.user,
                title=title,
                content=content,
                date=date_obj,
                mood=mood
            )
            
            return JsonResponse({
                'success': True,
                'entry': {
                    'id': entry.id,
                    'title': entry.title,
                    'content': entry.content,
                    'date': entry.date.strftime('%Y-%m-%d'),
                    'mood': entry.mood,
                    'created_at': entry.created_at.strftime('%Y-%m-%d %H:%M:%S')
                }
            })
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid date format'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def journal_stats_api(request):
    if request.method == 'GET':
        try:
            # Get total count of journal entries
            total_entries = Journal.objects.filter(user=request.user).count()
            
            # Get entries by mood
            mood_counts = {}
            moods = Journal.objects.filter(user=request.user).values('mood').annotate(count=Count('mood'))
            for mood_data in moods:
                if mood_data['mood']:
                    mood_counts[mood_data['mood']] = mood_data['count']
            
            # Get entries by month (last 6 months)
            today = datetime.now().date()
            six_months_ago = today - timedelta(days=180)
            entries_by_month = {}
            
            entries = Journal.objects.filter(
                user=request.user,
                date__gte=six_months_ago
            ).order_by('date')
            
            for entry in entries:
                month_key = entry.date.strftime('%Y-%m')
                if month_key not in entries_by_month:
                    entries_by_month[month_key] = 0
                entries_by_month[month_key] += 1
            
            # Get streak information
            entries_dates = Journal.objects.filter(user=request.user).values_list('date', flat=True).order_by('-date')
            current_streak = 0
            longest_streak = 0
            streak_count = 0
            last_date = None
            
            for date in entries_dates:
                if last_date is None:
                    streak_count = 1
                    last_date = date
                elif (last_date - date).days == 1:
                    streak_count += 1
                    last_date = date
                else:
                    if streak_count > longest_streak:
                        longest_streak = streak_count
                    streak_count = 1
                    last_date = date
            
            if streak_count > longest_streak:
                longest_streak = streak_count
            
            # Check if there's an entry for today
            has_entry_today = Journal.objects.filter(user=request.user, date=today).exists()
            
            # Calculate current streak
            if has_entry_today:
                current_streak = 1
                check_date = today - timedelta(days=1)
                while Journal.objects.filter(user=request.user, date=check_date).exists():
                    current_streak += 1
                    check_date -= timedelta(days=1)
            
            return JsonResponse({
                'success': True,
                'stats': {
                    'total_entries': total_entries,
                    'mood_counts': mood_counts,
                    'entries_by_month': entries_by_month,
                    'current_streak': current_streak,
                    'longest_streak': longest_streak,
                    'has_entry_today': has_entry_today
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def journal_entry_api(request, entry_id):
    try:
        entry = Journal.objects.get(id=entry_id, user=request.user)
    except Journal.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Journal entry not found'})
    
    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'entry': {
                'id': entry.id,
                'title': entry.title,
                'content': entry.content,
                'date': entry.date.strftime('%Y-%m-%d'),
                'mood': entry.mood,
                'created_at': entry.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': entry.updated_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(entry, 'updated_at') else None
            }
        })
    
    elif request.method == 'PUT':
        data = json.loads(request.body)
        title = data.get('title')
        content = data.get('content')
        date_str = data.get('date')
        mood = data.get('mood', '')
        
        if not title or not content or not date_str:
            return JsonResponse({'success': False, 'error': 'Missing required fields'})
        
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            entry.title = title
            entry.content = content
            entry.date = date_obj
            entry.mood = mood
            entry.save()
            
            return JsonResponse({
                'success': True,
                'entry': {
                    'id': entry.id,
                    'title': entry.title,
                    'content': entry.content,
                    'date': entry.date.strftime('%Y-%m-%d'),
                    'mood': entry.mood,
                    'created_at': entry.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'updated_at': entry.updated_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(entry, 'updated_at') else None
                }
            })
                
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid date format'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    elif request.method == 'DELETE':
        entry.delete()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


def register_view(request):
    """Handle user registration with automatic login on success.
    
    This view processes user registration forms, creates user accounts,
    and automatically logs in users upon successful registration.
    
    Args:
        request (HttpRequest): The HTTP request object containing form data.
        
    Returns:
        HttpResponse: Rendered registration template or redirect to dashboard/login.
        
    POST Processing:
        - Validates registration form data using RegisterForm.
        - Creates user account and profile.
        - Automatically authenticates and logs in the new user.
        - Redirects to dashboard on success or login on authentication failure.
    """
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            try:
                profile = form.save()
                user = profile.user
                # Authenticate and login the user automatically for better UX
                user = authenticate(username=user.username, password=form.cleaned_data['password1'])
                if user:
                    login(request, user)
                    messages.success(request, "Registration successful! Welcome to Gym Tracker.")
                    return redirect('dashboard')
                else:
                    messages.error(request, "Registration successful but login failed. Please log in manually.")
                    return redirect('login')
            except Exception as e:
                messages.error(request, f"Registration failed: {str(e)}")
    else:
        form = RegisterForm()
    return render(request, 'home/register.html', {'form': form})

@login_required
def log_goal_api(request):
    """API endpoint for creating new fitness goals.
    
    This view handles POST requests to create new fitness goals
    and stores them in the user's profile workout_info JSONField.
    
    Args:
        request (HttpRequest): The HTTP request object with authenticated user.
        
    Returns:
        JsonResponse: Success/failure status with goal data or error message.
        
    POST Expected data:
        - title (str): Goal title (required).
        - details (str): Goal details (optional).
        - target_date (str): Target completion date (optional).
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        title = data.get('title')
        details = data.get('details')
        target_date = data.get('target_date')

        if not title:
            return JsonResponse({'success': False, 'error': 'Missing required fields'})

        profile = Profile.objects.get(user=request.user)
        # Using JSONField for flexible goal storage - allows dynamic goal structures
        workout_info = profile.workout_info

        if 'goals' not in workout_info:
            workout_info['goals'] = []

        goal_entry = {
            'title': title,
            'details': details or '',
            'target_date': target_date,
            'progress': 0,  # Initial progress is 0% - using integer for easy calculation
            'created_at': datetime.now().strftime('%Y-%m-%d')  # ISO date format for consistency
        }

        workout_info['goals'].append(goal_entry)

        profile.workout_info = workout_info
        profile.save()

        return JsonResponse({'success': True, 'goal': goal_entry})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def goal_view(request):
    """Display the goals page with user's fitness goals.
    
    This view retrieves and displays all fitness goals from the user's
    profile workout_info JSONField.
    
    Args:
        request (HttpRequest): The HTTP request object with authenticated user.
        
    Returns:
        HttpResponse: Rendered goals template with user's goals data.
    """
    workout_info = Profile.objects.get(user=request.user).workout_info
    # Ensure goals key exists in JSONField to prevent KeyError
    if 'goals' not in workout_info:
        workout_info["goals"] = []
    context = {"goals": workout_info["goals"]}
    return render(request, 'home/goals.html', context=context)

@login_required
def weight_tracker_view(request):
    """Display the weight tracker page for authenticated users.
    
    This view renders the weight tracker template where users can
    log and visualize their weight progress over time.
    
    Args:
        request (HttpRequest): The HTTP request object with authenticated user.
        
    Returns:
        HttpResponse: Rendered weight tracker template.
    """
    return render(request, 'home/weight_tracker.html')

@login_required
def calculate_workout_streak(user, workouts):
    """Calculate the current workout streak for a user"""
    from datetime import datetime, timedelta
    
    # Get all workout dates (both logged workouts and completed scheduled workouts)
    workout_dates = set()
    
    # Add logged workout dates
    for workout in workouts:
        if workout.get('date'):
            try:
                workout_date = datetime.strptime(workout['date'], '%Y-%m-%d').date()
                workout_dates.add(workout_date)
            except (ValueError, TypeError):
                continue
    
    # Add completed scheduled workout dates
    scheduled_workouts = ScheduledWorkout.objects.filter(
        user=user, 
        status='completed'
    )
    for workout in scheduled_workouts:
        workout_dates.add(workout.date)
    
    if not workout_dates:
        return 0
    
    # Sort dates in descending order
    sorted_dates = sorted(workout_dates, reverse=True)
    
    # Calculate streak from today backwards
    today = timezone.now().date()
    current_streak = 0
    
    # Check if there's a workout today or yesterday (to account for different time zones)
    check_date = today
    
    for i in range(len(sorted_dates)):
        if sorted_dates[i] == check_date:
            current_streak += 1
            check_date = check_date - timedelta(days=1)
        elif sorted_dates[i] == check_date - timedelta(days=1):
            # Allow for one day gap (yesterday)
            current_streak += 1
            check_date = sorted_dates[i] - timedelta(days=1)
        else:
            # Gap found, streak ends
            break
    
    return current_streak

def dashboard_view(request):
    return render(request, 'home/dashboard.html')

@login_required
def dashboard_data_api(request):
    """API endpoint for dashboard statistics and recent activity data.
    
    This view aggregates workout statistics, goal progress, and recent activity
    from multiple sources (JSONField workouts, ScheduledWorkout model, Weight model)
    to provide comprehensive dashboard data.
    
    Args:
        request (HttpRequest): The HTTP request object with authenticated user.
        
    Returns:
        JsonResponse: Dashboard statistics including workout count, calories,
                     streak days, active goals, and recent activity feed.
    """
    if request.method == 'GET':
        try:
            profile = Profile.objects.get(user=request.user)
            # Using JSONField for flexible workout data storage
            workout_info = profile.workout_info
            
            # Calculate real workout statistics
            workouts = workout_info.get('workouts', [])
            workout_count = len(workouts)
            
            # Calculate total calories burned (estimate: 300-500 calories per workout)
            # Using integer calculation for consistent calorie tracking across sessions
            total_calories = 0
            for workout in workouts:
                # Simple calorie estimation: 400 calories per workout on average
                workout_calories = 400  # Base calories per workout
                total_calories += workout_calories
            
            # Converting to int for JSON serialization consistency
            total_calories = int(total_calories)
            
            # Calculate workout streak
            streak_days = calculate_workout_streak(request.user, workouts)
            
            # Get completed scheduled workouts count
            completed_scheduled = ScheduledWorkout.objects.filter(
                user=request.user, 
                status='completed'
            ).count()
            
            # Total workouts includes both logged workouts and completed scheduled workouts
            total_workouts = workout_count + completed_scheduled
            
            # Get active goals
            goals = workout_info.get('goals', [])
            active_goals = [g for g in goals if g.get('progress', 0) < 100]
            active_goals_count = len(active_goals)
            
            # Get recent activity (combine workouts, goals, and weights)
            recent_activity = []
            
            # Add workouts to activity
            for workout in workouts[-10:]:  # Last 10 workouts
                recent_activity.append({
                    'type': 'workout',
                    'date': workout.get('date'),
                    'workout_type': workout.get('type'),
                    'details': workout.get('details')
                })
            
            # Add completed scheduled workouts to activity
            scheduled_workouts = ScheduledWorkout.objects.filter(
                user=request.user, 
                status='completed'
            ).order_by('-date')[:5]
            
            for workout in scheduled_workouts:
                recent_activity.append({
                    'type': 'scheduled_workout',
                    'date': workout.date.strftime('%Y-%m-%d'),
                    'title': workout.title,
                    'description': workout.description
                })
            
            # Add goals to activity
            for goal in goals[-5:]:  # Last 5 goals
                recent_activity.append({
                    'type': 'goal',
                    'date': goal.get('created_at'),
                    'title': goal.get('title'),
                    'progress': goal.get('progress', 0)
                })
            
            # Add weight entries to activity
            weight_entries = Weight.objects.filter(user=request.user).order_by('-date')[:5]
            for entry in weight_entries:
                recent_activity.append({
                    'type': 'weight',
                    'date': entry.date.strftime('%Y-%m-%d'),
                    'weight': entry.weight
                })
            
            # Sort by date (newest first) and limit to 10 items
            recent_activity.sort(key=lambda x: x.get('date', ''), reverse=True)
            recent_activity = recent_activity[:10]
            
            return JsonResponse({
                'success': True,
                'workout_count': total_workouts,
                'total_calories': total_calories,
                'streak_days': streak_days,
                'active_goals_count': active_goals_count,
                'goals': goals,
                'recent_activity': recent_activity
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def log_weight_api(request):
    """API endpoint for weight tracking operations.
    
    Handles both GET requests for retrieving weight history and POST requests
    for logging new weight entries. Uses update_or_create for data consistency.
    
    Args:
        request (HttpRequest): The HTTP request object with authenticated user.
        
    Returns:
        JsonResponse: Weight history data for GET, success status for POST.
                     Includes weight values as floats for chart precision.
    """
    if request.method == 'GET':
        try:
            # Get all weight entries for chart visualization
            weight_history = Weight.objects.filter(user=request.user).order_by('date')
            # Converting DecimalField to float for JSON serialization and chart compatibility
            weight_data = [{
                'date': entry.date.strftime('%Y-%m-%d'),  # ISO date format for consistency
                'weight': float(entry.weight),  # Explicit float conversion for charts
                'notes': entry.notes
            } for entry in weight_history]
            
            return JsonResponse({
                'success': True,
                'weight_history': weight_data
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    elif request.method == 'POST':
        data = json.loads(request.body)
        weight_value = data.get('weight')
        date_str = data.get('date')
        notes = data.get('notes', '')

        if not weight_value or not date_str:
            return JsonResponse({'success': False, 'error': 'Missing required fields'})

        try:
            # Converting to float for validation before storing as Decimal
            weight_value = float(weight_value)
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Using update_or_create to prevent duplicate entries per date
            # Ensures data consistency with unique_together constraint
            weight_entry, created = Weight.objects.update_or_create(
                user=request.user,
                date=date_obj,
                defaults={'weight': weight_value, 'notes': notes}
            )
            
            # Get all weight entries for chart
            weight_history = Weight.objects.filter(user=request.user).order_by('date')
            weight_data = [{
                'date': entry.date.strftime('%Y-%m-%d'),
                'weight': entry.weight,
                'notes': entry.notes
            } for entry in weight_history]
            
            return JsonResponse({
                'success': True,
                'weight_history': weight_data
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


@login_required
def rest_timer_view(request):
    """View for the rest timer page"""
    return render(request, 'home/rest_timer.html')


@login_required
def rest_timer_api(request):
    """API endpoint for managing user's rest timer configurations.
    
    Handles CRUD operations for rest timers, ensuring only one default timer
    per user and validating duration values for workout rest periods.
    
    Args:
        request (HttpRequest): The HTTP request object with authenticated user.
        
    Returns:
        JsonResponse: Timer data for GET, success status for POST/PUT/DELETE.
                     Duration stored as integer seconds for precise timing.
    """
    # GET request - return all timers for the user
    if request.method == 'GET':
        timers = RestTimer.objects.filter(user=request.user)
        # Converting model fields to JSON-serializable format
        timer_data = [{
            'id': timer.id,
            'name': timer.name,
            'duration': timer.duration,  # Integer seconds for precise timing
            'is_default': timer.is_default
        } for timer in timers]
        
        return JsonResponse({
            'success': True,
            'timers': timer_data
        })
    
    # POST request - create a new timer
    elif request.method == 'POST':
        data = json.loads(request.body)
        name = data.get('name')
        duration = data.get('duration')
        is_default = data.get('is_default', False)
        
        if not name or not duration or duration <= 0:
            return JsonResponse({
                'success': False,
                'error': 'Invalid timer data'
            })
        
        # Ensuring only one default timer per user for consistent UX
        if is_default:
            RestTimer.objects.filter(user=request.user, is_default=True).update(is_default=False)
        
        # Create the new timer with validated data
        timer = RestTimer.objects.create(
            user=request.user,
            name=name,
            duration=duration,  # Stored as integer seconds
            is_default=is_default
        )
        
        return JsonResponse({
            'success': True,
            'timer': {
                'id': timer.id,
                'name': timer.name,
                'duration': timer.duration,
                'is_default': timer.is_default
            }
        })
    
    # Invalid method
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    })


@login_required
def rest_timer_detail_api(request, timer_id):
    """API for managing a specific rest timer"""
    try:
        timer = RestTimer.objects.get(id=timer_id, user=request.user)
    except RestTimer.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Timer not found'
        })
    
    # GET request - return timer details
    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'timer': {
                'id': timer.id,
                'name': timer.name,
                'duration': timer.duration,
                'is_default': timer.is_default
            }
        })
    
    # PUT request - update timer
    elif request.method == 'PUT':
        data = json.loads(request.body)
        name = data.get('name')
        duration = data.get('duration')
        is_default = data.get('is_default', False)
        
        if not name or not duration or duration <= 0:
            return JsonResponse({
                'success': False,
                'error': 'Invalid timer data'
            })
        
        # If this timer is set as default, unset any existing default
        if is_default and not timer.is_default:
            RestTimer.objects.filter(user=request.user, is_default=True).update(is_default=False)
        
        # Update the timer
        timer.name = name
        timer.duration = duration
        timer.is_default = is_default
        timer.save()
        
        return JsonResponse({
            'success': True,
            'timer': {
                'id': timer.id,
                'name': timer.name,
                'duration': timer.duration,
                'is_default': timer.is_default
            }
        })
    
    # DELETE request - delete timer
    elif request.method == 'DELETE':
        timer.delete()
        return JsonResponse({
            'success': True
        })
    
    # Invalid method
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    })

@login_required
def rest_timer_view(request):
    """View function for the rest timer page"""
    return render(request, 'home/rest_timer.html')

@login_required
def rest_timer_api(request):
    """API endpoint for rest timer operations"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name', 'Custom Timer')
            duration = data.get('duration')
            is_default = data.get('is_default', False)
            
            if not duration:
                return JsonResponse({'success': False, 'error': 'Duration is required'})
                
            # If this timer is set as default, unset any other defaults
            if is_default:
                RestTimer.objects.filter(user=request.user, is_default=True).update(is_default=False)
                
            timer = RestTimer.objects.create(
                user=request.user,
                name=name,
                duration=duration,
                is_default=is_default
            )
            
            return JsonResponse({
                'success': True,
                'timer': {
                    'id': timer.id,
                    'name': timer.name,
                    'duration': timer.duration,
                    'is_default': timer.is_default
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
            
    elif request.method == 'GET':
        try:
            timers = RestTimer.objects.filter(user=request.user).order_by('-is_default', 'name')
            timer_data = [{
                'id': timer.id,
                'name': timer.name,
                'duration': timer.duration,
                'is_default': timer.is_default
            } for timer in timers]
            
            return JsonResponse({'success': True, 'timers': timer_data})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def rest_timer_detail_api(request, timer_id):
    """API endpoint for operations on a specific timer"""
    try:
        timer = get_object_or_404(RestTimer, id=timer_id, user=request.user)
        
        if request.method == 'GET':
            return JsonResponse({
                'success': True,
                'timer': {
                    'id': timer.id,
                    'name': timer.name,
                    'duration': timer.duration,
                    'is_default': timer.is_default
                }
            })
            
        elif request.method == 'PUT':
            data = json.loads(request.body)
            name = data.get('name')
            duration = data.get('duration')
            is_default = data.get('is_default')
            
            if name:
                timer.name = name
            if duration:
                timer.duration = duration
            if is_default is not None:
                if is_default:
                    # Unset any other defaults
                    RestTimer.objects.filter(user=request.user, is_default=True).update(is_default=False)
                timer.is_default = is_default
                
            timer.save()
            
            return JsonResponse({
                'success': True,
                'timer': {
                    'id': timer.id,
                    'name': timer.name,
                    'duration': timer.duration,
                    'is_default': timer.is_default
                }
            })
            
        elif request.method == 'DELETE':
            timer.delete()
            return JsonResponse({'success': True})
            
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def progress_photos_view(request):
    """View function for the progress photos page"""
    return render(request, 'home/progress_photos.html')

@login_required
def progress_photo_api(request):
    """API endpoint for progress photo upload and retrieval operations.
    
    Handles multipart form data for image uploads with optional metadata.
    Uses ImageField for automatic file handling and validation.
    
    Args:
        request (HttpRequest): The HTTP request object with authenticated user.
        
    Returns:
        JsonResponse: Photo data with image URLs for GET, success status for POST.
                     Weight stored as DecimalField for precision, converted to float for JSON.
    """
    if request.method == 'POST':
        try:
            # Using request.FILES for multipart form data handling
            image = request.FILES.get('photo')
            date_str = request.POST.get('date')
            notes = request.POST.get('notes', '')
            weight = request.POST.get('weight', None)
            
            if not image:
                return JsonResponse({'success': False, 'error': 'Photo is required'})
                
            # Default to current date if not provided for user convenience
            if not date_str:
                date_str = timezone.now().strftime('%Y-%m-%d')
                
            # Converting string date to DateField format
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Creating ProgressPhoto with ImageField handling file upload automatically
            photo = ProgressPhoto.objects.create(
                user=request.user,
                image=image,  # ImageField handles file storage and validation
                date=date,
                notes=notes,
                weight=weight  # Optional DecimalField for precise weight tracking
            )
            
            return JsonResponse({
                'success': True,
                'photo': {
                    'id': photo.id,
                    'image_url': photo.image.url,
                    'date': photo.date.strftime('%Y-%m-%d'),
                    'notes': photo.notes,
                    'weight': photo.weight
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
            
    elif request.method == 'GET':
        try:
            photos = ProgressPhoto.objects.filter(user=request.user).order_by('-date')
            photo_data = [{
                'id': photo.id,
                'image_url': photo.image.url,
                'date': photo.date.strftime('%Y-%m-%d'),
                'notes': photo.notes,
                'weight': photo.weight
            } for photo in photos]
            
            return JsonResponse({'success': True, 'photos': photo_data})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def progress_photo_detail_api(request, photo_id):
    """API endpoint for operations on a specific photo"""
    try:
        photo = get_object_or_404(ProgressPhoto, id=photo_id, user=request.user)
        
        if request.method == 'GET':
            return JsonResponse({
                'success': True,
                'photo': {
                    'id': photo.id,
                    'image_url': photo.image.url,
                    'date': photo.date.strftime('%Y-%m-%d'),
                    'notes': photo.notes,
                    'weight': photo.weight
                }
            })
            
        elif request.method == 'PUT':
            date_str = request.POST.get('date')
            notes = request.POST.get('notes')
            weight = request.POST.get('weight')
            image = request.FILES.get('image')
            
            if date_str:
                photo.date = datetime.strptime(date_str, '%Y-%m-%d').date()
            if notes is not None:
                photo.notes = notes
            if weight is not None:
                photo.weight = weight
            if image:
                photo.image = image
                
            photo.save()
            
            return JsonResponse({
                'success': True,
                'photo': {
                    'id': photo.id,
                    'image_url': photo.image.url,
                    'date': photo.date.strftime('%Y-%m-%d'),
                    'notes': photo.notes,
                    'weight': photo.weight
                }
            })
            
        elif request.method == 'DELETE':
            photo.delete()
            return JsonResponse({'success': True})
            
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def export_progress_view(request):
    """View function for the export progress page"""
    return render(request, 'home/export_progress.html')

@login_required
def export_workout_csv(request):
    """Export workout data as CSV file for data portability.
    
    Extracts workout data from JSONField storage and formats it as CSV
    for external analysis or backup purposes.
    
    Args:
        request (HttpRequest): The HTTP request object with authenticated user.
        
    Returns:
        HttpResponse: CSV file download with workout history data.
                     Uses text/csv content type for proper browser handling.
    """
    try:
        # Setting proper content type and filename for CSV download
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="workout_history.csv"'
        
        writer = csv.writer(response)
        # CSV header row for structured data export
        writer.writerow(['Date', 'Exercise', 'Sets', 'Reps', 'Weight', 'Notes'])
        
        # Extracting workout data from JSONField for flexible data structure
        profile = Profile.objects.get(user=request.user)
        workout_info = profile.workout_info
        
        # Safe access to JSONField data with existence checks
        if 'workouts' in workout_info and workout_info['workouts']:
            for workout in workout_info['workouts']:
                # Using .get() for safe access to optional JSON keys
                writer.writerow([
                    workout.get('date', ''),
                    workout.get('exercise', ''),
                    workout.get('sets', ''),
                    workout.get('reps', ''),
                    workout.get('weight', ''),
                    workout.get('notes', '')
                ])
            
        return response
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def export_weight_csv(request):
    """Export weight data as CSV"""
    try:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="weight_history.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Weight', 'Notes'])
        
        weights = Weight.objects.filter(user=request.user).order_by('-date')
        for weight in weights:
            writer.writerow([
                weight.date.strftime('%Y-%m-%d'),
                weight.weight,
                weight.notes
            ])
            
        return response
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def export_workout_pdf(request):
    """Export workout data as PDF"""
    # This is a placeholder - PDF generation would require additional libraries
    return JsonResponse({'success': False, 'error': 'PDF export not yet implemented'})

@login_required
def export_weight_pdf(request):
    """Export weight data as PDF"""
    # This is a placeholder - PDF generation would require additional libraries
    return JsonResponse({'success': False, 'error': 'PDF export not yet implemented'})

@login_required
def ai_coach_view(request):
    """View function for the AI coach page"""
    return render(request, 'home/ai_coach.html')

@login_required
def ai_coach_api(request):
    """API endpoint for AI coach operations"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            question = data.get('question')
            
            if not question:
                return JsonResponse({'success': False, 'error': 'Question is required'})
                
            # Generate personalized AI response based on user data and question
            answer = generate_ai_response(question, request.user)
            
            # Save the question and answer
            ai_question = AICoachQuestion.objects.create(
                user=request.user,
                question=question,
                answer=answer
            )
            
            return JsonResponse({
                'success': True,
                'response': {
                    'id': ai_question.id,
                    'question': ai_question.question,
                    'answer': ai_question.answer,
                    'created_at': ai_question.created_at.strftime('%Y-%m-%d %H:%M:%S')
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
            
    elif request.method == 'GET':
        try:
            # Return the user's question history
            questions = AICoachQuestion.objects.filter(user=request.user).order_by('-created_at')
            question_data = [{
                'id': q.id,
                'question': q.question,
                'answer': q.answer,
                'created_at': q.created_at.strftime('%Y-%m-%d %H:%M:%S')
            } for q in questions]
            
            return JsonResponse({'success': True, 'history': question_data})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def ai_coach_question_api(request, question_id):
    """API endpoint for specific AI Coach questions"""
    try:
        question = get_object_or_404(AICoachQuestion, id=question_id, user=request.user)
        
        if request.method == 'GET':
            return JsonResponse({
                'success': True,
                'question': question.question,
                'answer': question.answer,
                'created_at': question.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        elif request.method == 'DELETE':
            question.delete()
            return JsonResponse({'success': True, 'message': 'Question deleted successfully'})
        else:
            return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def generate_ai_response(question, user=None):
    """Generate a comprehensive response to a fitness question with personalization"""
    question_lower = question.lower()
    
    # Get user context if available
    user_context = get_user_fitness_context(user) if user else {}
    
    # Weight Loss Questions
    if any(keyword in question_lower for keyword in ['weight loss', 'lose weight', 'fat loss', 'cutting']):
        response = "**Weight Loss Strategy:**\n\n"
        response += "• **Calorie Deficit**: Aim for 300-500 calories below maintenance (1-2 lbs/week loss)\n"
        response += "• **Nutrition**: Focus on protein (0.8-1g per lb bodyweight), vegetables, and whole foods\n"
        response += "• **Exercise**: Combine strength training (3-4x/week) with cardio (150+ min/week)\n"
        response += "• **Hydration**: Drink at least 8-10 glasses of water daily\n\n"
        
        if user_context.get('current_weight'):
            response += f"Based on your current weight of {user_context['current_weight']}kg, "
            response += "focus on gradual, sustainable changes rather than extreme restrictions.\n\n"
        
        response += "**Pro Tips**: Track your food intake, prioritize sleep (7-9 hours), and be patient with the process!"
        return response
    
    # Muscle Building Questions
    elif any(keyword in question_lower for keyword in ['muscle', 'strength', 'build', 'gain', 'bulk', 'hypertrophy']):
        response = "**Muscle Building Guide:**\n\n"
        response += "• **Progressive Overload**: Gradually increase weight, reps, or sets each week\n"
        response += "• **Protein**: 1.6-2.2g per kg bodyweight daily (spread across meals)\n"
        response += "• **Training**: 3-5 strength sessions/week, 6-20 reps per set\n"
        response += "• **Recovery**: 48-72 hours rest between training same muscle groups\n"
        response += "• **Calories**: Slight surplus (200-500 calories above maintenance)\n\n"
        
        if user_context.get('workout_count', 0) > 0:
            response += f"Great job on completing {user_context['workout_count']} workouts! "
            response += "Consistency is key for muscle growth.\n\n"
        
        response += "**Key Exercises**: Squats, deadlifts, bench press, rows, overhead press, and pull-ups form the foundation."
        return response
    
    # Cardio and Endurance Questions
    elif any(keyword in question_lower for keyword in ['cardio', 'running', 'endurance', 'stamina', 'conditioning']):
        response = "**Cardiovascular Training Plan:**\n\n"
        response += "• **HIIT**: 2-3 sessions/week (20-30 minutes) for efficiency\n"
        response += "• **Steady State**: 2-3 sessions/week (30-60 minutes) at moderate intensity\n"
        response += "• **Progression**: Increase duration by 10% weekly, intensity gradually\n"
        response += "• **Variety**: Mix running, cycling, swimming, rowing to prevent boredom\n\n"
        
        if user_context.get('streak_days', 0) > 0:
            response += f"Your {user_context['streak_days']}-day workout streak shows great dedication! "
            response += "This consistency will pay off in improved endurance.\n\n"
        
        response += "**Heart Rate Zones**: 60-70% max HR for fat burning, 70-85% for aerobic improvement, 85%+ for anaerobic power."
        return response
    
    # Nutrition Questions
    elif any(keyword in question_lower for keyword in ['nutrition', 'diet', 'eat', 'food', 'meal', 'calories']):
        response = "**Nutrition Fundamentals:**\n\n"
        response += "• **Macronutrients**: 45-65% carbs, 20-35% fats, 10-35% protein\n"
        response += "• **Meal Timing**: Eat protein within 2 hours post-workout\n"
        response += "• **Hydration**: Half your body weight in ounces of water daily\n"
        response += "• **Whole Foods**: Prioritize minimally processed options\n\n"
        response += "**Sample Day**: Oatmeal + berries (breakfast), chicken + rice + vegetables (lunch), "
        response += "salmon + sweet potato + salad (dinner), Greek yogurt + nuts (snacks)\n\n"
        response += "**Supplements**: Consider whey protein, creatine, and vitamin D after consulting a healthcare provider."
        return response
    
    # Form and Technique Questions
    elif any(keyword in question_lower for keyword in ['form', 'technique', 'squat', 'deadlift', 'bench', 'press']):
        response = "**Exercise Form Guidelines:**\n\n"
        if 'squat' in question_lower:
            response += "**Squat Form:**\n• Feet shoulder-width apart, toes slightly out\n"
            response += "• Keep chest up, core tight, knees track over toes\n"
            response += "• Descend until thighs parallel to floor\n• Drive through heels to stand\n\n"
        elif 'deadlift' in question_lower:
            response += "**Deadlift Form:**\n• Bar over mid-foot, shins close to bar\n"
            response += "• Neutral spine, chest up, shoulders back\n"
            response += "• Drive through heels, hips and shoulders rise together\n• Finish with hips forward, shoulders back\n\n"
        elif 'bench' in question_lower:
            response += "**Bench Press Form:**\n• Retract shoulder blades, arch back slightly\n"
            response += "• Grip bar slightly wider than shoulders\n"
            response += "• Lower bar to chest with control\n• Press up in straight line\n\n"
        
        response += "**General Tips**: Start with bodyweight or light weights, focus on movement quality over quantity, "
        response += "and consider working with a trainer initially."
        return response
    
    # Recovery and Rest Questions
    elif any(keyword in question_lower for keyword in ['recovery', 'rest', 'sleep', 'sore', 'tired']):
        response = "**Recovery Optimization:**\n\n"
        response += "• **Sleep**: 7-9 hours nightly for muscle repair and hormone regulation\n"
        response += "• **Active Recovery**: Light walking, stretching, or yoga on rest days\n"
        response += "• **Nutrition**: Post-workout protein + carbs within 2 hours\n"
        response += "• **Hydration**: Adequate water intake supports recovery processes\n"
        response += "• **Stress Management**: Meditation, deep breathing, or relaxing activities\n\n"
        response += "**Signs of Overtraining**: Persistent fatigue, declining performance, mood changes, frequent illness. "
        response += "Take extra rest days if experiencing these symptoms."
        return response
    
    # Motivation and Consistency Questions
    elif any(keyword in question_lower for keyword in ['motivation', 'habit', 'consistent', 'discipline', 'routine']):
        response = "**Building Lasting Fitness Habits:**\n\n"
        response += "• **Start Small**: Begin with 2-3 workouts per week, 20-30 minutes each\n"
        response += "• **Schedule It**: Treat workouts like important appointments\n"
        response += "• **Track Progress**: Log workouts, measurements, and how you feel\n"
        response += "• **Find Enjoyment**: Choose activities you actually like doing\n"
        response += "• **Accountability**: Workout partner, trainer, or fitness community\n\n"
        
        if user_context.get('streak_days', 0) > 0:
            response += f"You're already building momentum with your {user_context['streak_days']}-day streak! "
            response += "Keep this consistency going.\n\n"
        
        response += "**Mindset Shift**: Focus on becoming the type of person who exercises regularly, not just on outcomes."
        return response
    
    # Injury Prevention and Management
    elif any(keyword in question_lower for keyword in ['injury', 'pain', 'hurt', 'prevent']):
        response = "**Injury Prevention & Management:**\n\n"
        response += "• **Warm-Up**: 5-10 minutes of light cardio + dynamic stretching\n"
        response += "• **Cool-Down**: 5-10 minutes of static stretching post-workout\n"
        response += "• **Progressive Loading**: Gradually increase intensity and volume\n"
        response += "• **Listen to Your Body**: Distinguish between muscle fatigue and pain\n\n"
        response += "**For Current Pain**: RICE method (Rest, Ice, Compression, Elevation) for acute injuries. "
        response += "If pain persists >48 hours or is severe, consult a healthcare professional.\n\n"
        response += "**Red Flags**: Sharp pain, joint pain, numbness, or pain that worsens with movement requires medical attention."
        return response
    
    # Beginner Questions
    elif any(keyword in question_lower for keyword in ['beginner', 'start', 'new', 'first time']):
        response = "**Beginner's Fitness Roadmap:**\n\n"
        response += "• **Week 1-2**: Focus on movement patterns with bodyweight exercises\n"
        response += "• **Week 3-4**: Add light weights, learn proper form\n"
        response += "• **Week 5-8**: Gradually increase intensity and complexity\n"
        response += "• **Frequency**: Start with 2-3 days/week, progress to 4-5 days\n\n"
        response += "**Essential Movements**: Squat, hinge (deadlift), push, pull, carry, and core work\n\n"
        response += "**First Month Goals**: Establish routine, learn proper form, build base fitness level. "
        response += "Don't worry about heavy weights yet!"
        return response
    
    # Default comprehensive response
    else:
        response = "**Personalized Fitness Guidance:**\n\n"
        
        if user_context.get('workout_count', 0) > 0:
            response += f"Based on your {user_context['workout_count']} completed workouts, you're making great progress! "
        
        response += "For the most effective fitness journey:\n\n"
        response += "• **Consistency** beats perfection - aim for regular, sustainable habits\n"
        response += "• **Progressive Overload** - gradually challenge yourself over time\n"
        response += "• **Recovery** is when adaptation happens - prioritize sleep and rest\n"
        response += "• **Nutrition** fuels your workouts and recovery\n"
        response += "• **Patience** - meaningful changes take 4-12 weeks to become noticeable\n\n"
        response += "Feel free to ask more specific questions about training, nutrition, or recovery for detailed guidance!"
        return response

def get_user_fitness_context(user):
    """Get user's fitness context for personalized responses"""
    if not user:
        return {}
    
    try:
        profile = user.profile
        context = {}
        
        # Get current weight
        latest_weight = Weight.objects.filter(user=user).order_by('-date').first()
        if latest_weight:
            context['current_weight'] = latest_weight.weight
        
        # Get workout count
        workout_count = Journal.objects.filter(user=user).count()
        scheduled_workouts = ScheduledWorkout.objects.filter(user=user, status='completed').count()
        context['workout_count'] = workout_count + scheduled_workouts
        
        # Get streak days
        workouts = list(Journal.objects.filter(user=user).values('date', 'workout_type'))
        context['streak_days'] = calculate_workout_streak(user, workouts)
        
        # Get personal bests count
        pb_count = PersonalBest.objects.filter(user=user, is_current=True).count()
        context['personal_bests'] = pb_count
        
        return context
    except Exception as e:
        return {}

@login_required
def personal_best_progress_api(request):
    """API endpoint for personal best progress chart data"""
    try:
        exercise = request.GET.get('exercise', 'all')
        
        if exercise == 'all':
            # Get all exercises with their progress over time
            personal_bests = PersonalBest.objects.filter(
                user=request.user
            ).order_by('date_achieved')
            
            # Group by exercise and create time series
            exercise_data = {}
            for pb in personal_bests:
                if pb.exercise not in exercise_data:
                    exercise_data[pb.exercise] = []
                exercise_data[pb.exercise].append({
                    'date': pb.date_achieved.strftime('%b %Y'),
                    'weight': float(pb.weight) if pb.weight else 0
                })
            
            # Format for Chart.js
            datasets = []
            colors = ['#51cf66', '#339af0', '#ff6b6b', '#ffd43b', '#9775fa']
            color_index = 0
            
            for exercise_name, data in exercise_data.items():
                datasets.append({
                    'label': exercise_name.replace('_', ' ').title(),
                    'data': [item['weight'] for item in data],
                    'borderColor': colors[color_index % len(colors)],
                    'backgroundColor': colors[color_index % len(colors)] + '20',
                    'tension': 0.4
                })
                color_index += 1
            
            # Use dates from first exercise or create default labels
            labels = []
            if exercise_data:
                first_exercise = list(exercise_data.values())[0]
                labels = [item['date'] for item in first_exercise]
            
            if not labels:
                labels = ['No data']
                datasets = [{'label': 'No data', 'data': [0], 'borderColor': '#e9ecef'}]
            
        else:
            # Get specific exercise progress
            personal_bests = PersonalBest.objects.filter(
                user=request.user,
                exercise=exercise
            ).order_by('date_achieved')
            
            labels = [pb.date_achieved.strftime('%b %Y') for pb in personal_bests]
            data = [float(pb.weight) if pb.weight else 0 for pb in personal_bests]
            
            if not labels:
                labels = ['No data']
                data = [0]
            
            datasets = [{
                'label': exercise.replace('_', ' ').title(),
                'data': data,
                'borderColor': '#51cf66',
                'backgroundColor': 'rgba(81, 207, 102, 0.1)',
                'tension': 0.4
            }]
        
        return JsonResponse({
            'labels': labels,
            'datasets': datasets
        })
        
    except Exception as e:
        return JsonResponse({
            'labels': ['No data'],
            'datasets': [{'label': 'No data', 'data': [0], 'borderColor': '#e9ecef'}]
        })

@login_required
def weight_progress_api(request):
    """API endpoint for weight progress chart data"""
    try:
        period = request.GET.get('period', '6months')
        
        # Calculate date range based on period
        end_date = timezone.now().date()
        if period == '3months':
            start_date = end_date - timedelta(days=90)
        elif period == '1year':
            start_date = end_date - timedelta(days=365)
        else:  # 6months default
            start_date = end_date - timedelta(days=180)
        
        # Get weight entries in the date range
        weight_entries = Weight.objects.filter(
            user=request.user,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')
        
        labels = []
        actual_weights = []
        target_weights = []
        target_weight = 65  # Target weight goal
        
        if weight_entries.exists():
            for entry in weight_entries:
                labels.append(entry.date.strftime('%b %d'))
                actual_weights.append(float(entry.weight))
                target_weights.append(target_weight)
        else:
            # No data available
            labels = ['No data']
            actual_weights = [0]
            target_weights = [target_weight]
        
        # Calculate current weight and progress
        current_weight = actual_weights[-1] if actual_weights else 0
        progress = current_weight - target_weight if current_weight > 0 else 0
        
        return JsonResponse({
            'labels': labels,
            'actualWeight': actual_weights,
            'targetWeight': target_weights,
            'currentWeight': current_weight,
            'progress': progress,
            'targetWeight': target_weight
        })
        
    except Exception as e:
        return JsonResponse({
            'labels': ['No data'],
            'actualWeight': [0],
            'targetWeight': [65],
            'currentWeight': 0,
            'progress': 0,
            'targetWeight': 65
        })

@login_required
def performance_metrics_api(request):
    """API endpoint for performance metrics data"""
    try:
        profile = Profile.objects.get(user=request.user)
        workout_info = profile.workout_info
        workouts = workout_info.get('workouts', [])
        
        # Calculate total workouts
        total_workouts = len(workouts)
        
        # Calculate total training time (estimate 45 minutes per workout)
        total_training_hours = int(total_workouts * 0.75)  # 45 minutes = 0.75 hours
        
        # Calculate total calories burned
        total_calories = 0
        for workout in workouts:
            # Simple calorie estimation: 400 calories per workout on average
            workout_calories = 400
            total_calories += workout_calories
        total_calories = int(total_calories)
        
        # Get personal bests count
        personal_bests_count = PersonalBest.objects.filter(user=request.user).count()
        
        # Calculate monthly changes (last 30 days vs previous 30 days)
        from datetime import datetime, timedelta
        now = datetime.now()
        last_month = now - timedelta(days=30)
        prev_month = now - timedelta(days=60)
        
        # Recent workouts (last 30 days)
        recent_workouts = [w for w in workouts if datetime.strptime(w.get('date', '2024-01-01'), '%Y-%m-%d') >= last_month]
        prev_workouts = [w for w in workouts if prev_month <= datetime.strptime(w.get('date', '2024-01-01'), '%Y-%m-%d') < last_month]
        
        # Recent personal bests (last 30 days)
        recent_pbs = PersonalBest.objects.filter(
            user=request.user,
            date_achieved__gte=last_month
        ).count()
        
        prev_pbs = PersonalBest.objects.filter(
            user=request.user,
            date_achieved__gte=prev_month,
            date_achieved__lt=last_month
        ).count()
        
        # Calculate changes
        workout_change = len(recent_workouts) - len(prev_workouts)
        time_change = int(len(recent_workouts) * 0.75) - int(len(prev_workouts) * 0.75)
        
        # Calculate recent calories
        recent_calories = 0
        for workout in recent_workouts:
            sets = int(workout.get('sets', 0))
            reps = int(workout.get('reps', 0))
            weight = float(workout.get('weight', 0))
            workout_calories = (sets * reps * weight * 0.05) + 200
            recent_calories += min(workout_calories, 600)
        
        prev_calories = 0
        for workout in prev_workouts:
            sets = int(workout.get('sets', 0))
            reps = int(workout.get('reps', 0))
            weight = float(workout.get('weight', 0))
            workout_calories = (sets * reps * weight * 0.05) + 200
            prev_calories += min(workout_calories, 600)
        
        calorie_change = int(recent_calories - prev_calories)
        pb_change = recent_pbs - prev_pbs
        
        return JsonResponse({
            'totalWorkouts': total_workouts,
            'trainingTime': f'{total_training_hours}h',
            'caloriesBurned': f'{total_calories:,}',
            'personalBests': personal_bests_count,
            'changes': {
                'workouts': workout_change,
                'time': time_change,
                'calories': calorie_change,
                'personalBests': pb_change
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'totalWorkouts': 0,
            'trainingTime': '0h',
            'caloriesBurned': '0',
            'personalBests': 0,
            'changes': {
                'workouts': 0,
                'time': 0,
                'calories': 0,
                'personalBests': 0
            }
        })
