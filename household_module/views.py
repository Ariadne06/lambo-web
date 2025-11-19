from rest_framework import viewsets, status, serializers
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from .models import HouseType, Household, PhilhealthCategory
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import connection
from .models import HouseOwnershipType, HouseholdType, WaterSourceType, ToiletFacilityType, WasteManagementType, RelationshipToHouseholdHead, NutritionStatus, MedicalHistoryType, Class, FPMethod, FPStatus, Relationship, FeedingMethod, Month, TTStatus, VaccineType, DoseType, Supplements
from .serializers import (
    FamilyMemberCreateSerializer, HouseOwnershipTypeSerializer, HouseTypeSerializer, HouseholdTypeSerializer, NutritionStatusSerializer, WaterSourceTypeSerializer,
    ToiletFacilityTypeSerializer, WasteManagementTypeSerializer,
    HouseholdInsertSerializer, FamilyCreateSerializer, RelationshipToHouseholdHeadSerializer, PhilhealthCategorySerializer, MedicalHistoryTypeSerializer, ClassSerializer, 
    FPMethodSerializer, FPStatusSerializer, GeneralHealthCreateSerializer, GeneralHealthUpdateSerializer, QuarterSerializer, RelationshipSerializer, HouseholdUpdateSerializer, FeedingMethodSerializer, MonthSerializer, TTStatusSerializer,
    VaccineTypeSerializer, DoseTypeSerializer, SupplementsSerializer,
    ChildHealthRecordCreateSerializer, ChildHealthRecordUpdateSerializer, ChildGrowthMonitoringCreateSerializer, ChildImmunizationCreateSerializer
)
from .utils.database_helpers import (
    search_child, view_specific_child_health_record, view_all_child_health_records
)
from .services.household_service import HouseholdService
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from resident_profiling_module.models import Quarter
import re
import json


# ViewSets for lookup data - following your exact pattern
class HouseOwnershipTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HouseOwnershipType.objects.all()
    serializer_class = HouseOwnershipTypeSerializer

class HouseTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HouseType.objects.all()
    serializer_class = HouseTypeSerializer

class HouseholdTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HouseholdType.objects.all()
    serializer_class = HouseholdTypeSerializer

class WaterSourceTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WaterSourceType.objects.all()
    serializer_class = WaterSourceTypeSerializer

class ToiletFacilityTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ToiletFacilityType.objects.all()
    serializer_class = ToiletFacilityTypeSerializer

class WasteManagementTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WasteManagementType.objects.all()
    serializer_class = WasteManagementTypeSerializer

class RelationshipViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RelationshipToHouseholdHead.objects.all()
    serializer_class = RelationshipToHouseholdHeadSerializer

class PhilhealthCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PhilhealthCategory.objects.all()
    serializer_class = PhilhealthCategorySerializer

class NutritionStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NutritionStatus.objects.all()
    serializer_class = NutritionStatusSerializer

class MedicalHistoryTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MedicalHistoryType.objects.all()
    serializer_class = MedicalHistoryTypeSerializer

class ClassViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Class.objects.all()
    serializer_class = ClassSerializer

class FPMethodViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FPMethod.objects.all()
    serializer_class = FPMethodSerializer

class FPStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FPStatus.objects.all()
    serializer_class = FPStatusSerializer

class QuarterViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Quarter.objects.all().order_by('-year', '-quarter_number')
    serializer_class = QuarterSerializer

class ResidentFamilyRelationshipViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Relationship.objects.all().order_by('relationship_id')
    serializer_class = RelationshipSerializer

class FeedingMethodViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FeedingMethod.objects.filter(is_active=True)
    serializer_class = FeedingMethodSerializer


class MonthViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Month.objects.all().order_by('month_number')
    serializer_class = MonthSerializer


class TTStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TTStatus.objects.all().order_by('tt_status_id')
    serializer_class = TTStatusSerializer


class VaccineTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = VaccineType.objects.all().order_by('vaccine_name')
    serializer_class = VaccineTypeSerializer


class DoseTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DoseType.objects.all()
    serializer_class = DoseTypeSerializer


class SupplementsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Supplements.objects.filter(is_active=True)
    serializer_class = SupplementsSerializer



