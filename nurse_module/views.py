from django.shortcuts import render
from authentication.decorators import custom_login_required, role_required

# Create your views here.
@custom_login_required
@role_required('Midwife')
def nurse_dashboard(request):
    return render(request, 'nurse_module/nurse_dashboard.html')

@custom_login_required
@role_required('Midwife')
def nurse_residentList(request):
    return render(request, 'nurse_module/nurse_residentList.html')

@custom_login_required
@role_required('Midwife')
def nurse_moreResident(request):
    return render(request, 'nurse_module/nurse_moreResident.html')

@custom_login_required
@role_required('Midwife')
def nurse_household(request):
    return render(request, 'nurse_module/nurse_household.html')

@custom_login_required
@role_required('Midwife')
def householdMore(request):
    return render(request, 'nurse_module/householdMore.html')

@custom_login_required
@role_required('Midwife')
def householdInfo1(request):
    return render(request, 'nurse_module/householdInfo1.html')

@custom_login_required
@role_required('Midwife')
def householdInfo2(request):
    return render(request, 'nurse_module/householdInfo2.html')

@custom_login_required
@role_required('Midwife')
def childrecordList(request):
    return render(request, 'nurse_module/childrecordList.html')

@custom_login_required
@role_required('Midwife')
def moreChildRecord(request):
    return render(request, 'nurse_module/moreChildRecord.html')

@custom_login_required
@role_required('Midwife')
def childImmunization(request):
    return render(request, 'nurse_module/childImmunization.html')

@custom_login_required
@role_required('Midwife')
def childSupplements(request):
    return render(request, 'nurse_module/childSupplements.html')

@custom_login_required
@role_required('Midwife')
def childGrowth(request):
    return render(request, 'nurse_module/childGrowth.html')

@custom_login_required
@role_required('Midwife')
def childSurgical(request):
    return render(request, 'nurse_module/childSurgical.html')

@custom_login_required
@role_required('Midwife')
def maternalrecord(request):
    return render(request, 'nurse_module/maternalrecord.html')

@custom_login_required
@role_required('Midwife')
def Morematernalrecord(request):
    return render(request, 'nurse_module/Morematernalrecord.html')

def maternalObstetrical(request):
    return render(request, 'nurse_module/maternalObstetrical.html')

@custom_login_required
@role_required('Midwife')
def maternalCheckUp(request):
    return render(request, 'nurse_module/maternalCheckUp.html')

@custom_login_required
@role_required('Midwife')
def maternalImmunization(request):
    return render(request, 'nurse_module/maternalImmunization.html')

@custom_login_required
@role_required('Midwife')
def maternalScreening(request):
    return render(request, 'nurse_module/maternalScreening.html')

@custom_login_required
@role_required('Midwife')
def maternalLabScreening(request):
    return render(request, 'nurse_module/maternalLabScreening.html')

@custom_login_required
@role_required('Midwife')
def maternalSupplement(request):
    return render(request, 'nurse_module/maternalSupplement.html')

@custom_login_required
@role_required('Midwife')
def maternalIron(request):
    return render(request, 'nurse_module/maternalIron.html')

@custom_login_required
@role_required('Midwife')
def maternalOutcome(request):
    return render(request, 'nurse_module/maternalOutcome.html')

@custom_login_required
@role_required('Midwife')
def maternalPostpartum(request):
    return render(request, 'nurse_module/maternalPostpartum.html')

@custom_login_required
@role_required('Midwife')
def maternalSurgical(request):
    return render(request, 'nurse_module/maternalSurgical.html')

@custom_login_required
@role_required('Midwife')
def nurseGeneralInfo(request):
    return render(request, 'nurse_module/nurseGeneralInfo.html')

@custom_login_required
@role_required('Midwife')
def moreGenInfo(request):
    return render(request, 'nurse_module/moreGenInfo.html')

@custom_login_required
@role_required('Midwife')
def ImmunizationStatus(request):
    return render(request, 'nurse_module/ImmunizationStatus.html')