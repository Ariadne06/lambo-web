from django.shortcuts import render, redirect
from authentication.decorators import custom_login_required, role_required
from django.utils.http import urlencode
from utils.flash import set_flash, get_flash
from utils.db_message import _clean_db_error, _clean_params, coerce_message
from utils.constants import VALID_SORT_BY, VALID_SORT_DIR, LIMIT_OPTIONS
from .models import (
    Secretary, Dashboard, BusinessFee, AmusementDeviceType, OtherClearanceType,
    BusinessTaxConfig, AnnouncementRepo, Business, SecretaryHelpers,ResidentList
)
from utils.supa import url_for_doc
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.db import connection
from math import ceil
from django.core.paginator import Paginator
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods
from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.conf import settings
from django.core.files.storage import default_storage
from datetime import datetime
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from urllib.parse import urlencode
from household_module.models import Household, Family
import json
from django.views.decorators.http import require_GET

# PDF generation (HTML -> PDF)
import io, os
from django.conf import settings
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject, NumberObject

_UI_TO_SQL_AUDIENCE = {
    'EVERYONE': 'both',
    'PERSONNEL': 'personnel',
    'RESIDENTS': 'resident',
    'both': 'both', 'personnel': 'personnel', 'resident': 'resident',  # tolerate lowercase
}
_SQL_TO_UI_AUDIENCE = {
    'both': 'EVERYONE',
    'personnel': 'PERSONNEL',
    'resident': 'RESIDENTS',
}

def _to_list(val):
    if val is None: return []
    if isinstance(val, (list, tuple)): return [str(v) for v in val]
    s = str(val).strip()
    try:
        j = json.loads(s)
        if isinstance(j, list):
            return [str(v) for v in j]
    except Exception:
        pass
    return [p.strip().strip('[]{}()"\'') for p in s.split(',') if p.strip()]


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def secretary_dashboard(request):
    barangay = request.GET.get("barangay") or None
    city     = request.GET.get("city") or None

    # ---- Totals (KPIs) ----
    try:
        totals = Dashboard.sp_dashboard_totals(barangay=barangay, city=city)
    except Exception as e:
        messages.error(request, f"Failed loading totals: {e}")
        totals = {
            "total_resident": 0, "total_non_resident": 0, "total_pending": 0,
            "total_male": 0, "total_female": 0
        }

    # ---- Residents per sitio (bar chart) ----
    try:
        per_sitio_rows   = Dashboard.sp_residents_per_sitio_json()
        per_sitio_labels = [str(r.get("sitio_name", "Unknown")) for r in per_sitio_rows]
        per_sitio_data   = [int(r.get("resident_count") or 0)   for r in per_sitio_rows]
    except Exception as e:
        messages.error(request, f"Failed loading per-sitio data: {e}")
        per_sitio_labels, per_sitio_data = [], []

    # ---- Age distribution (pie) ----
    try:
        age_rows = Dashboard.sp_age_bracket_distribution()
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

    # ===========================
    # Announcements (Secretary sees personnel + both)
    # ===========================
    ALLOWED = {"personnel", "both"}

    # Pull a few recent then filter to ALLOWED and take top 3
    try:
        # ask for more than 3, then slice after filtering to ensure we still get 3
        rows = AnnouncementRepo.list_all(sort='date_desc', limit=12, audience=None)
        latest_announcements = []
        for a in rows:
            # normalize aliases
            if 'created_date' in a and 'announcement_date' not in a:
                a['announcement_date'] = a['created_date']
            aud = (a.get('audience') or 'both').lower()
            if aud in ALLOWED:
                a['audience'] = aud
                latest_announcements.append(a)
            if len(latest_announcements) >= 3:
                break
    except Exception as e:
        messages.error(request, f"Failed loading latest announcements: {e}")
        latest_announcements = []

    # Modal filters (GET -> ann_*)
    ann_q        = (request.GET.get('ann_q') or '').strip() or None
    ann_aud      = (request.GET.get('ann_audience') or '').strip() or None  # '', resident, personnel, both
    ann_from_str = (request.GET.get('ann_from') or '').strip()
    ann_to_str   = (request.GET.get('ann_to') or '').strip()

    ann_from = ann_to = None
    try:
        if ann_from_str:
            ann_from = datetime.strptime(ann_from_str, '%Y-%m-%d').date()
        if ann_to_str:
            ann_to = datetime.strptime(ann_to_str, '%Y-%m-%d').date()
    except ValueError:
        messages.warning(request, 'Invalid date filter for announcements.')

    # Full list for the modal (server filter + enforce secretary scope)
    try:
        announcements_all = AnnouncementRepo.list_all(
            q=ann_q, date_from=ann_from, date_to=ann_to,
            created_by=None, sort='date_desc', limit=200, offset=0,
            audience=ann_aud or None   # None = DB shows all audiences
        )
        filtered = []
        for a in announcements_all:
            if 'created_date' in a and 'announcement_date' not in a:
                a['announcement_date'] = a['created_date']
            a['audience'] = (a.get('audience') or 'both').lower()
            if a['audience'] in ALLOWED:
                filtered.append(a)
        announcements_all = filtered
    except Exception as e:
        messages.error(request, f"Failed loading announcements list: {e}")
        announcements_all = []

    ann_open = request.GET.get('ann_open') == '1'

    ctx = {
        "totals": totals,
        "per_sitio_labels": per_sitio_labels,
        "per_sitio_data": per_sitio_data,
        "age_labels": age_labels,
        "age_labels_pct": age_labels_pct,
        "age_data": age_data,

        "latest_announcements": latest_announcements,
        "announcements_all": announcements_all,
        "ann_filters": {
            "q": ann_q or "",
            "audience": (ann_aud or ""),
            "from": ann_from_str,
            "to": ann_to_str,
        },
        "ann_open": ann_open,
    }
    return render(request, "secretary_module/secretary_dashboard.html", ctx)

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def resident_list(request):
    q = request.GET.get("q") or None
    sex = request.GET.get("sex") or None            # 'male'/'female'
    status_id = request.GET.get("status_id") or None
    min_age = request.GET.get("min_age") or None
    max_age = request.GET.get("max_age") or None
    page = int(request.GET.get("page") or 1)
    page_size = int(request.GET.get("page_size") or 50)

    # Coerce ints
    try:
        status_id = int(status_id) if status_id not in (None, "",) else None
    except ValueError:
        status_id = None
    try:
        min_age = int(min_age) if min_age not in (None, "",) else None
    except ValueError:
        min_age = None
    try:
        max_age = int(max_age) if max_age not in (None, "",) else None
    except ValueError:
        max_age = None

    result = ResidentList.search(
        p_query=q,
        p_sex=sex,
        p_status_id=status_id,
        p_min_age=min_age,
        p_max_age=max_age,
        page=page,
        page_size=page_size,
    )

    # Use the values returned by the search result
    page  = result["page"]
    pages = result["pages"]

    # Base params for pagination
    from django.utils.http import urlencode
    base_params = {
        "q": q or "",
        "sex": sex or "",
        "status_id": status_id if status_id is not None else "",
        "min_age": min_age if min_age is not None else "",
        "max_age": max_age if max_age is not None else "",
        "page_size": page_size,
    }
    def page_url(p):
        params = base_params.copy()
        params["page"] = p
        return f"?{urlencode(params)}"

    # Precompute URLs so template doesn't call functions
    prev_url  = page_url(page - 1) if page > 1 else None
    next_url  = page_url(page + 1) if page < pages else None
    curr_url  = page_url(page)

    p1_num, p1_url = page, curr_url
    p2_num, p2_url = (page + 1, page_url(page + 1)) if page < pages else (None, None)
    p3_num, p3_url = (page + 2, page_url(page + 2)) if page + 1 < pages else (None, None)
    last_num, last_url = (pages, page_url(pages)) if pages > 1 else (None, None)

    showing_start = (result["offset"] + 1) if result["total"] > 0 else 0
    showing_end = min(result["offset"] + len(result["rows"]), result["total"])

    with connection.cursor() as cur:
        cur.execute("SELECT status_id, status_name FROM Resident_Status ORDER BY status_name;")
        status_options = cur.fetchall()  # list of tuples [(id, name), ...]

    context = {
        "residents": result["rows"],
        "total": result["total"],
        "page": page,
        "pages": pages,
        "page_size": result["limit"],
        "showing_start": showing_start,
        "showing_end": showing_end,
        # pagination links/numbers
        "prev_url": prev_url,
        "next_url": next_url,
        "p1_num": p1_num, "p1_url": p1_url,
        "p2_num": p2_num, "p2_url": p2_url,
        "p3_num": p3_num, "p3_url": p3_url,
        "last_num": last_num, "last_url": last_url,
        "status_options": status_options,
    }
    return render(request, 'secretary_module/resident_list.html', context)

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def household_list(request):
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
        quarter_id = None

    # ✅ Are we looking at the current quarter?
    is_current_quarter = bool(
        current_quarter_id is not None and quarter_id is not None and int(quarter_id) == int(current_quarter_id)
    )

    try:
        sitio_id = int(raw_sitio) if raw_sitio not in (None, '', '0') else None
    except ValueError:
        sitio_id = None
    
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
    # ✅ keep quarter in pagination / limit links
    if quarter_id is not None:
        base_params["quarter_id"] = quarter_id

    prev_url = "?" + urlencode({**base_params, "page": page - 1}) if has_prev else ""
    next_url = "?" + urlencode({**base_params, "page": page + 1}) if has_next else ""
    limit_urls = {n: "?" + urlencode({**base_params, "limit": n, "page": 1}) for n in LIMIT_OPTIONS}

    sitio = Household.sp_get_sitio()
    quarter = Household.sp_get_quarter()
    
    flash = get_flash(request)
    return render(request, 'secretary_module/household_list.html',{
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
        # ✅ expose these to the template
        'current_quarter_id': int(current_quarter_id) if current_quarter_id else None,
        'is_current_quarter': is_current_quarter,
        'message': flash['message'],
        'message_level': flash['message_level'],
    })
    