class HouseholdListView(APIView):
    """Optimized household list with pagination and filtering"""
    
    def get(self, request):
        print("GET /household_api/households/ called")
        
        try:
            # Get pagination parameters
            limit = int(request.GET.get('limit', 50))
            offset = int(request.GET.get('offset', 0))
            
            # NEW: Get ALL filter parameters
            quarter_id = request.GET.get('quarter_id', None)
            sitio_id = request.GET.get('sitio_id', None)
            visit_status = request.GET.get('visit_status', 'all')  # 'all', 'visited', 'not_visited'
            search_query = request.GET.get('search', None)
            
            # Convert empty strings to None for SQL
            if quarter_id == '':
                quarter_id = None
            if sitio_id == '':
                sitio_id = None
            if search_query == '':
                search_query = None
            
            # Validate visit_status
            if visit_status not in ['all', 'visited', 'not_visited']:
                visit_status = 'all'
            
            # Create cache key based on ALL params
            cache_key = f'households_list_{quarter_id}_{sitio_id}_{visit_status}_{search_query}_{limit}_{offset}'
            
            # Try to get from cache first (cache for 5 minutes)
            cached_data = cache.get(cache_key)
            if cached_data:
                print(f"✓ Returning cached data ({len(cached_data)} households)")
                return Response({
                    'success': True,
                    'message': 'Households retrieved from cache',
                    'data': cached_data,
                    'count': len(cached_data),
                    'has_more': len(cached_data) == limit,
                    'filters': {
                        'quarter_id': quarter_id,
                        'sitio_id': sitio_id,
                        'visit_status': visit_status,
                        'search': search_query
                    }
                }, status=status.HTTP_200_OK)
            
            # Optimized query with ALL filters
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM get_all_households(
                        %s,  -- bhw_id (NULL for all)
                        %s,  -- quarter_id (NEW: filter by quarter)
                        %s,  -- sitio_id (NEW: filter by sitio)
                        %s,  -- filter (NEW: all/visited/not_visited)
                        %s,  -- search_query (NEW: search filter)
                        %s,  -- limit
                        %s   -- offset
                    )
                """, [None, quarter_id, sitio_id, visit_status, search_query, limit, offset])
                
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                
                households = []
                for row in rows:
                    household_dict = dict(zip(columns, row))
                    # Format dates
                    if household_dict.get('date_visited'):
                        household_dict['date_visited'] = household_dict['date_visited'].isoformat()
                    if household_dict.get('created_at'):
                        household_dict['created_at'] = household_dict['created_at'].isoformat()
                    if household_dict.get('updated_at'):
                        household_dict['updated_at'] = household_dict['updated_at'].isoformat()
                    households.append(household_dict)
            
            # Cache the result for 5 minutes
            cache.set(cache_key, households, 300)
            
            print(f"✓ Retrieved {len(households)} households with filters: quarter={quarter_id}, sitio={sitio_id}, visit_status={visit_status}")
            
            return Response({
                'success': True,
                'message': 'Households retrieved successfully',
                'data': households,
                'count': len(households),
                'has_more': len(households) == limit,
                'limit': limit,
                'offset': offset,
                'filters': {
                    'quarter_id': quarter_id,
                    'sitio_id': sitio_id,
                    'visit_status': visit_status,
                    'search': search_query
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"✗ Error retrieving households: {e}")
            
            return Response({
                'success': False,
                'message': 'Failed to retrieve households',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# class HouseholdCreateView(APIView):
#     parser_classes = (MultiPartParser, FormParser)

#     def post(self, request):
#         serializer = HouseholdCreateSerializer(data=request.data)
#         if not serializer.is_valid():
#             return Response({
#                 'success': False,
#                 'error': 'Validation failed',
#                 'details': serializer.errors
#             }, status=status.HTTP_400_BAD_REQUEST)

#         household = HouseholdService.create_household(serializer.validated_data)
#         return Response({
#             'success': True,
#             'household_id': household.household_id,
#             'household_number': household.household_number,
#             'message': 'Household created successfully'
#         }, status=status.HTTP_201_CREATED)
    
class FamilyCreateView(APIView):
    """Create family - following your pattern"""
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request, household_id):
        print(f"POST /api/households/{household_id}/families/create/ called")
        
        try:
            serializer = FamilyCreateSerializer(
                data=request.data, 
                context={'request': request, 'household_id': household_id}
            )
            
            if not serializer.is_valid():
                print("Family serializer validation failed:", serializer.errors)
                return Response({
                    'success': False,
                    'error': 'Validation failed',
                    'user_message': self._format_validation_errors(serializer.errors),
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            print("Family serializer is valid")
            try:
                family = serializer.save()
            except serializers.ValidationError as serr:
                # propagate serializer validation
                print("Serializer raised ValidationError:", serr)
                return Response({
                    'success': False,
                    'error': 'Validation failed',
                    'user_message': str(serr.detail) if hasattr(serr, 'detail') else str(serr),
                    'details': serr.detail if hasattr(serr, 'detail') else str(serr)
                }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                # map DB/internal errors to friendly messages
                err_text = str(e)
                user_msg = self._get_user_friendly_error(err_text)
                print(f"Database error creating family: {err_text}")
                return Response({
                    'success': False,
                    'error': err_text,
                    'user_message': user_msg
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # CLEAR CACHE so household details show newly created family
            try:
                cache.delete(f'household_families_{household_id}')
                cache.delete(f'household_detail_{household_id}')
                cache.delete(f'households_list_{household_id}')
                print(f"Cleared caches for household {household_id}")
            except Exception as ce:
                print(f"Could not clear cache: {ce}")
            
            print(f"Family creation successful for ID: {family.family_id}")
            
            return Response({
                'success': True,
                'family_id': family.family_id,
                'message': 'Family created successfully'
            }, status=201)
            
        except Exception as e:
            print(f"Unexpected error in family creation: {e}")
            err_text = str(e)
            user_msg = self._get_user_friendly_error(err_text)
            return Response({
                'success': False,
                'error': 'Family creation failed. Please try again.',
                'user_message': user_msg,
                'detail': err_text
            }, status=500)
        
    def _format_validation_errors(self, errors):
        """Convert validation errors to user-friendly messages"""
        messages = []
        for field, error_list in errors.items():
            if isinstance(error_list, list):
                messages.extend(error_list)
            else:
                messages.append(str(error_list))
        return '; '.join(messages)
    
    def _extract_error_code(self, error_message):
        """Extract error code from SQL error"""
        import re
        match = re.search(r'E(\d+[A-Z]*)', error_message)
        return match.group(0) if match else 'UNKNOWN_ERROR'
    
    def _get_user_friendly_error(self, error_message):
        """Convert SQL error codes to user-friendly messages"""
        
        # Relationship validation errors
        if 'E7209M' in error_message:
            return "Family head and respondent are the same person but have different relationships to household head. Please ensure they have the same relationship."
        
        if 'E7206HH' in error_message:
            return "When respondent is the family head (same person), their relationship to family head must be 'Family Head'."
        
        if 'E7217H' in error_message:
            return "Family head is marked as 'Household Head', but the selected person is not the actual household head. Please select the correct person or change the relationship."
        
        if 'E7206H' in error_message:
            return "Respondent is marked as 'Family Head', but the selected person is not the family head. Please select the correct person or change the relationship."
        
        if 'E7209H' in error_message:
            return "Respondent is marked as 'Household Head', but the selected person is not the actual household head."
        
        # Required field errors
        if 'E7203A' in error_message:
            return "Family head is required. Please select a family head."
        
        if 'E7204R' in error_message:
            return "Respondent is required. Please select a respondent."
        
        if 'E7217R' in error_message:
            return "Family head's relationship to household head is required."
        
        if 'E7206R' in error_message:
            return "Respondent's relationship to family head is required."
        
        if 'E7209R' in error_message and 'respondent_rth_id' in error_message:
            return "Respondent's relationship to household head is required when respondent is different from family head."
        
        if 'E7207R' in error_message:
            return "Water source type is required. Please select a water source."
        
        if 'E7208R' in error_message:
            return "Toilet facility type is required. Please select a toilet facility."
        
        if 'E7209R' in error_message and 'Waste' in error_message:
            return "Waste management type is required. Please select waste management type."
        
        # Lookup validation errors
        if 'E7201' in error_message:
            return "Household not found. Please refresh and try again."
        
        if 'E7202' in error_message:
            return "Invalid household type selected. Please choose a valid household type."
        
        if 'E7203' in error_message:
            return "Selected family head not found in the system."
        
        if 'E7204' in error_message:
            return "Selected respondent not found in the system."
        
        if 'E7207' in error_message:
            return "Invalid water source type selected."
        
        if 'E7208' in error_message:
            return "Invalid toilet facility type selected."
        
        if 'E7209' in error_message:
            return "Invalid waste management type selected."
        
        if 'E7217' in error_message:
            return "Invalid relationship to household head selected."
        
        if 'E7206' in error_message:
            return "Invalid relationship to family head selected."
        
        # Permission/assignment errors
        if 'E7213' in error_message:
            return "You are not assigned to this area. Please contact your administrator."
        
        if 'E7200' in error_message:
            return "Authentication error. Please log in again."
        
        # Generic fallback
        if 'unique_violation' in error_message.lower():
            return "This family already exists or there's a duplicate entry. Please check your data."
        
        # Return original message if no pattern matches
        return f"Family creation failed: {error_message}"

    
class HouseholdInsertView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        serializer = HouseholdInsertSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = serializer.save()
            return Response({
                'success': True,
                'household_id': result['household_id'],
                'message': 'Household created successfully'
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Failed to create household'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class ResidentSearchView(APIView):
    def get(self, request):
        query = request.GET.get('q', '')
        only_verified = request.GET.get('only_verified', 'false') == 'true'
        status_filter = request.GET.get('status_filter', None)
        exclude_linked = request.GET.get('exclude_linked', 'false') == 'true'
        limit = int(request.GET.get('limit', 25))
        offset = int(request.GET.get('offset', 0))

        try:
            with connection.cursor() as cursor:
                cursor.callproc('search_resident', [
                    query,
                    only_verified,
                    status_filter,
                    exclude_linked,
                    limit,
                    offset
                ])
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                results = [dict(zip(columns, row)) for row in rows]
            return Response({'success': True, 'results': results}, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Resident search error: {e}")
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class HouseholdDetailView(APIView):
    """Optimized household detail with caching"""
    
    def get(self, request, household_id):
        try:
            quarter_id = request.GET.get('quarter_id', None)
            
            # Get current quarter for comparison
            current_quarter_id = None
            with connection.cursor() as cursor:
                cursor.execute("SELECT get_current_quarter_id()")
                result = cursor.fetchone()
                if result:
                    current_quarter_id = result[0]
            
            cache_key = f'household_detail_{household_id}_{quarter_id}'
            cached_data = cache.get(cache_key)
            
            if cached_data:
                # Add current quarter flag to cached data
                if isinstance(cached_data, dict) and cached_data.get('success') and cached_data.get('data'):
                    cached_data['data']['is_current_quarter'] = (
                        cached_data['data'].get('quarter_id') == current_quarter_id
                    )
                return Response(cached_data)
            
            with connection.cursor() as cursor:
                cursor.callproc('get_specific_household', [household_id, quarter_id])
                cols = [c[0] for c in cursor.description]
                row = cursor.fetchone()
                
                if row:
                    household_data = dict(zip(cols, row))
                    
                    # Add current quarter flag
                    household_data['is_current_quarter'] = (
                        household_data.get('quarter_id') == current_quarter_id
                    )
                    
                    # Format dates
                    if household_data.get('date_visited'):
                        household_data['date_visited'] = household_data['date_visited'].isoformat()
                    
                    response_data = {
                        'success': True,
                        'data': household_data
                    }
                    
                    # Cache for 10 minutes
                    cache.set(cache_key, response_data, 60)
                    return Response(response_data)
                else:
                    return Response({
                        'success': False,
                        'message': 'Household not found'
                    }, status=404)
                    
        except Exception as e:
            print(f"Error: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)

class HouseholdFamiliesView(APIView):
    """Optimized families view with caching"""
    
    def get(self, request, household_id):
        try:
            # Get quarter parameter
            quarter_id = request.GET.get('quarter_id', None)
            
            # Create cache key that includes quarter
            cache_key = f'household_families_{household_id}_{quarter_id}'
            cached_data = cache.get(cache_key)
            
            if cached_data:
                return Response(cached_data, status=200)
            
            # Fetch from database with quarter parameter
            with connection.cursor() as cursor:
                cursor.callproc('get_family_summaries_per_household', [household_id, quarter_id])
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                
                families = [dict(zip(columns, row)) for row in rows]
                
                response_data = {
                    'success': True,
                    'data': families
                }
                
                # Cache for 5 minutes
                cache.set(cache_key, response_data, 300)
                return Response(response_data, status=200)
                    
        except Exception as e:
            print(f"Error: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)

class HouseholdUpdateView(APIView):
    """Update household - only allowed for current quarter and non-visited households"""
    parser_classes = (MultiPartParser, FormParser)
    
    def put(self, request, household_id):
        try:
            # Get current quarter to enforce restriction
            current_quarter = self._get_current_quarter()
            if not current_quarter:
                return Response({
                    'success': False,
                    'error': 'Unable to determine current quarter'
                }, status=500)
            
            # Validate household exists and is in current quarter
            household_validation = self._validate_household_for_update(household_id, current_quarter['quarter_id'])
            if not household_validation['valid']:
                return Response({
                    'success': False,
                    'error': household_validation['error'],
                    'user_message': household_validation['user_message']
                }, status=400)
            
            # Create serializer for validation
            serializer = HouseholdUpdateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'error': 'Validation failed',
                    'details': serializer.errors,
                    'user_message': self._format_validation_errors(serializer.errors)
                }, status=400)
            
            # Call the SQL function
            updated_household_id = HouseholdService.update_household(household_id, serializer.validated_data)
            
            if updated_household_id:
                # Clear cache for the updated household
                cache_keys_to_clear = [
                    f'household_detail_{household_id}_*',
                    f'household_families_{household_id}_*',
                    'households_list_*'
                ]
                for pattern in cache_keys_to_clear:
                    cache.delete_many(cache.get_many(pattern))
                
                return Response({
                    'success': True,
                    'household_id': updated_household_id,
                    'message': 'Household updated successfully'
                }, status=200)
            else:
                return Response({
                    'success': False,
                    'error': 'Update operation failed'
                }, status=500)
                
        except Exception as e:
            error_message = str(e)
            user_message = self._get_user_friendly_update_error(error_message)
            
            return Response({
                'success': False,
                'error': error_message,
                'user_message': user_message
            }, status=500)
    
    def _get_current_quarter(self):
        """Get the current active quarter"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT get_current_quarter_id()")
                current_quarter_id = cursor.fetchone()[0]
                
                if current_quarter_id:
                    cursor.execute("""
                        SELECT quarter_id, quarter_name, year, start_date, end_date
                        FROM Quarter 
                        WHERE quarter_id = %s
                    """, [current_quarter_id])
                    row = cursor.fetchone()
                    
                    if row:
                        return {
                            'quarter_id': row[0],
                            'quarter_name': row[1],
                            'year': row[2],
                            'start_date': row[3],
                            'end_date': row[4]
                        }
            return None
        except Exception:
            return None
    
    def _validate_household_for_update(self, household_id, current_quarter_id):
        """Validate if household can be updated"""
        try:
            with connection.cursor() as cursor:
                # Check if household exists and get its details
                cursor.execute("""
                    SELECT h.household_id, h.quarter, h.is_visited, h.is_active,
                           q.quarter_name, q.year
                    FROM Household h
                    LEFT JOIN Quarter q ON h.quarter = q.quarter_id
                    WHERE h.household_id = %s
                """, [household_id])
                
                row = cursor.fetchone()
                if not row:
                    return {
                        'valid': False,
                        'error': 'Household not found',
                        'user_message': 'The household you are trying to update does not exist.'
                    }
                
                household_quarter = row[1]
                is_visited = row[2]
                is_active = row[3]
                quarter_name = row[4]
                year = row[5]
                
                # Check if household is active
                if not is_active:
                    return {
                        'valid': False,
                        'error': 'Household is inactive',
                        'user_message': 'This household is inactive and cannot be updated.'
                    }
                
                # Check if already visited
                if is_visited:
                    return {
                        'valid': False,
                        'error': 'Household already visited',
                        'user_message': 'This household has already been visited and cannot be modified.'
                    }
                
                # Check if it's from current quarter
                if household_quarter != current_quarter_id:
                    return {
                        'valid': False,
                        'error': 'Quarter restriction',
                        'user_message': f'You can only update households from the current quarter. This household is from {quarter_name} {year}.'
                    }
                
                return {'valid': True}
                
        except Exception as e:
            return {
                'valid': False,
                'error': f'Validation error: {str(e)}',
                'user_message': 'Unable to validate household for update. Please try again.'
            }
    
    def _format_validation_errors(self, errors):
        """Convert validation errors to user-friendly messages"""
        messages = []
        for field, error_list in errors.items():
            if isinstance(error_list, list):
                for error in error_list:
                    messages.append(f"{field.replace('_', ' ').title()}: {error}")
            else:
                messages.append(f"{field.replace('_', ' ').title()}: {error_list}")
        return '. '.join(messages)
    
    def _get_user_friendly_update_error(self, error_message):
        """Convert SQL errors to user-friendly messages"""
        
        if 'E7101' in error_message:
            return "Household not found. Please refresh and try again."
        
        if 'E7117' in error_message:
            return "This household has already been visited and cannot be modified."
        
        if 'E7102' in error_message:
            return "Invalid house ownership type selected."
        
        if 'E7103' in error_message:
            return "Invalid house type selected."
        
        if 'E7104' in error_message:
            return "Invalid sitio/purok selected."
        
        if 'E7105' in error_message:
            return "Selected respondent not found in the system."
        
        if 'E7106' in error_message:
            return "Respondent's relationship to household head is required."
        
        if 'E7107' in error_message:
            return "Invalid relationship to household head selected."
        
        if 'E7108' in error_message:
            return "Selected household head not found in the system."
        
        if 'E7112' in error_message:
            return "Barangay is required and cannot be empty."
        
        if 'E7113' in error_message:
            return "City/Municipality is required and cannot be empty."
        
        if 'E7116' in error_message:
            return "You are not assigned to this area and cannot make updates."
        
        if 'not_null_violation' in error_message.lower():
            return "Required fields are missing. Please fill in all required information."
        
        if 'foreign_key_violation' in error_message.lower():
            return "Invalid selection detected. Please check your selections and try again."
        
        return "Update failed. Please check your information and try again."

