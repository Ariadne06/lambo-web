from django.urls import path
from . import views

app_name = 'nurse_module'

urlpatterns = [
     path('', views.nurse_dashboard, name='nurse_dashboard'),
     path("residents/", views.nurse_resident_list, name="nurse_residentList"),
     path('households/', views.nurse_household, name='nurse_household'),
     path('households/<int:household_id>/', views.nurse_household_more, name='nurse_household_more'),
     path("child/", views.childrecordList, name="childrecordList"),
     path("child/<int:child_health_id>/", views.moreChildRecord, name="moreChildRecord"),
     path("child/<int:child_health_id>/growth/", views.child_growth_monitoring_api, name="childGrowthMonitoring"),
     path("child/<int:child_health_id>/immunization/", views.child_immunization_api, name="childImmunization"),
     path("child/<int:child_health_id>/medsurg/", views.childMedSurg, name="childMedSurg"),
     path("child/<int:child_health_id>/supplements/", views.childSupplements, name="childSupplements"),
     path('maternalrecord', views.maternalrecord, name='maternalrecord'),
     path("maternalrecord/<int:maternal_health_id>/", views.Morematernalrecord, name="Morematernalrecord"),
     path('maternalLabScreening', views.maternalLabScreening),
     path('maternalIron', views.maternalIron),
     path('general-health/', views.nurseGeneralInfo, name='nurse_general_health'),
     path('ImmunizationStatus', views.ImmunizationStatus),

    
]
