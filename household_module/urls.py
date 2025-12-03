from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
import django.contrib.admin as admin
from .views import DiseaseTypeListView, TestTypeListView

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
router.register(r'disease-types', views.DiseaseTypeViewSet)
router.register(r'trimesters', views.TrimesterViewSet)
router.register(r'test-types', views.TestTypeViewSet)
router.register(r'supplement-types', views.SupplementTypeViewSet)
router.register(r'deworming-types', views.DewormingTypeViewSet)
router.register(r'outcome-types', views.OutcomeTypeViewSet)
router.register(r'delivery-types', views.DeliveryTypeViewSet)
router.register(r'place-delivery-types', views.PlaceDeliveryTypeViewSet)
router.register(r'ownership-types', views.OwnershipTypeViewSet)
router.register(r'birth-attendants', views.BirthAttendantViewSet)
router.register(r'record-statuses', views.RecordStatusViewSet)

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
    path('child-health-records/', views.ChildHealthRecordListView.as_view(), name='child-health-records-list'),
    path('child-health-records/create/', views.ChildHealthRecordCreateView.as_view(), name='create-child-health-record'),
    path('child-health-records/<int:child_health_id>/', views.ChildHealthRecordDetailView.as_view(), name='child-health-record-detail'),
    path('child-health-records/<int:child_health_id>/update/', views.ChildHealthRecordUpdateView.as_view(), name='update-child-health-record'),


