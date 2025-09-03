from django.shortcuts import render, redirect
from authentication.decorators import custom_login_required, role_required
from .models import Admin
from django.contrib import messages
from django.urls import reverse
from utils.flash import set_flash, get_flash
from utils.db_message import _clean_db_error
from django.utils.timezone import localtime
from django.utils.http import urlencode

# Create your views here.
@custom_login_required
@role_required('Admin')
def admin_dashboard(request):
    return render(request, 'admin_module/admin_dashboard.html')

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
                    role_id = request.POST.get('edit_position')
                    
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

    # GET: live search + filter
    query = (request.GET.get('query') or '').strip()
    filter_status = (request.GET.get('filter_status') or '').strip()

    # Call a helper that applies search/filter (and excludes Admin)
    results = Admin.sp_display_personnel_credentials(query=query, role_filter=filter_status or None)

    return render(request, 'admin_module/personnel_list.html', {
        'results': results,
        'query': query,
        'filter_status': filter_status,
        'message': flash['message'],
        'message_level': flash['message_level'],
    })

# @custom_login_required
# @role_required('Admin')
# def personnel_list(request):
#     # Handle POST actions (activate/deactivate)
#     if request.method == 'POST':
#         pid = int(request.POST.get('pid'))
#         active = request.POST.get('active')  # 'true' | 'false'
#         try:
#             admin_personnel_id = request.session.get('personnel_id')
#             Admin.sp_set_personnel_active_status(pid, active, admin_personnel_id)
#             messages.success(request, f"Personnel {'activated' if active == 'true' else 'deactivated'} successfully.")
#         except Exception as e:
#             messages.error(request, str(e))
#         return redirect('admin_module:personnel_list')

#     # --- GET: filters/pagination/sorting ---
#     # Search: empty string means "show all"
#     query = (request.GET.get('query') or '').strip()

#     approval_status = request.GET.get('approval_status') or None  # 'pending'|'approved'|'rejected'|None
#     is_active_raw   = request.GET.get('is_active')                 # 'true'|'false'|''|None
#     sort_by         = request.GET.get('sort_by') or 'full_name'
#     sort_dir        = request.GET.get('sort_dir') or 'asc'

#     # Pagination defaults so the page works on first load
#     try:
#         limit = int(request.GET.get('limit', 25))
#     except (TypeError, ValueError):
#         limit = 25
#     try:
#         offset = int(request.GET.get('offset', 0))
#     except (TypeError, ValueError):
#         offset = 0
#     if limit < 0: limit = 0
#     if offset < 0: offset = 0

#     # Convert is_active ('true'/'false'/None) → bool|None
#     is_active = None
#     if is_active_raw is not None and is_active_raw != '':
#         low = is_active_raw.lower()
#         if low == 'true':
#             is_active = True
#         elif low == 'false':
#             is_active = False

#     # Always use search_personnels; empty query ('') = show all
#     results = Admin.sp_search_personnels(
#         query=query,
#         approval_status=approval_status,
#         is_active=is_active,
#         limit=limit,
#         offset=offset,
#         sort_by=sort_by,
#         sort_dir=sort_dir
#     )

#     # Pagination helpers
#     count_on_page = len(results)
#     has_prev = offset > 0
#     has_next = (limit > 0) and (count_on_page == limit)
#     page = (offset // limit + 1) if limit > 0 else 1
#     from_row = (offset + 1) if count_on_page else 0
#     to_row = (offset + count_on_page) if count_on_page else 0

#     # Options for limit dropdown (avoid .split in template)
#     limit_options = [10, 25, 50, 100]

#     return render(request, 'admin_module/personnel_list.html', {
#         'results': results,

#         'query': query,
#         'approval_status': approval_status,
#         'is_active': is_active_raw,

#         'sort_by': sort_by,
#         'sort_dir': sort_dir,

#         'limit': limit,
#         'offset': offset,
#         'limit_options': limit_options,

#         'has_prev': has_prev,
#         'has_next': has_next,
#         'count_on_page': count_on_page,
#         'page': page,
#         'from_row': from_row,
#         'to_row': to_row,
#     })




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
 return render(request, 'admin_module/password_request.html')

VALID_SORT_BY = {"log_timestamp", "action", "subsystem_name", "table_name", "performed_by_name"}
VALID_SORT_DIR = {"asc", "desc"}
LIMIT_OPTIONS = [10, 25, 50, 100]

def activityLogs(request):
        # --- Query params ---
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
    ) or []

    has_next = len(rows) > limit
    has_prev = page > 1
    activity_logs = rows[:limit]

    # format timestamps
    for r in activity_logs:
        ts = r.get("log_timestamp")
        r["log_timestamp_fmt"] = localtime(ts).strftime("%m/%d/%Y, %I:%M %p") if ts else ""

    # ---- Build URLs in the view (no function calls in template) ----
    base_params = {"limit": limit, "sort_by": sort_by, "sort_dir": sort_dir}

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
    }
    return render(request, "admin_module/activityLogs.html", context)

@custom_login_required
@role_required('Admin')
def authenticationlog(request):
    return render(request, 'admin_module/authenticationlog.html')

@custom_login_required
@role_required('Admin')
def documentlog(request):
    return render(request, 'admin_module/documentlog.html')

@custom_login_required
@role_required('Admin')
def residentlog(request):
    return render(request, 'admin_module/residentlog.html')
