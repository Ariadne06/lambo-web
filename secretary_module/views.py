from django.shortcuts import render, redirect
from authentication.decorators import custom_login_required, role_required

# Create your views here.

@custom_login_required
@role_required('Barangay Secretary')
def secretary_dashboard(request):
    return render(request, 'secretary_module/secretary_dashboard.html')

@custom_login_required
@role_required('Barangay Secretary')
def resident_list(request):
    return render(request, 'secretary_module/resident_list.html')

@custom_login_required
@role_required('Barangay Secretary')
def household_list(request):
    return render(request, 'secretary_module/household_list.html')

@custom_login_required
@role_required('Barangay Secretary')
def moreHousehold(request):
    return render(request, 'secretary_module/moreHousehold.html')

@custom_login_required
@role_required('Barangay Secretary')
def Addbusiness(request):
    return render(request, 'secretary_module/Addbusiness.html')

@custom_login_required
@role_required('Barangay Secretary')
def businessDetail1(request):
    return render(request, 'secretary_module/businessDetail1.html')

@custom_login_required
@role_required('Barangay Secretary')
def businessDetail2(request):
    return render(request, 'secretary_module/businessDetail2.html')

@custom_login_required
@role_required('Barangay Secretary')
def businessDetail3(request):
    return render(request, 'secretary_module/businessDetail3.html')

@custom_login_required
@role_required('Barangay Secretary')
def business_list(request):
    return render(request, 'secretary_module/manageBusiness.html')

@custom_login_required
@role_required('Barangay Secretary')
def add_certificate(request):
    return render(request, 'secretary_module/addCertificate.html')

@custom_login_required
@role_required('Barangay Secretary')
def manageCert1(request):
    return render(request, 'secretary_module/manageCert1.html')

@custom_login_required
@role_required('Barangay Secretary')
def manageCert2(request):
    return render(request, 'secretary_module/manageCert2.html')

@custom_login_required
@role_required('Barangay Secretary')
def applications(request):
    return render(request, 'secretary_module/applications.html')

@custom_login_required
@role_required('Barangay Secretary')
def price_update(request):
    return render(request, 'secretary_module/priceUpdate.html')

@custom_login_required
@role_required('Barangay Secretary')
def announcement(request):
    return render(request, 'secretary_module/announcement.html')

@custom_login_required
@role_required('Barangay Secretary')
def approval(request):
    return render(request, 'secretary_module/approval.html')