def _ok(payload=None):  return JsonResponse({"ok": True, **(payload or {})})
def _err(msg, code=400): return JsonResponse({"ok": False, "error": str(msg)}, status=code)

def _coerce_jsonb(v):
    # get_resident_links returns JSONB arrays for guardians/children
    if v is None: return []
    if isinstance(v, (list, tuple, dict)): return v
    if isinstance(v, (bytes, bytearray, memoryview)): v = bytes(v).decode('utf-8')
    if isinstance(v, str) and v: return json.loads(v)
    return []
    
@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_GET
def resident_links_list_api(request):
    try:
        rid = int(request.GET.get('resident_id') or 0)
        if not rid: return _err("resident_id is required.")
        # row with {mother_id, mother_name, mother_relationship_id, father_..., guardians, children}
        rows = Family.sp_get_resident_links(rid)
        row = rows[0] if rows else {}

        # relationship id -> name map for labels
        rel_rows = Family.sp_get_link_relationship()
        rel_map = {r["relationship_id"]: r["relationship_name"] for r in rel_rows}

        relations = []

        if row.get("mother_id"):
            relations.append({
                "related_resident_id": row["mother_id"],
                "full_name": row.get("mother_name"),
                "relationship_id": row.get("mother_relationship_id"),
                "relationship_label": rel_map.get(row.get("mother_relationship_id"), "Mother"),
            })
        if row.get("father_id"):
            relations.append({
                "related_resident_id": row["father_id"],
                "full_name": row.get("father_name"),
                "relationship_id": row.get("father_relationship_id"),
                "relationship_label": rel_map.get(row.get("father_relationship_id"), "Father"),
            })

        for key, fallback in (("guardians", "Guardian"), ("children", "Child")):
            for it in _coerce_jsonb(row.get(key)):
                rel_id = it.get("relationship_id")
                relations.append({
                    "related_resident_id": it.get("resident_id"),
                    "full_name": it.get("full_name"),
                    "relationship_id": rel_id,
                    "relationship_label": rel_map.get(rel_id, fallback),
                })

        return _ok({"relations": relations})
    except Exception as e:
        return _err(e)
    
@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_GET
def general_health_get_api(request):
    fm_id = request.GET.get("member_id") or request.GET.get("family_member_id")
    if not fm_id:
        return JsonResponse({"error": "member_id is required"}, status=400)
    try:
        fm_id = int(fm_id)
    except ValueError:
        return JsonResponse({"error": "member_id must be an integer"}, status=400)

    try:
        row = Family.sp_get_specific_family_member_genhealth(fm_id)
    except Exception as e:
        # Log if you have logging; return a safe message to client
        return JsonResponse({"error": "database_error", "detail": str(e)}, status=500)

    if not row:
        return JsonResponse({"record": None, "exists": False}, status=200)

    # ----- Optional normalization (keeps raw keys intact) -----
    # Map to the keys your JS expects; fall back to whatever the SP returns.
    record = dict(row)  # start with raw db keys

    # Friendly, consistent keys your modal code handles:
    record.setdefault("gh_id",                 row.get("record_id") or row.get("id") or row.get("general_health_id"))
    record.setdefault("smoker",                row.get("smoker"))
    record.setdefault("alcohol_drinker",       row.get("alcohol_drinker"))
    record.setdefault("sexually_active",       row.get("sexually_active"))
    record.setdefault("last_menstrual_period", row.get("last_menstrual_period"))
    record.setdefault("age_menarche",          row.get("age_of_menarche"))
    record.setdefault("fp_use",                row.get("fp_method_yn"))
    record.setdefault("fp_method_id",          row.get("fp_method_id"))
    record.setdefault("fp_status_id",          row.get("fp_status_id"))
    record.setdefault("class_id",              row.get("class_id"))
    # Normalize medical_history to list
    mh = row.get("medical_history") or row.get("medical_history_ids") or row.get("mh")
    record["medical_history"] = _to_list(mh)

    return JsonResponse({"record": record, "exists": True}, status=200)
    
