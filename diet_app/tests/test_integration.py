"""Integration tests for diet_app full workflow."""
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
import json

from diet_app.models import UserProfile, DietPlan, Feedback


class IntegrationFlowTests(TestCase):
    """Integration tests for complete user workflow."""

    def setUp(self):
        self.client = APIClient()
        self.valid_profile_data = {
            'name': 'Integration User',
            'age': 28,
            'gender': 'female',
            'height': 165.0,
            'weight': 60.0,
            'activity_level': 'light',
            'goal': 'maintain',
            'diet_type': 'vegetarian',
            'medical_conditions': 'None',
            'allergies': 'nuts',
            'favorite_foods': 'tofu, quinoa',
            'disliked_foods': 'mushrooms',
        }

    @patch('diet_app.ai_engine.generate_diet_plan')
    def test_complete_user_workflow(self, mock_generate):
        """Test complete workflow: create profile -> generate plan -> history -> rate -> download."""
        # Mock Gemini to return a valid plan
        mock_generate.return_value = {
            'total_calories_per_day': 2000,
            'nutritional_summary': {
                'daily_protein': '80g',
                'daily_carbs': '250g',
                'daily_fat': '70g',
                'daily_fiber': '30g',
            },
            'days': [
                {
                    'day': 'Day {}'.format(i),
                    'meals': [
                        {
                            'meal_type': 'Breakfast',
                            'time': '7:30 AM',
                            'food_items': ['Oatmeal with berries', 'Green tea'],
                            'calories': 350,
                            'protein': '12g',
                            'carbs': '55g',
                            'fat': '8g',
                        },
                        {
                            'meal_type': 'Lunch',
                            'time': '1:00 PM',
                            'food_items': ['Quinoa salad', 'Chickpeas', 'Mixed vegetables'],
                            'calories': 550,
                            'protein': '20g',
                            'carbs': '70g',
                            'fat': '15g',
                        },
                        {
                            'meal_type': 'Snack',
                            'time': '4:00 PM',
                            'food_items': ['Apple', 'Almond butter'],
                            'calories': 150,
                            'protein': '3g',
                            'carbs': '20g',
                            'fat': '7g',
                        },
                        {
                            'meal_type': 'Dinner',
                            'time': '7:00 PM',
                            'food_items': ['Vegetable stir-fry', 'Brown rice', 'Tofu'],
                            'calories': 600,
                            'protein': '25g',
                            'carbs': '75g',
                            'fat': '20g',
                        },
                    ],
                } for i in range(1, 8)
            ],
            'tips': [
                'Drink plenty of water',
                'Eat slowly and mindfully',
                'Include protein in every meal',
            ],
        }

        # Step 1: Create profile
        response = self.client.post(
            '/api/create-profile/',
            self.valid_profile_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['success'])
        profile_id = data['profile_id']

        # Step 2: Generate diet plan
        response = self.client.post(
            '/api/generate-plan/',
            {'profile_id': profile_id},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['success'])
        plan_id = data['diet_plan_id']
        generated_plan = data['diet_plan']

        # Verify plan structure
        self.assertEqual(generated_plan['total_calories_per_day'], 2000)
        self.assertEqual(len(generated_plan['days']), 7)
        for day in generated_plan['days']:
            self.assertEqual(len(day['meals']), 4)

        # Step 3: Get history
        response = self.client.get('/api/history/{}/'.format(profile_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['history']), 1)
        self.assertEqual(data['history'][0]['id'], plan_id)

        # Step 4: Rate the plan
        response = self.client.post(
            '/api/rate-plan/',
            {'diet_plan_id': plan_id, 'rating': 5, 'feedback': 'Excellent plan!'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['success'])

        # Verify rating saved
        plan = DietPlan.objects.get(id=plan_id)
        self.assertEqual(plan.rating, 5)
        self.assertEqual(plan.feedback_text, 'Excellent plan!')

        # Step 5: Download PDF
        response = self.client.get('/api/download-pdf/{}/'.format(plan_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment', response['Content-Disposition'])

    @patch('diet_app.views.generate_diet_plan')
    def test_multiple_plans_for_same_profile(self, mock_generate):
        """Test generating multiple plans for the same profile."""
        mock_generate.return_value = {
            'total_calories_per_day': 2000,
            'nutritional_summary': {'daily_protein': '80g', 'daily_carbs': '250g', 'daily_fat': '70g', 'daily_fiber': '30g'},
            'days': [
                {'day': 'Day {}'.format(i), 'meals': [
                    {'meal_type': 'Breakfast', 'time': '7:00', 'food_items': ['A'], 'calories': 300, 'protein': '10g', 'carbs': '40g', 'fat': '5g'},
                    {'meal_type': 'Lunch', 'time': '12:00', 'food_items': ['B'], 'calories': 500, 'protein': '20g', 'carbs': '60g', 'fat': '15g'},
                    {'meal_type': 'Snack', 'time': '3:00', 'food_items': ['C'], 'calories': 150, 'protein': '5g', 'carbs': '20g', 'fat': '5g'},
                    {'meal_type': 'Dinner', 'time': '7:00', 'food_items': ['D'], 'calories': 550, 'protein': '25g', 'carbs': '70g', 'fat': '20g'},
                ]} for i in range(1, 8)
            ],
            'tips': ['Tip'],
        }

        # Create profile
        response = self.client.post('/api/create-profile/', self.valid_profile_data, format='json')
        profile_id = response.json()['profile_id']

        # Generate first plan
        response = self.client.post('/api/generate-plan/', {'profile_id': profile_id}, format='json')
        plan1_id = response.json()['diet_plan_id']

        # Generate second plan
        response = self.client.post('/api/generate-plan/', {'profile_id': profile_id}, format='json')
        plan2_id = response.json()['diet_plan_id']

        # Both should succeed and be different
        self.assertNotEqual(plan1_id, plan2_id)

        # History should show both
        response = self.client.get('/api/history/{}/'.format(profile_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data['history']), 2)

    @patch('diet_app.views.generate_diet_plan')
    def test_feedback_on_specific_meals(self, mock_generate):
        """Test submitting feedback for specific meals."""
        mock_generate.return_value = {
            'total_calories_per_day': 2000,
            'nutritional_summary': {'daily_protein': '80g', 'daily_carbs': '250g', 'daily_fat': '70g', 'daily_fiber': '30g'},
            'days': [
                {'day': 'Day {}'.format(i), 'meals': [
                    {'meal_type': 'Breakfast', 'time': '7:00', 'food_items': ['A'], 'calories': 300, 'protein': '10g', 'carbs': '40g', 'fat': '5g'},
                    {'meal_type': 'Lunch', 'time': '12:00', 'food_items': ['B'], 'calories': 500, 'protein': '20g', 'carbs': '60g', 'fat': '15g'},
                    {'meal_type': 'Snack', 'time': '3:00', 'food_items': ['C'], 'calories': 150, 'protein': '5g', 'carbs': '20g', 'fat': '5g'},
                    {'meal_type': 'Dinner', 'time': '7:00', 'food_items': ['D'], 'calories': 550, 'protein': '25g', 'carbs': '70g', 'fat': '20g'},
                ]} for i in range(1, 8)
            ],
            'tips': ['Tip'],
        }

        # Setup
        response = self.client.post('/api/create-profile/', self.valid_profile_data, format='json')
        profile_id = response.json()['profile_id']
        response = self.client.post('/api/generate-plan/', {'profile_id': profile_id}, format='json')
        plan_id = response.json()['diet_plan_id']

        # Add feedback for different meals via the rate-plan endpoint
        # Note: /api/rate-plan/ updates DietPlan.rating and feedback_text, not the Feedback model
        feedback_data = [
            {'diet_plan_id': plan_id, 'rating': 5, 'feedback': 'Love the oatmeal!'},
            {'diet_plan_id': plan_id, 'rating': 4, 'feedback': 'Good portion'},
            {'diet_plan_id': plan_id, 'rating': 3, 'feedback': 'A bit salty'},
        ]

        for fb in feedback_data:
            response = self.client.post('/api/rate-plan/', fb, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.json()['success'])

        # Verify only the last rating is saved (endpoint overwrites)
        plan = DietPlan.objects.get(id=plan_id)
        self.assertEqual(plan.rating, 3)
        self.assertEqual(plan.feedback_text, 'A bit salty')

    def test_error_handling_invalid_input(self):
        """Test error handling for various invalid inputs."""
        # Invalid profile creation
        response = self.client.post('/api/create-profile/', {'name': 'Test'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('errors', data)

        # Missing profile_id for plan generation
        response = self.client.post('/api/generate-plan/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid profile_id
        response = self.client.post('/api/generate-plan/', {'profile_id': 99999}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Invalid plan_id for rating
        response = self.client.post('/api/rate-plan/', {'diet_plan_id': 99999, 'rating': 5}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Invalid plan_id for PDF
        response = self.client.get('/api/download-pdf/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Missing rating
        response = self.client.post('/api/rate-plan/', {'diet_plan_id': 1}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('diet_app.views.generate_diet_plan')
    def test_different_diet_types(self, mock_generate):
        """Test workflow with different diet types."""
        diet_types = ['vegetarian', 'non_vegetarian', 'vegan', 'keto', 'paleo']

        for diet_type in diet_types:
            mock_generate.return_value = {
                'total_calories_per_day': 2000,
                'nutritional_summary': {'daily_protein': '80g', 'daily_carbs': '250g', 'daily_fat': '70g', 'daily_fiber': '30g'},
                'days': [
                    {'day': 'Day {}'.format(i), 'meals': [
                        {'meal_type': 'Breakfast', 'time': '7:00', 'food_items': ['Food'], 'calories': 300, 'protein': '10g', 'carbs': '40g', 'fat': '5g'},
                        {'meal_type': 'Lunch', 'time': '12:00', 'food_items': ['Food'], 'calories': 500, 'protein': '20g', 'carbs': '60g', 'fat': '15g'},
                        {'meal_type': 'Snack', 'time': '3:00', 'food_items': ['Food'], 'calories': 150, 'protein': '5g', 'carbs': '20g', 'fat': '5g'},
                        {'meal_type': 'Dinner', 'time': '7:00', 'food_items': ['Food'], 'calories': 550, 'protein': '25g', 'carbs': '70g', 'fat': '20g'},
                    ]} for i in range(1, 8)
                ],
                'tips': ['Tip for {}'.format(diet_type)],
            }

            data = self.valid_profile_data.copy()
            data['diet_type'] = diet_type
            data['name'] = 'User {}'.format(diet_type)

            response = self.client.post('/api/create-profile/', data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            profile_id = response.json()['profile_id']

            response = self.client.post('/api/generate-plan/', {'profile_id': profile_id}, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.json()['success'])

            # Verify plan was created with correct diet_type
            plan_id = response.json()['diet_plan_id']
            plan = DietPlan.objects.get(id=plan_id)
            self.assertEqual(plan.user_profile.diet_type, diet_type)


class EdgeCaseTests(TestCase):
    """Tests for edge cases and boundary conditions."""

    def setUp(self):
        self.client = APIClient()

    def test_bmi_edge_cases(self):
        """Test BMI calculation at boundary values."""
        edge_cases = [
            # (height_cm, weight_kg, expected_bmi)
            (100, 30, 30.0),      # Very short, light
            (250, 300, 48.0),     # Very tall, heavy
            (150, 150, 66.67),    # Extreme BMI
        ]

        for height, weight, expected_bmi in edge_cases:
            profile = UserProfile.objects.create(
                name='Test',
                age=25,
                gender='male',
                height=height,
                weight=weight,
                activity_level='sedentary',
                goal='maintain',
                diet_type='vegetarian',
            )
            self.assertAlmostEqual(profile.bmi, expected_bmi, places=1)

    def test_plan_with_empty_days(self):
        """Test DietPlan with empty days array."""
        profile = UserProfile.objects.create(
            name='Test', age=25, gender='male',
            height=175, weight=70,
            activity_level='sedentary', goal='maintain', diet_type='vegetarian',
        )
        plan = DietPlan.objects.create(
            user_profile=profile,
            plan_data={'total_calories_per_day': 2000, 'days': []},
        )
        # plan_summary returns "0 day plan" for empty days
        self.assertEqual(plan.plan_summary, '0 day plan')

    def test_unicode_in_fields(self):
        """Test handling of unicode characters in text fields."""
        profile = UserProfile.objects.create(
            name='用户',
            age=25,
            gender='male',
            height=175.0,
            weight=70.0,
            activity_level='sedentary',
            goal='maintain',
            diet_type='vegetarian',
            medical_conditions='糖尿病',
            allergies='花生',
            favorite_foods='寿司, 拉面',
            disliked_foods='香菜',
        )
        self.assertEqual(profile.name, '用户')
        self.assertEqual(profile.medical_conditions, '糖尿病')

    def test_large_food_items_array(self):
        """Test meal with many food items."""
        profile = UserProfile.objects.create(
            name='Test', age=25, gender='male',
            height=175, weight=70,
            activity_level='sedentary', goal='maintain', diet_type='vegetarian',
        )
        plan = DietPlan.objects.create(
            user_profile=profile,
            plan_data={
                'total_calories_per_day': 2000,
                'days': [
                    {
                        'day': 'Day 1',
                        'meals': [
                            {
                                'meal_type': 'Breakfast',
                                'time': '7:00',
                                'food_items': ['Item {}'.format(i) for i in range(20)],
                                'calories': 500,
                                'protein': '20g',
                                'carbs': '80g',
                                'fat': '10g',
                            },
                        ],
                    },
                ],
            },
        )
        self.assertEqual(len(plan.plan_data['days'][0]['meals'][0]['food_items']), 20)