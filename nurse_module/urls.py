from django.urls import path
from . import views

app_name = 'nurse_module'

urlpatterns = [
     path('', views.nurse_dashboard, name='nurse_dashboard'),
     path("residents/", views.nurse_resident_list, name="nurse_residentList"),
     path('households/', views.nurse_household, name='nurse_household'),
     path('nurseHouseholdView/', views.nurse_householdView, name='nurse_householdView'),
     path("child/", views.childrecordList, name="childrecordList"),
     path("child/<int:child_health_id>/", views.moreChildRecord, name="moreChildRecord"),
     path("child/<int:child_health_id>/growth/", views.child_growth_monitoring_api, name="childGrowthMonitoring"),
     path("child/<int:child_health_id>/immunization/", views.child_immunization_api, name="childImmunization"),
     path("child/<int:child_health_id>/medsurg/", views.childMedSurg, name="childMedSurg"),
     path("child/<int:child_health_id>/supplements/", views.childSupplements, name="childSupplements"),
     path("child/<int:child_health_id>/immunization/add/", views.child_immunization_add_api,name="childImmunizationAdd"),
     path('maternalrecord', views.maternalrecord, name='maternalrecord'),
     path("maternalrecord/<int:maternal_health_id>/", views.Morematernalrecord, name="Morematernalrecord"),
     path("maternalrecord/<int:maternal_health_id>/add-disease/", views.add_maternal_disease_screening, name="add_maternal_disease_screening"),
     path('maternalLabScreening/', views.maternalLabScreening),
     path('maternalIron/', views.maternalIron),
     path('general-health/', views.nurseGeneralInfo, name='nurse_general_health'),
     path('ImmunizationStatus/', views.ImmunizationStatus),
     path("api/general-health/", views.general_health_get_api, name="generalHealthGetApi"),
     path('api/resident-links', views.resident_links_list_api, name='nurse_residentLinksListApi'),
]
