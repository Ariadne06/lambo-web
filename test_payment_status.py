import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lambo.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    # Get table info
    print("Getting table columns:")
    try:
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'application'
            ORDER BY ordinal_position
        """)
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]}")
    except Exception as e:
        print("Error:", e)
