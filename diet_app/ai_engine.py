"""
AI Engine for generating personalized diet plans using Google Gemini API (google-genai SDK).
"""
import json
import os
import uuid
import random
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

# Initialize client
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
    print("Gemini API configured successfully (google-genai SDK)")
else:
    print("Warning: GEMINI_API_KEY not set. Using placeholder diet plans.")
    client = None


def generate_diet_plan(user_profile):
    """
    Generate a personalized diet plan using Gemini AI.

    Args:
        user_profile: UserProfile instance with user health data

    Returns:
        dict: Complete diet plan with daily meals and nutritional info
    """

    # Try to use Gemini API
    if client:
        return _generate_with_gemini(user_profile)
    else:
        # Fallback to placeholder plan
        return _generate_placeholder_plan(user_profile)


def _generate_with_gemini(user_profile):
    """Generate diet plan using Gemini AI (google-genai SDK)."""
    try:
        # Build user context
        country_name = ''
        if user_profile.country:
            try:
                country_obj = pycountry.countries.get(alpha_2=user_profile.country)
                if country_obj:
                    country_name = country_obj.name
            except:
                country_name = user_profile.country
        
        user_context = f"""
        User Profile:
        - Name: {user_profile.name}
        - Age: {user_profile.age}
        - Gender: {user_profile.gender}
        - Height: {user_profile.height} cm
        - Weight: {user_profile.weight} kg
        - BMI: {user_profile.bmi}
        - Activity Level: {user_profile.activity_level}
        - Goal: {user_profile.goal}
        - Diet Type: {user_profile.diet_type}
        - Country: {country_name or 'Not specified'}
        - Medical Conditions: {user_profile.medical_conditions or 'None'}
        - Allergies: {user_profile.allergies or 'None'}
        - Favorite Foods: {user_profile.favorite_foods or 'None'}
        - Disliked Foods: {user_profile.disliked_foods or 'None'}
        """

        # Detect cuisine preference (simple heuristic: user may include 'south' or 'south indian')
        fav_foods_lower = (user_profile.favorite_foods or '').lower()
        prefers_south_indian = 'south' in fav_foods_lower or 'south indian' in fav_foods_lower or 'south_indian' in fav_foods_lower

        # Create a per-request variation seed to encourage unique outputs per user/call.
        # Also include the profile id/created_at so the prompt is user-specific.
        variation_seed = str(uuid.uuid4())[:8]
        profile_token = getattr(user_profile, 'id', None) or getattr(user_profile, 'created_at', '')

        # Enhanced prompt: ask the model to diversify meals across days and to prioritize
        # South Indian recipes when the user prefers them. Also request only JSON output
        # and ask the model to vary menus when asked multiple times.
        prompt = f"""
        Based on the following user profile, generate a detailed 7-day personalized diet plan in JSON format only.
        Do NOT include any extra explanation or commentary—only valid JSON.

        {user_context}

        Important instructions for variety and regional preferences:
        - Vary meals across the 7 days; avoid repeating the exact same meal more than once.
        - If this function is called multiple times for the same user, produce a different but
          nutritionally equivalent plan (introduce reasonable variation in recipes and timings).
        - Generate meals appropriate for the user's country ({country_name or 'international'}) cuisine.
          Use authentic ingredients, cooking methods, and traditional dishes from that cuisine.
        - If the user prefers South Indian food (detected below), prioritize South Indian
          breakfast/lunch/dinner options while keeping snacks balanced and aligned with the diet type.

        Preferences detected: prefers_south_indian={prefers_south_indian}
        Profile token: {profile_token}
        Variation seed: {variation_seed}

        Output JSON structure (example):
        {{
            "total_calories_per_day": 2000,
            "nutritional_summary": {{"daily_protein": "100g", "daily_carbs": "250g", "daily_fat": "60g", "daily_fiber": "25g"}},
            "days": [{{"day": "Day 1", "meals": [{{"meal_type":"Breakfast","time":"7:00 AM","food_items":["idli","sambar","coconut chutney"],"calories":300,"protein":"12g","carbs":"45g","fat":"8g"}}]}}],
            "tips": ["Tip 1", "Tip 2"]
        }}

        Requirements:
        - Follow the user's `diet_type`: {user_profile.diet_type}
        - Align with user's goal: {user_profile.goal}
        - Avoid allergens: {user_profile.allergies or 'None'}
        - Exclude disliked foods: {user_profile.disliked_foods or 'None'}
        - Prefer favorite foods: {user_profile.favorite_foods or 'None'}
        - Consider medical conditions: {user_profile.medical_conditions or 'None'}
        - Provide 7 full days with 4 meals per day (breakfast, lunch, dinner, snack)
        - Keep meals realistic, locally available, and easy to prepare
        - Ensure macros sum roughly to the daily calories and label grams for macros
        - Use authentic {country_name or 'international'} cuisine ingredients and cooking methods
        """

        # Model to use - google-genai uses model names directly
        model_name = 'gemini-2.5-flash'

        # Use higher temperature to encourage diversity
        temp = 0.85
        max_tokens = 16384

        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temp,
                    max_output_tokens=max_tokens,
                    response_mime_type="application/json"
                )
            )
        except Exception as e:
            print(f"Error with generation config: {e}")
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
            except Exception as fallback_error:
                print(f"Fallback generation failed: {fallback_error}")
                return _generate_placeholder_plan(user_profile)

        # Parse the response as JSON
        if not response or not hasattr(response, 'text'):
            print("Empty or invalid response from Gemini")
            return _generate_placeholder_plan(user_profile)

        response_text = response.text.strip()

        # Try to extract valid JSON from the response
        diet_plan = _extract_json_from_response(response_text)
        if diet_plan and _validate_diet_plan_structure(diet_plan):
            print("Successfully parsed and validated JSON from Gemini response")
            return diet_plan

        # If Gemini fails, fall back to placeholder
        print("Falling back to placeholder plan")
        return _generate_placeholder_plan(user_profile)

    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return _generate_placeholder_plan(user_profile)


