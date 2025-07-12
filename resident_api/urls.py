from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (ResidentViewSet, CivilStatusViewSet, EducationalAttainmentViewSet, SitioViewSet, ReligionViewSet, ResidentStatusViewSet, ReligionCategoryViewSet, ResidentRegistrationView)

router = DefaultRouter()
router.register(r'residents', ResidentViewSet)
router.register(r'civil-statuses', CivilStatusViewSet)
router.register(r'educational-attainments', EducationalAttainmentViewSet)
router.register(r'sitios', SitioViewSet)
router.register(r'religions', ReligionViewSet)
router.register(r'resident-statuses', ResidentStatusViewSet)
router.register(r'religion-categories', ReligionCategoryViewSet)

urlpatterns = router.urls

urlpatterns += [
    path('register/', ResidentRegistrationView.as_view(), name='resident-register'),
]