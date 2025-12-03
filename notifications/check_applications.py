from django.db import connection

# Find applications requested by residents
with connection.cursor() as cur:
    cur.execute("""
        SELECT application_id, application_code, requested_by, requested_by_id, application_status 
        FROM application 
        WHERE requested_by = 'resident' 
        ORDER BY application_id 
        LIMIT 10
    """)
    rows = cur.fetchall()
    
    if rows:
        print("Applications requested by residents:")
        for r in rows:
            print(f"  ID: {r[0]}, Code: {r[1]}, Resident ID: {r[3]}, Status: {r[4]}")
    else:
        print("No applications found requested by residents")

print("\nAll applications:")
with connection.cursor() as cur:
    cur.execute("""
        SELECT application_id, application_code, requested_by, requested_by_id, application_status 
        FROM application 
        ORDER BY application_id 
        LIMIT 10
    """)
    rows = cur.fetchall()
    
    for r in rows:
        print(f"  ID: {r[0]}, Code: {r[1]}, Requested by: {r[2]}, By ID: {r[3]}, Status: {r[4]}")
