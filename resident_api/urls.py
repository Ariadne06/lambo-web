from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (ResidentViewSet, CivilStatusViewSet, EducationalAttainmentViewSet, SitioViewSet, ReligionViewSet, ResidentStatusViewSet, ReligionCategoryViewSet, ResidentRegistrationView, ResidentIdDocumentOCRView, UpdateResidentProfileView, VerifyIdFieldsView, IdentityDocTypeViewSet, VerifyGuardianView, VerifyGuardianIdFieldsView, MobileLoginView, ResidentProfileView)

router = DefaultRouter()
router.register(r'residents', ResidentViewSet)
router.register(r'civil-statuses', CivilStatusViewSet)
router.register(r'educational-attainments', EducationalAttainmentViewSet)
router.register(r'sitios', SitioViewSet)
router.register(r'religions', ReligionViewSet)
router.register(r'resident-statuses', ResidentStatusViewSet)
router.register(r'religion-categories', ReligionCategoryViewSet)
router.register(r'identity-doc-types', IdentityDocTypeViewSet)

urlpatterns = router.urls

urlpatterns += [
    path('verify-id-fields/', VerifyIdFieldsView.as_view(), name='verify-id-fields'),
    path('register/', ResidentRegistrationView.as_view(), name='resident-register'),
    # path('id-document/upload/', ResidentIdDocumentUploadView.as_view(), name='id-document-upload'),
    path('id-document/<int:pk>/ocr/', ResidentIdDocumentOCRView.as_view(), name='id-document-ocr'),
    path('verify-guardian/', VerifyGuardianView.as_view(), name='verify-guardian'),
    path('verify-guardian-id-fields/', VerifyGuardianIdFieldsView.as_view(), name='verify-guardian-id-fields'),
    path('mobile-login/', MobileLoginView.as_view(), name='mobile-login'),
    path('resident-profile/<int:resident_id>/', ResidentProfileView.as_view(), name='resident-profile'),
    path('update-resident-profile/<int:resident_id>/', UpdateResidentProfileView.as_view(), name='update-resident-profile'),
]