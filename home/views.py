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
from django.contrib.auth import logout
from datetime import datetime, timedelta
import csv
import os
from django.conf import settings
from django.http import FileResponse
from django.utils import timezone


def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('home')


@login_required
def workout_view(request):
    workout_info = Profile.objects.get(user=request.user).workout_info
    if 'workouts' not in workout_info:
        workout_info["workouts"] = []
    context = {"workout_info": workout_info["workouts"]}
    return render(request, 'home/workout.html', context=context)


@login_required
def log_workout_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        exercise = data.get('exercise')
        sets = data.get('sets')
        reps = data.get('reps')
        weight = data.get('weight')
        date = data.get('date')

        if not all([exercise, sets, reps, weight]):
            return JsonResponse({'success': False, 'error': 'Missing required fields'})

        profile = Profile.objects.get(user=request.user)
        workout_info = profile.workout_info

        if 'workouts' not in workout_info:
            workout_info['workouts'] = []

        workout_entry = {
            'exercise': exercise,
            'sets': sets,
            'reps': reps,
            'weight': weight,
            'date': date or datetime.now().strftime('%Y-%m-%d')
        }

        workout_info['workouts'].append(workout_entry)

        profile.workout_info = workout_info
        profile.save()

        return JsonResponse({'success': True, 'workout': workout_entry})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def calendar_view(request):
    return render(request, 'home/calendar.html', {'page_title': 'Workout Calendar'})

