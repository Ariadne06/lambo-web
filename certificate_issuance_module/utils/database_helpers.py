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