def _extract_json_from_response(response_text: str) -> dict | None:
    """
    Robustly extract JSON from Gemini response.
    Handles markdown code blocks, extra text, and nested structures.
    """
    if not response_text:
        return None

    # First, try to extract from markdown code blocks
    if '```' in response_text:
        parts = response_text.split('```')
        for part in parts:
            part = part.strip()
            if part.startswith('json'):
                part = part[4:].strip()
            # Try to parse this part as JSON
            try:
                return json.loads(part)
            except (json.JSONDecodeError, ValueError):
                continue

    # If no code blocks or parsing failed, try to find JSON object in text
    # Use brace counting to handle nested structures correctly
    start_idx = response_text.find('{')
    if start_idx < 0:
        return None

    # Find the matching closing brace for the outermost object
    brace_count = 0
    end_idx = -1
    for i, char in enumerate(response_text[start_idx:], start=start_idx):
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                end_idx = i + 1
                break

    if end_idx > start_idx:
        json_str = response_text[start_idx:end_idx]
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"JSON parsing error: {e}")
            print(f"Response text preview: {response_text[:300]}")

    return None


def _validate_diet_plan_structure(diet_plan: dict) -> bool:
    """Validate that the parsed diet plan has the expected 7-day structure."""
    if not isinstance(diet_plan, dict):
        return False

    # Check required top-level keys
    required_keys = ['total_calories_per_day', 'nutritional_summary', 'days', 'tips']
    for key in required_keys:
        if key not in diet_plan:
            print(f"Validation failed: missing required key '{key}'")
            return False

    # Validate days structure
    days = diet_plan.get('days')
    if not isinstance(days, list) or len(days) != 7:
        print(f"Validation failed: 'days' must be a list of 7 elements, got {len(days) if isinstance(days, list) else type(days)}")
        return False

    for i, day in enumerate(days):
        if not isinstance(day, dict):
            print(f"Validation failed: day {i+1} is not a dict")
            return False
        if 'day' not in day or 'meals' not in day:
            print(f"Validation failed: day {i+1} missing 'day' or 'meals'")
            return False
        meals = day.get('meals')
        if not isinstance(meals, list) or len(meals) != 4:
            print(f"Validation failed: day {i+1} must have 4 meals, got {len(meals) if isinstance(meals, list) else type(meals)}")
            return False
        for meal in meals:
            if not isinstance(meal, dict):
                return False
            required_meal_keys = ['meal_type', 'time', 'food_items', 'calories', 'protein', 'carbs', 'fat']
            for mk in required_meal_keys:
                if mk not in meal:
                    print(f"Validation failed: meal missing '{mk}'")
                    return False

    return True


