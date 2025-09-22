from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('silent_logout/', views.silent_logout, name='silent_logout'),
    path('req_pwd_change/', views.req_pwd_change, name='req_pwd_change'),
    path('reset_password/', views.reset_password, name='reset_password'),
    path('forgot_password/', views.forgotpassword, name='forgot_password'),
    path('api/forgot_password/', views.api_forgot_password, name='api_forgot_password'),
    path('reset/<str:token>/', views.reset_from_link, name='reset_from_link'),
]