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
    """List all non-Pending applications for Treasurer using treasurer_get_all_application."""
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
        rows = TreasurerRepo.list_all(q, per_page, offset)
        total = TreasurerRepo.count_all(q)
    except Exception as e:
        messages.error(request, f"Failed to load payments: {_clean_db_error(e)}")
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
    return render(request, 'treasurer_module/payments.html', ctx)

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
        def ser(v):
            if isinstance(v, D): return float(v)
            if isinstance(v, (date, datetime)): return v.isoformat()
            return v
        return JsonResponse({k: ser(v) for k, v in row.items()})
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
        return redirect('treasurer_module:payments')
    try:
        TreasurerRepo.set_paid(application_id, or_number)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'message': 'Marked as Paid.'})
        messages.success(request, 'Application marked as Paid and Approved.')
        return redirect('treasurer_module:payments')
    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'message': _clean_db_error(e)}, status=400)
        messages.error(request, _clean_db_error(e))
        return redirect('treasurer_module:payments')