class FamilyDetailView(APIView):
    """Get specific family details"""
    
    def get(self, request, family_id):
        try:
            cache_key = f'family_detail_{family_id}'
            cached_data = cache.get(cache_key)
            
            if cached_data:
                return Response({
                    'success': True,
                    'data': cached_data
                })
            
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM get_specific_family(%s, NULL)",
                    [family_id]
                )
                columns = [col[0] for col in cursor.description]
                row = cursor.fetchone()
                
                if not row:
                    return Response({
                        'success': False,
                        'message': 'Family not found'
                    }, status=404)
                
                data = dict(zip(columns, row))
                
                # Parse members_json if it's a JSONB string
                if data.get('members_json'):
                    if isinstance(data['members_json'], str):
                        try:
                            import json
                            data['members_json'] = json.loads(data['members_json'])
                        except:
                            data['members_json'] = []
                else:
                    data['members_json'] = []
                
                # Format dates
                if data.get('date_visited'):
                    data['date_visited'] = data['date_visited'].isoformat()
                
                # Cache for 10 minutes
                cache.set(cache_key, data, 60)
                
                print(f"Family {family_id} has {len(data['members_json'])} members")
                
                return Response({
                    'success': True,
                    'data': data
                })
                
        except Exception as e:
            print(f"Error fetching family {family_id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)


class FamilyMemberCreateView(APIView):
    """Add family member """
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request, family_id):
        try:
            personnel_id = request.data.get('personnel_id')
            
            serializer = FamilyMemberCreateSerializer(
                data=request.data,
                context={'family_id': family_id, 'personnel_id': personnel_id}
            )
            
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'errors': serializer.errors
                }, status=400)
            
            result = serializer.save()
            
            return Response({
                'success': True,
                'family_member_id': result['family_member_id'],
                'message': 'Family member added successfully'
            }, status=201)
            
        except Exception as e:
            print(f"Error: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)

class FamilyMembersListView(APIView):
    """Get family members"""
    
    def get(self, request, family_id):
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM get_family_members_list(%s, NULL)",
                    [family_id]
                )
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                
                members = []
                for row in rows:
                    member_dict = dict(zip(columns, row))
                    if member_dict.get('date_added'):
                        member_dict['date_added'] = member_dict['date_added'].isoformat()
                    members.append(member_dict)
                
                return Response({
                    'success': True,
                    'data': members,
                    'count': len(members)
                })
                
        except Exception as e:
            print(f"Error: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)

# family member details w/ general health        
class FamilyMemberDetailView(APIView):
    """Get family member detail WITH General Health"""
    
    def get(self, request, family_member_id):
        try:
            quarter_id = request.GET.get('quarter_id', None)
            
            cache_key = f'family_member_detail_{family_member_id}_{quarter_id}'
            cached_data = cache.get(cache_key)
            
            if cached_data:
                return Response({
                    'success': True,
                    'data': cached_data
                })
            
            with connection.cursor() as cursor:
                #  Step 1: Get basic member info (includes sex)
                cursor.execute(
                    "SELECT * FROM get_specific_family_member(%s, %s)",
                    [family_member_id, quarter_id]
                )
                columns = [col[0] for col in cursor.description]
                row = cursor.fetchone()
                
                if not row:
                    return Response({
                        'success': False,
                        'message': 'Member not found'
                    }, status=404)
                
                data = dict(zip(columns, row))
                
                #  Ensure sex is present
                if not data.get('sex'):
                    cursor.execute(
                        "SELECT sex FROM resident WHERE resident_id = %s",
                        [data.get('resident_id')]
                    )
                    sex_row = cursor.fetchone()
                    if sex_row:
                        data['sex'] = sex_row[0]
                
                #  Step 2: Try to get General Health data
                try:
                    cursor.execute(
                        "SELECT * FROM get_specific_family_member_genhealth(%s, %s)",
                        [family_member_id, quarter_id]
                    )
                    
                    gh_row = cursor.fetchone()
                    
                    #   Check if GH record actually exists
                    if gh_row:
                        gh_columns = [col[0] for col in cursor.description]
                        gh_data = dict(zip(gh_columns, gh_row))
                        
                        #  IMPORTANT: Only set has_general_health to True if record_id is valid
                        # record_id will be NULL or 0 if no GH exists
                        gh_record_id = gh_data.get('record_id')
                        
                        if gh_record_id and gh_record_id > 0:
                            #  Valid GH record found
                            # Format dates
                            if gh_data.get('last_menstrual_period'):
                                gh_data['last_menstrual_period'] = gh_data['last_menstrual_period'].isoformat()
                            if gh_data.get('created_at'):
                                gh_data['created_at'] = gh_data['created_at'].isoformat()
                            if gh_data.get('updated_at'):
                                gh_data['updated_at'] = gh_data['updated_at'].isoformat()
                            
                            #  Add GH fields to response
                            data['has_general_health'] = True
                            data['gh_id'] = gh_data.get('record_id')
                            data['gh_class_id'] = gh_data.get('class_id')
                            data['gh_class_description'] = gh_data.get('class_description')
                            data['gh_medical_history_ids'] = gh_data.get('medical_history_ids')
                            data['gh_medical_history_names'] = gh_data.get('medical_history_names')
                            data['gh_age'] = gh_data.get('age')
                            data['gh_smoker'] = gh_data.get('smoker')
                            data['gh_alcohol_drinker'] = gh_data.get('alcohol_drinker')
                            data['gh_sexually_active'] = gh_data.get('sexually_active')
                            
                            # Female-specific fields
                            if data.get('sex', '').lower() == 'female':
                                data['gh_last_menstrual_period'] = gh_data.get('last_menstrual_period')
                                data['gh_fp_method_yn'] = gh_data.get('fp_method_yn')
                                data['gh_fp_method_id'] = gh_data.get('fp_method_id')
                                data['gh_fp_method_name'] = gh_data.get('fp_method_name')
                                data['gh_fp_status_id'] = gh_data.get('fp_status_id')
                                data['gh_fp_status_name'] = gh_data.get('fp_status_name')
                                data['gh_age_of_menarche'] = gh_data.get('age_of_menarche')
                            
                            print(f" Valid GH found for member {family_member_id} (gh_id: {gh_record_id})")
                        else:
                            #  No valid GH record (record_id is NULL or 0)
                            data['has_general_health'] = False
                            data['gh_id'] = None
                            print(f" No GH record for member {family_member_id} (record_id was {gh_record_id})")
                    else:
                        #  No row returned at all
                        data['has_general_health'] = False
                        data['gh_id'] = None
                        print(f" No GH record for member {family_member_id} (no row returned)")
                        
                except Exception as gh_error:
                    #  Error fetching GH - treat as no GH exists
                    print(f" GH function error for member {family_member_id}: {gh_error}")
                    data['has_general_health'] = False
                    data['gh_id'] = None
                
                # Format member dates
                if data.get('date_added'):
                    data['date_added'] = data['date_added'].isoformat()
                
                #  Log the response for debugging
                print(f" Sending response for member {family_member_id}:")
                print(f"   - has_general_health: {data.get('has_general_health')}")
                print(f"   - gh_id: {data.get('gh_id')}")
                print(f"   - sex: {data.get('sex')}")
                
                # Cache for 10 minutes
                cache.set(cache_key, data, 600)
                
                return Response({
                    'success': True,
                    'data': data
                })
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)
        
