# Debugging Logs

This document contains documented debugging scenarios encountered during the development of the Gym Tracker application, along with their solutions and lessons learned.

## Scenario 1: JSONField Data Corruption Issue

### Problem Description
**Date:** 2024-01-15  
**Severity:** High  
**Component:** Profile Model - workout_info JSONField

**Issue:** Users reported that their workout data was occasionally being lost or corrupted, with some workouts showing as `null` or empty objects in the database.

**Error Messages:**
```
KeyError: 'workouts' at /dashboard/
Internal Server Error: /api/dashboard-data/
Exception Type: KeyError
Exception Value: 'workouts'
Exception Location: /home/views.py, line 915, in dashboard_data_api
```

**Symptoms:**
- Dashboard showing "0 workouts" for users with existing data
- Intermittent crashes when accessing workout statistics
- Some users' workout_info field containing `{}` instead of expected structure

### Root Cause Analysis

The issue was traced to inconsistent initialization of the JSONField structure. When new profiles were created, the `workout_info` field was sometimes initialized as an empty dict `{}` instead of the expected structure `{"workouts": [], "goals": []}`.

**Code causing the issue:**
```python
# In signals.py - PROBLEMATIC CODE
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(
            user=instance,
            workout_info={}  # This caused the KeyError
        )
```

### Solution Implemented

1. **Fixed Profile Creation Signal:**
```python
# In signals.py - FIXED CODE
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(
            user=instance,
            workout_info={
                "workouts": [],
                "goals": []
            }
        )
```

2. **Added Defensive Programming in Views:**
```python
# In views.py - Added safety checks
workout_info = profile.workout_info
if 'workouts' not in workout_info:
    workout_info["workouts"] = []
if 'goals' not in workout_info:
    workout_info["goals"] = []
```

3. **Database Migration for Existing Data:**
```python
# Migration to fix existing corrupted data
from django.db import migrations

def fix_workout_info(apps, schema_editor):
    Profile = apps.get_model('home', 'Profile')
    for profile in Profile.objects.all():
        if not profile.workout_info or 'workouts' not in profile.workout_info:
            profile.workout_info = {"workouts": [], "goals": []}
            profile.save()

class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(fix_workout_info),
    ]
```

### Lessons Learned
- Always initialize JSONFields with expected structure
- Implement defensive programming for dynamic data structures
- Add data validation at the model level using `clean()` methods
- Consider using JSONField default values in model definitions

---

## Scenario 2: Memory Leak in Dashboard API

### Problem Description
**Date:** 2024-01-22  
**Severity:** Medium  
**Component:** Dashboard Data API

**Issue:** The application server was experiencing memory leaks and eventual crashes during peak usage times, particularly when multiple users accessed the dashboard simultaneously.

**Error Messages:**
```
MemoryError: Unable to allocate array
django.db.utils.OperationalError: database is locked
Timeout: The view didn't return an HttpResponse object
```

**Symptoms:**
- Server memory usage continuously increasing
- Slow response times for dashboard API calls
- Occasional 500 errors during high traffic
- Database connection pool exhaustion

### Root Cause Analysis

The issue was caused by inefficient database queries in the `dashboard_data_api` view. The function was loading entire user profiles and related objects into memory without proper optimization.

**Problematic code:**
```python
# PROBLEMATIC CODE - Loading too much data
def dashboard_data_api(request):
    profile = Profile.objects.get(user=request.user)
    # This loaded ALL scheduled workouts into memory
    scheduled_workouts = ScheduledWorkout.objects.filter(user=request.user)
    # This loaded ALL weight entries into memory
    weight_entries = Weight.objects.filter(user=request.user)
    # Processing large datasets in Python instead of database
    for workout in scheduled_workouts:
        # Complex calculations on large datasets
```

### Solution Implemented

1. **Optimized Database Queries:**
```python
# OPTIMIZED CODE - Using select_related and limiting results
def dashboard_data_api(request):
    profile = Profile.objects.select_related('user').get(user=request.user)
    
    # Only get completed scheduled workouts with limit
    scheduled_workouts = ScheduledWorkout.objects.filter(
        user=request.user, 
        status='completed'
    ).order_by('-date')[:5]  # Limit results
    
    # Only get recent weight entries
    weight_entries = Weight.objects.filter(
        user=request.user
    ).order_by('-date')[:5]  # Limit results
```

2. **Added Database-Level Aggregations:**
```python
# Use database aggregation instead of Python loops
from django.db.models import Count, Avg

completed_count = ScheduledWorkout.objects.filter(
    user=request.user, 
    status='completed'
).count()  # Database-level count

avg_weight = Weight.objects.filter(
    user=request.user
).aggregate(avg_weight=Avg('weight'))['avg_weight']
```

3. **Implemented Caching:**
```python
from django.core.cache import cache

def dashboard_data_api(request):
    cache_key = f'dashboard_data_{request.user.id}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return JsonResponse(cached_data)
    
    # Generate data...
    data = {...}
    
    # Cache for 5 minutes
    cache.set(cache_key, data, 300)
    return JsonResponse(data)
```

### Lessons Learned
- Always use `select_related()` and `prefetch_related()` for related objects
- Limit query results when possible to prevent memory issues
- Use database aggregations instead of Python loops for calculations
- Implement caching for expensive operations
- Monitor memory usage in production environments

---

## Scenario 3: File Upload Security Vulnerability

