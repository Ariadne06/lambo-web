from django.urls import path
from . import views

app_name = 'captain_module'

urlpatterns = [
     path('', views.captain_dashboard, name='captain_dashboard'),
     path('captain_viewResident/', views.captain_viewResident, name='captain_viewResident'),
     path('captain_viewMoreResident/', views.captain_viewMoreResident),
     path('captain_householdList/', views.captain_householdList, name='captain_householdList'),
     path('captain_householdView/', views.captain_householdView, name='captain_householdView'),
     path('captain_businessList/', views.captain_businessList, name='captain_businessList'),
     path('captain_moreBusinessInfo/', views.captain_moreBusinessInfo),
     path('personnelRequest/', views.personnelRequest, name='personnelRequest'),
     path("api/general-health/", views.general_health_get_api, name="generalHealthGetApi"),
     path('api/resident-links', views.resident_links_list_api, name='captain_residentLinksListApi'),
]