def _generate_placeholder_plan(user_profile):
    """Generate a placeholder diet plan when AI is not available."""

    # Calculate basic calories based on BMI and goal
    base_calories = 2000
    if user_profile.goal == 'lose':
        base_calories = 1800
    elif user_profile.goal == 'gain':
        base_calories = 2500
    elif user_profile.goal == 'muscle':
        base_calories = 2200

    # Adjust for activity level
    activity_multipliers = {
        'sedentary': 1.0,
        'light': 1.1,
        'moderate': 1.2,
        'active': 1.3,
        'very_active': 1.4,
    }
    total_calories = int(base_calories * activity_multipliers.get(user_profile.activity_level, 1.2))

    # Calculate macros
    protein_grams = int((total_calories * 0.30) / 4)  # 30% of calories, 4 cal/g
    carbs_grams = int((total_calories * 0.45) / 4)     # 45% of calories, 4 cal/g
    fat_grams = int((total_calories * 0.25) / 9)       # 25% of calories, 9 cal/g
    fiber_grams = 25

    # Get food items based on diet type
    diet_foods = _get_diet_foods(user_profile)

    # Build 7-day plan
    days = []
    for day_num in range(1, 8):
        # Helper to get random items
        def get_random_items(items, count):
            if not items:
                return []
            # If we have enough items, sample them. If not, take what we have and maybe duplicate/shuffle
            if len(items) >= count:
                return random.sample(items, count)
            return items # Return all if not enough

        meals = [
            {
                "meal_type": "Breakfast",
                "time": "7:00 AM",
                "food_items": get_random_items(diet_foods['breakfast'], 3),
                "calories": str(int(total_calories * 0.25)),
                "protein": f"{int(protein_grams * 0.25)}",
                "carbs": f"{int(carbs_grams * 0.25)}",
                "fat": f"{int(fat_grams * 0.25)}"
            },
            {
                "meal_type": "Lunch",
                "time": "12:30 PM",
                "food_items": get_random_items(diet_foods['lunch'], 3),
                "calories": str(int(total_calories * 0.35)),
                "protein": f"{int(protein_grams * 0.35)}",
                "carbs": f"{int(carbs_grams * 0.35)}",
                "fat": f"{int(fat_grams * 0.35)}"
            },
            {
                "meal_type": "Dinner",
                "time": "7:00 PM",
                "food_items": get_random_items(diet_foods['dinner'], 3),
                "calories": str(int(total_calories * 0.30)),
                "protein": f"{int(protein_grams * 0.30)}",
                "carbs": f"{int(carbs_grams * 0.30)}",
                "fat": f"{int(fat_grams * 0.30)}"
            },
            {
                "meal_type": "Snack",
                "time": "4:00 PM",
                "food_items": get_random_items(diet_foods['snack'], 2),
                "calories": str(int(total_calories * 0.10)),
                "protein": f"{int(protein_grams * 0.10)}",
                "carbs": f"{int(carbs_grams * 0.10)}",
                "fat": f"{int(fat_grams * 0.10)}"
            }
        ]

        days.append({
            "day": f"Day {day_num}",
            "meals": meals
        })

    return {
        "total_calories_per_day": total_calories,
        "nutritional_summary": {
            "daily_protein": f"{protein_grams}g",
            "daily_carbs": f"{carbs_grams}g",
            "daily_fat": f"{fat_grams}g",
            "daily_fiber": f"{fiber_grams}g"
        },
        "days": days,
        "tips": [
            "Drink at least 8-10 glasses of water daily",
            "Include colorful vegetables in every meal",
            "Prepare meals in advance to stay on track",
            f"Your goal is {user_profile.goal} - focus on consistency",
            "Track your meals and progress regularly",
            "Listen to your body and adjust portions as needed",
            "Consider consulting a nutritionist for personalized advice"
        ]
    }


