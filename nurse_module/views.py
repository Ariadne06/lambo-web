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

def maternalrecord(request):
    return render(request, 'nurse_module/maternalrecord.html')

def Morematernalrecord(request):
    return render(request, 'nurse_module/Morematernalrecord.html')

def maternalObstetrical(request):
    return render(request, 'nurse_module/maternalObstetrical.html')

def maternalCheckUp(request):
    return render(request, 'nurse_module/maternalCheckUp.html')

def maternalImmunization(request):
    return render(request, 'nurse_module/maternalImmunization.html')

def maternalScreening(request):
    return render(request, 'nurse_module/maternalScreening.html')

def maternalLabScreening(request):
    return render(request, 'nurse_module/maternalLabScreening.html')

def maternalSupplement(request):
    return render(request, 'nurse_module/maternalSupplement.html')

def maternalIron(request):
    return render(request, 'nurse_module/maternalIron.html')

def maternalOutcome(request):
    return render(request, 'nurse_module/maternalOutcome.html')

def maternalPostpartum(request):
    return render(request, 'nurse_module/maternalPostpartum.html')

def maternalSurgical(request):
    return render(request, 'nurse_module/maternalSurgical.html')

def nurseGeneralInfo(request):
    return render(request, 'nurse_module/nurseGeneralInfo.html')

def moreGenInfo(request):
    return render(request, 'nurse_module/moreGenInfo.html')

def ImmunizationStatus(request):
    return render(request, 'nurse_module/ImmunizationStatus.html')