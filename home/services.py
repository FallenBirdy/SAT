"""Service classes for fitness calculations and data processing.

This module contains helper classes that encapsulate business logic
for fitness calculations, data validation, and other utility functions.
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from typing import Optional, Dict, List, Tuple
from django.contrib.auth.models import User
from .constants import (
    BMI_MIN, BMI_MAX, MIN_HEIGHT_CM, MAX_HEIGHT_CM,
    MIN_BODY_WEIGHT_KG, MAX_BODY_WEIGHT_KG, MIN_AGE, MAX_AGE,
    CALORIE_ESTIMATE_PER_WORKOUT, MAX_WORKOUT_MINUTES
)


class FitnessCalculationService:
    """Service class for fitness-related calculations and metrics.
    
    This class provides methods for calculating BMI, calorie estimates,
    age-based recommendations, and other fitness metrics. It demonstrates
    the use of private methods for internal calculations.
    
    Attributes:
        _precision (int): Decimal precision for calculations.
    """
    
    def __init__(self, precision: int = 2):
        """Initialize the fitness calculation service.
        
        Args:
            precision (int): Number of decimal places for calculations.
        """
        self._precision = precision
    
    def calculate_bmi(self, weight_kg: float, height_cm: float) -> Optional[Decimal]:
        """Calculate Body Mass Index (BMI) from weight and height.
        
        Args:
            weight_kg (float): Weight in kilograms.
            height_cm (float): Height in centimeters.
            
        Returns:
            Optional[Decimal]: BMI value rounded to specified precision, or None if invalid input.
        """
        if not self._is_valid_weight(weight_kg) or not self._is_valid_height(height_cm):
            return None
            
        height_m = self._convert_cm_to_meters(height_cm)
        bmi = Decimal(str(weight_kg)) / (Decimal(str(height_m)) ** 2)
        return self._round_decimal(bmi)
    
    def get_bmi_category(self, bmi: Decimal) -> str:
        """Get BMI category classification.
        
        Args:
            bmi (Decimal): BMI value.
            
        Returns:
            str: BMI category (Underweight, Normal, Overweight, Obese).
        """
        if bmi < 18.5:
            return "Underweight"
        elif bmi < 25:
            return "Normal weight"
        elif bmi < 30:
            return "Overweight"
        else:
            return "Obese"
    
    def estimate_calories_burned(self, workout_duration_minutes: int, 
                               workout_type: str = "general") -> int:
        """Estimate calories burned during a workout.
        
        Args:
            workout_duration_minutes (int): Duration of workout in minutes.
            workout_type (str): Type of workout for more accurate estimation.
            
        Returns:
            int: Estimated calories burned.
        """
        if not self._is_valid_workout_duration(workout_duration_minutes):
            return 0
            
        base_calories_per_minute = self._get_base_calorie_rate(workout_type)
        return int(workout_duration_minutes * base_calories_per_minute)
    
    def calculate_age_from_dob(self, date_of_birth: date) -> int:
        """Calculate age from date of birth.
        
        Args:
            date_of_birth (date): User's date of birth.
            
        Returns:
            int: Age in years.
        """
        today = date.today()
        age = today.year - date_of_birth.year
        
        # Adjust if birthday hasn't occurred this year
        if today.month < date_of_birth.month or \
           (today.month == date_of_birth.month and today.day < date_of_birth.day):
            age -= 1
            
        return max(0, age)  # Ensure non-negative age
    
    def get_age_based_recommendations(self, age: int) -> Dict[str, str]:
        """Get fitness recommendations based on age.
        
        Args:
            age (int): User's age in years.
            
        Returns:
            Dict[str, str]: Dictionary with recommendation categories and advice.
        """
        if not self._is_valid_age(age):
            return {"error": "Invalid age provided"}
            
        return self._generate_age_recommendations(age)
    
    # Private methods for internal calculations and validation
    
    def _is_valid_weight(self, weight_kg: float) -> bool:
        """Validate weight input.
        
        Args:
            weight_kg (float): Weight in kilograms.
            
        Returns:
            bool: True if weight is within valid range.
        """
        try:
            weight = float(weight_kg)
            return MIN_BODY_WEIGHT_KG <= weight <= MAX_BODY_WEIGHT_KG
        except (ValueError, TypeError):
            return False
    
    def _is_valid_height(self, height_cm: float) -> bool:
        """Validate height input.
        
        Args:
            height_cm (float): Height in centimeters.
            
        Returns:
            bool: True if height is within valid range.
        """
        try:
            height = float(height_cm)
            return MIN_HEIGHT_CM <= height <= MAX_HEIGHT_CM
        except (ValueError, TypeError):
            return False
    
    def _is_valid_age(self, age: int) -> bool:
        """Validate age input.
        
        Args:
            age (int): Age in years.
            
        Returns:
            bool: True if age is within valid range.
        """
        try:
            age_int = int(age)
            return MIN_AGE <= age_int <= MAX_AGE
        except (ValueError, TypeError):
            return False
    
    def _is_valid_workout_duration(self, duration_minutes: int) -> bool:
        """Validate workout duration input.
        
        Args:
            duration_minutes (int): Workout duration in minutes.
            
        Returns:
            bool: True if duration is within valid range.
        """
        try:
            duration = int(duration_minutes)
            return 1 <= duration <= MAX_WORKOUT_MINUTES
        except (ValueError, TypeError):
            return False
    
    def _convert_cm_to_meters(self, height_cm: float) -> float:
        """Convert height from centimeters to meters.
        
        Args:
            height_cm (float): Height in centimeters.
            
        Returns:
            float: Height in meters.
        """
        return float(height_cm) / 100.0
    
    def _round_decimal(self, value: Decimal) -> Decimal:
        """Round decimal to specified precision.
        
        Args:
            value (Decimal): Value to round.
            
        Returns:
            Decimal: Rounded value.
        """
        return value.quantize(
            Decimal('0.' + '0' * self._precision), 
            rounding=ROUND_HALF_UP
        )
    
    def _get_base_calorie_rate(self, workout_type: str) -> float:
        """Get base calorie burn rate per minute for workout type.
        
        Args:
            workout_type (str): Type of workout.
            
        Returns:
            float: Calories burned per minute.
        """
        # Calorie rates per minute for different workout types
        calorie_rates = {
            "strength": 8.0,
            "cardio": 12.0,
            "flexibility": 4.0,
            "hiit": 15.0,
            "general": 6.0
        }
        return calorie_rates.get(workout_type.lower(), calorie_rates["general"])
    
    def _generate_age_recommendations(self, age: int) -> Dict[str, str]:
        """Generate age-specific fitness recommendations.
        
        Args:
            age (int): User's age in years.
            
        Returns:
            Dict[str, str]: Recommendations by category.
        """
        if age < 25:
            return {
                "focus": "Build strength foundation and establish consistent habits",
                "cardio": "Mix high-intensity and moderate cardio 4-5 times per week",
                "strength": "Focus on compound movements and progressive overload",
                "recovery": "7-9 hours sleep, active recovery 1-2 times per week"
            }
        elif age < 40:
            return {
                "focus": "Maintain strength while improving functional fitness",
                "cardio": "Moderate cardio 3-4 times per week with occasional HIIT",
                "strength": "Maintain muscle mass with consistent resistance training",
                "recovery": "Prioritize sleep and stress management"
            }
        elif age < 60:
            return {
                "focus": "Preserve muscle mass and maintain mobility",
                "cardio": "Low-impact cardio 3-4 times per week",
                "strength": "Focus on functional movements and joint health",
                "recovery": "Extended warm-up and cool-down periods"
            }
        else:
            return {
                "focus": "Maintain independence and prevent falls",
                "cardio": "Gentle cardio like walking or swimming",
                "strength": "Light resistance training for bone health",
                "recovery": "Balance and flexibility exercises daily"
            }


class WorkoutAnalysisService:
    """Service class for analyzing workout data and progress.
    
    This class provides methods for analyzing workout patterns,
    calculating progress metrics, and generating insights.
    """
    
    def __init__(self):
        """Initialize the workout analysis service."""
        self._fitness_calc = FitnessCalculationService()
    
    def analyze_workout_consistency(self, user: User, days: int = 30) -> Dict[str, any]:
        """Analyze user's workout consistency over a period.
        
        Args:
            user (User): The user to analyze.
            days (int): Number of days to analyze.
            
        Returns:
            Dict[str, any]: Analysis results including consistency metrics.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # This would typically query the database for workout data
        # For demonstration, we'll use placeholder logic
        workout_days = self._get_workout_days_in_period(user, start_date, end_date)
        
        consistency_rate = len(workout_days) / days if days > 0 else 0
        
        return {
            "period_days": days,
            "workout_days": len(workout_days),
            "consistency_rate": round(consistency_rate * 100, 1),
            "recommendation": self._get_consistency_recommendation(consistency_rate)
        }
    
    def _get_workout_days_in_period(self, user: User, start_date: date, end_date: date) -> List[date]:
        """Get list of days user worked out in the given period.
        
        Args:
            user (User): The user to query.
            start_date (date): Start of the period.
            end_date (date): End of the period.
            
        Returns:
            List[date]: List of workout dates.
        """
        # Placeholder implementation - would query actual workout data
        return []
    
    def _get_consistency_recommendation(self, consistency_rate: float) -> str:
        """Get recommendation based on consistency rate.
        
        Args:
            consistency_rate (float): Consistency rate (0.0 to 1.0).
            
        Returns:
            str: Recommendation message.
        """
        if consistency_rate >= 0.8:
            return "Excellent consistency! Keep up the great work."
        elif consistency_rate >= 0.6:
            return "Good consistency. Try to maintain regular workout schedule."
        elif consistency_rate >= 0.4:
            return "Moderate consistency. Consider setting specific workout days."
        else:
            return "Low consistency. Start with 2-3 workouts per week and build gradually."