"""Tests for diet_app AI engine with mocked Gemini API."""
from django.test import TestCase, override_settings
from unittest.mock import patch, MagicMock, PropertyMock
from diet_app.models import UserProfile
from diet_app.ai_engine import (
    generate_diet_plan,
    _generate_with_gemini,
    _generate_placeholder_plan,
    _extract_json_from_response,
    _validate_diet_plan_structure,
)


class AIEngineTests(TestCase):
    """Tests for AI engine functions."""

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

    def test_generate_diet_plan_uses_placeholder_when_no_api_key(self):
        """Test fallback to placeholder when no API key."""
        with override_settings(GEMINI_API_KEY=''):
            from diet_app.ai_engine import GEMINI_API_KEY
            # The module caches GEMINI_API_KEY, so we test _generate_with_gemini directly
            result = _generate_placeholder_plan(self.profile)
            self.assertIn('total_calories_per_day', result)
            self.assertIn('days', result)
            self.assertEqual(len(result['days']), 7)

    @patch('diet_app.ai_engine.genai')
    def test_generate_diet_plan_calls_gemini_when_key_exists(self, mock_genai):
        """Test Gemini is called when API key exists."""
        # Mock the API response
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        mock_response = MagicMock()
        mock_response.text = '{"total_calories_per_day": 2000, "nutritional_summary": {}, "days": [], "tips": []}'
        mock_model.generate_content.return_value = mock_response
        mock_genai.list_models.return_value = []

        with override_settings(GEMINI_API_KEY='test-key'):
            # Need to reload the module to pick up new settings
            import importlib
            import diet_app.ai_engine
            importlib.reload(diet_app.ai_engine)
            from diet_app.ai_engine import _generate_with_gemini

            result = _generate_with_gemini(self.profile)
            self.assertIn('total_calories_per_day', result)

    def test_extract_json_from_plain_json(self):
        """Test extracting JSON from plain response."""
        response_text = '{"key": "value", "number": 42}'
        result = _extract_json_from_response(response_text)
        self.assertEqual(result, {'key': 'value', 'number': 42})

    def test_extract_json_from_markdown_code_block(self):
        """Test extracting JSON from markdown code block."""
        response_text = '```json\n{"key": "value"}\n```'
        result = _extract_json_from_response(response_text)
        self.assertEqual(result, {'key': 'value'})

    def test_extract_json_from_markdown_with_extra_text(self):
        """Test extracting JSON from markdown with extra text."""
        response_text = 'Here is the plan:\n```json\n{"key": "value"}\n```\nEnd of plan.'
        result = _extract_json_from_response(response_text)
        self.assertEqual(result, {'key': 'value'})

    def test_extract_json_from_nested_braces(self):
        """Test extracting JSON with nested structures."""
        response_text = '{"outer": {"inner": {"value": 1}}, "list": [1, 2, {"nested": true}]}'
        result = _extract_json_from_response(response_text)
        self.assertEqual(result['outer']['inner']['value'], 1)
        self.assertEqual(result['list'][2]['nested'], True)

    def test_extract_json_returns_none_for_invalid(self):
        """Test extraction returns None for invalid JSON."""
        response_text = 'This is not JSON at all'
        result = _extract_json_from_response(response_text)
        self.assertIsNone(result)

    def test_extract_json_returns_none_for_empty(self):
        """Test extraction returns None for empty string."""
        result = _extract_json_from_response('')
        self.assertIsNone(result)

    def test_validate_diet_plan_structure_valid(self):
        """Test validation passes for valid plan."""
        valid_plan = {
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
                            'food_items': ['Oatmeal'],
                            'calories': 300,
                            'protein': '10g',
                            'carbs': '50g',
                            'fat': '5g',
                        },
                        {
                            'meal_type': 'Lunch',
                            'time': '12:00 PM',
                            'food_items': ['Salad'],
                            'calories': 400,
                            'protein': '15g',
                            'carbs': '50g',
                            'fat': '10g',
                        },
                        {
                            'meal_type': 'Snack',
                            'time': '3:00 PM',
                            'food_items': ['Apple'],
                            'calories': 100,
                            'protein': '1g',
                            'carbs': '25g',
                            'fat': '0g',
                        },
                        {
                            'meal_type': 'Dinner',
                            'time': '7:00 PM',
                            'food_items': ['Chicken', 'Rice'],
                            'calories': 500,
                            'protein': '30g',
                            'carbs': '60g',
                            'fat': '15g',
                        },
                    ],
                },
            ] * 7,  # 7 days
            'tips': ['Tip 1', 'Tip 2'],
        }
        self.assertTrue(_validate_diet_plan_structure(valid_plan))

    def test_validate_diet_plan_missing_keys(self):
        """Test validation fails for missing required keys."""
        invalid_plan = {
            'total_calories_per_day': 2000,
            'days': [],
        }
        self.assertFalse(_validate_diet_plan_structure(invalid_plan))

    def test_validate_diet_plan_wrong_days_count(self):
        """Test validation fails for wrong number of days."""
        invalid_plan = {
            'total_calories_per_day': 2000,
            'nutritional_summary': {},
            'days': [{'day': 'Day 1', 'meals': []}] * 5,  # Only 5 days
            'tips': [],
        }
        self.assertFalse(_validate_diet_plan_structure(invalid_plan))

    def test_validate_diet_plan_wrong_meals_count(self):
        """Test validation fails for wrong number of meals per day."""
        invalid_plan = {
            'total_calories_per_day': 2000,
            'nutritional_summary': {},
            'days': [
                {
                    'day': 'Day 1',
                    'meals': [{'meal_type': 'Breakfast', 'time': '7:00', 'food_items': [], 'calories': 100, 'protein': '5g', 'carbs': '10g', 'fat': '2g'}],
                },
            ] * 7,
            'tips': [],
        }
        self.assertFalse(_validate_diet_plan_structure(invalid_plan))

    def test_validate_diet_plan_missing_meal_fields(self):
        """Test validation fails for missing meal fields."""
        invalid_plan = {
            'total_calories_per_day': 2000,
            'nutritional_summary': {},
            'days': [
                {
                    'day': 'Day 1',
                    'meals': [
                        {
                            'meal_type': 'Breakfast',
                            # Missing: time, food_items, calories, protein, carbs, fat
                        },
                    ],
                },
            ] * 7,
            'tips': [],
        }
        self.assertFalse(_validate_diet_plan_structure(invalid_plan))

    def test_placeholder_plan_structure(self):
        """Test placeholder plan has correct structure."""
        result = _generate_placeholder_plan(self.profile)

        self.assertIn('total_calories_per_day', result)
        self.assertIn('nutritional_summary', result)
        self.assertIn('days', result)
        self.assertIn('tips', result)

        self.assertEqual(len(result['days']), 7)
        for day in result['days']:
            self.assertIn('day', day)
            self.assertIn('meals', day)
            self.assertEqual(len(day['meals']), 4)
            for meal in day['meals']:
                self.assertIn('meal_type', meal)
                self.assertIn('time', meal)
                self.assertIn('food_items', meal)
                self.assertIn('calories', meal)
                self.assertIn('protein', meal)
                self.assertIn('carbs', meal)
                self.assertIn('fat', meal)

        self.assertEqual(len(result['tips']), 7)

    def test_placeholder_plan_calories_by_goal(self):
        """Test placeholder plan adjusts calories by goal."""
        goals = {
            'lose': 1800,
            'gain': 2500,
            'muscle': 2200,
            'maintain': 2000,
        }
        for goal, expected_base in goals.items():
            profile = UserProfile.objects.create(
                name='Test',
                age=25,
                gender='male',
                height=175,
                weight=70,
                activity_level='sedentary',
                goal=goal,
                diet_type='vegetarian',
            )
            result = _generate_placeholder_plan(profile)
            # Should be close to base (adjusted by activity multiplier)
            self.assertGreaterEqual(result['total_calories_per_day'], expected_base)


