from django.shortcuts import render, redirect
from httpx import request
from authentication.decorators import custom_login_required, role_required
from django.contrib import messages
from django.db import connection
from .models import Dashboard
from household_module.models import Household, Family
from utils.flash import set_flash, get_flash
from utils.db_message import _clean_db_error, _clean_params, coerce_message
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from utils.constants import LIMIT_OPTIONS
from django.utils.http import urlencode
from django.urls import reverse
import json

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
    return render(request, "bhw_module/bhw_dashboard.html", ctx)

@custom_login_required
@role_required('Barangay Health Worker')
def householdList(request):
    
    limit = None
    offset = None
    results = []
    status= ''
    
    query = (request.GET.get('query') or '').strip()
    status = (request.GET.get('status') or 'all').strip()
    raw_sitio = request.GET.get('sitio_id')
    quarter_id = request.POST.get('quarter_id') or request.GET.get('quarter_id')
    current_quarter_id = Household.sp_get_current_quarter_id()
    
    if quarter_id:
        quarter_id = int(quarter_id)
    elif current_quarter_id:
        quarter_id = int(current_quarter_id)
    else:
        quarter_id = None  # or some default value if needed


    try:
        sitio_id = int(raw_sitio) if raw_sitio not in (None, '', '0') else None
    except ValueError:
        sitio_id = None  # ignore bad input
    
    try:
        limit = int(request.GET.get("limit", 25))
    except Exception:
        limit = 25
    if limit not in LIMIT_OPTIONS:
        limit = 25

    try:
        page = int(request.GET.get("page", 1))
    except Exception:
        page = 1
    if page < 1:
        page = 1
    
    offset = (page - 1) * limit
    
    try:
        results = Household.sp_get_all_households(
            query=query,
            barangay=None,
            sitio_id=sitio_id,
            status=status,
            quarter_id=quarter_id,
            limit=limit + 1,
            offset=offset,
        )
    except Exception as e:
        msg = _clean_db_error(e)
        set_flash(request, str(e), "error")
    
    has_next = len(results) > limit
    has_prev = page > 1
    final_result = results[:limit]
    
    base_params = {
        "limit": limit,
        "query": query,
        "status": status,
    }
    if sitio_id is not None:
        base_params["sitio_id"] = sitio_id

    prev_url = "?" + urlencode({**base_params, "page": page - 1}) if has_prev else ""
    next_url = "?" + urlencode({**base_params, "page": page + 1}) if has_next else ""
    limit_urls = {n: "?" + urlencode({**base_params, "limit": n, "page": 1}) for n in LIMIT_OPTIONS}

    
    sitio = Household.sp_get_sitio()
    quarter = Household.sp_get_quarter()
    
    flash = get_flash(request)
    return render(request, 'bhw_module/householdList.html',{
        "results": final_result,
        "limit": limit,
        "page": page,
        'status': status,
        'sitio_id': sitio_id,
        "has_prev": has_prev,
        "has_next": has_next,
        "prev_url": prev_url,
        "next_url": next_url,
        "limit_options": LIMIT_OPTIONS,
        "limit_urls": limit_urls,
        'query': query,
        'sitio': sitio,
        'quarter': quarter,
        'quarter_id': quarter_id,
        'message': flash['message'],
        'message_level': flash['message_level'],
    })
    
@custom_login_required
@role_required('Barangay Health Worker')
@require_POST
def mark_household_visit(request):
    # optional: keep user's current filters/pagination to return to
    back_url = request.POST.get('redirect') or reverse('bhw_module:householdList')

    hid_raw = request.POST.get('household_id')
    pid_raw = request.session.get('personnel_id')
    visited = request.POST.get('visited')  # expects "True" or "False"

    # Validate inputs early (avoid int(None))
    if not hid_raw:
        set_flash(request, "Missing household id.", "error")
        return redirect(back_url)
    if not pid_raw:
        set_flash(request, "Missing personnel id.", "error")
        return redirect(back_url)

    try:
        hid = int(hid_raw)
        pid = int(pid_raw)
    except (TypeError, ValueError):
        set_flash(request, "Invalid id value.", "error")
        return redirect(back_url)

    # Simple trapping based on posted flag
    if visited == 'True':
        set_flash(request, "Household already marked as visited.", "info")
        return redirect(back_url)

    try:
        # Call your stored procedure / function
        Household.sp_mark_household_visited(hid, pid)
        set_flash(request, "Household marked as visited.", "success")
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")

    return redirect(back_url)

    