### Problem Description
**Date:** 2024-02-03  
**Severity:** Critical  
**Component:** Progress Photo Upload Feature

**Issue:** Security audit revealed that the progress photo upload feature was vulnerable to malicious file uploads, potentially allowing code execution on the server.

**Security Issues Identified:**
- No file type validation beyond Django's basic checks
- No file size limits enforced
- Uploaded files served directly without sanitization
- No virus scanning or content validation

**Potential Attack Vectors:**
```python
# Malicious file upload attempts logged:
# 1. PHP shell uploaded as "progress.jpg"
# 2. JavaScript file with .png extension
# 3. Executable files with image extensions
# 4. Extremely large files (>100MB) causing DoS
```

### Root Cause Analysis

The original implementation relied solely on Django's basic ImageField validation, which only checked file extensions and basic image headers. This was insufficient for production security requirements.

**Vulnerable code:**
```python
# VULNERABLE CODE
class ProgressPhoto(models.Model):
    image = models.ImageField(
        upload_to='progress_photos/%Y/%m/'
        # No additional validation
    )

# In views.py
def progress_photo_api(request):
    image = request.FILES.get('photo')
    # No validation beyond Django defaults
    photo = ProgressPhoto.objects.create(
        user=request.user,
        image=image
    )
```

### Solution Implemented

1. **Enhanced File Validation:**
```python
# In validators.py - Custom file validators
import magic
from django.core.exceptions import ValidationError
from PIL import Image

def validate_image_file(file):
    """Comprehensive image file validation"""
    # Check file size (max 5MB)
    if file.size > 5 * 1024 * 1024:
        raise ValidationError('File size cannot exceed 5MB')
    
    # Check MIME type using python-magic
    file_mime = magic.from_buffer(file.read(1024), mime=True)
    file.seek(0)  # Reset file pointer
    
    allowed_mimes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if file_mime not in allowed_mimes:
        raise ValidationError(f'Invalid file type: {file_mime}')
    
    # Validate image content using PIL
    try:
        img = Image.open(file)
        img.verify()  # Verify image integrity
        file.seek(0)  # Reset file pointer
    except Exception:
        raise ValidationError('Invalid or corrupted image file')
    
    # Check image dimensions (reasonable limits)
    if img.width > 4000 or img.height > 4000:
        raise ValidationError('Image dimensions too large (max 4000x4000)')

def sanitize_filename(filename):
    """Sanitize uploaded filename"""
    import re
    import uuid
    
    # Generate safe filename with UUID
    ext = filename.split('.')[-1].lower()
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    return safe_name
```

2. **Updated Model with Validation:**
```python
# SECURE CODE
class ProgressPhoto(models.Model):
    image = models.ImageField(
        upload_to='progress_photos/%Y/%m/',
        validators=[validate_image_file],
        help_text="Upload progress photo (max 5MB, JPEG/PNG/GIF/WebP only)"
    )
    
    def save(self, *args, **kwargs):
        # Sanitize filename before saving
        if self.image:
            self.image.name = sanitize_filename(self.image.name)
        super().save(*args, **kwargs)
```

3. **Enhanced API Validation:**
```python
# In views.py - Additional security checks
def progress_photo_api(request):
    if request.method == 'POST':
        image = request.FILES.get('photo')
        
        if not image:
            return JsonResponse({'success': False, 'error': 'Photo required'})
        
        # Additional security checks
        try:
            validate_image_file(image)
        except ValidationError as e:
            return JsonResponse({'success': False, 'error': str(e)})
        
        # Rate limiting check
        cache_key = f'photo_upload_{request.user.id}'
        if cache.get(cache_key):
            return JsonResponse({
                'success': False, 
                'error': 'Please wait before uploading another photo'
            })
        
        # Set rate limit (1 upload per minute)
        cache.set(cache_key, True, 60)
        
        # Proceed with secure upload...
```

4. **Server Configuration Updates:**
```nginx
# Nginx configuration for additional security
location /media/progress_photos/ {
    # Prevent execution of uploaded files
    location ~* \.(php|py|js|html|htm)$ {
        deny all;
    }
    
    # Set proper headers
    add_header X-Content-Type-Options nosniff;
    add_header Content-Security-Policy "default-src 'none'; img-src 'self';";
}
```

### Lessons Learned
- Never trust user-uploaded content without thorough validation
- Implement multiple layers of security (validation, sanitization, server config)
- Use specialized libraries (python-magic, PIL) for content validation
- Implement rate limiting for file uploads
- Regular security audits are essential for production applications
- Consider using cloud storage services with built-in security features

---

## General Debugging Best Practices

### Logging Strategy
```python
# Comprehensive logging setup
import logging

logger = logging.getLogger(__name__)

def api_view_with_logging(request):
    logger.info(f"API call from user {request.user.id}: {request.path}")
    
    try:
        # API logic here
        result = process_data()
        logger.info(f"API success for user {request.user.id}")
        return JsonResponse({'success': True, 'data': result})
    
    except Exception as e:
        logger.error(f"API error for user {request.user.id}: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Internal server error'})
```

### Error Monitoring
- Use tools like Sentry for production error tracking
- Implement custom error pages with error IDs for user support
- Set up alerts for critical errors and performance issues
- Regular log analysis to identify patterns and potential issues

### Testing Strategy
- Write unit tests for all critical functions
- Implement integration tests for API endpoints
- Use Django's test client for view testing
- Regular security testing and code reviews

---

*Last updated: January 2024*  
*Document maintained by: Development Team*