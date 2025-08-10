from django.shortcuts import render

# Create your views here.
def treasurer_dashboard(request):
    return render(request, 'treasurer_module/treasurer_dashboard.html')

def payments(request):
    return render(request, 'treasurer_module/payments.html')

def transactions(request):
    return render(request, 'treasurer_module/transactions.html')

def summary(request):
    return render(request, 'treasurer_module/summary.html')