def _get_diet_foods(user_profile):
    """Get food recommendations based on country cuisine, diet type, and preferences."""

    allergies = (user_profile.allergies or '').lower()
    disliked = (user_profile.disliked_foods or '').lower()
    fav_foods_lower = (user_profile.favorite_foods or '').lower()

    # Get country name
    country_name = ''
    if user_profile.country:
        try:
            country_obj = pycountry.countries.get(alpha_2=user_profile.country)
            if country_obj:
                country_name = country_obj.name
        except:
            country_name = user_profile.country

    # Country-based cuisine mapping with meal items
    # Each country has meals organized by breakfast, lunch, dinner, snack
    cuisine_db = {
        'India': {
            'vegetarian': {
                'breakfast': ['Idli with sambar and coconut chutney', 'Masala dosa with sambar', 'Rava upma with coconut chutney', 'Aloo paratha with yogurt', 'Poha with peanuts'],
                'lunch': ['Rajma chawal (kidney beans with rice)', 'Chana masala with roti', 'Vegetable biryani with raita', 'Dal tadka with jeera rice', 'Palak paneer with naan'],
                'dinner': ['Aloo gobi with roti', 'Baingan bharta with rice', 'Mixed vegetable curry with dal', 'Kadhi pakora with rice', 'Vegetable korma with chapati'],
                'snack': ['Roasted chana', 'Masala peanuts', 'Fruit chaat', 'Sprouts salad', 'Dhokla']
            },
            'non_vegetarian': {
                'breakfast': ['Egg bhurji with toast', 'Masala omelette with paratha', 'Chicken keema with pav', 'Egg curry with appam', 'Mutton keema with roti'],
                'lunch': ['Chicken biryani with raita', 'Butter chicken with naan', 'Fish curry with rice', 'Mutton rogan josh with rice', 'Chicken tikka masala with roti'],
                'dinner': ['Tandoori chicken with naan', 'Fish fry with dal rice', 'Chicken chettinad with appam', 'Mutton curry with rice', 'Prawn masala with roti'],
                'snack': ['Chicken tikka', 'Seekh kebab', 'Egg pakora', 'Chicken 65', 'Mutton samosa']
            }
        },
        'United States': {
            'vegetarian': {
                'breakfast': ['Oatmeal with berries and nuts', 'Avocado toast with eggs', 'Greek yogurt parfait with granola', 'Vegetable omelette with toast', 'Smoothie bowl with spinach'],
                'lunch': ['Quinoa salad with chickpeas', 'Grilled vegetable sandwich', 'Lentil soup with bread', 'Buddha bowl with tofu', 'Caprese salad with quinoa'],
                'dinner': ['Vegetable stir-fry with brown rice', 'Black bean tacos', 'Vegetable lasagna', 'Stuffed bell peppers', 'Portobello mushroom burger'],
                'snack': ['Apple with almond butter', 'Hummus with veggies', 'Trail mix', 'Greek yogurt', 'Energy bars']
            },
            'non_vegetarian': {
                'breakfast': ['Scrambled eggs with bacon', 'Chicken sausage with toast', 'Turkey bacon with eggs', 'Protein pancakes', 'Breakfast burrito'],
                'lunch': ['Grilled chicken salad', 'Turkey club sandwich', 'Tuna salad sandwich', 'Chicken wrap', 'BBQ chicken sandwich'],
                'dinner': ['Grilled salmon with asparagus', 'Chicken breast with sweet potato', 'Lean beef with roasted vegetables', 'Turkey meatballs with pasta', 'Grilled chicken with quinoa'],
                'snack': ['Beef jerky', 'Hard boiled eggs', 'Protein shake', 'Turkey roll-ups', 'Chicken salad']
            }
        },
        'Mexico': {
            'vegetarian': {
                'breakfast': ['Chilaquiles with eggs', 'Huevos rancheros', 'Bean and cheese quesadilla', 'Avocado toast with salsa', 'Chilaquiles verdes'],
                'lunch': ['Bean burrito bowl', 'Vegetable quesadilla', 'Black bean tacos', 'Vegetarian enchiladas', 'Nopales salad'],
                'dinner': ['Vegetable enchiladas', 'Bean and cheese burritos', 'Vegetable fajitas', 'Chiles rellenos', 'Vegetable tamales'],
                'snack': ['Guacamole with chips', 'Roasted corn', 'Jicama with chili', 'Fresh fruit with tajin', 'Churros']
            },
            'non_vegetarian': {
                'breakfast': ['Chilaquiles with chicken', 'Huevos rancheros with chorizo', 'Breakfast tacos', 'Machaca con huevo', 'Chilaquiles rojos'],
                'lunch': ['Chicken tacos', 'Carne asada burrito', 'Chicken quesadilla', 'Beef enchiladas', 'Carnitas bowl'],
                'dinner': ['Chicken mole', 'Carne asada with rice', 'Fish tacos', 'Chicken enchiladas', 'Beef fajitas'],
                'snack': ['Chicharrones', 'Beef jerky', 'Queso fundido', 'Chicken taquitos', 'Beef empanada']
            }
        },
        'Italy': {
            'vegetarian': {
                'breakfast': ['Cappuccino with cornetto', 'Frittata with vegetables', 'Ricotta toast with honey', 'Yogurt with granola', 'Panini with mozzarella'],
                'lunch': ['Pasta primavera', 'Margherita pizza', 'Risotto with vegetables', 'Pasta e fagioli', 'Caprese salad with bread'],
                'dinner': ['Eggplant parmigiana', 'Vegetable lasagna', 'Pasta with pesto', 'Ratatouille with polenta', 'Stuffed peppers'],
                'snack': ['Bruschetta', 'Olives', 'Cheese plate', 'Fruit', 'Gelato']
            },
            'non_vegetarian': {
                'breakfast': ['Prosciutto with melon', 'Eggs with prosciutto', 'Frittata with ham', 'Panini with salami', 'Cappuccino with pastry'],
                'lunch': ['Chicken parmigiana', 'Spaghetti carbonara', 'Chicken piccata', 'Beef bolognese', 'Prosciutto panini'],
                'dinner': ['Osso buco', 'Chicken marsala', 'Beef ragu', 'Saltimbocca', 'Grilled fish with lemon'],
                'snack': ['Prosciutto', 'Parmesan', 'Olives', 'Salami', 'Arancini']
            }
        },
        'Japan': {
            'vegetarian': {
                'breakfast': ['Miso soup with tofu', 'Rice with natto', 'Vegetable tamagoyaki', 'Grilled vegetables', 'Rice porridge'],
                'lunch': ['Vegetable sushi rolls', 'Vegetable tempura', 'Tofu donburi', 'Vegetable ramen', 'Inari sushi'],
                'dinner': ['Vegetable stir-fry with rice', 'Agedashi tofu', 'Vegetable curry rice', 'Grilled vegetables with rice', 'Miso eggplant'],
                'snack': ['Edamame', 'Mochi', 'Rice crackers', 'Fruit', 'Sweet potato']
            },
            'non_vegetarian': {
                'breakfast': ['Grilled salmon with rice', 'Tamagoyaki', 'Fish with miso soup', 'Natto with rice', 'Tamago kake gohan'],
                'lunch': ['Chicken teriyaki bowl', 'Salmon sushi', 'Beef gyudon', 'Chicken katsu', 'Unagi don'],
                'dinner': ['Grilled salmon', 'Chicken teriyaki', 'Beef sukiyaki', 'Tonkatsu', 'Miso black cod'],
                'snack': ['Yakitori', 'Fish cakes', 'Shrimp tempura', 'Onigiri', 'Karaage']
            }
        },
        'Thailand': {
            'vegetarian': {
                'breakfast': ['Rice porridge with vegetables', 'Sticky rice with mango', 'Vegetable spring rolls', 'Tofu scramble', 'Rice noodle soup'],
                'lunch': ['Pad thai with tofu', 'Green curry with vegetables', 'Papaya salad (no fish sauce)', 'Vegetable fried rice', 'Massaman curry with vegetables'],
                'dinner': ['Red curry with vegetables', 'Stir-fried vegetables', 'Pineapple fried rice', 'Vegetable pad see ew', 'Yellow curry with tofu'],
                'snack': ['Fresh spring rolls', 'Mango sticky rice', 'Banana fritters', 'Coconut ice cream', 'Roasted peanuts']
            },
            'non_vegetarian': {
                'breakfast': ['Khao tom with shrimp', 'Kai jeow (Thai omelette)', 'Rice porridge with pork', 'Grilled pork with rice', 'Khanom jeen'],
                'lunch': ['Pad thai with shrimp', 'Green curry chicken', 'Pad kra pao (basil chicken)', 'Tom yum goong', 'Massaman curry beef'],
                'dinner': ['Pad thai with chicken', 'Green curry beef', 'Grilled fish with herbs', 'Panang curry chicken', 'Stir-fried basil pork'],
                'snack': ['Satay chicken', 'Fish cakes', 'Spring rolls', 'Grilled pork skewers', 'Shrimp cakes']
            }
        },
        'China': {
            'vegetarian': {
                'breakfast': ['Congee with pickled vegetables', 'Steamed buns with vegetables', 'Soy milk with youtiao', 'Vegetable dumplings', 'Noodle soup'],
                'lunch': ['Mapo tofu (vegetarian)', 'Buddha delight', 'Vegetable fried rice', 'Stir-fried vegetables', 'Vegetable lo mein'],
                'dinner': ['Mapo tofu', 'Stir-fried bok choy', 'Vegetable fried rice', 'Braised eggplant', 'Vegetable dumplings'],
                'snack': ['Steamed buns', 'Spring rolls', 'Vegetable dumplings', 'Fruit', 'Mooncakes']
            },
            'non_vegetarian': {
                'breakfast': ['Congee with century egg', 'Steamed buns with pork', 'Soy milk with fried dough', 'Pork dumplings', 'Noodle soup with beef'],
                'lunch': ['Kung pao chicken', 'Sweet and sour pork', 'Beef with broccoli', 'Orange chicken', 'Mapo tofu with pork'],
                'dinner': ['Peking duck', 'Kung pao chicken', 'Sweet and sour fish', 'Beef with oyster sauce', 'Steamed fish with ginger'],
                'snack': ['Pork buns', 'Shrimp dumplings', 'Scallion pancakes', 'Chicken feet', 'Egg tarts']
            }
        },
    }

    # Get cuisine for country, fallback to international (US-style) if not found
    cuisine = cuisine_db.get(country_name, cuisine_db.get('United States', {}))
    
    # Get diet-specific foods
    diet_type = user_profile.diet_type or 'non_vegetarian'
    foods = cuisine.get(diet_type, cuisine.get('non_vegetarian', {}))

    # If country not found, use a generic international fallback
    if not foods:
        foods = {
            'breakfast': ['Oatmeal with fruit', 'Scrambled eggs with toast', 'Yogurt with granola'],
            'lunch': ['Grilled chicken salad', 'Vegetable wrap', 'Quinoa bowl'],
            'dinner': ['Grilled salmon with vegetables', 'Chicken with rice', 'Vegetable stir-fry'],
            'snack': ['Nuts', 'Fruit', 'Yogurt', 'Hummus with vegetables']
        }

    # Filter out disliked and allergenic foods
    filtered_foods = {}
    for meal_type, items in foods.items():
        filtered_foods[meal_type] = [
            item for item in items
            if item.lower() not in disliked and item.lower() not in allergies
        ]
        # Ensure we have at least some options
        if not filtered_foods[meal_type]:
            # Fallback generic items
            filtered_foods[meal_type] = [
                'Oatmeal with fruit', 'Scrambled eggs with toast', 'Yogurt with granola'
            ] if meal_type == 'breakfast' else [
                'Grilled chicken salad', 'Vegetable wrap', 'Quinoa bowl'
            ] if meal_type == 'lunch' else [
                'Grilled salmon with vegetables', 'Chicken with rice', 'Vegetable stir-fry'
            ] if meal_type == 'dinner' else [
                'Nuts', 'Fruit', 'Yogurt', 'Hummus with vegetables'
            ]

    return filtered_foods