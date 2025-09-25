# Certificate Issuance Module Documentation

## Overview

The `certificate_issuance_module` is a Django module following the exact same architectural pattern as the `household_module`. It provides APIs for certificate application management including document selection, fee calculation, application submission, and certificate issuance processing.

## Module Structure

```
certificate_issuance_module/
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── serializers.py
├── tests.py
├── urls.py
├── views.py
├── migrations/
│   └── __init__.py
├── services/
│   └── certificate_service.py
└── utils/
    └── database_helpers.py
```

## Architecture Pattern (Based on household_module)

### 1. Models (models.py)

- **DocumentType**: Available certificate types
- **ClearancePurpose**: Clearance purposes with fees
- **ApplicationStatus**: Status types (Pending, Approved, Rejected)
- **CertificateApplication**: Main application records
- **CertificateIssuance**: Issued certificate records

All models use `managed = False` (database-first approach like household_module).

### 2. Database Helpers (utils/database_helpers.py)

Direct database interaction functions using PostgreSQL stored procedures:

- `get_document_types()` - Get available document types
- `get_clearance_purposes()` - Get purposes with fees
- `calculate_certificate_fee()` - Calculate application fee
- `create_certificate_application()` - Submit application
- `get_resident_applications()` - Get user applications
- `get_application_details()` - Get detailed application info
- `get_pending_applications()` - Get pending applications for personnel
- `process_application()` - Approve/reject applications
- `issue_certificate()` - Issue certificates

### 3. Service Layer (services/certificate_service.py)

Business logic wrapper following `HouseholdService` pattern:

- Simple static methods that wrap database helpers
- Consistent error handling and logging
- Separation of concerns from views

### 4. Serializers (serializers.py)

Django REST Framework serializers following household_module pattern:

- **Lookup serializers**: DocumentType, ClearancePurpose, ApplicationStatus
- **Request serializers**: FeeQuoteRequest, CertificateApplication
- **Response serializers**: ApplicationList, ApplicationDetail, PendingApplication
- **Action serializers**: ProcessApplication, IssueCertificate

### 5. Views (views.py)

REST API views following household_module pattern:

#### ViewSets (ReadOnly)

- `DocumentTypeViewSet` - List document types
- `ClearancePurposeViewSet` - List clearance purposes
- `ApplicationStatusViewSet` - List status types

#### APIViews (Complex Operations)

- `CertificateDataView` - Get form dropdown data
- `FeeQuoteView` - Calculate fees
- `SubmitApplicationView` - Submit applications
- `ResidentApplicationsView` - Get user applications
- `ApplicationDetailView` - Get application details
- `PendingApplicationsView` - Get pending applications
- `ProcessApplicationView` - Approve/reject applications
- `IssueCertificateView` - Issue certificates

### 6. URL Configuration (urls.py)

Router-based URL configuration following household_module pattern:

- ViewSets registered with DefaultRouter
- APIView endpoints with descriptive paths
- Organized mobile vs personnel endpoints

## API Endpoints

### Mobile Endpoints (for resident_api integration)

```
GET    /certificate_api/certificate-data/                     - Get form data
POST   /certificate_api/fee-quote/                           - Calculate fees
POST   /certificate_api/submit-application/                  - Submit application
GET    /certificate_api/resident/<id>/applications/         - Get user applications
GET    /certificate_api/application/<id>/details/           - Get application details
```

### Personnel Endpoints (for web dashboard)

```
GET    /certificate_api/pending-applications/               - Get pending applications
POST   /certificate_api/application/<id>/process/          - Approve/reject
POST   /certificate_api/application/<id>/issue/             - Issue certificate
```

### ViewSet Endpoints

```
GET    /certificate_api/document-types/                     - List document types
GET    /certificate_api/clearance-purposes/                - List purposes with fees
GET    /certificate_api/application-statuses/              - List status types
```

## Response Format Consistency

All endpoints follow the same response pattern as household_module:

### Success Response

```json
{
  "success": true,
  "data": { ... },
  "message": "Optional success message"
}
```

### Error Response

```json
{
  "success": false,
  "message": "Error description",
  "error": "Technical error details",
  "errors": { "field": ["validation errors"] }
}
```

## Database Integration

The module uses PostgreSQL stored procedures for all database operations:

### Required Database Functions

- `resident_quote_fee(resident_id, document_type_id, business_id, clearance_purpose_id)`
- `resident_create_application(applicant_id, document_type_id, description, business_id, clearance_purpose_id)`
- `process_certificate_application(application_id, personnel_id, action, remarks)`
- `issue_certificate(application_id, issued_by_id, certificate_number, valid_until)`

### Database Tables

- `document_type` - Certificate types
- `clearance_purpose` - Purposes with fees
- `application_status` - Status types
- `certificate_application` - Applications
- `certificate_issuance` - Issued certificates

## Integration Points

### With resident_api Module

The certificate_issuance_module provides the mobile-friendly endpoints that can be consumed by the resident_api mobile app, maintaining the same response patterns and authentication mechanisms.

### With Personnel Modules

Personnel (Secretary, Captain, etc.) can access the web dashboard endpoints for processing applications and issuing certificates.

### Example Mobile Integration

```javascript
// Get certificate data for form dropdowns
const response = await fetch("/certificate_api/certificate-data/");
const data = await response.json();

// Calculate fee
const feeResponse = await fetch("/certificate_api/fee-quote/", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    resident_id: 123,
    document_type_id: 1,
    clearance_purpose_id: 2,
  }),
});

// Submit application
const appResponse = await fetch("/certificate_api/submit-application/", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    applicant_id: 123,
    document_type_id: 1,
    application_description: "For employment",
    clearance_purpose_id: 2,
  }),
});
```

## Installation & Configuration

### 1. Module Registration

The module is already registered in:

- `lambo/settings.py` - Added to INSTALLED_APPS
- `lambo/urls.py` - Added certificate_api/ URL pattern

### 2. Database Setup

Create the required database tables and stored procedures in PostgreSQL to support the certificate functionality.

### 3. Testing

Run Django tests to ensure all endpoints work correctly:

```bash
python manage.py test certificate_issuance_module
```

## Key Features

✅ **Consistent Architecture** - Follows household_module pattern exactly  
✅ **Database-First Approach** - Uses managed=False models  
✅ **Service Layer Separation** - Business logic in services/  
✅ **PostgreSQL Stored Procedures** - Database operations via functions  
✅ **REST API Standards** - DRF ViewSets and APIViews  
✅ **Mobile-Ready Responses** - Same format as resident_api  
✅ **Error Handling** - Comprehensive error management  
✅ **Logging & Debugging** - Print statements and logging  
✅ **Validation** - Request data validation via serializers  
✅ **Modular Design** - Easy to extend and maintain

The certificate_issuance_module provides a complete, production-ready solution for certificate management that seamlessly integrates with the existing LAMBO system architecture.
