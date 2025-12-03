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


# ==================== HOUSEHOLD-RELATED QUERIES ====================

def get_specific_household(household_id, quarter_id=None):
    """
    Fetch specific household details using get_specific_household function.
    
    Args:
        household_id: Household ID to retrieve
        quarter_id: Optional quarter ID for historical data
    
    Returns:
        Dictionary containing household details or None if not found
    """
    query = "SELECT * FROM get_specific_household(%s, %s)"
    with connection.cursor() as cursor:
        cursor.execute(query, [household_id, quarter_id])
        columns = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        if row:
            return dict(zip(columns, row))
        return None


def get_all_households(query=None, barangay=None, sitio_id=None, status=None, quarter_id=None, limit=10000, offset=0):
    """
    Fetch all households with filtering using get_all_households function.
    
    Args:
        query: Search query string (optional)
        barangay: Barangay filter (optional)
        sitio_id: Sitio ID filter (optional)
        status: Status filter ('all', 'active', 'inactive') (optional)
        quarter_id: Quarter ID for historical data (optional)
        limit: Maximum number of records to return (default: 10000)
        offset: Number of records to skip (default: 0)
    
    Returns:
        List of household dictionaries
    """
    sql = """
        SELECT * FROM get_all_households(
            p_query := %s,
            p_barangay := %s,
            p_sitio_id := %s,
            p_status := %s,
            p_quarter_id := %s,
            p_limit := %s,
            p_offset := %s
        )
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [query, barangay, sitio_id, status, quarter_id, limit, offset])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_all_quarters():
    """
    Fetch all quarters from the database.
    
    Returns:
        List of quarter dictionaries
    """
    query = "SELECT * FROM get_all_quarters()"
    with connection.cursor() as cursor:
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_sitios():
    """
    Fetch all sitios from the database.
    
    Returns:
        List of sitio dictionaries with sitio_id and sitio_name
    """
    query = "SELECT sitio_id, sitio_name FROM sitio ORDER BY sitio_name"
    with connection.cursor() as cursor:
        cursor.execute(query)
        return [{"sitio_id": row[0], "sitio_name": row[1]} for row in cursor.fetchall()]


def get_quarter_info(quarter_id):
    """
    Fetch quarter information by quarter_id.
    
    Args:
        quarter_id: Quarter ID to retrieve
    
    Returns:
        Dictionary with quarter_number and year, or None if not found
    """
    query = "SELECT quarter_number, year FROM quarter WHERE quarter_id = %s"
    with connection.cursor() as cursor:
        cursor.execute(query, [quarter_id])
        row = cursor.fetchone()
        if row:
            return {"quarter_number": row[0], "year": row[1]}
        return None


def get_household_family_summaries(household_id, quarter_id=None):
    """
    Fetch family summaries for a specific household using get_household_family_summaries function.
    
    Args:
        household_id: Household ID to retrieve families for
        quarter_id: Optional quarter ID for historical data
    
    Returns:
        List of family summary dictionaries containing:
        - family_id
        - family_code
        - family_head
        - total_members
        - is_visited
        - date_visited
        - quarter_id
    """
    query = "SELECT * FROM get_household_family_summaries(%s, %s)"
    with connection.cursor() as cursor:
        cursor.execute(query, [household_id, quarter_id])
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        # Filter out sentinel rows (family_id = 0)
        return [r for r in results if r.get('family_id', 0) != 0]


def get_harmonized_family_profile(family_id, quarter_id=None):
    """
    Fetch harmonized family profile using get_harmonized_family_profile function.
    Returns unified profile with household, family, and member health data.
    
    Args:
        family_id: Family ID to retrieve
        quarter_id: Optional quarter ID for historical data (uses current quarter if None)
    
    Returns:
        Dictionary containing:
        - quarter_id: The quarter ID used
        - household: Household information dict
        - family: Family information dict
        - members: List of member dicts with demographic and general_health data
    """
    import json
    query = "SELECT get_harmonized_family_profile(%s, %s)"
    with connection.cursor() as cursor:
        cursor.execute(query, [family_id, quarter_id])
        result = cursor.fetchone()
        if result and result[0]:
            return json.loads(result[0]) if isinstance(result[0], str) else result[0]
        return None
