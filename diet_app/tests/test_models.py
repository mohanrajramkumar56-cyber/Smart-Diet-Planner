"""Tests for diet_app models."""
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from diet_app.models import UserProfile, DietPlan, Feedback


class UserProfileModelTests(TestCase):
    """Tests for UserProfile model."""

    def setUp(self):
        self.valid_profile_data = {
            'name': 'Test User',
            'age': 30,
            'gender': 'male',
            'height': 175.0,
            'weight': 70.0,
            'activity_level': 'moderate',
            'goal': 'lose',
            'diet_type': 'vegetarian',
        }

    def test_create_user_profile(self):
        """Test creating a valid user profile."""
        profile = UserProfile.objects.create(**self.valid_profile_data)
        self.assertEqual(profile.name, 'Test User')
        self.assertEqual(profile.age, 30)
        self.assertEqual(profile.gender, 'male')
        self.assertEqual(profile.height, 175.0)
        self.assertEqual(profile.weight, 70.0)
        self.assertEqual(profile.activity_level, 'moderate')
        self.assertEqual(profile.goal, 'lose')
        self.assertEqual(profile.diet_type, 'vegetarian')

    def test_bmi_calculation(self):
        """Test BMI property calculation."""
        profile = UserProfile.objects.create(**self.valid_profile_data)
        # BMI = 70 / (1.75^2) = 22.86
        self.assertAlmostEqual(profile.bmi, 22.86, places=2)

    def test_bmi_various_values(self):
        """Test BMI with various height/weight combinations."""
        test_cases = [
            (175, 70, 22.86),
            (160, 50, 19.53),
            (180, 100, 30.86),
            (150, 45, 20.00),
        ]
        for height, weight, expected_bmi in test_cases:
            profile = UserProfile.objects.create(
                name=f'Test {height}',
                age=25,
                gender='male',
                height=height,
                weight=weight,
                activity_level='sedentary',
                goal='maintain',
                diet_type='vegetarian',
            )
            self.assertAlmostEqual(profile.bmi, expected_bmi, places=2)

    def test_gender_choices_validation(self):
        """Test gender field choices validation."""
        data = self.valid_profile_data.copy()
        data['gender'] = 'invalid'
        profile = UserProfile(**data)
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_diet_type_choices_validation(self):
        """Test diet_type field choices validation."""
        data = self.valid_profile_data.copy()
        data['diet_type'] = 'invalid'
        profile = UserProfile(**data)
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_activity_level_choices_validation(self):
        """Test activity_level field choices validation."""
        data = self.valid_profile_data.copy()
        data['activity_level'] = 'invalid'
        profile = UserProfile(**data)
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_goal_choices_validation(self):
        """Test goal field choices validation."""
        data = self.valid_profile_data.copy()
        data['goal'] = 'invalid'
        profile = UserProfile(**data)
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_name_max_length(self):
        """Test name field max_length validation."""
        data = self.valid_profile_data.copy()
        data['name'] = 'A' * 101
        profile = UserProfile(**data)
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_optional_fields_can_be_blank(self):
        """Test optional fields can be blank."""
        data = self.valid_profile_data.copy()
        data['medical_conditions'] = ''
        data['allergies'] = ''
        data['favorite_foods'] = ''
        data['disliked_foods'] = ''
        profile = UserProfile.objects.create(**data)
        self.assertEqual(profile.medical_conditions, '')
        self.assertEqual(profile.allergies, '')
        self.assertEqual(profile.favorite_foods, '')
        self.assertEqual(profile.disliked_foods, '')

    def test_user_relationship(self):
        """Test UserProfile to User relationship."""
        user = User.objects.create_user(username='testuser', password='pass123')
        profile = UserProfile.objects.create(user=user, **self.valid_profile_data)
        self.assertEqual(profile.user, user)

    def test_str_representation(self):
        """Test __str__ method."""
        profile = UserProfile.objects.create(**self.valid_profile_data)
        expected = "Test User - 30y male"
        self.assertEqual(str(profile), expected)


