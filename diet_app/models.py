from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import json
import pycountry

class UserProfile(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    
    ACTIVITY_CHOICES = [
        ('sedentary', 'Sedentary (little/no exercise)'),
        ('light', 'Light (light exercise 1-3 days/week)'),
        ('moderate', 'Moderate (moderate exercise 3-5 days/week)'),
        ('active', 'Active (hard exercise 6-7 days/week)'),
        ('very_active', 'Very Active (very hard exercise, physical job)'),
    ]
    
    GOAL_CHOICES = [
        ('lose', 'Weight Loss'),
        ('gain', 'Weight Gain'),
        ('maintain', 'Maintain Weight'),
        ('muscle', 'Build Muscle'),
    ]
    
    DIET_TYPE_CHOICES = [
        ('vegetarian', 'Vegetarian'),
        ('non_vegetarian', 'Non-Vegetarian'),
        ('vegan', 'Vegan'),
        ('keto', 'Keto'),
        ('paleo', 'Paleo'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    age = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(120)],
        help_text="Age in years (1-120)"
    )
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    height = models.FloatField(help_text="Height in cm")
    weight = models.FloatField(help_text="Weight in kg")
    activity_level = models.CharField(max_length=20, choices=ACTIVITY_CHOICES)
    goal = models.CharField(max_length=20, choices=GOAL_CHOICES)
    diet_type = models.CharField(max_length=20, choices=DIET_TYPE_CHOICES)
    country = models.CharField(
        max_length=2,
        choices=[(c.alpha_2, c.name) for c in sorted(list(pycountry.countries), key=lambda x: x.name)],
        blank=True,
        null=True,
        help_text="Country for cuisine preferences (ISO 2-letter code)"
    )
    medical_conditions = models.TextField(blank=True, null=True)
    allergies = models.TextField(blank=True, null=True)
    favorite_foods = models.TextField(blank=True, null=True)
    disliked_foods = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.age}y {self.gender}"
    
    @property
    def bmi(self):
        height_m = self.height / 100
        return round(self.weight / (height_m ** 2), 2)

class DietPlan(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    plan_data = models.JSONField()  # Store the complete diet plan
    created_at = models.DateTimeField(auto_now_add=True)
    rating = models.IntegerField(null=True, blank=True, choices=[(1, 'Dislike'), (5, 'Like')])
    feedback_text = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Nourish Plan for {self.user_profile.name} - {self.created_at.strftime('%Y-%m-%d')}"
    
    @property
    def plan_summary(self):
        if self.plan_data and 'days' in self.plan_data:
            return f"{len(self.plan_data['days'])} day plan"
        return "Nourish Plan"

class Feedback(models.Model):
    diet_plan = models.ForeignKey(DietPlan, on_delete=models.CASCADE)
    meal_day = models.CharField(max_length=20)  # e.g., "Day 1", "Day 2"
    meal_type = models.CharField(max_length=20)  # breakfast, lunch, dinner, snack
    rating = models.IntegerField(choices=[(1, 'Dislike'), (5, 'Like')])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Feedback for {self.diet_plan.user_profile.name} - {self.meal_day} {self.meal_type}"