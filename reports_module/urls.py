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
]
