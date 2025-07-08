from django.shortcuts import render

# Create your views here.

def admin_dashboard(request):
    return render(request, 'admin_module/admin_dashboard.html')

def admin_Addpersonnel(request):
    return render(request, 'admin_module/admin_Addpersonnel.html')

def add_personnel1(request):
 return render(request, 'admin_module/add_personnel1.html')

def add_personnel2(request):
 return render(request, 'admin_module/add_personnel2.html')

def personnel_list(request):
 return render(request, 'admin_module/personnel_list.html')

def update_personnel(request):
 return render(request, 'admin_module/update_personnel.html')

def password_request(request):
 return render(request, 'admin_module/password_request.html')

def activityLogs(request):
 return render(request, 'admin_module/activityLogs.html')