@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def sec_householdView(request):
    
    def _to_bool(v):
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return v != 0
        if isinstance(v, str):
            return v.strip().lower() in {"true", "t", "1", "yes", "y"}
        return False

    raw_hid = (
        request.GET.get('household_id')
        or request.POST.get('household_id')
        or request.GET.get('hid') 
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
        qid = None

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

        
        for m in members:
            name = (m.get('full_name') or '').strip()
            parts = [p for p in name.split() if p]
            m['initials'] = (''.join(p[0] for p in parts[:2]) or 'NA').upper()

        families.append({
            'family_id':               r.get('family_id'),
            'family_code':             r.get('family_code') or '',
            'family_head':             r.get('family_head') or '',
            'respondent':              r.get('respondent_name') or '',
            'rtf':                     r.get('respondent_relationship') or '',
            'nhts_status':             _to_bool(r.get('nhts_status')),
            'indigent':                _to_bool(r.get('indigent')),
            'household_type':          r.get('household_type') or '',
            'water_source':            r.get('water_source') or '',
            'waste_management':        r.get('waste_management') or '',
            'is_visited':               _to_bool(r.get('is_visited')),
            'date_visited':             r.get('date_visited'),
            'toilet_type':             r.get('toilet_type') or '',
            'family_head_id':          r.get('family_head_id'),
            'respondent_id':           r.get('respondent_id'),
            'rth':                     r.get('relationship_of_family_head_to_hh ') or '',
            'rth_id':                  r.get('relationship_of_family_head_to_hh_id'),
            'rtf_id':                  r.get('relationship_of_respondent_to_family_head_id'),
            'household_type_id':       r.get('household__type_id'),
            'waste_management_id':     r.get('waste_management_id'),
            'water_source_id':         r.get('water_source_id'),
            'toilet_type_id':          r.get('toilet_type_id'),
            'ip_tribe':                r.get('ip_tribe') or '',
            'quarter_id':              r.get('quarter_id'),
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
    philhealth_category = Family.sp_get_philhealth_category()
    nutrition_status = Family.sp_get_nutrition_status()
    current_quarter = Household.sp_get_current_quarter_id()
    link_relationship = Family.sp_get_link_relationship()
    fp_method = Family.sp_get_fp_method()
    fp_status = Family.sp_get_fp_status()
    classification = Family.sp_get_classifications()

    flash = get_flash(request)
    return render(request, 'secretary_module/moreHousehold.html', {
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
        'philhealth_category': philhealth_category,
        'nutrition_status': nutrition_status,
        'fp_method': fp_method,
        'fp_status': fp_status,
        'class': classification,
        'results': result,
        'link_relationship': link_relationship,
        'current_quarter': current_quarter,
        'families': families,
        'message': flash['message'],
        'message_level': flash['message_level'],
    })

def _find_resident_id_by_name(query: str):
    """
    Uses your PostgreSQL function search_business_owner to resolve resident_id
    from a name/email/phone query. Returns a single resident_id or raises.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM search_business_owner(%s, %s, %s)", [query, 20, 0])
        rows = cursor.fetchall()

    if not rows:
        raise ValueError("Resident not found")
    if len(rows) > 1:
        raise ValueError("Multiple residents found. Please be more specific.")
    return rows[0][0]  # first column = resident_id

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def Addbusiness(request):
    # load dropdown options
    try:
        clearance_categories = Business.sp_get_business_clearance_categories_for_select()
    except Exception as e:
        clearance_categories = []
        set_flash(request, f"Could not load clearance categories: {e}", "error")

    if request.method == "POST":
        try:
            resident_name = request.POST.get("resident_name")
            resident_id = _find_resident_id_by_name(resident_name)

            business_name         = request.POST.get("business_name")
            business_type_id      = int(request.POST.get("business_type_id"))
            nature_of_business    = request.POST.get("nature_of_business")
            ownership_id          = int(request.POST.get("ownership_id"))
            house_number          = request.POST.get("house_number")
            street                = request.POST.get("street")
            barangay              = request.POST.get("barangay") or "Cansaga"
            sitio_id              = int(request.POST.get("sitio_id"))
            city_municipality     = request.POST.get("city_municipality") or "Consolacion"
            country               = request.POST.get("country") or "Philippines"
            total_gross_income    = request.POST.get("total_gross_income")
            dti_sec_cda_reg_num   = request.POST.get("dti_sec_cda_reg_number") or None
            clearance_category_id = int(request.POST.get("clearance_category_id"))
            clearance_date_issued = request.POST.get("clearance_date_issued") or None

            # total_units (optional overall; required by SP only if category supports it)
            total_units_raw = request.POST.get("total_units")
            total_units = int(total_units_raw) if (total_units_raw not in [None, ""]) else None

            # NEW: amusement device quantities (required by SP only if category is Amusement)
            def _i(val):
                return int(val) if (val not in [None, ""]) else None

            videoke_count       = _i(request.POST.get("videoke_count"))
            billiard_count      = _i(request.POST.get("billiard_count"))
            other_device_count  = _i(request.POST.get("other_device_count"))

            personnel_id = int(request.session.get("personnel_id"))

            Secretary.sp_register_business(
                resident_id, business_name, business_type_id, nature_of_business, ownership_id,
                house_number, street, barangay, sitio_id, city_municipality, country,
                total_gross_income, dti_sec_cda_reg_num, clearance_category_id,
                total_units,
                videoke_count, billiard_count, other_device_count,  # <-- NEW
                clearance_date_issued, personnel_id
            )
            set_flash(request, "Successfully Submitted", "success")
        except Exception as e:
            set_flash(request, str(e), "error")

    flash = get_flash(request)
    return render(request, "secretary_module/Addbusiness.html", {
        'message': flash.get('message'),
        'message_level': flash.get('message_level'),
        'clearance_categories': clearance_categories,
    })


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def business_list(request):
    q = (request.GET.get("q") or "").strip() or None
    status = request.GET.get("status") or None
    page = max(int(request.GET.get("page", 1)), 1)
    per_page = max(min(int(request.GET.get("per_page", 10)), 100), 1)
    offset = (page - 1) * per_page

    # ✅ Always use the business list SP so we have business_id in the rows.
    rows  = Business.sp_get_all_businesses(q, status, None, None, None, per_page, offset)
    total = _count_get_all_businesses(q, status)

    total_pages = max(ceil(total / per_page), 1)

    def page_window(curr, last, radius=1):
        if last <= 7:
            return list(range(1, last + 1))
        win = set([1, last])
        for p in range(curr - radius, curr + radius + 1):
            if 1 <= p <= last:
                win.add(p)
        win.add(2); win.add(last - 1)
        return sorted(win)

    page_numbers = page_window(page, total_pages)

    ctx = {
        "rows": rows,
        "q": q or "",
        "status": status or "",
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "page_numbers": page_numbers,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_page": page - 1,
        "next_page": page + 1,
    }

    with connection.cursor() as cur:
        cur.execute("SELECT business_type_id, type_name FROM business_type ORDER BY type_name")
        business_types = [{"id": row[0], "name": row[1]} for row in cur.fetchall()]

    with connection.cursor() as cur:
        cur.execute("SELECT ownership_id, ownership_name FROM ownership ORDER BY ownership_name")
        ownerships = [{"id": row[0], "name": row[1]} for row in cur.fetchall()]
    
    # NEW: clearance categories (includes supported_units from SQL)
    try:
        clearance_categories = Business.sp_get_business_clearance_categories_for_select()
    except Exception:
        clearance_categories = []

    ctx.update({
        "business_types": business_types,
        "ownerships": ownerships,
        "clearance_categories": clearance_categories,
    })
    return render(request, "secretary_module/manageBusiness.html", ctx)

def business_detail_json(request, business_id: int):
    """Returns JSON data for one business (for the View modal)."""
    data = Business.sp_get_business_detail(business_id)
    if not data:
        raise Http404("Business not found")
    return JsonResponse(data, safe=False)


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def business_renewal_summary_json(request, business_id: int):
    """Return renewal summary using get_business_renewal_summary(business_id).

    Response shape:
      { ok, business_id, business_status, needs_renewal, renewal_total, renewal_total_details }
    """
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM get_business_renewal_summary(%s)", [business_id])
            row = cur.fetchone()
            if not row:
                return JsonResponse({
                    'ok': False,
                    'message': 'No data returned for business.'
                }, status=404)

            cols = [c[0] for c in cur.description]
            payload = dict(zip(cols, row))

        # Normalize numeric for JSON
        total = payload.get('renewal_total')
        try:
            payload['renewal_total'] = float(total) if total is not None else None
        except Exception:
            pass

        payload['ok'] = True
        return JsonResponse(payload)
    except Exception as e:
        return JsonResponse({'ok': False, 'message': _clean_db_error(e)}, status=400)

def _count_get_all_businesses(q, status):
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) FROM (
              SELECT 1 FROM get_all_businesses(%s, %s, %s, %s, %s, %s, %s)
            ) t
            """,
            [q or None, status or None, None, None, None, 1_000_000_000, 0]
        )
        return cur.fetchone()[0]
    
def _none_if_blank(v):
    if v is None:
        return None
    if isinstance(v, str) and v.strip() == "":
        return None
    return v

def _to_int_or_none(v):
    try:
        return int(v) if _none_if_blank(v) is not None else None
    except (TypeError, ValueError):
        return None

def _to_decimal_or_none(v):
    v = _none_if_blank(v)
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None
    
    return render(request, "secretary_module/manageBusiness.html")

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_http_methods(["POST"])
def business_update(request, business_id: int):
    try:
        personnel_id = int(request.session.get("personnel_id") or 0)
        if not personnel_id:
            return JsonResponse({"ok": False, "message": "No personnel ID in session."}, status=400)

        # Current state (for rule checks)
        current = Business.sp_get_business_detail(business_id) or {}
        curr_own = int(current.get('ownership_id') or 0)
        curr_cat = int(current.get('clearance_category_id') or 0)

        # Optional owner transfer via name (uses your resolver)
        resident_name = (request.POST.get("resident_name") or "").strip()
        resident_id = None
        if resident_name:
            # Owner change only if NOT sole proprietorship (id=1)
            if curr_own == 1:
                return JsonResponse({"ok": False, "message": "Owner cannot be changed for Sole Proprietorship."}, status=400)
            resident_id = _find_resident_id_by_name(resident_name)

        # New (requested) clearance category
        new_cat = _to_int_or_none(request.POST.get("clearance_category_id"))

        # Rule: Clearance Category can change only:
        # - Sole Prop (3/4): within {3,4}
        # - Lessor (6..10): within 6..10
        # - Others: cannot change
        if new_cat is not None and new_cat != curr_cat:
            if curr_cat in (3, 4):
                if new_cat not in (3, 4):
                    return JsonResponse({"ok": False, "message": "Sole Proprietorship may switch only between categories 3 and 4."}, status=400)
            elif 6 <= curr_cat <= 10:
                if not (6 <= new_cat <= 10):
                    return JsonResponse({"ok": False, "message": "Lessor categories may switch only within 6–10."}, status=400)
            else:
                return JsonResponse({"ok": False, "message": "This clearance category cannot be changed."}, status=400)

        # Parse units and amusement device counts (zeros are valid)
        total_units        = _to_int_or_none(request.POST.get("total_units"))
        videoke_count      = _to_int_or_none(request.POST.get("videoke_count"))
        billiard_count     = _to_int_or_none(request.POST.get("billiard_count"))
        other_device_count = _to_int_or_none(request.POST.get("other_device_count"))

        # Build payload (leave non-editables as None so proc won’t touch them)
        payload = {
            "business_name":          _none_if_blank(request.POST.get("business_name")),
            "business_type_id":       None,  # not editable
            "nature_of_business":     _none_if_blank(request.POST.get("nature_of_business")),
            "ownership_id":           None,  # not editable
            "resident_id":            resident_id,  # only when provided and allowed
            "house_number":           _none_if_blank(request.POST.get("house_number")),
            "street":                 _none_if_blank(request.POST.get("street")),
            "barangay":               _none_if_blank(request.POST.get("barangay")),
            "sitio_id":               _to_int_or_none(request.POST.get("sitio_id")),
            "city_municipality":      _none_if_blank(request.POST.get("city_municipality")),
            "country":                _none_if_blank(request.POST.get("country")),
            "total_gross_income":     _to_decimal_or_none(request.POST.get("total_gross_income")),
            "clearance_category_id":  new_cat,   # may be None if unchanged or not allowed
            "dti_sec_cda_reg_number": None,      # not editable
            "total_units":            total_units,
            "videoke_count":          videoke_count,       # <-- NEW
            "billiard_count":         billiard_count,      # <-- NEW
            "other_device_count":     other_device_count,  # <-- NEW
        }

        result = Business.sp_update_business(
            business_id=business_id,
            updated_by=personnel_id,
            **payload
        )
        msg = coerce_message(result)
        return JsonResponse({"ok": True, "message": msg})

    except ValueError as ve:
        return JsonResponse({"ok": False, "message": str(ve)}, status=400)
    except Exception as e:
        return JsonResponse({"ok": False, "message": _clean_db_error(e)}, status=400)
        
@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_POST
def business_close(request, business_id: int):
    """
    Marks a business as Closed via the SQL function.
    Only Secretary / Assistant Secretary can do this (enforced here and in SQL).
    """
    try:
        personnel_id = int(request.session.get("personnel_id") or 0)
        if not personnel_id:
            return JsonResponse({"ok": False, "message": "No personnel ID in session."}, status=400)

        msg = Business.sp_set_closed_business(business_id, personnel_id)
        return JsonResponse({"ok": True, "message": msg})
    except Exception as e:
        # Return DB error (your SQL has nice messages)
        return JsonResponse({"ok": False, "message": str(e)}, status=400)

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def add_certificate(request):
    # Provide fee types and other clearance purposes for the Create UI
    try:
        fee_types = SecretaryHelpers.get_fee_types_dropdown()
    except Exception:
        fee_types = []
    try:
        other_clearances = SecretaryHelpers.get_other_clearance_purposes_dropdown()
    except Exception:
        other_clearances = []
    return render(request, 'secretary_module/addCertificate.html', {
        'fee_types': fee_types,
        'other_clearances': other_clearances,
    })

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def manageCert1(request):
    return render(request, 'secretary_module/manageCert1.html')

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def manageCert2(request):
    return render(request, 'secretary_module/manageCert2.html')

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def applications(request):
    """List all applications using get_all_application() with search + pagination."""
    q = (request.GET.get('q') or '').strip() or None
    # Support multi-select via repeated params ?application_status=Pending&application_status=For+Payment
    app_status_list = [s.strip() for s in request.GET.getlist('application_status') if s and s.strip()]
    req_label_list = [r.strip() for r in request.GET.getlist('request_label') if r and r.strip()]
    try:
        page = max(int(request.GET.get('page', 1)), 1)
    except Exception:
        page = 1
    try:
        per_page = max(min(int(request.GET.get('per_page', 25)), 100), 1)
    except Exception:
        per_page = 25
    offset = (page - 1) * per_page

    try:
        # If single selections (or none), use direct DB filtering for efficiency
        if len(app_status_list) <= 1 and len(req_label_list) <= 1:
            single_status = app_status_list[0] if app_status_list else None
            single_req    = req_label_list[0] if req_label_list else None
            rows = SecretaryHelpers.list_all_applications(q, single_status, single_req, per_page, offset)
            total = SecretaryHelpers.count_all_applications(q, single_status, single_req)
        else:
            # Multi-select: build cross-product of filters and merge results ordered by date_submitted desc
            # 1) Build combinations
            statuses = app_status_list or [None]
            requests = req_label_list or [None]
            combos = [(s, r) for s in statuses for r in requests]

            # 2) Count total exactly (sum; disjoint across status/request categories)
            total = 0
            per_combo_counts = {}
            for s, r in combos:
                c = SecretaryHelpers.count_all_applications(q, s, r)
                per_combo_counts[(s, r)] = c
                total += c

            # 3) Fetch top-K from each combo where K = min(count, page*per_page), then merge and slice
            end_idx = page * per_page
            merged = {}
            for s, r in combos:
                take = min(per_combo_counts[(s, r)], end_idx)
                if take <= 0:
                    continue
                subset = SecretaryHelpers.list_all_applications(q, s, r, take, 0)
                for row in subset:
                    merged[row['application_id']] = row

            # 4) Global sort by (date_submitted desc, application_id desc)
            merged_rows = list(merged.values())
            try:
                merged_rows.sort(key=lambda x: (x.get('date_submitted'), x.get('application_id')), reverse=True)
            except Exception:
                # Fallback if date types vary
                merged_rows.sort(key=lambda x: str(x.get('date_submitted')) + '-' + str(x.get('application_id')), reverse=True)

            start_idx = (page - 1) * per_page
            rows = merged_rows[start_idx:end_idx]
    except Exception as e:
        messages.error(request, f"Failed to load applications: {_clean_db_error(e)}")
        rows, total = [], 0

    total_pages = max(ceil((total or 0) / per_page), 1)
    # Build pagination URLs that preserve filters (doseq=True)
    def _qs(base_dict: dict, statuses: list[str], reqs: list[str]) -> str:
        params = []
        for k, v in base_dict.items():
            if v is not None and v != "":
                params.append((k, v))
        for s in statuses:
            params.append(('application_status', s))
        for r in reqs:
            params.append(('request_label', r))
        return urlencode(params, doseq=True)

    prev_url = next_url = ''
    if page > 1:
        prev_url = '?' + _qs({'q': q or '', 'page': page - 1, 'per_page': per_page}, app_status_list, req_label_list)
    if page < total_pages:
        next_url = '?' + _qs({'q': q or '', 'page': page + 1, 'per_page': per_page}, app_status_list, req_label_list)

    # Use Django's Paginator solely to get elided page range; rows are already sliced
    paginator = Paginator(range(total), per_page)  # dummy sequence just for pagination metadata
    # Clamp page within bounds (Paginator.get_page handles invalid values)
    page_obj = paginator.get_page(page)
    # Replace page with possibly adjusted number (e.g., too high -> last page)
    page = page_obj.number
    total_pages = paginator.num_pages
    # Elided page range (provides automatic ellipses)
    page_numbers = list(paginator.get_elided_page_range(number=page, on_each_side=1, on_ends=1))
    page_urls = {}
    for pn in page_numbers:
        if isinstance(pn, int):
            page_urls[pn] = '?' + _qs({'q': q or '', 'page': pn, 'per_page': per_page}, app_status_list, req_label_list)
    # Build template-friendly items to avoid dict indexing in templates
    page_items = []
    for item in page_numbers:
        if isinstance(item, int):
            page_items.append({'num': item, 'url': page_urls.get(item, ''), 'current': (item == page)})
        else:
            page_items.append({'ellipsis': True})
    # Update prev/next flags after clamping
    has_prev = page_obj.has_previous()
    has_next = page_obj.has_next()
    prev_url = '?' + _qs({'q': q or '', 'page': page - 1, 'per_page': per_page}, app_status_list, req_label_list) if has_prev else ''
    next_url = '?' + _qs({'q': q or '', 'page': page + 1, 'per_page': per_page}, app_status_list, req_label_list) if has_next else ''

    # Build chip removal links
    def _remove_one(kind: str, val: str) -> str:
        s_list = list(app_status_list)
        r_list = list(req_label_list)
        if kind == 'status' and val in s_list:
            s_list.remove(val)
        if kind == 'request' and val in r_list:
            r_list.remove(val)
        return '?' + _qs({'q': q or '', 'page': 1, 'per_page': per_page}, s_list, r_list)

    status_chips = [{'label': s, 'url': _remove_one('status', s)} for s in app_status_list]
    request_chips = [{'label': r, 'url': _remove_one('request', r)} for r in req_label_list]

    ctx = {
        'rows': rows,
        'q': q or '',
        'application_status': app_status_list[0] if len(app_status_list) == 1 else '',
        'request_label': req_label_list[0] if len(req_label_list) == 1 else '',
        'application_status_list': app_status_list,
        'request_label_list': req_label_list,
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages,
        'has_prev': has_prev,
        'has_next': has_next,
        'prev_page': page - 1,
        'next_page': page + 1,
        'prev_url': prev_url,
        'next_url': next_url,
        'page_numbers': page_numbers,
    'page_urls': page_urls,
    'page_items': page_items,
        # provide option lists for filter UI
        'application_status_options': ['Pending','For Payment','Approved','Completed','Rejected','Cancelled'],
        'request_label_options': ['Business Clearance','Business Closure','Business Clearance (Reprint)','Barangay Clearance'],
        'status_chips': status_chips,
        'request_chips': request_chips,
        'clear_all_url': '?' + _qs({'q': q or '', 'page': 1, 'per_page': per_page}, [], []),
    }
    return render(request, 'secretary_module/applications.html', ctx)

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def application_detail(request, application_id: int):
    """Server-rendered detail page for a specific application."""
    try:
        row = SecretaryHelpers.get_specific_application(application_id)
        if not row:
            raise Http404('Application not found')
    except Http404:
        raise
    except Exception as e:
        messages.error(request, _clean_db_error(e))
        return redirect('secretary_module:applications')

    # Normalize breakdown and numeric formatting
    import json
    details_json = row.get('total_amount_details')
    if isinstance(details_json, str):
        try:
            details_json = json.loads(details_json)
        except Exception:
            details_json = None

    # normalize to a list of structured items and a total
    breakdown_items = []
    breakdown_total = None
    purpose_value = None

    def to_float(x):
        try:
            from decimal import Decimal as D
            return float(x) if isinstance(x, (int, float, D)) else x
        except Exception:
            return x

    if isinstance(details_json, dict):
        items = details_json.get('items')
        breakdown_total = to_float(details_json.get('total'))
        # Extract purpose if provided in details JSON (e.g., { items:[], total:..., purpose:"..." })
        try:
            purpose_value = details_json.get('purpose') or purpose_value
        except Exception:
            purpose_value = purpose_value
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict):
                    breakdown_items.append({
                        'label': it.get('item') or it.get('label') or it.get('name') or 'Item',
                        'amount': to_float(it.get('amount') or it.get('total') or it.get('price') or 0),
                        'qty': it.get('qty'),
                        'rate': to_float(it.get('rate')) if it.get('rate') is not None else None,
                        'rate_percent': to_float(it.get('rate_percent')) if it.get('rate_percent') is not None else None,
                        'extra_units': it.get('extra_units'),
                        'total_units': it.get('total_units'),
                        'minimum_units': it.get('minimum_units'),
                    })
        else:
            # dict but no 'items' array; try to flatten key-values
            for k, v in details_json.items():
                if k == 'total':
                    continue
                if isinstance(v, (int, float)):
                    breakdown_items.append({'label': k, 'amount': to_float(v)})
                elif isinstance(v, dict) and 'amount' in v:
                    breakdown_items.append({'label': k, 'amount': to_float(v.get('amount'))})
    elif isinstance(details_json, list):
        for it in details_json:
            if isinstance(it, dict):
                breakdown_items.append({
                    'label': it.get('item') or it.get('label') or it.get('name') or 'Item',
                    'amount': to_float(it.get('amount') or it.get('total') or it.get('price') or 0),
                    'qty': it.get('qty'),
                    'rate': to_float(it.get('rate')) if it.get('rate') is not None else None,
                    'rate_percent': to_float(it.get('rate_percent')) if it.get('rate_percent') is not None else None,
                    'extra_units': it.get('extra_units'),
                    'total_units': it.get('total_units'),
                    'minimum_units': it.get('minimum_units'),
                })

    # If purpose was embedded in the JSON and row has no explicit purpose, surface it
    try:
        if purpose_value and not row.get('purpose'):
            row['purpose'] = purpose_value
    except Exception:
        pass

    ctx = {
        'row': row,
        'application_id': application_id,
        'breakdown': breakdown_items,
        'breakdown_total': breakdown_total,
    }
    # Provide personnel_id for forms that may need to submit it (e.g., cancellation)
    try:
        ctx['personnel_id'] = int(request.session.get('personnel_id') or 0) or _acting_personnel_id(request)
    except Exception:
        ctx['personnel_id'] = _acting_personnel_id(request)
    return render(request, 'secretary_module/application_detail.html', ctx)

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_POST
def set_application_to_completed(request, application_id: int):
    """Mark an Approved application as Completed (finalized/printed)."""
    try:
        SecretaryHelpers.set_application_to_completed(application_id)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'message': 'Application marked as Completed.'})
        set_flash(request, 'Application marked as Completed.', 'success')
        return redirect('secretary_module:application_detail', application_id=application_id)
    except Exception as e:
        msg = _clean_db_error(e)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'message': msg}, status=400)
        set_flash(request, msg, 'error')
        return redirect('secretary_module:application_detail', application_id=application_id)

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def application_detail_json(request, application_id: int):
    """Return JSON for a specific application using get_specific_application()."""
    try:
        row = SecretaryHelpers.get_specific_application(application_id)
        if not row:
            raise Http404('Application not found')

        # Serialize decimals and datetimes
        from datetime import date, datetime
        from decimal import Decimal as D
        def ser(v):
            if isinstance(v, D): return float(v)
            if isinstance(v, (date, datetime)): return v.isoformat()
            return v
        row = {k: ser(v) for k, v in row.items()}
        return JsonResponse(row)
    except Http404:
        raise
    except Exception as e:
        return JsonResponse({'ok': False, 'message': _clean_db_error(e)}, status=400)

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_POST
def set_application_to_for_payment(request, application_id: int):
    """Move a Pending application to For Payment using set_application_to_for_payment()."""
    try:
        SecretaryHelpers.set_application_to_for_payment(application_id)
        # AJAX vs normal POST
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'message': 'Moved to For Payment'})
        set_flash(request, 'Application moved to For Payment.', 'success')
        return redirect('secretary_module:applications')
    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'message': _clean_db_error(e)}, status=400)
        set_flash(request, _clean_db_error(e), 'error')
        return redirect('secretary_module:applications')

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def announcement(request):
    return render(request, 'secretary_module/announcement.html')

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def get_doc_url(request):

    file_path = request.GET.get("file_path")
    if not file_path:
        return HttpResponseBadRequest("Missing file_path")

    try:
        url = url_for_doc(file_path)
        if not url:
            return HttpResponseBadRequest("Could not generate URL")
        return JsonResponse({"url": url})
    except Exception as e:
        return HttpResponseBadRequest(str(e))

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def approval_decide(request):
    
    rid = int(request.POST.get("rid"))
    doc_type_id = int(request.POST.get("doctype_id"))
    action = request.POST.get("action")      
    review_notes = request.POST.get("rejection_notes", "")
    pid = int(request.session.get("personnel_id"))
    review_action = request.POST.get("review_action", "")          

    if action not in ("approve", "reject"):
        set_flash(request, "Invalid request.", "error")
        return redirect("secretary_module:approval")

    try:
        result = Secretary.sp_review_resident_supporting_certificate(
            rid=rid,
            doc_type_id=doc_type_id,
            review_status=action,
            pid=pid,
            review_notes=review_notes,
            review_action=review_action
        )
        msg = coerce_message(result)
        set_flash(request, msg, "success")
    except Exception as e:
        set_flash(request, str(e), "error")

    return redirect("secretary_module:approval")

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def approval(request):
    flash = get_flash(request) 
    
    limit = None
    offset = None
    sort_by = ''
    sort_dir = ''
    results = []
    
    query = (request.GET.get('query') or '').strip()
    
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
        
    sort_by  = request.GET.get("sort_by")
    sort_dir = request.GET.get("sort_dir", "desc").lower()
    if sort_by not in VALID_SORT_BY:
        sort_by = ""
    if sort_dir not in VALID_SORT_DIR:
        sort_dir = "desc"
        
    offset = (page - 1) * limit
    
    try:
        results = Secretary.sp_get_pending_supporting_certificates(
            query=query,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_dir=sort_dir
        )
    except Exception as e:
        msg = _clean_db_error(e)
        set_flash(request, msg, "error")
    
    has_next = len(results) > limit
    has_prev = page > 1
    final_result = results[:limit]

    
    base_params = _clean_params({
        "limit": limit,
        "sort_by": sort_by,
        "sort_dir": sort_dir,
        "query": query,    
    })

    prev_url = "?" + urlencode({**base_params, "page": page - 1}) if has_prev else ""
    next_url = "?" + urlencode({**base_params, "page": page + 1}) if has_next else ""
    
        # limit pills reset page to 1
    limit_urls = {n: "?" + urlencode({**base_params, "limit": n, "page": 1}) for n in LIMIT_OPTIONS}

    return render(request, 'secretary_module/approval.html', {
        "results": final_result,
        "limit": limit,
        "page": page,
        "sort_by": sort_by,
        "sort_dir": sort_dir,
        "has_prev": has_prev,
        "has_next": has_next,
        "prev_url": prev_url,
        "next_url": next_url,
        "limit_options": LIMIT_OPTIONS,
        "limit_urls": limit_urls,
        'query': query,
        'message': flash['message'],
        'message_level': flash['message_level'],
        'session_personnel_id': request.session.get('personnel_id'),
    })

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def businessFee(request):
    try:
        categories = BusinessFee.sp_get_all_business_clearance_cat()
    except Exception as e:
        messages.error(request, f"Could not load fee categories: {e}")
        categories = []
    return render(request, 'secretary_module/businessFee.html', {"categories": categories})

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def business_fee_update(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Method not allowed"}, status=405)

    def to_decimal(val):
        if val in (None, "", "null", "None"):
            return None
        try:
            return Decimal(val)
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError("Invalid decimal value")

    def to_int(val):
        if val in (None, "", "null", "None"):
            return None
        return int(val)

    try:
        cid = int(request.POST.get("clearance_category_id"))
        base_fee = to_decimal(request.POST.get("base_fee"))
        addl = to_decimal(request.POST.get("additional_fee_per_unit"))
        min_units = to_int(request.POST.get("minimum_units"))

        # ✅ pull personnel_id from session (consistent with other views)
        try:
            updated_by = int(request.session.get("personnel_id") or 0)
        except (TypeError, ValueError):
            updated_by = 0
        if not updated_by:
            return JsonResponse({"ok": False, "error": "No personnel ID in session."}, status=400)

        message = BusinessFee.sp_update_business_clearance_category(
            cid, base_fee, addl, min_units, updated_by
        )

        row = BusinessFee.sp_get_specific_business_clearance_cat(cid)

        from datetime import date, datetime
        from decimal import Decimal as D
        def ser(v):
            if isinstance(v, D): return float(v)
            if isinstance(v, (date, datetime)): return v.isoformat()
            return v

        row = {k: ser(v) for k, v in (row or {}).items()}
        return JsonResponse({"ok": True, "message": message, "row": row})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)


