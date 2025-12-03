from django.shortcuts import render, redirect
from authentication.decorators import custom_login_required, role_required
from django.http import JsonResponse, Http404
from django.contrib import messages
from math import ceil
from .models import TreasurerRepo, AnnouncementRepo
from utils.db_message import _clean_db_error
from django.views.decorators.http import require_http_methods, require_POST
from django.db import connection
from notifications.service import NotificationService
import logging

logger = logging.getLogger(__name__)

# Create your views here.
@custom_login_required
@role_required('Barangay Treasurer')
def treasurer_dashboard(request):
    # Year filter: default to the latest year available or current year if none
    try:
        year_choices = TreasurerRepo.get_year_for_filter_choice() or []
    except Exception:
        year_choices = []

    import datetime
    curr_year = datetime.date.today().year
    raw_year = request.GET.get('year')
    try:
        sel_year = int(raw_year) if raw_year else (year_choices[-1] if year_choices else curr_year)
    except (TypeError, ValueError):
        sel_year = year_choices[-1] if year_choices else curr_year

    # Monthly collections for the selected year
    months = []
    try:
        months = TreasurerRepo.get_all_months_collections(sel_year)
    except Exception:
        months = []
    months_labels = [str((m.get('month_name') or '').strip()) for m in months]
    months_values = []
    for m in months:
        val = m.get('total_collected')
        try:
            months_values.append(float(val) if val is not None else 0.0)
        except Exception:
            months_values.append(0.0)

    # KPIs
    try:
        kpi_total_today = TreasurerRepo.get_total_collections_today()
    except Exception:
        kpi_total_today = 0.0
    try:
        kpi_or_today = TreasurerRepo.get_total_or_issued_today()
    except Exception:
        kpi_or_today = 0
    try:
        kpi_pending = TreasurerRepo.get_pending_payments()
    except Exception:
        kpi_pending = 0

    # Recent transactions (top 5)
    try:
        recent = TreasurerRepo.get_recent_transactions()
    except Exception:
        recent = []

    # Recent announcements for personnel
    try:
        latest_announcements = AnnouncementRepo.latest_for_personnel(limit=3)
    except Exception:
        latest_announcements = []

    ctx = {
        'year_choices': year_choices,
        'selected_year': sel_year,
        'months_labels': months_labels,
        'months_values': months_values,
        'kpi_total_today': kpi_total_today,
        'kpi_or_today': kpi_or_today,
        'kpi_pending': kpi_pending,
        'recent': recent,
        'latest_announcements': latest_announcements,
    }
    return render(request, 'treasurer_module/treasurer_dashboard.html', ctx)

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
def summary(request):
    """Reports: monthly summary by application type using treasurer_get_monthly_summary.

    Filters mimic Payments: search `q`, multi-select `application_label`, plus month and year.
    We filter application_label and month in Python over the aggregated result set.
    """
    from django.core.paginator import Paginator
    from urllib.parse import urlencode as _urlencode

    q = (request.GET.get('q') or '').strip() or None
    # Year (single select). Default to latest year with data or current year
    try:
        year_choices = TreasurerRepo.get_year_for_filter_choice() or []
    except Exception:
        year_choices = []
    import datetime
    curr_year = datetime.date.today().year
    raw_year = request.GET.get('year')
    try:
        sel_year = int(raw_year) if raw_year else (year_choices[-1] if year_choices else curr_year)
    except (TypeError, ValueError):
        sel_year = year_choices[-1] if year_choices else curr_year

    # Application labels (multi-select)
    app_labels = [s.strip() for s in request.GET.getlist('application_label') if s and s.strip()]
    # Month (single select; 1-12). Optional
    try:
        month = int(request.GET.get('month')) if request.GET.get('month') else None
        if month is not None and (month < 1 or month > 12):
            month = None
    except Exception:
        month = None

    # Fetch summary rows from DB (already aggregated)
    try:
        rows_all = TreasurerRepo.get_monthly_summary(sel_year, q)
    except Exception as e:
        messages.error(request, f"Failed to load summary: {_clean_db_error(e)}")
        rows_all = []

    # Build options from data
    try:
        application_label_options = TreasurerRepo.get_distinct_application_labels(sel_year)
    except Exception:
        # Fallback to gathered set
        application_label_options = sorted({(r.get('application_label') or '').strip() for r in rows_all if (r.get('application_label') or '').strip()})

    # Month options present in the dataset (1..12 with names)
    month_map = {}
    for r in rows_all:
        try:
            mon_no = int(r.get('month_no'))
            mon_name = str((r.get('month_name') or '').strip())
            if mon_no and mon_name and mon_no not in month_map:
                month_map[mon_no] = mon_name
        except Exception:
            continue
    month_options = sorted(month_map.items(), key=lambda x: x[0])  # list[(no, name)]

    # Apply Python-side filters for application_label and month
    def _match(r):
        if app_labels and (r.get('application_label') or '') not in app_labels:
            return False
        if month is not None and int(r.get('month_no') or 0) != month:
            return False
        return True

    rows_filtered = [r for r in rows_all if _match(r)]

    # Pagination
    try:
        page = max(int(request.GET.get('page', 1)), 1)
    except Exception:
        page = 1
    try:
        per_page = max(min(int(request.GET.get('per_page', 25)), 100), 1)
    except Exception:
        per_page = 25
    paginator = Paginator(rows_filtered, per_page)
    page_obj = paginator.get_page(page)
    page = page_obj.number
    total_pages = paginator.num_pages

    # Build URLs that preserve multi-select filters
    def _qs(base: dict, labels: list[str]) -> str:
        params = []
        for k, v in base.items():
            if v is not None and v != '':
                params.append((k, v))
        for s in labels:
            params.append(('application_label', s))
        return _urlencode(params, doseq=True)

    page_numbers = list(paginator.get_elided_page_range(number=page, on_each_side=1, on_ends=1))
    page_urls = {}
    for pn in page_numbers:
        if isinstance(pn, int):
            page_urls[pn] = '?' + _qs({'q': q or '', 'year': sel_year, 'month': month or '', 'page': pn, 'per_page': per_page}, app_labels)
    page_items = []
    for item in page_numbers:
        if isinstance(item, int):
            page_items.append({'num': item, 'url': page_urls.get(item, ''), 'current': item == page})
        else:
            page_items.append({'ellipsis': True})
    has_prev = page_obj.has_previous()
    has_next = page_obj.has_next()
    prev_url = '?' + _qs({'q': q or '', 'year': sel_year, 'month': month or '', 'page': page - 1, 'per_page': per_page}, app_labels) if has_prev else ''
    next_url = '?' + _qs({'q': q or '', 'year': sel_year, 'month': month or '', 'page': page + 1, 'per_page': per_page}, app_labels) if has_next else ''

    # Chips
    def _remove_label(val: str) -> str:
        lst = list(app_labels)
        if val in lst:
            lst.remove(val)
        return '?' + _qs({'q': q or '', 'year': sel_year, 'month': month or '', 'page': 1, 'per_page': per_page}, lst)

    label_chips = [{'label': s, 'url': _remove_label(s)} for s in app_labels]
    clear_all_url = '?' + _qs({'q': q or '', 'year': sel_year, 'month': month or '', 'page': 1, 'per_page': per_page}, [])

    # Totals for current filtered set
    from decimal import Decimal as D
    total_apps = 0
    total_collected = D('0')
    for r in rows_filtered:
        try:
            total_apps += int(r.get('applications_count') or 0)
        except Exception:
            pass
        try:
            total_collected += (r.get('total_collected') or D('0'))
        except Exception:
            try:
                total_collected += D(str(r.get('total_collected') or '0'))
            except Exception:
                pass

    ctx = {
        'q': q or '',
        'year_choices': year_choices,
        'selected_year': sel_year,
        'application_label_options': application_label_options,
        'application_label_list': app_labels,
        'month_options': month_options,  # list of (no, name)
        'selected_month': month or '',
        'rows': list(page_obj.object_list),
        'page': page,
        'per_page': per_page,
        'total': len(rows_filtered),
        'total_pages': total_pages,
        'has_prev': has_prev,
        'has_next': has_next,
        'prev_url': prev_url,
        'next_url': next_url,
        'page_items': page_items,
        'label_chips': label_chips,
        'clear_all_url': clear_all_url,
        'sum_applications': total_apps,
        'sum_collected': total_collected,
    }
    return render(request, 'treasurer_module/summary.html', ctx)


