from django.shortcuts import render, redirect
from authentication.decorators import custom_login_required, role_required
from django.utils.http import urlencode
from utils.flash import set_flash, get_flash
from utils.db_message import _clean_db_error, _clean_params, coerce_message
from utils.constants import VALID_SORT_BY, VALID_SORT_DIR, LIMIT_OPTIONS
from .models import (
    Secretary, Dashboard, BusinessFee, AmusementDeviceType, OtherClearanceType,
    BusinessTaxConfig, AnnouncementRepo, Business, SecretaryHelpers,
    
)
from utils.supa import url_for_doc
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
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
from django.template.loader import render_to_string

# PDF generation (HTML -> PDF)
import io, os
from django.conf import settings
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject

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
            dti_sec_cda_reg_num   = request.POST.get("dti_sec_cda_reg_number") or None
            clearance_category_id = int(request.POST.get("clearance_category_id"))
            clearance_date_issued = request.POST.get("clearance_date_issued") or None

            # NEW: total_units (optional overall; required for unitized categories)
            total_units_raw = request.POST.get("total_units")
            total_units = int(total_units_raw) if (total_units_raw not in [None, ""]) else None

            personnel_id          = int(request.session.get("personnel_id"))

            Secretary.sp_register_business(
                resident_id, business_name, business_type_id, nature_of_business, ownership_id,
                house_number, street, barangay, sitio_id, city_municipality, country,
                total_gross_income, dti_sec_cda_reg_num, clearance_category_id,
                total_units,                      # <-- NEW
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
    
    # NEW: clearance categories (includes supported_units from SQL)
    try:
        clearance_categories = Business.sp_get_business_clearance_categories_for_select()
    except Exception:
        clearance_categories = []

    ctx.update({
        "business_types": business_types,
        "ownerships": ownerships,
        "clearance_categories": clearance_categories,
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
            "total_units":            _to_int_or_none(request.POST.get("total_units")),
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
    """List all applications using get_all_application() with search + pagination."""
    q = (request.GET.get('q') or '').strip() or None
    try:
        page = max(int(request.GET.get('page', 1)), 1)
    except Exception:
        page = 1
    try:
        per_page = max(min(int(request.GET.get('per_page', 25)), 100), 1)
    except Exception:
        per_page = 25
    offset = (page - 1) * per_page

    try:
        rows = SecretaryHelpers.list_all_applications(q, per_page, offset)
        total = SecretaryHelpers.count_all_applications(q)
    except Exception as e:
        messages.error(request, f"Failed to load applications: {_clean_db_error(e)}")
        rows, total = [], 0

    total_pages = max(ceil((total or 0) / per_page), 1)
    ctx = {
        'rows': rows,
        'q': q or '',
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_page': page - 1,
        'next_page': page + 1,
    }
    return render(request, 'secretary_module/applications.html', ctx)

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def application_detail_json(request, application_id: int):
    """Return JSON for a specific application using get_specific_application()."""
    try:
        row = SecretaryHelpers.get_specific_application(application_id)
        if not row:
            raise Http404('Application not found')

        # Serialize decimals and datetimes
        from datetime import date, datetime
        from decimal import Decimal as D
        def ser(v):
            if isinstance(v, D): return float(v)
            if isinstance(v, (date, datetime)): return v.isoformat()
            return v
        row = {k: ser(v) for k, v in row.items()}
        return JsonResponse(row)
    except Http404:
        raise
    except Exception as e:
        return JsonResponse({'ok': False, 'message': _clean_db_error(e)}, status=400)

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_POST
def set_application_to_for_payment(request, application_id: int):
    """Move a Pending application to For Payment using set_application_to_for_payment()."""
    try:
        SecretaryHelpers.set_application_to_for_payment(application_id)
        # AJAX vs normal POST
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'message': 'Moved to For Payment'})
        set_flash(request, 'Application moved to For Payment.', 'success')
        return redirect('secretary_module:applications')
    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'message': _clean_db_error(e)}, status=400)
        set_flash(request, _clean_db_error(e), 'error')
        return redirect('secretary_module:applications')

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


