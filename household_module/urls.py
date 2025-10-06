from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views


# Router for ViewSets
router = DefaultRouter()
router.register(r'house-ownership-types', views.HouseOwnershipTypeViewSet)
router.register(r'household-types', views.HouseholdTypeViewSet)
router.register(r'water-source-types', views.WaterSourceTypeViewSet)
router.register(r'toilet-facility-types', views.ToiletFacilityTypeViewSet)
router.register(r'waste-management-types', views.WasteManagementTypeViewSet)
router.register(r'relationships', views.RelationshipViewSet)
router.register(r'house-types', views.HouseTypeViewSet)

app_name = 'household_module'

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # APIView endpoints
    path('households/', views.HouseholdListView.as_view(), name='household_list'),
    path('households/insert/', views.HouseholdInsertView.as_view(), name='household-insert'),
    path('search-resident/', views.ResidentSearchView.as_view(), name='search-resident'),
    # path('households/create/', views.HouseholdCreateView.as_view(), name='household-create'),
    path('households/<int:household_id>/families/create/', views.FamilyCreateView.as_view(), name='create_family'),
    # path("relationships/", views.RelationshipViewSet.as_view({"get": "list_relationships"}), name="household-relationships"),
]