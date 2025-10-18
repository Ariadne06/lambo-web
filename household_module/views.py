from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from .models import HouseType, Household, PhilhealthCategory
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import connection
from .models import HouseOwnershipType, HouseholdType, WaterSourceType, ToiletFacilityType, WasteManagementType, RelationshipToHouseholdHead, NutritionStatus, MedicalHistoryType, Class, FPMethod, FPStatus
from .serializers import (
    FamilyMemberCreateSerializer, HouseOwnershipTypeSerializer, HouseTypeSerializer, HouseholdTypeSerializer, NutritionStatusSerializer, WaterSourceTypeSerializer,
    ToiletFacilityTypeSerializer, WasteManagementTypeSerializer,
    HouseholdInsertSerializer, FamilyCreateSerializer, RelationshipToHouseholdHeadSerializer, PhilhealthCategorySerializer, MedicalHistoryTypeSerializer, ClassSerializer, 
    FPMethodSerializer, FPStatusSerializer, GeneralHealthCreateSerializer, GeneralHealthUpdateSerializer
)
from .services.household_service import HouseholdService
from django.core.cache import cache
from django.views.decorators.cache import cache_page
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


class HouseholdListView(APIView):
    """Optimized household list with pagination and caching"""
    
    def get(self, request):
        print("GET /household_api/households/ called")
        
        try:
            # ✅ Get pagination parameters
            limit = int(request.GET.get('limit', 50))  # Default 50 households
            offset = int(request.GET.get('offset', 0))
            quarter_id = request.GET.get('quarter_id', None)
            
            #  Create cache key based on params
            cache_key = f'households_list_{quarter_id}_{limit}_{offset}'
            
            #  Try to get from cache first (cache for 5 minutes)
            cached_data = cache.get(cache_key)
            if cached_data:
                print(f"✓ Returning cached data ({len(cached_data)} households)")
                return Response({
                    'success': True,
                    'message': 'Households retrieved from cache',
                    'data': cached_data,
                    'count': len(cached_data),
                    'has_more': len(cached_data) == limit  # Indicate if there's more data
                }, status=status.HTTP_200_OK)
            
            #  Optimized query with pagination
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM get_all_households(
                        %s,  -- bhw_id (NULL for all)
                        %s,  -- quarter_id
                        NULL,  -- sitio_id (NULL for all)
                        'all',  -- filter (all/visited/not_visited)
                        NULL,  -- search_query
                        %s,  -- limit
                        %s   -- offset
                    )
                """, [None, quarter_id, limit, offset])
                
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                
                households = []
                for row in rows:
                    household_dict = dict(zip(columns, row))
                    
                    # Convert dates to ISO format
                    if household_dict.get('date_visited'):
                        household_dict['date_visited'] = household_dict['date_visited'].isoformat()
                    if household_dict.get('created_at'):
                        household_dict['created_at'] = household_dict['created_at'].isoformat()
                    if household_dict.get('updated_at'):
                        household_dict['updated_at'] = household_dict['updated_at'].isoformat()
                    
                    households.append(household_dict)
            
            #  Cache the result for 5 minutes
            cache.set(cache_key, households, 300)  # 300 seconds = 5 minutes
            
            print(f"✓ Retrieved {len(households)} households from database")
            
            return Response({
                'success': True,
                'message': 'Households retrieved successfully',
                'data': households,
                'count': len(households),
                'has_more': len(households) == limit,
                'limit': limit,
                'offset': offset
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"✗ Error retrieving households: {e}")
            import traceback
            traceback.print_exc()
            
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
                print("Family serializer is not valid")
                print("Errors:", serializer.errors)
                return Response({
                    'success': False,
                    'error': 'Validation failed',
                    'details': serializer.errors
                }, status=400)
            
            print("Family serializer is valid")
            family = serializer.save()
            
            print(f"Family creation successful for ID: {family.family_id}")
            
            return Response({
                'success': True,
                'family_id': family.family_id,
                'message': 'Family created successfully'
            }, status=201)
            
        except Exception as e:
            print(f"Unexpected error in family creation: {e}")
            return Response({
                'success': False,
                'error': 'Family creation failed. Please try again.',
                'error_code': 'FAMILY_CREATION_ERROR'
            }, status=500)

    
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
            # Check cache first
            cache_key = f'household_detail_{household_id}'
            cached_data = cache.get(cache_key)
            
            if cached_data:
                return Response({
                    'success': True,
                    'data': cached_data
                })
            
            # Fetch from database
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM get_specific_household(%s, NULL)", [household_id])
                columns = [col[0] for col in cursor.description]
                row = cursor.fetchone()
                
                if not row:
                    return Response({
                        'success': False,
                        'message': 'Household not found'
                    }, status=404)
                
                data = dict(zip(columns, row))
                
                # Convert dates
                if data.get('date_visited'):
                    data['date_visited'] = data['date_visited'].isoformat()
                if data.get('created_at'):
                    data['created_at'] = data['created_at'].isoformat()
                if data.get('updated_at'):
                    data['updated_at'] = data['updated_at'].isoformat()
                
                # Cache for 10 minutes
                cache.set(cache_key, data, 600)
                
                return Response({
                    'success': True,
                    'data': data
                })
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
            # Check cache
            cache_key = f'household_families_{household_id}'
            cached_data = cache.get(cache_key)
            
            if cached_data:
                return Response({
                    'success': True,
                    'data': cached_data,
                    'count': len(cached_data)
                })
            
            # Fetch from database
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM get_family_summaries_per_household(%s, NULL)",
                    [household_id]
                )
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                
                families = [dict(zip(columns, row)) for row in rows]
                
                # Cache for 10 minutes
                cache.set(cache_key, families, 600)
                
                return Response({
                    'success': True,
                    'data': families,
                    'count': len(families)
                })
        except Exception as e:
            print(f"Error: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)

class FamilyDetailView(APIView):
    """Get specific family details"""
    
    def get(self, request, family_id):
        try:
            # Check cache first
            cache_key = f'family_detail_{family_id}'
            cached_data = cache.get(cache_key)
            
            if cached_data:
                return Response({
                    'success': True,
                    'data': cached_data
                })
            
            #  Fetch from database using your SQL function
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
                
                # Parse members_json if it's a string
                if isinstance(data.get('members_json'), str):
                    try:
                        data['members_json'] = json.loads(data['members_json'])
                    except:
                        data['members_json'] = []
                
                # Format dates
                if data.get('date_visited'):
                    data['date_visited'] = data['date_visited'].isoformat()
                if data.get('updated_at'):
                    data['updated_at'] = data['updated_at'].isoformat()
                if data.get('date_created'):
                    data['date_created'] = data['date_created'].isoformat()
                
                # Cache for 10 minutes
                cache.set(cache_key, data, 600)
                
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
                    
                    #  CRITICAL FIX: Check if GH record actually exists
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
                            
                            # Female-specific fields
                            if data.get('sex', '').lower() == 'female':
                                data['gh_last_menstrual_period'] = gh_data.get('last_menstrual_period')
                                data['gh_fp_method_yn'] = gh_data.get('fp_method_yn')
                                data['gh_fp_method_id'] = gh_data.get('fp_method_id')
                                data['gh_fp_method_name'] = gh_data.get('fp_method_name')
                                data['gh_fp_status_id'] = gh_data.get('fp_status_id')
                                data['gh_fp_status_name'] = gh_data.get('fp_status_name')
                            
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
                
                # ✅ Log the response for debugging
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