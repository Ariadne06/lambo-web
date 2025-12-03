from django.shortcuts import render, redirect
from authentication.decorators import custom_login_required, role_required
from django.contrib import messages
from django.db import connection
from .models import Dashboard, AnnouncementRepo, MedicalConditionRow, SurgicalHistoryRow, ResidentList, ChildHealthListRow, ChildHealthDetailRow, GrowthMonitoringRow, ImmunizationRow, MaternalHealthListRow, MaternalHealthDetailRow, ObstetricalHistoryRow, MaternalMedicalConditionRow, MaternalSurgicalHistoryRow, MaternalImmunizationStatusTrackRow, MaternalDiseaseSurveillanceRow, MaternalLaboratoryScreeningRow, MaternalCheckupRow, MaternalSupplementRow, MaternalDeliveryOutcomeRow, MaternalPostpartumVisitRow, DiseaseType,  DiseaseTypeRow, TestTypeRow
from datetime import datetime
from django.shortcuts import render
from django.utils.http import urlencode
from django.views.decorators.http import require_GET
from utils.constants import LIMIT_OPTIONS
from utils.flash import set_flash, get_flash
from utils.db_message import _clean_db_error, _clean_params, coerce_message
from household_module.models import Household, Family
from django.http import JsonResponse, Http404, HttpResponseNotAllowed
import json
import math
from django.db import DatabaseError
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_http_methods


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
    # ---- Core BHW/Nurse dashboard metrics ----
    # Fallback to 0 if personnel_id is not set; this still returns barangay-wide totals.
    personnel_id = getattr(request.user, "personnel_id", 0) or 0

    # Safe defaults for all expected keys
    default_dash = {
        "total_households": 0,
        "total_families": 0,
        "total_active_maternal": 0,
        "total_active_maternal_by_bhw": 0,
        "total_children_upcoming_immun_5d": 0,
        "households_visited_today_by_bhw": 0,
        "total_male": 0,
        "total_female": 0,
        "age_group_0_5": 0,
        "age_group_6_12": 0,
        "age_group_13_17": 0,
        "age_group_18_59": 0,
        "age_group_60_plus": 0,
        "hh_visited_count": 0,
        "hh_not_visited_count": 0,
        "hh_visited_percent": 0,
        "fam_visited_count": 0,
        "fam_not_visited_count": 0,
        "fam_visited_percent": 0,
        "households_per_purok": [],
        "quarter_id": None,
    }

    try:
        raw_dash = Dashboard.bhw_dashboard(personnel_id=personnel_id, quarter_id=None)
    except Exception as e:
        messages.error(request, f"Failed loading dashboard metrics: {e}")
        raw_dash = {}

    dash = {**default_dash, **(raw_dash or {})}

    # ---- Households per Purok (bar chart) ----
    hh_per_purok = dash.get("households_per_purok") or []
    per_sitio_labels = [str(r.get("sitio_name") or "Unassigned") for r in hh_per_purok]
    per_sitio_data = [int(r.get("total_households") or 0) for r in hh_per_purok]

    # ---- Age distribution (pie chart) ----
    age_labels = ["0–5 yrs", "6–12 yrs", "13–17 yrs", "18–59 yrs", "60+ yrs"]
    age_data = [
        int(dash.get("age_group_0_5") or 0),
        int(dash.get("age_group_6_12") or 0),
        int(dash.get("age_group_13_17") or 0),
        int(dash.get("age_group_18_59") or 0),
        int(dash.get("age_group_60_plus") or 0),
    ]
    total_age = sum(age_data) or 1
    age_labels_pct = [
        f"{lbl} ({round((cnt / total_age) * 100)}%)"
        for lbl, cnt in zip(age_labels, age_data)
    ]

    # === Recent announcements (unchanged) ===
    try:
        raw_latest = AnnouncementRepo.list_all(sort='date_desc', limit=20, audience=None)
        latest_announcements = []
        for a in raw_latest:
            aud = ((a.get("audience") or a.get("p_audience") or "both").strip().lower())
            a["audience"] = aud
            a["announcement_date"] = a.get("announcement_date") or a.get("created_date")
            if aud in ("personnel", "both"):     # Midwife sees Personnel + Everyone
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
            if aud in ("personnel", "both"):   # enforce personnel scope
                announcements_all.append(a)
    except Exception as e:
        messages.error(request, f"Failed loading announcements list: {e}")
        announcements_all = []

    ctx = {
        "dash": dash,
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
@require_http_methods(["GET", "POST"])
def vaccine_list(request):
    """
    GET  -> show table of all vaccines + add-new form
    POST -> create new vaccine via insert_vaccine()
    """
    personnel_id = request.session.get("personnel_id")

    if request.method == "POST":
        if not personnel_id:
            messages.error(request, "Missing personnel id in session.")
            return redirect("nurse_module:vaccine_list")

        name = request.POST.get("vaccine_name", "").strip()
        at_birth = bool(request.POST.get("at_birth"))
        first_dose = bool(request.POST.get("first_dose"))
        second_dose = bool(request.POST.get("second_dose"))
        third_dose = bool(request.POST.get("third_dose"))
        interval_str = request.POST.get("interval_between_doses") or None

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT insert_vaccine(%s, %s, %s, %s, %s, %s, %s);",
                    [
                        name,
                        at_birth,
                        first_dose,
                        second_dose,
                        third_dose,
                        interval_str,     # e.g. "4 weeks" or NULL
                        personnel_id,
                    ],
                )
                new_id = cursor.fetchone()[0]

            messages.success(request, f"Vaccine “{name}” added (ID {new_id}).")
            return redirect("nurse_module:vaccine_list")

        except Exception as e:
            # You can parse e.__cause__ / e.args[0] for custom P45xx codes if you like
            messages.error(request, f"Unable to add vaccine: {e}")

    vaccines = _fetch_all_vaccines()
    context = {
        "vaccines": vaccines,
    }
    return render(request, "nurse_module/addVaccine.html", context)


