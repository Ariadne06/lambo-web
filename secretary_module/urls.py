from django.urls import path
from . import views

app_name = 'secretary_module'

urlpatterns = [
    path('', views.secretary_dashboard, name='secretary_dashboard'),
    path('resident_list/', views.resident_list, name="resident_list"),
    path('household_list/', views.household_list, name="household_list"),
    path('moreHousehold/', views.moreHousehold),
    path('Addbusiness/', views.Addbusiness, name="Addbusiness"),
    path('businessDetail1/', views.businessDetail1),
    path('businessDetail2/', views.businessDetail2),
    path('businessDetail3/', views.businessDetail3),
    path("business_list/", views.business_list, name="business_list"),
    path("business_detail_json/<int:business_id>", views.business_detail_json, name="business_detail_json"),
    path("businesses/<int:business_id>/update", views.business_update, name="business_update"),
    path("businesses/<int:business_id>/close", views.business_close, name="business_close"),
    path('add_certificate/', views.add_certificate, name="add_certificate"),
    path('manageCert1/', views.manageCert1),
    path('manageCert2/', views.manageCert2),
    path('applications/', views.applications, name="applications"),
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
]
