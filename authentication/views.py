from django.shortcuts import render, redirect
from .models import logging
from django.contrib import messages
from authentication.decorators import custom_login_required
from django.http import HttpResponse
from utils.db_message import _clean_db_error
from utils.flash import set_flash, get_flash
import os, json
from urllib.parse import urlencode
from django.http import JsonResponse, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.html import escape
from .tokens import make_reset_token, load_reset_token
from django.conf import settings


def login_view(request):
    
    flash = get_flash(request) 
    
    # If session expired or cookie is gone, flush it
    if not request.session.session_key or 'session_token' not in request.session:
        request.session.flush()

    # Already logged in?
    if request.session.get('session_token') and request.session.get('role_name'):
        role = request.session.get('role_name')
        if role == 'Admin':
            return redirect('admin_module:admin_dashboard')
        elif role == 'Barangay Captain':
            return redirect('captain_module:captain_dashboard')
        elif role == 'Barangay Secretary':
            return redirect('secretary_module:secretary_dashboard')
        elif role == 'Barangay Assistant Secretary':
            return redirect('secretary_module:secretary_dashboard')
        elif role == 'Barangay Treasurer':
            return redirect('treasurer_module:treasurer_dashboard')
        elif role == 'Barangay Health Worker':
            return redirect('bhw_module:bhw_dashboard')
        elif role == 'Midwife':
            return redirect('nurse_module:nurse_dashboard')
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
                elif role == 'Barangay Secretary':
                    return redirect('secretary_module:secretary_dashboard')
                elif role == 'Barangay Assistant Secretary':
                    return redirect('secretary_module:secretary_dashboard')
                elif role == 'Barangay Treasurer':
                    return redirect('treasurer_module:treasurer_dashboard')
                elif role == 'Barangay Health Worker':
                    return redirect('bhw_module:bhw_dashboard')
                elif role == 'Midwife':
                    return redirect('nurse_module:nurse_dashboard')
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
            result = logging.sp_request_password_reset(username, email)
            
            if result == "Reset request accepted. Personnel account matched.":
                set_flash(request, result, "success")
            else:
                set_flash(request, result, "error")
        except Exception as e:
            set_flash(request, _clean_db_error(e), "error")

        return redirect('authentication:req_pwd_change')  # ← important
            
    return render(request, 'authentication/requestForgotPassword.html', {
        'message': flash['message'],
        'message_level': flash['message_level'],
    })

def reset_password(request):
    if request.method == 'POST':
        pid = request.session.get('pending_personnel_id')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if pid:
            
            try:
                if new_password and new_password == confirm_password:
                    # Call the stored procedure to change the password
                    logging.sp_change_personnel_default_pwd(pid, new_password)
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

def forgot_password(request):
    flash = get_flash(request)
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        email    = (request.POST.get("email") or "").strip()
        p1       = (request.POST.get("new_password") or "").strip()
        p2       = (request.POST.get("confirm_password") or "").strip()

        if not username or not email:
            set_flash(request, "Invalid request: missing user info.", "error")
            return redirect("authentication:login")

        if len(p1) < 8:
            set_flash(request, "Password must be at least 8 characters.", "error")
            return render(request, "authentication/mobileForgotPassword.html", {
                "prefilled_username": username, "prefilled_email": email,
            })

        if p1 != p2:
            set_flash(request, "Passwords do not match.", "error")
            return render(request, "authentication/mobileForgotPassword.html", {
                "prefilled_username": username, "prefilled_email": email,
            })

        try:
            # print(f"[DEBUG] Attempting to reset password for user: {username} {p1}")
            results = logging.sp_reset_resident_password_by_username(username, p1) 
            # if results:
            #     print(f"[DEBUG] Password reset results: {results}")
            # print(f"[DEBUG] Password reset results: {results}")
            set_flash(request, results, "success")
            return redirect("authentication:login")
        except Exception as e:
            set_flash(request, _clean_db_error(e), "error")
            return render(request, "authentication/mobilForgotPassword.html", {
                "prefilled_username": username, 
                "prefilled_email": email,
                'message': flash['message'],
                'message_level': flash['message_level'],
            })

    return render(request, "authentication/mobileForgotPassword.html", {
        'message': flash['message'],
        'message_level': flash['message_level'],
    })

@csrf_exempt
def api_forgot_password(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    # 1) Parse JSON body
    try:
        body = json.loads(request.body.decode("utf-8"))
        username = (body.get("username") or "").strip()
        email    = (body.get("email") or "").strip()
        if not username or not email:
            return JsonResponse({"error": "username and email are required"}, status=400)
    except Exception:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    # 2) Verify this pair exists in your DB (use your stored proc)
    try:
        res = logging.sp_check_resident_username_email(username, email)
        if res is not True:
            return JsonResponse({"error": "User not found for that username+email"}, status=404)
    except Exception as e:
        return JsonResponse({"error": _clean_db_error(e)}, status=500)

    # 3) Create signed, expiring token with ONLY the info you need
    token = make_reset_token({"u": username, "e": email})

    # 4) Build the link to your reset page
    #    http://10.162.93.189:8000/authentication/reset/<token>/
    reset_path = reverse("authentication:reset_from_link", args=[token])
    reset_link = f"{settings.SITE_ORIGIN.rstrip('/')}{reset_path}"  # change to your public domain in prod
    # host = "http://10.162.93.189:8000" 
    # reset_link = f"{host}{reset_path}"

    # 5) Send the email (Django email backend will use your SMTP or SendGrid)
    subject = "Reset Your LAMBO Password"
    text_body = (
        f"Hi {username},\n\n"
        "We received a request to reset your password.\n\n"
        f"Username: {username}\n"
        f"Reset link: {reset_link}\n\n"
        "This link expires in 30 minutes.\n"
        "If you did not request this, please ignore this email."
    )
    html_body = f"""
      <h2>Reset Your Password</h2>
      <p>Hi <strong>{escape(username)}</strong>,</p>
      <p>Your username: <strong>{escape(username)}</strong></p>
      <p><a href="{escape(reset_link)}"
            style="background:#d32f2f;color:#fff;padding:10px 14px;border-radius:8px;text-decoration:none;">
        Reset Password
      </a></p>
      <p style="color:#666;font-size:12px">
        This link expires in 30 minutes. If you didn’t request this, ignore this email.
      </p>
    """
    try:
        send_mail(
            subject=subject,
            message=text_body,
            from_email=None,
            recipient_list=[email],
            html_message=html_body,
            fail_silently=False,
        )
    except Exception as e:
        return JsonResponse({"error": f"Failed to send email: {e}"}, status=500)

    return JsonResponse({"message": "Password reset email sent."}, status=200)


def reset_from_link(request, token: str):
    data = load_reset_token(token, max_age_seconds=30 * 60)  # 30 minutes
    if not data:
        set_flash(request,"Reset link is invalid or has expired.", "error")
        return redirect("authentication:login")

    # Pre-fill/lock username+email into the form (hidden inputs)
    return render(request, "authentication/mobileForgotPassword.html", {
        "prefilled_username": data.get("u"),
        "prefilled_email": data.get("e"),
    })
