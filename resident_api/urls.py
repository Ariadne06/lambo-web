from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (ResidentViewSet, CivilStatusViewSet, EducationalAttainmentViewSet, SitioViewSet, ReligionViewSet, ResidentStatusViewSet, ReligionCategoryViewSet, ResidentRegistrationView, ResidentIdDocumentOCRView, UpdateResidentProfileView, VerifyIdFieldsView, IdentityDocTypeViewSet, VerifyGuardianView, VerifyGuardianIdFieldsView, MobileLoginView, ResidentProfileView, ChangePersonnelPasswordView, OccupationViewSet, NationalityViewSet, EmploymentStatusViewSet, ResubmitSupportingCertificateView, ReRegisterResidentView, CheckUsernameAvailabilityView, LatestResidentAnnouncements, ResidentAnnouncementsList, OwnerBusinessesMobileView, SpecificBusinessMobileView, BusinessTypesLookupView, OwnershipsLookupView, ClearanceCategoriesLookupView, SitiosLookupView)
from . import views
router = DefaultRouter()
router.register(r'residents', ResidentViewSet)
router.register(r'civil-statuses', CivilStatusViewSet)
router.register(r'educational-attainments', EducationalAttainmentViewSet)
router.register(r'sitios', SitioViewSet)
router.register(r'religions', ReligionViewSet)
router.register(r'resident-statuses', ResidentStatusViewSet)
router.register(r'religion-categories', ReligionCategoryViewSet)
router.register(r'identity-doc-types', IdentityDocTypeViewSet)
router.register(r'occupations', OccupationViewSet)
router.register(r'nationalities', NationalityViewSet)
router.register(r'employment-statuses', EmploymentStatusViewSet)

urlpatterns = router.urls

urlpatterns += [
    path('verify-id-fields/', VerifyIdFieldsView.as_view(), name='verify-id-fields'),
    path('register/', ResidentRegistrationView.as_view(), name='resident-register'),
    path('id-document/<int:pk>/ocr/', ResidentIdDocumentOCRView.as_view(), name='id-document-ocr'),
    path('verify-guardian/', VerifyGuardianView.as_view(), name='verify-guardian'),
    path('verify-guardian-id-fields/', VerifyGuardianIdFieldsView.as_view(), name='verify-guardian-id-fields'),
    path('mobile-login/', MobileLoginView.as_view(), name='mobile-login'),
    path('resident-profile/<int:resident_id>/', ResidentProfileView.as_view(), name='resident-profile'),
    path('update-resident-profile/<int:resident_id>/', UpdateResidentProfileView.as_view(), name='update-resident-profile'),
    path('change-personnel-password/', ChangePersonnelPasswordView.as_view(), name='change-personnel-password'),
    path('resubmit-supporting-certificate/', ResubmitSupportingCertificateView.as_view(), name='resubmit-supporting-certificate'),
    path('re-register-resident/', ReRegisterResidentView.as_view(), name='re-register-resident'),
    path('check-username/', CheckUsernameAvailabilityView.as_view(), name='check-username'),
    path(
        'mobile/announcements/latest/',
        LatestResidentAnnouncements.as_view(),
        name='latest-resident-announcements'
    ),
    path(
        'mobile/announcements/',
        ResidentAnnouncementsList.as_view(),
        name='resident-announcements-list'
    ),

    path(
        'mobile/businesses/',
        OwnerBusinessesMobileView.as_view(),
        name='mobile-businesses-by-owner',
    ),
    path(
        'mobile/businesses/<int:business_id>/',
        SpecificBusinessMobileView.as_view(),
        name='mobile-specific-business',
    ),
    
    # Lookup endpoints for business registration form
    path(
        'mobile/business-types/',
        BusinessTypesLookupView.as_view(),
        name='mobile-business-types',
    ),
    path(
        'mobile/ownerships/',
        OwnershipsLookupView.as_view(),
        name='mobile-ownerships',
    ),
    path(
        'mobile/clearance-categories/',
        ClearanceCategoriesLookupView.as_view(),
        name='mobile-clearance-categories',
    ),
    path(
        'mobile/sitios/',
        SitiosLookupView.as_view(),
        name='mobile-sitios',
    ),
]