@login_required
def scheduled_workout_api(request):
    if request.method == 'GET':
        # Get all scheduled workouts for the user
        try:
            workouts = ScheduledWorkout.objects.filter(user=request.user).order_by('date')
            workout_data = [{
                'id': workout.id,
                'title': workout.title,
                'description': workout.description,
                'date': workout.date.strftime('%Y-%m-%d'),
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
        status = data.get('status', 'planned')
        notes = data.get('notes', '')
        
        if not title or not date_str:
            return JsonResponse({'success': False, 'error': 'Missing required fields'})
        
        try:
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
    return render(request, 'home/personal_bests.html', {'page_title': 'Personal Bests'})

@login_required
def personal_best_api(request):
    if request.method == 'GET':
        # Get all personal bests for the user
        try:
            prs = PersonalBest.objects.filter(user=request.user, is_current=True).order_by('exercise')
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
    return render(request, 'home/journal.html', {'page_title': 'Workout Journal'})

@login_required
def journal_api(request):
    if request.method == 'GET':
        # Get all journal entries for the user
        try:
            entries = Journal.objects.filter(user=request.user).order_by('-date')
            entry_data = [{
                'id': entry.id,
                'title': entry.title,
                'content': entry.content,
                'date': entry.date.strftime('%Y-%m-%d'),
                'mood': entry.mood,
                'created_at': entry.created_at.strftime('%Y-%m-%d %H:%M:%S')
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
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
            )
            profile, created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'dob': form.cleaned_data['dob']
                }
            )
            messages.success(request, "Registration successful. You can now log in.")
            return redirect('login')  # or any other page
    else:
        form = RegisterForm()
    return render(request, 'home/register.html', {'form': form})

@login_required
def log_goal_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        title = data.get('title')
        details = data.get('details')
        target_date = data.get('target_date')

        if not title:
            return JsonResponse({'success': False, 'error': 'Missing required fields'})

        profile = Profile.objects.get(user=request.user)
        workout_info = profile.workout_info

        if 'goals' not in workout_info:
            workout_info['goals'] = []

        goal_entry = {
            'title': title,
            'details': details or '',
            'target_date': target_date,
            'progress': 0,  # Initial progress is 0%
            'created_at': datetime.now().strftime('%Y-%m-%d')
        }

        workout_info['goals'].append(goal_entry)

        profile.workout_info = workout_info
        profile.save()

        return JsonResponse({'success': True, 'goal': goal_entry})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def goal_view(request):
    workout_info = Profile.objects.get(user=request.user).workout_info
    if 'goals' not in workout_info:
        workout_info["goals"] = []
    context = {"goals": workout_info["goals"]}
    return render(request, 'home/goals.html', context=context)

@login_required
def weight_tracker_view(request):
    return render(request, 'home/weight_tracker.html')

@login_required
def dashboard_view(request):
    return render(request, 'home/dashboard.html')

@login_required
def dashboard_data_api(request):
    if request.method == 'GET':
        try:
            profile = Profile.objects.get(user=request.user)
            workout_info = profile.workout_info
            
            # Get workout count
            workout_count = len(workout_info.get('workouts', []))
            
            # Get active goals
            goals = workout_info.get('goals', [])
            active_goals = [g for g in goals if g.get('progress', 0) < 100]
            active_goals_count = len(active_goals)
            
            # Get recent activity (combine workouts, goals, and weights)
            recent_activity = []
            
            # Add workouts to activity
            for workout in workout_info.get('workouts', []):
                recent_activity.append({
                    'type': 'workout',
                    'date': workout.get('date'),
                    'exercise': workout.get('exercise'),
                    'sets': workout.get('sets'),
                    'reps': workout.get('reps'),
                    'weight': workout.get('weight')
                })
            
            # Add goals to activity
            for goal in workout_info.get('goals', []):
                recent_activity.append({
                    'type': 'goal',
                    'date': goal.get('created_at'),
                    'title': goal.get('title'),
                    'progress': goal.get('progress', 0)
                })
            
            # Add weight entries to activity
            weight_entries = Weight.objects.filter(user=request.user).order_by('-date')[:10]
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
                'workout_count': workout_count,
                'active_goals_count': active_goals_count,
                'goals': goals,
                'recent_activity': recent_activity
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def log_weight_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        weight_value = data.get('weight')
        date_str = data.get('date')
        notes = data.get('notes', '')

        if not weight_value or not date_str:
            return JsonResponse({'success': False, 'error': 'Missing required fields'})

        try:
            weight_value = float(weight_value)
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Check if entry for this date already exists
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
    """API for managing rest timers"""
    # GET request - return all timers for the user
    if request.method == 'GET':
        timers = RestTimer.objects.filter(user=request.user)
        timer_data = [{
            'id': timer.id,
            'name': timer.name,
            'duration': timer.duration,
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
        
        # If this timer is set as default, unset any existing default
        if is_default:
            RestTimer.objects.filter(user=request.user, is_default=True).update(is_default=False)
        
        # Create the new timer
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
    """API endpoint for progress photo operations"""
    if request.method == 'POST':
        try:
            image = request.FILES.get('image')
            date_str = request.POST.get('date')
            notes = request.POST.get('notes', '')
            weight = request.POST.get('weight', None)
            
            if not image:
                return JsonResponse({'success': False, 'error': 'Image is required'})
                
            if not date_str:
                date_str = timezone.now().strftime('%Y-%m-%d')
                
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            photo = ProgressPhoto.objects.create(
                user=request.user,
                image=image,
                date=date,
                notes=notes,
                weight=weight
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
    """Export workout data as CSV"""
    try:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="workout_history.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Exercise', 'Sets', 'Reps', 'Weight', 'Notes'])
        
        # Get workout data from Profile.workout_info
        profile = Profile.objects.get(user=request.user)
        workout_info = profile.workout_info
        
        if 'workouts' in workout_info and workout_info['workouts']:
            for workout in workout_info['workouts']:
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
                
            # This is a placeholder - in a real implementation, you would call an AI API
            # For now, we'll just provide some canned responses based on keywords
            answer = generate_ai_response(question)
            
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

def generate_ai_response(question):
    """Generate a response to a fitness question"""
    question = question.lower()
    
    if 'weight loss' in question or 'lose weight' in question:
        return "Weight loss is primarily about calorie deficit. Focus on a balanced diet with plenty of protein and vegetables, and combine cardio with strength training for best results."
    elif 'muscle' in question or 'strength' in question or 'build' in question:
        return "Building muscle requires progressive overload (gradually increasing weight), adequate protein intake (1.6-2.2g per kg of bodyweight), and sufficient recovery time between workouts."
    elif 'cardio' in question or 'running' in question or 'endurance' in question:
        return "To improve cardiovascular fitness, mix high-intensity interval training (HIIT) with steady-state cardio. Gradually increase duration and intensity over time."
    elif 'nutrition' in question or 'diet' in question or 'eat' in question:
        return "Focus on whole foods, adequate protein, fruits, vegetables, and healthy fats. Portion control is key, and hydration is often overlooked but crucial."
    elif 'injury' in question or 'pain' in question or 'hurt' in question:
        return "For injuries, remember RICE: Rest, Ice, Compression, Elevation. If pain persists, consult a healthcare professional. Don't push through sharp pain."
    elif 'motivation' in question or 'habit' in question or 'consistent' in question:
        return "Build consistency by starting small, setting specific goals, tracking progress, and finding activities you enjoy. Consider a workout buddy or coach for accountability."
    else:
        return "That's a great fitness question! For personalized advice, consider consulting with a certified fitness professional who can tailor recommendations to your specific situation."
