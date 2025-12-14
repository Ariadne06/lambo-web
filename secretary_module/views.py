from django.shortcuts import render, redirect
from authentication.decorators import custom_login_required, role_required
from django.utils.http import urlencode
from utils.flash import set_flash, get_flash
from utils.db_message import _clean_db_error, _clean_params, coerce_message
from utils.constants import VALID_SORT_BY, VALID_SORT_DIR, LIMIT_OPTIONS
from .models import (
    Secretary, Dashboard, BusinessFee, AmusementDeviceType, OtherClearanceType,
    BusinessTaxConfig, CTCFeeConfig, AnnouncementRepo, Business, SecretaryHelpers,ResidentList
)
from utils.supa import url_for_doc
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.db import connection
from math import ceil
from django.core.paginator import Paginator
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods
from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.conf import settings
from django.core.files.storage import default_storage
from datetime import datetime
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from urllib.parse import urlencode
from household_module.models import Household, Family
import json
from django.views.decorators.http import require_GET
from notifications.service import NotificationService
from supabase import create_client, Client
import logging
import uuid
import os

logger = logging.getLogger(__name__)

# PDF generation (HTML -> PDF)
import io, os
from django.conf import settings
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject, NumberObject

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

def _to_list(val):
    if val is None: return []
    if isinstance(val, (list, tuple)): return [str(v) for v in val]
    s = str(val).strip()
    try:
        j = json.loads(s)
        if isinstance(j, list):
            return [str(v) for v in j]
    except Exception:
        pass
    return [p.strip().strip('[]{}()"\'') for p in s.split(',') if p.strip()]


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
    q = request.GET.get("q") or None
    # Support multiple status and sitio filters
    status_id_list = request.GET.getlist("status_id")
    sitio_id_list = request.GET.getlist("sitio_id")
    quarter_id = request.GET.get("quarter_id") or None
    page = int(request.GET.get("page") or 1)
    page_size = int(request.GET.get("page_size") or 50)

    # Convert to integers and filter out invalid values
    status_id_list = [int(s) for s in status_id_list if s and s.isdigit()]
    sitio_id_list = [int(s) for s in sitio_id_list if s and s.isdigit()]
    
    # Parse quarter_id
    if quarter_id and quarter_id.isdigit():
        quarter_id = int(quarter_id)
    else:
        quarter_id = None
    
    # Ensure page is at least 1
    page = max(1, page)
    page_size = max(1, min(page_size, 200))  # Cap at 200 to prevent huge queries
    
    # Calculate offset
    offset = (page - 1) * page_size

    # If multiple filters selected, we need to fetch and filter in Python
    # since the DB function only accepts single values
    if len(status_id_list) > 1 or len(sitio_id_list) > 1:
        # Fetch all matching residents (no limit) and filter in Python
        all_residents = []
        
        # If we have multiple statuses, fetch for each
        if len(status_id_list) > 1:
            for status_id in status_id_list:
                sitio_id = sitio_id_list[0] if sitio_id_list else None
                residents_batch = ResidentList.sp_get_all_residents(
                    p_status_id=status_id,
                    p_sitio_id=sitio_id,
                    p_query=q,
                    p_limit=None,
                    p_offset=0,
                    p_quarter_id=quarter_id
                )
                all_residents.extend(residents_batch)
        # If we have multiple sitios but single status
        elif len(sitio_id_list) > 1:
            status_id = status_id_list[0] if status_id_list else None
            for sitio_id in sitio_id_list:
                residents_batch = ResidentList.sp_get_all_residents(
                    p_status_id=status_id,
                    p_sitio_id=sitio_id,
                    p_query=q,
                    p_limit=None,
                    p_offset=0,
                    p_quarter_id=quarter_id
                )
                all_residents.extend(residents_batch)
        
        # Remove duplicates based on resident_id
        seen_ids = set()
        unique_residents = []
        for r in all_residents:
            if r.get('resident_id') not in seen_ids:
                seen_ids.add(r.get('resident_id'))
                unique_residents.append(r)
        
        # Calculate totals and pagination
        total = len(unique_residents)
        total_pages = max(1, ceil(total / page_size)) if page_size else 1
        
        # Apply manual pagination
        start_idx = offset
        end_idx = offset + page_size
        residents = unique_residents[start_idx:end_idx]
        
        # Set single values to None for context (not used when multiple filters)
        status_id = None
        sitio_id = None
    else:
        # Single or no filters - use DB function directly (more efficient)
        status_id = status_id_list[0] if status_id_list else None
        sitio_id = sitio_id_list[0] if sitio_id_list else None
        
        # Get total count for pagination
        total = ResidentList.sp_get_all_residents_count(
            p_status_id=status_id,
            p_sitio_id=sitio_id,
            p_query=q,
            p_quarter_id=quarter_id
        )

        # Get paginated residents
        residents = ResidentList.sp_get_all_residents(
            p_status_id=status_id,
            p_sitio_id=sitio_id,
            p_query=q,
            p_limit=page_size,
            p_offset=offset,
            p_quarter_id=quarter_id
        )

        # Calculate pagination info
        total_pages = max(1, ceil(total / page_size)) if page_size else 1
    
    # Get filter options
    with connection.cursor() as cur:
        cur.execute("SELECT status_id, status_name FROM Resident_Status ORDER BY status_name;")
        status_options = [{"id": row[0], "name": row[1]} for row in cur.fetchall()]
        
        cur.execute("SELECT sitio_id, sitio_name FROM Sitio ORDER BY sitio_name;")
        sitio_options = [{"id": row[0], "name": row[1]} for row in cur.fetchall()]
    
    # Get quarters for dropdown
    quarters = ResidentList.sp_get_all_quarters()

    # Build URL helper
    def build_url(**overrides):
        params = {
            "q": q or "",
            "page": page,
            "page_size": page_size,
        }
        
        # Handle quarter_id
        if "quarter_id" in overrides:
            qid_override = overrides.pop("quarter_id")
            if qid_override and qid_override != "":
                params["quarter_id"] = qid_override
        elif quarter_id:
            params["quarter_id"] = quarter_id
        
        # Handle status_id - default to current list unless overridden
        if "status_id" in overrides:
            status_override = overrides.pop("status_id")
            if status_override and status_override != "":
                if isinstance(status_override, list):
                    for s in status_override:
                        params[f"status_id"] = s  # Will be handled by urlencode with doseq
                else:
                    params["status_id"] = status_override
        else:
            # Use current status_id_list
            if status_id_list:
                params["status_id"] = status_id_list
        
        # Handle sitio_id - default to current list unless overridden  
        if "sitio_id" in overrides:
            sitio_override = overrides.pop("sitio_id")
            if sitio_override and sitio_override != "":
                if isinstance(sitio_override, list):
                    for s in sitio_override:
                        params[f"sitio_id"] = s
                else:
                    params["sitio_id"] = sitio_override
        else:
            # Use current sitio_id_list
            if sitio_id_list:
                params["sitio_id"] = sitio_id_list
        
        params.update(overrides)
        # Remove empty params
        params = {k: v for k, v in params.items() if v not in (None, "", [])}
        return f"?{urlencode(params, doseq=True)}"

    # Pagination URLs
    prev_url = build_url(page=page - 1) if page > 1 else None
    next_url = build_url(page=page + 1) if page < total_pages else None
    
    # Page items for pagination display (show current, +/- 1, and last)
    page_items = []
    for p in range(max(1, page - 1), min(total_pages + 1, page + 2)):
        page_items.append({
            "num": p,
            "url": build_url(page=p),
            "current": p == page
        })
    
    # Add ellipsis and last page if needed
    if page + 2 < total_pages:
        page_items.append({"ellipsis": True})
        page_items.append({
            "num": total_pages,
            "url": build_url(page=total_pages),
            "current": False
        })

    # Active filter chips
    status_chips = []
    sitio_chips = []
    
    # Build chips for each selected status
    for sid in status_id_list:
        status_name = next((s["name"] for s in status_options if s["id"] == sid), f"Status {sid}")
        # Build URL that removes this specific status
        other_statuses = [s for s in status_id_list if s != sid]
        status_chips.append({
            "label": status_name,
            "url": build_url(status_id=other_statuses, page=1) if other_statuses else build_url(status_id="", page=1)
        })
    
    # Build chips for each selected sitio
    for sit in sitio_id_list:
        sitio_name = next((s["name"] for s in sitio_options if s["id"] == sit), f"Sitio {sit}")
        # Build URL that removes this specific sitio
        other_sitios = [s for s in sitio_id_list if s != sit]
        sitio_chips.append({
            "label": f"Sitio {sitio_name}",
            "url": build_url(sitio_id=other_sitios, page=1) if other_sitios else build_url(sitio_id="", page=1)
        })

    clear_all_url = build_url(q=q, status_id="", sitio_id="", page=1)
    
    # Calculate total filter count
    filter_count = len(status_chips) + len(sitio_chips)

    context = {
        "residents": residents,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "page_size": page_size,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_url": prev_url,
        "next_url": next_url,
        "page_items": page_items,
        "q": q or "",
        "quarter_id": quarter_id,
        "quarters": quarters,
        "status_id": status_id,
        "sitio_id": sitio_id,
        "status_options": status_options,
        "sitio_options": sitio_options,
        "status_id_list": status_id_list,
        "sitio_id_list": sitio_id_list,
        "status_chips": status_chips,
        "sitio_chips": sitio_chips,
        "filter_count": filter_count,
        "clear_all_url": clear_all_url,
    }
    return render(request, 'secretary_module/resident_list.html', context)

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_GET
def resident_detail_json(request, resident_id: int):
    """AJAX endpoint to get specific resident details"""
    try:
        quarter_id = request.GET.get('quarter_id') or None
        if quarter_id and quarter_id.isdigit():
            quarter_id = int(quarter_id)
        else:
            quarter_id = None
        
        resident = ResidentList.sp_get_specific_resident(resident_id, quarter_id)
        
        if not resident:
            return JsonResponse({"ok": False, "message": "Resident not found"}, status=404)
        
        # Convert date to string for JSON serialization
        if resident.get('dob'):
            from datetime import date
            if isinstance(resident['dob'], date):
                resident['dob'] = resident['dob'].isoformat()
        
        # Convert businesses JSONB to list if needed
        if resident.get('businesses') and isinstance(resident['businesses'], str):
            import json
            try:
                resident['businesses'] = json.loads(resident['businesses'])
            except:
                resident['businesses'] = []
        
        return JsonResponse({"ok": True, "resident": resident})
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"[ERROR] Exception in resident_detail_json:")
        print(error_detail)
        return JsonResponse({"ok": False, "message": f"Database error: {str(e)}"}, status=500)

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def household_list(request):
    limit = None
    offset = None
    results = []
    status= ''
    
    query = (request.GET.get('query') or '').strip()
    status = (request.GET.get('status') or 'all').strip()
    raw_sitio = request.GET.get('sitio_id')
    quarter_id = request.POST.get('quarter_id') or request.GET.get('quarter_id')
    current_quarter_id = Household.sp_get_current_quarter_id()

    if quarter_id:
        quarter_id = int(quarter_id)
    elif current_quarter_id:
        quarter_id = int(current_quarter_id)
    else:
        quarter_id = None

    # ✅ Are we looking at the current quarter?
    is_current_quarter = bool(
        current_quarter_id is not None and quarter_id is not None and int(quarter_id) == int(current_quarter_id)
    )

    try:
        sitio_id = int(raw_sitio) if raw_sitio not in (None, '', '0') else None
    except ValueError:
        sitio_id = None
    
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
            quarter_id=quarter_id,
            limit=limit + 1,
            offset=offset,
        )
    except Exception as e:
        msg = _clean_db_error(e)
        set_flash(request, msg, "error")
    
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
    # ✅ keep quarter in pagination / limit links
    if quarter_id is not None:
        base_params["quarter_id"] = quarter_id

    prev_url = "?" + urlencode({**base_params, "page": page - 1}) if has_prev else ""
    next_url = "?" + urlencode({**base_params, "page": page + 1}) if has_next else ""
    limit_urls = {n: "?" + urlencode({**base_params, "limit": n, "page": 1}) for n in LIMIT_OPTIONS}

    sitio = Household.sp_get_sitio()
    quarter = Household.sp_get_quarter()
    
    # Calculate filter count and chips
    filter_count = 0
    status_chip = None
    sitio_chip = None
    
    # Count active filters (excluding query and quarter)
    if status and status != 'all':
        filter_count += 1
        # Create status chip with removal URL
        status_label = status.capitalize()
        remove_status_params = {k: v for k, v in base_params.items() if k != 'status'}
        remove_status_params['status'] = 'all'
        status_chip = {
            'label': status_label,
            'url': '?' + urlencode(remove_status_params)
        }
    
    if sitio_id is not None:
        filter_count += 1
        # Find sitio name
        sitio_name = next((s['sitio_name'] for s in sitio if s['sitio_id'] == sitio_id), f'Sitio {sitio_id}')
        # Create sitio chip with removal URL
        remove_sitio_params = {k: v for k, v in base_params.items() if k != 'sitio_id'}
        sitio_chip = {
            'label': f'Sitio {sitio_name}',
            'url': '?' + urlencode(remove_sitio_params)
        }
    
    # Clear all URL
    clear_all_params = {'query': query}
    if quarter_id is not None:
        clear_all_params['quarter_id'] = quarter_id
    clear_all_url = '?' + urlencode(clear_all_params)
    
    flash = get_flash(request)
    return render(request, 'secretary_module/household_list.html',{
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
        'quarter': quarter,
        'quarter_id': quarter_id,
        # ✅ expose these to the template
        'current_quarter_id': int(current_quarter_id) if current_quarter_id else None,
        'is_current_quarter': is_current_quarter,
        # Filter badges and chips
        'filter_count': filter_count,
        'status_chip': status_chip,
        'sitio_chip': sitio_chip,
        'clear_all_url': clear_all_url,
        'message': flash['message'],
        'message_level': flash['message_level'],
    })
    
