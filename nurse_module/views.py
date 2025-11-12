from django.shortcuts import render, redirect
from authentication.decorators import custom_login_required, role_required
from django.contrib import messages
from django.db import connection
from .models import Dashboard, AnnouncementRepo, ResidentList
from datetime import datetime
from django.shortcuts import render
from django.utils.http import urlencode
from django.views.decorators.http import require_GET
from utils.constants import LIMIT_OPTIONS
from utils.flash import set_flash, get_flash
from utils.db_message import _clean_db_error, _clean_params, coerce_message
from household_module.models import Household, Family
from django.http import JsonResponse
import json


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

PAGE_SIZE = 20
MAX_PAGE_SIZE = 200


@custom_login_required
@role_required('Midwife')
def nurse_dashboard(request):
    # ---- KPIs ----
    try:
        totals = Dashboard.sp_dashboard_totals(barangay=None, city=None)
    except Exception as e:
        messages.error(request, f"Failed loading totals: {e}")
        totals = {
            "total_resident": 0, "total_non_resident": 0, "total_pending": 0,
            "total_male": 0, "total_female": 0
        }

    # ---- Bar (per sitio) ----
    try:
        per_sitio_rows   = Dashboard.sp_residents_per_sitio_json()
        per_sitio_labels = [str(r.get("sitio_name", "Unknown")) for r in per_sitio_rows]
        per_sitio_data   = [int(r.get("resident_count") or 0)   for r in per_sitio_rows]
    except Exception as e:
        messages.error(request, f"Failed loading per-sitio data: {e}")
        per_sitio_labels, per_sitio_data = [], []

    # ---- Pie (age) ----
    try:
        age_rows = Dashboard.sp_age_bracket_distribution()
        cleaned = []
        for item in age_rows or []:
            cleaned.append(item.get("jsonb_build_object", item))
        age_labels = [str(r.get("bracket", "Unknown")) for r in cleaned]
        age_data   = [int(r.get("count") or 0) for r in cleaned]
        total = sum(age_data) or 1
        age_labels_pct = [f"{lbl} ({round((cnt/total)*100)}%)" for lbl, cnt in zip(age_labels, age_data)]
    except Exception as e:
        messages.error(request, f"Failed loading age distribution: {e}")
        age_labels, age_data, age_labels_pct = [], [], []

    # === Recent announcements (use list_all so we surely have 'audience') ===
    try:
        raw_latest = AnnouncementRepo.list_all(sort='date_desc', limit=20, audience=None)
        latest_announcements = []
        for a in raw_latest:
            aud = ((a.get("audience") or a.get("p_audience") or "both").strip().lower())
            a["audience"] = aud
            a["announcement_date"] = a.get("announcement_date") or a.get("created_date")
            if aud in ("personnel", "both"):     # BHW sees Personnel + Everyone
                latest_announcements.append(a)
            if len(latest_announcements) >= 3:
                break
    except Exception as e:
        messages.error(request, f"Failed loading recent announcements: {e}")
        latest_announcements = []

    # ---- Modal filters ----
    ann_q        = (request.GET.get('ann_q') or '').strip() or None
    ann_aud      = (request.GET.get('ann_audience') or '').strip() or None
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

    # ---- Full list for modal (restricted to personnel scope) ----
    try:
        rows = AnnouncementRepo.list_all(
            q=ann_q, date_from=ann_from, date_to=ann_to,
            created_by=None, sort='date_desc', limit=200, offset=0,
            audience=ann_aud or None
        )
        announcements_all = []
        for a in rows:
            aud = ((a.get("audience") or a.get("p_audience") or "both").strip().lower())
            a["audience"] = aud
            a["announcement_date"] = a.get("announcement_date") or a.get("created_date")
            if aud in ("personnel", "both"):   # enforce BHW scope
                announcements_all.append(a)
    except Exception as e:
        messages.error(request, f"Failed loading announcements list: {e}")
        announcements_all = []

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
            "audience": ann_aud or "",
            "from": ann_from_str,
            "to": ann_to_str,
        },
        "ann_open": request.GET.get('ann_open') == '1',
    }
    return render(request, "nurse_module/nurse_dashboard.html", ctx)


@custom_login_required
@role_required('Midwife')
def nurse_resident_list(request):
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
    return render(request, "nurse_module/nurse_residentList.html", context)

@custom_login_required
@role_required('Midwife')
def nurse_household(request):
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
    return render(request, 'nurse_module/nurse_household.html',{
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
@role_required('Midwife')
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
@role_required('Midwife')
def nurse_householdView(request):
    
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
    return render(request, 'nurse_module/householdMore.html', {
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
def maternalrecord(request):
    return render(request, 'nurse_module/maternalrecord.html')

@custom_login_required
@role_required('Midwife')
def Morematernalrecord(request):
    return render(request, 'nurse_module/Morematernalrecord.html')

@custom_login_required
@role_required('Midwife')
def maternalLabScreening(request):
    return render(request, 'nurse_module/maternalLabScreening.html')

@custom_login_required
@role_required('Midwife')
def maternalIron(request):
    return render(request, 'nurse_module/maternalIron.html')

@custom_login_required
@role_required('Midwife')
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
@role_required('Midwife')
def nurseGeneralInfo(request):
    limit = None
    offset = None
    results = []
    
    query = (request.GET.get('query') or '').strip()
    quarter_id = request.POST.get('quarter_id') or request.GET.get('quarter_id')
    current_quarter_id = Household.sp_get_current_quarter_id()
    raw_sex = request.GET.get('sex')
    sex = raw_sex.strip() if raw_sex and raw_sex.strip() else None
    raw_sitio = request.GET.get('sitio_id')

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
        results = Family.sp_view_all_general_health(
            query=query,
            quarter_id=quarter_id,
            sitio_id=sitio_id,
            sex=sex,
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
    }
    if sitio_id is not None:
        base_params["sitio_id"] = sitio_id
        
    if sex is not None:
        base_params["sex"] = sex

    if quarter_id is not None:
        base_params["quarter_id"] = quarter_id

    prev_url = "?" + urlencode({**base_params, "page": page - 1}) if has_prev else ""
    next_url = "?" + urlencode({**base_params, "page": page + 1}) if has_next else ""
    limit_urls = {n: "?" + urlencode({**base_params, "limit": n, "page": 1}) for n in LIMIT_OPTIONS}

    quarter = Household.sp_get_quarter()
    sitio = Household.sp_get_sitio()
    
    flash = get_flash(request)
    return render(request, 'nurse_module/nurseGeneralInfo.html', {
        "results": final_result,
        "limit": limit,
        "page": page,
        "sex": sex,
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
        'current_quarter_id': int(current_quarter_id) if current_quarter_id else None,
        'is_current_quarter': is_current_quarter,
        'message': flash['message'],
        'message_level': flash['message_level'],
    })

@custom_login_required
@role_required('Midwife')
def ImmunizationStatus(request):
    return render(request, 'nurse_module/ImmunizationStatus.html')