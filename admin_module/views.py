from django.shortcuts import render, redirect
from authentication.decorators import custom_login_required, role_required
from .models import Admin
from django.contrib import messages
from django.urls import reverse
import re
from utils.flash import set_flash, get_flash
CODE_MESSAGES = {}

def _clean_db_error(err: Exception) -> str:
    text = str(err)

    if "CONTEXT:" in text:
        text = text.split("CONTEXT:")[0].strip()

    m = re.search(r"(E\d{4,5})\s*:\s*(.*)", text)
    if m:
        code, raw_msg = m.group(1), m.group(2).strip()
        friendly = CODE_MESSAGES.get(code, raw_msg or "An error occurred.")
        return f"{friendly}"

    return "Password change failed. Please check your entries and try again."

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
        FALSE_SET = {'0', 'false', 'off', 'no', ''}

        if active_raw in TRUE_SET:
            active_bool = True
        elif active_raw in FALSE_SET:
            active_bool = False
        else:
            # unexpected value — handle safely
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

@custom_login_required
@role_required('Admin')
def activityLogs(request):
 return render(request, 'admin_module/activityLogs.html')