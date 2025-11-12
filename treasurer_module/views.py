from django.shortcuts import render, redirect
from authentication.decorators import custom_login_required, role_required
from django.http import JsonResponse, Http404
from django.contrib import messages
from math import ceil
from .models import TreasurerRepo
from utils.db_message import _clean_db_error
from django.views.decorators.http import require_http_methods, require_POST

# Create your views here.
@custom_login_required
@role_required('Barangay Treasurer')
def treasurer_dashboard(request):
    return render(request, 'treasurer_module/treasurer_dashboard.html')

@custom_login_required
@role_required('Barangay Treasurer')
def payments(request):
    """List all non-Pending applications (treasurer scope) with search, filters, and elided pagination."""
    q = (request.GET.get('q') or '').strip() or None
    # Multi-select filters similar to secretary: payment_status, request_label
    payment_status_list = [s.strip() for s in request.GET.getlist('payment_status') if s and s.strip()]
    request_label_list = [r.strip() for r in request.GET.getlist('request_label') if r and r.strip()]

    # Page & per_page
    try:
        page = max(int(request.GET.get('page', 1)), 1)
    except Exception:
        page = 1
    try:
        per_page = max(min(int(request.GET.get('per_page', 25)), 100), 1)
    except Exception:
        per_page = 25
    offset = (page - 1) * per_page

    # Fetch rows (optimize single filter case via direct DB filtering)
    try:
        if len(payment_status_list) <= 1 and len(request_label_list) <= 1:
            ps_single = payment_status_list[0] if payment_status_list else None
            rq_single = request_label_list[0] if request_label_list else None
            rows = TreasurerRepo.list_all(q, ps_single, rq_single, per_page, offset)
            total = TreasurerRepo.count_all(q, ps_single, rq_single)
        else:
            statuses = payment_status_list or [None]
            requests = request_label_list or [None]
            combos = [(s, r) for s in statuses for r in requests]
            # Count total across combinations
            total = 0
            per_combo_counts = {}
            for s, r in combos:
                c = TreasurerRepo.count_all(q, s, r)
                per_combo_counts[(s, r)] = c
                total += c
            # Fetch needed slice from each combo up to page*per_page
            end_idx = page * per_page
            merged = {}
            for s, r in combos:
                need = min(per_combo_counts[(s, r)], end_idx)
                if need <= 0:
                    continue
                subset = TreasurerRepo.list_all(q, s, r, need, 0)
                for row in subset:
                    merged[row['application_id']] = row
            merged_rows = list(merged.values())
            try:
                merged_rows.sort(key=lambda x: (x.get('date_submitted'), x.get('application_id')), reverse=True)
            except Exception:
                merged_rows.sort(key=lambda x: str(x.get('date_submitted')) + '-' + str(x.get('application_id')), reverse=True)
            start_idx = (page - 1) * per_page
            rows = merged_rows[start_idx:end_idx]
    except Exception as e:
        messages.error(request, f"Failed to load payments: {_clean_db_error(e)}")
        rows, total = [], 0

    # Pagination metadata
    total_pages = max(ceil((total or 0) / per_page), 1)

    # Build querystring builder preserving multi-select filters
    from urllib.parse import urlencode as _urlencode
    def _qs(base: dict, statuses: list[str], reqs: list[str]) -> str:
        params = []
        for k, v in base.items():
            if v is not None and v != '':
                params.append((k, v))
        for s in statuses:
            params.append(('payment_status', s))
        for r in reqs:
            params.append(('request_label', r))
        return _urlencode(params, doseq=True)

    prev_url = next_url = ''
    if page > 1:
        prev_url = '?' + _qs({'q': q or '', 'page': page - 1, 'per_page': per_page}, payment_status_list, request_label_list)
    if page < total_pages:
        next_url = '?' + _qs({'q': q or '', 'page': page + 1, 'per_page': per_page}, payment_status_list, request_label_list)

    # Elided page range via dummy paginator
    from django.core.paginator import Paginator
    paginator = Paginator(range(total), per_page)
    page_obj = paginator.get_page(page)
    page = page_obj.number
    total_pages = paginator.num_pages
    page_numbers = list(paginator.get_elided_page_range(number=page, on_each_side=1, on_ends=1))
    page_urls = {}
    for pn in page_numbers:
        if isinstance(pn, int):
            page_urls[pn] = '?' + _qs({'q': q or '', 'page': pn, 'per_page': per_page}, payment_status_list, request_label_list)
    page_items = []
    for item in page_numbers:
        if isinstance(item, int):
            page_items.append({'num': item, 'url': page_urls.get(item, ''), 'current': item == page})
        else:
            page_items.append({'ellipsis': True})
    has_prev = page_obj.has_previous()
    has_next = page_obj.has_next()
    prev_url = '?' + _qs({'q': q or '', 'page': page - 1, 'per_page': per_page}, payment_status_list, request_label_list) if has_prev else ''
    next_url = '?' + _qs({'q': q or '', 'page': page + 1, 'per_page': per_page}, payment_status_list, request_label_list) if has_next else ''

    # Chips removal links
    def _remove(kind: str, val: str) -> str:
        ps = list(payment_status_list)
        rq = list(request_label_list)
        if kind == 'status' and val in ps:
            ps.remove(val)
        if kind == 'request' and val in rq:
            rq.remove(val)
        return '?' + _qs({'q': q or '', 'page': 1, 'per_page': per_page}, ps, rq)

    status_chips = [{'label': s, 'url': _remove('status', s)} for s in payment_status_list]
    request_chips = [{'label': r, 'url': _remove('request', r)} for r in request_label_list]
    clear_all_url = '?' + _qs({'q': q or '', 'page': 1, 'per_page': per_page}, [], [])

    ctx = {
        'rows': rows,
        'q': q or '',
        'payment_status': payment_status_list[0] if len(payment_status_list) == 1 else '',
        'request_label': request_label_list[0] if len(request_label_list) == 1 else '',
        'payment_status_list': payment_status_list,
        'request_label_list': request_label_list,
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages,
        'has_prev': has_prev,
        'has_next': has_next,
        'prev_url': prev_url,
        'next_url': next_url,
        'page_items': page_items,
        'status_chips': status_chips,
        'request_chips': request_chips,
        'clear_all_url': clear_all_url,
        # Option lists inspired by secretary view
    # Function treasurer_get_all_application now yields 'Pending' (for payment) and 'Paid'
    'payment_status_options': ['Pending','Paid'],
        'request_label_options': ['Business Clearance','Business Closure','Business Clearance (Reprint)','Barangay Clearance'],
    }
    return render(request, 'treasurer_module/payments.html', ctx)

