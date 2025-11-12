from django.urls import path
from . import views

app_name = 'nurse_module'

urlpatterns = [
     path('', views.nurse_dashboard, name='nurse_dashboard'),
     path("residents/", views.nurse_resident_list, name="nurse_residentList"),
     path('households/', views.nurse_household, name='nurse_household'),
     path('nurseHouseholdView/', views.nurse_householdView, name='nurse_householdView'),
     path('childrecordList/', views.childrecordList, name='childrecordList'),
     path('moreChildRecord/', views.moreChildRecord, name='moreChildRecord'),
     path('maternalrecord/', views.maternalrecord, name='maternalrecord'),
     path('Morematernalrecord/', views.Morematernalrecord, name='Morematernalrecord'),
     path('maternalLabScreening/', views.maternalLabScreening),
     path('maternalIron/', views.maternalIron),
     path('general-health/', views.nurseGeneralInfo, name='nurse_general_health'),
     path('ImmunizationStatus/', views.ImmunizationStatus),
     path("api/general-health/", views.general_health_get_api, name="generalHealthGetApi"),
]
