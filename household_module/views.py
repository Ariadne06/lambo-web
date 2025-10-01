from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from .models import Household
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import DatabaseError, IntegrityError
from .models import HouseOwnershipType, HouseholdType, WaterSourceType, ToiletFacilityType, WasteManagementType
from .serializers import (
    HouseOwnershipTypeSerializer, HouseholdTypeSerializer, WaterSourceTypeSerializer,
    ToiletFacilityTypeSerializer, WasteManagementTypeSerializer,
    HouseholdCreateSerializer, FamilyCreateSerializer, HouseholdListSerializer,
    RelationshipListSerializer, HouseholdInsertSerializer
)
from .services.household_service import HouseholdService
from .utils.database_helpers import get_lookup_data

# ViewSets for lookup data - following your exact pattern
class HouseOwnershipTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HouseOwnershipType.objects.all()
    serializer_class = HouseOwnershipTypeSerializer

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

# APIViews for complex operations
class HouseholdListView(APIView):
    """Get households list - following your MobileLoginView pattern"""
    
    def get(self, request):
        print("GET /api/households/ called")
        
        try:
            # Get personnel_id from authenticated user
            personnel_id = request.user.personnel.personnel_id
            print(f"Fetching households for personnel: {personnel_id}")
            
            households = HouseholdService.get_households_for_personnel(personnel_id)
            
            # Convert to list of dicts for serializer
            household_data = []
            for row in households:
                household_data.append({
                    'household_id': row[0],
                    'household_code': row[1], 
                    'house_number': row[2],
                    'household_head_name': row[3],
                    'respondent_name': row[4],
                    'full_address': row[5],
                    'is_visited': row[6],
                    'family_count': row[7],
                    'visited_families': row[8],
                    'quarter': row[9],
                    'year': row[10]
                })
            
            serializer = HouseholdListSerializer(household_data, many=True)
            
            return Response({
                'success': True,
                'data': serializer.data
            })
            
        except Exception as e:
            print(f"Error fetching households: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class HouseholdCreateView(APIView):
    """Create household - following your ResidentRegistrationView pattern"""
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request):
        print("POST /api/households/create/ called")
        print(f"Request data keys: {list(request.data.keys())}")
        
        try:
            serializer = HouseholdCreateSerializer(data=request.data, context={'request': request})
            
            if not serializer.is_valid():
                print("Serializer is not valid")
                print("Errors:", serializer.errors)
                return Response({
                    'success': False,
                    'error': 'Validation failed',
                    'details': serializer.errors
                }, status=400)
            
            print("Serializer is valid")
            household = serializer.save()
            
            print(f"Household creation successful for ID: {household.household_id}")
            
            return Response({
                'success': True,
                'household_id': household.household_id,
                'message': 'Household created successfully'
            }, status=201)
            
        except Exception as e:
            print(f"Unexpected error in household creation: {e}")
            return Response({
                'success': False,
                'error': 'Household creation failed. Please try again.',
                'error_code': 'HOUSEHOLD_CREATION_ERROR'
            }, status=500)

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

class LookupDataView(APIView):
    """Get lookup data - following your pattern"""
    
    def get(self, request):
        print("GET /api/household-lookup-data/ called")
        
        try:
            data = get_lookup_data()
            
            return Response({
                'success': True,
                'data': data
            })
            
        except Exception as e:
            print(f"Error fetching lookup data: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
class RelationshipViewSet(ViewSet):
    def list(self, request):
        s = RelationshipListSerializer(instance={})  # <-- important
        return Response(s.data)
    
class InsertHouseholdView(APIView):
    parser_classes = (JSONParser,)

    def get(self, request):
        # lets DRF render the browsable page
        return Response({"detail": "POST to this URL to insert a household."})

    def post(self, request):
        s = HouseholdInsertSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        instance = s.save()  # calls your sp_insert_household via serializer.create()
        return Response({"success": True, **instance}, status=201)
    
    
