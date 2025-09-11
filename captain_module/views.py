from django.shortcuts import render, redirect
from authentication.decorators import custom_login_required, role_required
from utils.flash import set_flash, get_flash
from utils.db_message import _clean_db_error, _clean_params
from .models import Captain
from django.utils.http import urlencode
from utils.constants import VALID_SORT_BY, VALID_SORT_DIR, LIMIT_OPTIONS



@custom_login_required
@role_required('Barangay Captain')
def captain_dashboard(request):
    return render(request, 'captain_module/captain_dashboard.html')

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