from django.shortcuts import render
from authentication.decorators import custom_login_required, role_required
from django.contrib import messages
from django.db import connection
from .models import Dashboard

# Create your views herevenv\Scripts\activate
@custom_login_required
@role_required('Barangay Health Worker')
def bhw_dashboard(request):
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