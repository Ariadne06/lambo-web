-- ============================================
-- LAMBO Notifications Module Database Schema
-- ============================================
-- This file creates the necessary tables for the push notification system
-- Run this SQL in your PostgreSQL/Supabase database

-- ============================================
-- 1. USER TYPES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS user_type (
    user_type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default user types
INSERT INTO user_type (type_name, description) 
VALUES
    ('RESIDENT', 'Regular resident users'),
    ('PERSONNEL', 'Barangay personnel (BHW, Nurse, Admin, etc.)')
ON CONFLICT (type_name) DO NOTHING;

-- ============================================
-- 2. PUSH DEVICE TOKENS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS push_device (
    push_device_id SERIAL PRIMARY KEY,
    user_type_id INTEGER NOT NULL REFERENCES user_type(user_type_id) ON DELETE CASCADE,
    resident_id INTEGER,
    personnel_id INTEGER,
    platform VARCHAR(20) NOT NULL CHECK (platform IN ('ios', 'android')),
    expo_push_token TEXT NOT NULL,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints (adjust table names if different in your database)
    CONSTRAINT fk_resident FOREIGN KEY (resident_id) 
        REFERENCES resident(resident_id) ON DELETE CASCADE,
    CONSTRAINT fk_personnel FOREIGN KEY (personnel_id) 
        REFERENCES personnel(personnel_id) ON DELETE CASCADE,
    
    -- Ensure either resident_id or personnel_id is set, but not both
    CONSTRAINT check_user_id CHECK (
        (resident_id IS NOT NULL AND personnel_id IS NULL) OR
        (resident_id IS NULL AND personnel_id IS NOT NULL)
    )
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_push_device_resident ON push_device(resident_id);
CREATE INDEX IF NOT EXISTS idx_push_device_personnel ON push_device(personnel_id);
CREATE INDEX IF NOT EXISTS idx_push_device_token ON push_device(expo_push_token);
CREATE INDEX IF NOT EXISTS idx_push_device_user_type ON push_device(user_type_id);

-- ============================================
-- 3. NOTIFICATIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS notification (
    notification_id SERIAL PRIMARY KEY,
    user_type_id INTEGER NOT NULL REFERENCES user_type(user_type_id) ON DELETE CASCADE,
    resident_id INTEGER,
    personnel_id INTEGER,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    deep_link TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    CONSTRAINT fk_notification_resident FOREIGN KEY (resident_id) 
        REFERENCES resident(resident_id) ON DELETE CASCADE,
    CONSTRAINT fk_notification_personnel FOREIGN KEY (personnel_id) 
        REFERENCES personnel(personnel_id) ON DELETE CASCADE,
    
    -- Ensure either resident_id or personnel_id is set, but not both
    CONSTRAINT check_notification_user CHECK (
        (resident_id IS NOT NULL AND personnel_id IS NULL) OR
        (resident_id IS NULL AND personnel_id IS NOT NULL)
    )
);

-- Create indexes for performance (most recent unread notifications first)
CREATE INDEX IF NOT EXISTS idx_notification_resident 
    ON notification(resident_id, is_read, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notification_personnel 
    ON notification(personnel_id, is_read, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notification_created 
    ON notification(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notification_user_type 
    ON notification(user_type_id, created_at DESC);

-- ============================================
-- VERIFICATION QUERIES
-- ============================================
-- Run these to verify the tables were created successfully

-- Check tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('user_type', 'push_device', 'notification');

-- Check user types were inserted
SELECT * FROM user_type;

-- Check indexes were created
SELECT indexname, tablename 
FROM pg_indexes 
WHERE tablename IN ('push_device', 'notification') 
ORDER BY tablename, indexname;

-- ============================================
-- SAMPLE TEST DATA (Optional - for testing)
-- ============================================
-- Uncomment to insert test data

-- Insert test push device (replace resident_id with actual ID)
-- INSERT INTO push_device (user_type_id, resident_id, platform, expo_push_token)
-- VALUES (1, 1, 'android', 'ExponentPushToken[test-token-123]');

-- Insert test notification (replace resident_id with actual ID)
-- INSERT INTO notification (user_type_id, resident_id, title, body, deep_link)
-- VALUES (1, 1, 'Test Notification', 'This is a test notification', '/(tabs)/notifications');

-- ============================================
-- CLEANUP (if needed)
-- ============================================
-- Uncomment to drop all notification tables (USE WITH CAUTION!)
-- DROP TABLE IF EXISTS notification CASCADE;
-- DROP TABLE IF EXISTS push_device CASCADE;
-- DROP TABLE IF EXISTS user_type CASCADE;
