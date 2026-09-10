from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import json
import os
import pycountry
from .models import UserProfile, DietPlan, Feedback
from .serializers import UserProfileSerializer, DietPlanSerializer
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO
import datetime


def home(request):
    """Render the main application page"""
    return render(request, 'index.html')


@api_view(['POST'])
def create_user_profile(request):
    """Create or update user profile"""
    serializer = UserProfileSerializer(data=request.data)
    if serializer.is_valid():
        profile = serializer.save()
        return Response({
            'success': True,
            'profile_id': profile.id,
            'message': 'Profile created successfully'
        })
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def generate_diet_plan(request):
    """Generate AI-powered diet plan using Gemini"""
    profile_id = request.data.get('profile_id')
    if not profile_id:
        return Response({
            'success': False,
            'error': 'Profile ID is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Get profile first - returns 404 if not found (not caught by try/except)
    profile = get_object_or_404(UserProfile, id=profile_id)

    # Use the centralized AI engine for generation
    from .ai_engine import generate_diet_plan as engine_generate

    try:
        diet_data = engine_generate(profile)

        if not diet_data:
            return Response({
                'success': False,
                'error': 'Failed to generate diet plan'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Save diet plan to database
        diet_plan = DietPlan.objects.create(
            user_profile=profile,
            plan_data=diet_data
        )

        return Response({
            'success': True,
            'diet_plan_id': diet_plan.id,
            'diet_plan': diet_data,
            'message': 'AI Diet plan generated successfully!'
        })

    except Exception as engine_error:
        print(f"AI Engine Error: {engine_error}")
        import traceback
        traceback.print_exc()
        return Response({
            'success': False,
            'error': f"Error generating plan: {str(engine_error)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def create_sample_diet_plan(profile):
    """Create a South Indian–focused sample diet plan as fallback with variety and no repeats"""
    # Adjust calories based on user goal
    base_calories = 2000
    if profile.goal == 'lose':
        base_calories = 1800
    elif profile.goal == 'gain':
        base_calories = 2400
    elif profile.goal == 'muscle':
        base_calories = 2200

    # Protein base by diet type
    is_nonveg = profile.diet_type == 'non_vegetarian'
    is_vegan = profile.diet_type == 'vegan'

    def dairy(item):
        return item if not is_vegan else item.replace('Curd', 'Plant curd').replace('curd', 'plant curd').replace('Buttermilk', 'Spiced coconut buttermilk')

    return {
        "total_calories_per_day": base_calories,
        "days": [
            {
                "day": "Day 1",
                "meals": [
                    {
                        "meal_type": "Breakfast",
                        "time": "7:30 AM",
                        "food_items": ["Idli", "Sambar", "Coconut chutney"],
                        "calories": 360,
                        "protein": "12g",
                        "carbs": "68g",
                        "fat": "8g",
                        "description": "Steamed rice cakes with protein-rich sambar"
                    },
                    {
                        "meal_type": "Lunch",
                        "time": "1:00 PM",
                        "food_items": ["Sambar rice", "Beans poriyal", dairy("Curd")],
                        "calories": 520,
                        "protein": "18g",
                        "carbs": "85g",
                        "fat": "12g",
                        "description": "Balanced plate with dal, veggies and rice"
                    },
                    {
                        "meal_type": "Snack",
                        "time": "4:00 PM",
                        "food_items": ["Chana sundal", "Tender coconut water"],
                        "calories": 180,
                        "protein": "8g",
                        "carbs": "24g",
                        "fat": "5g",
                        "description": "Light protein snack"
                    },
                    {
                        "meal_type": "Dinner",
                        "time": "7:30 PM",
                        "food_items": [
                            "Fish curry" if is_nonveg else "Vegetable kurma",
                            "Steamed rice" if is_nonveg else "Chapati",
                            "Cucumber salad"
                        ],
                        "calories": 420,
                        "protein": "28g" if is_nonveg else "16g",
                        "carbs": "38g",
                        "fat": "16g",
                        "description": "South Indian main with sides"
                    }
                ]
            },
            {
                "day": "Day 2",
                "meals": [
                    {
                        "meal_type": "Breakfast",
                        "time": "7:30 AM",
                        "food_items": ["Masala dosa", "Sambar", "Mint chutney"],
                        "calories": 380,
                        "protein": "10g",
                        "carbs": "62g",
                        "fat": "12g",
                        "description": "Fermented crepe with potato masala"
                    },
                    {
                        "meal_type": "Lunch",
                        "time": "1:00 PM",
                        "food_items": ["Lemon rice", dairy("Curd"), "Mixed vegetable kootu"],
                        "calories": 500,
                        "protein": "16g",
                        "carbs": "82g",
                        "fat": "10g",
                        "description": "Zesty rice with protein sides"
                    },
                    {
                        "meal_type": "Snack",
                        "time": "4:00 PM",
                        "food_items": ["Roasted peanuts", "Buttermilk" if not is_vegan else "Spiced coconut buttermilk"],
                        "calories": 170,
                        "protein": "8g",
                        "carbs": "12g",
                        "fat": "10g",
                        "description": "Healthy fats and hydration"
                    },
                    {
                        "meal_type": "Dinner",
                        "time": "7:30 PM",
                        "food_items": [
                            "Chicken Chettinad" if is_nonveg else "Avial",
                            "Chapati",
                            "Tomato rasam"
                        ],
                        "calories": 440,
                        "protein": "30g" if is_nonveg else "14g",
                        "carbs": "42g",
                        "fat": "14g",
                        "description": "Spiced curry with whole grains"
                    }
                ]
            },
            {
                "day": "Day 3",
                "meals": [
                    {
                        "meal_type": "Breakfast",
                        "time": "7:30 AM",
                        "food_items": ["Rava upma", "Coconut chutney", dairy("Curd")],
                        "calories": 340,
                        "protein": "9g",
                        "carbs": "58g",
                        "fat": "9g",
                        "description": "Semolina upma with sides"
                    },
                    {
                        "meal_type": "Lunch",
                        "time": "1:00 PM",
                        "food_items": ["Vegetable biryani", dairy("Raita"), "Cabbage poriyal"],
                        "calories": 520,
                        "protein": "14g",
                        "carbs": "80g",
                        "fat": "14g",
                        "description": "Aromatic rice with vegetables"
                    },
                    {
                        "meal_type": "Snack",
                        "time": "4:00 PM",
                        "food_items": ["Sprouts salad", "Cut fruits"],
                        "calories": 160,
                        "protein": "9g",
                        "carbs": "20g",
                        "fat": "4g",
                        "description": "Light, fiber-rich snack"
                    },
                    {
                        "meal_type": "Dinner",
                        "time": "7:30 PM",
                        "food_items": [
                            "Egg curry" if is_nonveg else "Mixed veg kurma",
                            "Dosa",
                            "Onion chutney"
                        ],
                        "calories": 430,
                        "protein": "24g" if is_nonveg else "14g",
                        "carbs": "44g",
                        "fat": "16g",
                        "description": "Protein curry with dosa"
                    }
                ]
            },
            {
                "day": "Day 4",
                "meals": [
                    {
                        "meal_type": "Breakfast",
                        "time": "7:30 AM",
                        "food_items": ["Ven pongal", "Coconut chutney", "Sambar"],
                        "calories": 370,
                        "protein": "10g",
                        "carbs": "60g",
                        "fat": "11g",
                        "description": "Comforting rice-lentil dish"
                    },
                    {
                        "meal_type": "Lunch",
                        "time": "1:00 PM",
                        "food_items": ["Rasam rice", "Snake gourd kootu", dairy("Curd")],
                        "calories": 480,
                        "protein": "16g",
                        "carbs": "78g",
                        "fat": "9g",
                        "description": "Light, tangy lunch"
                    },
                    {
                        "meal_type": "Snack",
                        "time": "4:00 PM",
                        "food_items": ["Peanut sundal", "Lemon water"],
                        "calories": 170,
                        "protein": "8g",
                        "carbs": "14g",
                        "fat": "9g",
                        "description": "Protein snack"
                    },
                    {
                        "meal_type": "Dinner",
                        "time": "7:30 PM",
                        "food_items": ["Paneer tikka" if not is_vegan else "Tofu tikka", "Chapati", "Salad"],
                        "calories": 420,
                        "protein": "24g",
                        "carbs": "40g",
                        "fat": "16g",
                        "description": "Grilled protein with whole grains"
                    }
                ]
            },
            {
                "day": "Day 5",
                "meals": [
                    {
                        "meal_type": "Breakfast",
                        "time": "7:30 AM",
                        "food_items": ["Uttapam", "Tomato chutney", dairy("Curd")],
                        "calories": 360,
                        "protein": "11g",
                        "carbs": "62g",
                        "fat": "10g",
                        "description": "Thick dosa with toppings"
                    },
                    {
                        "meal_type": "Lunch",
                        "time": "1:00 PM",
                        "food_items": ["Curd rice" if not is_vegan else "Plant-curd rice", "Aloo fry", "Pickle"],
                        "calories": 500,
                        "protein": "14g",
                        "carbs": "82g",
                        "fat": "12g",
                        "description": "Cooling lunch with sides"
                    },
                    {
                        "meal_type": "Snack",
                        "time": "4:00 PM",
                        "food_items": ["Roasted chana", "Masala chai" if not is_vegan else "Herbal tea"],
                        "calories": 160,
                        "protein": "7g",
                        "carbs": "18g",
                        "fat": "4g",
                        "description": "Light crunchy snack"
                    },
                    {
                        "meal_type": "Dinner",
                        "time": "7:30 PM",
                        "food_items": [
                            "Prawn masala" if is_nonveg else ("Kadai paneer" if not is_vegan else "Kadai tofu"),
                            "Steamed rice",
                            "Cabbage poriyal"
                        ],
                        "calories": 450,
                        "protein": "30g" if is_nonveg else "20g",
                        "carbs": "44g",
                        "fat": "15g",
                        "description": "Seafood/veg main with rice"
                    }
                ]
            },
            {
                "day": "Day 6",
                "meals": [
                    {
                        "meal_type": "Breakfast",
                        "time": "7:30 AM",
                        "food_items": ["Ragi dosa", "Coconut chutney", "Sambar"],
                        "calories": 340,
                        "protein": "11g",
                        "carbs": "58g",
                        "fat": "9g",
                        "description": "Millet-based dosa"
                    },
                    {
                        "meal_type": "Lunch",
                        "time": "1:00 PM",
                        "food_items": ["Coconut rice", "Mixed veg avial", dairy("Curd")],
                        "calories": 510,
                        "protein": "15g",
                        "carbs": "80g",
                        "fat": "14g",
                        "description": "Coconut-flavored rice with veg"
                    },
                    {
                        "meal_type": "Snack",
                        "time": "4:00 PM",
                        "food_items": ["Fruits bowl", "Buttermilk" if not is_vegan else "Spiced coconut buttermilk"],
                        "calories": 150,
                        "protein": "5g",
                        "carbs": "26g",
                        "fat": "4g",
                        "description": "Hydrating snack"
                    },
                    {
                        "meal_type": "Dinner",
                        "time": "7:30 PM",
                        "food_items": [
                            "Pepper chicken" if is_nonveg else "Channa masala",
                            "Chapati",
                            "Onion salad"
                        ],
                        "calories": 440,
                        "protein": "30g" if is_nonveg else "18g",
                        "carbs": "46g",
                        "fat": "14g",
                        "description": "Spiced main with whole grains"
                    }
                ]
            },
            {
                "day": "Day 7",
                "meals": [
                    {
                        "meal_type": "Breakfast",
                        "time": "7:30 AM",
                        "food_items": ["Appam", "Vegetable stew" if not is_vegan else "Coconut milk veg stew"],
                        "calories": 360,
                        "protein": "9g",
                        "carbs": "60g",
                        "fat": "10g",
                        "description": "Fermented hoppers with stew"
                    },
                    {
                        "meal_type": "Lunch",
                        "time": "1:00 PM",
                        "food_items": ["Tomato rice", "Cucumber raita" if not is_vegan else "Cucumber salad", "Carrot poriyal"],
                        "calories": 500,
                        "protein": "14g",
                        "carbs": "82g",
                        "fat": "12g",
                        "description": "Flavored rice with sides"
                    },
                    {
                        "meal_type": "Snack",
                        "time": "4:00 PM",
                        "food_items": ["Groundnut chikki", "Herbal tea"],
                        "calories": 180,
                        "protein": "6g",
                        "carbs": "22g",
                        "fat": "8g",
                        "description": "Nut-based energy snack"
                    },
                    {
                        "meal_type": "Dinner",
                        "time": "7:30 PM",
                        "food_items": [
                            "Chicken curry" if is_nonveg else "Vegetable sambar",
                            "Steamed rice",
                            "Beetroot poriyal"
                        ],
                        "calories": 430,
                        "protein": "28g" if is_nonveg else "16g",
                        "carbs": "45g",
                        "fat": "12g",
                        "description": "Classic South Indian dinner"
                    }
                ]
            }
        ],
        "nutritional_summary": {
            "daily_protein": "85g",
            "daily_carbs": "150g",
            "daily_fat": "65g",
            "daily_fiber": "30g"
        },
        "tips": [
            f"Drink at least 8 glasses of water daily",
            f"Include 30 minutes of physical activity suitable for {profile.activity_level} lifestyle",
            f"Eat meals at regular intervals to support your {profile.goal} goal",
            f"This plan respects {profile.diet_type} preferences and emphasizes South Indian cuisine"
        ]
    }


@api_view(['GET'])
def get_diet_history(request, profile_id):
    """Get diet plan history for a user"""
    # Get profile first - returns 404 if not found
    profile = get_object_or_404(UserProfile, id=profile_id)
    diet_plans = DietPlan.objects.filter(user_profile=profile)
    serializer = DietPlanSerializer(diet_plans, many=True)

    return Response({
        'success': True,
        'history': serializer.data
    })


@api_view(['POST'])
def rate_diet_plan(request):
    """Rate a diet plan"""
    diet_plan_id = request.data.get('diet_plan_id')
    rating = request.data.get('rating')
    feedback_text = request.data.get('feedback', '')

    if not diet_plan_id:
        return Response({
            'success': False,
            'error': 'Diet plan ID is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    if rating is None:
        return Response({
            'success': False,
            'error': 'Rating is required'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Get diet plan first - returns 404 if not found
    diet_plan = get_object_or_404(DietPlan, id=diet_plan_id)

    try:
        diet_plan.rating = rating
        diet_plan.feedback_text = feedback_text
        diet_plan.save()

        return Response({
            'success': True,
            'message': 'Rating saved successfully!'
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def download_diet_plan_pdf(request, diet_plan_id):
    """Download diet plan as PDF"""
    # Get diet plan first - returns 404 if not found
    diet_plan = get_object_or_404(DietPlan, id=diet_plan_id)

    try:
        # Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.darkblue,
            alignment=1  # Center alignment
        )
        story.append(Paragraph("Nourish", title_style))
        story.append(Spacer(1, 20))

        # User info
        user_info = f"""
        <b>Name:</b> {diet_plan.user_profile.name}<br/>
        <b>Age:</b> {diet_plan.user_profile.age} years<br/>
        <b>BMI:</b> {diet_plan.user_profile.bmi}<br/>
        <b>Goal:</b> {diet_plan.user_profile.get_goal_display()}<br/>
        <b>Diet Type:</b> {diet_plan.user_profile.get_diet_type_display()}<br/>
        <b>Generated on:</b> {diet_plan.created_at.strftime('%B %d, %Y')}
        """
        story.append(Paragraph(user_info, styles['Normal']))
        story.append(Spacer(1, 20))

        # Diet plan table
        plan_data = diet_plan.plan_data
        if 'days' in plan_data:
            for day_data in plan_data['days']:
                # Day header
                day_title = Paragraph(f"<b>{day_data['day']}</b>", styles['Heading2'])
                story.append(day_title)

                # Meals table
                table_data = [['Meal', 'Time', 'Food Items', 'Calories', 'Protein']]

                for meal in day_data['meals']:
                    food_items = ', '.join(meal['food_items'])
                    table_data.append([
                        meal['meal_type'],
                        meal['time'],
                        food_items,
                        str(meal['calories']),
                        meal['protein']
                    ])

                table = Table(table_data, colWidths=[1*inch, 1*inch, 2.5*inch, 1*inch, 1*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))

                story.append(table)
                story.append(Spacer(1, 20))

        # Build PDF
        doc.build(story)
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="nourish_plan_{diet_plan.user_profile.name}_{diet_plan.created_at.strftime("%Y%m%d")}.pdf"'

        return response

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['GET'])
def get_countries(request):
    """Get list of all countries for dropdown"""
    try:
        countries = []
        for country in pycountry.countries:
            countries.append({
                'code': country.alpha_2,
                'name': country.name
            })
        # Sort by name
        countries.sort(key=lambda x: x['name'])
        return Response({
            'success': True,
            'countries': countries
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)