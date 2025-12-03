-- ============================================
-- Diagnostic Script: Check Push Notification Setup
-- ============================================

-- 1. Check if pg_net extension is installed
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_net') 
        THEN '✓ pg_net extension IS installed'
        ELSE '✗ pg_net extension NOT installed - HTTP calls will fail'
    END AS pg_net_status;

-- 2. Check if trigger exists and is active
SELECT 
    trigger_name,
    event_manipulation,
    action_statement,
    action_timing,
    CASE 
        WHEN status = 'ENABLED' THEN '✓ ACTIVE'
        ELSE '✗ DISABLED'
    END AS trigger_status
FROM information_schema.triggers
WHERE trigger_name = 'after_notification_insert';

-- 3. Check recent notifications
SELECT 
    notification_id,
    title,
    body,
    resident_id,
    created_at,
    is_read
FROM notification
ORDER BY created_at DESC
LIMIT 5;

-- 4. Check push devices registered
SELECT 
    pd.push_device_id,
    pd.resident_id,
    pd.personnel_id,
    ut.type_name,
    pd.platform,
    LEFT(pd.expo_push_token, 30) || '...' as token_preview,
    pd.created_at,
    pd.is_active
FROM push_device pd
JOIN user_type ut ON pd.user_type_id = ut.user_type_id
ORDER BY pd.created_at DESC
LIMIT 10;

-- 5. Test if net.http_post function exists (only works if pg_net is enabled)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_proc 
        WHERE proname = 'http_post' 
        AND pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'net')
    ) THEN
        RAISE NOTICE '✓ net.http_post function exists';
    ELSE
        RAISE NOTICE '✗ net.http_post function NOT found';
    END IF;
END $$;

-- 6. Count active push devices by user type
SELECT 
    ut.type_name,
    COUNT(*) as device_count,
    COUNT(DISTINCT CASE WHEN ut.type_name = 'RESIDENT' THEN pd.resident_id ELSE pd.personnel_id END) as unique_users
FROM push_device pd
JOIN user_type ut ON pd.user_type_id = ut.user_type_id
WHERE pd.is_active = true
GROUP BY ut.type_name;

-- 7. Check if webhook secret matches (just structure check)
SELECT 
    CASE 
        WHEN current_setting('app.cron_secret_token', true) IS NOT NULL 
        THEN '✓ Secret token is configured'
        ELSE '⚠ Secret token not found in database settings'
    END AS secret_status;
