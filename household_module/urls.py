from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
import django.contrib.admin as admin

app_name = 'household_module'

urlpatterns = [
    # Include router URLs
    path('admin/', admin.site.urls),
]