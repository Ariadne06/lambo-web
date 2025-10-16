from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'household_module'

urlpatterns = [
    # Include router URLs
    path('', include()),
]