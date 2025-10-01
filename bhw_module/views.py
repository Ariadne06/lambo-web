from django.shortcuts import render, redirect
from authentication.decorators import custom_login_required, role_required
from household_module.models import Household
from utils.flash import set_flash, get_flash
from utils.db_message import _clean_db_error, _clean_params, coerce_message

# Create your views here.

from django.shortcuts import render

@custom_login_required
@role_required('Barangay Health Worker')
def bhw_dashboard(request):
    return render(request, 'bhw_module/bhw_dashboard.html')

@custom_login_required
@role_required('Barangay Health Worker')
def householdList(request):
    flash = get_flash(request)
    return render(request, 'bhw_module/householdList.html',{
        'message': flash['message'],
        'message_level': flash['message_level'],
    })

@custom_login_required
@role_required('Barangay Health Worker')
def householdView(request):
    return render(request, 'bhw_module/householdView.html')

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
    return render(request, 'bhw_module/childList.html')

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
    return render(request, 'bhw_module/genInfo.html')

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
        results = Household.sp_search_resaident(query)
    
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
    
# bhw/views.py
from django.http import JsonResponse
from django.views.decorators.http import require_GET

@custom_login_required
@role_required('Barangay Health Worker')
@require_GET
def resident_search_api(request):
    q = (request.GET.get('q') or '').strip()
    if not q:
        return JsonResponse({'results': []})
    try:
        rows = Household.sp_search_resaident(q)  # uses your stored proc
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