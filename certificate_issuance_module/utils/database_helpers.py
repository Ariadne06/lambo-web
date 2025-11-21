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