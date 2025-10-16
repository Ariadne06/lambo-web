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
router.register(r'philhealth-categories', views.PhilhealthCategoryViewSet)
router.register(r'nutrition-statuses', views.NutritionStatusViewSet)
router.register(r'medical-history-types', views.MedicalHistoryTypeViewSet)
router.register(r'classes', views.ClassViewSet)
router.register(r'fp-methods', views.FPMethodViewSet)
router.register(r'fp-statuses', views.FPStatusViewSet)
router.register(r'relationships', views.RelationshipViewSet, basename="relationships")
router.register(r'house-ownerships', views.HouseOwnershipViewSet, basename="house-ownerships")
router.register(r'house-types', views.HouseTypeViewSet, basename="house-types")
router.register(r'sitios', views.SitioViewSet, basename="sitios")

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
    path('household-lookup-data/', views.LookupDataView.as_view(), name='lookup_data'),
    path("residents/search/", views.ResidentSearchView.as_view(), name="resident-search"),
    # path("relationships/", views.RelationshipViewSet.as_view({"get": "list_relationships"}), name="household-relationships"),
    path('households/<int:household_id>/details/', views.HouseholdDetailView.as_view(), name='household-detail'),
    path('households/<int:household_id>/families/', views.HouseholdFamiliesView.as_view(), name='household-families'),
    path('families/<int:family_id>/details/', views.FamilyDetailView.as_view(), name='family-detail'),
    path('families/<int:family_id>/members/', views.FamilyMembersListView.as_view(), name='family-members-list'),
    path('families/<int:family_id>/members/add/', views.FamilyMemberCreateView.as_view(), name='add-family-member'),
    path('family-members/<int:family_member_id>/', views.FamilyMemberDetailView.as_view(), name='family-member-detail'),
    path('family-members/<int:family_member_id>/general-health/create/', views.GeneralHealthCreateView.as_view(), name='create-general-health'),
]