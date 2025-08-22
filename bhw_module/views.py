from django.shortcuts import render

# Create your views here.

from django.shortcuts import render

# Create your views here.
def bhw_dashboard(request):
    return render(request, 'bhw_module/bhw_dashboard.html')

def householdList(request):
    return render(request, 'bhw_module/householdList.html')

def addHousehold1(request):
    return render(request, 'bhw_module/addHousehold1.html')

def addHousehold2(request):
    return render(request, 'bhw_module/addHousehold2.html')

def addHousehold3(request):
    return render(request, 'bhw_module/addHousehold3.html')

def addHousehold4(request):
    return render(request, 'bhw_module/addHousehold4.html')

def addHousehold5(request):
    return render(request, 'bhw_module/addHousehold5.html')

def householdView(request):
    return render(request, 'bhw_module/householdView.html')

def householdVisit(request):
    return render(request, 'bhw_module/householdVisit.html')

def memberProfile1(request):
    return render(request, 'bhw_module/memberProfile1.html')

def memberProfile2(request):
    return render(request, 'bhw_module/memberProfile2.html')

def residentList(request):
    return render(request, 'bhw_module/residentList.html')

def residentUpdate(request):
    return render(request, 'bhw_module/residentUpdate.html')

def residentUpdate1(request):
    return render(request, 'bhw_module/residentUpdate1.html')

def residentAdd1(request):
    return render(request, 'bhw_module/residentAdd1.html')

def residentAdd2(request):
    return render(request, 'bhw_module/residentAdd2.html')

def residentAdd3(request):
    return render(request, 'bhw_module/residentAdd3.html')

def residentAdd4(request):
    return render(request, 'bhw_module/residentAdd4.html')

def childList(request):
    return render(request, 'bhw_module/childList.html')

def addchild1(request):
    return render(request, 'bhw_module/addchild1.html')

def addchild2(request):
    return render(request, 'bhw_module/addchild2.html')

def addchild3(request):
    return render(request, 'bhw_module/addchild3.html')

def childView(request):
    return render(request, 'bhw_module/childView.html')

def childUpdate(request):
    return render(request, 'bhw_module/childUpdate.html')