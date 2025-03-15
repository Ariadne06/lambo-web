from django.shortcuts import render

# Create your views here.

def personnels(request):
    return render(request, 'personnels_module/personnels.html')
