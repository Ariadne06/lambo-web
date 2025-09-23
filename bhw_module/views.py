from django.shortcuts import render
from authentication.decorators import custom_login_required, role_required

# Create your views here.

from django.shortcuts import render

@custom_login_required
@role_required('Barangay Health Worker')
def bhw_dashboard(request):
    return render(request, 'bhw_module/bhw_dashboard.html')

@custom_login_required
@role_required('Barangay Health Worker')
def householdList(request):
    return render(request, 'bhw_module/householdList.html')

@custom_login_required
@role_required('Barangay Health Worker')
def householdView(request):
    return render(request, 'bhw_module/householdView.html')

@custom_login_required
@role_required('Barangay Health Worker')
def householdVisit(request):
    return render(request, 'bhw_module/householdVisit.html')

@custom_login_required
@role_required('Barangay Health Worker')
def residentList(request):
    return render(request, 'bhw_module/residentList.html')

@custom_login_required
@role_required('Barangay Health Worker')
def residentAdd1(request):
    return render(request, 'bhw_module/residentAdd1.html')

@custom_login_required
@role_required('Barangay Health Worker')
def residentAdd2(request):
    return render(request, 'bhw_module/residentAdd2.html')

@custom_login_required
@role_required('Barangay Health Worker')
def residentAdd3(request):
    return render(request, 'bhw_module/residentAdd3.html')

@custom_login_required
@role_required('Barangay Health Worker')
def residentAdd4(request):
    return render(request, 'bhw_module/residentAdd4.html')

@custom_login_required
@role_required('Barangay Health Worker')
def childList(request):
    return render(request, 'bhw_module/childList.html')

@custom_login_required
@role_required('Barangay Health Worker')
def addchild1(request):
    return render(request, 'bhw_module/addchild1.html')

@custom_login_required
@role_required('Barangay Health Worker')
def addchild2(request):
    return render(request, 'bhw_module/addchild2.html')

@custom_login_required
@role_required('Barangay Health Worker')
def addchild3(request):
    return render(request, 'bhw_module/addchild3.html')

@custom_login_required
@role_required('Barangay Health Worker')
def childView(request):
    return render(request, 'bhw_module/childView.html')

@custom_login_required
@role_required('Barangay Health Worker')
def genInfo(request):
    return render(request, 'bhw_module/genInfo.html')

@custom_login_required
@role_required('Barangay Health Worker')
def maternalList(request):
    return render(request, 'bhw_module/maternalList.html')

@custom_login_required
@role_required('Barangay Health Worker')
def maternalAdd(request):
    return render(request, 'bhw_module/maternalAdd.html')

@custom_login_required
@role_required('Barangay Health Worker')
def maternalView(request):
    return render(request, 'bhw_module/maternalView.html')

@custom_login_required
@role_required('Barangay Health Worker')
def HouseholdAdd(request):
    return render(request, 'bhw_module/HouseholdAdd.html')