@require_http_methods(["GET", "POST"])
def vaccine_edit(request, vaccine_type_id: int):
    """
    GET  -> show edit form pre-filled using view_specific_vaccine()
    POST -> update via update_vaccine()
    """
    personnel_id = request.session.get("personnel_id")

    vaccine = _fetch_vaccine(vaccine_type_id)
    if not vaccine:
        messages.error(request, "Vaccine not found.")
        return redirect("nurse_module:vaccine_list")

    if request.method == "POST":
        if not personnel_id:
            messages.error(request, "Missing personnel id in session.")
            return redirect("nurse_module:vaccine_list")

        name = request.POST.get("vaccine_name", "").strip() or None
        at_birth = request.POST.get("at_birth")
        first_dose = request.POST.get("first_dose")
        second_dose = request.POST.get("second_dose")
        third_dose = request.POST.get("third_dose")
        interval_str = request.POST.get("interval_between_doses") or None

        # Convert checkbox values: if checkbox is not present, we pass None (keep current)
        def cb_to_bool(value):
            if value is None:
                return None   # don’t change
            return value == "on"

        at_birth_bool = cb_to_bool(at_birth)
        first_bool = cb_to_bool(first_dose)
        second_bool = cb_to_bool(second_dose)
        third_bool = cb_to_bool(third_dose)

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT update_vaccine(
                      %s, %s, %s, %s, %s, %s, %s, %s
                    );
                    """,
                    [
                        vaccine_type_id,
                        name,            # NULL => keep old name
                        at_birth_bool,   # NULL => keep old flag
                        first_bool,
                        second_bool,
                        third_bool,
                        interval_str,    # NULL => keep old interval
                        personnel_id,
                    ],
                )
                updated_id = cursor.fetchone()[0]

            messages.success(request, "Vaccine updated successfully.")
            return redirect("nurse_module:vaccine_list")

        except Exception as e:
            messages.error(request, f"Unable to update vaccine: {e}")

    context = {
        "vaccine": vaccine,
    }
    return render(request, "nurse_module/vaccine_edit.html", context)


def _fetch_all_vaccines():
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM view_all_vaccine();")
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

    vaccines = []
    for row in rows:
        data = dict(zip(columns, row))
        # nice label for interval
        interval = data.get("interval_between_doses")
        if interval:
            days = interval.days
            weeks = days // 7
            if weeks >= 1:
                data["interval_label"] = f"Every {weeks} week(s)"
            else:
                data["interval_label"] = f"{days} day(s)"
        else:
            data["interval_label"] = "—"
        vaccines.append(data)
    return vaccines


# Helper to fetch a specific vaccine via view_specific_vaccine()
def _fetch_vaccine(vaccine_type_id: int):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM view_specific_vaccine(%s);", [vaccine_type_id])
        columns = [col[0] for col in cursor.description]
        row = cursor.fetchone()
    if not row:
        return None
    data = dict(zip(columns, row))
    interval = data.get("interval_between_doses")
    if interval:
        days = interval.days
        weeks = days // 7
        if weeks >= 1:
            data["interval_label"] = f"Every {weeks} week(s)"
        else:
            data["interval_label"] = f"{days} day(s)"
    else:
        data["interval_label"] = ""
    return data

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
        set_flash(request, msg, "error")
    
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
    # Search query
    search_query = (request.GET.get('q') or '').strip() or None

    # 🔹 Future-proof: sitio & sex filters (still optional)
    raw_sitio = request.GET.get('sitio')  # e.g. ?sitio=3
    sex = (request.GET.get('sex') or '').strip() or None  # e.g. 'Male' / 'Female'

    sitio_id = None
    if raw_sitio:
        try:
            sitio_id = int(raw_sitio)
        except (TypeError, ValueError):
            sitio_id = None  # ignore invalid values

    # Pagination
    page_str = request.GET.get('page')
    try:
        page = int(page_str)
        if page < 1:
            page = 1
    except (TypeError, ValueError):
        page = 1

    per_page = 25
    offset = (page - 1) * per_page

    error_message = None
    rows = []
    try:
        # Fetch one extra to know if “next” page exists
        rows = ChildHealthListRow.fetch(
            query=search_query,
            sitio_id=sitio_id,
            sex=sex,
            limit=per_page + 1,
            offset=offset,
        )
    except Exception as e:
        error_message = str(e)

    has_next = len(rows) > per_page
    children = rows[:per_page]

    has_prev = page > 1
    next_page = page + 1 if has_next else None
    prev_page = page - 1 if has_prev else None

    # Base querystring for pagination links
    base_query = {}
    if search_query:
        base_query['q'] = search_query
    if sitio_id is not None:
        base_query['sitio'] = sitio_id
    if sex:
        base_query['sex'] = sex

    base_qs = urlencode(base_query)

    context = {
        'children': children,
        'search_query': search_query or '',
        'page': page,
        'has_next': has_next,
        'has_prev': has_prev,
        'next_page': next_page,
        'prev_page': prev_page,
        'base_qs': base_qs,
        'error_message': error_message,
        # Optional: pass filters back if you later bind them to inputs
        'selected_sitio': sitio_id,
        'selected_sex': sex or '',
    }
    return render(request, 'nurse_module/childrecordList.html', context)


@custom_login_required
@custom_login_required
@role_required('Midwife')
def moreChildRecord(request, child_health_id: int):
    record = ChildHealthDetailRow.fetch_one(child_health_id)
    if not record:
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, "Child record not found or unavailable.")
        return redirect('nurse_module:childrecordList')

    # 🔹 Load vaccine list + dose types for the Add Immunization modal
    vaccines = []
    dose_types = []
    try:
        with connection.cursor() as cur:
            # All vaccines
            cur.execute("SELECT * FROM view_all_vaccine()")
            vaccines = _dictfetchall(cur)

            # All dose types
            cur.execute(
                "SELECT dose_type_id, dose_name FROM Dose_Type ORDER BY dose_type_id"
            )
            dose_types = _dictfetchall(cur)
    except Exception:
        # If something fails here, just leave them empty; UI will show fallback message
        vaccines = []
        dose_types = []

    return render(
        request,
        'nurse_module/moreChildRecord.html',
        {
            'record': record,
            'vaccines': vaccines,
            'dose_types': dose_types,
        },
    )

@custom_login_required
@role_required('Midwife')
@require_POST
def child_immunization_add_api(request, child_health_id: int):

    # Parse JSON or form
    if request.headers.get('Content-Type', '').startswith('application/json'):
        try:
            payload = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({"ok": False, "error": "Invalid JSON payload."}, status=400)
        vaccine_type_id = payload.get('vaccine_type_id')
        dose_type_id = payload.get('dose_type_id')
        date_given = payload.get('date_given')
    else:
        vaccine_type_id = request.POST.get('vaccine_type_id')
        dose_type_id = request.POST.get('dose_type_id')
        date_given = request.POST.get('date_given')

    # Validate inputs
    if not vaccine_type_id or not dose_type_id or not date_given:
        return JsonResponse({"ok": False, "error": "Vaccine, dose, and date are required."}, status=400)

    try:
        vaccine_type_id = int(vaccine_type_id)
        dose_type_id = int(dose_type_id)
    except:
        return JsonResponse({"ok": False, "error": "Invalid vaccine or dose."}, status=400)

    # Resolve personnel
    personnel_id = _resolve_personnel_id(request)
    if personnel_id is None:
        return JsonResponse({"ok": False, "error": "Invalid personnel session."}, status=400)

    # SQL call (updated with date)
    try:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT add_immunization(%s, %s, %s, %s, %s)",
                [child_health_id, vaccine_type_id, dose_type_id, date_given, personnel_id],
            )
            row = cur.fetchone()
            new_id = row[0] if row else None

        return JsonResponse({"ok": True, "immunization_id": new_id, "message": "Immunization recorded."})

    except DatabaseError as e:
        friendly = _pg_error_message(e)
        return JsonResponse({"ok": False, "error": friendly}, status=400)

    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


def _resolve_personnel_id(request):
    """
    Try to find the acting personnel_id from the logged-in user/session.
    Adjust this if your auth layer stores it differently.
    """
    pid = getattr(request.user, 'personnel_id', None)

    # If user has a related personnel object, e.g. request.user.personnel.personnel_id
    if pid is None and hasattr(request.user, 'personnel'):
        pid = getattr(request.user.personnel, 'personnel_id', None)

    # Fallback: session
    if pid is None:
        pid = request.session.get('personnel_id')

    # Final: cast to int if not None
    try:
        return int(pid) if pid is not None else None
    except (TypeError, ValueError):
        return None
    

def _pg_error_message(e: DatabaseError) -> str:
    """
    Extract a friendly message from a PostgreSQL error (with custom ERRCODEs like P4603–P4606).
    """
    orig = getattr(e, '__cause__', None)
    code = getattr(orig, 'pgcode', None)
    diag = getattr(orig, 'diag', None)
    primary = getattr(diag, 'message_primary', None) if diag else None

    # Map your custom codes to very user-friendly text
    if code == 'P4603':
        return "Vaccine type not found."
    if code == 'P4604':
        return "Dose type not found."
    if code == 'P4605':
        return "Invalid dose order or this dose is not enabled for this vaccine."
    if code == 'P4606':
        # 👈 THIS is the “already done” case from add_immunization()
        return "This dose for this vaccine is already recorded for this child."

    # Fallback: use the primary message if available, else whole exception
    return primary or str(e)


@custom_login_required
@role_required('Midwife')
def child_growth_monitoring_api(request, child_health_id: int):
    rows = GrowthMonitoringRow.fetch(child_health_id)
    # Optional: lightweight formatting of nulls is better in the frontend
    return JsonResponse({"rows": rows})

@custom_login_required
@role_required('Midwife')
def child_immunization_api(request, child_health_id: int):
    rows = ImmunizationRow.fetch(child_health_id)
    return JsonResponse({"rows": rows})

def _dictfetchall(cur):
    cols = [col[0] for col in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]

@custom_login_required
@role_required('Midwife')
def childMedSurg(request, child_health_id: int):
    """
    JSON endpoint for Medical Conditions + Surgical History
    Returns:
      { "medical": [...], "surgical": [...] }
    """
    try:
        # Fetch medical conditions with date_added
        medical = MedicalConditionRow.fetch(child_health_id)

        # Fetch surgical history with date_added
        surgical = SurgicalHistoryRow.fetch(child_health_id)

        # Return data as JSON
        return JsonResponse({"medical": medical, "surgical": surgical})
    except Exception as e:
        # Return an error response if there's an exception
        return JsonResponse({"medical": [], "surgical": [], "error": str(e)}, status=500)




@custom_login_required
@role_required('Midwife')
def childSupplements(request, child_health_id: int):
    """
    Returns:
      { "rows": [...] }
    SQL: view_all_child_supplements(p_child_health_id INT)
    """
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM view_all_child_supplements(%s)", [child_health_id])
            rows = _dictfetchall(cur)
            if not rows:
                print(f"No supplement records found for child_health_id: {child_health_id}")
        return JsonResponse({"rows": rows})
    except Exception as e:
        print(f"Error fetching supplement records: {e}")
        return JsonResponse({"rows": [], "error": str(e)}, status=500)



@custom_login_required
@role_required('Midwife')
def maternalrecord(request):
    # ---- Filters from GET ----
    q = request.GET.get("q") or None  # name / resident_id search
    family_code = request.GET.get("family_code") or None
    record_status = request.GET.get("record_status") or None

    date_from_str = request.GET.get("date_from") or ""
    date_to_str = request.GET.get("date_to") or ""

    date_from = _parse_date(date_from_str)
    date_to = _parse_date(date_to_str)

    # ---- Pagination ----
    try:
        page = int(request.GET.get("page", "1"))
    except ValueError:
        page = 1
    if page < 1:
        page = 1

    per_page = 10
    offset = (page - 1) * per_page

    total_count = MaternalHealthListRow.count(
        name_query=q,
        family_code=family_code,
        record_status=record_status,
        date_from=date_from,
        date_to=date_to,
    )
    maternal_records = MaternalHealthListRow.fetch(
        name_query=q,
        family_code=family_code,
        record_status=record_status,
        date_from=date_from,
        date_to=date_to,
        limit=per_page,
        offset=offset,
    )

    total_pages = max(1, math.ceil(total_count / per_page)) if total_count else 1
    if page > total_pages:
        page = total_pages

    # Simple window around current page (e.g., 1 2 [3] 4 5)
    window = 2
    start_page = max(1, page - window)
    end_page = min(total_pages, page + window)
    page_range = list(range(start_page, end_page + 1))

    # Build base query string for pagination links (keep filters, change page)
    qs_params = {}
    for key in ["q", "family_code", "record_status", "date_from", "date_to"]:
        val = request.GET.get(key)
        if val:
            qs_params[key] = val
    base_query = urlencode(qs_params)

    context = {
        "maternal_records": maternal_records,
        "filters": {
            "q": q or "",
            "family_code": family_code or "",
            "record_status": record_status or "",
            "date_from": date_from_str,
            "date_to": date_to_str,
        },
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "total_count": total_count,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "prev_page": page - 1,
            "next_page": page + 1,
            "page_range": page_range,
        },
        "base_query": base_query,
    }
    return render(request, 'nurse_module/maternalrecord.html', context)


def _parse_date(value):
    """Helper to safely parse YYYY-MM-DD from <input type='date'>."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None
    

