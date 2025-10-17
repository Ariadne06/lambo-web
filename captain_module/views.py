from django.shortcuts import render, redirect
from authentication.decorators import custom_login_required, role_required
from utils.flash import set_flash, get_flash
from utils.db_message import _clean_db_error, _clean_params
from .models import Captain, Dashboard, AnnouncementRepo
from django.utils.http import urlencode
from utils.constants import VALID_SORT_BY, VALID_SORT_DIR, LIMIT_OPTIONS
from django.contrib import messages
from datetime import datetime

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
@role_required('Barangay Captain')
def captain_dashboard(request):
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
    return render(request, "captain_module/captain_dashboard.html", ctx)



@custom_login_required
@role_required('Barangay Captain')
def captain_viewMoreResident(request):
    return render(request, 'captain_module/captain_viewMoreResident.html')

@custom_login_required
@role_required('Barangay Captain')
def captain_viewResident(request):
    return render(request, 'captain_module/captain_viewResident.html')

@custom_login_required
@role_required('Barangay Captain')
def captain_householdList(request):
    return render(request, 'captain_module/captain_householdList.html')

@custom_login_required
@role_required('Barangay Captain')
def captain_moreHousehold(request):
    return render(request, 'captain_module/captain_moreHousehold.html')

@custom_login_required
@role_required('Barangay Captain')
def captain_businessList(request):
    return render(request, 'captain_module/captain_businessList.html')

@custom_login_required
@role_required('Barangay Captain')
def captain_moreBusinessInfo(request):
    return render(request, 'captain_module/captain_moreBusinessInfo.html')

@custom_login_required
@role_required('Barangay Captain')
def personnelRequest(request):
    flash = get_flash(request) 
    
    limit = None
    offset = None
    sort_by = ''
    sort_dir = ''
    results = []
    
    query = (request.GET.get('query') or '').strip()
    filter_status = request.GET.get('filter_status')
    
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
        sort_by = None
    if sort_dir not in VALID_SORT_DIR:
        sort_dir = "desc"
        
    offset = (page - 1) * limit
    
    if request.method == 'POST':
        pid = int(request.POST.get('pid'))
        new_status = request.POST.get('action')

        try:
            captain_personnel_id = request.session.get('personnel_id')
            
            result = Captain.sp_review_personnel_account_by_captain(pid, new_status, captain_personnel_id)
            
            if result is None:
                raise Exception("Failed to change approval status.")
            
            msg = result[0]
            set_flash(request, msg, "success")
        except Exception as e:
            msg = _clean_db_error(e)
            set_flash(request, msg, "error")

        return redirect('captain_module:personnelRequest')

    # # GET: live search + filter
    # query = (request.GET.get('query') or '').strip()
    # filter_status = (request.GET.get('filter_status') or '').strip()
    
    try:
        results = Captain.sp_get_pending_personnel_requests(
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

    final_result = [
        r for r in final_result
        if not filter_status or (r.get('role_name') or '').strip().casefold() == filter_status.casefold()
    ]
    
    base_params = _clean_params({
        "limit": limit,
        "sort_by": sort_by,
        "sort_dir": sort_dir,
        "query": query,    
        "filter_status": filter_status,
    })

    prev_url = "?" + urlencode({**base_params, "page": page - 1}) if has_prev else ""
    next_url = "?" + urlencode({**base_params, "page": page + 1}) if has_next else ""
    
        # limit pills reset page to 1
    limit_urls = {n: "?" + urlencode({**base_params, "limit": n, "page": 1}) for n in LIMIT_OPTIONS}
    
    ROLE_LABELS = [
        "Barangay Captain",
        "Barangay Secretary",
        "Barangay Assistant Secretary",
        "Barangay Treasurer",
        "Barangay Health Worker",
        "Midwife",
    ]

    return render(request, 'captain_module/personnelRequest.html', {
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
        'filter_status': filter_status,
        'message': flash['message'],
        'message_level': flash['message_level'],
        'role_labels': ROLE_LABELS,
    })