class GeneralHealthCreateView(APIView):
    """Add general health profile for a family member"""
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    
    def post(self, request, family_member_id):
        try:
            personnel_id = request.data.get('personnel_id')
            
            serializer = GeneralHealthCreateSerializer(
                data=request.data,
                context={
                    'family_member_id': family_member_id,
                    'personnel_id': personnel_id
                }
            )
            
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'errors': serializer.errors
                }, status=400)
            
            result = serializer.save()
        
            #  Clear member cache
            cache_key_member = f'family_member_detail_{family_member_id}_None'
            cache.delete(cache_key_member)
            print(f" Cleared cache for member {family_member_id}")
            
            #  CRITICAL: Clear family cache to update members_json
            # First, get the family_id for this member
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT family_id FROM family_member WHERE family_member_id = %s",
                    [family_member_id]
                )
                row = cursor.fetchone()
                if row:
                    family_id = row[0]
                    cache_key_family = f'family_detail_{family_id}'
                    cache.delete(cache_key_family)
                    print(f" Cleared cache for family {family_id}")
            
            return Response({
                'success': True,
                'gh_id': result['gh_id'],
                'message': 'General health profile saved successfully'
            }, status=201)
            
        except Exception as e:
            print(f" Error: {e}")
            import traceback
            traceback.print_exc()
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)