def _ok(payload=None):  return JsonResponse({"ok": True, **(payload or {})})
def _err(msg, code=400): return JsonResponse({"ok": False, "error": str(msg)}, status=code)

def _coerce_jsonb(v):
    # get_resident_links returns JSONB arrays for guardians/children
    if v is None: return []
    if isinstance(v, (list, tuple, dict)): return v
    if isinstance(v, (bytes, bytearray, memoryview)): v = bytes(v).decode('utf-8')
    if isinstance(v, str) and v: return json.loads(v)
    return []
    
@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_GET
def resident_links_list_api(request):
    try:
        rid = int(request.GET.get('resident_id') or 0)
        if not rid: return _err("resident_id is required.")
        # row with {mother_id, mother_name, mother_relationship_id, father_..., guardians, children}
        rows = Family.sp_get_resident_links(rid)
        row = rows[0] if rows else {}

        # relationship id -> name map for labels
        rel_rows = Family.sp_get_link_relationship()
        rel_map = {r["relationship_id"]: r["relationship_name"] for r in rel_rows}

        relations = []

        if row.get("mother_id"):
            relations.append({
                "related_resident_id": row["mother_id"],
                "full_name": row.get("mother_name"),
                "relationship_id": row.get("mother_relationship_id"),
                "relationship_label": rel_map.get(row.get("mother_relationship_id"), "Mother"),
            })
        if row.get("father_id"):
            relations.append({
                "related_resident_id": row["father_id"],
                "full_name": row.get("father_name"),
                "relationship_id": row.get("father_relationship_id"),
                "relationship_label": rel_map.get(row.get("father_relationship_id"), "Father"),
            })

        for key, fallback in (("guardians", "Guardian"), ("children", "Child")):
            for it in _coerce_jsonb(row.get(key)):
                rel_id = it.get("relationship_id")
                relations.append({
                    "related_resident_id": it.get("resident_id"),
                    "full_name": it.get("full_name"),
                    "relationship_id": rel_id,
                    "relationship_label": rel_map.get(rel_id, fallback),
                })

        return _ok({"relations": relations})
    except Exception as e:
        return _err(e)
    
@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_GET
def general_health_get_api(request):
    fm_id = request.GET.get("member_id") or request.GET.get("family_member_id")
    if not fm_id:
        return JsonResponse({"error": "member_id is required"}, status=400)
    try:
        fm_id = int(fm_id)
    except ValueError:
        return JsonResponse({"error": "member_id must be an integer"}, status=400)

    try:
        row = Family.sp_get_specific_family_member_genhealth(fm_id)
    except Exception as e:
        # Log if you have logging; return a safe message to client
        return JsonResponse({"error": "database_error", "detail": str(e)}, status=500)

    if not row:
        return JsonResponse({"record": None, "exists": False}, status=200)

    # ----- Optional normalization (keeps raw keys intact) -----
    # Map to the keys your JS expects; fall back to whatever the SP returns.
    record = dict(row)  # start with raw db keys

    # Friendly, consistent keys your modal code handles:
    record.setdefault("gh_id",                 row.get("record_id") or row.get("id") or row.get("general_health_id"))
    record.setdefault("smoker",                row.get("smoker"))
    record.setdefault("alcohol_drinker",       row.get("alcohol_drinker"))
    record.setdefault("sexually_active",       row.get("sexually_active"))
    record.setdefault("last_menstrual_period", row.get("last_menstrual_period"))
    record.setdefault("age_menarche",          row.get("age_of_menarche"))
    record.setdefault("fp_use",                row.get("fp_method_yn"))
    record.setdefault("fp_method_id",          row.get("fp_method_id"))
    record.setdefault("fp_status_id",          row.get("fp_status_id"))
    record.setdefault("class_id",              row.get("class_id"))
    # Normalize medical_history to list
    mh = row.get("medical_history") or row.get("medical_history_ids") or row.get("mh")
    record["medical_history"] = _to_list(mh)

    return JsonResponse({"record": record, "exists": True}, status=200)
    
