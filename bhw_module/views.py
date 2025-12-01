from django.shortcuts import render, redirect
from authentication.decorators import custom_login_required, role_required
from django.contrib import messages
from django.db import connection
from .models import Dashboard, AnnouncementRepo, Child, Maternal
from household_module.models import Household, Family
from utils.flash import set_flash, get_flash
from utils.db_message import _clean_db_error, _clean_params, coerce_message
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from utils.constants import LIMIT_OPTIONS
from django.utils.http import urlencode
from django.urls import reverse
import json
import re 
from datetime import datetime, date
from django.utils.datastructures import MultiValueDictKeyError
from django.http import HttpResponseRedirect

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


@custom_login_required
@role_required('Barangay Health Worker')  # add more personnel roles if needed
def bhw_dashboard(request):
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
        # ✅ expose these to the template
        'current_quarter_id': int(current_quarter_id) if current_quarter_id else None,
        'is_current_quarter': is_current_quarter,
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
    hid = int(request.POST.get('household_id'))
    pid = int(request.session.get('personnel_id') or 0)
    household_number = (
        request.GET.get('household_number')
        or request.session.get('household_number')
        or request.POST.get('household_number')
    )
    

    # get quarter id if present (else None)
    qid = None
    qid_raw = request.POST.get('quarter_id') or request.GET.get('quarter_id')
    try:
        if qid_raw not in (None, "", "None"):
            qid = int(qid_raw)
    except (TypeError, ValueError):
        qid = None

    def redirect_to_view():
        if not hid:
            return redirect('bhw_module:householdList')

        params = {"hid": hid, "household_number": household_number}
        
        if qid is not None:
            params["quarter_id"] = qid
        return redirect(reverse('bhw_module:householdView') + "?" + urlencode(params))

    if not pid:
        set_flash(request, "Missing personnel id.", "error")
        return redirect('bhw_module:householdList')

    # pull current row to compare against (NOTE: now passing qid)
    try:
        prev = Household.sp_get_specific_household(hid, qid)
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
    hid = int(request.POST.get('household_id'))
    pid = int(request.session.get('personnel_id') or 0)
    household_number = (
        request.GET.get('household_number')
        or request.session.get('household_number')
        or request.POST.get('household_number')
    )
    
    def _to_bool(v, default=False):
        if isinstance(v, bool):
            return v
        if v is None:
            return default
        s = str(v).strip().lower()
        if s in {"1", "true", "t", "yes", "y", "on"}:
            return True
        if s in {"0", "false", "f", "no", "n", "off"}:
            return False
        return default

    # get quarter id if present (else None)
    qid = None
    qid_raw = request.POST.get('quarter_id') or request.GET.get('quarter_id')
    try:
        if qid_raw not in (None, "", "None"):
            qid = int(qid_raw)
    except (TypeError, ValueError):
        qid = None

    def redirect_to_view():
        if not hid:
            return redirect('bhw_module:householdList')

        params = {"hid": hid, "household_number": household_number}
        
        if qid is not None:
            params["quarter_id"] = qid
        return redirect(reverse('bhw_module:householdView') + "?" + urlencode(params))

    if not pid:
        set_flash(request, "Missing personnel id.", "error")
        return redirect('bhw_module:householdList')
    
    if request.method == 'POST':
        family_head_id = int(request.POST.get('family_head_id'))
        respondent_id = int(request.POST.get('respondent_id'))
        fam_head_rel = int(request.POST.get('fam_head_rel'))
        respondent_head_rel = int(request.POST.get('respondent_head_rel'))
        respondent_rel = int(request.POST.get('respondent_rel'))
        household_type = int(request.POST.get('household_type'))
        waste_management_type = int(request.POST.get('waste_management_type'))
        water_source_type = int(request.POST.get('water_source_type'))
        toilet_facility_type = int(request.POST.get('toilet_facility_type'))
        ip_tribe        = (request.POST.get('ip_tribe') or '').strip()
        waste_other_text = ''
        performed_by_type = 'personnel'
        bhw_assignment = False
        
        nhts_status_raw     = request.POST.get('nhts_status')
        ip_status_raw = request.POST.get('ip_status')

        nhts_status     = _to_bool(nhts_status_raw)
        ip_status = _to_bool(ip_status_raw)
    
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
                respondent_head_rel,
                fam_head_rel,
                ip_status,
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
@require_POST
def insert_family_member(request):
    hid = int(request.POST.get('household_id') or 0)
    pid = int(request.session.get('personnel_id') or 0)
    
    household_number = (
        request.GET.get('household_number')
        or request.session.get('household_number')
        or request.POST.get('household_number')
    )

    # get quarter id if present (else None)
    qid = None
    qid_raw = request.POST.get('quarter_id') or request.GET.get('quarter_id')
    try:
        if qid_raw not in (None, "", "None"):
            qid = int(qid_raw)
    except (TypeError, ValueError):
        qid = None

    def redirect_to_view():
        if not hid:
            return redirect('bhw_module:householdList')

        params = {"hid": hid, "household_number": household_number}
        
        if qid is not None:
            params["quarter_id"] = qid
        return redirect(reverse('bhw_module:householdView') + "?" + urlencode(params))

    if not pid:
        set_flash(request, "Missing personnel id.", "error")
        return redirect('bhw_module:householdList')
    
    if request.method == 'POST':
        rid = int(request.POST.get('resident_id'))
        fid = int(request.POST.get('family_id'))
        mem_rel_hh = int(request.POST.get('mem_rel_hh'))
        mem_rel_fh = int(request.POST.get('mem_rel_fh'))
        philhealth_number = (request.POST.get('philhealth_number') or '').strip()
        membership_type = (request.POST.get('membership_type') or '').strip()
        philhealth_category = request.POST.get('philhealth_category')
        nutrition_status = request.POST.get('nutritional_status')
        
        if philhealth_number and not re.fullmatch(r"[0-9\-]+", philhealth_number):
            set_flash(request, "PhilHealth Number should contain only digits and dashes.", "error")
            return redirect_to_view()

        
        if membership_type == '':
            membership_type = None
        
        if philhealth_category:
            try:
                philhealth_category = int(philhealth_category)
            except ValueError:
                philhealth_category = None
                
        if nutrition_status:
            try:
                nutrition_status = int(nutrition_status)
            except ValueError:
                nutrition_status = None
    
        try:
            Family.sp_insert_family_member(
                rid,
                fid,
                mem_rel_hh,
                mem_rel_fh,
                philhealth_number,
                membership_type,
                philhealth_category,
                nutrition_status,
                pid,
            )
            set_flash(request, f"Family member added successfully.", "success")
        except Exception as e:
            set_flash(request, _clean_db_error(e), "error")

    return redirect_to_view()

@custom_login_required
@role_required('Barangay Health Worker')
@require_POST
def mark_family_visit(request):

    hid = int(request.POST.get('household_id'))
    pid = int(request.session.get('personnel_id'))
    fid = int(request.POST.get('family_id'))
    
    household_number = (
        request.GET.get('household_number')
        or request.session.get('household_number')
        or request.POST.get('household_number')
    )

    # get quarter id if present (else None)
    qid = None
    qid_raw = request.POST.get('quarter_id') or request.GET.get('quarter_id')
    try:
        if qid_raw not in (None, "", "None"):
            qid = int(qid_raw)
    except (TypeError, ValueError):
        qid = None

    def redirect_to_view():
        if not hid:
            return redirect('bhw_module:householdList')

        params = {"hid": hid, "household_number": household_number}
        
        if qid is not None:
            params["quarter_id"] = qid
        return redirect(reverse('bhw_module:householdView') + "?" + urlencode(params))

    if not pid:
        set_flash(request, "Missing personnel id.", "error")
        return redirect('bhw_module:householdView')

    try:
        # Call your stored procedure / function
        Family.sp_mark_family_visited(fid, pid)
        set_flash(request, "Family marked as visited.", "success")
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")

    return redirect_to_view()