@custom_login_required
@role_required('Barangay Treasurer')
def summary_pdf(request):
    """Generate PDF for treasurer summary report with applied filters."""
    from django.http import HttpResponse
    from reports_module.pdf_templates.treasurer.summary_report import generate_summary_report_pdf
    
    q = (request.GET.get('q') or '').strip() or None
    
    # Year (single select)
    try:
        year_choices = TreasurerRepo.get_year_for_filter_choice() or []
    except Exception:
        year_choices = []
    import datetime
    curr_year = datetime.date.today().year
    raw_year = request.GET.get('year')
    try:
        sel_year = int(raw_year) if raw_year else (year_choices[-1] if year_choices else curr_year)
    except (TypeError, ValueError):
        sel_year = year_choices[-1] if year_choices else curr_year
    
    # Application labels (multi-select)
    app_labels = [s.strip() for s in request.GET.getlist('application_label') if s and s.strip()]
    
    # Month (single select; 1-12)
    try:
        month = int(request.GET.get('month')) if request.GET.get('month') else None
        if month is not None and (month < 1 or month > 12):
            month = None
    except Exception:
        month = None
    
    # Fetch all summary rows from DB
    try:
        rows_all = TreasurerRepo.get_monthly_summary(sel_year, q)
    except Exception as e:
        rows_all = []
    
    # Apply Python-side filters for application_label and month
    def _match(r):
        if app_labels and (r.get('application_label') or '') not in app_labels:
            return False
        if month is not None and int(r.get('month_no') or 0) != month:
            return False
        return True
    
    rows_filtered = [r for r in rows_all if _match(r)]
    
    # Get month name if month filter is applied
    month_name = None
    if month:
        month_map = {
            1: 'January', 2: 'February', 3: 'March', 4: 'April',
            5: 'May', 6: 'June', 7: 'July', 8: 'August',
            9: 'September', 10: 'October', 11: 'November', 12: 'December'
        }
        month_name = month_map.get(month)
    
    # Build filters dictionary for PDF
    filters_applied = {
        'year': sel_year,
        'month': month,
        'month_name': month_name,
        'application_labels': app_labels,
        'search_query': q
    }
    
    # Generate PDF
    try:
        pdf_buffer = generate_summary_report_pdf(rows_filtered, filters_applied)
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        
        # Build filename based on filters
        filename_parts = ['Summary_Report', str(sel_year)]
        if month_name:
            filename_parts.append(month_name)
        filename = '_'.join(filename_parts) + '.pdf'
        
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
    except Exception as e:
        messages.error(request, f"Failed to generate PDF: {_clean_db_error(e)}")
        return redirect('treasurer_module:summary')