@custom_login_required
@role_required('Barangay Health Worker')
@require_POST
def update_household(request):
    hid = int(request.POST.get('household_id') or 0)
    pid = int(request.session.get('personnel_id') or 0)

    def redirect_to_view():
        url = reverse('bhw_module:householdView') + "?" + urlencode({"hid": hid}) if hid else reverse('bhw_module:householdList')
        return redirect(url)

    if not pid:
        set_flash(request, "Missing personnel id.", "error")
        return redirect('bhw_module:householdList')

    # pull current row to compare against
    try:
        prev = Household.sp_get_specific_household(hid)
        if not prev:
            set_flash(request, "Household not found.", "error")
            return redirect('bhw_module:householdList')
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")
        return redirect('bhw_module:householdList')

    # ----- current (normalize) -----
    curr_ho_id    = int(prev.get('house_ownership_id'))
    curr_ht_id    = int(prev.get('house_type_id'))
    curr_rth_id   = int(prev.get('respondent_rth_id'))
    curr_sitio_id = int(prev.get('sitio_id'))
    curr_head_id  = int(prev.get('household_head_id'))
    curr_resp_id  = int(prev.get('respondent_id'))

    curr_barangay = (prev.get('barangay') or '').strip()
    curr_city     = (prev.get('city_municipality') or '').strip()
    curr_house_no = (prev.get('house_number') or '').strip()
    curr_street   = (prev.get('street') or '').strip()
    curr_country  = (prev.get('country') or '').strip()

    # ----- posted (convert) -----
    try:
        house_ownership_id = int(request.POST.get('house_ownership'))
        house_type_id      = int(request.POST.get('house_type'))
        sitio_id           = int(request.POST.get('sitio_id'))
        head_id            = int(request.POST.get('head_id'))
        respondent_id      = int(request.POST.get('respondent_id'))
        respondent_rth     = int(request.POST.get('respondent_rth'))
    except (TypeError, ValueError):
        set_flash(request, "Invalid numeric field(s).", "error")
        return redirect_to_view()

    barangay = (request.POST.get('barangay') or '').strip()
    city     = (request.POST.get('municipality') or '').strip()
    street   = (request.POST.get('street') or '').strip()
    house_number = (request.POST.get('house_number') or '').strip() or curr_house_no
    country = 'Philippines'

    # ----- compare -----
    changed = []
    if house_ownership_id != curr_ho_id:                   changed.append("House ownership")
    if house_type_id      != curr_ht_id:                   changed.append("House type")
    if sitio_id           != curr_sitio_id:                changed.append("Sitio")
    if head_id            != curr_head_id:                 changed.append("Household head")
    if respondent_id      != curr_resp_id:                 changed.append("Respondent")
    if respondent_rth     != curr_rth_id:                  changed.append("Relationship to head")
    if (barangay or '').casefold()     != curr_barangay.casefold(): changed.append("Barangay")
    if (city or '').casefold()         != curr_city.casefold():     changed.append("Municipality/City")
    if (house_number or '').casefold() != curr_house_no.casefold(): changed.append("House number")
    if (street or '').casefold()       != curr_street.casefold():   changed.append("Street")
    if (country or '').casefold()      != curr_country.casefold():  changed.append("Country")

    if not changed:
        set_flash(request, "No changes detected — nothing to update.", "info")
        return redirect_to_view()

    try:
        Household.sp_update_household(
            hid,
            pid,
            house_ownership_id,
            house_type_id,
            barangay,
            city,
            house_number,
            street,
            sitio_id,
            country,
            head_id,
            respondent_id,
            respondent_rth,
        )
        set_flash(request, f"Household updated successfully. Changed: {', '.join(changed)}.", "success")
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")

    return redirect_to_view()

