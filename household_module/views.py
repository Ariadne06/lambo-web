from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from .models import HouseType, Household
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import connection
from .models import HouseOwnershipType, HouseholdType, WaterSourceType, ToiletFacilityType, WasteManagementType, RelationshipToHouseholdHead
from .serializers import (
    HouseOwnershipTypeSerializer, HouseTypeSerializer, HouseholdTypeSerializer, WaterSourceTypeSerializer,
    ToiletFacilityTypeSerializer, WasteManagementTypeSerializer,
    HouseholdInsertSerializer, FamilyCreateSerializer, RelationshipToHouseholdHeadSerializer
)
from .services.household_service import HouseholdService


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

class HouseholdListView(APIView):
    """Get all households """
    
    def get(self, request):
        print("GET /household_api/households/ called")
        
        try:
            # Get ALL households 
            households_data = HouseholdService.get_all_households()
            
            print(f"Retrieved {len(households_data)} households")
            
            # Return raw data (let frontend filter)
            return Response({
                'success': True,
                'message': 'Households retrieved successfully',
                'data': households_data,
                'count': len(households_data)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"Error retrieving households: {e}")
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