from django.shortcuts import render, redirect
from authentication.decorators import custom_login_required, role_required
from utils.flash import set_flash, get_flash
from utils.db_message import _clean_db_error
from .models import Captain

# Create your views here.

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

    results = Captain.sp_get_pending_personnel_requests(None)

    return render(request, 'captain_module/personnelRequest.html', {
        'results': results,
        # 'query': query,
        # 'filter_status': filter_status,
        'message': flash['message'],
        'message_level': flash['message_level'],
    })