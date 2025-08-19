from django.urls import path
from . import views

app_name = 'bhw_module'

urlpatterns = [
     path('', views.bhw_dashboard, name='bhw_dashboard'),
     path('householdList', views.householdList),
     path('addHousehold1', views.addHousehold1),
     path('addHousehold2', views.addHousehold2),
     path('addHousehold3', views.addHousehold3),
     path('addHousehold4', views.addHousehold4),
     path('addHousehold5', views.addHousehold5),
     path('householdView', views.householdView),
     path('householdVisit', views.householdVisit),
     path('memberProfile1', views.memberProfile1),
     path('memberProfile2', views.memberProfile2),
     path('residentList', views.residentList),
     path('residentUpdate', views.residentUpdate),
     path('residentUpdate1', views.residentUpdate1),
     path('residentAdd1', views.residentAdd1),
     path('residentAdd2', views.residentAdd2),
     path('residentAdd3', views.residentAdd3),
     path('residentAdd4', views.residentAdd4),
        
    
]
