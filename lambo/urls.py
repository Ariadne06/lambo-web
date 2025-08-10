"""
URL configuration for lambo project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

app_name = 'lambo'

def redirect_to_login(request):
    return redirect('authentication:login')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', redirect_to_login, name='login_redirect'),
    
    # Authentication URLs
    path('authentication/', include('authentication.urls')),
    
    # Personnels Module URLs
    path('personnels_module/', include('personnels_module.urls')),

    # Browser Reload URLs
    path('__reload__', include('django_browser_reload.urls')),

    # Resident API URLs
    path('api/', include('resident_api.urls')),

    path('admin_module/', include('admin_module.urls')),

    path('captain_module/', include('captain_module.urls')),

    path('treasurer_module/', include('treasurer_module.urls')),

    path('nurse_module/', include('nurse_module.urls')),
]

