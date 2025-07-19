from django.shortcuts import render

# Create your views here.

def captain_dashboard(request):
    return render(request, 'captain_module/captain_dashboard.html')

def captain_viewMoreResident(request):
    return render(request, 'captain_module/captain_viewMoreResident.html')

def captain_viewResident(request):
    return render(request, 'captain_module/captain_viewResident.html')

def captain_householdList(request):
    return render(request, 'captain_module/captain_householdList.html')

def captain_moreHousehold(request):
    return render(request, 'captain_module/captain_moreHousehold.html')

def captain_businessList(request):
    return render(request, 'captain_module/captain_businessList.html')

def captain_moreBusinessInfo(request):
    return render(request, 'captain_module/captain_moreBusinessInfo.html')