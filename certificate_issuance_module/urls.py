from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'document-types', views.DocumentTypeViewSet)
router.register(r'clearance-purposes', views.ClearancePurposeViewSet)

app_name = 'certificate_issuance_module'

urlpatterns = [
    path('', include(router.urls)),
]