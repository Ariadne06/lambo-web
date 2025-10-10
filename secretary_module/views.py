from django.shortcuts import render, redirect
from authentication.decorators import custom_login_required, role_required
from django.utils.http import urlencode
from utils.flash import set_flash, get_flash
from utils.db_message import _clean_db_error, _clean_params, coerce_message
from utils.constants import VALID_SORT_BY, VALID_SORT_DIR, LIMIT_OPTIONS
from .models import Secretary, Business, Dashboard
from utils.supa import url_for_doc
from django.http import JsonResponse, HttpResponseBadRequest
from django.db import connection
from math import ceil
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods
from decimal import Decimal, InvalidOperation
from django.contrib import messages


@custom_login_required
@role_required('Barangay Secretary')
def secretary_dashboard(request):
    barangay = request.GET.get("barangay") or None
    city     = request.GET.get("city") or None

    # Totals
    try:
        totals = Dashboard.sp_dashboard_totals(barangay=barangay, city=city)
    except Exception as e:
        messages.error(request, f"Failed loading totals: {e}")
        totals = {"total_resident": 0, "total_non_resident": 0, "total_pending": 0, "total_male": 0, "total_female": 0}

    # Residents per sitio (no params)
    try:
        per_sitio_rows = Dashboard.sp_residents_per_sitio_json()
        print("DEBUG per_sitio_rows:", per_sitio_rows)  # check console once
        per_sitio_labels = [str(r.get("sitio_name", "Unknown")) for r in per_sitio_rows]
        per_sitio_data   = [int(r.get("resident_count") or 0)   for r in per_sitio_rows]
    except Exception as e:
        messages.error(request, f"Failed loading per-sitio data: {e}")
        per_sitio_labels, per_sitio_data = [], []

    # --- Age brackets (Pie) ---
    try:
        age_rows = Dashboard.sp_age_bracket_distribution()  # no params

        # unwrap if each item is {"jsonb_build_object": {...}}
        cleaned = []
        for item in age_rows or []:
            if isinstance(item, dict) and "jsonb_build_object" in item:
                cleaned.append(item["jsonb_build_object"])
            else:
                cleaned.append(item)

        age_labels = [str(r.get("bracket", "Unknown")) for r in cleaned]
        age_data   = [int(r.get("count") or 0) for r in cleaned]

        total = sum(age_data) or 1
        age_labels_pct = [f"{lbl} ({round((cnt/total)*100)}%)" for lbl, cnt in zip(age_labels, age_data)]
    except Exception as e:
        messages.error(request, f"Failed loading age distribution: {e}")
        age_labels, age_data, age_labels_pct = [], [], []

    ctx = {
        "totals": totals,
        "per_sitio_labels": per_sitio_labels,
        "per_sitio_data": per_sitio_data,
        "age_labels": age_labels,
        "age_labels_pct": age_labels_pct,  # optional pretty legend
        "age_data": age_data,
    }
    return render(request, "secretary_module/secretary_dashboard.html", ctx)

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
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def Addbusiness(request):
    if request.method == "POST":
        try:

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
def Addbusiness(request):
    if request.method == "POST":
        try:

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
    q = (request.GET.get("q") or "").strip() or None
    status = request.GET.get("status") or None
    page = max(int(request.GET.get("page", 1)), 1)
    per_page = max(min(int(request.GET.get("per_page", 10)), 100), 1)
    offset = (page - 1) * per_page

    # ✅ Always use the business list SP so we have business_id in the rows.
    rows  = Business.sp_get_all_businesses(q, status, None, None, None, per_page, offset)
    total = _count_get_all_businesses(q, status)

    total_pages = max(ceil(total / per_page), 1)

    def page_window(curr, last, radius=1):
        if last <= 7:
            return list(range(1, last + 1))
        win = set([1, last])
        for p in range(curr - radius, curr + radius + 1):
            if 1 <= p <= last:
                win.add(p)
        win.add(2); win.add(last - 1)
        return sorted(win)

    page_numbers = page_window(page, total_pages)

    ctx = {
        "rows": rows,
        "q": q or "",
        "status": status or "",
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "page_numbers": page_numbers,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_page": page - 1,
        "next_page": page + 1,
    }

    with connection.cursor() as cur:
        cur.execute("SELECT business_type_id, type_name FROM business_type ORDER BY type_name")
        business_types = [{"id": row[0], "name": row[1]} for row in cur.fetchall()]

    with connection.cursor() as cur:
        cur.execute("SELECT ownership_id, ownership_name FROM ownership ORDER BY ownership_name")
        ownerships = [{"id": row[0], "name": row[1]} for row in cur.fetchall()]

    ctx.update({
        "business_types": business_types,
        "ownerships": ownerships,
    })
    return render(request, "secretary_module/manageBusiness.html", ctx)

