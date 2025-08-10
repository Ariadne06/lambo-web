from django.shortcuts import render
from authentication.decorators import custom_login_required, role_required

# Create your views here.
@custom_login_required
@role_required('Admin')
def admin_dashboard(request):
    return render(request, 'admin_module/admin_dashboard.html')

@custom_login_required
@role_required('Admin')
def admin_Addpersonnel(request):
    return render(request, 'admin_module/admin_Addpersonnel.html')

@custom_login_required
@role_required('Admin')
def add_personnel1(request):
 return render(request, 'admin_module/add_personnel1.html')

@custom_login_required
@role_required('Admin')
def add_personnel2(request):
 return render(request, 'admin_module/add_personnel2.html')

@custom_login_required
@role_required('Admin')
def personnel_list(request):
 return render(request, 'admin_module/personnel_list.html')

@custom_login_required
@role_required('Admin')
def update_personnel(request):
 return render(request, 'admin_module/update_personnel.html')

@custom_login_required
@role_required('Admin')
def password_request(request):
 return render(request, 'admin_module/password_request.html')

@custom_login_required
@role_required('Admin')
def activityLogs(request):
 return render(request, 'admin_module/activityLogs.html')