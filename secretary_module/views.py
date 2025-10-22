from django.shortcuts import render, redirect
from authentication.decorators import custom_login_required, role_required
from django.utils.http import urlencode
from utils.flash import set_flash, get_flash
from utils.db_message import _clean_db_error, _clean_params, coerce_message
from utils.constants import VALID_SORT_BY, VALID_SORT_DIR, LIMIT_OPTIONS
from .models import Secretary, Business, Dashboard, BusinessFee, AmusementDeviceType, OtherClearanceType, BusinessTaxConfig, AnnouncementRepo
from utils.supa import url_for_doc
from django.http import JsonResponse, HttpResponseBadRequest
from django.db import connection
from math import ceil
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods
from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.conf import settings
from django.core.files.storage import default_storage
from datetime import datetime
from django.views.decorators.http import require_POST

_UI_TO_SQL_AUDIENCE = {
    'EVERYONE': 'both',
    'PERSONNEL': 'personnel',
    'RESIDENTS': 'resident',
    'both': 'both', 'personnel': 'personnel', 'resident': 'resident',  # tolerate lowercase
}
_SQL_TO_UI_AUDIENCE = {
    'both': 'EVERYONE',
    'personnel': 'PERSONNEL',
    'resident': 'RESIDENTS',
}


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def secretary_dashboard(request):
    barangay = request.GET.get("barangay") or None
    city     = request.GET.get("city") or None

    # ---- Totals (KPIs) ----
    try:
        totals = Dashboard.sp_dashboard_totals(barangay=barangay, city=city)
    except Exception as e:
        messages.error(request, f"Failed loading totals: {e}")
        totals = {
            "total_resident": 0, "total_non_resident": 0, "total_pending": 0,
            "total_male": 0, "total_female": 0
        }

    # ---- Residents per sitio (bar chart) ----
    try:
        per_sitio_rows   = Dashboard.sp_residents_per_sitio_json()
        per_sitio_labels = [str(r.get("sitio_name", "Unknown")) for r in per_sitio_rows]
        per_sitio_data   = [int(r.get("resident_count") or 0)   for r in per_sitio_rows]
    except Exception as e:
        messages.error(request, f"Failed loading per-sitio data: {e}")
        per_sitio_labels, per_sitio_data = [], []

    # ---- Age distribution (pie) ----
    try:
        age_rows = Dashboard.sp_age_bracket_distribution()
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

    # ===========================
    # Announcements (Secretary sees personnel + both)
    # ===========================
    ALLOWED = {"personnel", "both"}

    # Pull a few recent then filter to ALLOWED and take top 3
    try:
        # ask for more than 3, then slice after filtering to ensure we still get 3
        rows = AnnouncementRepo.list_all(sort='date_desc', limit=12, audience=None)
        latest_announcements = []
        for a in rows:
            # normalize aliases
            if 'created_date' in a and 'announcement_date' not in a:
                a['announcement_date'] = a['created_date']
            aud = (a.get('audience') or 'both').lower()
            if aud in ALLOWED:
                a['audience'] = aud
                latest_announcements.append(a)
            if len(latest_announcements) >= 3:
                break
    except Exception as e:
        messages.error(request, f"Failed loading latest announcements: {e}")
        latest_announcements = []

    # Modal filters (GET -> ann_*)
    ann_q        = (request.GET.get('ann_q') or '').strip() or None
    ann_aud      = (request.GET.get('ann_audience') or '').strip() or None  # '', resident, personnel, both
    ann_from_str = (request.GET.get('ann_from') or '').strip()
    ann_to_str   = (request.GET.get('ann_to') or '').strip()

    ann_from = ann_to = None
    try:
        if ann_from_str:
            ann_from = datetime.strptime(ann_from_str, '%Y-%m-%d').date()
        if ann_to_str:
            ann_to = datetime.strptime(ann_to_str, '%Y-%m-%d').date()
    except ValueError:
        messages.warning(request, 'Invalid date filter for announcements.')

    # Full list for the modal (server filter + enforce secretary scope)
    try:
        announcements_all = AnnouncementRepo.list_all(
            q=ann_q, date_from=ann_from, date_to=ann_to,
            created_by=None, sort='date_desc', limit=200, offset=0,
            audience=ann_aud or None   # None = DB shows all audiences
        )
        filtered = []
        for a in announcements_all:
            if 'created_date' in a and 'announcement_date' not in a:
                a['announcement_date'] = a['created_date']
            a['audience'] = (a.get('audience') or 'both').lower()
            if a['audience'] in ALLOWED:
                filtered.append(a)
        announcements_all = filtered
    except Exception as e:
        messages.error(request, f"Failed loading announcements list: {e}")
        announcements_all = []

    ann_open = request.GET.get('ann_open') == '1'

    ctx = {
        "totals": totals,
        "per_sitio_labels": per_sitio_labels,
        "per_sitio_data": per_sitio_data,
        "age_labels": age_labels,
        "age_labels_pct": age_labels_pct,
        "age_data": age_data,

        "latest_announcements": latest_announcements,
        "announcements_all": announcements_all,
        "ann_filters": {
            "q": ann_q or "",
            "audience": (ann_aud or ""),
            "from": ann_from_str,
            "to": ann_to_str,
        },
        "ann_open": ann_open,
    }
    return render(request, "secretary_module/secretary_dashboard.html", ctx)

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def resident_list(request):
    return render(request, 'secretary_module/resident_list.html')

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def household_list(request):
    return render(request, 'secretary_module/household_list.html')

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
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
    # load dropdown options
    try:
        clearance_categories = Business.sp_get_business_clearance_categories_for_select()
    except Exception as e:
        clearance_categories = []
        set_flash(request, f"Could not load clearance categories: {e}", "error")

    if request.method == "POST":
        try:
            resident_name = request.POST.get("resident_name")
            resident_id = _find_resident_id_by_name(resident_name)

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
            dti_sec_cda_reg_num   = request.POST.get("dti_sec_cda_reg_number") or None  # optional
            clearance_category_id = int(request.POST.get("clearance_category_id"))       # from dropdown
            clearance_date_issued = request.POST.get("clearance_date_issued") or None
            personnel_id          = int(request.session.get("personnel_id"))

            Secretary.sp_register_business(
                resident_id, business_name, business_type_id, nature_of_business, ownership_id,
                house_number, street, barangay, sitio_id, city_municipality, country,
                total_gross_income, dti_sec_cda_reg_num, clearance_category_id,
                clearance_date_issued, personnel_id
            )
            set_flash(request, "Successfully Submitted", "success")
        except Exception as e:
            set_flash(request, str(e), "error")

    flash = get_flash(request)
    return render(request, "secretary_module/Addbusiness.html", {
        'message': flash.get('message'),
        'message_level': flash.get('message_level'),
        'clearance_categories': clearance_categories,
    })


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def businessDetail1(request):
    return render(request, 'secretary_module/businessDetail1.html')

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def businessDetail2(request):
    return render(request, 'secretary_module/businessDetail2.html')

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def businessDetail3(request):
    return render(request, 'secretary_module/businessDetail3.html')

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
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
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_http_methods(["POST"])
def business_update(request, business_id: int):
    try:
        personnel_id = int(request.session.get("personnel_id") or 0)
        if not personnel_id:
            return JsonResponse({"ok": False, "message": "No personnel ID in session."}, status=400)

        # Current state (for rule checks)
        current = Business.sp_get_business_detail(business_id) or {}
        curr_own = int(current.get('ownership_id') or 0)
        curr_cat = int(current.get('clearance_category_id') or 0)

        # Optional owner transfer via name (uses your resolver)
        resident_name = (request.POST.get("resident_name") or "").strip()
        resident_id = None
        if resident_name:
            # Owner change only if NOT sole proprietorship (id=1)
            if curr_own == 1:
                return JsonResponse({"ok": False, "message": "Owner cannot be changed for Sole Proprietorship."}, status=400)
            resident_id = _find_resident_id_by_name(resident_name)

        # New (requested) clearance category
        new_cat = _to_int_or_none(request.POST.get("clearance_category_id"))

        # Rule: Clearance Category can change only:
        # - Sole Prop (3/4): within {3,4}
        # - Lessor (6..10): within 6..10
        # - Others: cannot change
        if new_cat is not None and new_cat != curr_cat:
            if curr_cat in (3, 4):
                if new_cat not in (3, 4):
                    return JsonResponse({"ok": False, "message": "Sole Proprietorship may switch only between categories 3 and 4."}, status=400)
            elif 6 <= curr_cat <= 10:
                if not (6 <= new_cat <= 10):
                    return JsonResponse({"ok": False, "message": "Lessor categories may switch only within 6–10."}, status=400)
            else:
                return JsonResponse({"ok": False, "message": "This clearance category cannot be changed."}, status=400)

        # Build payload (leave non-editables as None so proc won’t touch them)
        payload = {
            "business_name":          _none_if_blank(request.POST.get("business_name")),
            "business_type_id":       None,  # not editable
            "nature_of_business":     _none_if_blank(request.POST.get("nature_of_business")),
            "ownership_id":           None,  # not editable
            "resident_id":            resident_id,  # only when provided and allowed
            "house_number":           _none_if_blank(request.POST.get("house_number")),
            "street":                 _none_if_blank(request.POST.get("street")),
            "barangay":               _none_if_blank(request.POST.get("barangay")),
            "sitio_id":               _to_int_or_none(request.POST.get("sitio_id")),
            "city_municipality":      _none_if_blank(request.POST.get("city_municipality")),
            "country":                _none_if_blank(request.POST.get("country")),
            "total_gross_income":     _to_decimal_or_none(request.POST.get("total_gross_income")),
            "clearance_category_id":  new_cat,   # may be None if unchanged or not allowed
            "dti_sec_cda_reg_number": None,      # not editable
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
        return JsonResponse({"ok": False, "message": _clean_db_error(e)}, status=400)\
        
@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_POST
def business_close(request, business_id: int):
    """
    Marks a business as Closed via the SQL function.
    Only Secretary / Assistant Secretary can do this (enforced here and in SQL).
    """
    try:
        personnel_id = int(request.session.get("personnel_id") or 0)
        if not personnel_id:
            return JsonResponse({"ok": False, "message": "No personnel ID in session."}, status=400)

        msg = Business.sp_set_closed_business(business_id, personnel_id)
        return JsonResponse({"ok": True, "message": msg})
    except Exception as e:
        # Return DB error (your SQL has nice messages)
        return JsonResponse({"ok": False, "message": str(e)}, status=400)

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def add_certificate(request):
    return render(request, 'secretary_module/addCertificate.html')

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def manageCert1(request):
    return render(request, 'secretary_module/manageCert1.html')

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def manageCert2(request):
    return render(request, 'secretary_module/manageCert2.html')

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def applications(request):
    return render(request, 'secretary_module/applications.html')

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def announcement(request):
    return render(request, 'secretary_module/announcement.html')

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
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
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
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
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
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

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def businessFee(request):
    try:
        categories = BusinessFee.sp_get_all_business_clearance_cat()
    except Exception as e:
        messages.error(request, f"Could not load fee categories: {e}")
        categories = []
    return render(request, 'secretary_module/businessFee.html', {"categories": categories})

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def business_fee_update(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Method not allowed"}, status=405)

    def to_decimal(val):
        if val in (None, "", "null", "None"):
            return None
        try:
            return Decimal(val)
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError("Invalid decimal value")

    def to_int(val):
        if val in (None, "", "null", "None"):
            return None
        return int(val)

    try:
        cid = int(request.POST.get("clearance_category_id"))
        base_fee = to_decimal(request.POST.get("base_fee"))
        addl = to_decimal(request.POST.get("additional_fee_per_unit"))
        min_units = to_int(request.POST.get("minimum_units"))

        # ✅ pull personnel_id from session (consistent with other views)
        try:
            updated_by = int(request.session.get("personnel_id") or 0)
        except (TypeError, ValueError):
            updated_by = 0
        if not updated_by:
            return JsonResponse({"ok": False, "error": "No personnel ID in session."}, status=400)

        message = BusinessFee.sp_update_business_clearance_category(
            cid, base_fee, addl, min_units, updated_by
        )

        row = BusinessFee.sp_get_specific_business_clearance_cat(cid)

        from datetime import date, datetime
        from decimal import Decimal as D
        def ser(v):
            if isinstance(v, D): return float(v)
            if isinstance(v, (date, datetime)): return v.isoformat()
            return v

        row = {k: ser(v) for k, v in (row or {}).items()}
        return JsonResponse({"ok": True, "message": message, "row": row})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)


# --- List page
@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def amusement(request):
    try:
        devices = AmusementDeviceType.sp_get_all_amusement_device_type()
    except Exception as e:
        messages.error(request, f"Could not load amusement device types: {e}")
        devices = []
    return render(request, 'secretary_module/amusement.html', {"devices": devices})

# --- Update endpoint (Fee per unit)
@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def amusement_update(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Method not allowed"}, status=405)

    def to_decimal(val):
        if val in (None, "", "null", "None"):
            return None
        from decimal import Decimal, InvalidOperation
        try:
            return Decimal(val)
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError("Invalid decimal value")

    try:
        raw_id = request.POST.get("device_type_id")
        try:
            device_type_id = int(raw_id)
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "error": "Invalid or missing device_type_id."}, status=400)

        fee_per_unit = to_decimal(request.POST.get("fee_per_unit"))

        # who’s updating?
        updated_by = (lambda s: int(s) if s and str(s).isdigit() else None)(request.session.get("personnel_id"))
        if not updated_by:
            return JsonResponse({"ok": False, "error": "No personnel ID in session."}, status=400)

        message = AmusementDeviceType.sp_update_amusement_device_type(
            device_type_id, fee_per_unit, updated_by
        )

        row = AmusementDeviceType.sp_get_specific_amusement_device_type(device_type_id)

        from datetime import date, datetime
        from decimal import Decimal as D
        def ser(v):
            if isinstance(v, D): return float(v)
            if isinstance(v, (date, datetime)): return v.isoformat()
            return v
        row = {k: ser(v) for k, v in (row or {}).items()}

        return JsonResponse({"ok": True, "message": message, "row": row})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
    
