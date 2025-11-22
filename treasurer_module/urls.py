from django.urls import path
from . import views

app_name = 'treasurer_module'

urlpatterns = [
     path('', views.treasurer_dashboard, name='treasurer_dashboard'),
     path('payments', views.payments, name='payments'),
     path('summary', views.summary, name='summary'),
     # HTML detail page (new)
     path('applications/<int:application_id>/', views.treasurer_application_detail, name='treasurer_application_detail'),
     path('applications/<int:application_id>/detail/', views.treasurer_application_detail_json, name='treasurer_application_detail_json'),
     path('applications/<int:application_id>/paid/', views.set_application_to_paid, name='set_application_to_paid'),
]
