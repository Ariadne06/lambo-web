from django.urls import path
from . import views

app_name = 'captain_module'

urlpatterns = [
     path('', views.captain_dashboard, name='captain_dashboard'),
     path('captain_viewResident/', views.captain_viewResident, name='captain_viewResident'),
     path('resident/<int:resident_id>/detail/', views.resident_detail_json, name='captain-resident-detail'),
     path('captain_householdList/', views.captain_householdList, name='captain_householdList'),
     path('captain_householdView/', views.captain_householdView, name='captain_householdView'),
     path('captain_businessList/', views.captain_businessList, name='captain_businessList'),
     path('captain_moreBusinessInfo/', views.captain_moreBusinessInfo),
     path('personnelRequest/', views.personnelRequest, name='personnelRequest'),
     path("api/general-health/", views.general_health_get_api, name="generalHealthGetApi"),
     path('api/resident-links', views.resident_links_list_api, name='captain_residentLinksListApi'),
     
    # PDF Generation endpoints
    path('household_list/pdf/', views.generate_household_list_pdf, name='generate_household_list_pdf'),
    path('household/<int:household_id>/pdf/', views.generate_household_detail_pdf, name='generate_household_detail_pdf'),
    path('resident_list/pdf/', views.generate_resident_list_pdf, name='generate_resident_list_pdf'),
    path('resident/<int:resident_id>/pdf/', views.generate_resident_detail_pdf, name='generate_resident_detail_pdf'),
]