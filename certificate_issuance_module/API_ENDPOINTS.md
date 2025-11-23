# Certificate Issuance Module - API Endpoints

## 📋 Overview

This document describes the RESTful API endpoints for managing resident applications, transactions, and certificate issuance.

---

## 🔐 Authentication

All endpoints require proper authentication. Pass `resident_id` in the URL path for ownership verification.

---

## 📌 Endpoints Summary

| Method | Endpoint                                                                         | Description                           |
| ------ | -------------------------------------------------------------------------------- | ------------------------------------- |
| GET    | `/certificate_api/document-types/`                                               | List all document types               |
| GET    | `/certificate_api/clearance-purposes/`                                           | List all clearance purposes with fees |
| POST   | `/certificate_api/create-clearance-application/`                                 | Create barangay clearance application |
| GET    | `/certificate_api/residents/{resident_id}/applications/`                         | List all applications for a resident  |
| GET    | `/certificate_api/residents/{resident_id}/applications/{application_id}/`        | Get application details               |
| GET    | `/certificate_api/residents/{resident_id}/transactions/`                         | List all transactions for a resident  |
| GET    | `/certificate_api/residents/{resident_id}/transactions/{transaction_id}/`        | Get transaction details               |
| POST   | `/certificate_api/residents/{resident_id}/applications/{application_id}/cancel/` | Cancel clearance application          |

---

## 📖 Detailed Endpoint Documentation

### 1. List Document Types

**GET** `/certificate_api/document-types/`

Lists all available document types.

**Response:**

```json
[
  {
    "document_type_id": 1,
    "document_type_name": "Barangay Clearance"
  }
]
```

---

### 2. List Clearance Purposes

**GET** `/certificate_api/clearance-purposes/`

Lists all clearance purposes with associated fees.

**Response:**

```json
[
  {
    "other_clearance_id": 1,
    "purpose_name": "Employment",
    "fee_amount": "50.00"
  }
]
```

---

### 3. Create Barangay Clearance Application

**POST** `/certificate_api/create-clearance-application/`

Creates a new barangay clearance application.

**Request Body:**

```json
{
  "resident_id": 123,
  "other_clearance_id": 1
}
```

**Response (201 Created):**

```json
{
  "application_id": 456,
  "message": "Barangay clearance application created successfully"
}
```

---

### 4. List Resident Applications

**GET** `/certificate_api/residents/{resident_id}/applications/`

Gets all applications (barangay & business) for a specific resident with optional filtering.

**Path Parameters:**

- `resident_id` (int, required): ID of the resident

**Query Parameters:**

- `query` (string, optional): Search term for application code, business name, or fee type
- `app_status` (string, optional): Filter by application status (e.g., "Pending", "Approved")
- `pay_status` (string, optional): Filter by payment status (e.g., "Unpaid", "Paid")
- `limit` (int, optional, default=50): Maximum number of results (1-500)
- `offset` (int, optional, default=0): Pagination offset

**Example Request:**

```
GET /certificate_api/residents/123/applications/?query=clearance&app_status=Pending&limit=20&offset=0
```

**Response (200 OK):**

```json
{
  "success": true,
  "data": [
    {
      "application_id": 456,
      "application_code": "APP-2025-001",
      "request": "Barangay Clearance",
      "fee_type": "Clearance Fee",
      "application_status": "Pending",
      "payment_status": "Unpaid",
      "date_submitted": "2025-11-23T10:30:00+08:00",
      "updated_at": "2025-11-23T10:30:00+08:00",
      "total_amount": "50.00",
      "or_number": null,
      "date_paid": null,
      "is_business": false,
      "business_id": null,
      "business_name": null
    }
  ],
  "count": 1,
  "limit": 20,
  "offset": 0
}
```

---

### 5. Get Application Details

**GET** `/certificate_api/residents/{resident_id}/applications/{application_id}/`

Gets detailed information for a specific application.

**Path Parameters:**