@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def other_clearances(request):
    try:
        rows = OtherClearanceType.sp_get_all_other_barangay_clearance_type()
    except Exception as e:
        messages.error(request, f"Could not load other clearances: {e}")
        rows = []
    return render(request, "secretary_module/otherClearances.html", {"rows": rows})

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def other_clearances_update(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Method not allowed"}, status=405)

    def to_decimal(val):
        if val in (None, "", "null", "None"):
            return None
        try:
            return Decimal(val)
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError("Invalid decimal value")

    try:
        raw_id = request.POST.get("clearance_type_id")
        try:
            clearance_type_id = int(raw_id)
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "error": "Invalid or missing clearance_type_id."}, status=400)

        fee = to_decimal(request.POST.get("fee"))

        updated_by = _get_personnel_id(request)
        if not updated_by:
            return JsonResponse({"ok": False, "error": "No personnel ID in session."}, status=400)

        message = OtherClearanceType.sp_update_other_barangay_clearance_type(
            clearance_type_id, fee, updated_by
        )

        # fresh row
        row = OtherClearanceType.sp_get_specific_other_barangay_clearance_type(clearance_type_id)

        # serialize Decimals/Datetimes
        from datetime import date, datetime
        from decimal import Decimal as D
        def ser(v):
            if isinstance(v, D): return float(v)
            if isinstance(v, (date, datetime)): return v.isoformat()
            return v
        row = {k: ser(v) for k, v in (row or {}).items()}

        return JsonResponse({"ok": True, "message": message, "row": row})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
    
