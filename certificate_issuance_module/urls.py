from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'document-types', views.DocumentTypeViewSet)
router.register(r'clearance-purposes', views.ClearancePurposeViewSet)

app_name = 'certificate_issuance_module'

urlpatterns = [
    path('', include(router.urls)),
    path('create-clearance-application/', views.CreateClearanceApplicationView.as_view(), name='create-clearance-application'),
    
    # Resident applications endpoints
    path('residents/<int:resident_id>/applications/', views.ResidentApplicationListView.as_view(), name='resident-applications'),
    path('residents/<int:resident_id>/applications/<int:application_id>/', views.ResidentApplicationDetailView.as_view(), name='resident-application-detail'),
    
    # Resident transactions endpoints
    path('residents/<int:resident_id>/transactions/', views.ResidentTransactionListView.as_view(), name='resident-transactions'),
    path('residents/<int:resident_id>/transactions/<int:transaction_id>/', views.ResidentTransactionDetailView.as_view(), name='resident-transaction-detail'),
    
    # Cancel clearance endpoint
    path('residents/<int:resident_id>/applications/<int:application_id>/cancel/', views.CancelClearanceView.as_view(), name='cancel-clearance'),
    
    # Register business endpoint
    path('register-business/', views.RegisterBusinessResidentView.as_view(), name='register-business'),
]