# --- List page
@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def amusement(request):
    try:
        devices = AmusementDeviceType.sp_get_all_amusement_device_type()
    except Exception as e:
        messages.error(request, f"Could not load amusement device types: {e}")
        devices = []
    return render(request, 'secretary_module/amusement.html', {"devices": devices})

# --- Update endpoint (Fee per unit)
@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def amusement_update(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Method not allowed"}, status=405)

    def to_decimal(val):
        if val in (None, "", "null", "None"):
            return None
        from decimal import Decimal, InvalidOperation
        try:
            return Decimal(val)
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError("Invalid decimal value")

    try:
        raw_id = request.POST.get("device_type_id")
        try:
            device_type_id = int(raw_id)
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "error": "Invalid or missing device_type_id."}, status=400)

        fee_per_unit = to_decimal(request.POST.get("fee_per_unit"))

        # who’s updating?
        updated_by = (lambda s: int(s) if s and str(s).isdigit() else None)(request.session.get("personnel_id"))
        if not updated_by:
            return JsonResponse({"ok": False, "error": "No personnel ID in session."}, status=400)

        message = AmusementDeviceType.sp_update_amusement_device_type(
            device_type_id, fee_per_unit, updated_by
        )

        row = AmusementDeviceType.sp_get_specific_amusement_device_type(device_type_id)

        from datetime import date, datetime
        from decimal import Decimal as D
        def ser(v):
            if isinstance(v, D): return float(v)
            if isinstance(v, (date, datetime)): return v.isoformat()
            return v
        row = {k: ser(v) for k, v in (row or {}).items()}

        return JsonResponse({"ok": True, "message": message, "row": row})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
    