path("bhw-dashboard/", views.bhw_dashboard_view, name="bhw-dashboard"),

    # CHILD HEALTH - IMMUNIZATION
    path(
    'child-health-records/<int:child_health_id>/immunizations/',
    views.ChildImmunizationListView.as_view(),
    name='child-immunizations-list',
),
path(
    'child-health-records/<int:child_health_id>/immunizations/add/',
    views.ChildImmunizationCreateView.as_view(),
    name='child-immunizations-add',
),
    
    # CHILD HEALTH - SUPPLEMENTS
    path('child-health-records/<int:child_health_id>/supplements/', 
         views.ChildSupplementListView.as_view(), 
         name='child-supplements-list'),
    path('child-health-records/<int:child_health_id>/supplements/add/', 
         views.ChildSupplementCreateView.as_view(), 
         name='child-supplements-add'),
    
    # CHILD HEALTH - MEDICAL CONDITIONS
     path('child-health-records/<int:child_health_id>/medical-conditions/', 
          views.ChildMedicalConditionListView.as_view(), 
          name='child-medical-conditions-list'),
     path('child-health-records/<int:child_health_id>/medical-conditions/add/', 
          views.ChildMedicalConditionCreateView.as_view(), 
          name='child-medical-conditions-add'),

     # CHILD HEALTH - SURGICAL HISTORY
     path('child-health-records/<int:child_health_id>/surgical-history/', 
          views.ChildSurgicalHistoryListView.as_view(), 
          name='child-surgical-history-list'),
     path('child-health-records/<int:child_health_id>/surgical-history/add/', 
          views.ChildSurgicalHistoryCreateView.as_view(), 
          name='child-surgical-history-add'),
     
    # CHILD HEALTH - GROWTH MONITORING
     path('child-health-records/<int:child_health_id>/growth-monitoring/', 
          views.ChildGrowthMonitoringListView.as_view(), 
          name='child-growth-monitoring-list'),
     path('child-health-records/<int:child_health_id>/growth-monitoring/add/', 
          views.ChildGrowthMonitoringCreateView.as_view(), 
          name='child-growth-monitoring-add'),
    
    # CHILD HEALTH - EXCLUSIVE BREASTFEED
     path('child-health-records/<int:child_health_id>/exclusive-breastfeed/', 
         views.ExclusiveBreastfeedListView.as_view(), 
         name='child-exclusive-breastfeed-list'),
     path('child-health-records/<int:child_health_id>/exclusive-breastfeed/add/', 
          views.ExclusiveBreastfeedCreateView.as_view(), 
          name='child-exclusive-breastfeed-add'),
     
     # MONTHS LIST
     path('months/', 
          views.MonthsListView.as_view(), 
          name='months-list'),

     # GENERAL HEALTH
     path('general-health/', 
         views.GeneralHealthListView.as_view(), 
         name='general-health-list'),
     path('general-health/<int:family_member_id>/', 
         views.GeneralHealthDetailView.as_view(), 
         name='general-health-detail'),
     
     # ========================================
     # MATERNAL HEALTH - SEARCH & CRUD
     # ========================================
     path('search-mother/', views.SearchMotherView.as_view(), name='search-mother'),
     path('maternal-health-records/', views.MaternalHealthRecordListView.as_view(), name='maternal-health-records-list'),
     path('maternal-health-records/create/', views.MaternalHealthRecordCreateView.as_view(), name='maternal-health-records-create'),
     path('maternal-health-records/<int:maternal_health_id>/', views.MaternalHealthRecordDetailView.as_view(), name='maternal-health-record-detail'),
     
     path('maternal-health-records/<int:maternal_health_id>/update/', 
     views.MaternalHealthRecordUpdateView.as_view(), 
     name='maternal-health-record-update'),


     path('maternal-health-records/<int:maternal_health_id>/update-status/', 
     views.MaternalHealthRecordStatusUpdateView.as_view(), 
     name='maternal-health-record-status-update'),

     # MATERNAL HEALTH - OBSTETRICAL HISTORY
     path(
          'maternal-health-records/<int:maternal_health_id>/obstetrical-history/',
          views.MaternalObstetricalHistoryListView.as_view(),
          name='maternal-obstetrical-history-list'
     ),
     path(
        'maternal-health-records/<int:maternal_health_id>/obstetrical-history/create/',
        views.ObstetricalHistoryCreateView.as_view(),
        name='obstetrical-history-create'
    ),
     
     # ========================================
     # MEDICAL/SURGICAL HISTORY
     # ========================================
     path('maternal-health-records/<int:maternal_health_id>/medical-conditions/', 
          views.MaternalMedicalConditionListView.as_view(), 
          name='maternal-medical-conditions-list'),
     path('maternal-health-records/<int:maternal_health_id>/medical-conditions/add/', 
          views.MaternalMedicalConditionCreateView.as_view(), 
          name='maternal-medical-conditions-add'),
     
     path('maternal-health-records/<int:maternal_health_id>/surgical-history/', 
          views.MaternalSurgicalHistoryListView.as_view(), 
          name='maternal-surgical-history-list'),
     path('maternal-health-records/<int:maternal_health_id>/surgical-history/add/', 
          views.MaternalSurgicalHistoryCreateView.as_view(), 
          name='maternal-surgical-history-add'),
     
     # ========================================
     # IMMUNIZATION
     # ========================================
     path(
        'maternal-health-records/<int:maternal_health_id>/immunization/track/',
        views.MaternalImmunizationTrackView.as_view(),
        name='maternal-immunization-track'),
     path(
        'maternal-health-records/<int:maternal_health_id>/immunization/add/',
        views.MaternalImmunizationCreateView.as_view(),
        name='maternal-immunization-create'
     ),
     
     # ========================================
     # DISEASE SURVEILLANCE
     # ========================================
     path('maternal-health-records/<int:maternal_health_id>/disease-surveillance/', 
          views.DiseaseScreenListView.as_view(), 
          name='disease-surveillance-list'),
     path('maternal-health-records/<int:maternal_health_id>/disease-surveillance/add/', 
          views.DiseaseScreenCreateView.as_view(), 
          name='disease-surveillance-add'),

          path("disease-types/", DiseaseTypeListView.as_view()),

     
     # ========================================
     # LABORATORY SCREENING
     # ========================================
     path('maternal-health-records/<int:maternal_health_id>/laboratory-screening/', 
         views.LabScreeningListView.as_view(), 
         name='maternal-lab-screening-list'),
     path('maternal-health-records/<int:maternal_health_id>/lab-screening/add/', 
          views.LabScreeningCreateView.as_view(), 
          name='lab-screening-add'),

    path("test-types/", TestTypeListView.as_view()),

    path('residents/', views.get_resident_list, name='get_residents'),
  


     
     # ========================================
     # CHECKUP RECORDS
     # ========================================
      path(
        'maternal-health-records/<int:maternal_health_id>/checkups/', 
        views.CheckupRecordListView.as_view(), 
        name='checkups-list'
     ),
     path(
          'maternal-health-records/<int:maternal_health_id>/checkups/add/', 
          views.CheckupRecordCreateView.as_view(), 
          name='checkups-add'
     ),
     path(
          'maternal-health-records/<int:maternal_health_id>/checkups/track/', 
          views.CheckupRecordTrackView.as_view(), 
          name='checkups-track'
     ),

     path('maternal-health-records/<int:maternal_health_id>/checkups/<int:checkup_id>/update/', 
     views.CheckupRecordUpdateView.as_view(), 
     name='maternal_checkup_update'),

     # ========================================
     # SUPPLEMENTS
     # ========================================
     path('maternal-health-records/<int:maternal_health_id>/supplements/', 
          views.MaternalSupplementListView.as_view(), 
          name='maternal-supplements-list'),
     path('maternal-health-records/<int:maternal_health_id>/supplements/add/', 
          views.MaternalSupplementCreateView.as_view(), 
          name='maternal-supplements-add'),
     
     # ========================================
     # DEWORMING
     # ========================================
     path('maternal-health-records/<int:maternal_health_id>/deworming/', 
          views.DewormingListView.as_view(), 
          name='maternal-deworming-list'),
     path('maternal-health-records/<int:maternal_health_id>/deworming/add/', 
          views.DewormingCreateView.as_view(), 
          name='maternal-deworming-add'),
     
     # ========================================
     # PREGNANCY OUTCOME
     # ========================================
     path('maternal-health-records/<int:maternal_health_id>/delivery-outcome/', 
         views.DeliveryOutcomeView.as_view(), 
         name='delivery-outcome'),
     path('maternal-health-records/<int:maternal_health_id>/delivery-outcome/add/', 
         views.DeliveryOutcomeCreateView.as_view(), 
         name='delivery-outcome-add'),
     
     # ========================================
     # POSTPARTUM
     # ========================================
     path('maternal-health-records/<int:maternal_health_id>/postpartum/', 
         views.PostpartumVisitListView.as_view(), 
         name='postpartum-list'),
     path('maternal-health-records/<int:maternal_health_id>/postpartum/add/', 
         views.PostpartumVisitCreateView.as_view(), 
         name='postpartum-add'),
     
     # ========================================
     # BHW DASHBOARD
     # ========================================
     path('bhw/dashboard/', 
          views.BHWDashboardView.as_view(), 
          name='bhw-dashboard'),

     # Immunization Schedule
     path(
        'child-immunization-schedule/',
        views.ChildImmunizationScheduleListView.as_view(),
        name='child-immunization-schedule-list'
    ),
]