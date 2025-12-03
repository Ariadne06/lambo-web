# admin_module/urls.py
from django.urls import path
from . import views

app_name = 'admin_module'

urlpatterns = [
     path('', views.admin_dashboard, name='admin_dashboard'),
     path('admin_Addpersonnel/', views.admin_Addpersonnel, name='admin_Addpersonnel'),
     path('add_personnel1/', views.add_personnel1, name='add_personnel1'),
     path('add_personnel2/', views.add_personnel2, name='add_personnel2'),
     path('personnel_list/', views.personnel_list, name='personnel_list'),
     path('update_personnel/', views.update_personnel, name='update_personnel'),
     path('password_request/', views.password_request, name='password_request'),
     path('activityLogs/', views.activityLogs, name='activityLogs'),
     path('authenticationlog/', views.authenticationlog, name='authenticationlog'),
     path('documentlog/', views.documentlog, name='documentlog'),
     path('residentlog/', views.residentlog, name='residentlog'),\
     path('residentList/', views.residentList, name='residentList'),
     path('get-resident-profile/<int:resident_id>/', views.get_resident_profile, name='get_resident_profile'),
]
