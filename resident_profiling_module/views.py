from django.shortcuts import render

# Create your views here.

def resident_profiling(request):
    return render(request, 'resident_profiling_module/resident_profiling.html')