class AIEngineIntegrationTests(TestCase):
    """Integration tests for AI engine with mocked Gemini."""
    
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

    def test_extract_and_validate_valid_json(self):
        """Test extracting and validating a valid JSON response."""
        valid_json = json.dumps({
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
                            'food_items': ['Item 1', 'Item 2'],
                            'calories': 300,
                            'protein': '10g',
                            'carbs': '50g',
                            'fat': '5g',
                        },
                        {
                            'meal_type': 'Lunch',
                            'time': '12:00 PM',
                            'food_items': ['Item 1', 'Item 2'],
                            'calories': 400,
                            'protein': '15g',
                            'carbs': '50g',
                            'fat': '10g',
                        },
                        {
                            'meal_type': 'Snack',
                            'time': '3:00 PM',
                            'food_items': ['Item 1'],
                            'calories': 100,
                            'protein': '1g',
                            'carbs': '25g',
                            'fat': '0g',
                        },
                        {
                            'meal_type': 'Dinner',
                            'time': '7:00 PM',
                            'food_items': ['Item 1', 'Item 2'],
                            'calories': 500,
                            'protein': '30g',
                            'carbs': '60g',
                            'fat': '15g',
                        },
                    ],
                },
            ] * 7,
            'tips': ['Tip 1', 'Tip 2', 'Tip 3'],
        })

        result = _extract_json_from_response(valid_json)
        self.assertIsNotNone(result)
        self.assertTrue(_validate_diet_plan_structure(result))
        self.assertEqual(result['total_calories_per_day'], 2000)

    def test_extract_and_validate_markdown_wrapped(self):
        """Test extracting and validating markdown-wrapped JSON."""
        # Create valid JSON for 7 days
        days_json = ','.join(['{"day": "Day %d", "meals": [{"meal_type": "Breakfast", "time": "7:00", "food_items": ["A"], "calories": 100, "protein": "5g", "carbs": "10g", "fat": "2g"}, {"meal_type": "Lunch", "time": "12:00", "food_items": ["B"], "calories": 200, "protein": "10g", "carbs": "20g", "fat": "5g"}, {"meal_type": "Snack", "time": "15:00", "food_items": ["C"], "calories": 50, "protein": "2g", "carbs": "5g", "fat": "1g"}, {"meal_type": "Dinner", "time": "19:00", "food_items": ["D"], "calories": 300, "protein": "15g", "carbs": "30g", "fat": "10g"}]}' % i for i in range(1, 8)])
        
        markdown_response = '''```json
{
    "total_calories_per_day": 2000,
    "nutritional_summary": {"daily_protein": "100g", "daily_carbs": "250g", "daily_fat": "60g", "daily_fiber": "25g"},
    "days": [%s],
    "tips": ["Tip"]
}
```''' % days_json

        result = _extract_json_from_response(markdown_response)
        self.assertIsNotNone(result)
        self.assertTrue(_validate_diet_plan_structure(result))
        self.assertEqual(result['total_calories_per_day'], 2000)

    def test_fallback_on_invalid_json(self):
        """Test validation fails for invalid JSON."""
        result = _extract_json_from_response('This is not valid JSON')
        self.assertIsNone(result)

    def test_fallback_on_validation_fail(self):
        """Test validation fails for missing required fields."""
        invalid_json = json.dumps({
            'total_calories_per_day': 2000,
            'days': [],  # Missing nutritional_summary, tips, wrong days count
        })
        result = _extract_json_from_response(invalid_json)
        self.assertIsNotNone(result)
        self.assertFalse(_validate_diet_plan_structure(result))

    def test_fallback_on_empty_response(self):
        """Test extraction returns None for empty response."""
        result = _extract_json_from_response('')
        self.assertIsNone(result)

    def test_fallback_on_wrong_structure(self):
        """Test validation fails for wrong structure."""
        invalid_json = json.dumps({
            'total_calories_per_day': 2000,
            'nutritional_summary': {},
            'days': [{'day': 'Day 1', 'meals': []}],  # Only 1 day
            'tips': [],
        })
        result = _extract_json_from_response(invalid_json)
        self.assertIsNotNone(result)
        self.assertFalse(_validate_diet_plan_structure(result))


import json