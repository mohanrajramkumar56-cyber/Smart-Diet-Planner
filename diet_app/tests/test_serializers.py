"""Tests for diet_app serializers."""
from django.test import TestCase
from django.contrib.auth.models import User
from diet_app.models import UserProfile, DietPlan, Feedback
from diet_app.serializers import (
    UserProfileSerializer,
    DietPlanSerializer,
    FeedbackSerializer,
)


class UserProfileSerializerTests(TestCase):
    """Tests for UserProfileSerializer."""

    def setUp(self):
        self.valid_data = {
            'name': 'Test User',
            'age': 30,
            'gender': 'male',
            'height': 175.0,
            'weight': 70.0,
            'activity_level': 'moderate',
            'goal': 'lose',
            'diet_type': 'vegetarian',
            'medical_conditions': 'None',
            'allergies': 'None',
            'favorite_foods': 'chicken, rice',
            'disliked_foods': 'broccoli',
        }

    def test_valid_serialization(self):
        """Test serializing a valid profile."""
        profile = UserProfile.objects.create(**self.valid_data)
        serializer = UserProfileSerializer(profile)
        data = serializer.data

        self.assertEqual(data['name'], 'Test User')
        self.assertEqual(data['age'], 30)
        self.assertEqual(data['gender'], 'male')
        self.assertEqual(data['height'], 175.0)
        self.assertEqual(data['weight'], 70.0)
        self.assertEqual(data['activity_level'], 'moderate')
        self.assertEqual(data['goal'], 'lose')
        self.assertEqual(data['diet_type'], 'vegetarian')
        self.assertIn('bmi', data)
        self.assertAlmostEqual(data['bmi'], 22.86, places=2)
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)

    def test_bmi_is_read_only(self):
        """Test BMI field is read-only."""
        profile = UserProfile.objects.create(**self.valid_data)
        serializer = UserProfileSerializer(profile)
        # BMI should be in output but not writable
        self.assertIn('bmi', serializer.data)

        # Try to update BMI via serializer (should be ignored)
        data = self.valid_data.copy()
        data['bmi'] = 99.99
        serializer = UserProfileSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        saved = serializer.save()
        self.assertNotEqual(saved.bmi, 99.99)

    def test_valid_deserialization(self):
        """Test deserializing valid data."""
        serializer = UserProfileSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        profile = serializer.save()
        self.assertEqual(profile.name, 'Test User')

    def test_invalid_missing_required_fields(self):
        """Test validation fails for missing required fields."""
        data = {'name': 'Test'}
        serializer = UserProfileSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('age', serializer.errors)
        self.assertIn('gender', serializer.errors)
        self.assertIn('height', serializer.errors)
        self.assertIn('weight', serializer.errors)
        self.assertIn('activity_level', serializer.errors)
        self.assertIn('goal', serializer.errors)
        self.assertIn('diet_type', serializer.errors)

    def test_invalid_gender_choice(self):
        """Test validation fails for invalid gender."""
        data = self.valid_data.copy()
        data['gender'] = 'invalid'
        serializer = UserProfileSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('gender', serializer.errors)

    def test_invalid_diet_type_choice(self):
        """Test validation fails for invalid diet_type."""
        data = self.valid_data.copy()
        data['diet_type'] = 'invalid'
        serializer = UserProfileSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('diet_type', serializer.errors)

    def test_name_max_length(self):
        """Test name max length validation."""
        data = self.valid_data.copy()
        data['name'] = 'A' * 101
        serializer = UserProfileSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)


