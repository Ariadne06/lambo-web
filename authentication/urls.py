from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('silent_logout/', views.silent_logout, name='silent_logout'),
    path('req_pwd_change/', views.req_pwd_change, name='req_pwd_change'),
    path('reset_password/', views.reset_password, name='reset_password'),
    path('forgot_password/', views.forgot_password, name='forgot_password'),
    path('api/forgot_password/', views.api_forgot_password, name='api_forgot_password'),
    path('reset/<str:token>/', views.reset_from_link, name='reset_from_link'),
    path("api/resolve_account_type/", views.resolve_account_type, name="resolve_account_type"),
    path("api/resolve_account_type/ping/", views.resolve_ping, name="resolve_ping"),
]