- `resident_id` (int, required): ID of the resident (for ownership verification)
- `application_id` (int, required): ID of the application

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "application_id": 456,
    "application_code": "APP-2025-001",
    "request": "Barangay Clearance",
    "fee_type": "Clearance Fee",
    "application_status": "Pending",
    "payment_status": "Unpaid",
    "date_submitted": "2025-11-23T10:30:00+08:00",
    "updated_at": "2025-11-23T10:30:00+08:00",
    "total_amount": "50.00",
    "total_amount_details": {
      "base_fee": "50.00"
    },
    "or_number": null,
    "date_paid": null,
    "is_business": false,
    "business_id": null,
    "business_name": null,
    "applicant_id": 123,
    "applicant_name": "Juan Dela Cruz",
    "requested_by": "resident",
    "requested_by_id": 123,
    "requested_by_full_name": "Juan Dela Cruz",
    "cancel_reason": null,
    "canceled_at": null,
    "canceled_by_type": null,
    "canceled_by_id": null,
    "canceled_by_full_name": null,
    "reject_reason": null,
    "rejected_at": null,
    "rejected_by_type": null,
    "rejected_by_id": null,
    "rejected_by_full_name": null
  }
}
```

**Error Response (403 Forbidden):**

```json
{
  "success": false,
  "error": "You are not allowed to view this application."
}
```

---

### 6. List Resident Transactions

**GET** `/certificate_api/residents/{resident_id}/transactions/`

Gets all payment transactions for a specific resident with optional filtering.

**Path Parameters:**

- `resident_id` (int, required): ID of the resident

**Query Parameters:**

- `query` (string, optional): Search term for transaction code, application code, business name, or fee type
- `pay_status` (string, optional): Filter by payment status (e.g., "Unpaid", "Paid", "Cancelled")
- `limit` (int, optional, default=50): Maximum number of results (1-500)
- `offset` (int, optional, default=0): Pagination offset

**Example Request:**

```
GET /certificate_api/residents/123/transactions/?pay_status=Paid&limit=10
```

**Response (200 OK):**

```json
{
  "success": true,
  "data": [
    {
      "transaction_id": 789,
      "transaction_code": "TXN-2025-001",
      "application_id": 456,
      "request": "Barangay Clearance",
      "fee_type": "Clearance Fee",
      "total_amount": "50.00",
      "payment_status": "Paid",
      "date_paid": "2025-11-23T14:00:00+08:00",
      "or_number": "OR-12345",
      "date_submitted": "2025-11-23T10:30:00+08:00",
      "updated_at": "2025-11-23T14:00:00+08:00",
      "is_business": false,
      "business_id": null,
      "business_name": null
    }
  ],
  "count": 1,
  "limit": 10,
  "offset": 0
}
```

---

### 7. Get Transaction Details

**GET** `/certificate_api/residents/{resident_id}/transactions/{transaction_id}/`

Gets detailed information for a specific transaction.

**Path Parameters:**

- `resident_id` (int, required): ID of the resident (for ownership verification)
- `transaction_id` (int, required): ID of the transaction

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "transaction_id": 789,
    "transaction_code": "TXN-2025-001",
    "application_id": 456,
    "request": "Barangay Clearance",
    "fee_type": "Clearance Fee",
    "total_amount": "50.00",
    "total_amount_details": {
      "base_fee": "50.00"
    },
    "payment_status": "Paid",
    "date_paid": "2025-11-23T14:00:00+08:00",
    "or_number": "OR-12345",
    "is_business": false,
    "business_id": null,
    "business_name": null,
    "applicant_id": 123,
    "applicant_name": "Juan Dela Cruz",
    "cancel_reason": null,
    "canceled_at": null,
    "canceled_by_type": null,
    "canceled_by_id": null,
    "canceled_by_full_name": null
  }
}
```

**Error Response (403 Forbidden):**

```json
{
  "success": false,
  "error": "You are not allowed to view this transaction."
}
```

---

### 8. Cancel Clearance Application

**POST** `/certificate_api/residents/{resident_id}/applications/{application_id}/cancel/`

Cancels a clearance application. Only works for Pending/For Payment applications that haven't been paid.

**Path Parameters:**

- `resident_id` (int, required): ID of the resident
- `application_id` (int, required): ID of the application to cancel

**Request Body (Optional):**

```json
{
  "reason": "Changed my mind"
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "message": "Clearance application cancelled successfully"
}
```

**Error Responses:**

**404 Not Found:**

```json
{
  "success": false,
  "error": "Application 999 not found"
}
```

**403 Forbidden:**

```json
{
  "success": false,
  "error": "You can only cancel your own application."
}
```

**400 Bad Request:**

```json
{
  "success": false,
  "error": "Only Pending/For Payment applications can be cancelled."
}
```

---

## 🔧 Implementation Details

### Architecture Pattern

- **Pattern**: APIView with database helpers
- **Validation**: DRF Serializers
- **Database**: PostgreSQL stored procedures
- **Error Handling**: Try-catch with specific error messages

### Files Modified

1. `utils/database_helpers.py` - Database interaction functions
2. `serializers.py` - Request/response validation
3. `views.py` - HTTP request handling
4. `urls.py` - URL routing

### Business Rules

1. **Ownership Verification**: All endpoints verify that the resident owns the application/transaction
2. **Cancellation Rules**:
   - Only the applicant can cancel (not for business applications)
   - Only Pending/For Payment status can be cancelled
   - Cannot cancel if payment is already Paid
3. **Pagination**: Default 50 results, max 500
4. **DateTime Format**: ISO 8601 with timezone (e.g., "2025-11-23T10:30:00+08:00")

---

## 📝 Testing Examples

### Test Application List

```bash
curl -X GET "http://localhost:8000/certificate_api/residents/123/applications/?limit=10" \
  -H "Authorization: Token YOUR_TOKEN"
```

### Test Create Clearance

```bash
curl -X POST "http://localhost:8000/certificate_api/create-clearance-application/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Token YOUR_TOKEN" \
  -d '{
    "resident_id": 123,
    "other_clearance_id": 1
  }'
```

### Test Cancel Application

```bash
curl -X POST "http://localhost:8000/certificate_api/residents/123/applications/456/cancel/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Token YOUR_TOKEN" \
  -d '{
    "reason": "No longer needed"
  }'
```

---

## 🚀 Next Steps

1. Test all endpoints with actual data
2. Add authentication/permission classes if needed
3. Implement rate limiting for production
4. Add comprehensive logging
5. Create integration tests