@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def other_clearances(request):
    try:
        rows = OtherClearanceType.sp_get_all_other_barangay_clearance_type()
    except Exception as e:
        messages.error(request, f"Could not load other clearances: {e}")
        rows = []
    return render(request, "secretary_module/otherClearances.html", {"rows": rows})

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def other_clearances_update(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Method not allowed"}, status=405)

    def to_decimal(val):
        if val in (None, "", "null", "None"):
            return None
        try:
            return Decimal(val)
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError("Invalid decimal value")

    try:
        raw_id = request.POST.get("clearance_type_id")
        try:
            clearance_type_id = int(raw_id)
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "error": "Invalid or missing clearance_type_id."}, status=400)

        fee = to_decimal(request.POST.get("fee"))

        updated_by = _get_personnel_id(request)
        if not updated_by:
            return JsonResponse({"ok": False, "error": "No personnel ID in session."}, status=400)

        message = OtherClearanceType.sp_update_other_barangay_clearance_type(
            clearance_type_id, fee, updated_by
        )

        # fresh row
        row = OtherClearanceType.sp_get_specific_other_barangay_clearance_type(clearance_type_id)

        # serialize Decimals/Datetimes
        from datetime import date, datetime
        from decimal import Decimal as D
        def ser(v):
            if isinstance(v, D): return float(v)
            if isinstance(v, (date, datetime)): return v.isoformat()
            return v
        row = {k: ser(v) for k, v in (row or {}).items()}

        return JsonResponse({"ok": True, "message": message, "row": row})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
    
