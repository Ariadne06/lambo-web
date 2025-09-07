from django.shortcuts import render, redirect
from .models import logging
from django.contrib import messages
from authentication.decorators import custom_login_required
from django.http import HttpResponse
from utils.db_message import _clean_db_error
from utils.flash import set_flash, get_flash

def login_view(request):
    
    flash = get_flash(request) 
    
    # If session expired or cookie is gone, flush it
    if not request.session.session_key or 'session_token' not in request.session:
        request.session.flush()

    # Already logged in?
    if request.session.get('session_token') and request.session.get('role_name'):
        role = request.session.get('role_name')
        if role == 'Barangay Secretary':
            return redirect('personnels_module:secretary_dashboard')
        elif role == 'Barangay Captain':
            return redirect('captain_module:captain_dashboard')
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

            if not result:
                messages.error(request, 'Login failed: No response from server.')
                return render(request, 'authentication/login.html')

            status = result.get('status')
            token = result.get('session_token')

            # Require both success and a valid token
            if status == 'success' and token:
                # Store session details
                request.session['account_type'] = result.get('account_type')
                request.session['personnel_id'] = result.get('personnel_id')
                request.session['username'] = result.get('username')
                request.session['role_id'] = result.get('role_id')
                request.session['role_name'] = result.get('role_name')
                request.session['session_token'] = token

                role = request.session['role_name']
                if role == 'Admin':
                    return redirect('admin_module:admin_dashboard')
                elif role == 'Barangay Captain':
                    return redirect('captain_module:captain_dashboard')
                else:
                    messages.error(request, 'Access denied: Unrecognized role.')
                    request.session.flush()
                    return redirect('authentication:login')
            elif status == 'success' and not token:
                # Login success but no token returned
                messages.error(request, 'Login failed: Missing session token.')
                return render(request, 'authentication/login.html')
            elif status == 'require_password_change':
                request.session['pending_pwd_change'] = True
                request.session['pending_personnel_id'] = result.get('personnel_id')
                request.session['pending_username'] = result.get('username')
                request.session['account_type'] = 'personnel'
                messages.info(request, 'Please set a new password to continue.')
                return redirect('authentication:reset_password')
            elif status == 'error':
                msg = result.get('message', 'Login failed.')
                messages.error(request, msg)
                return render(request, 'authentication/login.html')

            messages.error(request, 'Login failed.')
        except Exception as e:
            messages.error(request, f'Login failed: {str(e)}')

    return render(request, 'authentication/login.html', {
        'message': flash['message'],
        'message_level': flash['message_level'],
    })


@custom_login_required
def logout_view(request):
    # Before adding a new message, clear old ones
    storage = messages.get_messages(request)
    storage.used = True
    
    # Check if user_id exists in the session
    if 'session_token' in request.session:
        token = request.session.get('session_token')
        result = logging.sp_logout_user(token) 
    
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

def silent_logout(request):
    
    token = request.POST.get('session_token') or request.session.get('session_token')
    if token:
        try:
            logging.sp_logout_user(token)
            request.session.flush()
        except Exception:
            pass
    return HttpResponse(status=204)

def req_pwd_change(request):
    
    flash = get_flash(request) 
    
    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        email = (request.POST.get('email') or '').strip()

        if not username:
            # you can also use set_flash here if you prefer uniform flash
            messages.error(request, 'Username is required.')
            return redirect('authentication:req_pwd_change')

        try:
            logging.sp_request_password_reset(username, email)
            # success → set flash, then REDIRECT (this is the “R” in PRG)
            set_flash(request, "Submitted successfully!", "success")
        except Exception as e:
            # normalize DB error and flash it
            set_flash(request, _clean_db_error(e), "error")

        return redirect('authentication:req_pwd_change')  # ← important
            
    return render(request, 'authentication/requestForgotPassword.html', {
        'message': flash['message'],
        'message_level': flash['message_level'],
    })

def reset_password(request):
    if request.method == 'POST':
        pid = request.session.get('pending_personnel_id')
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if pid:
            
            try:
                if new_password and new_password == confirm_password:
                    # Call the stored procedure to change the password
                    logging.sp_change_personnel_default_pwd(pid, old_password, confirm_password)
                    messages.success(request, 'Password changed successfully.')
                    request.session.flush()
                    return redirect('authentication:login')
                else:
                    messages.error(request, 'Passwords do not match.')
            except Exception as e:
                messages.error(request, _clean_db_error(e))
                return render(request, 'authentication/forgotPassword.html')
        else:
            messages.error(request, 'Session expired. Please log in again.')
            return redirect('authentication:login')
            
    return render(request, 'authentication/forgotPassword.html')
