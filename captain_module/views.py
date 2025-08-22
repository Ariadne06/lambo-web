from django.shortcuts import render
from authentication.decorators import custom_login_required, role_required

# Create your views here.

@custom_login_required
@role_required('Barangay Captain')
def captain_dashboard(request):
    return render(request, 'captain_module/captain_dashboard.html')

@custom_login_required
@role_required('Barangay Captain')
def captain_viewMoreResident(request):
    return render(request, 'captain_module/captain_viewMoreResident.html')

@custom_login_required
@role_required('Barangay Captain')
def captain_viewResident(request):
    return render(request, 'captain_module/captain_viewResident.html')

@custom_login_required
@role_required('Barangay Captain')
def captain_householdList(request):
    return render(request, 'captain_module/captain_householdList.html')

@custom_login_required
@role_required('Barangay Captain')
def captain_moreHousehold(request):
    return render(request, 'captain_module/captain_moreHousehold.html')

@custom_login_required
@role_required('Barangay Captain')
def captain_businessList(request):
    return render(request, 'captain_module/captain_businessList.html')

@custom_login_required
@role_required('Barangay Captain')
def captain_moreBusinessInfo(request):
    return render(request, 'captain_module/captain_moreBusinessInfo.html')

@custom_login_required
@role_required('Captain')
def personnelRequest(request):
    return render(request, 'captain_module/personnelRequest.html')