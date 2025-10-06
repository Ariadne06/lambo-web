from django.shortcuts import render, redirect
from authentication.decorators import custom_login_required, role_required
from household_module.models import Household
from utils.flash import set_flash, get_flash
from utils.db_message import _clean_db_error, _clean_params, coerce_message
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from utils.constants import LIMIT_OPTIONS
from django.utils.http import urlencode
from django.urls import reverse

@custom_login_required
@role_required('Barangay Health Worker')
def bhw_dashboard(request):
    return render(request, 'bhw_module/bhw_dashboard.html')

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
    
    try:
        sitio_id = int(raw_sitio) if raw_sitio not in (None, '', '0') else None
    except ValueError:
        sitio_id = None  # ignore bad input
    
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
        "status": status,
    }
    if sitio_id is not None:
        base_params["sitio_id"] = sitio_id

    prev_url = "?" + urlencode({**base_params, "page": page - 1}) if has_prev else ""
    next_url = "?" + urlencode({**base_params, "page": page + 1}) if has_next else ""
    limit_urls = {n: "?" + urlencode({**base_params, "limit": n, "page": 1}) for n in LIMIT_OPTIONS}

    
    sitio = Household.sp_get_sitio()
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
    hid = int(request.POST.get('household_id') or 0)
    pid = int(request.session.get('personnel_id') or 0)

    def redirect_to_view():
        url = reverse('bhw_module:householdView') + "?" + urlencode({"hid": hid}) if hid else reverse('bhw_module:householdList')
        return redirect(url)

    if not pid:
        set_flash(request, "Missing personnel id.", "error")
        return redirect('bhw_module:householdList')

    # pull current row to compare against
    try:
        prev = Household.sp_get_specific_household(hid)
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
def householdView(request):
    # Accept id from GET (?hid=) or POST (household_id)
    raw_hid = request.GET.get('hid') or request.POST.get('household_id')
    if not raw_hid:
        set_flash(request, "No household selected.", "error")
        return redirect('bhw_module:householdList')

    try:
        hid = int(raw_hid)
    except (TypeError, ValueError):
        set_flash(request, "Invalid household id.", "error")
        return redirect('bhw_module:householdList')

    # Always load the record so `results` is defined
    try:
        result = Household.sp_get_specific_household(hid)
        if not result:
            set_flash(request, "Household not found.", "error")
            return redirect('bhw_module:householdList')
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")
        return redirect('bhw_module:householdList')

    # Reference lists
    relationship    = Household.sp_get_relationship_to_household_head()
    house_ownership = Household.sp_get_house_ownership()
    house_type      = Household.sp_get_house_type()
    sitio           = Household.sp_get_sitio()

    flash = get_flash(request)
    return render(request, 'bhw_module/householdView.html', {
        'relationship': relationship,
        'house_ownership': house_ownership,
        'house_type': house_type,
        'sitio': sitio,
        'results': result,
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