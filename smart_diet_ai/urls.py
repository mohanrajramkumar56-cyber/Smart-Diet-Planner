from django.contrib import admin
from django.urls import path, include
from diet_app import views as diet_views

urlpatterns = [
    path('', diet_views.home, name='index'),
    path('admin/', admin.site.urls),
    path('', include('diet_app.urls')),
]