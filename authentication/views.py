from django.shortcuts import render, redirect
from .models import logging
from django.contrib import messages
from authentication.decorators import custom_login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

def login_view(request):
    # If session expired or cookie is gone, flush it
    if not request.session.session_key or 'session_token' not in request.session:
        request.session.flush()
        
    # Check if user is already logged in
    if request.session.get('session_token') and request.session.get('role_name'):
        role = request.session.get('role_name')
        if role == 'Secretary':
            return redirect('personnels_module:secretary_dashboard')
        elif role == 'Captain':
            return redirect('captain_module:dashboard_captain')
        elif role == 'Admin':
            return redirect('admin_module:admin_dashboard')
        else:
            messages.error(request, 'Access denied: Unrecognized role.')
            return redirect('authentication:login')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            result = logging.sp_login_personnel_web(username, password)

            if result:
                if result.get('status') == 'success':
                    # Store session details
                    request.session['account_type'] = result.get('account_type')
                    request.session['personnel_id'] = result.get('personnel_id')
                    request.session['username'] = result.get('username')
                    request.session['role_id'] = result.get('role_id')
                    request.session['role_name'] = result.get('role_name')
                    request.session['session_token'] = result.get('session_token')

                    messages.success(request, 'Login successful!')

                    # Redirect based on role
                    role = result.get('role_name')
                    if role == 'Secretary':
                        return redirect('personnels_module:secretary_dashboard')
                    elif role == 'Captain':
                        return redirect('captain_module:dashboard_captain')
                    elif role == 'Admin':
                        return redirect('admin_module:admin_dashboard')
                    else:
                        messages.error(request, 'Access denied: Unrecognized role.')
                        return redirect('authentication:login')
                else:
                    messages.error(request, 'Login failed: Invalid credentials.')
            else:
                messages.error(request, 'Login failed: No response from server.')
        except Exception as e:
            messages.error(request, f'Login failed: {str(e)}')

    return render(request, 'authentication/login.html')

@custom_login_required
def logout_view(request):
    # Check if user_id exists in the session
    if 'session_token' in request.session:     
        result = logging.sp_logout_user(request.session['session_token'])
    
        storage = messages.get_messages(request)
        storage.used = True
        
        try:
            if result and result.get('status') == 'success':
                messages.success(request, 'You have been logged out successfully.')
            else:
                messages.error(request, result.get('status'))
        except Exception as e:
            messages.error(request, f'Logout failed: {str(e)}')
        finally:
            # Clear the session
            request.session.flush()
    else:
        messages.warning(request, 'You are not logged in.')

    return redirect('authentication:login')

@csrf_exempt
def silent_logout(request):
    token = request.session.get('session_token')
    if token:
        try:
            logging.sp_logout_user(token)
        except Exception:
            pass
    # Do not flush here; let normal logout or session expiry handle it.
    return HttpResponse(status=204)