@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def sec_householdView(request):
    
    def _to_bool(v):
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return v != 0
        if isinstance(v, str):
            return v.strip().lower() in {"true", "t", "1", "yes", "y"}
        return False

    raw_hid = (
        request.GET.get('household_id')
        or request.POST.get('household_id')
        or request.GET.get('hid') 
    )
    qid_raw = request.GET.get('quarter_id') or request.POST.get('quarter_id')
    household_number = (
        request.GET.get('household_number')
        or request.session.get('household_number')
        or request.POST.get('household_number')
    )

    if not raw_hid:
        set_flash(request, "No household selected.", "error")
        return redirect('bhw_module:householdList')

    try:
        hid = int(raw_hid)
    except (TypeError, ValueError):
        set_flash(request, "Invalid household id.", "error")
        return redirect('bhw_module:householdList')

    # Parse quarter id if present
    qid = None
    try:
        if qid_raw not in (None, ""):
            qid = int(qid_raw)
    except (TypeError, ValueError):
        qid = None

    try:
        result   = Household.sp_get_specific_household(hid, qid)
        rows_raw = Family.sp_get_family_summaries_per_household(hid, qid)
        
        if not result:
            set_flash(request, "Household not found.", "error")
            return redirect('bhw_module:householdList')
    except Exception as e:
        set_flash(request, _clean_db_error(e), "error")
        return redirect('bhw_module:householdList')

    # Build families list and decode JSONB members
    families = []
    for r in rows_raw or []:
        # Skip sentinel row from your SQL (family_id = 0)
        if not r.get('family_id'):
            continue

        members = r.get('family_members') or []
        if isinstance(members, str):
            try:
                members = json.loads(members)
            except Exception:
                members = []

        
        for m in members:
            name = (m.get('full_name') or '').strip()
            parts = [p for p in name.split() if p]
            m['initials'] = (''.join(p[0] for p in parts[:2]) or 'NA').upper()

        families.append({
            'family_id':               r.get('family_id'),
            'family_code':             r.get('family_code') or '',
            'family_head':             r.get('family_head') or '',
            'respondent':              r.get('respondent_name') or '',
            'rtf':                     r.get('respondent_relationship') or '',
            'nhts_status':             _to_bool(r.get('nhts_status')),
            'indigent':                _to_bool(r.get('indigent')),
            'household_type':          r.get('household_type') or '',
            'water_source':            r.get('water_source') or '',
            'waste_management':        r.get('waste_management') or '',
            'is_visited':               _to_bool(r.get('is_visited')),
            'date_visited':             r.get('date_visited'),
            'toilet_type':             r.get('toilet_type') or '',
            'family_head_id':          r.get('family_head_id'),
            'respondent_id':           r.get('respondent_id'),
            'rth':                     r.get('relationship_of_family_head_to_hh ') or '',
            'rth_id':                  r.get('relationship_of_family_head_to_hh_id'),
            'rtf_id':                  r.get('relationship_of_respondent_to_family_head_id'),
            'household_type_id':       r.get('household__type_id'),
            'waste_management_id':     r.get('waste_management_id'),
            'water_source_id':         r.get('water_source_id'),
            'toilet_type_id':          r.get('toilet_type_id'),
            'ip_tribe':                r.get('ip_tribe') or '',
            'quarter_id':              r.get('quarter_id'),
            'members':                 members,
        })

    # reflect chosen quarter in result (your existing bit) …
    if qid is not None:
        try:
            setattr(result, 'quarter_id', qid)
        except Exception:
            if isinstance(result, dict):
                result['quarter_id'] = qid     

    relationship     = Household.sp_get_relationship_to_household_head()
    house_ownership  = Household.sp_get_house_ownership()
    house_type       = Household.sp_get_house_type()
    sitio            = Household.sp_get_sitio()
    household_type   = Household.sp_get_household_type()
    water_source     = Family.sp_get_water_source_type()
    quarter          = Household.sp_get_quarter()
    waste_management = Family.sp_get_waste_management_type()
    toilet_facility  = Family.sp_get_toilet_facility_type()
    family_relationship = Family.sp_get_relationship_to_family_head()
    philhealth_category = Family.sp_get_philhealth_category()
    nutrition_status = Family.sp_get_nutrition_status()
    current_quarter = Household.sp_get_current_quarter_id()
    link_relationship = Family.sp_get_link_relationship()
    fp_method = Family.sp_get_fp_method()
    fp_status = Family.sp_get_fp_status()
    classification = Family.sp_get_classifications()

    flash = get_flash(request)
    return render(request, 'secretary_module/moreHousehold.html', {
        'relationship': relationship,
        'house_ownership': house_ownership,
        'house_type': house_type,
        'sitio': sitio,
        'household_type': household_type,
        'water_source': water_source,
        'quarter': quarter,
        'household_number': household_number,
        'waste_management': waste_management,
        'toilet_facility': toilet_facility,
        'hid': hid,
        'family_relationship': family_relationship,
        'philhealth_category': philhealth_category,
        'nutrition_status': nutrition_status,
        'fp_method': fp_method,
        'fp_status': fp_status,
        'class': classification,
        'results': result,
        'link_relationship': link_relationship,
        'current_quarter': current_quarter,
        'families': families,
        'message': flash['message'],
        'message_level': flash['message_level'],
    })

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
@require_GET
def search_residents_api(request):
    """API endpoint for resident autocomplete search"""
    query = request.GET.get('q', '').strip()
    limit = min(int(request.GET.get('limit', 10)), 50)
    
    if not query or len(query) < 2:
        return JsonResponse({'results': []})
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM search_business_owner(%s, %s, %s)", [query, limit, 0])
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                resident = dict(zip(columns, row))
                results.append({
                    'resident_id': resident.get('resident_id'),
                    'full_name': resident.get('full_name'),
                    'email': resident.get('email'),
                    'phone': resident.get('phone_number') or resident.get('phone'),
                })
            
            return JsonResponse({'results': results})
    except Exception as e:
        logger.error(f"Error searching residents: {e}")
        return JsonResponse({'results': [], 'error': str(e)}, status=500)

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
            # Check if resident was selected from autocomplete
            selected_resident_id = request.POST.get("selected_resident_id")
            if selected_resident_id:
                resident_id = int(selected_resident_id)
            else:
                resident_id = _find_resident_id_by_name(resident_name)

            business_name         = request.POST.get("business_name")
            business_type_id      = int(request.POST.get("business_type_id"))
            nature_of_business    = request.POST.get("nature_of_business")
            ownership_id          = int(request.POST.get("ownership_id"))
            house_number          = request.POST.get("house_number")
            street                = request.POST.get("street")
            barangay              = request.POST.get("barangay") or "Cansaga"
            sitio_id              = int(request.POST.get("sitio_id"))
            city_municipality     = request.POST.get("city_municipality") or "Consolacion"
            country               = request.POST.get("country") or "Philippines"
            total_gross_income    = request.POST.get("total_gross_income")
            dti_sec_cda_reg_num   = request.POST.get("dti_sec_cda_reg_number") or None
            clearance_category_id = int(request.POST.get("clearance_category_id"))
            clearance_date_issued = request.POST.get("clearance_date_issued") or None

            # total_units (optional overall; required by SP only if category supports it)
            total_units_raw = request.POST.get("total_units")
            total_units = int(total_units_raw) if (total_units_raw not in [None, ""]) else None

            # NEW: amusement device quantities (required by SP only if category is Amusement)
            def _i(val):
                return int(val) if (val not in [None, ""]) else None

            videoke_count       = _i(request.POST.get("videoke_count"))
            billiard_count      = _i(request.POST.get("billiard_count"))
            other_device_count  = _i(request.POST.get("other_device_count"))

            personnel_id = int(request.session.get("personnel_id"))

            Secretary.sp_register_business(
                resident_id, business_name, business_type_id, nature_of_business, ownership_id,
                house_number, street, barangay, sitio_id, city_municipality, country,
                total_gross_income, dti_sec_cda_reg_num, clearance_category_id,
                total_units,
                videoke_count, billiard_count, other_device_count,  # <-- NEW
                clearance_date_issued, personnel_id
            )
            
            # Determine business status based on clearance_date_issued
            business_status = "Active" if clearance_date_issued else "Pending"
            
            # Send notification to business owner
            try:
                NotificationService.send_to_resident(
                    resident_id=resident_id,
                    title="Business Successfully Added",
                    body=f'Your business "{business_name}" has been successfully registered with status: {business_status}. Proceed to request a business clearance.',
                    deep_link="/(tabs)/business",
                    data={
                        'type': 'business_registered',
                        'business_name': business_name,
                        'business_status': business_status
                    }
                )
            except Exception as notif_error:
                logger.warning(f"Failed to send business registration notification: {notif_error}")
            
            set_flash(request, "Successfully Submitted", "success")
        except Exception as e:
            set_flash(request, _clean_db_error(e), "error")

    flash = get_flash(request)
    return render(request, "secretary_module/Addbusiness.html", {
        'message': flash.get('message'),
        'message_level': flash.get('message_level'),
        'clearance_categories': clearance_categories,
    })


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def business_list(request):
    q = (request.GET.get("q") or "").strip() or None
    page = max(int(request.GET.get("page", 1)), 1)
    per_page = max(min(int(request.GET.get("per_page", 10)), 100), 1)
    offset = (page - 1) * per_page

    # Parse multiple filter values
    business_type_ids = _to_list(request.GET.getlist("business_type_id"))
    clearance_category_ids = _to_list(request.GET.getlist("clearance_category_id"))
    ownership_ids = _to_list(request.GET.getlist("ownership_id"))
    business_status_ids = _to_list(request.GET.getlist("business_status_id"))

    # Fetch filter options for dropdowns
    with connection.cursor() as cur:
        cur.execute("SELECT business_type_id, type_name FROM business_type ORDER BY type_name")
        business_types = [{"id": row[0], "name": row[1]} for row in cur.fetchall()]

    with connection.cursor() as cur:
        cur.execute("SELECT ownership_id, ownership_name FROM ownership ORDER BY ownership_name")
        ownerships = [{"id": row[0], "name": row[1]} for row in cur.fetchall()]
    
    with connection.cursor() as cur:
        cur.execute("SELECT business_status_id, status_name FROM business_status ORDER BY status_name")
        business_statuses = [{"id": row[0], "name": row[1]} for row in cur.fetchall()]

    try:
        clearance_categories = Business.sp_get_business_clearance_categories_for_select()
    except Exception:
        clearance_categories = []

    # Create lookup maps for filtering (ID -> Name)
    business_type_map = {str(t['id']): t['name'] for t in business_types}
    ownership_map = {str(o['id']): o['name'] for o in ownerships}
    business_status_map = {str(s['id']): s['name'] for s in business_statuses}
    clearance_category_map = {str(c.get('clearance_category_id')): c.get('category_name') for c in clearance_categories if c.get('clearance_category_id')}

    # Get all businesses matching search query
    # Since SQL function takes single filter values, we'll fetch all and filter in Python for multi-select
    try:
        rows = Business.sp_get_all_businesses(
            query=q,
            business_type_id=None,
            business_clearance_cat_id=None,
            ownership_id=None,
            business_status_id=None,
            limit=1000,  # Get all for filtering
            offset=0
        )
    except Exception as e:
        print(f"ERROR calling sp_get_all_businesses: {e}")
        import traceback
        traceback.print_exc()
        rows = []
    
    # Apply filters in Python - match by name since the DB returns text fields
    if business_type_ids:
        selected_names = [business_type_map.get(id) for id in business_type_ids if id in business_type_map]
        rows = [r for r in rows if r.get('business_type_name') in selected_names]
    if clearance_category_ids:
        selected_names = [clearance_category_map.get(id) for id in clearance_category_ids if id in clearance_category_map]
        rows = [r for r in rows if r.get('clearance_category_name') in selected_names]
    if ownership_ids:
        selected_names = [ownership_map.get(id) for id in ownership_ids if id in ownership_map]
        rows = [r for r in rows if r.get('ownership_name') in selected_names]
    if business_status_ids:
        selected_names = [business_status_map.get(id) for id in business_status_ids if id in business_status_map]
        rows = [r for r in rows if r.get('business_status_name') in selected_names]
    
    total = len(rows)
    
    # Paginate
    rows = rows[offset:offset + per_page]
    
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

    # Build filter chips (like resident list)
    def build_remove_url(param_name, value_to_remove):
        params = request.GET.copy()
        vals = params.getlist(param_name)
        vals = [v for v in vals if str(v) != str(value_to_remove)]
        if vals:
            params.setlist(param_name, vals)
        else:
            params.pop(param_name, None)
        params['page'] = '1'
        return f"?{params.urlencode()}"

    business_type_chips = []
    clearance_category_chips = []
    ownership_chips = []
    business_status_chips = []
    
    for type_id in business_type_ids:
        type_name = next((t['name'] for t in business_types if str(t['id']) == str(type_id)), f"Type {type_id}")
        business_type_chips.append({
            'label': type_name,
            'url': build_remove_url('business_type_id', type_id)
        })
    
    for cat_id in clearance_category_ids:
        cat_name = next((c.get('category_name', f"Category {cat_id}") for c in clearance_categories 
                        if str(c.get('clearance_category_id')) == str(cat_id)), f"Category {cat_id}")
        clearance_category_chips.append({
            'label': cat_name,
            'url': build_remove_url('clearance_category_id', cat_id)
        })
    
    for own_id in ownership_ids:
        own_name = next((o['name'] for o in ownerships if str(o['id']) == str(own_id)), f"Ownership {own_id}")
        ownership_chips.append({
            'label': own_name,
            'url': build_remove_url('ownership_id', own_id)
        })
    
    for status_id in business_status_ids:
        status_name = next((s['name'] for s in business_statuses if str(s['id']) == str(status_id)), f"Status {status_id}")
        business_status_chips.append({
            'label': status_name,
            'url': build_remove_url('business_status_id', status_id)
        })

    # Clear all filters URL
    clear_all_params = {'q': q} if q else {}
    clear_all_url = f"?{urlencode(clear_all_params)}" if clear_all_params else "?"

    # Count active filters
    filter_count = (len(business_type_ids) + len(clearance_category_ids) + 
                   len(ownership_ids) + len(business_status_ids))

    # Build prev/next URLs preserving filters
    def build_page_url(p):
        params = request.GET.copy()
        params['page'] = str(p)
        return f"?{params.urlencode()}"

    prev_url = build_page_url(page - 1) if page > 1 else None
    next_url = build_page_url(page + 1) if page < total_pages else None

    # Build page items for pagination
    page_items = []
    for p in page_numbers:
        page_items.append({
            'page': p,
            'url': build_page_url(p),
            'is_current': p == page
        })

    ctx = {
        "rows": rows,
        "q": q or "",
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "page_numbers": page_numbers,
        "page_items": page_items,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_url": prev_url,
        "next_url": next_url,
        "business_types": business_types,
        "ownerships": ownerships,
        "business_statuses": business_statuses,
        "clearance_categories": clearance_categories,
        "business_type_id_list": business_type_ids,
        "clearance_category_id_list": clearance_category_ids,
        "ownership_id_list": ownership_ids,
        "business_status_id_list": business_status_ids,
        "business_type_chips": business_type_chips,
        "clearance_category_chips": clearance_category_chips,
        "ownership_chips": ownership_chips,
        "business_status_chips": business_status_chips,
        "clear_all_url": clear_all_url,
        "filter_count": filter_count,
    }
    return render(request, "secretary_module/manageBusiness.html", ctx)