@custom_login_required
@role_required('Barangay Health Worker')
@require_POST
def update_family(request):
    # --- ids / context ---
    try:
        family_id = int(request.POST.get('family_id'))
        hid       = int(request.POST.get('household_id'))
    except (TypeError, ValueError):
        set_flash(request, "Invalid household/family id.", "error")
        return redirect('bhw_module:householdList')

    pid = int(request.session.get('personnel_id') or 0)

    household_number = (
        request.GET.get('household_number')
        or request.session.get('household_number')
        or request.POST.get('household_number')
    )

    # quarter (optional)
    qid = None
    qid_raw = request.POST.get('quarter_id') or request.GET.get('quarter_id')
    try:
        if qid_raw not in (None, "", "None"):
            qid = int(qid_raw)
    except (TypeError, ValueError):
        qid = None

    def redirect_to_view():
        if not hid:
            return redirect('bhw_module:householdList')
        params = {"hid": hid, "household_number": household_number}
        if qid is not None:
            params["quarter_id"] = qid
        return redirect(reverse('bhw_module:householdView') + "?" + urlencode(params))

    if not pid:
        set_flash(request, "Missing personnel id.", "error")
        return redirect('bhw_module:householdList')

    # --- fetch previous row for comparison ---
    try:
        prev = Family.sp_get_specific_family(family_id, qid)
        if not prev:
            set_flash(request, "Family not found.", "error")
            return redirect_to_view()
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")
        return redirect_to_view()

    # helpers
    def _to_int(val, default=None):
        try:
            return int(val)
        except (TypeError, ValueError):
            return default

    def _to_bool(val):
        if val is None:
            return None
        s = str(val).strip().lower()
        if s in ("true", "1", "yes", "y"):  return True
        if s in ("false", "0", "no", "n"):  return False
        return None

    def _norm_str(s):
        return (s or "").strip()

    # --- current (normalize) ---
    curr_head_id   = _to_int(prev.get('family_head_id'), 0)
    curr_resp_id   = _to_int(prev.get('respondent_id'), 0)
    curr_rtf_id    = _to_int(prev.get('respondent_rtf_id'), 0) 
    curr_hht_id    = _to_int(prev.get('household_type_id'), 0)
    curr_wmt_id    = _to_int(prev.get('waste_management_type_id'), 0)
    curr_ws_id     = _to_int(prev.get('water_source_type_id'), 0)
    curr_tf_id     = _to_int(prev.get('toilet_facility_type_id'), 0)
    curr_nhts      = bool(prev.get('nhts_status')) if prev.get('nhts_status') is not None else None
    curr_indigent  = bool(prev.get('ip_status')) if prev.get('ip_status') is not None else None
    curr_ip_tribe  = _norm_str(prev.get('ip_tribe'))

    # --- posted (convert) ---
    try:
        new_head_id  = _to_int(request.POST.get('family_head_id'))
        new_resp_id  = _to_int(request.POST.get('respondent_id'))
        new_rtf_id   = _to_int(request.POST.get('respondent_rel'))
        new_hht_id   = _to_int(request.POST.get('household_type'))
        new_wmt_id   = _to_int(request.POST.get('waste_management_type'))
        new_ws_id    = _to_int(request.POST.get('water_source_type'))
        new_tf_id    = _to_int(request.POST.get('toilet_facility_type'))
    except (TypeError, ValueError):
        set_flash(request, "Invalid numeric field(s).", "error")
        return redirect_to_view()

    # booleans can come as "true"/"false"
    nhts_status     = _to_bool(request.POST.get('nhts_status'))
    # accept either 'indigent_status' (update modal) or 'ip_status' (older naming)
    indigent_status = _to_bool(request.POST.get('indigent_status'))
    if indigent_status is None:
        indigent_status = _to_bool(request.POST.get('ip_status'))

    ip_tribe = _norm_str(request.POST.get('ip_tribe'))

    # optional validation: require tribe if indigent/IP == True
    if indigent_status is True and not ip_tribe:
        set_flash(request, "Please specify the IP Tribe when Indigenous/Indigent = YES.", "error")
        return redirect_to_view()

    # guard: ensure required ints are present
    required_ints = [
        ("Family Head", new_head_id),
        ("Respondent", new_resp_id),
        ("Relationship (Respondent → Family Head)", new_rtf_id),
        ("Household Type", new_hht_id),
        ("Waste Management", new_wmt_id),
        ("Water Source", new_ws_id),
        ("Toilet Facility", new_tf_id),
    ]
    missing = [label for label, val in required_ints if val is None]
    if missing:
        set_flash(request, f"Missing/invalid fields: {', '.join(missing)}.", "error")
        return redirect_to_view()

    # --- compare for “Changed:” summary ---
    changed = []
    if new_head_id != curr_head_id: changed.append("Family head")
    if new_resp_id != curr_resp_id: changed.append("Respondent")
    if new_rtf_id  != curr_rtf_id:  changed.append("Rel (Respondent→Family Head)")
    if new_hht_id  != curr_hht_id:  changed.append("Household type")
    if new_wmt_id  != curr_wmt_id:  changed.append("Waste management")
    if new_ws_id   != curr_ws_id:   changed.append("Water source")
    if new_tf_id   != curr_tf_id:   changed.append("Toilet facility")
    if nhts_status is not None and nhts_status != curr_nhts:         changed.append("NHTS status")
    if indigent_status is not None and indigent_status != curr_indigent: changed.append("Indigenous/Indigent status")
    if _norm_str(ip_tribe).casefold() != curr_ip_tribe.casefold():   changed.append("IP Tribe")

    if not changed:
        set_flash(request, "No changes detected — nothing to update.", "info")
        return redirect_to_view()

    # --- persist ---
    try:
        # Adjust to your actual stored proc / ORM method signature.
        Family.sp_update_family(
            family_id,
            pid,
            hid,
            new_hht_id,
            new_head_id,
            new_resp_id,
            new_rtf_id,
            indigent_status,
            ip_tribe or None,
            nhts_status,
            new_ws_id,
            new_tf_id,
            new_wmt_id,
            waste_other_text=None,
        )
        set_flash(request, f"Family updated successfully. Changed: {', '.join(changed)}.", "success")
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")

    return redirect_to_view()

@custom_login_required
@role_required('Barangay Health Worker')
@require_POST
def deactivate_family(request):

    hid = int(request.POST.get('household_id'))
    pid = int(request.session.get('personnel_id'))
    fid = int(request.POST.get('family_id'))
    reason = (request.POST.get('reason') or '').strip()
    
    household_number = (
        request.GET.get('household_number')
        or request.session.get('household_number')
        or request.POST.get('household_number')
    )

    # get quarter id if present (else None)
    qid = None
    qid_raw = request.POST.get('quarter_id') or request.GET.get('quarter_id')
    try:
        if qid_raw not in (None, "", "None"):
            qid = int(qid_raw)
    except (TypeError, ValueError):
        qid = None

    def redirect_to_view():
        if not hid:
            return redirect('bhw_module:householdList')

        params = {"hid": hid, "household_number": household_number}
        
        if qid is not None:
            params["quarter_id"] = qid
        return redirect(reverse('bhw_module:householdView') + "?" + urlencode(params))

    if not pid:
        set_flash(request, "Missing personnel id.", "error")
        return redirect('bhw_module:householdView')

    try:
        # Call your stored procedure / function
        Family.sp_deactivate_family(fid, pid, reason)
        set_flash(request, "Family marked as inactive.", "success")
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")

    return redirect_to_view()

@custom_login_required
@role_required('Barangay Health Worker')
@require_POST
def deactivate_household(request):

    hid = int(request.POST.get('household_id'))
    pid = int(request.session.get('personnel_id'))
    reason = (request.POST.get('reason') or '').strip()
    
    household_number = (
        request.GET.get('household_number')
        or request.session.get('household_number')
        or request.POST.get('household_number')
    )

    # get quarter id if present (else None)
    qid = None
    qid_raw = request.POST.get('quarter_id') or request.GET.get('quarter_id')
    try:
        if qid_raw not in (None, "", "None"):
            qid = int(qid_raw)
    except (TypeError, ValueError):
        qid = None

    def redirect_to_view():
        if not hid:
            return redirect('bhw_module:householdList')

        params = {"hid": hid, "household_number": household_number}
        
        if qid is not None:
            params["quarter_id"] = qid
        return redirect(reverse('bhw_module:householdView') + "?" + urlencode(params))

    if not pid:
        set_flash(request, "Missing personnel id.", "error")
        return redirect('bhw_module:householdView')

    try:
        # Call your stored procedure / function
        Household.sp_deactivate_household(hid, reason, pid)
        set_flash(request, "Household marked as inactive.", "success")
        return redirect('bhw_module:householdList')
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")

    return redirect_to_view()

@custom_login_required
@role_required('Barangay Health Worker')
@require_POST
def reactivate_household(request):

    hid = int(request.POST.get('household_id'))
    pid = int(request.session.get('personnel_id'))
    
    household_number = (
        request.GET.get('household_number')
        or request.session.get('household_number')
        or request.POST.get('household_number')
    )

    # get quarter id if present (else None)
    qid = None
    qid_raw = request.POST.get('quarter_id') or request.GET.get('quarter_id')
    try:
        if qid_raw not in (None, "", "None"):
            qid = int(qid_raw)
    except (TypeError, ValueError):
        qid = None

    def redirect_to_view():
        if not hid:
            return redirect('bhw_module:householdList')

        params = {"hid": hid, "household_number": household_number}
        
        if qid is not None:
            params["quarter_id"] = qid
        return redirect(reverse('bhw_module:householdView') + "?" + urlencode(params))

    if not pid:
        set_flash(request, "Missing personnel id.", "error")
        return redirect('bhw_module:householdView')

    try:
        # Call your stored procedure / function
        Household.sp_reactivate_household(hid, pid)
        set_flash(request, "Household marked as inactive.", "success")
        return redirect('bhw_module:householdList')
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")

    return redirect_to_view()

@custom_login_required
@role_required('Barangay Health Worker')
@require_POST
def update_family_member(request):
    try:
        fm_id = int(request.POST.get('family_member_id'))
        hid   = int(request.POST.get('household_id'))
    except (TypeError, ValueError):
        set_flash(request, "Invalid household/member id.", "error")
        return redirect('bhw_module:householdList')

    pid = int(request.session.get('personnel_id') or 0)
    if not pid:
        set_flash(request, "Missing personnel id.", "error")
        return redirect('bhw_module:householdList')

    household_number = (
        request.GET.get('household_number')
        or request.session.get('household_number')
        or request.POST.get('household_number')
    )

    def redirect_to_view():
        if not hid:
            return redirect('bhw_module:householdList')
        params = {"hid": hid, "household_number": household_number}
        return redirect(reverse('bhw_module:householdView') + "?" + urlencode(params))

    # ---------- helpers ----------
    def _to_int(val, default=None):
        try:
            if val in (None, "", "None"):
                return default
            return int(val)
        except (TypeError, ValueError):
            return default

    def _norm_str(s):
        return (s or "").strip()

    def _norm_choice(s, allowed):
        v = _norm_str(s).upper()
        return v if v in allowed else None

    try:
        prev = Family.sp_get_specific_family_member(fm_id)
        if not prev:
            set_flash(request, "Family member not found.", "error")
            return redirect_to_view()
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")
        return redirect_to_view()

    curr_rth_id   = _to_int(prev.get('rth_id'), 0)
    curr_rtf_id   = _to_int(prev.get('rtf_id'), 0)
    curr_ph_no    = _norm_str(prev.get('philhealthid_number'))
    curr_mtype    = _norm_str(prev.get('membership_type')).upper() if prev.get('membership_type') else ""
    curr_pcat_id  = _to_int(prev.get('philhealth_category_id'), None)
    curr_nut_id   = _to_int(prev.get('nutrition_status_id'), None)

    new_rth_id  = _to_int(request.POST.get('mem_rel_hh'))
    new_rtf_id  = _to_int(request.POST.get('mem_rel_fh'))
    ph_no_raw   = _norm_str(request.POST.get('philhealth_number'))
    new_mtype   = _norm_choice(request.POST.get('membership_type'), {"M", "D"})
    new_pcat_id = _to_int(request.POST.get('philhealth_category'))
    new_nut_id  = _to_int(request.POST.get('nutritional_status'))

    # Required ints
    missing = []
    if new_rth_id is None: missing.append("Relationship to Household Head")
    if new_rtf_id is None: missing.append("Relationship to Family Head")
    if missing:
        set_flash(request, f"Missing/invalid fields: {', '.join(missing)}.", "error")
        return redirect_to_view()

    if ph_no_raw:
        if not new_mtype or new_pcat_id is None:
            set_flash(request,
                      "If a PhilHealth Number is provided, please select the Membership Type and Category.",
                      "error")
            return redirect_to_view()
        import re
        if not re.fullmatch(r"[0-9\-]+", ph_no_raw):
            set_flash(request, "PhilHealth Number should contain only digits and dashes.", "error")
            return redirect_to_view()
        ph_no = ph_no_raw
    else:
        ph_no = None
        new_mtype = None
        new_pcat_id = None

    changed = []
    if new_rth_id != curr_rth_id: changed.append("Rel (Member→Household Head)")
    if new_rtf_id != curr_rtf_id: changed.append("Rel (Member→Family Head)")
    if (ph_no or "") != (curr_ph_no or ""): changed.append("PhilHealth Number")
    if (new_mtype or "") != (curr_mtype or ""): changed.append("PhilHealth Membership Type")
    if (new_pcat_id or None) != (curr_pcat_id or None): changed.append("PhilHealth Category")
    if (new_nut_id or None) != (curr_nut_id or None): changed.append("Nutritional Status")

    if not changed:
        set_flash(request, "No changes detected — nothing to update.", "info")
        return redirect_to_view()

    try:
        Family.sp_update_family_member(
            fm_id,
            pid,
            new_rth_id,
            new_rtf_id,
            ph_no,
            new_mtype,
            new_pcat_id,
            new_nut_id,
        )
        set_flash(request, f"Family member updated successfully. Changed: {', '.join(changed)}.", "success")
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")

    return redirect_to_view()

