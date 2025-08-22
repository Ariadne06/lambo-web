from django.urls import path
from . import views

app_name = 'captain_module'

urlpatterns = [
     path('', views.captain_dashboard, name='captain_dashboard'),
     path('captain_viewResident', views.captain_viewResident),
     path('captain_viewMoreResident/', views.captain_viewMoreResident),
     path('captain_householdList/', views.captain_householdList),
     path('captain_moreHousehold/', views.captain_moreHousehold),
     path('captain_businessList/', views.captain_businessList),
     path('captain_moreBusinessInfo/', views.captain_moreBusinessInfo),
     path('personnelRequest/', views.personnelRequest),

    
]