def _get_personnel_id(request):
    try:
        pid = int(request.session.get("personnel_id") or 0)
        return pid if pid > 0 else None
    except (TypeError, ValueError):
        return None
    

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def tax_penalties(request):
    try:
        cfg = BusinessTaxConfig.sp_get_current_business_tax_config() or {}
    except Exception as e:
        messages.error(request, f"Could not load tax configuration: {e}")
        cfg = {}
    months = list(range(1, 13))
    return render(request, "secretary_module/taxPenalties.html", {"cfg": cfg, "months": months})

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def tax_penalties_update(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Method not allowed"}, status=405)

    def dec_or_none(v):
        if v in (None, "", "null", "None"):
            return None
        from decimal import Decimal, InvalidOperation
        try:
            return Decimal(str(v))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError("Invalid number.")

    def int_or_none(v):
        if v in (None, "", "null", "None"):
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            raise ValueError("Invalid integer.")

    try:
        # inputs (blank -> None so SQL treats them as "no change")
        th   = dec_or_none(request.POST.get("threshold_amount"))
        at   = dec_or_none(request.POST.get("rate_percent_at_or_below"))
        abv  = dec_or_none(request.POST.get("rate_percent_above"))
        winS = int_or_none(request.POST.get("window_month_start"))
        winE = int_or_none(request.POST.get("window_month_end"))
        mir  = dec_or_none(request.POST.get("monthly_interest_percent"))

        # who is updating?
        pid = request.session.get("personnel_id")
        try:
            pid = int(pid) if pid else None
        except (TypeError, ValueError):
            pid = None
        if not pid:
            return JsonResponse({"ok": False, "error": "No personnel ID in session."}, status=400)

        # get config_id (from current row or hidden input)
        cfg = BusinessTaxConfig.sp_get_current_business_tax_config() or {}
        config_id = cfg.get("config_id") or request.POST.get("config_id")
        try:
            config_id = int(config_id)
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "error": "No config to update. Seed a row first."}, status=400)

        # call SP: (config_id FIRST)
        message = BusinessTaxConfig.sp_update_business_tax_config(
            config_id,
            th, at, abv, winS, winE, mir, pid
        )

        # return fresh row
        row = BusinessTaxConfig.sp_get_current_business_tax_config() or {}
        from datetime import date, datetime
        from decimal import Decimal as D
        def ser(v):
            if isinstance(v, D): return float(v)
            if isinstance(v, (date, datetime)): return v.isoformat()
            return v
        row = {k: ser(v) for k, v in row.items()}
        return JsonResponse({"ok": True, "message": message, "row": row})

    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
    

def _acting_personnel_id(request) -> int:
    return (
        getattr(getattr(request, 'user', None), 'personnel_id', None)
        or request.session.get('personnel_id')
        or 1
    )

def _public_url(request, path: str | None):
    """
    Normalize DB-stored image paths so the template always gets a usable URL.
    - absolute http(s): return as-is
    - root-relative (starts with /): build absolute (so it works in emails or iframes)
    - plain relative like 'announcements/x.jpg': prefix MEDIA_URL and build absolute
    """
    if not path:
        return None
    if path.startswith('http://') or path.startswith('https://'):
        return path
    if path.startswith('/'):
        return request.build_absolute_uri(path)
    base = settings.MEDIA_URL or '/media/'
    if not base.endswith('/'):
        base += '/'
    return request.build_absolute_uri(base + path.lstrip('/'))

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def announcement(request):
    ctx = {'errors': []}
    personnel_id = _acting_personnel_id(request)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action in ('create', 'update'):
            header_title = (request.POST.get('header_title') or '').strip()
            details = (request.POST.get('details') or '').strip()
            event_date_str = (request.POST.get('announcement_at_date') or '').strip()
            raw_audience = (request.POST.get('audience') or 'EVERYONE').strip()
            audience = _UI_TO_SQL_AUDIENCE.get(raw_audience)

            event_date = None
            if event_date_str:
                try:
                    event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
                except ValueError:
                    ctx['errors'].append('Invalid Event Date.')

            if audience is None:
                ctx['errors'].append('Invalid audience selection.')
            if not header_title:
                ctx['errors'].append('Title is required.')
            if not details:
                ctx['errors'].append('Content is required.')

            # optional image upload
            image_db_path = None
            f = request.FILES.get('image')
            if f:
                saved = default_storage.save(f"announcements/{f.name}", f)  # store relative path
                image_db_path = saved

            try:
                if action == 'create' and not ctx['errors']:
                    new_id = AnnouncementRepo.create(
                        header_title=header_title,
                        details=details,
                        image_path=image_db_path,
                        created_by=personnel_id,
                        event_date=event_date,
                        audience=audience
                    )
                    return redirect(f"{request.path}?id={new_id}")

                elif action == 'update' and not ctx['errors']:
                    upd_id = request.POST.get('announcement_id')
                    if not upd_id:
                        ctx['errors'].append('Missing announcement id.')
                    else:
                        AnnouncementRepo.update(
                            announcement_id=int(upd_id),
                            updated_by=personnel_id,
                            header_title=header_title,
                            details=details,
                            image_path=image_db_path,
                            event_date=event_date,
                            audience=audience
                        )
                        return redirect(f"{request.path}?id={upd_id}")

            except Exception as e:
                ctx['errors'].append(str(e))
                # fall through to re-render with errors

            ctx['post_data'] = {
                'header_title': header_title,
                'details': details,
                'announcement_at_date': event_date_str,
                'audience': raw_audience,
            }

        elif action == 'delete':
            try:
                del_id = int(request.POST.get('announcement_id'))
                AnnouncementRepo.delete(del_id, personnel_id)
                return redirect(request.path)  # no id -> will show latest or empty
            except Exception as e:
                ctx['errors'].append(str(e))

    # GET: list + selected
    selected_id = request.GET.get('id')
    # (optional) list filter: ?audience=resident|personnel|both
    list_audience = request.GET.get('audience')
    announcements = AnnouncementRepo.list_all(sort='date_desc', limit=100, audience=list_audience)

    selected = None
    if selected_id:
        selected = AnnouncementRepo.get_one(int(selected_id))
    elif announcements:
        selected = AnnouncementRepo.get_one(int(announcements[0]['announcement_id']))

    # normalize image URL for the selected item (keeps your existing behavior)
    if selected and 'announcement_image_path' in selected:
        selected['image_url'] = _public_url(request, selected.get('announcement_image_path'))

    # normalize audience to what your template expects (EVERYONE | PERSONNEL | RESIDENTS)
    if selected and selected.get('audience'):
        selected['audience'] = _SQL_TO_UI_AUDIENCE.get(selected['audience'], 'EVERYONE')

    # compatibility aliases if your SQL returns created_date instead of date / announcement_date
    if selected and 'created_date' in selected and 'date' not in selected:
        selected['date'] = selected['created_date']
    for a in announcements:
        if 'created_date' in a and 'announcement_date' not in a:
            a['announcement_date'] = a['created_date']

    ctx.update({'announcements': announcements, 'selected': selected})
    return render(request, 'secretary_module/announcement.html', ctx)


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_POST
def cancel_application(request, application_id: int):
    """Cancel an application when allowed (Pending or For Payment).

    Accepts optional 'reason' field. Returns JSON for AJAX, or flashes and redirects otherwise.
    Server-side guard is primarily in SQL; we surface the DB message back to the client.
    """
    reason = (request.POST.get('reason') or '').strip() or None
    try:
        # Prefer posted personnel_id if provided; otherwise fall back to session/user
        posted_pid = request.POST.get('personnel_id')
        try:
            personnel_id = int(posted_pid) if posted_pid is not None else None
        except (TypeError, ValueError):
            personnel_id = None
        if not personnel_id:
            personnel_id = _acting_personnel_id(request)
        if not personnel_id:
            raise ValueError('Missing personnel_id for cancellation.')

        message = SecretaryHelpers.secretary_cancel_application(application_id, personnel_id, reason)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'message': message})
        set_flash(request, message or 'Application cancelled.', 'success')
        return redirect('secretary_module:application_detail', application_id=application_id)
    except Exception as e:
        msg = _clean_db_error(e)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'message': msg}, status=400)
        set_flash(request, msg, 'error')
        return redirect('secretary_module:application_detail', application_id=application_id)


