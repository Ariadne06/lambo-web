from django.shortcuts import render, redirect
from authentication.decorators import custom_login_required, role_required
from .models import Admin
from django.contrib import messages
from django.urls import reverse, NoReverseMatch
from utils.flash import set_flash, get_flash
from utils.db_message import _clean_db_error, _clean_params
from django.utils.timezone import localtime
from django.utils.http import urlencode
from utils.constants import VALID_SORT_BY, VALID_SORT_DIR, LIMIT_OPTIONS
from django.db import connection
from django.http import JsonResponse


# Create your views here.
@custom_login_required
@role_required('Admin')
def admin_dashboard(request):
    total, active = Admin.fn_personnel_counts()

    # Existing: password requests
    password_requests = Admin.get_password_reset_requests(limit=50)

    # NEW: recent activity logs mapped to your HTML's expected shape
    recent_logins = Admin.get_recent_activity_for_ui()

    try:
        manage_url = reverse('admin_manage_personnel')
    except NoReverseMatch:
        manage_url = None

    context = {
        'personnel_count': total,
        'personnel_active_count': active,
        'manage_personnel_url': manage_url,
        'password_requests': password_requests,
        'recent_logins': recent_logins,  # <-- powers your "Recent Logs" section
    }
    return render(request, 'admin_module/admin_dashboard.html', context)

@custom_login_required
@role_required('Admin')
def admin_Addpersonnel(request):

    query = (request.GET.get('query') or '').strip()
    filter_status = (request.GET.get('filter_status') or '').strip()

    flash = get_flash(request) 

    results = []
    if query:
        results = Admin.sp_search_residents_live_with_id(query)

    context = {
        'results': results,
        'query': query,
        'filter_status': filter_status,
        'message': flash['message'],
        'message_level': flash['message_level'],
    }
    return render(request, 'admin_module/admin_Addpersonnel.html', context)

@custom_login_required
@role_required('Admin')
def add_personnel1(request):
    
    if request.method != 'POST':
        set_flash(request, "No resident selected.", "error")
        return redirect('admin_module:admin_Addpersonnel')

    resident_id = request.POST.get('resident_id')
    if not resident_id:
        set_flash(request, "No resident selected.", "error")
        return redirect('admin_module:admin_Addpersonnel')

    try:
        results = Admin.sp_get_resident_profile(resident_id)
    except Exception as e:
        set_flash(request, f"Error retrieving resident profile: {e}", "error")
        return redirect('admin_module:admin_Addpersonnel')

    if not results:
        set_flash(request, "Resident not found.", "error")
        return redirect('admin_module:admin_Addpersonnel')

    return render(request, 'admin_module/add_personnel1.html', {'results': results})


@custom_login_required
@role_required('Admin')
def add_personnel2(request):
    if request.method != 'POST':
        set_flash(request, "No resident selected.", "error")
        return redirect('admin_module:admin_Addpersonnel')

    resident_id = request.POST.get('resident_id')
    role_id     = request.POST.get('role_id')
    email       = request.POST.get('email')
    username    = request.POST.get('username', '').strip()

    # Default: no message
    message = None
    message_level = None

    if not (resident_id and role_id and email):
        message = "Missing required fields (resident, role, or email)."
        message_level = "error"
        return render(request, 'admin_module/add_personnel2.html', {
            'resident_id': resident_id,
            'role_id': role_id,
            'email': email,
            'message': message,
            'message_level': message_level,
        })

    if username:
        try:
            msg = Admin.sp_insert_personnel_credentials(
                int(resident_id), int(role_id), username, email
            )
            message = msg or "Personnel created successfully."
            message_level = "success"
            return render(request, 'admin_module/add_personnel2.html', {
                'resident_id': resident_id,
                'role_id': role_id,
                'email': email,
                'message': message,
                'message_level': message_level,
            })
        except Exception as e:
            message = _clean_db_error(e)
            message_level = "error"

    # Initial form render (or after error)
    return render(request, 'admin_module/add_personnel2.html', {
        'resident_id': resident_id,
        'role_id': role_id,
        'email': email,
        'message': message,
        'message_level': message_level,
    })


