from django.shortcuts import render
from authentication.decorators import custom_login_required, role_required
from django.contrib import messages
from django.db import connection
from .models import Dashboard, AnnouncementRepo, ResidentList, Household, QuarterCatalog, HouseholdDetail, HouseholdFamilies
from datetime import datetime
from typing import Optional, Dict, Any
from django.shortcuts import render
from django.utils.http import urlencode
from django.utils.http import url_has_allowed_host_and_scheme
from django.http import Http404
from django.views.decorators.http import require_GET
from utils.constants import LIMIT_OPTIONS
from utils.flash import set_flash, get_flash
from utils.db_message import _clean_db_error, _clean_params, coerce_message
from household_module.models import Household, Family




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
    q          = request.GET.get("q") or None
    barangay   = request.GET.get("barangay") or None
    sitio_id   = request.GET.get("sitio_id")
    status     = (request.GET.get("status") or "all").lower()
    quarter_id = request.GET.get("quarter_id")
    page       = int(request.GET.get("page", "1"))
    page_size  = int(request.GET.get("page_size", "10"))

    try:
        sitio_id_val = int(sitio_id) if sitio_id not in (None, "", "null") else None
    except ValueError:
        sitio_id_val = None

    try:
        quarter_id_val = int(quarter_id) if quarter_id not in (None, "", "null") else None
    except ValueError:
        quarter_id_val = None

    limit = max(1, page_size)
    offset = max(0, (page - 1) * limit)

    rows, meta = Household.get_all_households(
        q=q,
        barangay=barangay,
        sitio_id=sitio_id_val,
        status=status,
        quarter_id=quarter_id_val,
        limit=limit,
        offset=offset
    )

    base_qs = {k: v for k, v in {
        "q": q,
        "barangay": barangay,
        "sitio_id": sitio_id,
        "status": status,
        "quarter_id": quarter_id,
        "page_size": page_size,
    }.items() if v not in (None, "", "null")}

    def page_url(p):
        qs = base_qs.copy()
        qs["page"] = p
        return f"?{urlencode(qs)}"

    # New: quarters with display labels
    curr_qid   = QuarterCatalog.get_current_quarter_id()
    quarters   = QuarterCatalog.get_all_quarters()

    context = {
        "rows": rows,
        "page": page,
        "page_size": page_size,
        "page_sizes": [10, 25, 50, 100],   # for the rows-per-page select (if you use it)
        "has_prev": meta["has_prev"] and page > 1,
        "has_next": meta["has_next"],
        "prev_url": page_url(max(1, page - 1)),
        "next_url": page_url(page + 1),
        "quarters": quarters,              # <-- list of QuarterOption
        "current_quarter_id": curr_qid,    # optional if you want to highlight
        "selected_quarter_id": quarter_id_val,
        "q": q,
    }
    return render(request, "nurse_module/nurse_household.html", context)


@custom_login_required
@role_required('Midwife')
def nurse_household_more(request, household_id: int):
    raw_q = request.GET.get("quarter_id")
    try:
        selected_qid = int(raw_q) if raw_q not in (None, "", "null") else None
    except ValueError:
        selected_qid = None

    summary = HouseholdDetail.get_summary(household_id, selected_qid)
    live_for_header = None
    if summary is None:
        live_for_header = HouseholdDetail.get_summary(household_id, None)

    quarters = QuarterCatalog.all()
    qlabel = QuarterCatalog.label_for(selected_qid) if selected_qid else (
        QuarterCatalog.label_for(summary.quarter_id) if summary else None
    )

    # Families + members (only if we have a summary for this quarter)
    families_with_members = []
    if summary is not None:
        fams = HouseholdFamilies.list_families(household_id, selected_qid or summary.quarter_id)
        for f in fams:
            members = HouseholdFamilies.list_members(f.family_id, selected_qid or summary.quarter_id)
            families_with_members.append({"family": f, "members": members})

    context = {
        "summary": summary,
        "header_fallback": live_for_header,
        "header_number": (summary.household_number if summary else (live_for_header.household_number if live_for_header else None)),
        "quarters": quarters,
        "selected_quarter_id": selected_qid if raw_q not in (None, "", "null") else (summary.quarter_id if summary else None),
        "quarter_label": qlabel,
        "household_id": household_id,
        "families_with_members": families_with_members,   # << pass to template
    }
    return render(request, "nurse_module/householdMore.html", context)

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
    limit = None
    offset = None
    results = []
    
    query = (request.GET.get('query') or '').strip()
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
    # ✅ keep quarter in pagination / limit links
    if quarter_id is not None:
        base_params["quarter_id"] = quarter_id

    prev_url = "?" + urlencode({**base_params, "page": page - 1}) if has_prev else ""
    next_url = "?" + urlencode({**base_params, "page": page + 1}) if has_next else ""
    limit_urls = {n: "?" + urlencode({**base_params, "limit": n, "page": 1}) for n in LIMIT_OPTIONS}

    quarter = Household.sp_get_quarter()
    
    flash = get_flash(request)
    return render(request, 'bhw_module/genInfo.html', {
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
        'quarter': quarter,
        'quarter_id': quarter_id,
        'current_quarter_id': int(current_quarter_id) if current_quarter_id else None,
        'is_current_quarter': is_current_quarter,
        'message': flash['message'],
        'message_level': flash['message_level'],
    })
    return render(request, 'nurse_module/nurseGeneralInfo.html')


@custom_login_required
@role_required('Midwife')
def ImmunizationStatus(request):
    return render(request, 'nurse_module/ImmunizationStatus.html')