from django.shortcuts import render, redirect
from authentication.decorators import custom_login_required, role_required
from django.utils.http import urlencode
from utils.flash import set_flash, get_flash
from utils.db_message import _clean_db_error, _clean_params, coerce_message
from utils.constants import VALID_SORT_BY, VALID_SORT_DIR, LIMIT_OPTIONS
from .models import Secretary
from utils.supa import url_for_doc
from django.http import JsonResponse, HttpResponseBadRequest
from django.db import connection


@custom_login_required
@role_required('Barangay Secretary')
def secretary_dashboard(request):
    return render(request, 'secretary_module/secretary_dashboard.html')

@custom_login_required
@role_required('Barangay Secretary')
def resident_list(request):
    return render(request, 'secretary_module/resident_list.html')

@custom_login_required
@role_required('Barangay Secretary')
def household_list(request):
    return render(request, 'secretary_module/household_list.html')

@custom_login_required
@role_required('Barangay Secretary')
def moreHousehold(request):
    return render(request, 'secretary_module/moreHousehold.html')

def _find_resident_id_by_name(query: str):
    """
    Uses your PostgreSQL function search_business_owner to resolve resident_id
    from a name/email/phone query. Returns a single resident_id or raises.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM search_business_owner(%s, %s, %s)", [query, 20, 0])
        rows = cursor.fetchall()

    if not rows:
        raise ValueError("Resident not found")
    if len(rows) > 1:
        raise ValueError("Multiple residents found. Please be more specific.")
    return rows[0][0]  # first column = resident_id

@custom_login_required
@role_required('Barangay Secretary')
def Addbusiness(request):
    if request.method == "POST":
        try:
            # 🔑 Resolve owner first
            resident_name = request.POST.get("resident_name")
            resident_id = _find_resident_id_by_name(resident_name)

            # Collect the rest
            business_name         = request.POST.get("business_name")
            business_type_id      = int(request.POST.get("business_type_id"))
            nature_of_business    = request.POST.get("nature_of_business")
            ownership_id          = int(request.POST.get("ownership_id"))
            house_number          = request.POST.get("house_number")
            street                = request.POST.get("street")
            barangay              = request.POST.get("barangay")
            sitio_id              = int(request.POST.get("sitio_id"))
            city_municipality     = request.POST.get("city_municipality")
            country               = request.POST.get("country") or "Philippines"
            total_gross_income    = request.POST.get("total_gross_income")
            dti_sec_cda_reg_num   = request.POST.get("dti_sec_cda_reg_number")
            clearance_date_issued = request.POST.get("clearance_date_issued") or None
            personnel_id          = int(request.session.get("personnel_id"))

            # Call your stored procedure
            result = Secretary.sp_register_business(
                resident_id,
                business_name,
                business_type_id,
                nature_of_business,
                ownership_id,
                house_number,
                street,
                barangay,
                sitio_id,
                city_municipality,
                country,
                total_gross_income,
                dti_sec_cda_reg_num,
                clearance_date_issued,
                personnel_id,
            )

            set_flash(request, "Successfully Submitted", "success")

        except ValueError as ve:
            set_flash(request, str(ve), "error")
        except Exception as e:
            set_flash(request, str(e), "error")

    flash = get_flash(request)
    return render(request, "secretary_module/Addbusiness.html", {
        'message': flash.get('message'),
        'message_level': flash.get('message_level'),
    })

@custom_login_required
@role_required('Barangay Secretary')
def businessDetail1(request):
    return render(request, 'secretary_module/businessDetail1.html')

@custom_login_required
@role_required('Barangay Secretary')
def businessDetail2(request):
    return render(request, 'secretary_module/businessDetail2.html')

@custom_login_required
@role_required('Barangay Secretary')
def businessDetail3(request):
    return render(request, 'secretary_module/businessDetail3.html')

@custom_login_required
@role_required('Barangay Secretary')
def business_list(request):
    return render(request, "secretary_module/manageBusiness.html")

@custom_login_required
@role_required('Barangay Secretary')
def add_certificate(request):
    return render(request, 'secretary_module/addCertificate.html')

@custom_login_required
@role_required('Barangay Secretary')
def manageCert1(request):
    return render(request, 'secretary_module/manageCert1.html')

@custom_login_required
@role_required('Barangay Secretary')
def manageCert2(request):
    return render(request, 'secretary_module/manageCert2.html')

@custom_login_required
@role_required('Barangay Secretary')
def applications(request):
    return render(request, 'secretary_module/applications.html')

@custom_login_required
@role_required('Barangay Secretary')
def price_update(request):
    return render(request, 'secretary_module/priceUpdate.html')

@custom_login_required
@role_required('Barangay Secretary')
def announcement(request):
    return render(request, 'secretary_module/announcement.html')

@custom_login_required
@role_required('Barangay Secretary')
def get_doc_url(request):
    """
    Given a file_path (path within the bucket), return a viewable URL.
    - If bucket is public (dev) -> public URL
    - If bucket is private (prod) -> short-lived signed URL
    SECURITY NOTE: In production, prefer accepting a doc_id and look up file_path server-side.
    """
    file_path = request.GET.get("file_path")
    if not file_path:
        return HttpResponseBadRequest("Missing file_path")

    try:
        url = url_for_doc(file_path)
        if not url:
            return HttpResponseBadRequest("Could not generate URL")
        return JsonResponse({"url": url})
    except Exception as e:
        return HttpResponseBadRequest(str(e))

@custom_login_required
@role_required('Barangay Secretary')
def approval_decide(request):
    
    rid = int(request.POST.get("rid"))
    doc_type_id = int(request.POST.get("doctype_id"))
    action = request.POST.get("action")      
    review_notes = request.POST.get("rejection_notes", "")
    pid = int(request.session.get("personnel_id"))          

    if action not in ("approved", "rejected"):
        return HttpResponseBadRequest("Invalid request.")

    try:
        result = Secretary.sp_review_resident_supporting_certificate(
            rid=rid,
            doc_type_id=doc_type_id,
            review_status=action,
            review_notes=review_notes,
            pid=pid
        )
        msg = coerce_message(result)
        set_flash(request, msg, "success")
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")

    return redirect("secretary_module:approval")

@custom_login_required
@role_required('Barangay Secretary')
def approval(request):
    flash = get_flash(request) 
    
    limit = None
    offset = None
    sort_by = ''
    sort_dir = ''
    results = []
    
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
        
    sort_by  = request.GET.get("sort_by")
    sort_dir = request.GET.get("sort_dir", "desc").lower()
    if sort_by not in VALID_SORT_BY:
        sort_by = ""
    if sort_dir not in VALID_SORT_DIR:
        sort_dir = "desc"
        
    offset = (page - 1) * limit
    
    try:
        results = Secretary.sp_get_pending_supporting_certificates(
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

    
    base_params = _clean_params({
        "limit": limit,
        "sort_by": sort_by,
        "sort_dir": sort_dir,
        "query": query,    
    })

    prev_url = "?" + urlencode({**base_params, "page": page - 1}) if has_prev else ""
    next_url = "?" + urlencode({**base_params, "page": page + 1}) if has_next else ""
    
        # limit pills reset page to 1
    limit_urls = {n: "?" + urlencode({**base_params, "limit": n, "page": 1}) for n in LIMIT_OPTIONS}

    return render(request, 'secretary_module/approval.html', {
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
        'message': flash['message'],
        'message_level': flash['message_level'],
        'session_personnel_id': request.session.get('personnel_id'),
    })