def _get_personnel_id(request):
    try:
        pid = int(request.session.get("personnel_id") or 0)
        return pid if pid > 0 else None
    except (TypeError, ValueError):
        return None
    

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def tax_penalties(request):
    try:
        cfg = BusinessTaxConfig.sp_get_current_business_tax_config() or {}
    except Exception as e:
        messages.error(request, f"Could not load tax configuration: {e}")
        cfg = {}
    months = list(range(1, 13))
    return render(request, "secretary_module/taxPenalties.html", {"cfg": cfg, "months": months})

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def tax_penalties_update(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Method not allowed"}, status=405)

    def dec_or_none(v):
        if v in (None, "", "null", "None"):
            return None
        from decimal import Decimal, InvalidOperation
        try:
            return Decimal(str(v))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError("Invalid number.")

    def int_or_none(v):
        if v in (None, "", "null", "None"):
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            raise ValueError("Invalid integer.")

    try:
        # inputs (blank -> None so SQL treats them as "no change")
        th   = dec_or_none(request.POST.get("threshold_amount"))
        at   = dec_or_none(request.POST.get("rate_percent_at_or_below"))
        abv  = dec_or_none(request.POST.get("rate_percent_above"))
        winS = int_or_none(request.POST.get("window_month_start"))
        winE = int_or_none(request.POST.get("window_month_end"))
        mir  = dec_or_none(request.POST.get("monthly_interest_percent"))

        # who is updating?
        pid = request.session.get("personnel_id")
        try:
            pid = int(pid) if pid else None
        except (TypeError, ValueError):
            pid = None
        if not pid:
            return JsonResponse({"ok": False, "error": "No personnel ID in session."}, status=400)

        # get config_id (from current row or hidden input)
        cfg = BusinessTaxConfig.sp_get_current_business_tax_config() or {}
        config_id = cfg.get("config_id") or request.POST.get("config_id")
        try:
            config_id = int(config_id)
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "error": "No config to update. Seed a row first."}, status=400)

        # call SP: (config_id FIRST)
        message = BusinessTaxConfig.sp_update_business_tax_config(
            config_id,
            th, at, abv, winS, winE, mir, pid
        )

        # return fresh row
        row = BusinessTaxConfig.sp_get_current_business_tax_config() or {}
        from datetime import date, datetime
        from decimal import Decimal as D
        def ser(v):
            if isinstance(v, D): return float(v)
            if isinstance(v, (date, datetime)): return v.isoformat()
            return v
        row = {k: ser(v) for k, v in row.items()}
        return JsonResponse({"ok": True, "message": message, "row": row})

    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
    

