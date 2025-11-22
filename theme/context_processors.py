from __future__ import annotations

from django.db import connection

def application_badges(request):
    """
    Provide counts for Applications badges in the sidebar.

    Exposes a dict `badges_applications` with keys:
      - total_today
      - pending_today
      - for_payment_today
      - approved_today

    If the SQL function isn't available or an error occurs, return zeros.
    """
    data = {
        "total_today": 0,
        "pending_today": 0,
        "for_payment_today": 0,
        "approved_today": 0,
    }

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT total_today, pending_today, for_payment_today, approved_today FROM applications_badges()")
            row = cursor.fetchone()
            if row:
                data = {
                    "total_today": row[0] or 0,
                    "pending_today": row[1] or 0,
                    "for_payment_today": row[2] or 0,
                    "approved_today": row[3] or 0,
                }
    except Exception:
        # Fail silently; sidebar should not break if function is missing
        pass

    return {"badges_applications": data}