def business_detail_json(request, business_id: int):
    """Returns JSON data for one business (for the View modal)."""
    data = Business.sp_get_business_detail(business_id)
    if not data:
        raise Http404("Business not found")
    return JsonResponse(data, safe=False)

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def business_detail_page(request, business_id: int):
    """Server-rendered full page for a specific business.

    Provides the business row plus a lightweight renewal summary so the
    template can render details and client JS can handle previews.
    """
    data = Business.sp_get_business_detail(business_id)
    if not data:
        raise Http404("Business not found")
    # Optional renewal summary
    renewal = {}
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM get_business_renewal_summary(%s)", [business_id])
            row = cur.fetchone()
            if row:
                cols = [c[0] for c in cur.description]
                renewal = dict(zip(cols, row))
    except Exception:
        renewal = {}
    return render(request, 'secretary_module/business_detail.html', {
        'business': data,
        'renewal': renewal,
    })

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_GET
def business_payment_history_json(request, business_id: int):
    """Return paginated payment history for a specific business.

    Query params:
      q (search text)
      status (payment_status filter)
      date_from (YYYY-MM-DD)
      date_to (YYYY-MM-DD)
      page (1-based)
      per_page (default 25)

    Response JSON:
      {
        ok: true,
        rows: [ { date_paid, amount, amount_display?, payment_status, request_label, application_id, or_number, fee_type_name } ],
        total, page, pages, per_page
      }
    """
    # Validate business existence quickly (optional; fail fast)
    try:
        b = Business.sp_get_business_detail(business_id)
        if not b:
            return JsonResponse({'ok': False, 'message': 'Business not found.'}, status=404)
    except Exception:
        return JsonResponse({'ok': False, 'message': 'Business lookup failed.'}, status=400)

    q = (request.GET.get('q') or '').strip() or None
    status = (request.GET.get('status') or '').strip() or None
    date_from = (request.GET.get('date_from') or '').strip() or None
    date_to = (request.GET.get('date_to') or '').strip() or None
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
        result = SecretaryHelpers.get_business_payment_history(
            business_id=business_id,
            query=q,
            payment_status=status,
            date_from=date_from or None,
            date_to=date_to or None,
            limit=per_page,
            offset=offset
        )
    except Exception as e:
        return JsonResponse({'ok': False, 'message': _clean_db_error(e)}, status=400)

    total = result['total']
    pages = max(ceil(total / per_page), 1)

    # Normalize rows (Decimal/Date serialization)
    from datetime import date, datetime
    from decimal import Decimal as D
    def ser(v):
        if isinstance(v, D):
            try:
                return float(v)
            except Exception:
                return str(v)
        if isinstance(v, (date, datetime)):
            return v.isoformat()
        return v
    rows = []
    for r in result['rows']:
        sr = {k: ser(v) for k, v in r.items()}
        # Canonicalize common fields to stabilize frontend rendering
        def pick(obj, keys):
            for k in keys:
                v = obj.get(k)
                if v is not None and v != '':
                    return v
            return None
        # Request label variations
        sr.setdefault('request_label', pick(sr, [
            'request_label', 'request', 'request_name', 'fee_type_name', 'purpose', 'label', 'description'
        ]))
        # Payment status variations
        sr.setdefault('payment_status', pick(sr, ['payment_status', 'status', 'paymentstate']))
        # Date paid variations
        sr.setdefault('date_paid', pick(sr, ['date_paid', 'paid_at', 'payment_date', 'date', 'created_at']))
        # OR number variations
        sr.setdefault('or_number', pick(sr, ['or_number', 'or_no', 'official_receipt_number']))
        # Application id variations
        sr.setdefault('application_id', pick(sr, ['application_id', 'app_id', 'id']))
        # Amount numeric
        amt = pick(sr, ['amount', 'paid', 'paid_amount', 'amount_paid', 'total', 'total_amount', 'payment_amount', 'net_amount'])
        try:
            sr['amount'] = float(amt) if amt is not None else None
        except Exception:
            # keep original if cannot coerce
            sr['amount'] = amt
        # Optional display text
        sr.setdefault('amount_display', pick(sr, ['amount_display', 'display']))
        rows.append(sr)

    return JsonResponse({
        'ok': True,
        'rows': rows,
        'total': total,
        'page': page,
        'pages': pages,
        'per_page': per_page,
    })


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def business_renewal_summary_json(request, business_id: int):
    """Return renewal summary using get_business_renewal_summary(business_id).

    Response shape:
      { ok, business_id, business_status, needs_renewal, renewal_total, renewal_total_details }
    """
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM get_business_renewal_summary(%s)", [business_id])
            row = cur.fetchone()
            if not row:
                return JsonResponse({
                    'ok': False,
                    'message': 'No data returned for business.'
                }, status=404)

            cols = [c[0] for c in cur.description]
            payload = dict(zip(cols, row))

        # Normalize numeric for JSON
        total = payload.get('renewal_total')
        try:
            payload['renewal_total'] = float(total) if total is not None else None
        except Exception:
            pass

        payload['ok'] = True
        return JsonResponse(payload)
    except Exception as e:
        return JsonResponse({'ok': False, 'message': _clean_db_error(e)}, status=400)

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

        # -----------------------------
        # Current state (for rule checks)
        # -----------------------------
        current = Business.sp_get_business_detail(business_id) or {}

        # Ownership
        curr_own = _to_int_or_none(current.get('ownership_id')) or 0

        # Try to read old clearance category:
        # 1) (optional) from POST hidden field, if you later add it
        curr_cat = _to_int_or_none(request.POST.get("old_clearance_category_id"))
        # 2) from the DB result if POST didn’t provide it
        if not curr_cat:
            curr_cat = _extract_clearance_cat(current)

        # -----------------------------
        # Optional owner transfer via name
        # -----------------------------
        resident_name = (request.POST.get("resident_name") or "").strip()
        resident_id = None
        if resident_name:
            # Owner change only if NOT sole proprietorship (id=1)
            if curr_own == 1:
                return JsonResponse(
                    {"ok": False, "message": "Owner cannot be changed for Sole Proprietorship."},
                    status=400
                )
            resident_id = _find_resident_id_by_name(resident_name)

        # -----------------------------
        # Clearance Category rules
        # -----------------------------
        raw_new_cat = request.POST.get("clearance_category_id")
        new_cat = _to_int_or_none(raw_new_cat)

        # Only run rules if there is a requested change
        if new_cat is not None and new_cat != curr_cat:

            # 1) Validate that the new category exists
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM business_clearance_category "
                    "WHERE clearance_category_id = %s",
                    [new_cat],
                )
                if cur.fetchone() is None:
                    return JsonResponse(
                        {
                            "ok": False,
                            "message": f"Unknown clearance_category_id {new_cat}."
                        },
                        status=400,
                    )

            # 2) Transition rules
            if curr_cat in (3, 4):
                # Sole Proprietorship: can switch only between 3 and 4
                if new_cat not in (3, 4):
                    return JsonResponse(
                        {
                            "ok": False,
                            "message": "Sole Proprietorship category can switch only between 3 and 4."
                        },
                        status=400,
                    )

            elif 6 <= curr_cat <= 10:
                # Lessor: can switch only within 6–10
                if not (6 <= new_cat <= 10):
                    return JsonResponse(
                        {
                            "ok": False,
                            "message": "Lessor category can switch only within 6–10."
                        },
                        status=400,
                    )

            else:
                # All other categories cannot change
                return JsonResponse(
                    {
                        "ok": False,
                        "message": f"This clearance category cannot be updated "
                                   f"(old={curr_cat}, new={new_cat})."
                    },
                    status=400,
                )

        # -----------------------------
        #  Rest of update logic
        # -----------------------------
        total_units        = _to_int_or_none(request.POST.get("total_units"))
        videoke_count      = _to_int_or_none(request.POST.get("videoke_count"))
        billiard_count     = _to_int_or_none(request.POST.get("billiard_count"))
        other_device_count = _to_int_or_none(request.POST.get("other_device_count"))

        payload = {
            "business_name":          _none_if_blank(request.POST.get("business_name")),
            "business_type_id":       None,  # not editable
            "nature_of_business":     _none_if_blank(request.POST.get("nature_of_business")),
            "ownership_id":           None,  # not editable
            "resident_id":            resident_id,
            "house_number":           _none_if_blank(request.POST.get("house_number")),
            "street":                 _none_if_blank(request.POST.get("street")),
            "barangay":               _none_if_blank(request.POST.get("barangay")),
            "sitio_id":               _to_int_or_none(request.POST.get("sitio_id")),
            "city_municipality":      _none_if_blank(request.POST.get("city_municipality")),
            "country":                _none_if_blank(request.POST.get("country")),
            "total_gross_income":     _to_decimal_or_none(request.POST.get("total_gross_income")),
            "clearance_category_id":  new_cat,   # may be None or same as old
            "dti_sec_cda_reg_number": None,      # not editable
            "total_units":            total_units,
            "videoke_count":          videoke_count,
            "billiard_count":         billiard_count,
            "other_device_count":     other_device_count,
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


def _extract_clearance_cat(current: dict) -> int:
    """
    Try to find the current clearance category ID from the dict returned
    by sp_get_business_detail, regardless of the exact column name.
    """
    if not current:
        return 0

    # 1) Look for any key that clearly looks like a clearance category id
    for key, val in current.items():
        if not key:
            continue
        lk = str(key).lower()
        # match things like 'clearance_category_id', 'business_clearance_category_id', etc.
        if 'clearance' in lk and 'category' in lk and 'id' in lk:
            v = _to_int_or_none(val)
            if v is not None:
                return v

    # 2) Fallback to some common explicit names
    for k in [
        'clearance_category_id',
        'business_clearance_category_id',
        'clearance_categoryid',
        'clearance_cat_id',
    ]:
        v = _to_int_or_none(current.get(k))
        if v is not None:
            return v

    # 3) Give up
    return 0

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
    # Provide fee types and other clearance purposes for the Create UI
    try:
        fee_types = SecretaryHelpers.get_fee_types_dropdown()
    except Exception:
        fee_types = []
    try:
        other_clearances = SecretaryHelpers.get_other_clearance_purposes_dropdown()
    except Exception:
        other_clearances = []
    return render(request, 'secretary_module/addCertificate.html', {
        'fee_types': fee_types,
        'other_clearances': other_clearances,
    })

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
    # Support multi-select via repeated params ?application_status=Pending&application_status=For+Payment
    app_status_list = [s.strip() for s in request.GET.getlist('application_status') if s and s.strip()]
    req_label_list = [r.strip() for r in request.GET.getlist('request_label') if r and r.strip()]
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
        # If single selections (or none), use direct DB filtering for efficiency
        if len(app_status_list) <= 1 and len(req_label_list) <= 1:
            single_status = app_status_list[0] if app_status_list else None
            single_req    = req_label_list[0] if req_label_list else None
            rows = SecretaryHelpers.list_all_applications(q, single_status, single_req, per_page, offset)
            total = SecretaryHelpers.count_all_applications(q, single_status, single_req)
        else:
            # Multi-select: build cross-product of filters and merge results ordered by date_submitted desc
            # 1) Build combinations
            statuses = app_status_list or [None]
            requests = req_label_list or [None]
            combos = [(s, r) for s in statuses for r in requests]

            # 2) Count total exactly (sum; disjoint across status/request categories)
            total = 0
            per_combo_counts = {}
            for s, r in combos:
                c = SecretaryHelpers.count_all_applications(q, s, r)
                per_combo_counts[(s, r)] = c
                total += c

            # 3) Fetch top-K from each combo where K = min(count, page*per_page), then merge and slice
            end_idx = page * per_page
            merged = {}
            for s, r in combos:
                take = min(per_combo_counts[(s, r)], end_idx)
                if take <= 0:
                    continue
                subset = SecretaryHelpers.list_all_applications(q, s, r, take, 0)
                for row in subset:
                    merged[row['application_id']] = row

            # 4) Global sort by (date_submitted desc, application_id desc)
            merged_rows = list(merged.values())
            try:
                merged_rows.sort(key=lambda x: (x.get('date_submitted'), x.get('application_id')), reverse=True)
            except Exception:
                # Fallback if date types vary
                merged_rows.sort(key=lambda x: str(x.get('date_submitted')) + '-' + str(x.get('application_id')), reverse=True)

            start_idx = (page - 1) * per_page
            rows = merged_rows[start_idx:end_idx]
    except Exception as e:
        messages.error(request, f"Failed to load applications: {_clean_db_error(e)}")
        rows, total = [], 0

    total_pages = max(ceil((total or 0) / per_page), 1)
    # Build pagination URLs that preserve filters (doseq=True)
    def _qs(base_dict: dict, statuses: list[str], reqs: list[str]) -> str:
        params = []
        for k, v in base_dict.items():
            if v is not None and v != "":
                params.append((k, v))
        for s in statuses:
            params.append(('application_status', s))
        for r in reqs:
            params.append(('request_label', r))
        return urlencode(params, doseq=True)

    prev_url = next_url = ''
    if page > 1:
        prev_url = '?' + _qs({'q': q or '', 'page': page - 1, 'per_page': per_page}, app_status_list, req_label_list)
    if page < total_pages:
        next_url = '?' + _qs({'q': q or '', 'page': page + 1, 'per_page': per_page}, app_status_list, req_label_list)

    # Use Django's Paginator solely to get elided page range; rows are already sliced
    paginator = Paginator(range(total), per_page)  # dummy sequence just for pagination metadata
    # Clamp page within bounds (Paginator.get_page handles invalid values)
    page_obj = paginator.get_page(page)
    # Replace page with possibly adjusted number (e.g., too high -> last page)
    page = page_obj.number
    total_pages = paginator.num_pages
    # Elided page range (provides automatic ellipses)
    page_numbers = list(paginator.get_elided_page_range(number=page, on_each_side=1, on_ends=1))
    page_urls = {}
    for pn in page_numbers:
        if isinstance(pn, int):
            page_urls[pn] = '?' + _qs({'q': q or '', 'page': pn, 'per_page': per_page}, app_status_list, req_label_list)
    # Build template-friendly items to avoid dict indexing in templates
    page_items = []
    for item in page_numbers:
        if isinstance(item, int):
            page_items.append({'num': item, 'url': page_urls.get(item, ''), 'current': (item == page)})
        else:
            page_items.append({'ellipsis': True})
    # Update prev/next flags after clamping
    has_prev = page_obj.has_previous()
    has_next = page_obj.has_next()
    prev_url = '?' + _qs({'q': q or '', 'page': page - 1, 'per_page': per_page}, app_status_list, req_label_list) if has_prev else ''
    next_url = '?' + _qs({'q': q or '', 'page': page + 1, 'per_page': per_page}, app_status_list, req_label_list) if has_next else ''

    # Build chip removal links
    def _remove_one(kind: str, val: str) -> str:
        s_list = list(app_status_list)
        r_list = list(req_label_list)
        if kind == 'status' and val in s_list:
            s_list.remove(val)
        if kind == 'request' and val in r_list:
            r_list.remove(val)
        return '?' + _qs({'q': q or '', 'page': 1, 'per_page': per_page}, s_list, r_list)

    status_chips = [{'label': s, 'url': _remove_one('status', s)} for s in app_status_list]
    request_chips = [{'label': r, 'url': _remove_one('request', r)} for r in req_label_list]

    ctx = {
        'rows': rows,
        'q': q or '',
        'application_status': app_status_list[0] if len(app_status_list) == 1 else '',
        'request_label': req_label_list[0] if len(req_label_list) == 1 else '',
        'application_status_list': app_status_list,
        'request_label_list': req_label_list,
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages,
        'has_prev': has_prev,
        'has_next': has_next,
        'prev_page': page - 1,
        'next_page': page + 1,
        'prev_url': prev_url,
        'next_url': next_url,
        'page_numbers': page_numbers,
    'page_urls': page_urls,
    'page_items': page_items,
        # provide option lists for filter UI
        'application_status_options': ['Pending','For Payment','Approved','Completed','Rejected','Cancelled'],
        'request_label_options': ['Business Clearance','Business Closure','Business Clearance (Reprint)','Barangay Clearance'],
        'status_chips': status_chips,
        'request_chips': request_chips,
        'clear_all_url': '?' + _qs({'q': q or '', 'page': 1, 'per_page': per_page}, [], []),
    }
    return render(request, 'secretary_module/applications.html', ctx)

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def application_detail(request, application_id: int):
    """Server-rendered detail page for a specific application."""
    try:
        row = SecretaryHelpers.get_specific_application(application_id)
        if not row:
            raise Http404('Application not found')
    except Http404:
        raise
    except Exception as e:
        messages.error(request, _clean_db_error(e))
        return redirect('secretary_module:applications')

    # Normalize breakdown and numeric formatting
    import json
    details_json = row.get('total_amount_details')
    if isinstance(details_json, str):
        try:
            details_json = json.loads(details_json)
        except Exception:
            details_json = None

    # normalize to a list of structured items and a total
    breakdown_items = []
    breakdown_total = None
    purpose_value = None

    def to_float(x):
        try:
            from decimal import Decimal as D
            return float(x) if isinstance(x, (int, float, D)) else x
        except Exception:
            return x

    if isinstance(details_json, dict):
        items = details_json.get('items')
        breakdown_total = to_float(details_json.get('total'))
        # Extract purpose if provided in details JSON (e.g., { items:[], total:..., purpose:"..." })
        try:
            purpose_value = details_json.get('purpose') or purpose_value
        except Exception:
            purpose_value = purpose_value
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict):
                    breakdown_items.append({
                        'label': it.get('item') or it.get('label') or it.get('name') or 'Item',
                        'amount': to_float(it.get('amount') or it.get('total') or it.get('price') or 0),
                        'qty': it.get('qty'),
                        'rate': to_float(it.get('rate')) if it.get('rate') is not None else None,
                        'rate_percent': to_float(it.get('rate_percent')) if it.get('rate_percent') is not None else None,
                        'extra_units': it.get('extra_units'),
                        'total_units': it.get('total_units'),
                        'minimum_units': it.get('minimum_units'),
                    })
        else:
            # dict but no 'items' array; try to flatten key-values
            for k, v in details_json.items():
                if k == 'total':
                    continue
                if isinstance(v, (int, float)):
                    breakdown_items.append({'label': k, 'amount': to_float(v)})
                elif isinstance(v, dict) and 'amount' in v:
                    breakdown_items.append({'label': k, 'amount': to_float(v.get('amount'))})
    elif isinstance(details_json, list):
        for it in details_json:
            if isinstance(it, dict):
                breakdown_items.append({
                    'label': it.get('item') or it.get('label') or it.get('name') or 'Item',
                    'amount': to_float(it.get('amount') or it.get('total') or it.get('price') or 0),
                    'qty': it.get('qty'),
                    'rate': to_float(it.get('rate')) if it.get('rate') is not None else None,
                    'rate_percent': to_float(it.get('rate_percent')) if it.get('rate_percent') is not None else None,
                    'extra_units': it.get('extra_units'),
                    'total_units': it.get('total_units'),
                    'minimum_units': it.get('minimum_units'),
                })

    # If purpose was embedded in the JSON and row has no explicit purpose, surface it
    try:
        if purpose_value and not row.get('purpose'):
            row['purpose'] = purpose_value
    except Exception:
        pass

    ctx = {
        'row': row,
        'application_id': application_id,
        'breakdown': breakdown_items,
        'breakdown_total': breakdown_total,
    }
    # Provide personnel_id for forms that may need to submit it (e.g., cancellation)
    try:
        ctx['personnel_id'] = int(request.session.get('personnel_id') or 0) or _acting_personnel_id(request)
    except Exception:
        ctx['personnel_id'] = _acting_personnel_id(request)
    return render(request, 'secretary_module/application_detail.html', ctx)

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_POST
def set_application_to_completed(request, application_id: int):
    """Mark an Approved application as Completed (finalized/printed)."""
    try:
        # Prefer posted personnel_id (if supplied by form), otherwise derive from session/user
        posted_pid = request.POST.get('personnel_id')
        try:
            personnel_id = int(posted_pid) if posted_pid is not None else None
        except (TypeError, ValueError):
            personnel_id = None
        if not personnel_id:
            personnel_id = _acting_personnel_id(request)
        if not personnel_id:
            raise ValueError('Missing personnel_id for completion.')

        # Get application details before updating status
        app_data = SecretaryHelpers.get_specific_application(application_id)
        
        SecretaryHelpers.set_application_to_completed(application_id, personnel_id)
        
        # Send notification to resident
        resident_id = None
        if app_data:
            # Priority 1: Extract applicant_id from total_amount_details JSON
            details_json = app_data.get('total_amount_details')
            if details_json:
                try:
                    if isinstance(details_json, str):
                        details_json = json.loads(details_json)
                    if isinstance(details_json, dict) and details_json.get('applicant_id'):
                        resident_id = details_json['applicant_id']
                        logger.info(f"Completion - Application {application_id}: Found applicant_id={resident_id} in total_amount_details")
                except Exception as e:
                    logger.error(f"Completion - Application {application_id}: Error parsing total_amount_details: {e}")
            
            # Priority 2: For business applications, get the business owner
            if not resident_id and app_data.get('business_id'):
                try:
                    business_data = Business.sp_get_business_detail(app_data['business_id'])
                    if business_data and business_data.get('owner_id'):
                        resident_id = business_data['owner_id']
                        logger.info(f"Completion - Application {application_id}: Found owner_id={resident_id} from business")
                except Exception as e:
                    logger.error(f"Failed to get business owner for business_id {app_data['business_id']}: {e}")
            
            # Priority 3: Fall back to requested_by_id (for resident-initiated applications)
            if not resident_id and app_data.get('requested_by') == 'resident' and app_data.get('requested_by_id'):
                resident_id = app_data['requested_by_id']
                logger.info(f"Completion - Application {application_id}: Using requested_by_id={resident_id}")
        
        if resident_id:
            certificate_type = app_data.get('request', 'Certificate')
            application_code = app_data.get('application_code', '')
            
            # Send notification
            try:
                NotificationService.send_to_resident(
                    resident_id=resident_id,
                    title="Certificate Issued",
                    body=f"Your {certificate_type} ({application_code}) has been successfully generated and issued. Thank you for using our services!",
                    deep_link=f"/(tabs)/documents/{application_id}"
                )
                logger.info(f"Completion notification sent to resident_id {resident_id} for application {application_id}")
            except Exception as notif_error:
                # Log but don't fail the main operation
                logger.error(f"Failed to send completion notification for application {application_id}: {notif_error}")
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'message': 'Application marked as Completed.'})
        set_flash(request, 'Application marked as Completed.', 'success')
        return redirect('secretary_module:application_detail', application_id=application_id)
    except Exception as e:
        msg = _clean_db_error(e)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'message': msg}, status=400)
        set_flash(request, msg, 'error')
        return redirect('secretary_module:application_detail', application_id=application_id)

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
        # Get application details before updating status
        app_data = SecretaryHelpers.get_specific_application(application_id)
        
        # Update status to For Payment
        SecretaryHelpers.set_application_to_for_payment(application_id)
        
        # Extract application details for notification
        certificate_type = app_data.get('request', 'Certificate') if app_data else 'Certificate'
        application_code = app_data.get('application_code', '') if app_data else ''
        
        # Send notification to ALL active treasurers about new application for payment
        try:
            logger.info(f"Attempting to send notification to treasurers for application {application_id}")
            # Get ALL active treasurer personnel IDs
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT pc.personnel_id, r.first_name, r.last_name
                    FROM Personnel_Credentials pc
                    JOIN Resident r ON pc.resident_id = r.resident_id
                    JOIN User_Role ur ON pc.role_id = ur.role_id
                    WHERE ur.role_name = 'Barangay Treasurer'
                    AND pc.is_active = TRUE
                """)
                treasurers = cursor.fetchall()
                
                if treasurers:
                    for treasurer in treasurers:
                        treasurer_id = treasurer[0]
                        treasurer_name = f"{treasurer[1]} {treasurer[2]}"
                        
                        result = NotificationService.send_to_personnel(
                            personnel_id=treasurer_id,
                            title="New Application for Payment",
                            body=f"{certificate_type} ({application_code}) has been forwarded and is ready for payment processing.",
                            deep_link=f"/treasurer_module/applications/{application_id}"
                        )
                        
                        if result:
                            logger.info(f"✅ Notification sent to treasurer {treasurer_name} (ID: {treasurer_id})")
                        else:
                            logger.error(f"❌ Failed to send notification to treasurer {treasurer_name} (ID: {treasurer_id})")
                else:
                    logger.warning(f"⚠️ No active treasurer found in database")
        except Exception as notif_error:
            logger.error(f"❌ Failed to send treasurer notification for application {application_id}: {notif_error}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Send notification to resident
        resident_id = None
        if app_data:
            # Priority 1: Extract applicant_id from total_amount_details JSON
            details_json = app_data.get('total_amount_details')
            if details_json:
                try:
                    if isinstance(details_json, str):
                        details_json = json.loads(details_json)
                    if isinstance(details_json, dict) and details_json.get('applicant_id'):
                        resident_id = details_json['applicant_id']
                        logger.info(f"Application {application_id}: Found applicant_id={resident_id} in total_amount_details")
                except Exception as e:
                    logger.error(f"Application {application_id}: Error parsing total_amount_details: {e}")
            
            # Priority 2: For business applications, get the business owner
            if not resident_id and app_data.get('business_id'):
                try:
                    business_data = Business.sp_get_business_detail(app_data['business_id'])
                    if business_data and business_data.get('owner_id'):
                        resident_id = business_data['owner_id']
                        logger.info(f"Application {application_id}: Found owner_id={resident_id} from business")
                except Exception as e:
                    logger.error(f"Failed to get business owner for business_id {app_data['business_id']}: {e}")
            
            # Priority 3: Fall back to requested_by_id (for resident-initiated applications)
            if not resident_id and app_data.get('requested_by') == 'resident' and app_data.get('requested_by_id'):
                resident_id = app_data['requested_by_id']
                logger.info(f"Application {application_id}: Using requested_by_id={resident_id}")
            
            if not resident_id:
                logger.warning(f"Could not determine resident_id for application {application_id}")
        
        if resident_id:
            certificate_type = app_data.get('request', 'Certificate')
            application_code = app_data.get('application_code', '')
            
            # Send notification
            try:
                NotificationService.send_to_resident(
                    resident_id=resident_id,
                    title="Certificate Ready for Payment",
                    body=f"Your {certificate_type} request ({application_code}) has been approved! Please visit the barangay office to complete your payment.",
                    deep_link=f"/(tabs)/documents/{application_id}"
                )
                logger.info(f"Notification sent to resident_id {resident_id} for application {application_id}")
            except Exception as notif_error:
                # Log but don't fail the main operation
                logger.error(f"Failed to send notification for application {application_id}: {notif_error}")
        
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
        set_flash(request, -_clean_db_error(e), "error")

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


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def ctc_fee(request):
    ctc_config = CTCFeeConfig.sp_get_ctc_fee()
    flash = get_flash(request)
    return render(request, 'secretary_module/ctcFee.html', {
        'ctc_config': ctc_config,
        'message': flash['message'],
        'message_level': flash['message_level'],
    })

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_POST
def ctc_fee_update(request):
    try:
        pid = _get_personnel_id(request)
        amount = request.POST.get('amount', '').strip()
        
        if not amount:
            return JsonResponse({'ok': False, 'error': 'Amount is required'}, status=400)
        
        try:
            amount_decimal = Decimal(amount)
        except (InvalidOperation, ValueError):
            return JsonResponse({'ok': False, 'error': 'Invalid amount format'}, status=400)
        
        if amount_decimal < 0:
            return JsonResponse({'ok': False, 'error': 'Amount must be non-negative'}, status=400)

        CTCFeeConfig.sp_update_ctc_fee(amount=amount_decimal, updated_by=pid)
        
        new_row = CTCFeeConfig.sp_get_ctc_fee()
        return JsonResponse({
            'ok': True,
            'row': {
                'amount': float(new_row.get('amount')) if new_row.get('amount') else None,
                'updated_at': new_row.get('updated_at').isoformat() if new_row.get('updated_at') else None,
            }
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def document_stamp_fee(request):
    """Display document stamp fee configuration page."""
    # Get Business Clearance Fee type ID (you may need to adjust this query)
    from .models import DocumentStampFee
    
    # Default to Business Clearance Fee (fee_type_id = 1, adjust if needed)
    fee_type_id = 1
    
    try:
        fee_data = DocumentStampFee.sp_get_document_stamp_fee(fee_type_id)
    except Exception:
        fee_data = None
    
    flash = get_flash(request)
    return render(request, 'secretary_module/documentStampFee.html', {
        'fee_data': fee_data,
        'fee_type_id': fee_type_id,
        'message': flash['message'],
        'message_level': flash['message_level'],
    })


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_POST
def document_stamp_fee_update(request):
    """Update document stamp fee amount."""
    from .models import DocumentStampFee
    
    try:
        pid = _get_personnel_id(request)
        fee_type_id = request.POST.get('fee_type_id', '').strip()
        amount = request.POST.get('amount', '').strip()
        
        if not fee_type_id:
            return JsonResponse({'ok': False, 'error': 'Fee type ID is required'}, status=400)
        
        if not amount:
            return JsonResponse({'ok': False, 'error': 'Amount is required'}, status=400)
        
        try:
            fee_type_id_int = int(fee_type_id)
        except (TypeError, ValueError):
            return JsonResponse({'ok': False, 'error': 'Invalid fee type ID'}, status=400)
        
        try:
            amount_decimal = Decimal(amount)
        except (InvalidOperation, ValueError):
            return JsonResponse({'ok': False, 'error': 'Invalid amount format'}, status=400)
        
        if amount_decimal < 0:
            return JsonResponse({'ok': False, 'error': 'Amount must be non-negative'}, status=400)

        message = DocumentStampFee.sp_update_document_stamp_fee(
            fee_type_id=fee_type_id_int,
            amount=amount_decimal,
            updated_by=pid
        )
        
        new_row = DocumentStampFee.sp_get_document_stamp_fee(fee_type_id_int)
        return JsonResponse({
            'ok': True,
            'message': message,
            'row': {
                'amount': float(new_row.get('amount')) if new_row and new_row.get('amount') else None,
                'updated_at': new_row.get('updated_at').isoformat() if new_row and new_row.get('updated_at') else None,
            }
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)
    

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
    # For relative paths, construct the media URL
    base = settings.MEDIA_URL or '/media/'
    if not base.endswith('/'):
        base += '/'
    media_path = base + path.lstrip('/')
    return request.build_absolute_uri(media_path)

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def announcement_detail(request, announcement_id: int):
    """View specific announcement details using get_specific_announcement function"""
    try:
        announcement = AnnouncementRepo.get_one(announcement_id)
        if not announcement:
            raise Http404('Announcement not found')
        
        # Normalize image URL for display
        if announcement.get('announcement_image_path'):
            image_path = announcement.get('announcement_image_path')
            if image_path and (image_path.startswith('http://') or image_path.startswith('https://')):
                announcement['image_url'] = image_path  # Already a full URL from Supabase
            else:
                announcement['image_url'] = _public_url(request, image_path)  # Fallback for local files
        
        # Normalize audience display
        if announcement.get('audience'):
            announcement['audience'] = _SQL_TO_UI_AUDIENCE.get(announcement['audience'], 'EVERYONE')
        
        # Compatibility aliases
        if 'created_date' in announcement and 'date' not in announcement:
            announcement['date'] = announcement['created_date']
        
        return render(request, 'secretary_module/announcement_detail.html', {
            'announcement': announcement
        })
    except Http404:
        raise
    except Exception as e:
        messages.error(request, f"Failed to load announcement: {str(e)}")
        return redirect('secretary_module:secretary_dashboard')

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
                try:
                    # Validate file type
                    if not f.content_type.startswith('image/'):
                        ctx['errors'].append('Please upload a valid image file.')
                    # Validate file size (5MB limit)
                    elif f.size > 5 * 1024 * 1024:
                        ctx['errors'].append('Image file size must be less than 5MB.')
                    else:
                        # Upload to Supabase
                        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
                        
                        # Generate unique filename
                        file_extension = os.path.splitext(f.name)[1].lower()
                        if file_extension not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                            file_extension = '.jpg'
                        unique_filename = f"{uuid.uuid4()}{file_extension}"
                        
                        # Upload file to Supabase storage
                        response = supabase.storage.from_(settings.SUPABASE_BUCKET_ANNOUNCEMENTS).upload(
                            unique_filename,
                            f.read()
                        )
                        
                        if response:
                            # Try public URL first, fallback to signed URL if bucket is private
                            try:
                                public_url = supabase.storage.from_(settings.SUPABASE_BUCKET_ANNOUNCEMENTS).get_public_url(unique_filename)
                                image_db_path = public_url
                            except Exception:
                                # Fallback to signed URL (24 hours expiry)
                                signed_url = supabase.storage.from_(settings.SUPABASE_BUCKET_ANNOUNCEMENTS).create_signed_url(unique_filename, 86400)
                                image_db_path = signed_url.get('signedURL') if signed_url else None
                                if not image_db_path:
                                    ctx['errors'].append('Failed to generate image URL.')
                        else:
                            ctx['errors'].append('Failed to upload image. Please try again.')
                except Exception as e:
                    ctx['errors'].append(f'Failed to upload image: {str(e)}')

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

    # normalize image URL for the selected item (Supabase URLs are already public)
    if selected and 'announcement_image_path' in selected:
        image_path = selected.get('announcement_image_path')
        if image_path and (image_path.startswith('http://') or image_path.startswith('https://')):
            selected['image_url'] = image_path  # Already a full URL from Supabase
        else:
            selected['image_url'] = _public_url(request, image_path)  # Fallback for local files

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


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_POST
def cancel_application(request, application_id: int):
    """Cancel an application when allowed (Pending or For Payment).

    Accepts optional 'reason' field. Returns JSON for AJAX, or flashes and redirects otherwise.
    Server-side guard is primarily in SQL; we surface the DB message back to the client.
    """
    reason = (request.POST.get('reason') or '').strip() or None
    try:
        # Prefer posted personnel_id if provided; otherwise fall back to session/user
        posted_pid = request.POST.get('personnel_id')
        try:
            personnel_id = int(posted_pid) if posted_pid is not None else None
        except (TypeError, ValueError):
            personnel_id = None
        if not personnel_id:
            personnel_id = _acting_personnel_id(request)
        if not personnel_id:
            raise ValueError('Missing personnel_id for cancellation.')

        message = SecretaryHelpers.secretary_cancel_application(application_id, personnel_id, reason)
        
        # Send notification to resident about cancellation
        try:
            app_data = SecretaryHelpers.get_specific_application(application_id)
            resident_id = None
            
            if app_data:
                # Extract applicant_id from total_amount_details JSON
                details_json = app_data.get('total_amount_details')
                if details_json:
                    try:
                        if isinstance(details_json, str):
                            details_json = json.loads(details_json)
                        if isinstance(details_json, dict) and details_json.get('applicant_id'):
                            resident_id = details_json['applicant_id']
                    except Exception:
                        pass
                
                # Fallback: business owner_id
                if not resident_id and app_data.get('business_id'):
                    try:
                        business_data = Business.sp_get_business_detail(app_data['business_id'])
                        if business_data and business_data.get('owner_id'):
                            resident_id = business_data['owner_id']
                    except Exception:
                        pass
                
                # Fallback: requested_by_id (only if requested_by == 'resident')
                if not resident_id and app_data.get('requested_by') == 'resident' and app_data.get('requested_by_id'):
                    resident_id = app_data['requested_by_id']
            
            if resident_id:
                certificate_type = app_data.get('request', 'Certificate')
                application_code = app_data.get('application_code', '')
                
                NotificationService.send_to_resident(
                    resident_id=resident_id,
                    title="Application Cancelled",
                    body=f"Your {certificate_type} application ({application_code}) has been cancelled.{' Reason: ' + reason if reason else ''}",
                    deep_link=f"/(tabs)/documents/{application_id}"
                )
                logger.info(f"Cancellation notification sent to resident {resident_id} for application {application_id}")
        except Exception as e:
            logger.error(f"Failed to send cancellation notification for application {application_id}: {e}")
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'message': message})
        set_flash(request, message or 'Application cancelled.', 'success')
        return redirect('secretary_module:application_detail', application_id=application_id)
    except Exception as e:
        msg = _clean_db_error(e)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'message': msg}, status=400)
        set_flash(request, msg, 'error')
        return redirect('secretary_module:application_detail', application_id=application_id)


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
    """Create an application for either Business or Barangay Clearances.
    Branch based on the fee_type_name.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest('POST required')

    fee_type_id_raw = request.POST.get('fee_type_id')
    try:
        fee_type_id = int(fee_type_id_raw)
    except (TypeError, ValueError):
        messages.error(request, 'Invalid fee type.')
        return redirect('secretary_module:create_application')

    # Look up fee type name to determine flow
    with connection.cursor() as cur:
        cur.execute('SELECT fee_type_name FROM Fee_Type WHERE fee_type_id=%s LIMIT 1', [fee_type_id])
        row = cur.fetchone()
        fee_type_name = (row[0] if row else '')

    acting_pid = _acting_personnel_id(request)

    # Robust match: fee type labels may be "Barangay Clearance Fee" (renamed from "Barangay Clearances")
    normalized_fee = fee_type_name.lower()
    if 'barangay clearance' in normalized_fee:
        # Resident-based Barangay Clearance
        resident_id_raw = request.POST.get('applicant_id')
        purpose_id_raw = request.POST.get('purpose')  # holds other_clearance_id when barangay clearances
        try:
            resident_id = int(resident_id_raw)
            other_clearance_id = int(purpose_id_raw)
        except (TypeError, ValueError):
            messages.error(request, 'Please select a resident and a purpose.')
            return redirect('secretary_module:create_application')
        try:
            app_id = SecretaryHelpers.create_application_barangay_clearance(
                personnel_id=acting_pid,
                resident_id=resident_id,
                other_clearance_id=other_clearance_id,
            )
            if not app_id:
                messages.error(request, 'Application was not created.')
                return redirect('secretary_module:create_application')
            messages.success(request, f'Barangay clearance application #{app_id} created.')
            return redirect('secretary_module:applications')
        except Exception as e:
            messages.error(request, _clean_db_error(e))
            return redirect('secretary_module:create_application')
    else:
        # Business Clearance flow
        try:
            business_id = int(request.POST.get('business_id') or 0)
            cat_id = int(request.POST.get('business_clearance_category') or request.POST.get('category_id') or 0)
        except (TypeError, ValueError):
            messages.error(request, 'Invalid business/category selection.')
            return redirect('secretary_module:create_application')

        purpose = (request.POST.get('purpose') or '').strip() or None
        vq = _to_int_or_none(request.POST.get('videoke_qty'))
        bq = _to_int_or_none(request.POST.get('billiard_qty'))
        oq = _to_int_or_none(request.POST.get('other_device_qty'))

        try:
            app_id = SecretaryHelpers.create_application_business(
                fee_type_id=fee_type_id,
                business_id=business_id,
                business_clearance_category=cat_id,
                videoke_qty=vq,
                billiard_qty=bq,
                other_device_qty=oq,
                purpose=purpose,
                requested_by='personnel',
                requested_by_id=acting_pid,
            )
            if not app_id:
                messages.error(request, 'Application was not created.')
                return redirect('secretary_module:create_application')
            messages.success(request, f'Business clearance application #{app_id} created.')
            return redirect('secretary_module:applications')
        except Exception as e:
            messages.error(request, _clean_db_error(e))
            return redirect('secretary_module:create_application')


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def application_search(request):
    """AJAX search used by the walk-in UI.
    If fee_name contains 'Barangay Clearance' (supports legacy 'Barangay Clearances' and new 'Barangay Clearance Fee')
    -> search residents; else -> search business/owner.
    """
    q = (request.GET.get('q') or '').strip()
    fee_name = (request.GET.get('fee_name') or '').strip()
    limit = 25
    offset = 0
    if not q:
        return JsonResponse([], safe=False)
    try:
        normalized_fee = fee_name.lower()
        if 'barangay clearance' in normalized_fee:
            # Use the new resident search tailored for clearance picker
            rows = SecretaryHelpers.search_resident_for_clearance(q, limit, offset, None, None, None)
            payload = [{
                'resident_id': r.get('resident_id'),
                'resident_code': r.get('resident_code'),
                'full_name': r.get('full_name'),
                'dob': r.get('dob'),
                'complete_address': r.get('complete_address'),
                # Include status field returned by the function so UI can show Pending/Resident
                'resident_status_name': r.get('resident_status_name') or r.get('resident_status') or None,
            } for r in rows]
            return JsonResponse(payload, safe=False)
        else:
            rows = SecretaryHelpers.search_owner(q, limit, offset)
            return JsonResponse(rows, safe=False)
    except Exception as e:
        return JsonResponse({'error': coerce_message(e)}, status=400)


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
@require_POST
def create_reprint_business_clearance(request):
    """Create a REPRINT business clearance application.

    POST params:
      - business_id
    Returns JSON { ok: true, application_id } or { ok: false, message }
    """
    try:
        business_id = int(request.POST.get('business_id'))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'message': 'Invalid business_id'}, status=400)
    try:
        personnel_id = _acting_personnel_id(request)
        app_id = SecretaryHelpers.create_reprint_business_clearance(
            business_id=business_id,
            requested_by='personnel',
            requested_by_id=personnel_id,
        )
        if not app_id:
            return JsonResponse({'ok': False, 'message': 'No application id returned.'}, status=400)
        return JsonResponse({'ok': True, 'application_id': app_id})
    except Exception as e:
        # Return a specific, cleaned DB error instead of a vague default
        return JsonResponse({'ok': False, 'message': _clean_db_error(e)}, status=400)


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_POST
def create_renewal_business_clearance(request):
    """Create a RENEWAL business clearance application.

    POST params:
      - business_id
    Returns JSON { ok: true, application_id } or { ok: false, message }
    """
    try:
        business_id = int(request.POST.get('business_id'))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'message': 'Invalid business_id'}, status=400)

    try:
        personnel_id = _acting_personnel_id(request)
        app_id = SecretaryHelpers.create_renewal_business_clearance(
            business_id=business_id,
            requested_by='personnel',
            requested_by_id=personnel_id,
        )
        if not app_id:
            return JsonResponse({'ok': False, 'message': 'No application id returned.'}, status=400)
        
        # Send notification to business owner
        # Note: The database trigger will automatically send the push notification via webhook
        try:
            # Get business details
            business_detail = Business.sp_get_business_detail(business_id)
            
            if business_detail:
                # Try different possible field names for resident_id
                resident_id = (
                    business_detail.get('resident_id') or 
                    business_detail.get('owner_id') or 
                    business_detail.get('owner_resident_id') or
                    business_detail.get('residentid')
                )
                business_name = business_detail.get('business_name')
                
                # Get application details for total amount
                app_data = SecretaryHelpers.get_specific_application(app_id)
                total_amount = app_data.get('total_amount') if app_data else None
                
                if resident_id and business_name:
                    amount_text = f"₱{total_amount:,.2f}" if total_amount else "TBD"
                    
                    # Create notification record only - trigger handles push notification
                    NotificationService.send_to_resident(
                        resident_id=resident_id,
                        title="Business Clearance Renewal Submitted",
                        body=f'Your business clearance renewal request for "{business_name}" has been successfully submitted.  Total amount: {amount_text}. Please proceed to payment.',
                        deep_link="/(tabs)/business",
                        data={
                            'type': 'business_clearance_renewal',
                            'application_id': app_id,
                            'business_id': business_id,
                            'business_name': business_name,
                            'total_amount': str(total_amount) if total_amount else None
                        }
                    )
        except Exception as notif_error:
            logger.error(f"Failed to create business clearance renewal notification: {notif_error}", exc_info=True)
        
        return JsonResponse({'ok': True, 'application_id': app_id})
    except Exception as e:
        return JsonResponse({'ok': False, 'message': _clean_db_error(e)}, status=400)


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_POST
def create_registration_business_clearance(request):
    """Create a REGISTRATION business clearance application.

    POST params:
      - business_id
    Returns JSON { ok: true, application_id } or { ok: false, message }
    """
    try:
        business_id = int(request.POST.get('business_id'))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'message': 'Invalid business_id'}, status=400)

    try:
        personnel_id = _acting_personnel_id(request)
        app_id = SecretaryHelpers.create_registration_business_clearance(
            business_id=business_id,
            requested_by='personnel',
            requested_by_id=personnel_id,
        )
        if not app_id:
            return JsonResponse({'ok': False, 'message': 'No application id returned.'}, status=400)
        
        # Send notification to business owner
        # Note: The database trigger will automatically send the push notification via webhook
        try:
            # Get business details
            business_detail = Business.sp_get_business_detail(business_id)
            
            if business_detail:
                # Try different possible field names for resident_id
                resident_id = (
                    business_detail.get('resident_id') or 
                    business_detail.get('owner_id') or 
                    business_detail.get('owner_resident_id') or
                    business_detail.get('residentid')
                )
                business_name = business_detail.get('business_name')
                
                # Get application details for total amount
                app_data = SecretaryHelpers.get_specific_application(app_id)
                total_amount = app_data.get('total_amount') if app_data else None
                
                if resident_id and business_name:
                    amount_text = f"₱{total_amount:,.2f}" if total_amount else "TBD"
                    
                    # Create notification record only - trigger handles push notification
                    NotificationService.send_to_resident(
                        resident_id=resident_id,
                        title="Business Clearance Request Submitted",
                        body=f'Your business clearance request for "{business_name}" has been successfully submitted.  Total amount: {amount_text}. Please proceed to payment.',
                        deep_link="/(tabs)/business",
                        data={
                            'type': 'business_clearance_registration',
                            'application_id': app_id,
                            'business_id': business_id,
                            'business_name': business_name,
                            'total_amount': str(total_amount) if total_amount else None
                        }
                    )
        except Exception as notif_error:
            logger.error(f"Failed to create business clearance registration notification: {notif_error}", exc_info=True)
        
        return JsonResponse({'ok': True, 'application_id': app_id})
    except Exception as e:
        return JsonResponse({'ok': False, 'message': _clean_db_error(e)}, status=400)


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_POST
def create_closure_business_clearance(request):
    """Create a BUSINESS CLOSURE application for an INACTIVE business.

    POST params:
      - business_id
    Returns JSON { ok: true, application_id } or { ok: false, message }
    """
    try:
        business_id = int(request.POST.get('business_id'))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'message': 'Invalid business_id'}, status=400)

    try:
        personnel_id = _acting_personnel_id(request)
        app_id = SecretaryHelpers.create_closure_business_clearance(
            business_id=business_id,
            requested_by='personnel',
            requested_by_id=personnel_id,
        )
        if not app_id:
            return JsonResponse({'ok': False, 'message': 'No application id returned.'}, status=400)
        return JsonResponse({'ok': True, 'application_id': app_id})
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
    """Generate a filled PDF for the given application.

    - Barangay Clearance uses static/prints/Template1_Clearance_LETTER.pdf and fills:
      full_name, full_address, purpose, day, month, year, or_number, fulldate_issue, fullname_captain
    - Business Clearance/Closure uses static/prints/Template2_Business_Clearance_LETTER.pdf and fills:
      business_name, owners_name, full_address, nature_of_business, day, month, year, paid, fulldate_issue, or_number, fullname_captain

    Falls back to applications list with an error message if anything fails.
    """
    # Step 1: Fetch and normalize context
    try:
        # Fetch core application first to enforce no PDF regeneration after completion
        app_row = SecretaryHelpers.get_specific_application(application_id) or {}
        app_status = (app_row.get('application_status') or '').strip().lower()
        if app_status == 'completed':
            messages.warning(request, 'Completed applications cannot be re-generated.')
            return redirect('secretary_module:application_detail', application_id=application_id)

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

    # Step 2: Choose template and fields based on request type, then fill AcroForm
    try:
        # Normalize date parts
        fulldate = ctx.get('fulldate_issue')
        day = ctx.get('day')
        month = ctx.get('month')
        year = ctx.get('year')
        try:
            if fulldate and (not day or not month or not year):
                day = day or f"{getattr(fulldate, 'day', '')}"
                try:
                    month = month or getattr(fulldate, 'strftime', lambda *_: '')('%B')
                except Exception:
                    month = month or ''
                year = year or f"{getattr(fulldate, 'year', '')}"
        except Exception:
            pass

        request_label = (ctx.get('request') or '').strip().lower()
        is_barangay = (request_label == 'barangay clearance')

        if is_barangay:
            # Barangay Clearance template selection (with Residency variant)
            purpose_label = (ctx.get('purpose') or '').strip().lower()
            is_residency = (purpose_label == 'certificate of residency' or 'residency' in purpose_label)

            if is_residency:
                # Certificate of Residency uses Template3_Residency_LETTER.pdf
                template_path = os.path.join(settings.BASE_DIR, 'static', 'prints', 'Template3_Residency_LETTER.pdf')
                if not os.path.exists(template_path):
                    messages.error(request, 'PDF generation error: Template3_Residency_LETTER.pdf not found.')
                    return redirect('secretary_module:applications')

                fields = {
                    'full_name':        ctx.get('full_name') or '',
                    'full_address':     ctx.get('full_address') or '',
                    'day':              str(day or ''),
                    'month':            str(month or ''),
                    'year':             str(year or ''),
                    'or_number':        str(ctx.get('or_number') or ''),
                    'fulldate_issue':   getattr(fulldate, 'strftime', lambda *_: '')('%B %d, %Y') if fulldate else (ctx.get('fulldate_issue') or ''),
                    'fullname_captain': ctx.get('fullname_captain') or '',
                }
                suggested_name = 'residency_certificate'
            else:
                # Default Barangay Clearance
                template_path = os.path.join(settings.BASE_DIR, 'static', 'prints', 'Template1_Clearance_LETTER.pdf')
                if not os.path.exists(template_path):
                    messages.error(request, 'PDF generation error: Template1_Clearance_LETTER.pdf not found.')
                    return redirect('secretary_module:applications')

                fields = {
                    'full_name':        ctx.get('full_name') or '',
                    'full_address':     ctx.get('full_address') or '',
                    'purpose':          ctx.get('purpose') or '',
                    'day':              str(day or ''),
                    'month':            str(month or ''),
                    'year':             str(year or ''),
                    'or_number':        str(ctx.get('or_number') or ''),
                    'fulldate_issue':   getattr(fulldate, 'strftime', lambda *_: '')('%B %d, %Y') if fulldate else (ctx.get('fulldate_issue') or ''),
                    'fullname_captain': ctx.get('fullname_captain') or '',
                }
                suggested_name = 'barangay_clearance'
        else:
            # Business Clearance/Closure template and field mapping
            template_path = os.path.join(settings.BASE_DIR, 'static', 'prints', 'Template2_Business_Clearance_LETTER.pdf')
            if not os.path.exists(template_path):
                messages.error(request, 'PDF generation error: Template2_Business_Clearance_LETTER.pdf not found.')
                return redirect('secretary_module:applications')

            paid_val = ctx.get('paid')
            try:
                if paid_val is not None:
                    paid_val = float(paid_val)
            except Exception:
                pass
            paid_str = (
                f"₱{paid_val:,.2f}" if isinstance(paid_val, (int, float)) else (str(paid_val) if paid_val is not None else '')
            )

            fields = {
                'business_name':      ctx.get('business_name') or '',
                'owners_name':        ctx.get('owners_name') or '',
                'full_address':       ctx.get('full_address') or '',
                'nature_of_business': ctx.get('nature_of_business') or '',
                'day':                str(day or ''),
                'month':              str(month or ''),
                'year':               str(year or ''),
                'paid':               paid_str,
                'fulldate_issue':     getattr(fulldate, 'strftime', lambda *_: '')('%B %d, %Y') if fulldate else (ctx.get('fulldate_issue') or ''),
                'or_number':          str(ctx.get('or_number') or ''),
                'fullname_captain':   ctx.get('fullname_captain') or '',
            }
            suggested_name = 'business_clearance'

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

        # Mark fields as ReadOnly (/Ff bit 1) so they aren't editable after filling
        try:
            acro_obj = writer._root_object.get(NameObject('/AcroForm'))
            if acro_obj is not None:
                fields_arr = acro_obj.get_object().get(NameObject('/Fields'))
                if fields_arr:
                    for f in fields_arr:
                        try:
                            f_obj = f.get_object()
                            curr = int(f_obj.get(NameObject('/Ff'), 0))
                            f_obj.update({NameObject('/Ff'): NumberObject(curr | 1)})
                        except Exception:
                            pass
        except Exception:
            # non-fatal
            pass

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

        # Attempt to apply document permissions: allow printing/accessibility; disallow edits/form filling
        try:
            try:
                # pypdf >= 4 style
                from pypdf import Permissions as _Perms
                allow_perms = {_Perms.PRINT, _Perms.ACCESSIBILITY}
                writer.encrypt(user_password="", permissions=allow_perms)
            except Exception:
                # Older pypdf fallback: best-effort basic encryption with empty password
                try:
                    writer.encrypt("")
                except Exception:
                    pass
        except Exception:
            pass

        # Stream to HTTP response
        pdf_bytes = io.BytesIO()
        writer.write(pdf_bytes)
        pdf_bytes.seek(0)

        # suggested_name determined above per branch (defaults handled for safety)
        suggested_name = locals().get('suggested_name') or ('barangay_clearance' if is_barangay else 'business_clearance')
        response = HttpResponse(pdf_bytes.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{suggested_name}_{application_id}.pdf"'
        return response
    except Exception as e:
        messages.error(request, f'PDF generation error: {coerce_message(e)}')
        return redirect('secretary_module:applications')

@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_POST
def preview_barangay_clearance(request):
    """Preview fee breakdown for a Barangay Clearance resident application."""
    try:
        resident_id = int(request.POST.get('resident_id'))
        other_clearance_id = int(request.POST.get('other_clearance_id'))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'message': 'Invalid resident or purpose selection.'}, status=400)
    try:
        data = SecretaryHelpers.secretary_preview_barangay_clearance(resident_id, other_clearance_id)
        if not data:
            return JsonResponse({'ok': False, 'message': 'No preview data returned.'}, status=404)
        return JsonResponse({
            'ok': True,
            'applicant_id': data.get('applicant_id'),
            'applicant_full_name': data.get('applicant_full_name'),
            'purpose': data.get('purpose'),
            'total_amount': data.get('total_amount'),
            'total_amount_details': data.get('total_amount_details'),
            'has_open_application': data.get('has_open_application'),
            'open_application_id': data.get('open_application_id'),
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'message': coerce_message(e)}, status=400)

    
@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_POST
def submit_barangay_clearance_application(request):
    """Create a barangay clearance application.

    Accepts POST fields:
      - applicant_id (resident id)
      - other_clearance_id (purpose id)

    Returns JSON when XHR or Accept header requests JSON; otherwise
    falls back to redirect + Django messages.
    """
    def _is_ajax(r):
        return r.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest' or 'application/json' in (r.headers.get('Accept',''))

    resident_raw = (request.POST.get('applicant_id') or request.POST.get('resident_id') or '').strip()
    purpose_raw  = (request.POST.get('other_clearance_id') or request.POST.get('purpose') or '').strip()

    # Coerce ints safely
    def _to_int(val):
        try:
            return int(val)
        except (TypeError, ValueError):
            return None

    resident_id = _to_int(resident_raw)
    other_clearance_id = _to_int(purpose_raw)

    if not resident_id:
        msg = 'Missing or invalid resident id.'
        if _is_ajax(request):
            return JsonResponse({'ok': False, 'error': msg}, status=400)
        messages.error(request, msg)
        return redirect('secretary_module:add_certificate')

    if not other_clearance_id:
        msg = 'Please select a valid purpose.'
        if _is_ajax(request):
            return JsonResponse({'ok': False, 'error': msg}, status=400)
        messages.error(request, msg)
        return redirect('secretary_module:add_certificate')

    personnel_id = _acting_personnel_id(request)

    try:
        application_id = SecretaryHelpers.create_application_barangay_clearance(
            personnel_id=personnel_id,
            resident_id=resident_id,
            other_clearance_id=other_clearance_id,
        )
        if not application_id:
            raise RuntimeError('No application id returned from database function.')
        
        # Send notification to resident
        try:
            NotificationService.send_to_resident(
                resident_id=resident_id,
                title="Application Created",
                body="A barangay clearance application has been created for you. Please wait for the Barangay Secretary to review and approve your request.",
                deep_link=f"/(tabs)/documents/{application_id}"
            )
            logger.info(f"Application creation notification sent to resident_id {resident_id} for application {application_id}")
        except Exception as notif_error:
            # Log but don't fail the main operation
            logger.error(f"Failed to send application creation notification for application {application_id}: {notif_error}")
            
    except Exception as e:
        # Prefer cleaned DB error message, fallback to str(e)
        cleaned = _clean_db_error(e) if callable(_clean_db_error) else None
        msg = cleaned or coerce_message(e) or str(e) or 'Unexpected error.'
        if _is_ajax(request):
            return JsonResponse({'ok': False, 'error': msg}, status=500)
        messages.error(request, f'Failed to create barangay clearance: {msg}')
        return redirect('secretary_module:add_certificate')

    success_msg = 'Barangay clearance application created.'
    if _is_ajax(request):
        return JsonResponse({'ok': True, 'application_id': application_id, 'message': success_msg})

    messages.success(request, success_msg)
    return redirect('secretary_module:applications')


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
def reports(request):
    """Reports page - shows available reports"""
    return render(request, 'secretary_module/Reports.html')


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_GET
def generate_resident_list_pdf(request):
    """Generate PDF report for resident list with applied filters"""
    from reports_module.pdf_templates.resident.resident_list_filtered import generate_resident_list_pdf
    
    # Get filters from request
    q = request.GET.get('q', '').strip()
    status_id_list = request.GET.getlist('status_id')
    sitio_id_list = request.GET.getlist('sitio_id')
    quarter_id = request.GET.get('quarter_id') or None
    
    # Convert to integers
    status_id_list = [int(sid) for sid in status_id_list if sid.isdigit()]
    sitio_id_list = [int(sid) for sid in sitio_id_list if sid.isdigit()]
    
    if quarter_id and quarter_id.isdigit():
        quarter_id = int(quarter_id)
    else:
        quarter_id = None
    
    try:
        # If multiple filters selected, fetch and merge results
        if len(status_id_list) > 1 or len(sitio_id_list) > 1:
            all_residents = []
            
            # If we have multiple statuses, fetch for each
            if len(status_id_list) > 1:
                for status_id in status_id_list:
                    sitio_id = sitio_id_list[0] if sitio_id_list else None
                    residents_batch = ResidentList.sp_get_all_residents(
                        p_status_id=status_id,
                        p_sitio_id=sitio_id,
                        p_query=q or None,
                        p_limit=None,
                        p_offset=0,
                        p_quarter_id=quarter_id
                    )
                    all_residents.extend(residents_batch)
            # If we have multiple sitios but single status
            elif len(sitio_id_list) > 1:
                status_id = status_id_list[0] if status_id_list else None
                for sitio_id in sitio_id_list:
                    residents_batch = ResidentList.sp_get_all_residents(
                        p_status_id=status_id,
                        p_sitio_id=sitio_id,
                        p_query=q or None,
                        p_limit=None,
                        p_offset=0,
                        p_quarter_id=quarter_id
                    )
                    all_residents.extend(residents_batch)
            
            # Remove duplicates
            seen_ids = set()
            residents = []
            for r in all_residents:
                if r.get('resident_id') not in seen_ids:
                    seen_ids.add(r.get('resident_id'))
                    residents.append(r)
            
            total_count = len(residents)
        else:
            # Single or no filters
            status_id = status_id_list[0] if status_id_list else None
            sitio_id = sitio_id_list[0] if sitio_id_list else None
            
            # Fetch all residents (without pagination for complete report)
            residents = ResidentList.sp_get_all_residents(
                p_status_id=status_id,
                p_sitio_id=sitio_id,
                p_query=q or None,
                p_limit=None,  # Get all
                p_offset=0,
                p_quarter_id=quarter_id
            )
            
            # Get total count
            total_count = ResidentList.sp_get_all_residents_count(
                p_status_id=status_id,
                p_sitio_id=sitio_id,
                p_query=q or None,
                p_quarter_id=quarter_id
            )
        
        # Build filter description with actual names
        filters_applied = {}
        if quarter_id:
            # Get quarter display label (simplified format: Q# YYYY)
            quarters = ResidentList.sp_get_all_quarters()
            quarter = next((q for q in quarters if q['quarter_id'] == quarter_id), None)
            if quarter:
                filters_applied['quarter'] = f"Q{quarter['quarter_number']} {quarter['year']}"
            else:
                filters_applied['quarter'] = f'Quarter ID: {quarter_id}'
        else:
            filters_applied['quarter'] = 'Current Quarter'
        if q:
            filters_applied['search_query'] = q
        if status_id_list:
            # Get status names from database
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT status_name FROM Resident_Status WHERE status_id = ANY(%s) ORDER BY status_name",
                    [status_id_list]
                )
                status_names = [row[0] for row in cur.fetchall()]
                filters_applied['status'] = status_names
        if sitio_id_list:
            # Get sitio names from database
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT sitio_name FROM Sitio WHERE sitio_id = ANY(%s) ORDER BY sitio_name",
                    [sitio_id_list]
                )
                sitio_names = [row[0] for row in cur.fetchall()]
                filters_applied['sitio'] = sitio_names
        
        # Generate PDF
        pdf_buffer = generate_resident_list_pdf(residents, filters_applied, total_count)
        
        # Return PDF response
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        filename = f"Resident_List_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
        
    except Exception as e:
        import traceback
        print(f"[ERROR] Failed to generate resident list PDF: {traceback.format_exc()}")
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_GET
def generate_resident_detail_pdf(request, resident_id: int):
    """Generate PDF report for specific resident details"""
    from reports_module.pdf_templates.resident.resident_detail import generate_resident_detail_pdf
    
    quarter_id = request.GET.get('quarter_id') or None
    if quarter_id and quarter_id.isdigit():
        quarter_id = int(quarter_id)
    else:
        quarter_id = None
    
    try:
        # Fetch resident details using the same function as the modal
        resident = ResidentList.sp_get_specific_resident(resident_id, quarter_id)
        
        if not resident:
            return HttpResponse("Resident not found", status=404)
        
        # Generate PDF
        pdf_buffer = generate_resident_detail_pdf(resident)
        
        # Return PDF response
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        resident_name = resident.get('full_name', f'Resident_{resident_id}').replace(' ', '_')
        filename = f"{resident_name}_Profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
        
    except Exception as e:
        import traceback
        print(f"[ERROR] Failed to generate resident detail PDF: {traceback.format_exc()}")
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_GET
def generate_household_list_pdf(request):
    """Generate PDF report for household list with applied filters"""
    from reports_module.pdf_templates.household.household_list_filtered import HouseholdListFilteredPDF
    
    # Get filters from request
    query = request.GET.get('query', '').strip() or None
    status = request.GET.get('status', 'all').strip()
    sitio_id = request.GET.get('sitio_id', '').strip() or None
    quarter_id = request.GET.get('quarter_id', '').strip() or None
    
    try:
        # Generate PDF
        pdf_generator = HouseholdListFilteredPDF(
            query=query,
            status=status,
            sitio_id=sitio_id,
            quarter_id=quarter_id
        )
        pdf_buffer = pdf_generator.generate()
        
        # Return PDF response
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        filename = f"Household_List_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
        
    except Exception as e:
        import traceback
        print(f"[ERROR] Failed to generate household list PDF: {traceback.format_exc()}")
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)


@custom_login_required
@role_required('Barangay Secretary', 'Barangay Assistant Secretary')
@require_GET
def generate_household_detail_pdf(request, household_id: int):
    """Generate PDF report for specific household details"""
    from reports_module.pdf_templates.household.household_detail import HouseholdDetailPDF
    
    quarter_id = request.GET.get('quarter_id') or None
    if quarter_id and quarter_id.isdigit():
        quarter_id = int(quarter_id)
    else:
        quarter_id = None
    
    try:
        # Generate PDF
        pdf_generator = HouseholdDetailPDF(household_id=household_id, quarter_id=quarter_id)
        pdf_buffer = pdf_generator.generate()
        
        # Return PDF response
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        filename = f"Household_{household_id}_Profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
        
    except Exception as e:
        import traceback
        print(f"[ERROR] Failed to generate household detail PDF: {traceback.format_exc()}")
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)

