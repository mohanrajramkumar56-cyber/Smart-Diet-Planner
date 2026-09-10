from django.urls import path
from . import views

urlpatterns = [
    # Main page
    path('', views.home, name='home'),
    
    # API endpoints
    path('api/create-profile/', views.create_user_profile, name='create_profile'),
    path('api/generate-plan/', views.generate_diet_plan, name='generate_plan'),
    path('api/history/<int:profile_id>/', views.get_diet_history, name='diet_history'),
    path('api/rate-plan/', views.rate_diet_plan, name='rate_plan'),
    path('api/download-pdf/<int:diet_plan_id>/', views.download_diet_plan_pdf, name='download_pdf'),
    path('api/countries/', views.get_countries, name='get_countries'),
]