# ---- Added at end: dynamic data endpoints used by the addCertificate UI
@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def add_certificate(request):
    """
    Render the create-application page. On GET, load fee types and other clearance purposes
    from the DB helper functions so the template can render dynamic dropdowns.
    """
    # Use SecretaryHelpers to load dropdowns (keeps DB logic in models and
    # uses the new helper container as requested).
    try:
        fee_types = SecretaryHelpers.get_fee_types_dropdown()
    except Exception:
        fee_types = []

    try:
        other_clearances = SecretaryHelpers.get_other_clearance_purposes_dropdown()
    except Exception:
        other_clearances = []

    # Preserve earlier simple render behavior for POST (creation handled elsewhere)
    if request.method == 'POST':
        # For now, let the form post to the same URL and be handled by existing flow (or future implementation)
        return render(request, 'secretary_module/addCertificate.html', {'fee_types': fee_types, 'other_clearances': other_clearances})

    return render(request, 'secretary_module/addCertificate.html', {'fee_types': fee_types, 'other_clearances': other_clearances})


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_POST
def submit_business_application(request):
    """Create an application for either Business or Barangay Clearances.
    Branch based on the fee_type_name.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest('POST required')

    fee_type_id_raw = request.POST.get('fee_type_id')
    try:
        fee_type_id = int(fee_type_id_raw)
    except (TypeError, ValueError):
        messages.error(request, 'Invalid fee type.')
        return redirect('secretary_module:create_application')

    # Look up fee type name to determine flow
    with connection.cursor() as cur:
        cur.execute('SELECT fee_type_name FROM Fee_Type WHERE fee_type_id=%s LIMIT 1', [fee_type_id])
        row = cur.fetchone()
        fee_type_name = (row[0] if row else '')

    acting_pid = _acting_personnel_id(request)

    # Robust match: fee type labels may be "Barangay Clearance Fee" (renamed from "Barangay Clearances")
    normalized_fee = fee_type_name.lower()
    if 'barangay clearance' in normalized_fee:
        # Resident-based Barangay Clearance
        resident_id_raw = request.POST.get('applicant_id')
        purpose_id_raw = request.POST.get('purpose')  # holds other_clearance_id when barangay clearances
        try:
            resident_id = int(resident_id_raw)
            other_clearance_id = int(purpose_id_raw)
        except (TypeError, ValueError):
            messages.error(request, 'Please select a resident and a purpose.')
            return redirect('secretary_module:create_application')
        try:
            app_id = SecretaryHelpers.create_application_barangay_clearance(
                personnel_id=acting_pid,
                resident_id=resident_id,
                other_clearance_id=other_clearance_id,
            )
            if not app_id:
                messages.error(request, 'Application was not created.')
                return redirect('secretary_module:create_application')
            messages.success(request, f'Barangay clearance application #{app_id} created.')
            return redirect('secretary_module:applications')
        except Exception as e:
            messages.error(request, _clean_db_error(e))
            return redirect('secretary_module:create_application')
    else:
        # Business Clearance flow
        try:
            business_id = int(request.POST.get('business_id') or 0)
            cat_id = int(request.POST.get('business_clearance_category') or request.POST.get('category_id') or 0)
        except (TypeError, ValueError):
            messages.error(request, 'Invalid business/category selection.')
            return redirect('secretary_module:create_application')

        purpose = (request.POST.get('purpose') or '').strip() or None
        vq = _to_int_or_none(request.POST.get('videoke_qty'))
        bq = _to_int_or_none(request.POST.get('billiard_qty'))
        oq = _to_int_or_none(request.POST.get('other_device_qty'))

        try:
            app_id = SecretaryHelpers.create_application_business(
                fee_type_id=fee_type_id,
                business_id=business_id,
                business_clearance_category=cat_id,
                videoke_qty=vq,
                billiard_qty=bq,
                other_device_qty=oq,
                purpose=purpose,
                requested_by='personnel',
                requested_by_id=acting_pid,
            )
            if not app_id:
                messages.error(request, 'Application was not created.')
                return redirect('secretary_module:create_application')
            messages.success(request, f'Business clearance application #{app_id} created.')
            return redirect('secretary_module:applications')
        except Exception as e:
            messages.error(request, _clean_db_error(e))
            return redirect('secretary_module:create_application')


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def application_search(request):
    """AJAX search used by the walk-in UI.
    If fee_name contains 'Barangay Clearance' (supports legacy 'Barangay Clearances' and new 'Barangay Clearance Fee')
    -> search residents; else -> search business/owner.
    """
    q = (request.GET.get('q') or '').strip()
    fee_name = (request.GET.get('fee_name') or '').strip()
    limit = 25
    offset = 0
    if not q:
        return JsonResponse([], safe=False)
    try:
        normalized_fee = fee_name.lower()
        if 'barangay clearance' in normalized_fee:
            # Use the new resident search tailored for clearance picker
            rows = SecretaryHelpers.search_resident_for_clearance(q, limit, offset, None, None, None)
            payload = [{
                'resident_id': r.get('resident_id'),
                'resident_code': r.get('resident_code'),
                'full_name': r.get('full_name'),
                'dob': r.get('dob'),
                'complete_address': r.get('complete_address'),
            } for r in rows]
            return JsonResponse(payload, safe=False)
        else:
            rows = SecretaryHelpers.search_owner(q, limit, offset)
            return JsonResponse(rows, safe=False)
    except Exception as e:
        return JsonResponse({'error': coerce_message(e)}, status=400)


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_POST
def preview_business_clearance(request):
    """Call the DB function secretary_preview_business_clearance and return JSON result.
    Expects form params: business_id (int), purpose (text), videoke_qty, billiard_qty, other_device_qty
    """
    try:
        business_id = int(request.POST.get('business_id') or 0)
    except (TypeError, ValueError):
        # Include posted keys to aid debugging (no sensitive data expected here)
        return JsonResponse({
            'ok': False,
            'message': 'Invalid or missing business_id',
            'posted_keys': list(request.POST.keys())
        }, status=400)

    purpose = request.POST.get('purpose')
    try:
        videoke_qty = _to_int_or_none(request.POST.get('videoke_qty'))
        billiard_qty = _to_int_or_none(request.POST.get('billiard_qty'))
        other_device_qty = _to_int_or_none(request.POST.get('other_device_qty'))
    except Exception:
        videoke_qty = billiard_qty = other_device_qty = None

    try:
        # Use the helper container which delegates to the DB function
        preview = SecretaryHelpers.secretary_preview_business_clearance(
            business_id, purpose, videoke_qty, billiard_qty, other_device_qty
        )
        if not preview:
            return JsonResponse({'ok': False, 'message': 'No preview data returned'}, status=404)
        resp = {
            'ok': True,
            'business_id': preview.get('business_id'),
            'category_id': preview.get('category_id'),
            'business_status': preview.get('business_status'),
            'purpose': preview.get('purpose'),
            'total_amount': float(preview.get('total_amount')) if preview.get('total_amount') is not None else None,
            'total_amount_details': preview.get('total_amount_details'),
        }
        return JsonResponse(resp)
    except Exception as e:
        return JsonResponse({'ok': False, 'message': _clean_db_error(e)}, status=400)


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_POST
def create_reprint_business_clearance(request):
    """Create a REPRINT business clearance application.

    POST params:
      - business_id
    Returns JSON { ok: true, application_id } or { ok: false, message }
    """
    try:
        business_id = int(request.POST.get('business_id'))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'message': 'Invalid business_id'}, status=400)
    try:
        personnel_id = _acting_personnel_id(request)
        app_id = SecretaryHelpers.create_reprint_business_clearance(
            business_id=business_id,
            requested_by='personnel',
            requested_by_id=personnel_id,
        )
        if not app_id:
            return JsonResponse({'ok': False, 'message': 'No application id returned.'}, status=400)
        return JsonResponse({'ok': True, 'application_id': app_id})
    except Exception as e:
        # Return a specific, cleaned DB error instead of a vague default
        return JsonResponse({'ok': False, 'message': _clean_db_error(e)}, status=400)


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_POST
def create_renewal_business_clearance(request):
    """Create a RENEWAL business clearance application.

    POST params:
      - business_id
    Returns JSON { ok: true, application_id } or { ok: false, message }
    """
    try:
        business_id = int(request.POST.get('business_id'))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'message': 'Invalid business_id'}, status=400)

    try:
        personnel_id = _acting_personnel_id(request)
        app_id = SecretaryHelpers.create_renewal_business_clearance(
            business_id=business_id,
            requested_by='personnel',
            requested_by_id=personnel_id,
        )
        if not app_id:
            return JsonResponse({'ok': False, 'message': 'No application id returned.'}, status=400)
        return JsonResponse({'ok': True, 'application_id': app_id})
    except Exception as e:
        return JsonResponse({'ok': False, 'message': _clean_db_error(e)}, status=400)


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_POST
def create_registration_business_clearance(request):
    """Create a REGISTRATION business clearance application.

    POST params:
      - business_id
    Returns JSON { ok: true, application_id } or { ok: false, message }
    """
    try:
        business_id = int(request.POST.get('business_id'))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'message': 'Invalid business_id'}, status=400)

    try:
        personnel_id = _acting_personnel_id(request)
        app_id = SecretaryHelpers.create_registration_business_clearance(
            business_id=business_id,
            requested_by='personnel',
            requested_by_id=personnel_id,
        )
        if not app_id:
            return JsonResponse({'ok': False, 'message': 'No application id returned.'}, status=400)
        return JsonResponse({'ok': True, 'application_id': app_id})
    except Exception as e:
        return JsonResponse({'ok': False, 'message': _clean_db_error(e)}, status=400)


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def print_application(request, application_id: int):
    """Deprecated HTML print: redirect to the PDF generator instead."""
    return redirect('secretary_module:print_application_pdf', application_id=application_id)


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def print_application_pdf(request, application_id: int):
    """Generate a filled PDF for the given application.

    - Barangay Clearance uses static/prints/Template1_Clearance_LETTER.pdf and fills:
      full_name, full_address, purpose, day, month, year, or_number, fulldate_issue, fullname_captain
    - Business Clearance/Closure uses static/prints/Template2_Business_Clearance_LETTER.pdf and fills:
      business_name, owners_name, full_address, nature_of_business, day, month, year, paid, fulldate_issue, or_number, fullname_captain

    Falls back to applications list with an error message if anything fails.
    """
    # Step 1: Fetch and normalize context
    try:
        # Fetch core application first to enforce no PDF regeneration after completion
        app_row = SecretaryHelpers.get_specific_application(application_id) or {}
        app_status = (app_row.get('application_status') or '').strip().lower()
        if app_status == 'completed':
            messages.warning(request, 'Completed applications cannot be re-generated.')
            return redirect('secretary_module:application_detail', application_id=application_id)

        row = SecretaryHelpers.get_clearance_details_for_printing(application_id)
        if not row:
            raise Http404('Application not found or no printable details.')

        from datetime import date, datetime
        from decimal import Decimal as D

        def ser(v):
            if isinstance(v, D):
                return float(v)
            if isinstance(v, (date, datetime)):
                return v
            return v

        ctx = {k: ser(v) for k, v in row.items()}
        ctx.setdefault('application_id', application_id)
    except Http404:
        raise
    except Exception as e:
        messages.error(request, _clean_db_error(e))
        return redirect('secretary_module:applications')

    # Step 2: Choose template and fields based on request type, then fill AcroForm
    try:
        # Normalize date parts
        fulldate = ctx.get('fulldate_issue')
        day = ctx.get('day')
        month = ctx.get('month')
        year = ctx.get('year')
        try:
            if fulldate and (not day or not month or not year):
                day = day or f"{getattr(fulldate, 'day', '')}"
                try:
                    month = month or getattr(fulldate, 'strftime', lambda *_: '')('%B')
                except Exception:
                    month = month or ''
                year = year or f"{getattr(fulldate, 'year', '')}"
        except Exception:
            pass

        request_label = (ctx.get('request') or '').strip().lower()
        is_barangay = (request_label == 'barangay clearance')

        if is_barangay:
            # Barangay Clearance template selection (with Residency variant)
            purpose_label = (ctx.get('purpose') or '').strip().lower()
            is_residency = (purpose_label == 'certificate of residency' or 'residency' in purpose_label)

            if is_residency:
                # Certificate of Residency uses Template3_Residency_LETTER.pdf
                template_path = os.path.join(settings.BASE_DIR, 'static', 'prints', 'Template3_Residency_LETTER.pdf')
                if not os.path.exists(template_path):
                    messages.error(request, 'PDF generation error: Template3_Residency_LETTER.pdf not found.')
                    return redirect('secretary_module:applications')

                fields = {
                    'full_name':        ctx.get('full_name') or '',
                    'full_address':     ctx.get('full_address') or '',
                    'day':              str(day or ''),
                    'month':            str(month or ''),
                    'year':             str(year or ''),
                    'or_number':        str(ctx.get('or_number') or ''),
                    'fulldate_issue':   getattr(fulldate, 'strftime', lambda *_: '')('%B %d, %Y') if fulldate else (ctx.get('fulldate_issue') or ''),
                    'fullname_captain': ctx.get('fullname_captain') or '',
                }
                suggested_name = 'residency_certificate'
            else:
                # Default Barangay Clearance
                template_path = os.path.join(settings.BASE_DIR, 'static', 'prints', 'Template1_Clearance_LETTER.pdf')
                if not os.path.exists(template_path):
                    messages.error(request, 'PDF generation error: Template1_Clearance_LETTER.pdf not found.')
                    return redirect('secretary_module:applications')

                fields = {
                    'full_name':        ctx.get('full_name') or '',
                    'full_address':     ctx.get('full_address') or '',
                    'purpose':          ctx.get('purpose') or '',
                    'day':              str(day or ''),
                    'month':            str(month or ''),
                    'year':             str(year or ''),
                    'or_number':        str(ctx.get('or_number') or ''),
                    'fulldate_issue':   getattr(fulldate, 'strftime', lambda *_: '')('%B %d, %Y') if fulldate else (ctx.get('fulldate_issue') or ''),
                    'fullname_captain': ctx.get('fullname_captain') or '',
                }
                suggested_name = 'barangay_clearance'
        else:
            # Business Clearance/Closure template and field mapping
            template_path = os.path.join(settings.BASE_DIR, 'static', 'prints', 'Template2_Business_Clearance_LETTER.pdf')
            if not os.path.exists(template_path):
                messages.error(request, 'PDF generation error: Template2_Business_Clearance_LETTER.pdf not found.')
                return redirect('secretary_module:applications')

            paid_val = ctx.get('paid')
            try:
                if paid_val is not None:
                    paid_val = float(paid_val)
            except Exception:
                pass
            paid_str = (
                f"₱{paid_val:,.2f}" if isinstance(paid_val, (int, float)) else (str(paid_val) if paid_val is not None else '')
            )

            fields = {
                'business_name':      ctx.get('business_name') or '',
                'owners_name':        ctx.get('owners_name') or '',
                'full_address':       ctx.get('full_address') or '',
                'nature_of_business': ctx.get('nature_of_business') or '',
                'day':                str(day or ''),
                'month':              str(month or ''),
                'year':               str(year or ''),
                'paid':               paid_str,
                'fulldate_issue':     getattr(fulldate, 'strftime', lambda *_: '')('%B %d, %Y') if fulldate else (ctx.get('fulldate_issue') or ''),
                'or_number':          str(ctx.get('or_number') or ''),
                'fullname_captain':   ctx.get('fullname_captain') or '',
            }
            suggested_name = 'business_clearance'

        reader = PdfReader(template_path)
        writer = PdfWriter()
        writer.append_pages_from_reader(reader)

        # Copy AcroForm from the template (some viewers require this for field rendering)
        try:
            acro = reader.trailer[NameObject('/Root')].get(NameObject('/AcroForm'))
            if acro is not None:
                writer._root_object.update({NameObject('/AcroForm'): acro})
                # Set NeedAppearances on the AcroForm itself
                try:
                    writer._root_object[NameObject('/AcroForm')].get_object().update({
                        NameObject('/NeedAppearances'): BooleanObject(True)
                    })
                except Exception:
                    pass
        except Exception:
            # Fallback: set NeedAppearances on root (some renderers honor this)
            try:
                writer._root_object.update({
                    NameObject('/AcroForm'): writer._root_object.get(NameObject('/AcroForm'), {})
                })
                writer._root_object[NameObject('/AcroForm')].update({
                    NameObject('/NeedAppearances'): BooleanObject(True)
                })
            except Exception:
                pass

        # Update fields for each page (safe if fields appear on only one page)
        for page in writer.pages:
            try:
                writer.update_page_form_field_values(page, fields)
            except Exception:
                # continue filling other pages even if one update fails
                continue

        # Mark fields as ReadOnly (/Ff bit 1) so they aren't editable after filling
        try:
            acro_obj = writer._root_object.get(NameObject('/AcroForm'))
            if acro_obj is not None:
                fields_arr = acro_obj.get_object().get(NameObject('/Fields'))
                if fields_arr:
                    for f in fields_arr:
                        try:
                            f_obj = f.get_object()
                            curr = int(f_obj.get(NameObject('/Ff'), 0))
                            f_obj.update({NameObject('/Ff'): NumberObject(curr | 1)})
                        except Exception:
                            pass
        except Exception:
            # non-fatal
            pass

        # If nothing got filled (all values empty), attempt to hint field names in DEBUG
        try:
            if settings.DEBUG:
                avail = {}
                try:
                    # pypdf provides get_form_text_fields on the reader
                    avail = getattr(reader, 'get_form_text_fields', lambda: {})() or {}
                except Exception:
                    avail = {}
                # If we didn't match any field name, surface a message once
                if avail and not any(k in avail for k in fields.keys()):
                    messages.warning(request, f"PDF form fields not matched. Available: {', '.join(sorted(avail.keys()))}")
        except Exception:
            pass

        # Attempt to apply document permissions: allow printing/accessibility; disallow edits/form filling
        try:
            try:
                # pypdf >= 4 style
                from pypdf import Permissions as _Perms
                allow_perms = {_Perms.PRINT, _Perms.ACCESSIBILITY}
                writer.encrypt(user_password="", permissions=allow_perms)
            except Exception:
                # Older pypdf fallback: best-effort basic encryption with empty password
                try:
                    writer.encrypt("")
                except Exception:
                    pass
        except Exception:
            pass

        # Stream to HTTP response
        pdf_bytes = io.BytesIO()
        writer.write(pdf_bytes)
        pdf_bytes.seek(0)

        # suggested_name determined above per branch (defaults handled for safety)
        suggested_name = locals().get('suggested_name') or ('barangay_clearance' if is_barangay else 'business_clearance')
        response = HttpResponse(pdf_bytes.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{suggested_name}_{application_id}.pdf"'
        return response
    except Exception as e:
        messages.error(request, f'PDF generation error: {coerce_message(e)}')
        return redirect('secretary_module:applications')

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_POST
def preview_barangay_clearance(request):
    """Preview fee breakdown for a Barangay Clearance resident application."""
    try:
        resident_id = int(request.POST.get('resident_id'))
        other_clearance_id = int(request.POST.get('other_clearance_id'))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'message': 'Invalid resident or purpose selection.'}, status=400)
    try:
        data = SecretaryHelpers.secretary_preview_barangay_clearance(resident_id, other_clearance_id)
        if not data:
            return JsonResponse({'ok': False, 'message': 'No preview data returned.'}, status=404)
        return JsonResponse({
            'ok': True,
            'applicant_id': data.get('applicant_id'),
            'applicant_full_name': data.get('applicant_full_name'),
            'purpose': data.get('purpose'),
            'total_amount': data.get('total_amount'),
            'total_amount_details': data.get('total_amount_details'),
            'has_open_application': data.get('has_open_application'),
            'open_application_id': data.get('open_application_id'),
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'message': coerce_message(e)}, status=400)

    