@custom_login_required
@role_required('Barangay Health Worker')
@require_POST
def remove_family_member(request):

    hid = int(request.POST.get('household_id'))
    pid = int(request.session.get('personnel_id'))
    rid = int(request.POST.get('resident_id'))
    fid = int(request.POST.get('family_id'))
    reason = (request.POST.get('reason') or '').strip()
    performed_by_type = 'personnel'
    assignment_bhw = False
    
    household_number = (
        request.GET.get('household_number')
        or request.session.get('household_number')
        or request.POST.get('household_number')
    )

    # get quarter id if present (else None)
    qid = None
    qid_raw = request.POST.get('quarter_id') or request.GET.get('quarter_id')
    try:
        if qid_raw not in (None, "", "None"):
            qid = int(qid_raw)
    except (TypeError, ValueError):
        qid = None

    def redirect_to_view():
        if not hid:
            return redirect('bhw_module:householdList')

        params = {"hid": hid, "household_number": household_number}
        
        if qid is not None:
            params["quarter_id"] = qid
        return redirect(reverse('bhw_module:householdView') + "?" + urlencode(params))

    if not pid:
        set_flash(request, "Missing personnel id.", "error")
        return redirect('bhw_module:householdView')

    try:
        # Call your stored procedure / function
        Family.sp_remove_family_member_from_family(rid, fid, pid, performed_by_type, assignment_bhw, reason)
        set_flash(request, "Family member removed successfully.", "success")
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")

    return redirect_to_view()

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
@role_required('Barangay Health Worker')
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
@role_required('Barangay Health Worker')
@require_POST
def resident_link_insert(request):
    try:
        origin_id = int(request.POST["source_resident_id"])
        target_id = int(request.POST["related_resident_id"])
        rel_id    = int(request.POST["relationship_id"])
        if origin_id == target_id:
            return _err("You cannot link a resident to themselves.")

        relation_id = Family.sp_link_resident_relation(origin_id, target_id, rel_id)
        return _ok({"relation_id": relation_id})
    except (KeyError, MultiValueDictKeyError, ValueError):
        return _err("source_resident_id, related_resident_id and relationship_id are required.")
    except Exception as e:
        # surfaces E810x messages from your PL/pgSQL
        return _err(e)

@custom_login_required
@role_required('Barangay Health Worker')
@require_POST
def resident_link_remove(request):
    try:
        origin_id = int(request.POST["source_resident_id"])
        target_id = int(request.POST["related_resident_id"])
        rel_id    = int(request.POST["relationship_id"])
        closed = Family.sp_unlink_resident_relation(origin_id, target_id, rel_id)
        return _ok({"closed": closed})
    except (KeyError, MultiValueDictKeyError, ValueError):
        return _err("source_resident_id, related_resident_id and relationship_id are required.")
    except Exception as e:
        return _err(e)
    
