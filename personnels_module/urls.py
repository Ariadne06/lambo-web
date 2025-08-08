from django.urls import path

from . import views

app_name = 'personnels_module'

urlpatterns = [
    path('', views.personnels, name='secretary_dashboard'),
]