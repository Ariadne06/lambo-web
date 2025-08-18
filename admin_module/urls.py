# admin_module/urls.py
from django.urls import path
from . import views

app_name = 'admin_module'

urlpatterns = [
     path('', views.admin_dashboard, name='admin_dashboard'),
     path('admin_Addpersonnel/', views.admin_Addpersonnel),
     path('add_personnel1/', views.add_personnel1),
     path('add_personnel2/', views.add_personnel2),
     path('personnel_list/', views.personnel_list),
     path('update_personnel/', views.update_personnel),
     path('password_request/', views.password_request),
     path('activityLogs/', views.activityLogs, name='activityLogs'),
]
