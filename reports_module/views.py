"""
Views for Reports Module.
Handles PDF generation and download endpoints.
"""
from django.http import HttpResponse, FileResponse
from django.shortcuts import render
from django.views import View
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime

from .pdf_templates.resident_statistics import ResidentStatisticsReport
from .pdf_templates.clearance_applications import ClearanceApplicationsReport
from .pdf_templates.revenue_report import RevenueReport
from .pdf_templates.resident_list import ResidentListReport


class ReportTestView(View):
    """View for testing report generation with buttons."""
    
    def get(self, request):
        """Render the test page with report generation buttons."""
        return render(request, 'reports_module/sample_test.html')


class GenerateResidentStatisticsReport(APIView):
    """API view to generate Resident Statistics PDF report."""
    
    def get(self, request):
        """
        Generate and display/download resident statistics report.
        
        Query parameters:
        - date_from: Start date (YYYY-MM-DD) (optional)
        - date_to: End date (YYYY-MM-DD) (optional)
        - download: Set to '1' or 'true' to force download (optional)
        """
        try:
            # Get query parameters
            date_from = request.GET.get('date_from', None)
            date_to = request.GET.get('date_to', None)
            force_download = request.GET.get('download', '0').lower() in ['1', 'true', 'yes']
            
            # Generate report
            report = ResidentStatisticsReport(date_from=date_from, date_to=date_to)
            pdf_buffer = report.generate()
            
            # Create response
            response = HttpResponse(pdf_buffer, content_type='application/pdf')
            filename = f'resident_statistics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            
            if force_download:
                # Force download
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
            else:
                # Inline preview in browser
                response['Content-Disposition'] = f'inline; filename="{filename}"'
            
            return response
            
        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GenerateClearanceApplicationsReport(APIView):
    """API view to generate Clearance Applications PDF report."""
    
    def get(self, request):
        """
        Generate and display/download clearance applications report.
        
        Query parameters:
        - date_from: Start date (YYYY-MM-DD) (optional)
        - date_to: End date (YYYY-MM-DD) (optional)
        - status: Application status filter (optional)
        - download: Set to '1' or 'true' to force download (optional)
        """
        try:
            # Get query parameters
            date_from = request.GET.get('date_from', None)
            date_to = request.GET.get('date_to', None)
            status_filter = request.GET.get('status', None)
            force_download = request.GET.get('download', '0').lower() in ['1', 'true', 'yes']
            
            # Generate report
            report = ClearanceApplicationsReport(
                date_from=date_from,
                date_to=date_to,
                status=status_filter
            )
            pdf_buffer = report.generate()
            
            # Create response
            response = HttpResponse(pdf_buffer, content_type='application/pdf')
            filename = f'clearance_applications_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            
            if force_download:
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
            else:
                response['Content-Disposition'] = f'inline; filename="{filename}"'
            
            return response
            
        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GenerateRevenueReport(APIView):
    """API view to generate Revenue PDF report."""
    
    def get(self, request):
        """
        Generate and display/download revenue report.
        
        Query parameters:
        - date_from: Start date (YYYY-MM-DD) (optional)
        - date_to: End date (YYYY-MM-DD) (optional)
        - download: Set to '1' or 'true' to force download (optional)
        """
        try:
            # Get query parameters
            date_from = request.GET.get('date_from', None)
            date_to = request.GET.get('date_to', None)
            force_download = request.GET.get('download', '0').lower() in ['1', 'true', 'yes']
            
            # Generate report
            report = RevenueReport(date_from=date_from, date_to=date_to)
            pdf_buffer = report.generate()
            
            # Create response
            response = HttpResponse(pdf_buffer, content_type='application/pdf')
            filename = f'revenue_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            
            if force_download:
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
            else:
                response['Content-Disposition'] = f'inline; filename="{filename}"'
            
            return response
            
        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GenerateResidentListReport(APIView):
    """API view to generate Resident List PDF report."""
    
    def get(self, request):
        """
        Generate and display/download resident list report.
        
        Query parameters:
        - download: Set to '1' or 'true' to force download (optional)
        """
        try:
            force_download = request.GET.get('download', '0').lower() in ['1', 'true', 'yes']
            
            # Generate report
            report = ResidentListReport()
            pdf_buffer = report.generate()
            
            # Create response
            response = HttpResponse(pdf_buffer, content_type='application/pdf')
            filename = f'resident_list_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            
            if force_download:
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
            else:
                response['Content-Disposition'] = f'inline; filename="{filename}"'
            
            return response
            
        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Template view for non-API access
def generate_resident_statistics_view(request):
    """Django template view wrapper for resident statistics report."""
    view = GenerateResidentStatisticsReport.as_view()
    return view(request._request if hasattr(request, '_request') else request)


def generate_clearance_applications_view(request):
    """Django template view wrapper for clearance applications report."""
    view = GenerateClearanceApplicationsReport.as_view()
    return view(request._request if hasattr(request, '_request') else request)


def generate_revenue_report_view(request):
    """Django template view wrapper for revenue report."""
    view = GenerateRevenueReport.as_view()
    return view(request._request if hasattr(request, '_request') else request)


def generate_resident_list_view(request):
    """Django template view wrapper for resident list report."""
    view = GenerateResidentListReport.as_view()
    return view(request._request if hasattr(request, '_request') else request)