@custom_login_required
@role_required('Barangay Treasurer')
def treasurer_application_detail(request, application_id: int):
    """Server-rendered detail page for treasurer (replaces modal)."""
    try:
        row = TreasurerRepo.get_one(application_id)
        if not row:
            raise Http404('Application not found')
    except Http404:
        raise
    except Exception as e:
        messages.error(request, _clean_db_error(e))
        return redirect('treasurer_module:payments')

    # Normalize breakdown details similar to secretary implementation
    import json
    details_json = row.get('total_amount_details')
    if isinstance(details_json, str):
        try:
            details_json = json.loads(details_json)
        except Exception:
            details_json = None

    breakdown_items = []
    breakdown_total = None
    purpose_value = None

    def _to_float(x):
        try:
            from decimal import Decimal as D
            return float(x) if isinstance(x, (int, float, D)) else x
        except Exception:
            return x

    if isinstance(details_json, dict):
        items = details_json.get('items')
        breakdown_total = _to_float(details_json.get('total'))
        try:
            purpose_value = details_json.get('purpose') or purpose_value
        except Exception:
            purpose_value = purpose_value
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict):
                    breakdown_items.append({
                        'label': it.get('item') or it.get('label') or it.get('name') or 'Item',
                        'amount': _to_float(it.get('amount') or it.get('total') or it.get('price') or 0),
                        'qty': it.get('qty'),
                        'rate': _to_float(it.get('rate')) if it.get('rate') is not None else None,
                        'rate_percent': _to_float(it.get('rate_percent')) if it.get('rate_percent') is not None else None,
                        'extra_units': it.get('extra_units'),
                        'total_units': it.get('total_units'),
                        'minimum_units': it.get('minimum_units'),
                    })
        else:
            for k, v in details_json.items():
                if k == 'total':
                    continue
                if isinstance(v, (int, float)):
                    breakdown_items.append({'label': k, 'amount': _to_float(v)})
                elif isinstance(v, dict) and 'amount' in v:
                    breakdown_items.append({'label': k, 'amount': _to_float(v.get('amount'))})
    elif isinstance(details_json, list):
        for it in details_json:
            if isinstance(it, dict):
                breakdown_items.append({
                    'label': it.get('item') or it.get('label') or it.get('name') or 'Item',
                    'amount': _to_float(it.get('amount') or it.get('total') or it.get('price') or 0),
                    'qty': it.get('qty'),
                    'rate': _to_float(it.get('rate')) if it.get('rate') is not None else None,
                    'rate_percent': _to_float(it.get('rate_percent')) if it.get('rate_percent') is not None else None,
                    'extra_units': it.get('extra_units'),
                    'total_units': it.get('total_units'),
                    'minimum_units': it.get('minimum_units'),
                })

    # Surface purpose for templates if not already present on row
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
    return render(request, 'treasurer_module/treasurer_application_detail.html', ctx)

