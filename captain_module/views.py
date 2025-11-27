from django.shortcuts import render, redirect
from authentication.decorators import custom_login_required, role_required
from utils.flash import set_flash, get_flash
from utils.db_message import _clean_db_error, _clean_params
from .models import Captain, Dashboard, AnnouncementRepo, ResidentList, BusinessList
from django.utils.http import urlencode
from utils.constants import VALID_SORT_BY, VALID_SORT_DIR, LIMIT_OPTIONS
from django.contrib import messages
from datetime import datetime
import json
from household_module.models import Household, Family
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from django.db import connection
from math import ceil


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
@role_required('Barangay Captain')
def captain_dashboard(request):
    # ---- KPIs ----
    try:
        totals = Dashboard.sp_dashboard_totals(barangay=None, city=None)
    except Exception as e:
        messages.error(request, f"Failed loading totals: {e}")
        totals = {
            "total_resident": 0, "total_non_resident": 0, "total_pending": 0,
            "total_male": 0, "total_female": 0
        }

    # ---- Bar (per sitio) ----
    try:
        per_sitio_rows   = Dashboard.sp_residents_per_sitio_json()
        per_sitio_labels = [str(r.get("sitio_name", "Unknown")) for r in per_sitio_rows]
        per_sitio_data   = [int(r.get("resident_count") or 0)   for r in per_sitio_rows]
    except Exception as e:
        messages.error(request, f"Failed loading per-sitio data: {e}")
        per_sitio_labels, per_sitio_data = [], []

    # ---- Pie (age) ----
    try:
        age_rows = Dashboard.sp_age_bracket_distribution()
        cleaned = []
        for item in age_rows or []:
            cleaned.append(item.get("jsonb_build_object", item))
        age_labels = [str(r.get("bracket", "Unknown")) for r in cleaned]
        age_data   = [int(r.get("count") or 0) for r in cleaned]
        total = sum(age_data) or 1
        age_labels_pct = [f"{lbl} ({round((cnt/total)*100)}%)" for lbl, cnt in zip(age_labels, age_data)]
    except Exception as e:
        messages.error(request, f"Failed loading age distribution: {e}")
        age_labels, age_data, age_labels_pct = [], [], []

    # === Recent announcements (use list_all so we surely have 'audience') ===
    try:
        raw_latest = AnnouncementRepo.list_all(sort='date_desc', limit=20, audience=None)
        latest_announcements = []
        for a in raw_latest:
            aud = ((a.get("audience") or a.get("p_audience") or "both").strip().lower())
            a["audience"] = aud
            a["announcement_date"] = a.get("announcement_date") or a.get("created_date")
            if aud in ("personnel", "both"):     # BHW sees Personnel + Everyone
                latest_announcements.append(a)
            if len(latest_announcements) >= 3:
                break
    except Exception as e:
        messages.error(request, f"Failed loading recent announcements: {e}")
        latest_announcements = []

    # ---- Modal filters ----
    ann_q        = (request.GET.get('ann_q') or '').strip() or None
    ann_aud      = (request.GET.get('ann_audience') or '').strip() or None
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

    # ---- Full list for modal (restricted to personnel scope) ----
    try:
        rows = AnnouncementRepo.list_all(
            q=ann_q, date_from=ann_from, date_to=ann_to,
            created_by=None, sort='date_desc', limit=200, offset=0,
            audience=ann_aud or None
        )
        announcements_all = []
        for a in rows:
            aud = ((a.get("audience") or a.get("p_audience") or "both").strip().lower())
            a["audience"] = aud
            a["announcement_date"] = a.get("announcement_date") or a.get("created_date")
            if aud in ("personnel", "both"):   # enforce BHW scope
                announcements_all.append(a)
    except Exception as e:
        messages.error(request, f"Failed loading announcements list: {e}")
        announcements_all = []

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
            "audience": ann_aud or "",
            "from": ann_from_str,
            "to": ann_to_str,
        },
        "ann_open": request.GET.get('ann_open') == '1',
    }
    return render(request, "captain_module/captain_dashboard.html", ctx)


@custom_login_required
@role_required('Barangay Captain')
def captain_viewResident(request):
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
    return render(request, 'captain_module/captain_viewResident.html', context)


