from django.shortcuts import render
from authentication.decorators import custom_login_required, role_required

# Create your views here.
@custom_login_required
@role_required('Barangay Treasurer')
def treasurer_dashboard(request):
    return render(request, 'treasurer_module/treasurer_dashboard.html')

@custom_login_required
@role_required('Barangay Treasurer')
def payments(request):
    return render(request, 'treasurer_module/payments.html')

@custom_login_required
@role_required('Barangay Treasurer')
def transactions(request):
    return render(request, 'treasurer_module/transactions.html')

@custom_login_required
@role_required('Barangay Treasurer')
def summary(request):
    return render(request, 'treasurer_module/summary.html')