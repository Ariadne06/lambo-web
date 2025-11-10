from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from utils.flash import set_flash, get_flash

def custom_login_required(view_func):
    """
    Decorator for views that checks that the user is logged in using session-based authentication,
    redirecting to the login page if necessary.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Check if user ID is stored in the session
        if 'personnel_id' not in request.session:
            set_flash(request, 'You need to log in to access this page.', 'error')
            login_url = 'authentication:login'  # Replace with your login URL
            return redirect(login_url)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def role_required(*required_role):
    """
    Decorator to check if the user has the required role to access the view.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Check the user's role (assuming the role is stored in the session or user model)
            user_role = request.session.get('role_name')
            
            if user_role not in required_role:
                set_flash(request, 'You do not have permission to access this page.', 'error')
                return redirect('authentication:login') 
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator