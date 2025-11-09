from django.urls import path
from . import views

app_name = 'nurse_module'

urlpatterns = [
     path('', views.nurse_dashboard, name='nurse_dashboard'),
     path("residents/", views.nurse_resident_list, name="nurse_residentList"),
     path('households/', views.nurse_household, name='nurse_household'),
     path('households/<int:household_id>/', views.nurse_household_more, name='nurse_household_more'),
     path('childrecordList', views.childrecordList),
     path('moreChildRecord', views.moreChildRecord),
     path('childImmunization', views.childImmunization),
     path('childSupplements', views.childSupplements),
     path('childGrowth', views.childGrowth),
     path('maternalrecord', views.maternalrecord),
     path('Morematernalrecord', views.Morematernalrecord),
     path('maternalObstetrical', views.maternalObstetrical),
     path('maternalCheckUp', views.maternalCheckUp),
     path('maternalImmunization', views.maternalImmunization),
     path('maternalScreening', views.maternalScreening),
     path('maternalLabScreening', views.maternalLabScreening),
     path('maternalSupplement', views.maternalSupplement),
     path('maternalIron', views.maternalIron),
     path('maternalOutcome', views.maternalOutcome),
     path('maternalPostpartum', views.maternalPostpartum),
     path('maternalSurgical', views.maternalSurgical),
     path('general-health/', views.nurseGeneralInfo, name='nurse_general_health'),
     path('ImmunizationStatus', views.ImmunizationStatus),

    
]
