from django.urls import path
from . import views

app_name = 'bhw_module'

urlpatterns = [
     path('', views.bhw_dashboard, name='bhw_dashboard'),
     path('householdList/', views.householdList, name='householdList'),
     path('householdView/', views.householdView, name='householdView'),
     path('householdVisit/', views.householdVisit, name='householdVisit'),
     path('household/update/', views.update_household, name='householdUpdate'),
     path("household/visit/mark/", views.mark_household_visit, name="householdVisitMark"),
     path('residentList/', views.residentList),
     path('residentAdd1/', views.residentAdd1),
     path('residentAdd2/', views.residentAdd2),
     path('residentAdd3/', views.residentAdd3),
     path('residentAdd4/', views.residentAdd4),
     path('childList/', views.childList, name='childList'),
     path('addchild1/', views.addchild1),
     path('addchild2/', views.addchild2),
     path('addchild3/', views.addchild3),
     path('childView/', views.childView),
     path('genInfo/', views.genInfo, name='genInfo'),
     path('maternalList/', views.maternalList, name='maternalList'),
     path('maternalAdd/', views.maternalAdd),
     path('maternalView/', views.maternalView),
     path('HouseholdAdd/', views.HouseholdAdd, name='HouseholdAdd'),
     path('residents/search/', views.resident_search_api, name='resident_search_api'),
]

