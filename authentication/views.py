from django.shortcuts import render
from .models import logging
from django.contrib import messages

# Create your views here.

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        try:
            result = logging.sp_login_personnel_web(username, password)
            
            if result:
                request.session['user_id'] = result[0]
                request.session['user_id'] = result[0]
                request.session['user_id'] = result[0]
                request.session['user_id'] = result[0]
        except Exception as e:
            messages.error(request, 'Login failed: Invalid credentials.')
        
    return render(request, 'authentication/login.html')