# ---- Added at end: dynamic data endpoints used by the addCertificate UI
@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def add_certificate(request):
    """
    Render the create-application page. On GET, load fee types and other clearance purposes
    from the DB helper functions so the template can render dynamic dropdowns.
    """
    # Use SecretaryHelpers to load dropdowns (keeps DB logic in models and
    # uses the new helper container as requested).
    try:
        fee_types = SecretaryHelpers.get_fee_types_dropdown()
    except Exception:
        fee_types = []

    try:
        other_clearances = SecretaryHelpers.get_other_clearance_purposes_dropdown()
    except Exception:
        other_clearances = []

    # Preserve earlier simple render behavior for POST (creation handled elsewhere)
    if request.method == 'POST':
        # For now, let the form post to the same URL and be handled by existing flow (or future implementation)
        return render(request, 'secretary_module/addCertificate.html', {'fee_types': fee_types, 'other_clearances': other_clearances})

    return render(request, 'secretary_module/addCertificate.html', {'fee_types': fee_types, 'other_clearances': other_clearances})


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_POST
def submit_business_application(request):
    """Create a Business application using Create_Application_Business.
    Expects POST fields:
      - fee_type_id (int)
      - business_id (int)
      - business_clearance_category (int)  # category id for business
      - purpose (text)                      # Registration | Renewal | Business Closure
      - videoke_qty, billiard_qty, other_device_qty (ints, optional; used for category 12)
    """
    try:
        fee_type_id = int(request.POST.get('fee_type_id') or 0)
        business_id = int(request.POST.get('business_id') or 0)
        cat_id = int(request.POST.get('business_clearance_category') or request.POST.get('category_id') or 0)
    except (TypeError, ValueError):
        set_flash(request, 'Invalid inputs. Please check your selections.', 'error')
        return redirect('secretary_module:create_application')

    purpose = (request.POST.get('purpose') or '').strip() or None
    vq = _to_int_or_none(request.POST.get('videoke_qty'))
    bq = _to_int_or_none(request.POST.get('billiard_qty'))
    oq = _to_int_or_none(request.POST.get('other_device_qty'))

    # All secretary-side creates are by personnel
    requested_by = 'personnel'

    try:
        app_id = SecretaryHelpers.create_application_business(
            fee_type_id=fee_type_id,
            business_id=business_id,
            business_clearance_category=cat_id,
            videoke_qty=vq,
            billiard_qty=bq,
            other_device_qty=oq,
            purpose=purpose,
            requested_by=requested_by,
        )

        if not app_id:
            set_flash(request, 'Application was not created.', 'error')
            return redirect('secretary_module:create_application')

        set_flash(request, f'Application #{app_id} created.', 'success')
        return redirect('secretary_module:applications')
    except Exception as e:
        set_flash(request, _clean_db_error(e), 'error')
        return redirect('secretary_module:create_application')


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def application_search(request):
    """AJAX search used by the walk-in UI.
    - If fee_type indicates Business (name contains 'Business'), call search_owner(p_query)
    - Otherwise, attempt to call search_resident(p_query) if available; fall back to empty
    Returns JSON array of result objects.
    """
    q = (request.GET.get('q') or '').strip() or None
    fee_name = (request.GET.get('fee_name') or '').strip()
    limit = int(request.GET.get('limit') or 25)
    offset = int(request.GET.get('offset') or 0)

    try:
        if q is None:
            return JsonResponse([], safe=False)

        if fee_name and 'business' in fee_name.lower():
            # Use the DB-level search_owner function via the helper container
            rows = SecretaryHelpers.search_owner(q, limit, offset)
            return JsonResponse(rows, safe=False)
        else:
            # resident search; let search_resident raise if not available
            try:
                rows = Secretary.sp_search_resident(q, limit, offset)
                return JsonResponse(rows, safe=False)
            except Exception:
                # no resident search implementation in DB
                return JsonResponse([], safe=False)
    except Exception as e:
        return JsonResponse({'ok': False, 'message': str(e)}, status=500)


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_POST
def preview_business_clearance(request):
    """Call the DB function secretary_preview_business_clearance and return JSON result.
    Expects form params: business_id (int), purpose (text), videoke_qty, billiard_qty, other_device_qty
    """
    try:
        business_id = int(request.POST.get('business_id') or 0)
    except (TypeError, ValueError):
        # Include posted keys to aid debugging (no sensitive data expected here)
        return JsonResponse({
            'ok': False,
            'message': 'Invalid or missing business_id',
            'posted_keys': list(request.POST.keys())
        }, status=400)

    purpose = request.POST.get('purpose')
    try:
        videoke_qty = _to_int_or_none(request.POST.get('videoke_qty'))
        billiard_qty = _to_int_or_none(request.POST.get('billiard_qty'))
        other_device_qty = _to_int_or_none(request.POST.get('other_device_qty'))
    except Exception:
        videoke_qty = billiard_qty = other_device_qty = None

    try:
        # Use the helper container which delegates to the DB function
        preview = SecretaryHelpers.secretary_preview_business_clearance(
            business_id, purpose, videoke_qty, billiard_qty, other_device_qty
        )
        if not preview:
            return JsonResponse({'ok': False, 'message': 'No preview data returned'}, status=404)
        resp = {
            'ok': True,
            'business_id': preview.get('business_id'),
            'category_id': preview.get('category_id'),
            'business_status': preview.get('business_status'),
            'purpose': preview.get('purpose'),
            'total_amount': float(preview.get('total_amount')) if preview.get('total_amount') is not None else None,
            'total_amount_details': preview.get('total_amount_details'),
        }
        return JsonResponse(resp)
    except Exception as e:
        return JsonResponse({'ok': False, 'message': _clean_db_error(e)}, status=400)


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def print_application(request, application_id: int):
    """Deprecated HTML print: redirect to the PDF generator instead."""
    return redirect('secretary_module:print_application_pdf', application_id=application_id)


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def print_application_pdf(request, application_id: int):
    """Fill the Business Clearance PDF (Template2_Business_Clearance_LETTER.pdf) with DB fields.

    Fields filled (if available): business_name, owners_name, full_address, nature_of_business,
    day, month, year, paid, fulldate_issue, or_number, fullname_captain.

    Falls back to HTML printable view if anything fails.
    """
    # Step 1: Fetch and normalize context
    try:
        row = SecretaryHelpers.get_clearance_details_for_printing(application_id)
        if not row:
            raise Http404('Application not found or no printable details.')

        from datetime import date, datetime
        from decimal import Decimal as D

        def ser(v):
            if isinstance(v, D):
                return float(v)
            if isinstance(v, (date, datetime)):
                return v
            return v

        ctx = {k: ser(v) for k, v in row.items()}
        ctx.setdefault('application_id', application_id)
    except Http404:
        raise
    except Exception as e:
        messages.error(request, _clean_db_error(e))
        return redirect('secretary_module:applications')

    # Step 2: Try fill the AcroForm PDF; on failure, render HTML with a message
    try:
        # Locate the template PDF under static/prints (old theme/templates/prints fallback removed)
        template_candidates = [
            os.path.join(settings.BASE_DIR, 'static', 'prints', 'Template2_Business_Clearance_LETTER.pdf'),
        ]
        template_path = next((p for p in template_candidates if os.path.exists(p)), None)
        if not template_path:
            messages.error(request, 'PDF generation error: template not found.')
            return redirect('secretary_module:applications')

        # Build field values
        paid_val = ctx.get('paid')
        try:
            if paid_val is not None:
                paid_val = float(paid_val)
        except Exception:
            pass
        paid_str = (
            f"₱{paid_val:,.2f}" if isinstance(paid_val, (int, float)) else (str(paid_val) if paid_val is not None else '')
        )

        fulldate = ctx.get('fulldate_issue')
        day = ctx.get('day')
        month = ctx.get('month')
        year = ctx.get('year')
        try:
            # If fulldate provided and parts are missing, derive them
            if fulldate and (not day or not month or not year):
                day = day or f"{getattr(fulldate, 'day', '')}"
                try:
                    # month name
                    month = month or getattr(fulldate, 'strftime', lambda *_: '')('%B')
                except Exception:
                    month = month or ''
                year = year or f"{getattr(fulldate, 'year', '')}"
        except Exception:
            pass

        # Build dict for AcroForm
        fields = {
            'business_name':    ctx.get('business_name') or '',
            'owners_name':      ctx.get('owners_name') or '',
            'full_address':     ctx.get('full_address') or '',
            'nature_of_business': ctx.get('nature_of_business') or '',
            'day':              str(day or ''),
            'month':            str(month or ''),
            'year':             str(year or ''),
            'paid':             paid_str,
            'fulldate_issue':   getattr(fulldate, 'strftime', lambda *_: '')('%B %d, %Y') if fulldate else (ctx.get('fulldate_issue') or ''),
            'or_number':        str(ctx.get('or_number') or ''),
            'fullname_captain': ctx.get('fullname_captain') or '',
        }

        reader = PdfReader(template_path)
        writer = PdfWriter()
        writer.append_pages_from_reader(reader)

        # Copy AcroForm from the template (some viewers require this for field rendering)
        try:
            acro = reader.trailer[NameObject('/Root')].get(NameObject('/AcroForm'))
            if acro is not None:
                writer._root_object.update({NameObject('/AcroForm'): acro})
                # Set NeedAppearances on the AcroForm itself
                try:
                    writer._root_object[NameObject('/AcroForm')].get_object().update({
                        NameObject('/NeedAppearances'): BooleanObject(True)
                    })
                except Exception:
                    pass
        except Exception:
            # Fallback: set NeedAppearances on root (some renderers honor this)
            try:
                writer._root_object.update({
                    NameObject('/AcroForm'): writer._root_object.get(NameObject('/AcroForm'), {})
                })
                writer._root_object[NameObject('/AcroForm')].update({
                    NameObject('/NeedAppearances'): BooleanObject(True)
                })
            except Exception:
                pass

        # Update fields for each page (safe if fields appear on only one page)
        for page in writer.pages:
            try:
                writer.update_page_form_field_values(page, fields)
            except Exception:
                # continue filling other pages even if one update fails
                continue

        # If nothing got filled (all values empty), attempt to hint field names in DEBUG
        try:
            if settings.DEBUG:
                avail = {}
                try:
                    # pypdf provides get_form_text_fields on the reader
                    avail = getattr(reader, 'get_form_text_fields', lambda: {})() or {}
                except Exception:
                    avail = {}
                # If we didn't match any field name, surface a message once
                if avail and not any(k in avail for k in fields.keys()):
                    messages.warning(request, f"PDF form fields not matched. Available: {', '.join(sorted(avail.keys()))}")
        except Exception:
            pass

        # Stream to HTTP response
        pdf_bytes = io.BytesIO()
        writer.write(pdf_bytes)
        pdf_bytes.seek(0)

        response = HttpResponse(pdf_bytes.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="application_{application_id}.pdf"'
        return response
    except Exception:
        messages.error(request, 'PDF generation error.')
        return redirect('secretary_module:applications')
