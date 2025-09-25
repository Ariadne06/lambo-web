from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets - following SQL schema functions
router = DefaultRouter()
router.register(r'document-types', views.DocumentTypeViewSet)
router.register(r'clearance-purposes', views.ClearancePurposeViewSet)
router.register(r'application-status', views.ApplicationStatusViewSet)

app_name = 'certificate_issuance_module'

# URL patterns - following SQL workflow functions
urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # Certificate Data API
    path('certificate-data/', views.CertificateDataView.as_view(), name='certificate-data'),
    
    # Fee Calculation API - uses SQL function resident_quote_fee()
    path('fee-quote/', views.FeeQuoteView.as_view(), name='fee-quote'),
    
    # Application Submission API - uses SQL function resident_create_application()
    path('submit-application/', views.SubmitApplicationView.as_view(), name='submit-application'),
    
    # Resident Application Management API
    path('resident/<int:resident_id>/applications/', views.ResidentApplicationsView.as_view(), name='resident-applications'),
    
    # Application Details API
    path('application/<int:application_id>/details/', views.ApplicationDetailView.as_view(), name='application-details'),
    
    # Personnel Management APIs
    path('pending-applications/', views.PendingApplicationsView.as_view(), name='pending-applications'),
    
    # Secretary Workflow API - uses SQL function secretary_review_application()
    path('application/<int:application_id>/review/', views.ReviewApplicationView.as_view(), name='review-application'),
    
    # Treasurer Workflow API - uses SQL function treasurer_record_payment_and_approve()
    path('application/<int:application_id>/payment/', views.RecordPaymentView.as_view(), name='record-payment'),
    
    # Secretary Final Step API - uses SQL function secretary_mark_completed()
    path('application/<int:application_id>/complete/', views.MarkCompletedView.as_view(), name='mark-completed'),
]