@custom_login_required
@role_required('Barangay Treasurer')
def financial_report_pdf(request):
    """Generate PDF for treasurer financial report with applied filters."""
    from django.http import HttpResponse
    from reports_module.pdf_templates.treasurer.financial_report import generate_financial_report_pdf
    
    # Get filter parameters
    raw_year = request.GET.get('year')
    raw_month = request.GET.get('month')
    start_date = request.GET.get('start_date') or None
    end_date = request.GET.get('end_date') or None
    
    # Parse year
    year = None
    if raw_year:
        try:
            year = int(raw_year)
        except (TypeError, ValueError):
            pass
    
    # Parse month
    month = None
    month_name = None
    if raw_month:
        try:
            month = int(raw_month)
            if month < 1 or month > 12:
                month = None
            else:
                month_map = {
                    1: 'January', 2: 'February', 3: 'March', 4: 'April',
                    5: 'May', 6: 'June', 7: 'July', 8: 'August',
                    9: 'September', 10: 'October', 11: 'November', 12: 'December'
                }
                month_name = month_map.get(month)
        except (TypeError, ValueError):
            pass
    
    # Fetch financial report data
    try:
        financial_data = TreasurerRepo.get_financial_report(
            year=year,
            month=month,
            start_date=start_date,
            end_date=end_date,
            limit=10000,
            offset=0
        )
    except Exception as e:
        messages.error(request, f"Failed to fetch financial data: {_clean_db_error(e)}")
        return redirect('treasurer_module:summary')
    
    # Build filters dictionary for PDF
    filters_applied = {
        'year': year,
        'month': month,
        'month_name': month_name,
        'start_date': start_date,
        'end_date': end_date
    }
    
    # Generate PDF
    try:
        pdf_buffer = generate_financial_report_pdf(financial_data, filters_applied)
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        
        # Build filename based on filters
        filename_parts = ['Financial_Report']
        if year:
            filename_parts.append(str(year))
        if month_name:
            filename_parts.append(month_name)
        if start_date and end_date:
            filename_parts.append(f"{start_date}_to_{end_date}")
        filename = '_'.join(filename_parts) + '.pdf'
        
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
    except Exception as e:
        messages.error(request, f"Failed to generate PDF: {_clean_db_error(e)}")
        return redirect('treasurer_module:summary')


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
        
        # Send notification to resident
        try:
            # Get application details to check if it's from a resident
            app_data = TreasurerRepo.get_one(application_id)
            resident_id = None
            
            if app_data:
                # Priority 1: Extract applicant_id from total_amount_details JSON
                details_json = app_data.get('total_amount_details')
                if details_json:
                    try:
                        import json
                        if isinstance(details_json, str):
                            details_json = json.loads(details_json)
                        if isinstance(details_json, dict) and details_json.get('applicant_id'):
                            resident_id = details_json['applicant_id']
                            logger.info(f"Payment - Application {application_id}: Found applicant_id={resident_id} in total_amount_details")
                    except Exception as e:
                        logger.error(f"Payment - Application {application_id}: Error parsing total_amount_details: {e}")
                
                # Priority 2: For business applications, get the business owner
                if not resident_id and app_data.get('business_id'):
                    try:
                        from secretary_module.models import Business
                        business_data = Business.sp_get_business_detail(app_data['business_id'])
                        if business_data and business_data.get('owner_id'):
                            resident_id = business_data['owner_id']
                            logger.info(f"Payment - Application {application_id}: Found owner_id={resident_id} from business")
                    except Exception as e:
                        logger.error(f"Failed to get business owner for business_id {app_data['business_id']}: {e}")
                
                # Priority 3: Fall back to requested_by_id (for resident-initiated applications)
                if not resident_id and app_data.get('requested_by') == 'resident' and app_data.get('requested_by_id'):
                    resident_id = app_data['requested_by_id']
                    logger.info(f"Payment - Application {application_id}: Using requested_by_id={resident_id}")
            
            if resident_id:
                certificate_type = app_data.get('request', 'Certificate')
                application_code = app_data.get('application_code', '')
                
                # Send notification
                NotificationService.send_to_resident(
                    resident_id=resident_id,
                    title="Payment Confirmed",
                    body=f"Your payment for {certificate_type} ({application_code}) has been confirmed. You can now proceed to the secretary for printing.",
                    deep_link=f"/(tabs)/documents/{application_id}"
                )
                logger.info(f"Payment confirmation notification sent to resident_id {resident_id} for application {application_id}")
        except Exception as notif_error:
            # Log but don't fail the main operation
            logger.error(f"Failed to send payment notification for application {application_id}: {notif_error}")
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'message': 'Marked as Paid.'})
        messages.success(request, 'Application marked as Paid and Approved.')
        return redirect('treasurer_module:payments')
    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'message': _clean_db_error(e)}, status=400)
        messages.error(request, _clean_db_error(e))
        return redirect('treasurer_module:treasurer_application_detail', application_id=application_id)

@custom_login_required
@role_required('Barangay Treasurer')
def announcement_detail(request, announcement_id: int):
    """View specific announcement details"""
    try:
        announcement = AnnouncementRepo.get_one(announcement_id)
        if not announcement:
            raise Http404('Announcement not found')
        
        return render(request, 'treasurer_module/announcement_detail.html', {
            'announcement': announcement
        })
    except Http404:
        raise
    except Exception as e:
        messages.error(request, f"Failed to load announcement: {str(e)}")
        return redirect('treasurer_module:treasurer_dashboard')