@custom_login_required
@role_required('Midwife')
def Morematernalrecord(request, maternal_health_id: int):
    mhr = MaternalHealthDetailRow.get_by_id(maternal_health_id)
    if mhr is None:
        raise Http404("Maternal health record not found.")

    obst_hist = ObstetricalHistoryRow.fetch_for_mhr(maternal_health_id)
    medical_conditions = MaternalMedicalConditionRow.fetch_for_mhr(maternal_health_id)
    surgical_history = MaternalSurgicalHistoryRow.fetch_for_mhr(maternal_health_id)
    immu_track = MaternalImmunizationStatusTrackRow.fetch_for_mhr(maternal_health_id)
    disease_surveillance = MaternalDiseaseSurveillanceRow.fetch_for_mhr(maternal_health_id)
    checkups = MaternalCheckupRow.fetch_for_mhr(maternal_health_id)
    lab_screenings = MaternalLaboratoryScreeningRow.fetch_for_mhr(maternal_health_id)
    supplements = MaternalSupplementRow.fetch_for_mhr(maternal_health_id)
    delivery_outcomes = MaternalDeliveryOutcomeRow.fetch_for_mhr(maternal_health_id)
    postpartum_visits = MaternalPostpartumVisitRow.fetch_for_mhr(maternal_health_id)

    disease_types = DiseaseTypeRow.fetch_all()
    test_types = TestTypeRow.fetch_all()   # 👈 for Lab Screening dropdown

    context = {
        "mhr": mhr,
        "obst_hist": obst_hist,
        "medical_conditions": medical_conditions,
        "surgical_history": surgical_history,
        "immu_track": immu_track,
        "disease_surveillance": disease_surveillance,
        "checkups": checkups,
        "lab_screenings": lab_screenings,
        "supplements": supplements,
        "delivery_outcomes": delivery_outcomes,
        "postpartum_visits": postpartum_visits,
        "disease_types": disease_types,
        "test_types": test_types,          # 👈 pass to template
    }
    return render(request, "nurse_module/Morematernalrecord.html", context)


