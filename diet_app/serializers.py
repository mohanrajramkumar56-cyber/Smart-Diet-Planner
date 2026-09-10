from rest_framework import serializers
from .models import UserProfile, DietPlan, Feedback

class UserProfileSerializer(serializers.ModelSerializer):
    bmi = serializers.ReadOnlyField()
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'name', 'age', 'gender', 'height', 'weight', 
            'activity_level', 'goal', 'diet_type', 'country',
            'medical_conditions', 'allergies', 'favorite_foods', 'disliked_foods', 'bmi',
            'created_at', 'updated_at'
        ]

class DietPlanSerializer(serializers.ModelSerializer):
    user_profile = UserProfileSerializer(read_only=True)
    plan_summary = serializers.ReadOnlyField()
    
    class Meta:
        model = DietPlan
        fields = [
            'id', 'user_profile', 'plan_data', 'created_at', 
            'rating', 'feedback_text', 'plan_summary'
        ]

class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = [
            'id', 'diet_plan', 'meal_day', 'meal_type', 
            'rating', 'comment', 'created_at'
        ]