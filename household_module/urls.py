from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
import django.contrib.admin as admin

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
router.register(r'quarters', views.QuarterViewSet)
router.register(r'family-relationships', views.ResidentFamilyRelationshipViewSet)
router.register(r'feeding-methods', views.FeedingMethodViewSet)
router.register(r'months', views.MonthViewSet)
router.register(r'tt-statuses', views.TTStatusViewSet)
router.register(r'vaccine-types', views.VaccineTypeViewSet)
router.register(r'dose-types', views.DoseTypeViewSet)
router.register(r'supplements', views.SupplementsViewSet)


app_name = 'household_module'

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    path('admin/', admin.site.urls),
    
    # APIView endpoints
    path('households/', views.HouseholdListView.as_view(), name='household_list'),
    path('households/insert/', views.HouseholdInsertView.as_view(), name='household-insert'),
    path('search-resident/', views.ResidentSearchView.as_view(), name='search-resident'),
    # path('households/create/', views.HouseholdCreateView.as_view(), name='household-create'),
    path('households/<int:household_id>/families/create/', views.FamilyCreateView.as_view(), name='create_family'),
    # path("relationships/", views.RelationshipViewSet.as_view({"get": "list_relationships"}), name="household-relationships"),
    path('households/<int:household_id>/details/', views.HouseholdDetailView.as_view(), name='household-detail'),
    path('households/<int:household_id>/families/', views.HouseholdFamiliesView.as_view(), name='household-families'),
    path('families/<int:family_id>/details/', views.FamilyDetailView.as_view(), name='family-detail'),
    path('families/<int:family_id>/members/', views.FamilyMembersListView.as_view(), name='family-members-list'),
    path('families/<int:family_id>/members/add/', views.FamilyMemberCreateView.as_view(), name='add-family-member'),
    path('family-members/<int:family_member_id>/', views.FamilyMemberDetailView.as_view(), name='family-member-detail'),
    path('family-members/<int:family_member_id>/general-health/create/', views.GeneralHealthCreateView.as_view(), name='create-general-health'),
    path('family-members/<int:family_member_id>/general-health/update/', views.GeneralHealthUpdateView.as_view(), name='update-general-health'),
    path('households/<int:household_id>/mark-visited/', views.HouseholdMarkVisitedView.as_view(), name='mark-household-visited'),
    path('families/<int:family_id>/mark-visited/', views.FamilyMarkVisitedView.as_view(), name='mark-family-visited'),
    path('families/<int:family_id>/gh-readiness/', views.FamilyGHReadinessView.as_view(), name='family-gh-readiness'),
    path('households/<int:household_id>/update/', views.HouseholdUpdateView.as_view(), name='household-update'),
    path('families/<int:family_id>/update/', views.FamilyUpdateView.as_view(), name='family-update'),
    path('resident/<int:resident_id>/relationships/', views.ResidentRelationshipsView.as_view(), name='resident-relationships'),
    path('resident/link-relation/', views.ResidentLinkRelationView.as_view(), name='link-resident-relation'),
    path('resident/unlink-relation/', views.ResidentUnlinkRelationView.as_view(), name='unlink-resident-relation'),
    path('search-child/', views.SearchChildView.as_view(), name='search-child'),
    path('child-health-records/create/', views.ChildHealthRecordCreateView.as_view(), name='create-child-health-record'),
    path('child-health-records/<int:child_health_id>/', views.ChildHealthRecordDetailView.as_view(), name='child-health-record-detail'),
    path('child-health-records/<int:child_health_id>/update/', views.ChildHealthRecordUpdateView.as_view(), name='update-child-health-record'),
]