class DietPlanSerializerTests(TestCase):
    """Tests for DietPlanSerializer."""

    def setUp(self):
        self.profile = UserProfile.objects.create(
            name='Test User',
            age=30,
            gender='male',
            height=175.0,
            weight=70.0,
            activity_level='moderate',
            goal='lose',
            diet_type='vegetarian',
        )
        self.plan_data = {
            'total_calories_per_day': 2000,
            'nutritional_summary': {
                'daily_protein': '100g',
                'daily_carbs': '250g',
                'daily_fat': '60g',
                'daily_fiber': '25g',
            },
            'days': [
                {
                    'day': 'Day 1',
                    'meals': [
                        {
                            'meal_type': 'Breakfast',
                            'time': '7:00 AM',
                            'food_items': ['Oatmeal', 'Banana'],
                            'calories': 300,
                            'protein': '10g',
                            'carbs': '50g',
                            'fat': '5g',
                        },
                    ],
                },
            ],
            'tips': ['Drink water', 'Exercise'],
        }

    def test_valid_serialization(self):
        """Test serializing a valid diet plan."""
        plan = DietPlan.objects.create(
            user_profile=self.profile,
            plan_data=self.plan_data,
        )
        serializer = DietPlanSerializer(plan)
        data = serializer.data

        self.assertEqual(data['id'], plan.id)
        self.assertIn('user_profile', data)
        self.assertEqual(data['user_profile']['name'], 'Test User')
        self.assertEqual(data['plan_data'], self.plan_data)
        self.assertIn('plan_summary', data)
        self.assertEqual(data['plan_summary'], '1 day plan')
        self.assertIsNone(data['rating'])
        self.assertIsNone(data['feedback_text'])

    def test_plan_summary_read_only(self):
        """Test plan_summary is read-only."""
        plan = DietPlan.objects.create(
            user_profile=self.profile,
            plan_data=self.plan_data,
        )
        serializer = DietPlanSerializer(plan)
        self.assertIn('plan_summary', serializer.data)

    def test_user_profile_nested_read_only(self):
        """Test user_profile is nested and read-only."""
        plan = DietPlan.objects.create(
            user_profile=self.profile,
            plan_data=self.plan_data,
        )
        serializer = DietPlanSerializer(plan)
        user_profile_data = serializer.data['user_profile']
        self.assertIn('id', user_profile_data)
        self.assertIn('name', user_profile_data)
        self.assertIn('bmi', user_profile_data)


class FeedbackSerializerTests(TestCase):
    """Tests for FeedbackSerializer."""

    def setUp(self):
        self.profile = UserProfile.objects.create(
            name='Test User',
            age=30,
            gender='male',
            height=175.0,
            weight=70.0,
            activity_level='moderate',
            goal='lose',
            diet_type='vegetarian',
        )
        self.plan = DietPlan.objects.create(
            user_profile=self.profile,
            plan_data={'days': [], 'total_calories_per_day': 2000},
        )

    def test_valid_serialization(self):
        """Test serializing valid feedback."""
        feedback = Feedback.objects.create(
            diet_plan=self.plan,
            meal_day='Day 1',
            meal_type='breakfast',
            rating=5,
            comment='Great!',
        )
        serializer = FeedbackSerializer(feedback)
        data = serializer.data

        self.assertEqual(data['id'], feedback.id)
        self.assertEqual(data['diet_plan'], self.plan.id)
        self.assertEqual(data['meal_day'], 'Day 1')
        self.assertEqual(data['meal_type'], 'breakfast')
        self.assertEqual(data['rating'], 5)
        self.assertEqual(data['comment'], 'Great!')
        self.assertIn('created_at', data)

    def test_valid_deserialization(self):
        """Test deserializing valid feedback."""
        data = {
            'diet_plan': self.plan.id,
            'meal_day': 'Day 1',
            'meal_type': 'breakfast',
            'rating': 5,
            'comment': 'Great!',
        }
        serializer = FeedbackSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        feedback = serializer.save()
        self.assertEqual(feedback.rating, 5)

    def test_invalid_rating(self):
        """Test invalid rating value."""
        data = {
            'diet_plan': self.plan.id,
            'meal_day': 'Day 1',
            'meal_type': 'breakfast',
            'rating': 10,
        }
        serializer = FeedbackSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('rating', serializer.errors)