@custom_login_required
@role_required('Admin')
def personnel_list(request):
    
    flash = get_flash(request) 
    
    if request.method == 'POST':
        pid = int(request.POST.get('pid'))
        active_raw = (request.POST.get('active') or '').strip().lower()

        TRUE_SET  = {'1', 'true', 'on', 'yes'}
        FALSE_SET = {'0', 'false', 'off', 'no'}
        PENDING_SET = {'pending'} 

        if active_raw in TRUE_SET:
            active_bool = True
        elif active_raw in FALSE_SET:
            active_bool = False
        elif active_raw in PENDING_SET:
            try:
                admin_personnel_id = request.session.get('personnel_id')
                
                try:
                    username = request.POST.get('edit_username')
                    email = request.POST.get('edit_email')
                    role_name = request.POST.get('edit_role')
                    
                    ROLE_MAP = {
                        'Barangay Captain': 2,
                        'Barangay Secretary': 3,
                        'Barangay Assistant Secretary': 4,
                        'Barangay Treasurer': 5,
                        'Barangay Health Worker': 6,
                        'Midwife': 7,
                    }
                    role_id = ROLE_MAP.get(role_name)
                    
                    reslt = Admin.sp_edit_personnel_draft(pid, admin_personnel_id, role_id, username, email)
                    
                    if reslt is None:
                        raise Exception("Failed to edit personnel credentials.")
                except Exception as e:
                    msg = _clean_db_error(e)
                    set_flash(request, msg, "error")
                    return redirect('admin_module:personnel_list')
                
                result = Admin.sp_admin_reset_personnel_to_pending(pid, admin_personnel_id)
                if result is None:
                    raise Exception("Failed to reset personnel to pending.")
                
                msg = f"Status set to Pending. This personnel can now be re-evaluated for approval or rejection."
                set_flash(request, msg, "success")
            except Exception as e:
                msg = _clean_db_error(e)
                set_flash(request, msg, "error")
                
            return redirect('admin_module:personnel_list')
        else:
            set_flash(request, "Invalid active flag.", "error")
            return redirect('admin_module:personnel_list')

        try:
            admin_personnel_id = request.session.get('personnel_id')
            
            result = Admin.sp_set_personnel_active_status(pid, active_bool, admin_personnel_id)
            if result is None:
                raise Exception("Failed to update personnel active status.")
            
            msg = f"Personnel {'activated' if active_bool else 'deactivated'} successfully."
            set_flash(request, msg, "success")
        except Exception as e:
            msg = _clean_db_error(e)
            set_flash(request, msg, "error")

        return redirect('admin_module:personnel_list')

    query = (request.GET.get('query') or '').strip()
    filter_status = request.GET.get('filter_status')

    limit = None
    offset = None
    sort_by = ''
    sort_dir = ''
    results = []

    try:
        if query:
            results = Admin.sp_search_personnels(
                query,
                approval_status=None,
                is_active=None,
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                sort_dir=sort_dir
            )
        else:
            results = Admin.sp_view_all_personnels(
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                sort_dir=sort_dir
            )
    except Exception as e:
        msg = _clean_db_error(e)
        set_flash(request, msg, "error")
        results = []

    results = [
        r for r in results
        if not filter_status or (r.get('role_name') or '').strip().casefold() == filter_status.casefold()
    ]

    return render(request, 'admin_module/personnel_list.html', {
        'results': results,
        'query': query,
        'filter_status': filter_status,
        'message': flash['message'],
        'message_level': flash['message_level'],
    })

@custom_login_required
@role_required('Admin')
def update_personnel(request):
    
    flash = get_flash(request) 
    
    if request.method not in ["GET", "POST"]: 
        set_flash(request, "Invalid request method.", "error")
        return redirect("admin_module:personnel_list")
    
    if request.method == "POST":
        pid = request.POST.get("pid")
        username = (request.POST.get("username") or "").strip()
        email    = (request.POST.get("email") or "").strip()
        role_id = request.POST.get("role_id")

        if not pid:
            set_flash(request, "Missing personnel id.", "error")
            return redirect("admin_module:personnel_list")

        # Case A: POST from list page (only pid, no fields) -> just redirect to GET form
        if username == "" and email == "":
            return redirect(f"{reverse('admin_module:update_personnel')}?pid={pid}")

        # Case B: POST from update form -> only update if something actually changed
        current = Admin.get_personnel_by_id(int(pid))
        new_username = username if username and username != current.get("username") else None
        new_email    = email    if email    and email    != current.get("email")    else None
        new_role_id = role_id if role_id and int(role_id) != current.get("role_id") else None

        if new_username is None and new_email is None and new_role_id is None:
            set_flash(request, "No changes to save.")
            return redirect(f"{reverse('admin_module:update_personnel')}?pid={pid}")

        try:
            msg = Admin.sp_update_personnel_credentials(int(pid), new_username, new_email, new_role_id)
            set_flash(request, "Updated successfully.", "success")
        except Exception as e:
            msg = _clean_db_error(e)
            set_flash(request, msg, "error")

        return redirect(f"{reverse('admin_module:update_personnel')}?pid={pid}")

    # GET: load and prefill
    pid = request.GET.get("pid")
    personnel = Admin.get_personnel_by_id(int(pid)) if pid else None
    if pid and not personnel:
        set_flash(request, "Personnel not found.", "error")
        messages.error(request, "Personnel not found.")
    return render(request, "admin_module/update_personnel.html", {
        "pid": pid, 
        "personnel": personnel,
        'message': flash['message'],
        'message_level': flash['message_level'
        ]})

