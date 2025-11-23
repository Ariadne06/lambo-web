from django.db import connection


def get_document_types():
    """Return all document types using SQL function fn_list_document_types()."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM fn_list_document_types()")
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_clearance_purposes():
    """Return all clearance purposes and fees using SQL function fn_list_clearance_purposes()."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM fn_list_clearance_purposes()")
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def create_barangay_clearance(resident_id, other_clearance_id):
    """
    Create a barangay clearance application for a resident.
    
    Args:
        resident_id: ID of the resident requesting clearance
        other_clearance_id: ID of the clearance purpose type
    
    Returns:
        int: The created application ID
    
    Raises:
        Exception: If fee type not found or creation fails
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT resident_create_barangay_clearance(%s, %s)",
            [resident_id, other_clearance_id]
        )
        result = cursor.fetchone()
        return result[0] if result else None


def get_resident_applications(resident_id, query=None, app_status=None, pay_status=None, limit=50, offset=0):
    """
    Get all applications (barangay & business) for a specific resident.
    
    Args:
        resident_id: ID of the resident
        query: Optional search query
        app_status: Optional application status filter
        pay_status: Optional payment status filter
        limit: Maximum number of results (default: 50)
        offset: Offset for pagination (default: 0)
    
    Returns:
        list: List of application dictionaries
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM get_specific_resident_all_applications(%s, %s, %s, %s, %s, %s)",
            [resident_id, query, app_status, pay_status, limit, offset]
        )
        columns = [col[0] for col in cursor.description]
        results = []
        for row in cursor.fetchall():
            app_dict = dict(zip(columns, row))
            # Format datetime fields
            if app_dict.get('date_submitted'):
                app_dict['date_submitted'] = app_dict['date_submitted'].isoformat()
            if app_dict.get('updated_at'):
                app_dict['updated_at'] = app_dict['updated_at'].isoformat()
            if app_dict.get('date_paid'):
                app_dict['date_paid'] = app_dict['date_paid'].isoformat()
            results.append(app_dict)
        return results


def get_resident_application_detail(resident_id, application_id):
    """
    Get detailed information for a specific application.
    
    Args:
        resident_id: ID of the resident (for ownership verification)
        application_id: ID of the application
    
    Returns:
        dict: Application details or None if not found
    
    Raises:
        Exception: If resident doesn't own the application
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM get_specific_resident_specific_application(%s, %s)",
            [resident_id, application_id]
        )
        columns = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        
        if not row:
            return None
        
        app_dict = dict(zip(columns, row))
        
        # Format datetime fields
        datetime_fields = ['date_submitted', 'updated_at', 'date_paid', 'canceled_at', 'rejected_at']
        for field in datetime_fields:
            if app_dict.get(field):
                app_dict[field] = app_dict[field].isoformat()
        
        return app_dict


def get_resident_transactions(resident_id, query=None, pay_status=None, limit=50, offset=0):
    """
    Get all payment transactions for a specific resident.
    
    Args:
        resident_id: ID of the resident
        query: Optional search query
        pay_status: Optional payment status filter
        limit: Maximum number of results (default: 50)
        offset: Offset for pagination (default: 0)
    
    Returns:
        list: List of transaction dictionaries
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM get_specific_resident_all_transactions(%s, %s, %s, %s, %s)",
            [resident_id, query, pay_status, limit, offset]
        )
        columns = [col[0] for col in cursor.description]
        results = []
        for row in cursor.fetchall():
            trans_dict = dict(zip(columns, row))
            # Format datetime fields
            if trans_dict.get('date_paid'):
                trans_dict['date_paid'] = trans_dict['date_paid'].isoformat()
            if trans_dict.get('date_submitted'):
                trans_dict['date_submitted'] = trans_dict['date_submitted'].isoformat()
            if trans_dict.get('updated_at'):
                trans_dict['updated_at'] = trans_dict['updated_at'].isoformat()
            results.append(trans_dict)
        return results


def get_resident_transaction_detail(resident_id, transaction_id):
    """
    Get detailed information for a specific transaction.
    
    Args:
        resident_id: ID of the resident (for ownership verification)
        transaction_id: ID of the transaction
    
    Returns:
        dict: Transaction details or None if not found
    
    Raises:
        Exception: If resident doesn't own the transaction
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM get_specific_resident_specific_transaction(%s, %s)",
            [resident_id, transaction_id]
        )
        columns = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        
        if not row:
            return None
        
        trans_dict = dict(zip(columns, row))
        
        # Format datetime fields
        if trans_dict.get('date_paid'):
            trans_dict['date_paid'] = trans_dict['date_paid'].isoformat()
        if trans_dict.get('canceled_at'):
            trans_dict['canceled_at'] = trans_dict['canceled_at'].isoformat()
        
        return trans_dict


def cancel_resident_clearance(application_id, resident_id, reason=None):
    """
    Cancel a clearance application.
    
    Args:
        application_id: ID of the application to cancel
        resident_id: ID of the resident cancelling
        reason: Optional cancellation reason
    
    Raises:
        Exception: If cancellation fails or not allowed
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT resident_cancel_clearance(%s, %s, %s)",
            [application_id, resident_id, reason]
        )