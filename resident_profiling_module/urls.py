from django.urls import path

from . import views

urlpatterns = [
    path('resident_profiling/', views.resident_profiling, name='resident_profiling'),
]