@custom_login_required
@role_required('Admin')
def password_request(request):
    
    limit = None
    offset = None
    sort_by = ''
    sort_dir = ''
    results = []
    
    query = (request.GET.get('query') or '').strip()
    filter_status = request.GET.get('filter_status')
    action = (request.POST.get('action') or '').strip().lower()
    
    if action is not None and action != '':
        try:
            pid = int(request.POST.get('pid'))
                
            result = Admin.sp_admin_review_personnel_password_request(pid, action)
                
            msg = result
            set_flash(request, msg, "success")
        except Exception as e:
            msg = _clean_db_error(e)
            set_flash(request, msg, "error")
    
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

    try:
        results = Admin.sp_get_personnel_password_requests_forgot(
            query=query,
            approval_status=None,
            is_active=None,
            role_id=None,
            start_ts=None,
            end_ts=None,
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
    
    flash = get_flash(request)

    return render(request, 'admin_module/password_request.html', {
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

@custom_login_required
@role_required('Admin')
def activityLogs(request):
    
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

    sort_by  = request.GET.get("sort_by", "log_timestamp")
    sort_dir = request.GET.get("sort_dir", "desc").lower()
    if sort_by not in VALID_SORT_BY:
        sort_by = "log_timestamp"
    if sort_dir not in VALID_SORT_DIR:
        sort_dir = "desc"

    offset = (page - 1) * limit

    # --- Fetch logs (grab one extra to detect next) ---
    rows = Admin.sp_get_activty_logs(
        limit=limit + 1,
        offset=offset,
        sort_by=sort_by,
        sort_dir=sort_dir,
        query=query,
    ) or []

    has_next = len(rows) > limit
    has_prev = page > 1
    activity_logs = rows[:limit]

    # format timestamps
    for r in activity_logs:
        ts = r.get("log_timestamp")
        r["log_timestamp_fmt"] = localtime(ts).strftime("%m/%d/%Y, %I:%M %p") if ts else ""

    # ---- Build URLs in the view (no function calls in template) ----
    base_params = {
        "limit": limit, 
        "sort_by": sort_by, 
        "sort_dir": sort_dir,
        "query": query,
        }

    prev_url = "?" + urlencode({**base_params, "page": page - 1}) if has_prev else ""
    next_url = "?" + urlencode({**base_params, "page": page + 1}) if has_next else ""

    # limit pills reset page to 1
    limit_urls = {n: "?" + urlencode({**base_params, "limit": n, "page": 1}) for n in LIMIT_OPTIONS}

    context = {
        "activity_logs": activity_logs,
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
    }
    return render(request, "admin_module/activityLogs.html", context)

@custom_login_required
@role_required('Admin')
def authenticationlog(request):
    limit = None
    offset = None
    results = []
    
    query = (request.GET.get('query') or '').strip()
    account_type = request.GET.get('account_type')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
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
        with connection.cursor() as cursor:
            cursor.callproc('view_authentication_logs', [
                f'%{query}%' if query else None,
                account_type if account_type else None,
                start_date if start_date else None,
                end_date if end_date else None,
                limit + 1,
                offset
            ])
            cols = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            results = [dict(zip(cols, row)) for row in rows]
    except Exception as e:
        msg = _clean_db_error(e)
        set_flash(request, msg, "error")
        results = []
    
    has_next = len(results) > limit
    has_prev = page > 1
    final_result = results[:limit]
    
    base_params = {
        "limit": limit,
        "query": query,
    }
    if account_type:
        base_params["account_type"] = account_type
    if start_date:
        base_params["start_date"] = start_date
    if end_date:
        base_params["end_date"] = end_date

    prev_url = "?" + urlencode({**base_params, "page": page - 1}) if has_prev else ""
    next_url = "?" + urlencode({**base_params, "page": page + 1}) if has_next else ""
    limit_urls = {n: "?" + urlencode({**base_params, "limit": n, "page": 1}) for n in LIMIT_OPTIONS}
    
    flash = get_flash(request)
    return render(request, 'admin_module/authenticationlog.html', {
        "results": final_result,
        "limit": limit,
        "page": page,
        "account_type": account_type,
        "start_date": start_date,
        "end_date": end_date,
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
@role_required('Admin')
def documentlog(request):
    return render(request, 'admin_module/documentlog.html')

@custom_login_required
@role_required('Admin')
def residentlog(request):
    return render(request, 'admin_module/residentlog.html')

@custom_login_required
@role_required('Admin')
def residentList(request):
    if request.method == 'POST':
        resident_id = request.POST.get('resident_id')
        email = request.POST.get('email')
        admin_personnel_id = request.session.get('personnel_id')
        
        if resident_id and email and admin_personnel_id:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE Resident SET email = %s WHERE resident_id = %s",
                        [email, int(resident_id)]
                    )
                    set_flash(request, "Email updated successfully.", "success")
            except Exception as e:
                set_flash(request, _clean_db_error(e), "error")
        else:
            set_flash(request, "Missing required information for email update.", "error")
        
        return redirect('admin_module:residentList')
    
    limit = None
    offset = None
    results = []
    
    query = (request.GET.get('query') or '').strip()
    raw_sex = request.GET.get('sex')
    sex = raw_sex.strip() if raw_sex and raw_sex.strip() else None
    raw_status_id = request.GET.get('status_id')
    
    try:
        status_id = int(raw_status_id) if raw_status_id not in (None, '', '0') else None
    except ValueError:
        status_id = None
    
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
        with connection.cursor() as cursor:
            # Request more results to account for potential filtering
            cursor.callproc('view_all_resident', [
                query or None,
                sex,
                status_id,
                None,  # p_min_age
                None,  # p_max_age
                limit + 10,  # Request extra results to account for filtering
                offset
            ])
            cols = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            # Filter out resident_id = 1
            all_results = [dict(zip(cols, row)) for row in rows if dict(zip(cols, row)).get('resident_id') != 1]
            
            # Take only what we need for this page plus one to check if there's a next page
            results = all_results[:limit + 1]
    except Exception as e:
        msg = _clean_db_error(e)
        set_flash(request, msg, "error")
        results = []
    
    has_next = len(results) > limit
    has_prev = page > 1
    final_result = results[:limit]
    
    base_params = {
        "limit": limit,
        "query": query,
    }
    if sex is not None:
        base_params["sex"] = sex
    if status_id is not None:
        base_params["status_id"] = status_id

    prev_url = "?" + urlencode({**base_params, "page": page - 1}) if has_prev else ""
    next_url = "?" + urlencode({**base_params, "page": page + 1}) if has_next else ""
    limit_urls = {n: "?" + urlencode({**base_params, "limit": n, "page": 1}) for n in LIMIT_OPTIONS}
    
    # Get status options for filter dropdown
    status_options = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT status_id, status_name FROM Resident_Status ORDER BY status_name")
            status_options = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
    except Exception:
        pass
    
    flash = get_flash(request)
    return render(request, 'admin_module/residentList.html', {
        "results": final_result,
        "limit": limit,
        "page": page,
        "sex": sex,
        "status_id": status_id,
        "has_prev": has_prev,
        "has_next": has_next,
        "prev_url": prev_url,
        "next_url": next_url,
        "limit_options": LIMIT_OPTIONS,
        "limit_urls": limit_urls,
        "status_options": status_options,
        'query': query,
        'message': flash['message'],
        'message_level': flash['message_level'],
    })
@custom_login_required
@role_required('Admin')
def get_resident_profile(request, resident_id):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT get_resident_profile(%s)", [resident_id])
            result = cursor.fetchone()
            if result and result[0]:
                return JsonResponse(result[0])
            else:
                return JsonResponse({'error': 'Resident not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)