from django.shortcuts import render

# Create your views here.
def nurse_dashboard(request):
    return render(request, 'nurse_module/nurse_dashboard.html')

def nurse_residentList(request):
    return render(request, 'nurse_module/nurse_residentList.html')

def nurse_moreResident(request):
    return render(request, 'nurse_module/nurse_moreResident.html')

def nurse_household(request):
    return render(request, 'nurse_module/nurse_household.html')

def householdMore(request):
    return render(request, 'nurse_module/householdMore.html')

def householdInfo1(request):
    return render(request, 'nurse_module/householdInfo1.html')

def householdInfo2(request):
    return render(request, 'nurse_module/householdInfo2.html')

def childrecordList(request):
    return render(request, 'nurse_module/childrecordList.html')

def moreChildRecord(request):
    return render(request, 'nurse_module/moreChildRecord.html')

def childImmunization(request):
    return render(request, 'nurse_module/childImmunization.html')

def childSupplements(request):
    return render(request, 'nurse_module/childSupplements.html')

def childGrowth(request):
    return render(request, 'nurse_module/childGrowth.html')

def childSurgical(request):
    return render(request, 'nurse_module/childSurgical.html')