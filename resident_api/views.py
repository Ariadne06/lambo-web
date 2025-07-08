from django.shortcuts import render
from rest_framework import viewsets
from .serializers import ResidentSerializer
from resident_profiling_module.models import Resident

# Create your views here.

class ResidentViewSet(viewsets.ModelViewSet):
    queryset = Resident.objects.all()
    serializer_class = ResidentSerializer
