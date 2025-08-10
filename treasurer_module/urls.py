from django.urls import path
from . import views

app_name = 'treasurer_module'

urlpatterns = [
     path('', views.treasurer_dashboard, name='treasurer_dashboard'),
     path('payments', views.payments),
     path('summary', views.summary),
     path('transactions', views.transactions),
    

    
]
