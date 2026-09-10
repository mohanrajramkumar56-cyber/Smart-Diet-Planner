from django.contrib import admin
from .models import UserProfile, DietPlan, Feedback

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'age', 'gender', 'bmi', 'goal', 'diet_type', 'created_at']
    list_filter = ['gender', 'goal', 'diet_type', 'activity_level']
    search_fields = ['name', 'medical_conditions']
    readonly_fields = ['bmi', 'created_at', 'updated_at']

@admin.register(DietPlan)
class DietPlanAdmin(admin.ModelAdmin):
    list_display = ['user_profile', 'plan_summary', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['user_profile__name']
    readonly_fields = ['created_at']

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['diet_plan', 'meal_day', 'meal_type', 'rating', 'created_at']
    list_filter = ['rating', 'meal_type', 'created_at']
    search_fields = ['diet_plan__user_profile__name']