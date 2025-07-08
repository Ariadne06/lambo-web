from django.shortcuts import render

# Create your views here.

def captain_dashboard(request):
    return render(request, 'captain_module/captain_dashboard.html')