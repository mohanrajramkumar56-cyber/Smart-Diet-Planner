"""Tests for diet_app API views."""
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
import json

from diet_app.models import UserProfile, DietPlan, Feedback


class APIViewTests(TestCase):
    """Tests for API views."""

    def setUp(self):
        self.client = APIClient()
        self.valid_profile_data = {
            'name': 'Test User',
            'age': 30,
            'gender': 'male',
            'height': 175.0,
            'weight': 70.0,
            'activity_level': 'moderate',
            'goal': 'lose',
            'diet_type': 'vegetarian',
            'medical_conditions': '',
            'allergies': '',
            'favorite_foods': 'chicken, rice',
            'disliked_foods': '',
        }

    @patch('diet_app.ai_engine.generate_diet_plan')
    def test_create_user_profile(self, mock_generate):
        """Test creating a user profile via API."""
        response = self.client.post(
            '/api/create-profile/',
            self.valid_profile_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('profile_id', data)
        self.assertEqual(data['message'], 'Profile created successfully')

        # Verify profile was created in DB
        profile = UserProfile.objects.get(id=data['profile_id'])
        self.assertEqual(profile.name, 'Test User')

    @patch('diet_app.ai_engine.generate_diet_plan')
    def test_create_user_profile_invalid_data(self, mock_generate):
        """Test creating profile with invalid data."""
        response = self.client.post(
            '/api/create-profile/',
            {'name': 'Test'},  # Missing required fields
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('errors', data)
        self.assertIn('age', data['errors'])

    @patch('diet_app.views.generate_diet_plan')
    def test_generate_diet_plan_success(self, mock_generate):
        """Test generating diet plan successfully."""
        mock_generate.return_value = {
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
            'tips': ['Drink water'],
        }

        # Create profile first
        profile_response = self.client.post(
            '/api/create-profile/',
            self.valid_profile_data,
            format='json'
        )
        profile_id = profile_response.json()['profile_id']

        # Generate plan
        response = self.client.post(
            '/api/generate-plan/',
            {'profile_id': profile_id},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('diet_plan_id', data)
        self.assertIn('diet_plan', data)
        self.assertEqual(data['message'], 'AI Diet plan generated successfully!')

        # Verify plan was saved
        plan = DietPlan.objects.get(id=data['diet_plan_id'])
        self.assertEqual(plan.user_profile_id, profile_id)

    def test_generate_diet_plan_missing_profile_id(self):
        """Test generating plan without profile_id."""
        response = self.client.post(
            '/api/generate-plan/',
            {},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Profile ID is required')

    def test_generate_diet_plan_invalid_profile_id(self):
        """Test generating plan with invalid profile_id returns 404."""
        response = self.client.post(
            '/api/generate-plan/',
            {'profile_id': 99999},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('diet_app.ai_engine.generate_diet_plan')
    def test_generate_diet_plan_returns_fallback(self, mock_generate):
        """Test that view returns 500 when AI returns None."""
        mock_generate.return_value = None  # Simulate AI failure

        profile_response = self.client.post(
            '/api/create-profile/',
            self.valid_profile_data,
            format='json'
        )
        profile_id = profile_response.json()['profile_id']

        response = self.client.post(
            '/api/generate-plan/',
            {'profile_id': profile_id},
            format='json'
        )
        # When AI returns None, view returns 500 (fallback is in ai_engine, not view)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('error', data)

    def test_get_diet_history(self):
        """Test getting diet history for a profile."""
        profile = UserProfile.objects.create(**self.valid_profile_data)
        plan = DietPlan.objects.create(
            user_profile=profile,
            plan_data={'days': [], 'total_calories_per_day': 2000},
        )

        response = self.client.get('/api/history/{}/'.format(profile.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['history']), 1)
        self.assertEqual(data['history'][0]['id'], plan.id)

    def test_get_diet_history_invalid_profile(self):
        """Test getting history for invalid profile returns 404."""
        response = self.client.get('/api/history/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_rate_diet_plan(self):
        """Test rating a diet plan."""
        profile = UserProfile.objects.create(**self.valid_profile_data)
        plan = DietPlan.objects.create(
            user_profile=profile,
            plan_data={'days': [], 'total_calories_per_day': 2000},
        )

        response = self.client.post(
            '/api/rate-plan/',
            {'diet_plan_id': plan.id, 'rating': 5, 'feedback': 'Great!'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Rating saved successfully!')

        # Verify rating was saved
        plan.refresh_from_db()
        self.assertEqual(plan.rating, 5)
        self.assertEqual(plan.feedback_text, 'Great!')

    def test_rate_diet_plan_missing_id(self):
        """Test rating without diet_plan_id."""
        response = self.client.post(
            '/api/rate-plan/',
            {'rating': 5},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Diet plan ID is required')

    def test_rate_diet_plan_missing_rating(self):
        """Test rating without rating value."""
        profile = UserProfile.objects.create(**self.valid_profile_data)
        plan = DietPlan.objects.create(
            user_profile=profile,
            plan_data={'days': [], 'total_calories_per_day': 2000},
        )

        response = self.client.post(
            '/api/rate-plan/',
            {'diet_plan_id': plan.id},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Rating is required')

    def test_rate_diet_plan_invalid_id(self):
        """Test rating invalid diet plan returns 404."""
        response = self.client.post(
            '/api/rate-plan/',
            {'diet_plan_id': 99999, 'rating': 5},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_download_pdf(self):
        """Test downloading diet plan as PDF."""
        profile = UserProfile.objects.create(**self.valid_profile_data)
        plan = DietPlan.objects.create(
            user_profile=profile,
            plan_data={
                'days': [
                    {
                        'day': 'Day 1',
                        'meals': [
                            {
                                'meal_type': 'Breakfast',
                                'time': '7:00 AM',
                                'food_items': ['Oatmeal'],
                                'calories': 300,
                                'protein': '10g',
                                'carbs': '50g',
                                'fat': '5g',
                            },
                        ],
                    },
                ],
                'total_calories_per_day': 2000,
            },
        )

        response = self.client.get('/api/download-pdf/{}/'.format(plan.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment', response['Content-Disposition'])

    def test_download_pdf_invalid_id(self):
        """Test downloading PDF for invalid plan returns 404."""
        response = self.client.get('/api/download-pdf/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_home_page(self):
        """Test home page loads."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')

    def test_admin_page(self):
        """Test admin page redirects to login."""
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)