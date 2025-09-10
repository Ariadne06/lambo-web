from django.urls import path
from . import views

app_name = 'secretary_module'

urlpatterns = [
     path('', views.secretary_dashboard, name='secretary_dashboard'),
     path('resident_list/', views.resident_list, name="resident_list"),
     path('household_list/', views.household_list, name="household_list"),
     path('moreHousehold/', views.moreHousehold),
     path('Addbusiness/', views.Addbusiness),
     path('businessDetail1/', views.businessDetail1),
     path('businessDetail2/', views.businessDetail2),
     path('businessDetail3/', views.businessDetail3),
     path('business_list/', views.business_list, name="business_list"),
     path('add_certificate/', views.add_certificate, name="add_certificate"),
     path('manageCert1/', views.manageCert1),
     path('manageCert2/', views.manageCert2),
     path('applications/', views.applications, name="applications"),
     path('price_update/', views.price_update, name="price_update"),
     path('announcement/', views.announcement, name="announcement"),
     path('approval/', views.approval, name="approval"),    
]