def business_detail_json(request, business_id: int):
    """Returns JSON data for one business (for the View modal)."""
    data = Business.sp_get_business_detail(business_id)
    if not data:
        raise Http404("Business not found")
    return JsonResponse(data, safe=False)

def _count_get_all_businesses(q, status):
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) FROM (
              SELECT 1 FROM get_all_businesses(%s, %s, %s, %s, %s, %s, %s)
            ) t
            """,
            [q or None, status or None, None, None, None, 1_000_000_000, 0]
        )
        return cur.fetchone()[0]
    
def _none_if_blank(v):
    if v is None:
        return None
    if isinstance(v, str) and v.strip() == "":
        return None
    return v

def _to_int_or_none(v):
    try:
        return int(v) if _none_if_blank(v) is not None else None
    except (TypeError, ValueError):
        return None

def _to_decimal_or_none(v):
    v = _none_if_blank(v)
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None
    
    return render(request, "secretary_module/manageBusiness.html")

@custom_login_required
@role_required('Barangay Secretary')
@require_http_methods(["POST"])
def business_update(request, business_id: int):
    try:
        personnel_id = int(request.session.get("personnel_id") or 0)
        if not personnel_id:
            return JsonResponse({"ok": False, "message": "No personnel ID in session."}, status=400)

        # Optional owner transfer via name (uses your resolver)
        resident_name = (request.POST.get("resident_name") or "").strip()
        resident_id = None
        if resident_name:
            resident_id = _find_resident_id_by_name(resident_name)

        payload = {
            "business_name":          _none_if_blank(request.POST.get("business_name")),
            "business_type_id":       _to_int_or_none(request.POST.get("business_type_id")),
            "nature_of_business":     _none_if_blank(request.POST.get("nature_of_business")),
            "ownership_id":           _to_int_or_none(request.POST.get("ownership_id")),
            "resident_id":            resident_id,  # only when provided
            "house_number":           _none_if_blank(request.POST.get("house_number")),
            "street":                 _none_if_blank(request.POST.get("street")),
            "barangay":               _none_if_blank(request.POST.get("barangay")),
            "sitio_id":               _to_int_or_none(request.POST.get("sitio_id")),
            "city_municipality":      _none_if_blank(request.POST.get("city_municipality")),
            "country":                _none_if_blank(request.POST.get("country")),
            "total_gross_income":     _to_decimal_or_none(request.POST.get("total_gross_income")),
            "dti_sec_cda_reg_number": _none_if_blank(request.POST.get("dti_sec_cda_reg_number")),
        }

        result = Business.sp_update_business(
            business_id=business_id,
            updated_by=personnel_id,
            **payload
        )
        msg = coerce_message(result)
        return JsonResponse({"ok": True, "message": msg})
    except ValueError as ve:
        return JsonResponse({"ok": False, "message": str(ve)}, status=400)
    except Exception as e:
        return JsonResponse({"ok": False, "message": _clean_db_error(e)}, status=400)

@custom_login_required
@role_required('Barangay Secretary')
@require_http_methods(["POST"])
def business_close(request, business_id: int):
    try:
        personnel_id = int(request.session.get("personnel_id") or 0)
        if not personnel_id:
            return JsonResponse({"ok": False, "message": "No personnel ID in session."}, status=400)

        result = Business.sp_set_closed_business(business_id, personnel_id)
        return JsonResponse({"ok": True, "message": result})
    except Exception as e:
        import traceback
        print("Error in business_close:", traceback.format_exc())
        return JsonResponse({"ok": False, "message": str(e)}, status=400)


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
    review_action = request.POST.get("review_action", "")          

    if action not in ("approve", "reject"):
        set_flash(request, "Invalid request.", "error")
        return redirect("secretary_module:approval")

    try:
        result = Secretary.sp_review_resident_supporting_certificate(
            rid=rid,
            doc_type_id=doc_type_id,
            review_status=action,
            pid=pid,
            review_notes=review_notes,
            review_action=review_action
        )
        msg = coerce_message(result)
        set_flash(request, msg, "success")
    except Exception as e:
        set_flash(request, str(e), "error")

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