@custom_login_required
@role_required('Barangay Health Worker')
@require_POST
def insert_general_health(request):
    hid = int(request.POST.get('household_id') or 0)
    pid = int(request.session.get('personnel_id') or 0)
    
    household_number = (
        request.GET.get('household_number')
        or request.session.get('household_number')
        or request.POST.get('household_number')
    )

    # get quarter id if present (else None)
    qid = None
    qid_raw = request.POST.get('quarter_id') or request.GET.get('quarter_id')
    try:
        if qid_raw not in (None, "", "None"):
            qid = int(qid_raw)
    except (TypeError, ValueError):
        qid = None

    def redirect_to_view():
        if not hid:
            return redirect('bhw_module:householdList')

        params = {"hid": hid, "household_number": household_number}
        
        if qid is not None:
            params["quarter_id"] = qid
        return redirect(reverse('bhw_module:householdView') + "?" + urlencode(params))

    if not pid:
        set_flash(request, "Missing personnel id.", "error")
        return redirect('bhw_module:householdList')
    
    if request.method == 'POST':
        fmid = int(request.POST.get('member_id'))
        class_id = int(request.POST.get('class'))
        raw_ids = request.POST.getlist("medical_history")
        fp_method_str = request.POST.get("fp_method")
        fp_status_str = request.POST.get("fp_status")
        age_of_menarche_str = request.POST.get("age_menarche")

        fp_method_bool = request.POST.get("fp_use")
        smoker_bool = request.POST.get("smoker")
        alcohol_drinker_bool = request.POST.get("alcohol_drinker")
        sexually_active_bool = request.POST.get("sexually_active")
        
        age_of_menarche = int(age_of_menarche_str) if age_of_menarche_str is not None and age_of_menarche_str.strip() != "" else None
        fp_status_id = int(fp_status_str) if fp_status_str is not None and fp_status_str.strip() != "" else None
        fp_method_id = int(fp_method_str) if fp_method_str is not None and fp_method_str.strip() != "" else None
        fp_method_yn = {'true': True, 'false': False}.get((fp_method_bool or '').lower(), None)
        smoker = {'true': True, 'false': False}.get((smoker_bool or '').lower(), None)
        alcohol_drinker = {'true': True, 'false': False}.get((alcohol_drinker_bool or '').lower(), None)
        sexually_active = {'true': True, 'false': False}.get((sexually_active_bool or '').lower(), None)
        
        med_ids = sorted({int(x) for x in raw_ids if x.isdigit()})
        med_ids_param = med_ids or None
        
        date_str = request.POST.get("last_menstrual_period")
        try:
            lmp = date.fromisoformat(date_str) if date_str else None
        except ValueError:
            lmp = None
    
        try:
            Family.sp_save_general_health_for_member(
                fmid,
                class_id,
                med_ids_param,
                lmp,
                fp_method_yn,
                fp_method_id,
                fp_status_id,
                age_of_menarche,
                smoker,
                alcohol_drinker,
                sexually_active,
                pid,
            )
            set_flash(request, f"General health information added successfully.", "success")
        except Exception as e:
            set_flash(request, _clean_db_error(e), "error")

    return redirect_to_view()

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
@role_required('Barangay Health Worker')
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
        return JsonResponse({"error": "database_error", "detail": _clean_db_error(e)}, status=500)

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
@role_required('Barangay Health Worker')
@require_POST
def update_general_health(request):
    # ----------- helpers -----------
    def _to_int(val, default=None):
        try:
            if val in (None, "", "None"):
                return default
            return int(val)
        except (TypeError, ValueError):
            return default

    def _to_bool(val):
        s = (val or "").strip().lower()
        if s in ("true", "1", "yes", "y", "on"):  return True
        if s in ("false", "0", "no", "n", "off"): return False
        return None

    def _to_date(val):
        if not val: return None
        try:
            return datetime.strptime(val, "%Y-%m-%d").date()
        except Exception:
            return None

    def _to_int_list(vals):
        out = []
        for v in (vals or []):
            try: out.append(int(v))
            except Exception: pass
        return out

    def _same_mh(a, b):
        # treat NULL and [] as equal for "no change" UX (avoid spurious updates)
        A = set(a or [])
        B = set(b or [])
        return A == B

    def _redirect_back(hid, household_number):
        if not hid:
            return redirect('bhw_module:householdList')
        params = {"hid": hid}
        if household_number:
            params["household_number"] = household_number
        return HttpResponseRedirect(reverse('bhw_module:householdView') + "?" + urlencode(params))

    # ----------- basics -----------
    try:
        fm_id = int(request.POST.get('member_id'))
        hid   = int(request.POST.get('household_id'))
    except (TypeError, ValueError):
        set_flash(request, "Invalid household/member id.", "error")
        return redirect('bhw_module:householdList')

    pid = int(request.session.get('personnel_id') or 0)
    if not pid:
        set_flash(request, "Missing personnel id.", "error")
        return redirect('bhw_module:householdList')

    household_number = (
        request.GET.get('household_number')
        or request.session.get('household_number')
        or request.POST.get('household_number')
    )

    # ----------- current row -----------
    try:
        cur = Family.sp_get_specific_family_member_genhealth(fm_id)
        if not cur:
            set_flash(request, "No General Health record for this member in the current quarter.", "error")
            return _redirect_back(hid, household_number)
    except Exception as e:
        set_flash(request, _clean_db_error(e) if ' _clean_db_error' in globals() else _clean_db_error(e), "error")
        return _redirect_back(hid, household_number)

    # Normalize current values
    sex = (cur.get("sex") or "").strip().lower()
    is_female = (sex == "female")

    cur_class_id  = _to_int(cur.get("class_id"))
    cur_mh_ids    = cur.get("medical_history_ids") or []
    if isinstance(cur_mh_ids, str):
        # robust fallback if driver returns a JSON string
        try:
            import json
            cur_mh_ids = [int(x) for x in json.loads(cur_mh_ids)]
        except Exception:
            cur_mh_ids = []

    cur_smoker          = cur.get("smoker")
    cur_alcohol         = cur.get("alcohol_drinker")
    cur_sex_active      = cur.get("sexually_active")
    cur_lmp             = cur.get("last_menstrual_period")
    cur_fp_use          = cur.get("fp_method_yn")
    cur_fp_method_id    = _to_int(cur.get("fp_method_id"))
    cur_fp_status_id    = _to_int(cur.get("fp_status_id"))
    cur_age_menarche    = _to_int(cur.get("age_of_menarche"))

    # ----------- new (posted) values -----------
    new_class_id       = _to_int(request.POST.get("class"))
    new_mh_ids         = _to_int_list(request.POST.getlist("medical_history"))
    new_smoker         = _to_bool(request.POST.get("smoker"))
    new_alcohol        = _to_bool(request.POST.get("alcohol_drinker"))
    new_sex_active     = _to_bool(request.POST.get("sexually_active"))

    new_lmp            = _to_date(request.POST.get("last_menstrual_period"))
    new_fp_use         = _to_bool(request.POST.get("fp_use"))
    new_fp_method_id   = _to_int(request.POST.get("fp_method"))
    new_fp_status_id   = _to_int(request.POST.get("fp_status"))
    new_age_menarche   = _to_int(request.POST.get("age_menarche"))

    # If fp_use is FALSE, we intend to clear method & status
    eff_method_id = new_fp_method_id if new_fp_use else None
    eff_status_id = new_fp_status_id if new_fp_use else None

    # ----------- detect changes -----------
    changed = []

    class_changed = (new_class_id is not None and new_class_id != cur_class_id)
    if class_changed:
        changed.append("Classification by Age")

    mh_changed = (not _same_mh(new_mh_ids, cur_mh_ids))
    if mh_changed:
        changed.append("Medical History")

    lifestyle_changed = any([
        new_smoker is not None and new_smoker != cur_smoker,
        new_alcohol is not None and new_alcohol != cur_alcohol,
        new_sex_active is not None and new_sex_active != cur_sex_active,
    ])
    if lifestyle_changed:
        # split names for nicer flash
        if new_smoker is not None and new_smoker != cur_smoker:           changed.append("Smoker")
        if new_alcohol is not None and new_alcohol != cur_alcohol:        changed.append("Alcohol Drinker")
        if new_sex_active is not None and new_sex_active != cur_sex_active: changed.append("Sexually Active")

    fp_changed = False
    apply_fp = False
    if is_female:
        fp_changed = any([
            new_lmp is not cur_lmp and new_lmp != cur_lmp,
            new_fp_use is not None and new_fp_use != cur_fp_use,
            eff_method_id != cur_fp_method_id,
            eff_status_id != cur_fp_status_id,
            (new_age_menarche is not None and new_age_menarche != cur_age_menarche),
        ])
        if fp_changed:
            apply_fp = True
            if new_lmp is not cur_lmp and new_lmp != cur_lmp:             changed.append("Last Menstrual Period")
            if new_fp_use is not None and new_fp_use != cur_fp_use:        changed.append("FP Use")
            if eff_method_id != cur_fp_method_id:                          changed.append("FP Method")
            if eff_status_id != cur_fp_status_id:                          changed.append("FP Status")
            if new_age_menarche is not None and new_age_menarche != cur_age_menarche:
                changed.append("Age of Menarche")

    # Turn on apply flags only if their section changed
    apply_medical_history = mh_changed
    apply_lifestyle       = lifestyle_changed

    # If nothing changed at all, short-circuit.
    if not any([class_changed, apply_medical_history, apply_lifestyle, apply_fp]):
        set_flash(request, "No changes detected — nothing to update.", "info")
        return _redirect_back(hid, household_number)

    # ----------- call SP -----------
    try:
        Family.sp_update_general_health_for_member(
            family_member_id   = fm_id,
            class_id           = (new_class_id if class_changed else None),

            apply_medical_history = apply_medical_history,
            medical_history_ids   = (new_mh_ids if apply_medical_history else None),

            apply_fp          = apply_fp,
            wra_lmp           = (new_lmp if apply_fp else None),
            fp_method_yn      = (new_fp_use if apply_fp else None),
            fp_method_id      = (eff_method_id if apply_fp else None),
            fp_status_id      = (eff_status_id if apply_fp else None),
            age_of_menarche   = (new_age_menarche if apply_fp else None),

            apply_lifestyle   = apply_lifestyle,
            smoker            = (new_smoker if apply_lifestyle else None),
            alcohol_drinker   = (new_alcohol if apply_lifestyle else None),
            sexually_active   = (new_sex_active if apply_lifestyle else None),

            pid               = pid
        )
        set_flash(request, f"General Health updated. Changed: {', '.join(changed)}.", "success")
    except Exception as e:
        set_flash(request, _clean_db_error(e) if ' _clean_db_error' in globals() else _clean_db_error(e), "error")

    return _redirect_back(hid, household_number)

