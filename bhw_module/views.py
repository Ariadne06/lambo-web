from django.shortcuts import render, redirect
from authentication.decorators import custom_login_required, role_required
from django.contrib import messages
from django.db import connection
from .models import Dashboard, AnnouncementRepo, Child
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
        set_flash(request, _clean_db_error(e) if ' _clean_db_error' in globals() else str(e), "error")
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
        set_flash(request, _clean_db_error(e) if ' _clean_db_error' in globals() else str(e), "error")

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
            cursor.execute("SELECT * FROM search_child(%s)", [q])
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
        return JsonResponse({'error': str(e)}, status=500)