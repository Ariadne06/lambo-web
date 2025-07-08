from django.urls import path
from . import views

urlpatterns = [
     path('', views.captain_dashboard),
     path('admin_Addpersonnel/', views.admin_Addpersonnel),
    
]