class DietPlanModelTests(TestCase):
    """Tests for DietPlan model."""

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
        self.valid_plan_data = {
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

    def test_create_diet_plan(self):
        """Test creating a diet plan."""
        plan = DietPlan.objects.create(
            user_profile=self.profile,
            plan_data=self.valid_plan_data,
        )
        self.assertEqual(plan.user_profile, self.profile)
        self.assertEqual(plan.plan_data, self.valid_plan_data)
        self.assertIsNone(plan.rating)
        self.assertIsNone(plan.feedback_text)

    def test_jsonfield_storage(self):
        """Test JSONField stores dict correctly."""
        plan = DietPlan.objects.create(
            user_profile=self.profile,
            plan_data=self.valid_plan_data,
        )
        # Reload from DB
        plan = DietPlan.objects.get(id=plan.id)
        self.assertEqual(plan.plan_data['total_calories_per_day'], 2000)
        self.assertEqual(plan.plan_data['nutritional_summary']['daily_protein'], '100g')

    def test_plan_summary_property(self):
        """Test plan_summary property."""
        plan = DietPlan.objects.create(
            user_profile=self.profile,
            plan_data=self.valid_plan_data,
        )
        self.assertEqual(plan.plan_summary, "1 day plan")

    def test_cascade_delete_user_profile(self):
        """Test cascade delete when UserProfile is deleted."""
        plan = DietPlan.objects.create(
            user_profile=self.profile,
            plan_data=self.valid_plan_data,
        )
        plan_id = plan.id
        self.profile.delete()
        self.assertFalse(DietPlan.objects.filter(id=plan_id).exists())

    def test_rating_choices(self):
        """Test rating field choices."""
        plan = DietPlan.objects.create(
            user_profile=self.profile,
            plan_data=self.valid_plan_data,
        )
        plan.rating = 5
        plan.save()
        self.assertEqual(plan.rating, 5)

        plan.rating = 1
        plan.save()
        self.assertEqual(plan.rating, 1)

    def test_ordering(self):
        """Test default ordering by created_at desc."""
        plan1 = DietPlan.objects.create(
            user_profile=self.profile,
            plan_data=self.valid_plan_data,
        )
        # Ensure different created_at times
        import time
        time.sleep(0.01)
        plan2 = DietPlan.objects.create(
            user_profile=self.profile,
            plan_data=self.valid_plan_data,
        )
        plans = list(DietPlan.objects.all())
        # Ordering is by -created_at, so newer (plan2) comes first
        self.assertEqual(plans[0].id, plan2.id)
        self.assertEqual(plans[1].id, plan1.id)


class FeedbackModelTests(TestCase):
    """Tests for Feedback model."""

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

    def test_create_feedback(self):
        """Test creating feedback."""
        feedback = Feedback.objects.create(
            diet_plan=self.plan,
            meal_day='Day 1',
            meal_type='breakfast',
            rating=5,
            comment='Great meal!',
        )
        self.assertEqual(feedback.diet_plan, self.plan)
        self.assertEqual(feedback.meal_day, 'Day 1')
        self.assertEqual(feedback.meal_type, 'breakfast')
        self.assertEqual(feedback.rating, 5)
        self.assertEqual(feedback.comment, 'Great meal!')

    def test_rating_choices(self):
        """Test rating field choices."""
        feedback = Feedback.objects.create(
            diet_plan=self.plan,
            meal_day='Day 1',
            meal_type='breakfast',
            rating=1,
        )
        self.assertEqual(feedback.rating, 1)

    def test_cascade_delete_diet_plan(self):
        """Test cascade delete when DietPlan is deleted."""
        feedback = Feedback.objects.create(
            diet_plan=self.plan,
            meal_day='Day 1',
            meal_type='breakfast',
            rating=5,
        )
        feedback_id = feedback.id
        self.plan.delete()
        self.assertFalse(Feedback.objects.filter(id=feedback_id).exists())

    def test_str_representation(self):
        """Test __str__ method."""
        feedback = Feedback.objects.create(
            diet_plan=self.plan,
            meal_day='Day 1',
            meal_type='breakfast',
            rating=5,
        )
        expected = f"Feedback for Test User - Day 1 breakfast"
        self.assertEqual(str(feedback), expected)