def _acting_personnel_id(request) -> int:
    return (
        getattr(getattr(request, 'user', None), 'personnel_id', None)
        or request.session.get('personnel_id')
        or 1
    )

def _public_url(request, path: str | None):
    """
    Normalize DB-stored image paths so the template always gets a usable URL.
    - absolute http(s): return as-is
    - root-relative (starts with /): build absolute (so it works in emails or iframes)
    - plain relative like 'announcements/x.jpg': prefix MEDIA_URL and build absolute
    """
    if not path:
        return None
    if path.startswith('http://') or path.startswith('https://'):
        return path
    if path.startswith('/'):
        return request.build_absolute_uri(path)
    base = settings.MEDIA_URL or '/media/'
    if not base.endswith('/'):
        base += '/'
    return request.build_absolute_uri(base + path.lstrip('/'))

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def announcement(request):
    ctx = {'errors': []}
    personnel_id = _acting_personnel_id(request)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action in ('create', 'update'):
            header_title = (request.POST.get('header_title') or '').strip()
            details = (request.POST.get('details') or '').strip()
            event_date_str = (request.POST.get('announcement_at_date') or '').strip()
            raw_audience = (request.POST.get('audience') or 'EVERYONE').strip()
            audience = _UI_TO_SQL_AUDIENCE.get(raw_audience)

            event_date = None
            if event_date_str:
                try:
                    event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
                except ValueError:
                    ctx['errors'].append('Invalid Event Date.')

            if audience is None:
                ctx['errors'].append('Invalid audience selection.')
            if not header_title:
                ctx['errors'].append('Title is required.')
            if not details:
                ctx['errors'].append('Content is required.')

            # optional image upload
            image_db_path = None
            f = request.FILES.get('image')
            if f:
                saved = default_storage.save(f"announcements/{f.name}", f)  # store relative path
                image_db_path = saved

            try:
                if action == 'create' and not ctx['errors']:
                    new_id = AnnouncementRepo.create(
                        header_title=header_title,
                        details=details,
                        image_path=image_db_path,
                        created_by=personnel_id,
                        event_date=event_date,
                        audience=audience
                    )
                    return redirect(f"{request.path}?id={new_id}")

                elif action == 'update' and not ctx['errors']:
                    upd_id = request.POST.get('announcement_id')
                    if not upd_id:
                        ctx['errors'].append('Missing announcement id.')
                    else:
                        AnnouncementRepo.update(
                            announcement_id=int(upd_id),
                            updated_by=personnel_id,
                            header_title=header_title,
                            details=details,
                            image_path=image_db_path,
                            event_date=event_date,
                            audience=audience
                        )
                        return redirect(f"{request.path}?id={upd_id}")

            except Exception as e:
                ctx['errors'].append(str(e))
                # fall through to re-render with errors

            ctx['post_data'] = {
                'header_title': header_title,
                'details': details,
                'announcement_at_date': event_date_str,
                'audience': raw_audience,
            }

        elif action == 'delete':
            try:
                del_id = int(request.POST.get('announcement_id'))
                AnnouncementRepo.delete(del_id, personnel_id)
                return redirect(request.path)  # no id -> will show latest or empty
            except Exception as e:
                ctx['errors'].append(str(e))

    # GET: list + selected
    selected_id = request.GET.get('id')
    # (optional) list filter: ?audience=resident|personnel|both
    list_audience = request.GET.get('audience')
    announcements = AnnouncementRepo.list_all(sort='date_desc', limit=100, audience=list_audience)

    selected = None
    if selected_id:
        selected = AnnouncementRepo.get_one(int(selected_id))
    elif announcements:
        selected = AnnouncementRepo.get_one(int(announcements[0]['announcement_id']))

    # normalize image URL for the selected item (keeps your existing behavior)
    if selected and 'announcement_image_path' in selected:
        selected['image_url'] = _public_url(request, selected.get('announcement_image_path'))

    # normalize audience to what your template expects (EVERYONE | PERSONNEL | RESIDENTS)
    if selected and selected.get('audience'):
        selected['audience'] = _SQL_TO_UI_AUDIENCE.get(selected['audience'], 'EVERYONE')

    # compatibility aliases if your SQL returns created_date instead of date / announcement_date
    if selected and 'created_date' in selected and 'date' not in selected:
        selected['date'] = selected['created_date']
    for a in announcements:
        if 'created_date' in a and 'announcement_date' not in a:
            a['announcement_date'] = a['created_date']

    ctx.update({'announcements': announcements, 'selected': selected})
    return render(request, 'secretary_module/announcement.html', ctx)