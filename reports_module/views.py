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

from .pdf_templates.resident.resident_statistics import ResidentStatisticsReport
from .pdf_templates.business.clearance_applications import ClearanceApplicationsReport
from .pdf_templates.business import BusinessListFilteredPDF, BusinessDetailPDF, BusinessPaymentHistoryPDF
from .pdf_templates.financial.revenue_report import RevenueReport
from .pdf_templates.resident.resident_list import ResidentListReport
from .pdf_templates.family.harmonized_family_profile import HarmonizedFamilyProfilePDF
from .pdf_templates.demographic import DemographicDashboardPDF


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


def generate_harmonized_family_profile_view(request, family_id, quarter_id=None):
    """
    Generate Harmonized Family/Household Profile PDF.
    
    Args:
        family_id: Family ID to generate profile for
        quarter_id: Optional quarter ID for historical data
    
    Query parameters:
        - download: Set to '1' or 'true' to force download (optional)
    """
    try:
        force_download = request.GET.get('download', '0').lower() in ['1', 'true', 'yes']
        
        # Generate report
        report = HarmonizedFamilyProfilePDF(family_id=family_id, quarter_id=quarter_id)
        pdf_buffer = report.generate()
        
        # Create response
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        filename = f'harmonized_family_profile_{family_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        
        if force_download:
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        else:
            response['Content-Disposition'] = f'inline; filename="{filename}"'
        
        return response
        
    except Exception as e:
        return HttpResponse(
            f'<h1>Error generating PDF</h1><p>{str(e)}</p>',
            status=500
        )


def generate_business_list_view(request):
    """
    Generate filtered business list PDF.
    
    Query parameters:
        - q: Search query (optional)
        - business_type_id: Business type filter (optional)
        - clearance_category_id: Clearance category filter (optional)
        - ownership_id: Ownership filter (optional)
        - business_status_id: Business status filter (optional)
        - download: Set to '1' or 'true' to force download (optional)
    """
    try:
        # Get query parameters
        query = request.GET.get('q', None)
        business_type_id = request.GET.get('business_type_id', None)
        clearance_category_id = request.GET.get('clearance_category_id', None)
        ownership_id = request.GET.get('ownership_id', None)
        business_status_id = request.GET.get('business_status_id', None)
        force_download = request.GET.get('download', '0').lower() in ['1', 'true', 'yes']
        
        # Generate report
        report = BusinessListFilteredPDF(
            query=query,
            business_type_id=business_type_id,
            clearance_category_id=clearance_category_id,
            ownership_id=ownership_id,
            business_status_id=business_status_id
        )
        pdf_buffer = report.generate()
        
        # Create response
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        filename = f'business_list_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        
        if force_download:
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        else:
            response['Content-Disposition'] = f'inline; filename="{filename}"'
        
        return response
        
    except Exception as e:
        return HttpResponse(
            f'<h1>Error generating PDF</h1><p>{str(e)}</p>',
            status=500
        )


def generate_business_detail_view(request, business_id):
    """
    Generate business detail PDF.
    
    Args:
        business_id: Business ID to generate profile for
    
    Query parameters:
        - download: Set to '1' or 'true' to force download (optional)
    """
    try:
        force_download = request.GET.get('download', '0').lower() in ['1', 'true', 'yes']
        
        # Generate report
        report = BusinessDetailPDF(business_id=business_id)
        pdf_buffer = report.generate()
        
        # Create response
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        filename = f'business_detail_{business_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        
        if force_download:
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        else:
            response['Content-Disposition'] = f'inline; filename="{filename}"'
        
        return response
        
    except Exception as e:
        return HttpResponse(
            f'<h1>Error generating PDF</h1><p>{str(e)}</p>',
            status=500
        )


def generate_business_payment_history_view(request, business_id):
    """
    Generate business payment history PDF with filter support.
    
    Args:
        business_id: Business ID to generate payment history for
    
    Query parameters:
        - q: Search query (optional)
        - status: Payment status filter (optional)
        - date_from: Start date filter (optional)
        - date_to: End date filter (optional)
        - download: Set to '1' or 'true' to force download (optional)
    """
    try:
        # Get filter parameters
        query = request.GET.get('q', None)
        payment_status = request.GET.get('status', None)
        date_from = request.GET.get('date_from', None)
        date_to = request.GET.get('date_to', None)
        force_download = request.GET.get('download', '0').lower() in ['1', 'true', 'yes']
        
        # Generate report
        report = BusinessPaymentHistoryPDF(
            business_id=business_id,
            query=query,
            payment_status=payment_status,
            date_from=date_from,
            date_to=date_to
        )
        pdf_buffer = report.generate()
        
        # Create response
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        filename = f'business_payment_history_{business_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        
        if force_download:
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        else:
            response['Content-Disposition'] = f'inline; filename="{filename}"'
        
        return response
        
    except Exception as e:
        return HttpResponse(
            f'<h1>Error generating PDF</h1><p>{str(e)}</p>',
            status=500
        )


class GenerateDemographicDashboardReport(APIView):
    """API view to generate Demographic Dashboard PDF report."""
    
    def get(self, request):
        """
        Generate and display/download demographic dashboard report.
        
        Query parameters:
        - download: Set to '1' or 'true' to force download (optional)
        """
        try:
            force_download = request.GET.get('download', '0').lower() in ['1', 'true', 'yes']
            
            # Generate report
            report = DemographicDashboardPDF()
            pdf_buffer = report.generate()
            
            # Create response
            response = HttpResponse(pdf_buffer, content_type='application/pdf')
            filename = f'demographic_dashboard_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            
            if force_download:
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
            else:
                response['Content-Disposition'] = f'inline; filename="{filename}"'
            
            return response
            
        except Exception as e:
            return HttpResponse(
                f'<h1>Error generating PDF</h1><p>{str(e)}</p>',
                status=500
            )


