"""
URL Configuration for Reports Module.
"""
from django.urls import path
from . import views

app_name = 'reports_module'

urlpatterns = [
    # Test page with buttons
    path('test/', views.ReportTestView.as_view(), name='test_reports'),
    
    # API endpoints for PDF generation
    path('api/resident-statistics/', 
         views.GenerateResidentStatisticsReport.as_view(), 
         name='api_resident_statistics'),
    
    path('api/clearance-applications/', 
         views.GenerateClearanceApplicationsReport.as_view(), 
         name='api_clearance_applications'),
    
    path('api/revenue/', 
         views.GenerateRevenueReport.as_view(), 
         name='api_revenue'),
    
    path('api/resident-list/', 
         views.GenerateResidentListReport.as_view(), 
         name='api_resident_list'),
    
    # Template-friendly URLs (non-API)
    path('resident-statistics/', 
         views.generate_resident_statistics_view, 
         name='resident_statistics'),
    
    path('clearance-applications/', 
         views.generate_clearance_applications_view, 
         name='clearance_applications'),
    
    path('revenue/', 
         views.generate_revenue_report_view, 
         name='revenue'),
    
    path('resident-list/', 
         views.generate_resident_list_view, 
         name='resident_list'),
    
    # Harmonized Family Profile PDF
    path('family-profile/<int:family_id>/', 
         views.generate_harmonized_family_profile_view, 
         name='family_profile'),
    
    path('family-profile/<int:family_id>/<int:quarter_id>/', 
         views.generate_harmonized_family_profile_view, 
         name='family_profile_quarter'),
    
    # Business PDF Reports
    path('business-list/', 
         views.generate_business_list_view, 
         name='business_list'),
    
    path('business-detail/<int:business_id>/', 
         views.generate_business_detail_view, 
         name='business_detail'),
    
    path('business-payment-history/<int:business_id>/', 
         views.generate_business_payment_history_view, 
         name='business_payment_history'),
    
    # Demographic Dashboard Report
    path('api/demographic-dashboard/', 
         views.GenerateDemographicDashboardReport.as_view(), 
         name='api_demographic_dashboard'),
    
    # Child Health List Report
    path('api/child-health-list/', 
         views.GenerateChildHealthListReport.as_view(), 
         name='api_child_health_list'),
    
    # Child Health Detail Report
    path('api/child-health-detail/<int:child_health_id>/', 
         views.GenerateChildHealthDetailReport.as_view(), 
         name='api_child_health_detail'),
]