@custom_login_required
@role_required('Barangay Treasurer')
def transactions(request):
    return render(request, 'treasurer_module/transactions.html')

@custom_login_required
@role_required('Barangay Treasurer')
def summary(request):
    return render(request, 'treasurer_module/summary.html')


# --- API endpoints for details and payment action ---
@custom_login_required
@role_required('Barangay Treasurer')
def treasurer_application_detail_json(request, application_id: int):
    try:
        row = TreasurerRepo.get_one(application_id)
        if not row:
            raise Http404('Application not found')
        from datetime import date, datetime
        from decimal import Decimal as D
        def deep_ser(v):
            if isinstance(v, D):
                return float(v)
            if isinstance(v, (date, datetime)):
                return v.isoformat()
            if isinstance(v, dict):
                return {k: deep_ser(x) for k, x in v.items()}
            if isinstance(v, (list, tuple)):
                return [deep_ser(x) for x in v]
            return v
        return JsonResponse({k: deep_ser(v) for k, v in row.items()})
    except Http404:
        raise
    except Exception as e:
        return JsonResponse({'ok': False, 'message': _clean_db_error(e)}, status=400)


@custom_login_required
@role_required('Barangay Treasurer')
@require_POST
def set_application_to_paid(request, application_id: int):
    or_number = (request.POST.get('or_number') or '').strip()
    if not or_number:
        messages.error(request, 'OR Number is required.')
        return redirect('treasurer_module:treasurer_application_detail', application_id=application_id)
    try:
        # Acting treasurer personnel id
        personnel_id = (
            getattr(getattr(request, 'user', None), 'personnel_id', None)
            or request.session.get('personnel_id')
            or 1
        )
        TreasurerRepo.set_paid(application_id, or_number, personnel_id)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'message': 'Marked as Paid.'})
        messages.success(request, 'Application marked as Paid and Approved.')
        return redirect('treasurer_module:payments')
    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'message': _clean_db_error(e)}, status=400)
        messages.error(request, _clean_db_error(e))
        return redirect('treasurer_module:treasurer_application_detail', application_id=application_id)