@custom_login_required
@role_required('Barangay Health Worker')
@require_POST
def insert_family(request):
    hid = int(request.POST.get('household_id') or 0)
    pid = int(request.session.get('personnel_id') or 0)

    def redirect_to_view():
        url = reverse('bhw_module:householdView') + "?" + urlencode({"household_id": hid})
        return redirect(url)

    if not pid:
        set_flash(request, "Missing personnel id.", "error")
        return redirect('bhw_module:householdList')
    
    if request.method == 'POST':
        family_head_id = int(request.POST.get('family_head_id'))
        respondent_id = int(request.POST.get('respondent_id'))
        fam_head_rel = int(request.POST.get('fam_head_rel'))
        respondent_rel = int(request.POST.get('respondent_rel'))
        household_type = int(request.POST.get('household_type'))
        waste_management_type = int(request.POST.get('waste_management_type'))
        water_source_type = int(request.POST.get('water_source_type'))
        toilet_facility_type = int(request.POST.get('toilet_facility_type'))
        nhts_status     = (request.POST.get('nhts_status') == 'true')
        indigent_status = (request.POST.get('indigent_status') == 'true')
        ip_tribe        = (request.POST.get('ip_tribe') or '').strip()
        waste_other_text = ''
        performed_by_type = 'personnel'
        bhw_assignment = False
    
        try:
            Family.sp_insert_family(
                hid,
                household_type,
                family_head_id,
                water_source_type,
                toilet_facility_type,
                waste_management_type,
                respondent_id,
                respondent_rel,
                fam_head_rel,
                indigent_status,
                ip_tribe,
                nhts_status,
                waste_other_text,
                pid,
                performed_by_type,
                bhw_assignment
            )
            set_flash(request, f"Family Profile added successfully.", "success")
        except Exception as e:
            set_flash(request, _clean_db_error(e), "error")

    return redirect_to_view()

