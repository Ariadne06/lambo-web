from django.urls import path
from . import views

app_name = 'secretary_module'

urlpatterns = [
    path('', views.secretary_dashboard, name='secretary_dashboard'),
    path('resident_list/', views.resident_list, name="resident_list"),
    path('household_list/', views.household_list, name="household_list"),
    path('sec_householdView/', views.sec_householdView, name="sec_householdView"),
    path("api/general-health/", views.general_health_get_api, name="generalHealthGetApi"),
    path('api/resident-links', views.resident_links_list_api, name='sec_residentLinksListApi'),
    path('Addbusiness/', views.Addbusiness, name="Addbusiness"),
    path('businessDetail1/', views.businessDetail1),
    path('businessDetail2/', views.businessDetail2),
    path('businessDetail3/', views.businessDetail3),
    path("business_list/", views.business_list, name="business_list"),
    path("business_detail_json/<int:business_id>", views.business_detail_json, name="business_detail_json"),
    path("businesses/<int:business_id>/update", views.business_update, name="business_update"),
    path("business/<int:business_id>/close/", views.business_close, name="business_close"),
    path('applications/create/', views.add_certificate, name='create_application'),
    path('applications/submit/', views.submit_business_application, name='submit_business_application'),
    path('manageCert1/', views.manageCert1, name='manageCert1'),
    path('manageCert2/', views.manageCert2, name='manageCert2'),
    path('applications/', views.applications, name="applications"),
    # HTML detail page and JSON detail endpoint
    path('applications/<int:application_id>/', views.application_detail, name='application_detail'),
    path('applications/<int:application_id>/detail/', views.application_detail_json, name='application_detail_json'),
    path('applications/<int:application_id>/for-payment/', views.set_application_to_for_payment, name='set_application_to_for_payment'),
    path('applications/<int:application_id>/completed/', views.set_application_to_completed, name='set_application_to_completed'),
    path('applications/<int:application_id>/cancel/', views.cancel_application, name='cancel_application'),
    path('applications/<int:application_id>/print/', views.print_application, name='print_application'),
    path('applications/<int:application_id>/print/pdf/', views.print_application_pdf, name='print_application_pdf'),
    path('announcement/', views.announcement, name="announcement"),
    path('approval/', views.approval, name="approval"),
    path("approval/get-doc-url", views.get_doc_url, name="approval_get_doc_url"),
    path("approval/decide", views.approval_decide, name="approval_decide"),

    # Business fee pages
    path('businessFee/', views.businessFee, name='business_fee'),
    path('businessFee/update/', views.business_fee_update, name='business_fee_update'),
    path('amusement/', views.amusement, name='amusement'),
    path('amusement/update/', views.amusement_update, name='amusement_update'),
    path("otherClearances/", views.other_clearances, name="other_clearances"),
    path("otherClearances/update/", views.other_clearances_update, name="other_clearances_update"),
    path("taxPenalties/", views.tax_penalties, name="tax_penalties"),
    path("taxPenalties/update/", views.tax_penalties_update, name="tax_penalties_update"),

    # Dynamic AJAX endpoints for the Create Application (walk-in) UI
    path('applications/search/', views.application_search, name='application_search'),
    path('applications/preview/', views.preview_business_clearance, name='preview_business_clearance'),
    path('applications/preview/barangay/', views.preview_barangay_clearance, name='preview_barangay_clearance'),
    path('applications/reprint/', views.create_reprint_business_clearance, name='create_reprint_business_clearance'),
]