@custom_login_required
@role_required("Midwife")
def add_maternal_disease_screening(request, maternal_health_id: int):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    # 1. Resolve personnel_id (required by add_disease_screen_record)
    personnel_id = get_current_personnel_id(request)
    if not personnel_id:
        messages.error(request, "Unable to resolve current personnel account for this action.")
        return redirect("nurse_module:Morematernalrecord", maternal_health_id=maternal_health_id)

    # 2. Get form values
    disease_type_id = request.POST.get("disease_type_id") or None
    screening_date = request.POST.get("screening_date") or None  # YYYY-MM-DD string, psycopg2 will cast
    result = request.POST.get("result") or None

    try:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT add_disease_screen_record(%s, %s, %s, %s, %s)
                """,
                [maternal_health_id, disease_type_id, screening_date, result, personnel_id],
            )
            new_id = cur.fetchone()[0]  # ids_id
        messages.success(request, "Infectious disease screening record added.")
    except DatabaseError as e:
        # Optional: inspect e.__cause__ / e.args for custom ERRCODEs like M4601..M4604
        messages.error(request, f"Unable to add disease screening record: {e}")
    
    return redirect("nurse_module:Morematernalrecord", maternal_health_id=maternal_health_id)

def get_current_personnel_id(request) -> int | None:
    # 1. Prefer session if you already store it during login
    pid = request.session.get("personnel_id")
    if pid:
        return pid

    # 2. Fallback: resolve via SQL helper, if you’re using it
    user = getattr(request, "user", None)
    if not user or not getattr(user, "id", None):
        return None

    try:
        with connection.cursor() as cur:
            cur.execute("SELECT resolve_current_personnel_id(%s)", [user.id])
            row = cur.fetchone()
            return row[0] if row and row[0] is not None else None
    except DatabaseError:
        return None


@custom_login_required
@role_required("Midwife")
def add_maternal_lab_screening(request, maternal_health_id: int):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    # Resolve personnel_id
    personnel_id = get_current_personnel_id(request)
    if not personnel_id:
        messages.error(request, "Unable to resolve current personnel account for this action.")
        return redirect("nurse_module:Morematernalrecord", maternal_health_id=maternal_health_id)

    # Get form values
    test_type_id = request.POST.get("test_type_id") or None
    test_date = request.POST.get("test_date") or None          # YYYY-MM-DD string
    result = request.POST.get("result") or None

    iron_tablet_given_date = request.POST.get("iron_tablet_given_date") or None
    iron_quantity_raw = request.POST.get("iron_tablet_quantity") or None

    iron_tablet_quantity = None
    if iron_quantity_raw not in (None, ""):
        try:
            iron_tablet_quantity = int(iron_quantity_raw)
        except ValueError:
            messages.error(request, "Iron tablet quantity must be a whole number.")
            return redirect("nurse_module:Morematernalrecord", maternal_health_id=maternal_health_id)

    try:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT add_lab_screening_record(
                  %s,  -- p_maternal_health_id
                  %s,  -- p_test_type_id
                  %s,  -- p_test_date
                  %s,  -- p_result
                  %s,  -- p_iron_tablet_given_date
                  %s,  -- p_iron_tablet_quantity
                  %s   -- p_personnel_id
                )
                """,
                [
                    maternal_health_id,
                    test_type_id,
                    test_date,
                    result,
                    iron_tablet_given_date,
                    iron_tablet_quantity,
                    personnel_id,
                ],
            )
            new_id = cur.fetchone()[0]  # lab_screening_id
        messages.success(request, "Laboratory screening record added.")
    except DatabaseError as e:
        # If you later want to decode custom ERRCODEs (M4701..M4704), you can inspect e.__cause__
        messages.error(request, f"Unable to add laboratory screening record: {e}")

    return redirect("nurse_module:Morematernalrecord", maternal_health_id=maternal_health_id)

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
        set_flash(request, msg, "error")
    
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