from django.shortcuts import render, redirect
from authentication.decorators import custom_login_required, role_required
from .models import Admin
from django.contrib import messages
from django.urls import reverse

# Create your views here.
@custom_login_required
@role_required('Admin')
def admin_dashboard(request):
    return render(request, 'admin_module/admin_dashboard.html')

@custom_login_required
@role_required('Admin')
def admin_Addpersonnel(request):
    # Read query + filter from URL (?query=...&filter_status=...)
    query = (request.GET.get('query') or '').strip()
    filter_status = (request.GET.get('filter_status') or '').strip()

    results = []
    if query:
        # If you want to avoid tiny searches, you can check len(query) >= 2
        results = Admin.sp_search_residents_live_with_id(query)

    context = {
        'results': results,
        'query': query,
        'filter_status': filter_status,
    }
    return render(request, 'admin_module/admin_Addpersonnel.html', context)

@custom_login_required
@role_required('Admin')
def add_personnel1(request):
    # If someone hits this URL directly via GET, bounce them to the search page
    if request.method != 'POST':
        return redirect('admin_module:admin_Addpersonnel')

    resident_id = request.POST.get('resident_id')
    if not resident_id:
        messages.error(request, "No resident selected.")
        return redirect('admin_module:admin_Addpersonnel')

    try:
        results = Admin.sp_get_resident_profile(resident_id)  # should return a list with one dict (or None)
    except Exception as e:
        messages.error(request, f"Error retrieving resident profile: {e}")
        return redirect('admin_module:admin_Addpersonnel')

    if not results:
        messages.error(request, "Resident not found.")
        return redirect('admin_module:admin_Addpersonnel')

    return render(request, 'admin_module/add_personnel1.html', {'results': results})

@custom_login_required
@role_required('Admin')
def add_personnel2(request):
    if request.method != 'POST':
        return redirect('admin_module:admin_Addpersonnel')

    resident_id = request.POST.get('resident_id')
    role_id     = request.POST.get('role_id')
    email       = request.POST.get('email')  # or 'resident_email' if you keep Option B
    username    = request.POST.get('username', '').strip()  # if this page also collects username

    if not (resident_id and role_id and email):
        messages.error(request, "Missing required fields (resident, role, or email).")
        return redirect('admin_module:add_personnel1')

    # If your Step 2 template collects username and submits on the same page:
    if username:
        try:
            msg = Admin.sp_insert_personnel_credentials(int(resident_id), int(role_id), username, email)
            messages.success(request, msg or "Personnel created.")
            return redirect('admin_module:personnel_list')
        except Exception as e:
            messages.error(request, f"Error adding personnel: {e}")

    # Otherwise, render the Step 2 form to collect username (and show email read-only)
    return render(request, 'admin_module/add_personnel2.html', {
        'resident_id': resident_id,
        'role_id': role_id,
        'email': email,
    })


@custom_login_required
@role_required('Admin')
def personnel_list(request):
    if request.method == 'POST':
        pid = int(request.POST.get('pid'))
        active = request.POST.get('active') 

        try:
            admin_personnel_id = request.session.get('personnel_id')
            
            result = Admin.sp_set_personnel_active_status(pid, active, admin_personnel_id)
            if result is None:
                raise Exception("Failed to update personnel active status.")
            
            msg = f"Personnel {'activated' if active else 'deactivated'} successfully."
            messages.success(request, msg)
        except Exception as e:
            messages.error(request, str(e))

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
    if request.method == "POST":
        pid = request.POST.get("pid")
        username = (request.POST.get("username") or "").strip()
        email    = (request.POST.get("email") or "").strip()

        if not pid:
            messages.error(request, "Missing personnel id.")
            return redirect("admin_module:personnel_list")

        # Case A: POST from list page (only pid, no fields) -> just redirect to GET form
        if username == "" and email == "":
            return redirect(f"{reverse('admin_module:update_personnel')}?pid={pid}")

        # Case B: POST from update form -> only update if something actually changed
        current = Admin.get_personnel_by_id(int(pid))  # see helper below
        new_username = username if username and username != current.get("username") else None
        new_email    = email    if email    and email    != current.get("email")    else None

        if new_username is None and new_email is None:
            messages.info(request, "No changes to save.")
            return redirect(f"{reverse('admin_module:update_personnel')}?pid={pid}")

        try:
            msg = Admin.sp_update_personnel_credentials(int(pid), new_username, new_email)
            messages.success(request, msg or "Updated successfully.")
        except Exception as e:
            messages.error(request, str(e))

        return redirect(f"{reverse('admin_module:update_personnel')}?pid={pid}")

    # GET: load and prefill
    pid = request.GET.get("pid")
    personnel = Admin.get_personnel_by_id(int(pid)) if pid else None
    if pid and not personnel:
        messages.error(request, "Personnel not found.")
    return render(request, "admin_module/update_personnel.html", {"pid": pid, "personnel": personnel})


@custom_login_required
@role_required('Admin')
def password_request(request):
 return render(request, 'admin_module/password_request.html')

@custom_login_required
@role_required('Admin')
def activityLogs(request):
 return render(request, 'admin_module/activityLogs.html')


def authenticationlog(request):
    return render(request, 'admin_module/authenticationlog.html')

def documentlog(request):
    return render(request, 'admin_module/documentlog.html')

def residentlog(request):
    return render(request, 'admin_module/residentlog.html')