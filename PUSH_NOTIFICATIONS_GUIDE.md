# Push Notifications Setup - Complete Guide

## Summary

This guide documents the complete push notification system for the LAMBO project, including the fix for the database trigger integration.

---

## Architecture

```
Supabase Cron Job (schedule: 0 8 1 1 *)
    ↓
PostgreSQL Function (e.g., set_all_business_to_for_renewal)
    ↓
INSERT INTO notification table
    ↓
Database Trigger: after_notification_insert
    ↓
Calls: net.http_post() → Django Webhook
    ↓
Django: /api/notifications/send-push/
    ↓
Expo Push Service → Firebase Cloud Messaging
    ↓
Mobile Device receives push notification 🔔
```

---

## Required Components

### 1. Supabase Extensions

- ✅ **pg_net** - Required for HTTP calls from database triggers
  - Enable: Supabase Dashboard → Database → Extensions → pg_net

### 2. Database Trigger Function

```sql
CREATE OR REPLACE FUNCTION trigger_push_notification()
RETURNS TRIGGER AS $$
DECLARE
    v_request_id BIGINT;
BEGIN
    -- Call Django webhook to send push notification
    SELECT INTO v_request_id
        net.http_post(
            url := 'https://lambo-web-5mka.onrender.com/api/notifications/send-push/',
            headers := jsonb_build_object(
                'Content-Type', 'application/json',
                'X-Cron-Secret', 'uswn-j2NfhJh7yYLoWvSZB_0WcJLOtfqqlbt_6xMzkw'
            ),
            body := jsonb_build_object(
                'notification_id', NEW.notification_id,
                'user_type_id', NEW.user_type_id,
                'user_id', NEW.resident_id,
                'title', NEW.title,
                'body', NEW.body,
                'deep_link', NEW.deep_link
            )
        );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger
CREATE TRIGGER after_notification_insert
AFTER INSERT ON notification
FOR EACH ROW
EXECUTE FUNCTION trigger_push_notification();
```

### 3. Django Webhook Endpoint

**File:** `notifications/views.py`

**Endpoint:** `POST /api/notifications/send-push/`

**Authentication:** `X-Cron-Secret` header must match `CRON_SECRET_TOKEN` in `.env`

**Fixed Issue:** Changed from non-existent `get_db_connection()` to Django's `connection` object.

---

## Testing

### Manual Test (Database)

```sql
INSERT INTO notification (user_type_id, resident_id, title, body, deep_link, is_read, created_at)
VALUES (
    (SELECT user_type_id FROM user_type WHERE LOWER(type_name) = 'resident' LIMIT 1),
    (SELECT resident_id FROM push_device WHERE is_active = true LIMIT 1),
    'Test Notification',
    'Testing push notification system!',
    '/(tabs)/notifications',
    false,
    NOW()
);
```

### Manual Test (Django)

```bash
python manage.py send_test_notification
```

---

## Supabase Cron Jobs

### Example: Business Renewal Notification

**Schedule:** `0 8 1 1 *` (January 1st at 8:00 AM yearly)

**Command:**

```sql
SELECT set_all_business_to_for_renewal();
```

**Function:**

```sql
CREATE OR REPLACE FUNCTION set_all_business_to_for_renewal()
RETURNS INT AS $$
DECLARE
    v_for_renewal_status_id INT;
    v_active_status_id INT;
    v_resident_type_id INT;
    v_updated_count INT := 0;
    v_business RECORD;
BEGIN
    -- Get status IDs
    SELECT business_status_id INTO v_for_renewal_status_id
    FROM business_status
    WHERE LOWER(business_status_name) = 'for renewal' LIMIT 1;

    SELECT business_status_id INTO v_active_status_id
    FROM business_status
    WHERE LOWER(business_status_name) = 'active' LIMIT 1;

    SELECT user_type_id INTO v_resident_type_id
    FROM user_type
    WHERE LOWER(type_name) = 'resident' LIMIT 1;

    -- Loop through active businesses
    FOR v_business IN
        SELECT b.business_id, b.business_name, b.resident_id
        FROM business b
        WHERE b.business_status_id = v_active_status_id
    LOOP
        -- Update business status
        UPDATE business
        SET business_status_id = v_for_renewal_status_id,
            updated_at = NOW()
        WHERE business_id = v_business.business_id;

        -- Insert notification (trigger automatically sends push)
        INSERT INTO notification (user_type_id, resident_id, title, body, deep_link, is_read, created_at)
        VALUES (
            v_resident_type_id,
            v_business.resident_id,
            'Business Renewal Required 📋',
            'Your business "' || v_business.business_name || '" requires renewal. Please submit renewal requirements by March 31, 2025.',
            '/(tabs)/business',
            false,
            NOW()
        );

        v_updated_count := v_updated_count + 1;
    END LOOP;

    -- Log activity
    INSERT INTO activity_log (activity_type, description, created_at)
    VALUES ('BUSINESS_RENEWAL', 'Set ' || v_updated_count || ' businesses to For Renewal status and sent push notifications', NOW());

    RETURN v_updated_count;
END;
$$ LANGUAGE plpgsql;
```

---

## Troubleshooting

### Issue: No push notifications sent

**Check 1: pg_net enabled?**

```sql
SELECT * FROM pg_extension WHERE extname = 'pg_net';
```

**Check 2: Trigger exists?**

```sql
SELECT trigger_name FROM information_schema.triggers
WHERE trigger_name = 'after_notification_insert';
```

**Check 3: User has push token?**

```sql
SELECT * FROM push_device
WHERE resident_id = [YOUR_ID] AND is_active = true;
```

**Check 4: Django logs**

- Go to Render Dashboard → Logs
- Look for `POST /api/notifications/send-push/`
- Should see `Successfully sent push notifications to X device(s)`

### Issue: ImportError in webhook

**Symptom:** `cannot import name 'get_db_connection'`

**Fix:** Use Django's `connection` object:

```python
from django.db import connection as db_connection
with db_connection.cursor() as cursor:
    cursor.execute(...)
```

---

## Environment Variables

Required in `.env`:

```
CRON_SECRET_TOKEN=uswn-j2NfhJh7yYLoWvSZB_0WcJLOtfqqlbt_6xMzkw
```

This must match the secret in the database trigger function.

---

## Mobile App Setup

Users must:

1. Login to the LAMBO mobile app
2. Grant notification permissions
3. App automatically registers push token in `push_device` table

---

## Cron Schedule Reference

| Description              | Cron Expression |
| ------------------------ | --------------- |
| January 1st, 8 AM yearly | `0 8 1 1 *`     |
| 1st of every month, 8 AM | `0 8 1 * *`     |
| Every Monday, 8 AM       | `0 8 * * 1`     |
| Every day, 8 AM          | `0 8 * * *`     |
| Every hour               | `0 * * * *`     |

Format: `minute hour day month day-of-week`

---

## Key Files

- `notifications/views.py` - Django webhook endpoint
- `notifications/service.py` - NotificationService class
- `notifications/repo.py` - Database operations
- `notifications/management/commands/send_test_notification.py` - Test command
- Database trigger: `trigger_push_notification()`

---

## Success Checklist

- [ ] pg_net extension enabled
- [ ] Trigger `after_notification_insert` exists
- [ ] Django webhook returns 200 status
- [ ] User has registered push token
- [ ] Mobile app has notification permissions
- [ ] CRON_SECRET_TOKEN matches in trigger and .env
- [ ] Test notification sends successfully
