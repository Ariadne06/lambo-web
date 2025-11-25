"""
Database helper functions for Reports Module.
Contains raw SQL queries to PostgreSQL stored procedures and functions.
"""
from django.db import connection
from datetime import datetime


def execute_query(query, params=None):
    """
    Execute a raw SQL query and return results.
    
    Args:
        query: SQL query string
        params: Query parameters (optional)
    
    Returns:
        List of dictionaries containing query results
    """
    with connection.cursor() as cursor:
        cursor.execute(query, params or [])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_resident_statistics(barangay_id=None, date_from=None, date_to=None):
    """
    Get resident statistics for report generation.
    
    Example stored procedure call:
    SELECT * FROM get_resident_statistics(%s, %s, %s)
    
    Args:
        barangay_id: Filter by barangay (optional)
        date_from: Start date filter (optional)
        date_to: End date filter (optional)
    
    Returns:
        List of resident statistics data
    """
    query = """
        SELECT 
            COUNT(*) as total_residents,
            COUNT(CASE WHEN gender = 'Male' THEN 1 END) as male_count,
            COUNT(CASE WHEN gender = 'Female' THEN 1 END) as female_count,
            COUNT(CASE WHEN voter_status = 'Registered' THEN 1 END) as registered_voters
        FROM resident_profiling_module_resident
        WHERE is_archived = FALSE
    """
    
    params = []
    if date_from:
        query += " AND created_at >= %s"
        params.append(date_from)
    if date_to:
        query += " AND created_at <= %s"
        params.append(date_to)
    
    return execute_query(query, params)


def get_clearance_applications_report(date_from=None, date_to=None, status=None):
    """
    Get clearance applications data for report generation.
    
    Args:
        date_from: Start date filter (optional)
        date_to: End date filter (optional)
        status: Application status filter (optional)
    
    Returns:
        List of clearance application records
    """
    query = """
        SELECT 
            application_code,
            applicant_name,
            application_status,
            payment_status,
            total_amount,
            created_at,
            date_paid
        FROM get_all_applications()
        WHERE 1=1
    """
    
    params = []
    if date_from:
        query += " AND created_at >= %s"
        params.append(date_from)
    if date_to:
        query += " AND created_at <= %s"
        params.append(date_to)
    if status:
        query += " AND application_status = %s"
        params.append(status)
    
    query += " ORDER BY created_at DESC"
    
    return execute_query(query, params)


def get_revenue_report(date_from=None, date_to=None):
    """
    Get revenue/transaction summary for financial reports.
    
    Args:
        date_from: Start date filter (optional)
        date_to: End date filter (optional)
    
    Returns:
        Revenue summary data
    """
    query = """
        SELECT 
            COUNT(*) as total_transactions,
            SUM(amount_paid) as total_revenue,
            COUNT(CASE WHEN payment_status = 'Paid' THEN 1 END) as paid_count,
            COUNT(CASE WHEN payment_status = 'Pending' THEN 1 END) as pending_count
        FROM get_all_transactions()
        WHERE payment_status = 'Paid'
    """
    
    params = []
    if date_from:
        query += " AND date_paid >= %s"
        params.append(date_from)
    if date_to:
        query += " AND date_paid <= %s"
        params.append(date_to)
    
    return execute_query(query, params)


def get_household_statistics():
    """
    Get household statistics for demographic reports.
    
    Returns:
        Household statistics data
    """
    query = """
        SELECT 
            COUNT(*) as total_households,
            AVG(household_member_count) as avg_household_size
        FROM household_module_household
        WHERE is_archived = FALSE
    """
    
    return execute_query(query)


def get_resident_list_report():
    """
    Get complete list of all residents with status = 'Resident'.
    Uses the report_resident_list() stored procedure.
    
    Returns:
        List of resident records with full details
    """
    query = """
        SELECT 
            resident_code,
            full_name,
            dob,
            full_address,
            phone_number,
            email
        FROM report_resident_list()
    """
    
    return execute_query(query)


def get_blotter_report(date_from=None, date_to=None, status=None):
    """
    Get blotter/incident records for report generation.
    
    Args:
        date_from: Start date filter (optional)
        date_to: End date filter (optional)
        status: Blotter status filter (optional)
    
    Returns:
        List of blotter records
    """
    # Add your blotter query here based on your database schema
    # This is a placeholder example
    query = """
        SELECT 
            case_number,
            complainant_name,
            respondent_name,
            incident_date,
            status,
            created_at
        FROM blotter_records
        WHERE 1=1
    """
    
    params = []
    if date_from:
        query += " AND incident_date >= %s"
        params.append(date_from)
    if date_to:
        query += " AND incident_date <= %s"
        params.append(date_to)
    if status:
        query += " AND status = %s"
        params.append(status)
    
    query += " ORDER BY incident_date DESC"
    
    return execute_query(query, params)


def format_datetime_for_report(dt):
    """
    Format datetime object for report display.
    
    Args:
        dt: datetime object or string
    
    Returns:
        Formatted date string
    """
    if isinstance(dt, str):
        return dt
    if isinstance(dt, datetime):
        return dt.strftime('%B %d, %Y %I:%M %p')
    return ''


def format_currency(amount):
    """
    Format currency for Philippine Peso.
    
    Args:
        amount: Decimal or float amount
    
    Returns:
        Formatted currency string
    """
    if amount is None:
        return '₱0.00'
    return f'₱{amount:,.2f}'
