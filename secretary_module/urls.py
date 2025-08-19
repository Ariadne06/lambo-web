from django.urls import path
from . import views

app_name = 'secretray_module'

urlpatterns = [
     path('', views.secretary_dashboard, name='secretary_dashboard'),
     path('resident_list', views.resident_list),
     path('household_list', views.household_list),
     path('moreHousehold', views.moreHousehold),
     path('householdMember', views.householdMember),
     path('Addbusiness', views.Addbusiness),
     path('businessDetail1', views.businessDetail1),
     path('businessDetail2', views.businessDetail2),
     path('businessDetail3', views.businessDetail3),
     path('manageBusiness', views.manageBusiness),
     path('businessView', views.businessView),
     path('businessUpdate', views.businessUpdate),
     path('businessPayment', views.businessPayment),
     path('addCertificate', views.addCertificate),
     path('manageCert1', views.manageCert1),
     path('manageCert2', views.manageCert2),
     path('applications', views.applications),
     path('applicationInfo', views.applicationInfo),
     path('priceUpdate', views.priceUpdate),
     path('announcement', views.announcement),
     path('addAnnouncement', views.addAnnouncement),
     path('residentInfo1', views.residentInfo1),
     path('residentInfo2', views.residentInfo2),
  

    
]
