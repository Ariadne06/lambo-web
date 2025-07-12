from rest_framework import viewsets, generics, status
from .serializers import ResidentSerializer, SitioSerializer, CivilStatusSerializer, EducationalAttainmentSerializer, ReligionSerializer, ResidentStatusSerializer, ReligionCategorySerializer, ResidentRegistrationSerializer, AddressSerializer
from resident_profiling_module.models import Resident, Sitio, CivilStatus, EducationalAttainment, Religion, ResidentStatus, ReligionCategory, Address

class ResidentViewSet(viewsets.ModelViewSet):
    queryset = Resident.objects.all()
    serializer_class = ResidentSerializer

class CivilStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CivilStatus.objects.all()
    serializer_class = CivilStatusSerializer

class EducationalAttainmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EducationalAttainment.objects.all()
    serializer_class = EducationalAttainmentSerializer

class SitioViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Sitio.objects.all()
    serializer_class = SitioSerializer

class ReligionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Religion.objects.all()
    serializer_class = ReligionSerializer

class ResidentStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ResidentStatus.objects.all()
    serializer_class = ResidentStatusSerializer

class ReligionCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ReligionCategory.objects.all()
    serializer_class = ReligionCategorySerializer

class ResidentRegistrationView(generics.CreateAPIView):
    queryset = Resident.objects.all()
    serializer_class = ResidentRegistrationSerializer

