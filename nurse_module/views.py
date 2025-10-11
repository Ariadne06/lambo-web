from django.shortcuts import render
from authentication.decorators import custom_login_required, role_required
from django.contrib import messages
from django.db import connection
from .models import Dashboard

# Create your views here.
@custom_login_required
@role_required('Midwife')
def nurse_dashboard(request):
    barangay = request.GET.get("barangay") or None
    city     = request.GET.get("city") or None

    # Totals
    try:
        totals = Dashboard.sp_dashboard_totals(barangay=barangay, city=city)
    except Exception as e:
        messages.error(request, f"Failed loading totals: {e}")
        totals = {"total_resident": 0, "total_non_resident": 0, "total_pending": 0, "total_male": 0, "total_female": 0}

    # Residents per sitio (no params)
    try:
        per_sitio_rows = Dashboard.sp_residents_per_sitio_json()
        print("DEBUG per_sitio_rows:", per_sitio_rows)  # check console once
        per_sitio_labels = [str(r.get("sitio_name", "Unknown")) for r in per_sitio_rows]
        per_sitio_data   = [int(r.get("resident_count") or 0)   for r in per_sitio_rows]
    except Exception as e:
        messages.error(request, f"Failed loading per-sitio data: {e}")
        per_sitio_labels, per_sitio_data = [], []

    # --- Age brackets (Pie) ---
    try:
        age_rows = Dashboard.sp_age_bracket_distribution()  # no params

        # unwrap if each item is {"jsonb_build_object": {...}}
        cleaned = []
        for item in age_rows or []:
            if isinstance(item, dict) and "jsonb_build_object" in item:
                cleaned.append(item["jsonb_build_object"])
            else:
                cleaned.append(item)

        age_labels = [str(r.get("bracket", "Unknown")) for r in cleaned]
        age_data   = [int(r.get("count") or 0) for r in cleaned]

        total = sum(age_data) or 1
        age_labels_pct = [f"{lbl} ({round((cnt/total)*100)}%)" for lbl, cnt in zip(age_labels, age_data)]
    except Exception as e:
        messages.error(request, f"Failed loading age distribution: {e}")
        age_labels, age_data, age_labels_pct = [], [], []

    ctx = {
        "totals": totals,
        "per_sitio_labels": per_sitio_labels,
        "per_sitio_data": per_sitio_data,
        "age_labels": age_labels,
        "age_labels_pct": age_labels_pct,  # optional pretty legend
        "age_data": age_data,
    }
    return render(request, "secretary_module/secretary_dashboard.html", ctx)

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