from django.urls import path

from . import views

urlpatterns = [
    path('personnels/', views.personnels, name='personnels'),
]