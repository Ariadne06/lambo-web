from django.urls import path
from . import views

app_name = 'nurse_module'

urlpatterns = [
     path('', views.nurse_dashboard, name='nurse_dashboard'),
     path('nurse_residentList', views.nurse_residentList),
     path('nurse_moreResident', views.nurse_moreResident),
     path('nurse_household', views.nurse_household),
     path('householdMore', views.householdMore),
     path('householdInfo1', views.householdInfo1),
     path('householdInfo2', views.householdInfo2),
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
     path('nurseGeneralInfo', views.nurseGeneralInfo),
     path('moreGenInfo', views.moreGenInfo),
     path('ImmunizationStatus', views.ImmunizationStatus),

    
]