@custom_login_required
@role_required('Barangay Health Worker')
def householdView(request):
    
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
        results = Child.sp_view_all_child_health_record(
            query=query,
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
    return render(request, 'bhw_module/childList.html', {
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
@role_required('Barangay Health Worker')
def addchild1(request):
    context = {}
    if request.method == 'POST':
        # Handle back navigation from addchild2 - pass POST data to template
        context.update({
            'child_data': {
                'child_id': request.POST.get('child_id', ''),
                'child_name': request.POST.get('child_name', ''),
                'mother_id': request.POST.get('mother_id', ''),
                'mother_name': request.POST.get('mother_name', ''),
                'father_id': request.POST.get('father_id', ''),
                'father_name': request.POST.get('father_name', ''),
                'sex': request.POST.get('sex', ''),
                'dob': request.POST.get('dob', ''),
                'philhealth_no': request.POST.get('philhealth_no', ''),
                'phone_number': request.POST.get('phone_number', ''),
            }
        })
    else:
        # Clear session data when starting new record
        if 'child_step4_data' in request.session:
            del request.session['child_step4_data']
    flash = get_flash(request)
    context.update({
        'message': flash['message'],
        'message_level': flash['message_level'],
    })
    return render(request, 'bhw_module/addchild1.html', context)

@custom_login_required
@role_required('Barangay Health Worker')
def addchild2(request):
    context = {}
    # Always get existing session data first
    existing_data = request.session.get('child_step4_data', {})
    
    if request.method == 'POST':
        # Check if child ID changed - clear session if different child selected
        current_child_id = request.POST.get('child_id', '')
        if current_child_id and existing_data.get('child_id') and current_child_id != existing_data.get('child_id'):
            existing_data = {}
            if 'child_step4_data' in request.session:
                del request.session['child_step4_data']
        
        # Check if this is form submission to go to step 3
        if request.POST.get('time_of_birth') is not None:
            # Store data in session before going to step 3, preserving step 3 data
            session_data = {
                'child_id': request.POST.get('child_id', '') or existing_data.get('child_id', ''),
                'child_name': request.POST.get('child_name', '') or existing_data.get('child_name', ''),
                'mother_id': request.POST.get('mother_id', '') or existing_data.get('mother_id', ''),
                'mother_name': request.POST.get('mother_name', '') or existing_data.get('mother_name', ''),
                'father_id': request.POST.get('father_id', '') or existing_data.get('father_id', ''),
                'father_name': request.POST.get('father_name', '') or existing_data.get('father_name', ''),
                'sex': request.POST.get('sex', '') or existing_data.get('sex', ''),
                'dob': request.POST.get('dob', '') or existing_data.get('dob', ''),
                'philhealth_no': request.POST.get('philhealth_no', '') or existing_data.get('philhealth_no', ''),
                'phone_number': request.POST.get('phone_number', '') or existing_data.get('phone_number', ''),
                'time_of_birth': request.POST.get('time_of_birth', ''),
                'birth_weight': request.POST.get('birth_weight', ''),
                'birth_height': request.POST.get('birth_height', ''),
                'place_of_delivery': request.POST.get('place_of_delivery', ''),
                # Preserve existing step 3 data
                'address_landmark': existing_data.get('address_landmark', ''),
                'tt_status_mother': existing_data.get('tt_status_mother', ''),
                'tt_status_date': existing_data.get('tt_status_date', ''),
                'newborn_screening': existing_data.get('newborn_screening', ''),
                'newborn_screening_date': existing_data.get('newborn_screening_date', ''),
                'feeding_method_id': existing_data.get('feeding_method_id', ''),
            }
            request.session['child_step4_data'] = session_data
            return redirect('/bhw_module/addchild3/')
        
        # Handle POST data from addchild1 or back navigation from addchild3
        # Merge POST data with existing session data, preserving step 3 data
        merged_data = {
            'child_id': request.POST.get('child_id', '') or existing_data.get('child_id', ''),
            'child_name': request.POST.get('child_name', '') or existing_data.get('child_name', ''),
            'mother_id': request.POST.get('mother_id', '') or existing_data.get('mother_id', ''),
            'mother_name': request.POST.get('mother_name', '') or existing_data.get('mother_name', ''),
            'father_id': request.POST.get('father_id', '') or existing_data.get('father_id', ''),
            'father_name': request.POST.get('father_name', '') or existing_data.get('father_name', ''),
            'sex': request.POST.get('sex', '') or existing_data.get('sex', ''),
            'dob': request.POST.get('dob', '') or existing_data.get('dob', ''),
            'philhealth_no': request.POST.get('philhealth_no', '') or existing_data.get('philhealth_no', ''),
            'phone_number': request.POST.get('phone_number', '') or existing_data.get('phone_number', ''),
            'time_of_birth': request.POST.get('time_of_birth', '') or existing_data.get('time_of_birth', ''),
            'birth_weight': request.POST.get('birth_weight', '') or existing_data.get('birth_weight', ''),
            'birth_height': request.POST.get('birth_height', '') or existing_data.get('birth_height', ''),
            'place_of_delivery': request.POST.get('place_of_delivery', '') or existing_data.get('place_of_delivery', ''),
            # Always preserve step 3 data
            'address_landmark': existing_data.get('address_landmark', ''),
            'tt_status_mother': existing_data.get('tt_status_mother', ''),
            'tt_status_date': existing_data.get('tt_status_date', ''),
            'newborn_screening': existing_data.get('newborn_screening', ''),
            'newborn_screening_date': existing_data.get('newborn_screening_date', ''),
            'feeding_method_id': existing_data.get('feeding_method_id', ''),
        }
        context.update({'child_data': merged_data})
    else:
        # Handle GET request - always use session data if available
        if existing_data:
            context.update({'child_data': existing_data})
    
    flash = get_flash(request)
    context.update({
        'message': flash['message'],
        'message_level': flash['message_level'],
    })
    return render(request, 'bhw_module/addchild2.html', context)

@custom_login_required
@role_required('Barangay Health Worker')
def addchild3(request):
    context = {}
    # Always get existing session data first
    existing_data = request.session.get('child_step4_data', {})
    
    if request.method == 'POST':
        # Check if this is just saving step 3 data (back navigation)
        if request.POST.get('save_step3_data'):
            session_data = {
                'child_id': request.POST.get('child_id', '') or existing_data.get('child_id', ''),
                'child_name': request.POST.get('child_name', '') or existing_data.get('child_name', ''),
                'mother_id': request.POST.get('mother_id', '') or existing_data.get('mother_id', ''),
                'mother_name': request.POST.get('mother_name', '') or existing_data.get('mother_name', ''),
                'father_id': request.POST.get('father_id', '') or existing_data.get('father_id', ''),
                'father_name': request.POST.get('father_name', '') or existing_data.get('father_name', ''),
                'sex': request.POST.get('sex', '') or existing_data.get('sex', ''),
                'dob': request.POST.get('dob', '') or existing_data.get('dob', ''),
                'philhealth_no': request.POST.get('philhealth_no', '') or existing_data.get('philhealth_no', ''),
                'phone_number': request.POST.get('phone_number', '') or existing_data.get('phone_number', ''),
                'time_of_birth': request.POST.get('time_of_birth', '') or existing_data.get('time_of_birth', ''),
                'birth_weight': request.POST.get('birth_weight', '') or existing_data.get('birth_weight', ''),
                'birth_height': request.POST.get('birth_height', '') or existing_data.get('birth_height', ''),
                'place_of_delivery': request.POST.get('place_of_delivery', '') or existing_data.get('place_of_delivery', ''),
                'address_landmark': request.POST.get('address_landmark', ''),
                'tt_status_mother': request.POST.get('tt_status_mother', ''),
                'tt_status_date': request.POST.get('tt_status_date', ''),
                'newborn_screening': request.POST.get('newborn_screening', ''),
                'newborn_screening_date': request.POST.get('newborn_screening_date', ''),
                'feeding_method_id': request.POST.get('feeding_method_id', ''),
            }
            request.session['child_step4_data'] = session_data
            return JsonResponse({'status': 'saved'})
        
        # Check if this is form submission to go to step 4 (review)
        if request.POST.get('address_landmark') is not None:
            # Update session data with current form data
            session_data = {
                'child_id': request.POST.get('child_id', '') or existing_data.get('child_id', ''),
                'child_name': request.POST.get('child_name', '') or existing_data.get('child_name', ''),
                'mother_id': request.POST.get('mother_id', '') or existing_data.get('mother_id', ''),
                'mother_name': request.POST.get('mother_name', '') or existing_data.get('mother_name', ''),
                'father_id': request.POST.get('father_id', '') or existing_data.get('father_id', ''),
                'father_name': request.POST.get('father_name', '') or existing_data.get('father_name', ''),
                'sex': request.POST.get('sex', '') or existing_data.get('sex', ''),
                'dob': request.POST.get('dob', '') or existing_data.get('dob', ''),
                'philhealth_no': request.POST.get('philhealth_no', '') or existing_data.get('philhealth_no', ''),
                'phone_number': request.POST.get('phone_number', '') or existing_data.get('phone_number', ''),
                'time_of_birth': request.POST.get('time_of_birth', '') or existing_data.get('time_of_birth', ''),
                'birth_weight': request.POST.get('birth_weight', '') or existing_data.get('birth_weight', ''),
                'birth_height': request.POST.get('birth_height', '') or existing_data.get('birth_height', ''),
                'place_of_delivery': request.POST.get('place_of_delivery', '') or existing_data.get('place_of_delivery', ''),
                'address_landmark': request.POST.get('address_landmark', ''),
                'tt_status_mother': request.POST.get('tt_status_mother', ''),
                'tt_status_date': request.POST.get('tt_status_date', ''),
                'newborn_screening': request.POST.get('newborn_screening', ''),
                'newborn_screening_date': request.POST.get('newborn_screening_date', ''),
                'feeding_method_id': request.POST.get('feeding_method_id', ''),
            }
            request.session['child_step4_data'] = session_data
            return redirect('/bhw_module/addchild4/')
        
        # Handle POST data from addchild2 or back navigation from addchild4
        # Merge POST data with existing session data
        merged_data = {
            'child_id': request.POST.get('child_id', '') or existing_data.get('child_id', ''),
            'child_name': request.POST.get('child_name', '') or existing_data.get('child_name', ''),
            'mother_id': request.POST.get('mother_id', '') or existing_data.get('mother_id', ''),
            'mother_name': request.POST.get('mother_name', '') or existing_data.get('mother_name', ''),
            'father_id': request.POST.get('father_id', '') or existing_data.get('father_id', ''),
            'father_name': request.POST.get('father_name', '') or existing_data.get('father_name', ''),
            'sex': request.POST.get('sex', '') or existing_data.get('sex', ''),
            'dob': request.POST.get('dob', '') or existing_data.get('dob', ''),
            'philhealth_no': request.POST.get('philhealth_no', '') or existing_data.get('philhealth_no', ''),
            'phone_number': request.POST.get('phone_number', '') or existing_data.get('phone_number', ''),
            'time_of_birth': request.POST.get('time_of_birth', '') or existing_data.get('time_of_birth', ''),
            'birth_weight': request.POST.get('birth_weight', '') or existing_data.get('birth_weight', ''),
            'birth_height': request.POST.get('birth_height', '') or existing_data.get('birth_height', ''),
            'place_of_delivery': request.POST.get('place_of_delivery', '') or existing_data.get('place_of_delivery', ''),
            'address_landmark': request.POST.get('address_landmark', '') or existing_data.get('address_landmark', ''),
            'tt_status_mother': request.POST.get('tt_status_mother', '') or existing_data.get('tt_status_mother', ''),
            'tt_status_date': request.POST.get('tt_status_date', '') or existing_data.get('tt_status_date', ''),
            'newborn_screening': request.POST.get('newborn_screening', '') or existing_data.get('newborn_screening', ''),
            'newborn_screening_date': request.POST.get('newborn_screening_date', '') or existing_data.get('newborn_screening_date', ''),
            'feeding_method_id': request.POST.get('feeding_method_id', '') or existing_data.get('feeding_method_id', ''),
        }
        context.update({'child_data': merged_data})
    else:
        # Handle GET request - always use session data if available
        if existing_data:
            context.update({'child_data': existing_data})
    
    flash = get_flash(request)
    context.update({
        'message': flash['message'],
        'message_level': flash['message_level'],
    })
    return render(request, 'bhw_module/addchild3.html', context)

@custom_login_required
@role_required('Barangay Health Worker')
def addchild4(request):
    context = {}
    
    # Always get data from session
    child_data = request.session.get('child_step4_data', {})
    context['child_data'] = child_data
    
    if request.method == 'POST':
        # Handle final submission
        if 'submit_final' in request.POST:
            try:
                # Get and validate data from session (not POST)
                child_id = int(child_data.get('child_id', 0))
                time_of_birth = child_data.get('time_of_birth', '').strip() or None
                
                # Convert numeric fields
                birth_weight_str = child_data.get('birth_weight', '').strip()
                birth_weight = float(birth_weight_str) if birth_weight_str else None
                
                birth_height_str = child_data.get('birth_height', '').strip()
                birth_height = float(birth_height_str) if birth_height_str else None
                
                place_of_delivery = child_data.get('place_of_delivery', '').strip() or None
                address_landmark = child_data.get('address_landmark', '').strip() or None
                
                # Convert TT status to integer
                tt_status_str = child_data.get('tt_status_mother', '').strip()
                tt_status_mother = int(tt_status_str) if tt_status_str else None
                
                # Convert date fields
                tt_status_date_str = child_data.get('tt_status_date', '').strip()
                tt_status_date = tt_status_date_str if tt_status_date_str else None
                
                # Convert boolean field
                newborn_screening_str = child_data.get('newborn_screening', '').strip()
                newborn_screening_status = newborn_screening_str == 'true' if newborn_screening_str else None
                
                # Convert screening date
                screening_date_str = child_data.get('newborn_screening_date', '').strip()
                newborn_screening_status_date = screening_date_str if screening_date_str else None
                
                # Convert feeding method ID
                feeding_method_str = child_data.get('feeding_method_id', '').strip()
                feeding_method_id = int(feeding_method_str) if feeding_method_str else None
                
                pid = int(request.session.get('personnel_id') or 0)
                
                # Validate required fields
                if not child_id:
                    raise ValueError("Child ID is required")
                if not pid:
                    raise ValueError("Personnel ID is required")
                if not address_landmark:
                    raise ValueError("Address with Landmark is required")
                
                result = Child.sp_insert_child_health_record(
                    child_id=child_id,
                    time_of_birth=time_of_birth,
                    birth_weight=birth_weight,
                    birth_height=birth_height,
                    place_of_delivery=place_of_delivery,
                    address_landmark=address_landmark,
                    tt_status_mother=tt_status_mother,
                    tt_status_date=tt_status_date,
                    newborn_screening_status=newborn_screening_status,
                    newborn_screening_date=newborn_screening_status_date,
                    feeding_method=feeding_method_id,
                    pid=pid,
                )
                msg = coerce_message(result, "Child Record successfully added.")
                set_flash(request, msg, 'success')
                # Clear session data after successful submission
                if 'child_step4_data' in request.session:
                    del request.session['child_step4_data']
                return redirect('bhw_module:childList')
            except ValueError as e:
                set_flash(request, _clean_db_error(e), "error")
            except Exception as e:
                msg = _clean_db_error(e)
                set_flash(request, msg, "error")
    
    flash = get_flash(request)
    context.update({
        'message': flash['message'],
        'message_level': flash['message_level'],
    })
    return render(request, 'bhw_module/addchild4.html', context)

@custom_login_required
@role_required('Barangay Health Worker')
@require_POST
def add_medical_condition(request):
    child_health_id = request.POST.get('child_health_id')
    pid = int(request.session.get('personnel_id') or 0)
    medical_condition = request.POST.get('medical_condition_name', '').strip()
    
    def redirect_to_view():
        return redirect(f'/bhw_module/childView/?child_health_id={child_health_id}') if child_health_id else redirect('bhw_module:childList')
    
    if not pid:
        set_flash(request, "Missing personnel id.", "error")
        return redirect('bhw_module:childList')
    
    if not child_health_id:
        set_flash(request, "Missing child health record ID.", "error")
        return redirect('bhw_module:childList')
    
    if not medical_condition:
        set_flash(request, "Medical condition name is required.", "error")
        return redirect_to_view()
    
    try:
        Child.sp_add_child_medical_condition(
            child_health_id=child_health_id,
            medical_condition=medical_condition,
            pid=pid
        )
        set_flash(request, "Medical condition added successfully.", "success")
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")
    
    return redirect_to_view()

@custom_login_required
@role_required('Barangay Health Worker')
@require_POST
def add_surgical_history(request):
    child_health_id = request.POST.get('child_health_id')
    pid = int(request.session.get('personnel_id') or 0)
    surgical_history_name = request.POST.get('surgical_history_name', '').strip()
    date_of_surgery = request.POST.get('date_of_surgery', '').strip()
    
    def redirect_to_view():
        return redirect(f'/bhw_module/childView/?child_health_id={child_health_id}') if child_health_id else redirect('bhw_module:childList')
    
    if not pid:
        set_flash(request, "Missing personnel id.", "error")
        return redirect('bhw_module:childList')
    
    if not child_health_id:
        set_flash(request, "Missing child health record ID.", "error")
        return redirect('bhw_module:childList')
    
    if not surgical_history_name:
        set_flash(request, "Surgical history name is required.", "error")
        return redirect_to_view()
    
    if not date_of_surgery:
        set_flash(request, "Date of surgery is required.", "error")
        return redirect_to_view()
    
    try:
        Child.sp_add_child_surgical_history(
            child_health_id=child_health_id,
            surgical_history_name=surgical_history_name,
            date_of_surgery=date_of_surgery,
            pid=pid
        )
        set_flash(request, "Surgical history added successfully.", "success")
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")
    
    return redirect_to_view()

@custom_login_required
@role_required('Barangay Health Worker')
@require_POST
def add_child_growth_monitoring(request):
    child_health_id = request.POST.get('child_health_id')
    pid = int(request.session.get('personnel_id') or 0)
    
    def redirect_to_view():
        return redirect(f'/bhw_module/childView/?child_health_id={child_health_id}') if child_health_id else redirect('bhw_module:childList')
    
    if not pid:
        set_flash(request, "Missing personnel id.", "error")
        return redirect('bhw_module:childList')
    
    if not child_health_id:
        set_flash(request, "Missing child health record ID.", "error")
        return redirect('bhw_module:childList')
    
    try:
        Child.sp_add_child_growth_monitoring(
            child_health_id=child_health_id,
            weight_kg=float(request.POST.get('weight_kg')),
            height_cm=float(request.POST.get('height_cm')),
            temp_c=float(request.POST.get('temp_c')),
            resp_rate=int(request.POST.get('resp_rate')),
            pulse_rate=int(request.POST.get('pulse_rate')),
            notes=request.POST.get('notes', '').strip() or None,
            pid=pid
        )
        set_flash(request, "Growth monitoring record added successfully.", "success")
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")
    
    return redirect_to_view()

@custom_login_required
@role_required('Barangay Health Worker')
@require_POST
def add_child_supplement(request):
    child_health_id = request.POST.get('child_health_id')
    pid = int(request.session.get('personnel_id') or 0)
    supplement_id = request.POST.get('supplement_id')
    age_in_months = request.POST.get('age_in_months')
    
    def redirect_to_view():
        return redirect(f'/bhw_module/childView/?child_health_id={child_health_id}') if child_health_id else redirect('bhw_module:childList')
    
    if not pid:
        set_flash(request, "Missing personnel id.", "error")
        return redirect('bhw_module:childList')
    
    if not child_health_id:
        set_flash(request, "Missing child health record ID.", "error")
        return redirect('bhw_module:childList')
    
    if not supplement_id:
        set_flash(request, "Supplement type is required.", "error")
        return redirect_to_view()
    
    if not age_in_months:
        set_flash(request, "Age in months is required.", "error")
        return redirect_to_view()
    
    try:
        Child.sp_add_child_supplement(
            child_health_id=child_health_id,
            supplement_id=int(supplement_id),
            age_in_months=int(age_in_months),
            pid=pid
        )
        set_flash(request, "Supplement added successfully.", "success")
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")
    
    return redirect_to_view()

@custom_login_required
@role_required('Barangay Health Worker')
@require_POST
def update_child_health_record(request):
    child_health_id = request.POST.get('child_health_id')
    pid = int(request.session.get('personnel_id') or 0)
    
    def redirect_to_view():
        return redirect(f'/bhw_module/childView/?child_health_id={child_health_id}') if child_health_id else redirect('bhw_module:childList')
    
    if not pid:
        set_flash(request, "Missing personnel id.", "error")
        return redirect('bhw_module:childList')
    
    if not child_health_id:
        set_flash(request, "Missing child health record ID.", "error")
        return redirect('bhw_module:childList')
    
    # Get current record for comparison
    try:
        prev = Child.sp_view_specific_child_health_record(child_health_id)
        if not prev:
            set_flash(request, "Child health record not found.", "error")
            return redirect('bhw_module:childList')
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")
        return redirect('bhw_module:childList')
    
    # Current values
    curr_place = (prev.get('place_of_delivery') or '').strip()
    curr_address = (prev.get('address_landmark') or '').strip()
    curr_tt_status = prev.get('tt_status_id')
    curr_tt_date = prev.get('tt_status_date')
    curr_screening = prev.get('newborn_screening_status')
    curr_screening_date = prev.get('newborn_screening_status_date')
    curr_feeding = prev.get('feeding_method_id')
    
    # New values
    new_place = (request.POST.get('place_of_delivery', '').strip() or '').strip()
    new_address = (request.POST.get('address_landmark', '').strip() or '').strip()
    new_tt_status = int(request.POST.get('tt_status_of_mother')) if request.POST.get('tt_status_of_mother') else None
    new_tt_date = request.POST.get('tt_status_date', '').strip() or None
    new_screening = request.POST.get('newborn_screening_status') == 'true' if request.POST.get('newborn_screening_status') else None
    new_screening_date = request.POST.get('newborn_screening_status_date', '').strip() or None
    new_feeding = int(request.POST.get('feeding_method_id')) if request.POST.get('feeding_method_id') else None
    
    # Compare changes
    changed = []
    if new_place != curr_place: changed.append("Place of delivery")
    if new_address != curr_address: changed.append("Address with landmark")
    if new_tt_status != curr_tt_status: changed.append("TT status of mother")
    if str(new_tt_date or '') != str(curr_tt_date or ''): changed.append("TT status date")
    if new_screening != curr_screening: changed.append("Newborn screening status")
    if str(new_screening_date or '') != str(curr_screening_date or ''): changed.append("Screening date")
    if new_feeding != curr_feeding: changed.append("Feeding method")
    
    if not changed:
        set_flash(request, "No changes detected — nothing to update.", "info")
        return redirect_to_view()
    
    try:
        Child.sp_update_child_health_record(
            child_health_id=child_health_id,
            place_of_delivery=new_place or None,
            address_landmark=new_address or None,
            tt_status_of_mother=new_tt_status,
            tt_status_date=new_tt_date,
            newborn_screening_status=new_screening,
            newborn_screening_status_date=new_screening_date,
            feeding_method_id=new_feeding,
            updated_by=pid
        )
        set_flash(request, f"Child health record updated successfully. Changed: {', '.join(changed)}.", "success")
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")
    
    return redirect_to_view()

@custom_login_required
@role_required('Barangay Health Worker')
def childView(request):
    child_health_id = request.POST.get('child_health_id') or request.GET.get('child_health_id')
    result = None
    medical_result = []
    surgical_result = []
    immunization_result = []
    supplement_result = []
    
    try:
        result = Child.sp_view_specific_child_health_record(child_health_id)
        medical_data = Child.sp_view_specific_child_all_medical_condition(child_health_id)
        surgical_data = Child.sp_view_specific_child_all_surgical_history(child_health_id)
        immunization_data = Child.sp_view_specific_child_immunization_record(child_health_id)
        supplement_data = Child.sp_view_all_child_supplements(child_health_id)
        growth_data = Child.sp_view_specific_child_all_growth_monitoring(child_health_id)
        breastfeed_data = Child.sp_view_specific_child_exclusive_breastfeed_track(child_health_id)
        
        medical_result = medical_data if medical_data else []
        surgical_result = surgical_data if surgical_data else []
        immunization_result = immunization_data if immunization_data else []
        supplement_result = supplement_data if supplement_data else []
        growth_result = growth_data if growth_data else []
        breastfeed_result = breastfeed_data if breastfeed_data else []
        
        # Calculate growth trends for the template
        growth_trends = {}
        if len(growth_result) >= 2:
            sorted_growth = sorted(growth_result, key=lambda x: (x.get('date_of_visit', ''), x.get('created_at', '')), reverse=True)
            latest = sorted_growth[0]
            previous = sorted_growth[1]
            
            latest_weight = float(latest.get('weight_kg', 0))
            latest_height = float(latest.get('height_cm', 0))
            previous_weight = float(previous.get('weight_kg', 0))
            previous_height = float(previous.get('height_cm', 0))
            
            weight_diff = latest_weight - previous_weight
            height_diff = latest_height - previous_height
            
            growth_trends = {
                'weight_change': weight_diff,
                'height_change': height_diff,
                'latest_values': latest,
                'previous_values': previous,
                'has_weight_change': abs(weight_diff) > 0.01,
                'has_height_change': abs(height_diff) > 0.01
            }
        
        if not result:
            set_flash(request, "Child Record not found.", "error")
            return redirect('bhw_module:childList')
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")
        return redirect('bhw_module:childList')
    
    # Get supplements list for dropdown
    supplements = []
    try:
        supplements = Child.sp_get_supplements()
    except Exception as e:
        pass  # Continue without supplements if there's an error
    
    flash = get_flash(request)
    
    return render(request, 'bhw_module/childView.html', {
        "results": result,
        "medical_results": medical_result,
        "surgical_results": surgical_result,
        "immunization_results": immunization_result,
        "supplement_results": supplement_result,
        "growth_results": growth_result,
        "growth_trends": growth_trends,
        "breastfeed_results": breastfeed_result,
        "supplements": supplements,
        "message": flash['message'],
        "message_level": flash['message_level'],
    })

@custom_login_required
@role_required('Barangay Health Worker')
def genInfo(request):
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
    return render(request, 'bhw_module/genInfo.html', {
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
@role_required('Barangay Health Worker')
def maternalList(request):
    limit = None
    offset = None
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
    
    offset = (page - 1) * limit
    
    try:
        results = Maternal.sp_view_all_maternal_record(
            name_query=query,
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

    prev_url = "?" + urlencode({**base_params, "page": page - 1}) if has_prev else ""
    next_url = "?" + urlencode({**base_params, "page": page + 1}) if has_next else ""
    limit_urls = {n: "?" + urlencode({**base_params, "limit": n, "page": 1}) for n in LIMIT_OPTIONS}
    
    flash = get_flash(request)
    return render(request, 'bhw_module/maternalList.html', {
        "results": final_result,
        "limit": limit,
        "page": page,
        "has_prev": has_prev,
        "has_next": has_next,
        "prev_url": prev_url,
        "next_url": next_url,
        "limit_options": LIMIT_OPTIONS,
        "limit_urls": limit_urls,
        'query': query,
        'message': flash['message'],
        'message_level': flash['message_level'],
    })

@custom_login_required
@role_required('Barangay Health Worker')
def maternalAdd(request):
    context = {}
    if request.method == 'POST':
        try:
            maternal_id = int(request.POST.get('maternal_id', 0))
            address_landmark = request.POST.get('address_landmark', '').strip()
            pid = int(request.session.get('personnel_id') or 0)
            
            if not maternal_id:
                raise ValueError("Maternal ID is required")
            if not pid:
                raise ValueError("Personnel ID is required")
            if not address_landmark:
                raise ValueError("Address with Landmark is required")
            
            result = Maternal.sp_insert_maternal(
                maternal_id=maternal_id,
                address_landmark=address_landmark,
                created_by=pid,
            )
            msg = coerce_message(result, "Maternal Record successfully added.")
            set_flash(request, msg, 'success')
            return redirect('bhw_module:maternalList')
        except ValueError as e:
            set_flash(request, _clean_db_error(e), "error")
        except Exception as e:
            msg = _clean_db_error(e)
            set_flash(request, msg, "error")
    
    flash = get_flash(request)
    context.update({
        'message': flash['message'],
        'message_level': flash['message_level'],
    })
    return render(request, 'bhw_module/maternalAdd.html', context)

@custom_login_required
@role_required('Barangay Health Worker')
def maternalView(request):
    maternal_health_id = request.POST.get('maternal_health_id') or request.GET.get('maternal_health_id')
    result = None
    
    try:
        result = Maternal.sp_view_specific_maternal_health_record(maternal_health_id)
        obstetrical_data = Maternal.sp_view_obstetrical_history(maternal_health_id)
        medical_conditions = Maternal.sp_view_specific_maternal_all_medical_condition(maternal_health_id)
        surgical_history = Maternal.sp_view_specific_maternal_all_surgical_history(maternal_health_id)
        immunization_data = Maternal.sp_view_specific_maternal_immunization_status_track(maternal_health_id)
        
        # Get last gravida and abortion for validation
        last_gravida = 0
        last_abortion = 0
        if result and result.get('maternal_id'):
            last_gravida = Maternal.sp_get_last_completed_gravida(result.get('maternal_id'))
            last_abortion = Maternal.sp_get_last_completed_abortion(result.get('maternal_id'))
        
        if not result:
            set_flash(request, "Maternal Record not found.", "error")
            return redirect('bhw_module:maternalList')
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")
        return redirect('bhw_module:maternalList')
    
    flash = get_flash(request)
    
    # Get disease surveillance data
    disease_surveillance_data = []
    try:
        disease_surveillance_data = Maternal.sp_view_specific_maternal_all_disease_surveillance(maternal_health_id)
    except Exception as e:
        pass  # Continue without disease surveillance data if there's an error
    
    # Get disease types for dropdown
    disease_types = []
    try:
        disease_types = Maternal.sp_get_disease_types()
    except Exception as e:
        pass  # Continue without disease types if there's an error
    
    return render(request, 'bhw_module/maternalView.html', {
        "results": result,
        "obstetrical_data": obstetrical_data,
        "medical_conditions": medical_conditions or [],
        "surgical_history": surgical_history or [],
        "immunization_data": immunization_data,
        "disease_surveillance_data": disease_surveillance_data,
        "disease_types": disease_types,
        "last_gravida": last_gravida,
        "last_abortion": last_abortion,
        "message": flash['message'],
        "message_level": flash['message_level'],
    })

@custom_login_required
@role_required('Barangay Health Worker')
def add_obstetrical_history(request):
    maternal_health_id = request.POST.get('maternal_health_id')
    pid = int(request.session.get('personnel_id') or 0)
    
    def redirect_to_view():
        return redirect(f'/bhw_module/maternalView/?maternal_health_id={maternal_health_id}') if maternal_health_id else redirect('bhw_module:maternalList')
    
    if request.method == 'POST':
        try:
            maternal_health_id = int(request.POST.get('maternal_health_id', 0))
            gravida = int(request.POST.get('gravida', 0))
            para = int(request.POST.get('para', 0))
            abortion = int(request.POST.get('abortion', 0))
            last_menstrual_period = request.POST.get('last_menstrual_period')
            expected_date_of_delivery = request.POST.get('expected_date_of_delivery')
            
            if not maternal_health_id:
                raise ValueError("Maternal Health ID is required")
            if not pid:
                raise ValueError("Personnel ID is required")
            
            # Get maternal record to find maternal_id
            maternal_record = Maternal.sp_view_specific_maternal_health_record(maternal_health_id)
            if not maternal_record:
                raise ValueError("Maternal record not found")
            
            maternal_id = maternal_record.get('maternal_id')
            if not maternal_id:
                raise ValueError("Maternal ID not found in record")
            
            # Check gravida restriction - new record must have higher gravida
            last_gravida = Maternal.sp_get_last_completed_gravida(maternal_id)
            if gravida <= last_gravida:
                raise ValueError(f"Gravida must be greater than {last_gravida} (based on previous record)")
            
            # Check abortion restriction - new record must have >= abortion count
            last_abortion = Maternal.sp_get_last_completed_abortion(maternal_id)
            if abortion < last_abortion:
                raise ValueError(f"Abortion count must be greater than or equal to {last_abortion} (based on previous record)")
            
            result = Maternal.sp_add_obstetrical_history(
                maternal_health_id=maternal_health_id,
                gravida=gravida,
                para=para,
                aborption=abortion,
                last_menstrual_period=last_menstrual_period,
                expected_date_of_delivery=expected_date_of_delivery,
                pid=pid
            )
            
            msg = coerce_message(result, "Obstetrical history successfully added.")
            set_flash(request, msg, 'success')
            
        except ValueError as e:
            set_flash(request, str(e), "error")
        except Exception as e:
            msg = _clean_db_error(e)
            set_flash(request, msg, "error")
    
    return redirect_to_view()

@custom_login_required
@role_required('Barangay Health Worker')
@require_POST
def add_maternal_medical_condition(request):
    maternal_health_id = request.POST.get('maternal_health_id')
    pid = int(request.session.get('personnel_id') or 0)
    medical_condition_name = request.POST.get('medical_condition_name', '').strip()
    
    def redirect_to_view():
        return redirect(f'/bhw_module/maternalView/?maternal_health_id={maternal_health_id}') if maternal_health_id else redirect('bhw_module:maternalList')
    
    if not pid:
        set_flash(request, "Missing personnel id.", "error")
        return redirect('bhw_module:maternalList')
    
    if not maternal_health_id:
        set_flash(request, "Missing maternal health record ID.", "error")
        return redirect('bhw_module:maternalList')
    
    if not medical_condition_name:
        set_flash(request, "Medical condition name is required.", "error")
        return redirect_to_view()
    
    try:
        Maternal.sp_add_maternal_medical_condition(
            maternal_health_id=maternal_health_id,
            medical_condition_name=medical_condition_name,
            pid=pid
        )
        set_flash(request, "Medical condition added successfully.", "success")
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")
    
    return redirect_to_view()

@custom_login_required
@role_required('Barangay Health Worker')
@require_POST
def add_maternal_surgical_history(request):
    maternal_health_id = request.POST.get('maternal_health_id')
    pid = int(request.session.get('personnel_id') or 0)
    surgical_history_name = request.POST.get('surgical_history_name', '').strip()
    date_of_surgery = request.POST.get('date_of_surgery', '').strip()
    
    def redirect_to_view():
        return redirect(f'/bhw_module/maternalView/?maternal_health_id={maternal_health_id}') if maternal_health_id else redirect('bhw_module:maternalList')
    
    if not pid:
        set_flash(request, "Missing personnel id.", "error")
        return redirect('bhw_module:maternalList')
    
    if not maternal_health_id:
        set_flash(request, "Missing maternal health record ID.", "error")
        return redirect('bhw_module:maternalList')
    
    if not surgical_history_name:
        set_flash(request, "Surgical history name is required.", "error")
        return redirect_to_view()
    
    if not date_of_surgery:
        set_flash(request, "Date of surgery is required.", "error")
        return redirect_to_view()
    
    try:
        Maternal.sp_add_maternal_surgical_history(
            maternal_health_id=maternal_health_id,
            surgical_history_name=surgical_history_name,
            date_of_surgery=date_of_surgery,
            pid=pid
        )
        set_flash(request, "Surgical history added successfully.", "success")
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")
    
    return redirect_to_view()

@custom_login_required
@role_required('Barangay Health Worker')
@require_POST
def add_maternal_immunization(request):
    maternal_health_id = request.POST.get('maternal_health_id')
    pid = int(request.session.get('personnel_id') or 0)
    dose_number = request.POST.get('dose_number')
    date_given = request.POST.get('date_given', '').strip()
    
    def redirect_to_view():
        return redirect(f'/bhw_module/maternalView/?maternal_health_id={maternal_health_id}') if maternal_health_id else redirect('bhw_module:maternalList')
    
    if not pid:
        set_flash(request, "Missing personnel id.", "error")
        return redirect('bhw_module:maternalList')
    
    if not maternal_health_id:
        set_flash(request, "Missing maternal health record ID.", "error")
        return redirect('bhw_module:maternalList')
    
    if not dose_number:
        set_flash(request, "Dose number is required.", "error")
        return redirect_to_view()
    
    if not date_given:
        set_flash(request, "Date given is required.", "error")
        return redirect_to_view()
    
    try:
        Maternal.sp_add_maternal_immunization(
            maternal_health_id=maternal_health_id,
            dose_number=int(dose_number),
            date_given=date_given,
            pid=pid
        )
        set_flash(request, f"Dose {dose_number} immunization added successfully.", "success")
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")
    
    return redirect_to_view()

@custom_login_required
@role_required('Barangay Health Worker')
@require_POST
def add_disease_screening(request):
    maternal_health_id = request.POST.get('maternal_health_id')
    pid = int(request.session.get('personnel_id') or 0)
    disease_type_id = request.POST.get('disease_type_id')
    screening_date = request.POST.get('screening_date', '').strip()
    result = request.POST.get('result', '').strip()
    
    def redirect_to_view():
        return redirect(f'/bhw_module/maternalView/?maternal_health_id={maternal_health_id}') if maternal_health_id else redirect('bhw_module:maternalList')
    
    if not pid:
        set_flash(request, "Missing personnel id.", "error")
        return redirect('bhw_module:maternalList')
    
    if not maternal_health_id:
        set_flash(request, "Missing maternal health record ID.", "error")
        return redirect('bhw_module:maternalList')
    
    if not disease_type_id:
        set_flash(request, "Disease type is required.", "error")
        return redirect_to_view()
    
    if not screening_date:
        set_flash(request, "Screening date is required.", "error")
        return redirect_to_view()
    
    try:
        Maternal.sp_add_disease_screen_record(
            maternal_health_id=maternal_health_id,
            disease_type_id=int(disease_type_id),
            screening_date=screening_date,
            result=result or None,
            pid=pid
        )
        set_flash(request, "Disease screening record added successfully.", "success")
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")
    
    return redirect_to_view()

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
        return JsonResponse({'error': _clean_db_error(e)}, status=500)
    
@custom_login_required
@role_required('Barangay Health Worker')
@require_GET
def child_search_api(request):
    q = (request.GET.get('q') or '').strip()
    if not q:
        return JsonResponse({'results': []})

    try:
        # Call your search_child() SQL function
        with connection.cursor() as cursor:
            cursor.callproc("search_child", [q])
            cols = [col[0] for col in cursor.description]
            raw_rows = [dict(zip(cols, row)) for row in cursor.fetchall()]

        # Normalize / whitelist fields for the frontend
        normalized = []
        for r in raw_rows:
            normalized.append({
                'child_resident_id': r.get('child_resident_id'),
                'full_name': r.get('child_full_name') or '',
                'sex': r.get('sex') or '',
                'dob': r.get('dob').isoformat() if r.get('dob') else '',
                'family_code': r.get('family_code') or '',
                'address': r.get('complete_address') or '',

                'mother_resident_id': r.get('mother_resident_id'),
                'mother_full_name': r.get('mother_full_name') or '',

                'father_resident_id': r.get('father_resident_id'),
                'father_full_name': r.get('father_full_name') or '',

                'guardian_resident_id': r.get('guardian_resident_id'),
                'guardian_full_name': r.get('guardian_full_name') or '',

                'philhealth_no': r.get('philhealth_no') or '',
                'phone_number': r.get('phone_number') or '',
            })

        return JsonResponse({'results': normalized})

    except Exception as e:
        return JsonResponse({'error': _clean_db_error(e)}, status=500)

@custom_login_required
@role_required('Barangay Health Worker')
@require_POST
def add_exclusive_breastfeed(request):
    child_health_id = request.POST.get('child_health_id')
    pid = int(request.session.get('personnel_id') or 0)
    month_id = request.POST.get('month_id')
    
    def redirect_to_view():
        return redirect(f'/bhw_module/childView/?child_health_id={child_health_id}') if child_health_id else redirect('bhw_module:childList')
    
    if not pid:
        set_flash(request, "Missing personnel id.", "error")
        return redirect('bhw_module:childList')
    
    if not child_health_id:
        set_flash(request, "Missing child health record ID.", "error")
        return redirect('bhw_module:childList')
    
    if not month_id:
        set_flash(request, "Assessment month is required.", "error")
        return redirect_to_view()
    
    try:
        Child.sp_add_exclusive_breastfeed_backfill(
            child_health_id=child_health_id,
            month_id=int(month_id),
            pid=pid
        )
        set_flash(request, "Exclusive breastfeeding assessment added successfully.", "success")
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")
    
    return redirect_to_view()

@custom_login_required
@role_required('Barangay Health Worker')
@require_GET
def mother_search_api(request):
    q = (request.GET.get('q') or '').strip()
    if not q:
        return JsonResponse({'results': []})
    
    try:
        # Call Search_mother() SQL function
        with connection.cursor() as cursor:
            cursor.callproc("search_mother", [q])
            cols = [col[0] for col in cursor.description]
            raw_rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
        
        normalized = []
        for r in raw_rows:
            normalized.append({
                'maternal_id': r.get('maternal_id'),
                'full_name': r.get('full_name') or '',
                'dob': r.get('dob').isoformat() if r.get('dob') else '',
                'age_years': r.get('age_years') or 0,
                'family_code': r.get('family_code') or '',
                'nhts_status': r.get('nhts_status'),
                'complete_address': r.get('complete_address') or '',
                'phone_number': r.get('phone_number') or '',
            })
        return JsonResponse({'results': normalized})
    except Exception as e:
        return JsonResponse({'error': _clean_db_error(e)}, status=500)
    
# ===========================================================================================
# HOUSEHOLD PDF GENERATION VIEWS FOR BHW MODULE
# ===========================================================================================
@custom_login_required
@role_required('Barangay Health Worker')
@require_GET
def generate_household_list_pdf(request):
    '''
    Generate PDF report for household list with applied filters
    '''
    import traceback
    from datetime import datetime
    from django.http import HttpResponse
    from reports_module.pdf_templates.household.household_list_filtered import HouseholdListFilteredPDF
    
    try:
        # Get filter parameters from query string
        query = request.GET.get('query', '').strip() or None
        status = request.GET.get('status', 'all').strip()
        sitio_id = request.GET.get('sitio_id', '').strip() or None
        quarter_id = request.GET.get('quarter_id', '').strip() or None
        
        # Generate PDF using the report utility
        pdf_generator = HouseholdListFilteredPDF(
            query=query,
            status=status,
            sitio_id=sitio_id,
            quarter_id=quarter_id
        )
        
        pdf_buffer = pdf_generator.generate()
        
        # Create HTTP response with PDF
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        response['Content-Disposition'] = f'inline; filename="household_list_{timestamp}.pdf"'
        
        return response
    
    except Exception as e:
        # Log the error with full traceback
        print(f"Error generating household list PDF: {str(e)}")
        print(traceback.format_exc())
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)

@custom_login_required
@role_required('Barangay Health Worker')
@require_GET
def generate_household_detail_pdf(request, household_id: int):
    '''
    Generate PDF report for specific household details
    '''
    import traceback
    from datetime import datetime
    from django.http import HttpResponse
    from reports_module.pdf_templates.household.household_detail import HouseholdDetailPDF
    
    try:
        quarter_id = request.GET.get('quarter_id', '').strip() or None
        
        # Generate PDF using the report utility
        pdf_generator = HouseholdDetailPDF(
            household_id=household_id,
            quarter_id=quarter_id
        )
        
        pdf_buffer = pdf_generator.generate()
        
        # Create HTTP response with PDF
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        response['Content-Disposition'] = f'inline; filename="household_{household_id}_{timestamp}.pdf"'
        
        return response
    
    except Exception as e:
        # Log the error with full traceback
        print(f"Error generating household detail PDF: {str(e)}")
        print(traceback.format_exc())
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)
