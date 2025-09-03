from django.shortcuts import render

# Create your views here.

def secretary_dashboard(request):
    return render(request, 'secretary_module/secretary_dashboard.html')

def resident_list(request):
    return render(request, 'secretary_module/resident_list.html')

def household_list(request):
    return render(request, 'secretary_module/household_list.html')

def moreHousehold(request):
    return render(request, 'secretary_module/moreHousehold.html')

def Addbusiness(request):
    return render(request, 'secretary_module/Addbusiness.html')

def businessDetail1(request):
    return render(request, 'secretary_module/businessDetail1.html')

def businessDetail2(request):
    return render(request, 'secretary_module/businessDetail2.html')

def businessDetail3(request):
    return render(request, 'secretary_module/businessDetail3.html')

def manageBusiness(request):
    return render(request, 'secretary_module/manageBusiness.html')

def addCertificate(request):
    return render(request, 'secretary_module/addCertificate.html')

def manageCert1(request):
    return render(request, 'secretary_module/manageCert1.html')

def manageCert2(request):
    return render(request, 'secretary_module/manageCert2.html')

def applications(request):
    return render(request, 'secretary_module/applications.html')

def priceUpdate(request):
    return render(request, 'secretary_module/priceUpdate.html')

def announcement(request):
    return render(request, 'secretary_module/announcement.html')

def approval(request):
    return render(request, 'secretary_module/approval.html')