@custom_login_required
@role_required('Barangay Health Worker')
def householdView(request):
    # Read from GET first (links / reloads), then POST (form submits)
    raw_hid = (
        request.GET.get('household_id')
        or request.POST.get('household_id')
        or request.GET.get('hid')          # fallback for older links
    )
    qid_raw = request.GET.get('quarter_id') or request.POST.get('quarter_id')
    household_number = (
        request.GET.get('household_number')
        or request.session.get('household_number')
        or request.POST.get('household_number')
    )

    if not raw_hid:
        set_flash(request, "No household selected.", "error")
        return redirect('bhw_module:householdList')

    try:
        hid = int(raw_hid)
    except (TypeError, ValueError):
        set_flash(request, "Invalid household id.", "error")
        return redirect('bhw_module:householdList')

    # Parse quarter id if present
    qid = None
    try:
        if qid_raw not in (None, ""):
            qid = int(qid_raw)
    except (TypeError, ValueError):
        qid = None  # fall back to whatever your SP treats as "current quarter"

    try:
        result   = Household.sp_get_specific_household(hid, qid)
        rows_raw = Family.sp_get_family_summaries_per_household(hid, qid)
        if not result:
            set_flash(request, "Household not found.", "error")
            return redirect('bhw_module:householdList')
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")
        return redirect('bhw_module:householdList')

    # Build families list and decode JSONB members
    families = []
    for r in rows_raw or []:
        # Skip sentinel row from your SQL (family_id = 0)
        if not r.get('family_id'):
            continue

        members = r.get('family_members') or []
        if isinstance(members, str):
            try:
                members = json.loads(members)
            except Exception:
                members = []

        # add initials for chips (optional)
        for m in members:
            name = (m.get('full_name') or '').strip()
            parts = [p for p in name.split() if p]
            m['initials'] = (''.join(p[0] for p in parts[:2]) or 'NA').upper()

        families.append({
            'family_id':               r.get('family_id'),
            'family_code':             r.get('family_code') or '',
            'family_head':             r.get('family_head') or '',
            'respondent':              r.get('respondent_name') or '',
            'head_rth':                r.get('respondent_relationship') or '',
            'nhts_status':             bool(r.get('nhts_status')),
            'indigent':                bool(r.get('indigent')),
            'household_type':          r.get('household_type') or '',
            'water_source':            r.get('water_source') or '',
            'waste_management':        r.get('waste_management') or '',
            'toilet_type':             r.get('toilet_type') or '',
            'members':                 members,
        })

    # reflect chosen quarter in result (your existing bit) …
    if qid is not None:
        try:
            setattr(result, 'quarter_id', qid)
        except Exception:
            if isinstance(result, dict):
                result['quarter_id'] = qid

    relationship     = Household.sp_get_relationship_to_household_head()
    house_ownership  = Household.sp_get_house_ownership()
    house_type       = Household.sp_get_house_type()
    sitio            = Household.sp_get_sitio()
    household_type   = Household.sp_get_household_type()
    water_source     = Family.sp_get_water_source_type()
    quarter          = Household.sp_get_quarter()
    waste_management = Family.sp_get_waste_management_type()
    toilet_facility  = Family.sp_get_toilet_facility_type()
    family_relationship = Family.sp_get_relationship_to_family_head()

    flash = get_flash(request)
    return render(request, 'bhw_module/householdView.html', {
        'relationship': relationship,
        'house_ownership': house_ownership,
        'house_type': house_type,
        'sitio': sitio,
        'household_type': household_type,
        'water_source': water_source,
        'quarter': quarter,
        'household_number': household_number,
        'waste_management': waste_management,
        'toilet_facility': toilet_facility,
        'hid': hid,
        'family_relationship': family_relationship,
        'results': result,
        'families': families,
        'message': flash['message'],
        'message_level': flash['message_level'],
    })

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
    query = (request.GET.get('query') or '').strip()
    
    if request.method == 'POST':
        hh_id = int(request.POST.get('household_head_id') or 0)
        res_id = int(request.POST.get('respondent_id') or 0)
        relationship_id = int(request.POST.get('relationship') or 0)
        house_number = (request.POST.get('household_number') or '').strip()
        house_ownership_id = int(request.POST.get('house_ownership') or 0)
        house_type_id = int(request.POST.get('house_type') or 0)
        sitio_id = int(request.POST.get('sitio') or 0)
        street = (request.POST.get('street') or '').strip()
        barangay = (request.POST.get('barangay') or '').strip()
        city = (request.POST.get('municipality_city') or '').strip()
        pid = int(request.session.get('personnel_id') or 0)
        country ='Philippines'
        
        try:
            result = Household.sp_insert_household(
                house_ownership_id, 
                house_type_id,
                barangay,
                city,
                sitio_id,
                pid,
                house_number,
                street,
                country,
                hh_id, 
                res_id, 
                relationship_id, 
            )
            msg = coerce_message(result, "Household successfully added.")
            set_flash(request, msg, 'success')
            return redirect('bhw_module:householdList')
        except Exception as e:
            msg = _clean_db_error(e)
            set_flash(request, msg, "error")
            return redirect('bhw_module:HouseholdAdd')
        

    if query:
        results = Household.sp_search_resident(query)
    
    relationship = Household.sp_get_relationship_to_household_head()
    house_ownership = Household.sp_get_house_ownership()
    house_type = Household.sp_get_house_type()
    sitio = Household.sp_get_sitio()
    
    flash = get_flash(request)
    return render(request, 'bhw_module/HouseholdAdd.html', {
        'relationship': relationship,
        'house_ownership': house_ownership,
        'house_type': house_type,
        'sitio': sitio,
        'results': results if query else [],
        'query': query,
        'message': flash['message'],
        'message_level': flash['message_level'],
    })

@custom_login_required
@role_required('Barangay Health Worker')
@require_GET
def resident_search_api(request):
    q = (request.GET.get('q') or '').strip()
    if not q:
        return JsonResponse({'results': []})
    try:
        rows = Household.sp_search_resident(q)  # uses your stored proc
        # Normalize/whitelist fields returned to the frontend
        normalized = []
        for r in rows:
            normalized.append({
                'resident_id': r.get('resident_id') or r.get('id') or r.get('residentid'),
                'full_name': r.get('full_name') or r.get('fullname') or r.get('name'),
                'address': r.get('address') or '',
                'sex': r.get('sex') or '',
                'dob': r.get('dob') or '',
            })
        return JsonResponse({'results': normalized})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)