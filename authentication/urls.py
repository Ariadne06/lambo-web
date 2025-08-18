from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('silent_logout/', views.silent_logout, name='silent_logout'),
    # path("tab-close-logout/", views.tab_close_logout, name="tab_close_logout"),
]