class GeneralHealthUpdateView(APIView):
    """Update general health profile for a family member"""
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    
    def put(self, request, family_member_id):
        try:
            personnel_id = request.data.get('personnel_id')
            
            if not personnel_id:
                return Response({
                    'success': False,
                    'error': 'personnel_id is required'
                }, status=400)
            
            serializer = GeneralHealthUpdateSerializer(
                data=request.data,
                context={
                    'family_member_id': family_member_id,
                    'personnel_id': personnel_id
                }
            )
            
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'errors': serializer.errors
                }, status=400)
            
            # Perform update
            result = serializer.update(None, serializer.validated_data)
            
            #  Clear member cache
            cache_key_member = f'family_member_detail_{family_member_id}_None'
            cache.delete(cache_key_member)
            
            #  CRITICAL: Clear family cache to update members_json
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT family_id FROM family_member WHERE family_member_id = %s",
                    [family_member_id]
                )
                row = cursor.fetchone()
                if row:
                    family_id = row[0]
                    cache_key_family = f'family_detail_{family_id}'
                    cache.delete(cache_key_family)
                    print(f" Cleared cache for family {family_id}")
            
            return Response({
                'success': True,
                'gh_id': result['gh_id'],
                'message': 'General health profile updated successfully'
            }, status=200)
            
        except Exception as e:
            print(f" Error: {e}")
            import traceback
            traceback.print_exc()
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)
            

class HouseholdMarkVisitedView(APIView):
    """Mark household as visited"""
    
    def post(self, request, household_id):
        try:
            personnel_id = request.data.get('personnel_id')
            enforce_bhw_assignment = request.data.get('enforce_bhw_assignment', False)
            
            if not personnel_id:
                return Response({
                    'success': False,
                    'error': 'personnel_id is required'
                }, status=400)
            
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT mark_household_visited(%s, %s, %s)",
                    [household_id, personnel_id, enforce_bhw_assignment]
                )
                result = cursor.fetchone()
                household_id_returned = result[0] if result else None
            
            if household_id_returned:
                cache.delete(f'household_detail_{household_id}')
                cache.delete('households_list_*')
                
                return Response({
                    'success': True,
                    'household_id': household_id_returned,
                    'message': 'Household marked as visited'
                }, status=200)
            else:
                return Response({
                    'success': False,
                    'error': 'Failed to mark household as visited'
                }, status=500)
                
        except Exception as e:
            print(f"Error marking household visited: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)


class FamilyMarkVisitedView(APIView):
    """
    Mark family as visited - STRICT GATE
    Only allows marking if ALL members have GH data for current quarter
    """
    
    def post(self, request, family_id):
        try:
            personnel_id = request.data.get('personnel_id')
            enforce_bhw_assignment = request.data.get('enforce_bhw_assignment', False)
            
            if not personnel_id:
                return Response({
                    'success': False,
                    'error': 'personnel_id is required'
                }, status=400)
            
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT mark_family_visited(%s, %s, %s)",
                    [family_id, personnel_id, enforce_bhw_assignment]
                )
                result = cursor.fetchone()
                family_id_returned = result[0] if result else None
            
            if family_id_returned:
                cache.delete(f'family_detail_{family_id}')
                cache.delete('household_families_*')
                
                return Response({
                    'success': True,
                    'family_id': family_id_returned,
                    'message': 'Family marked as visited'
                }, status=200)
            else:
                return Response({
                    'success': False,
                    'error': 'Failed to mark family as visited'
                }, status=500)
                
        except Exception as e:
            error_msg = str(e)
            
            if 'E8815' in error_msg:
                return Response({
                    'success': False,
                    'error': 'incomplete_gh',
                    'message': 'Cannot mark family as visited. Some members are missing General Health data for the current quarter.',
                    'details': error_msg
                }, status=400)
            elif 'E8814' in error_msg:
                return Response({
                    'success': False,
                    'error': 'no_active_quarter',
                    'message': 'No active quarter found. Please contact administrator.'
                }, status=400)
            elif 'E8813' in error_msg:
                return Response({
                    'success': False,
                    'error': 'not_assigned',
                    'message': 'You are not assigned to this area.'
                }, status=403)
            else:
                return Response({
                    'success': False,
                    'error': str(e)
                }, status=500)