@custom_login_required
@role_required('Barangay Captain')
@require_GET
def resident_detail_json(request, resident_id: int):
    """
    AJAX endpoint returning JSON for one resident (for the View modal).
    Mirrors secretary_module.resident_detail_json but made available to Captain.
    """
    import traceback
    try:
        quarter_id = request.GET.get('quarter_id') or None
        if quarter_id and str(quarter_id).isdigit():
            quarter_id = int(quarter_id)
        else:
            quarter_id = None

        resident = ResidentList.sp_get_specific_resident(resident_id, quarter_id)
        if not resident:
            return JsonResponse({"ok": False, "message": "Resident not found."}, status=404)

        # Normalize date to string
        if resident.get('dob') is not None:
            resident['dob'] = str(resident['dob'])

        # Ensure businesses JSON is parsed
        if resident.get('businesses') and isinstance(resident['businesses'], str):
            try:
                resident['businesses'] = json.loads(resident['businesses'])
            except Exception:
                resident['businesses'] = []

        return JsonResponse({"ok": True, "resident": resident}, status=200)
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"[ERROR] resident_detail_json: {error_detail}")
        return JsonResponse({"ok": False, "message": str(e)}, status=500)


@custom_login_required
@role_required('Barangay Captain')
def captain_householdList(request):
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
    
    flash = get_flash(request)
    return render(request, 'captain_module/captain_householdList.html',{
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
@role_required('Barangay Captain')
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
@role_required('Barangay Captain')
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
@role_required('Barangay Captain')
def captain_householdView(request):
    
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
    return render(request, 'captain_module/captain_moreHousehold.html', {
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

@custom_login_required
@role_required("Barangay Captain")
def captain_businessList(request):
    q = (request.GET.get("q") or "").strip() or None
    status = request.GET.get("status") or None  # you can keep this for future filters
    page = max(int(request.GET.get("page", 1)), 1)
    page_size = max(min(int(request.GET.get("page_size", 10)), 100), 1)

    result = BusinessList.search(
        p_query=q,
        p_status=status,
        page=page,
        page_size=page_size,
    )

    page = result["page"]
    pages = result["pages"]
    total = result["total"]

    # For "Showing X–Y of Z"
    showing_start = (result["offset"] + 1) if total > 0 else 0
    showing_end = min(result["offset"] + len(result["rows"]), total)

    # Pagination URLs
    base_params = {
        "q": q or "",
        "status": status or "",
        "page_size": page_size,
    }

    def page_url(p):
        params = base_params.copy()
        params["page"] = p
        return f"?{urlencode(params)}"

    prev_url = page_url(page - 1) if page > 1 else None
    next_url = page_url(page + 1) if page < pages else None

    context = {
        "rows": result["rows"],
        "q": q or "",
        "status": status or "",
        "total": total,
        "page": page,
        "pages": pages,
        "page_size": page_size,
        "showing_start": showing_start,
        "showing_end": showing_end,
        "prev_url": prev_url,
        "next_url": next_url,
    }
    return render(request, "captain_module/captain_businessList.html", context)

@custom_login_required
@role_required('Barangay Captain')
def captain_moreBusinessInfo(request):
    return render(request, 'captain_module/captain_moreBusinessInfo.html')

@custom_login_required
@role_required('Barangay Captain')
def personnelRequest(request):
    flash = get_flash(request) 
    
    limit = None
    offset = None
    sort_by = ''
    sort_dir = ''
    results = []
    
    query = (request.GET.get('query') or '').strip()
    filter_status = request.GET.get('filter_status')
    
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
        sort_by = None
    if sort_dir not in VALID_SORT_DIR:
        sort_dir = "desc"
        
    offset = (page - 1) * limit
    
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
    
    try:
        results = Captain.sp_get_pending_personnel_requests(
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

    final_result = [
        r for r in final_result
        if not filter_status or (r.get('role_name') or '').strip().casefold() == filter_status.casefold()
    ]
    
    base_params = _clean_params({
        "limit": limit,
        "sort_by": sort_by,
        "sort_dir": sort_dir,
        "query": query,    
        "filter_status": filter_status,
    })

    prev_url = "?" + urlencode({**base_params, "page": page - 1}) if has_prev else ""
    next_url = "?" + urlencode({**base_params, "page": page + 1}) if has_next else ""
    
        # limit pills reset page to 1
    limit_urls = {n: "?" + urlencode({**base_params, "limit": n, "page": 1}) for n in LIMIT_OPTIONS}
    
    ROLE_LABELS = [
        "Barangay Captain",
        "Barangay Secretary",
        "Barangay Assistant Secretary",
        "Barangay Treasurer",
        "Barangay Health Worker",
        "Midwife",
    ]

    return render(request, 'captain_module/personnelRequest.html', {
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
        'filter_status': filter_status,
        'message': flash['message'],
        'message_level': flash['message_level'],
        'role_labels': ROLE_LABELS,
    })