class FamilyGHReadinessView(APIView):
    """Check if family is ready for visit (all members have GH data)"""
    
    def get(self, request, family_id):
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT family_general_health_readiness_current(%s)",
                    [family_id]
                )
                result = cursor.fetchone()
                
                if result and result[0]:
                   
                    readiness_data = result[0]

                    if isinstance(readiness_data, str):
                        readiness_data = json.loads(readiness_data)
                    
                    print(f" GH Readiness for family {family_id}: {readiness_data}")
                    
                    return Response({
                        'success': True,
                        'data': readiness_data
                    })
                else:
                    return Response({
                        'success': False,
                        'error': 'Could not check family readiness'
                    }, status=500)
                    
        except Exception as e:
            print(f" Error checking family readiness: {e}")
            import traceback
            traceback.print_exc()
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)


class FamilyUpdateView(APIView):
    """Update family - comprehensive family update endpoint"""
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    
    def put(self, request, family_id):
        try:
            # Get current family data first
            current_family = self._get_family_details(family_id)
            if not current_family:
                return Response({
                    'success': False,
                    'error': 'Family not found',
                    'user_message': 'The selected family could not be found.'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check if family can be updated (not visited)
            if current_family.get('is_visited', False):
                return Response({
                    'success': False,
                    'error': 'Family already visited',
                    'user_message': 'This family has already been visited and cannot be modified.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate required fields
            personnel_id = request.data.get('personnel_id')
            if not personnel_id:
                return Response({
                    'success': False,
                    'error': 'personnel_id is required',
                    'user_message': 'Authentication error. Please log in again.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Extract and validate update parameters
            update_params = self._extract_update_params(request.data, current_family)
            
            # Call the SQL function using the service
            result = HouseholdService.update_family(family_id, update_params, personnel_id)
            
            if result:
                return Response({
                    'success': True,
                    'family_id': result,
                    'message': 'Family updated successfully!'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'error': 'Update failed',
                    'user_message': 'Failed to update family. Please try again.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            error_message = str(e)
            user_message = self._get_user_friendly_error(error_message)
            
            return Response({
                'success': False,
                'error': error_message,
                'user_message': user_message
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_family_details(self, family_id):
        """Get current family details"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT family_id, is_visited, household_id, household_type_id,
                           family_head_id, respondent_id, respondent_rtf_id,
                           ip_status, ip_tribe, nhts_status,
                           water_source_type_id, toilet_facility_type_id, 
                           waste_management_type_id, waste_other_text
                    FROM family 
                    WHERE family_id = %s
                """, [family_id])
                
                result = cursor.fetchone()
                if result:
                    columns = [col[0] for col in cursor.description]
                    return dict(zip(columns, result))
                return None
        except Exception as e:
            print(f"Error getting family details: {e}")
            return None
    
    def _extract_update_params(self, data, current_family):
        """Extract and prepare update parameters"""
        params = {
            'household_id': int(data.get('household_id', current_family['household_id'])),
            'household_type_id': int(data.get('household_type_id', current_family['household_type_id'])),
        }
        
        # Optional fields - only include if provided
        if 'family_head_id' in data and data['family_head_id']:
            params['family_head_id'] = int(data['family_head_id'])
        
        if 'respondent_id' in data and data['respondent_id']:
            params['respondent_id'] = int(data['respondent_id'])
        
        # FIX: Map the correct field name for respondent RTF
        respondent_rtf_id = data.get('respondent_rtf_id') or data.get('respondent_relationship_to_fh_id')
        if respondent_rtf_id:
            params['respondent_rtf_id'] = int(respondent_rtf_id)
        
        if 'ip_status' in data:
            params['ip_status'] = str(data['ip_status']).lower() == 'true'
        
        if 'ip_tribe' in data:
            params['ip_tribe'] = data['ip_tribe'] or None
        
        if 'nhts_status' in data:
            params['nhts_status'] = str(data['nhts_status']).lower() == 'true'
        
        if 'water_source_type_id' in data and data['water_source_type_id']:
            params['water_source_type_id'] = int(data['water_source_type_id'])
        
        if 'toilet_facility_type_id' in data and data['toilet_facility_type_id']:
            params['toilet_facility_type_id'] = int(data['toilet_facility_type_id'])
        
        if 'waste_management_type_id' in data and data['waste_management_type_id']:
            params['waste_management_type_id'] = int(data['waste_management_type_id'])
        
        # Remove waste_other_text since you don't want it
        # if 'waste_other_text' in data:
        #     params['waste_other_text'] = data['waste_other_text'] or None
        
        # Add enforcement flag
        params['enforce_bhw_assignment'] = str(data.get('enforce_bhw_assignment', 'false')).lower() == 'true'
        
        return params
    
    def _get_user_friendly_error(self, error_message):
        """Convert SQL error codes to user-friendly messages"""
        
        # Family head validation errors
        if 'E7305B' in error_message:
            return "The selected family head is not a member of this family. Please add them as a member first."
        
        # General validation errors
        if 'E7301A' in error_message:
            return "Authentication error. Please log in again."
        
        if 'E7302' in error_message:
            return "Family not found. Please refresh and try again."
        
        if 'E7303' in error_message:
            return "Target household not found. Please refresh and try again."
        
        if 'E7304' in error_message:
            return "Invalid household type selected."
        
        if 'E7305' in error_message:
            return "Selected family head not found in the system."
        
        if 'E7306' in error_message:
            return "Selected respondent not found in the system."
        
        if 'E7307' in error_message or 'E7307H' in error_message or 'E7307J' in error_message:
            return "Invalid relationship configuration. Please check the relationships between family members."
        
        if 'E7308' in error_message:
            return "Invalid respondent relationship selected."
        
        # Environmental validation errors
        if 'E7309' in error_message:
            return "Invalid water source type selected."
        
        if 'E7310' in error_message:
            return "Invalid toilet facility type selected."
        
        if 'E7311' in error_message or 'E7316' in error_message:
            return "Invalid waste management type selected."
        
        # Assignment errors
        if 'E7318' in error_message or 'E7319' in error_message:
            return "You are not assigned to this area. Please contact your administrator."
        
        # Generic fallback
        return "Update failed. Please check your information and try again."


class ResidentRelationshipsView(APIView):
    """Get resident relationships"""
    
    def get(self, request, resident_id):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM get_resident_links(%s)", [resident_id])
                columns = [col[0] for col in cursor.description]
                row = cursor.fetchone()
                
                if row:
                    relationships = dict(zip(columns, row))
                    # Convert JSONB fields to Python objects
                    if relationships.get('guardians'):
                        relationships['guardians'] = relationships['guardians']
                    if relationships.get('children'):
                        relationships['children'] = relationships['children']
                    
                    return Response({
                        'success': True,
                        'data': relationships
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'success': True,
                        'data': {
                            'guardians': [],
                            'children': []
                        }
                    }, status=status.HTTP_200_OK)
                    
        except Exception as e:
            print(f"Error fetching relationships: {e}")
            return Response({
                'success': False,
                'message': 'Failed to fetch relationships'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ResidentLinkRelationView(APIView):
    """Link resident relationships"""
    
    def post(self, request):
        try:
            origin_resident_id = request.data.get('origin_resident_id')
            target_resident_id = request.data.get('target_resident_id')
            relationship_id = request.data.get('relationship_id')
            
            if not all([origin_resident_id, target_resident_id, relationship_id]):
                return Response({
                    'success': False,
                    'message': 'Missing required fields'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT link_resident_relation(%s, %s, %s)
                """, [origin_resident_id, target_resident_id, relationship_id])
                
                result = cursor.fetchone()
                relation_id = result[0] if result else None
                
                if relation_id:
                    return Response({
                        'success': True,
                        'relation_id': relation_id,
                        'message': 'Relationship linked successfully'
                    }, status=status.HTTP_201_CREATED)
                else:
                    return Response({
                        'success': False,
                        'message': 'Failed to link relationship'
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
        except Exception as e:
            error_message = str(e)
            
            # Handle specific error codes from your SQL function
            if 'E8106' in error_message:
                message = 'This person already has a linked mother'
            elif 'E8107' in error_message:
                message = 'This person already has a linked father'
            elif 'E8108' in error_message:
                message = 'This relationship already exists'
            elif 'E8111' in error_message:
                message = 'The target person already has a parent of this type'
            else:
                message = 'Failed to link relationship'
            
            return Response({
                'success': False,
                'message': message
            }, status=status.HTTP_400_BAD_REQUEST)

class ResidentUnlinkRelationView(APIView):
    """Unlink resident relationships"""
    
    def post(self, request):
        try:
            origin_resident_id = request.data.get('origin_resident_id')
            target_resident_id = request.data.get('target_resident_id')
            relationship_id = request.data.get('relationship_id')
            
            if not all([origin_resident_id, target_resident_id, relationship_id]):
                return Response({
                    'success': False,
                    'message': 'Missing required fields'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT unlink_resident_relation(%s, %s, %s)
                """, [origin_resident_id, target_resident_id, relationship_id])
                
                result = cursor.fetchone()
                closed_count = result[0] if result else 0
                
                if closed_count > 0:
                    return Response({
                        'success': True,
                        'closed_count': closed_count,
                        'message': 'Relationship removed successfully'
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'success': False,
                        'message': 'No active relationship found to remove'
                    }, status=status.HTTP_404_NOT_FOUND)
                    
        except Exception as e:
            return Response({
                'success': False,
                'message': 'Failed to remove relationship'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# child health

class SearchChildView(APIView):
    """
    Search for children (for form selection - child picker modal)
    """
    
    def get(self, request):
        query = request.GET.get('q', '').strip()
        
        # Require minimum query length
        if not query or len(query) < 2:
            return Response({
                'success': False,
                'error': 'Please enter at least 2 characters to search',
                'data': [],
                'count': 0
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            children = search_child(query)
            
            return Response({
                'success': True,
                'data': children,
                'count': len(children),
                'query': query,
                'message': f"Found {len(children)} {'child' if len(children) == 1 else 'children'} matching '{query}'"
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"Search child error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e),
                'data': [],
                'count': 0
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChildHealthRecordListView(APIView):
    """
    View ALL child health records (for list screen - index.tsx)
    """
    
    def get(self, request):
        query = request.GET.get('q', '').strip()
        limit = int(request.GET.get('limit', 50))
        offset = int(request.GET.get('offset', 0))
        
        # Validate pagination
        limit = min(max(limit, 1), 500)
        offset = max(offset, 0)
        
        try:
            records = view_all_child_health_records(
                query=query if query else None,
                limit=limit,
                offset=offset
            )
            
            return Response({
                'success': True,
                'data': records,
                'count': len(records),
                'query': query if query else 'all',
                'limit': limit,
                'offset': offset
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"View child health records error: {str(e)}")
            return Response({
                'success': False,
                'error': str(e),
                'data': [],
                'count': 0
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChildHealthRecordCreateView(APIView):
    """Create child health record"""
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    
    def post(self, request):
        try:
            personnel_id = request.data.get('personnel_id')
            if not personnel_id:
                return Response({
                    'success': False,
                    'message': 'Personnel ID required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = ChildHealthRecordCreateSerializer(
                data=request.data,
                context={'personnel_id': personnel_id}
            )
            
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'error': 'Validation failed',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            result = serializer.save()
            
            return Response({
                'success': True,
                'child_health_id': result['child_health_id'],
                'message': 'Child health record created successfully'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChildHealthRecordDetailView(APIView):
    """View specific child health record"""
    
    def get(self, request, child_health_id):
        try:
            record = view_specific_child_health_record(child_health_id)
            
            if not record:
                return Response({
                    'success': False,
                    'message': 'Child health record not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                'success': True,
                'data': record
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChildHealthRecordUpdateView(APIView):
    """Update child health record - only non-sensitive fields"""
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    
    def put(self, request, child_health_id):
        try:
            # Get personnel_id from request
            personnel_id = request.data.get('personnel_id')
            if not personnel_id:
                return Response({
                    'success': False,
                    'error': 'Personnel ID is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify record exists
            from .utils.database_helpers import view_specific_child_health_record
            try:
                existing_record = view_specific_child_health_record(child_health_id)
            except Exception as e:
                return Response({
                    'success': False,
                    'error': 'Child health record not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Validate and update
            serializer = ChildHealthRecordUpdateSerializer(
                data=request.data,
                context={'personnel_id': personnel_id}
            )
            
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'error': 'Validation failed',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Perform update
            serializer.update(child_health_id, serializer.validated_data)
            
            # Fetch updated record
            updated_record = view_specific_child_health_record(child_health_id)
            
            return Response({
                'success': True,
                'message': 'Child health record updated successfully',
                'data': updated_record
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            error_message = str(e)
            
            # Handle specific SQL error codes
            if 'P4301' in error_message:
                user_message = 'Child health record not found'
            elif 'P4302' in error_message:
                user_message = 'Invalid feeding method selected'
            elif 'P4303' in error_message:
                user_message = 'Invalid TT status selected'
            elif 'P4304' in error_message:
                user_message = 'Screening date is required when screening status is completed'
            else:
                user_message = 'Failed to update child health record'
            
            return Response({
                'success': False,
                'error': user_message,
                'technical_error': error_message
            }, status=status.HTTP_400_BAD_REQUEST)
        
# ========================================
# CHILD HEALTH - IMMUNIZATION ENDPOINTS
# ========================================
class ChildImmunizationListView(APIView):
    """Get child's immunization records"""
    
    def get(self, request, child_health_id):
        try:
            from .utils.database_helpers import view_specific_child_immunization_record
            
            records = view_specific_child_immunization_record(child_health_id)
            
            return Response({
                'success': True,
                'data': records
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class ChildImmunizationCreateView(APIView):
    """Add immunization record"""
    parser_classes = (JSONParser,)
    
    def post(self, request, child_health_id):
        try:
            personnel_id = request.data.get('personnel_id')
            if not personnel_id:
                return Response({
                    'success': False,
                    'error': 'Personnel ID required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = ChildImmunizationCreateSerializer(
                data=request.data,
                context={'personnel_id': personnel_id, 'child_health_id': child_health_id}
            )
            
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'error': 'Validation failed',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            immunization_id = serializer.save()
            
            return Response({
                'success': True,
                'message': 'Immunization added successfully',
                'immunization_id': immunization_id
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# ========================================
# CHILD HEALTH - SUPPLEMENTS ENDPOINTS
# ========================================
class ChildSupplementListView(APIView):
    """Get child's supplement records"""
    
    def get(self, request, child_health_id):
        try:
            from .utils.database_helpers import view_all_child_supplements
            
            records = view_all_child_supplements(child_health_id)
            
            return Response({
                'success': True,
                'data': records
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class ChildSupplementCreateView(APIView):
    """Add supplement record"""
    parser_classes = (JSONParser,)
    
    def post(self, request, child_health_id):
        try:
            personnel_id = request.data.get('personnel_id')
            if not personnel_id:
                return Response({
                    'success': False,
                    'error': 'Personnel ID required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = ChildSupplementCreateSerializer(
                data=request.data,
                context={'personnel_id': personnel_id, 'child_health_id': child_health_id}
            )
            
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'error': 'Validation failed',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer.save()
            
            return Response({
                'success': True,
                'message': 'Supplement added successfully'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# ========================================
# CHILD HEALTH - MEDICAL HISTORY ENDPOINTS
# ========================================
class ChildMedicalConditionListView(APIView):
    """Get child's medical conditions"""
    
    def get(self, request, child_health_id):
        try:
            from .utils.database_helpers import view_specific_child_all_medical_condition
            
            records = view_specific_child_all_medical_condition(child_health_id)
            
            return Response({
                'success': True,
                'data': records
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class ChildMedicalConditionCreateView(APIView):
    """Add medical condition"""
    parser_classes = (JSONParser,)
    
    def post(self, request, child_health_id):
        try:
            personnel_id = request.data.get('personnel_id')
            if not personnel_id:
                return Response({
                    'success': False,
                    'error': 'Personnel ID required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = ChildMedicalConditionCreateSerializer(
                data=request.data,
                context={'personnel_id': personnel_id, 'child_health_id': child_health_id}
            )
            
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'error': 'Validation failed',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            rmh_id = serializer.save()
            
            return Response({
                'success': True,
                'message': 'Medical condition added successfully',
                'rmh_id': rmh_id
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# ========================================
# CHILD HEALTH - SURGICAL HISTORY ENDPOINTS
# ========================================
class ChildSurgicalHistoryListView(APIView):
    """Get child's surgical history"""
    
    def get(self, request, child_health_id):
        try:
            from .utils.database_helpers import view_specific_child_all_surgical_history
            
            records = view_specific_child_all_surgical_history(child_health_id)
            
            return Response({
                'success': True,
                'data': records
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class ChildSurgicalHistoryCreateView(APIView):
    """Add surgical history"""
    parser_classes = (JSONParser,)
    
    def post(self, request, child_health_id):
        try:
            personnel_id = request.data.get('personnel_id')
            if not personnel_id:
                return Response({
                    'success': False,
                    'error': 'Personnel ID required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = ChildSurgicalHistoryCreateSerializer(
                data=request.data,
                context={'personnel_id': personnel_id, 'child_health_id': child_health_id}
            )
            
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'error': 'Validation failed',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            rsh_id = serializer.save()
            
            return Response({
                'success': True,
                'message': 'Surgical history added successfully',
                'rsh_id': rsh_id
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# ========================================
# CHILD HEALTH - GROWTH MONITORING ENDPOINTS
# ========================================
class ChildGrowthMonitoringListView(APIView):
    """Get child's growth monitoring records"""
    
    def get(self, request, child_health_id):
        try:
            from .utils.database_helpers import view_specific_child_all_growth_monitoring
            
            records = view_specific_child_all_growth_monitoring(child_health_id)
            
            # Get child info
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        r.first_name || ' ' || r.last_name as child_name
                    FROM Child_Health_Record chr
                    JOIN Resident r ON chr.child_id = r.resident_id
                    WHERE chr.child_health_id = %s
                """, [child_health_id])
                
                row = cursor.fetchone()
                child_name = row[0] if row else 'Child'
            
            print(f"📊 Returning {len(records)} growth records")
            print(f"Sample record: {records[0] if records else 'No records'}")  # Debug log
            
            return Response({
                'success': True,
                'data': records,
                'child_name': child_name,
                'count': len(records)
            })
            
        except Exception as e:
            print(f"❌ Failed to view growth monitoring: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class ChildGrowthMonitoringCreateView(APIView):
    """Add growth monitoring record"""
    parser_classes = (JSONParser,)
    
    def post(self, request, child_health_id):
        try:
            personnel_id = request.data.get('personnel_id')
            if not personnel_id:
                return Response({
                    'success': False,
                    'error': 'Personnel ID required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = ChildGrowthMonitoringCreateSerializer(
                data=request.data,
                context={'personnel_id': personnel_id, 'child_health_id': child_health_id}
            )
            
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'error': 'Validation failed',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            cgm_id = serializer.save()
            
            return Response({
                'success': True,
                'message': 'Growth monitoring record added successfully',
                'cgm_id': cgm_id
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# ========================================
# CHILD HEALTH - EXCLUSIVE BREASTFEED ENDPOINTS
# ========================================
class ChildBreastfeedTrackView(APIView):
    """Get child's exclusive breastfeed tracking"""
    
    def get(self, request, child_health_id):
        try:
            from .utils.database_helpers import view_specific_child_exclusive_breastfeed_track
            
            records = view_specific_child_exclusive_breastfeed_track(child_health_id)
            
            return Response({
                'success': True,
                'data': records
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class ChildBreastfeedCreateView(APIView):
    """Add exclusive breastfeed assessment"""
    parser_classes = (JSONParser,)
    
    def post(self, request, child_health_id):
        try:
            personnel_id = request.data.get('personnel_id')
            if not personnel_id:
                return Response({
                    'success': False,
                    'error': 'Personnel ID required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = ExclusiveBreastfeedCreateSerializer(
                data=request.data,
                context={'personnel_id': personnel_id, 'child_health_id': child_health_id}
            )
            
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'error': 'Validation failed',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            results = serializer.save()
            
            return Response({
                'success': True,
                'message': 'Breastfeed assessment added successfully',
                'data': results
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)