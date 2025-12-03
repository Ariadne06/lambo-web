# Notifications Module - Implementation Guide

## Overview

Complete push notification system for LAMBO mobile app (resident-side). This system allows sending real-time push notifications to users about certificate approvals, announcements, payment confirmations, and more.

## ✅ Completed Setup

### Backend (Django)

1. **Created `notifications` app** with the following structure:

   - `models.py` - Django ORM models (structure only, managed=False)
   - `repo.py` - Raw SQL database operations (9 functions)
   - `service.py` - Push notification business logic
   - `views.py` - REST API endpoints (4 views)
   - `urls.py` - URL routing
   - `admin.py` - Admin panel configuration

2. **Installed dependencies**:

   - `exponent-server-sdk==2.1.0` ✅

3. **Registered app**:
   - Added `'notifications'` to `INSTALLED_APPS` in `settings.py` ✅
   - Added URLs to main `urls.py` at `/api/notifications/` ✅

### Mobile (React Native/Expo)

1. **Installed packages**:

   - `expo-notifications` ✅
   - `expo-device` ✅
   - `expo-constants` ✅

2. **Created utility files**:

   - `utils/pushNotifications.ts` - Push token registration & listeners
   - `utils/notificationService.ts` - API calls for notifications
   - `components/NotificationBell.tsx` - Bell icon with badge
   - `context/notificationContext.tsx` - Global notification state

3. **Created UI**:

   - `app/(tabs)/notifications.tsx` - Full notifications screen
   - Added bell icon to tab bar ✅
   - Added bell icon to main menu header with badge ✅

4. **Updated configuration**:
   - `constants/apiConfig.ts` - Added notification endpoints ✅
   - `app.json` - Configured notification plugin ✅
   - `app/_layout.tsx` - Wrapped app with NotificationProvider ✅

## 📊 Database Schema

### Tables Required

Run this SQL to create the necessary tables:

```sql
-- User types table
CREATE TABLE user_type (
    user_type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default user types
INSERT INTO user_type (type_name, description) VALUES
('RESIDENT', 'Regular resident users'),
('PERSONNEL', 'Barangay personnel (BHW, Nurse, etc.)');

-- Push device tokens
CREATE TABLE push_device (
    push_device_id SERIAL PRIMARY KEY,
    user_type_id INTEGER NOT NULL REFERENCES user_type(user_type_id) ON DELETE CASCADE,
    resident_id INTEGER,
    personnel_id INTEGER,
    platform VARCHAR(20) NOT NULL CHECK (platform IN ('ios', 'android')),
    expo_push_token TEXT NOT NULL,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_resident FOREIGN KEY (resident_id) REFERENCES resident(resident_id) ON DELETE CASCADE,
    CONSTRAINT fk_personnel FOREIGN KEY (personnel_id) REFERENCES personnel(personnel_id) ON DELETE CASCADE,
    CONSTRAINT check_user_id CHECK (
        (resident_id IS NOT NULL AND personnel_id IS NULL) OR
        (resident_id IS NULL AND personnel_id IS NOT NULL)
    )
);

CREATE INDEX idx_push_device_resident ON push_device(resident_id);
CREATE INDEX idx_push_device_personnel ON push_device(personnel_id);
CREATE INDEX idx_push_device_token ON push_device(expo_push_token);

-- Notifications
CREATE TABLE notification (
    notification_id SERIAL PRIMARY KEY,
    user_type_id INTEGER NOT NULL REFERENCES user_type(user_type_id) ON DELETE CASCADE,
    resident_id INTEGER,
    personnel_id INTEGER,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    deep_link TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notification_resident FOREIGN KEY (resident_id) REFERENCES resident(resident_id) ON DELETE CASCADE,
    CONSTRAINT fk_notification_personnel FOREIGN KEY (personnel_id) REFERENCES personnel(personnel_id) ON DELETE CASCADE,
    CONSTRAINT check_notification_user CHECK (
        (resident_id IS NOT NULL AND personnel_id IS NULL) OR
        (resident_id IS NULL AND personnel_id IS NOT NULL)
    )
);

CREATE INDEX idx_notification_resident ON notification(resident_id, is_read, created_at DESC);
CREATE INDEX idx_notification_personnel ON notification(personnel_id, is_read, created_at DESC);
CREATE INDEX idx_notification_created ON notification(created_at DESC);
```

## 🔧 API Endpoints

All endpoints are prefixed with `/api/notifications/`

### 1. Register Push Token

**POST** `/register-push-token/`

Register or update a device's Expo push token.

**Request Body:**

```json
{
  "user_type": "RESIDENT",
  "resident_id": 1,
  "expo_push_token": "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
  "platform": "android"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Push token registered successfully",
  "push_device_id": 1
}
```

### 2. Get Notifications

**GET** `/get-notifications/?user_type=RESIDENT&resident_id=1&limit=50`

Get all notifications for a user.

**Response:**

```json
{
  "success": true,
  "notifications": [
    {
      "notification_id": 1,
      "title": "Certificate Approved",
      "body": "Your Barangay Clearance has been approved",
      "deep_link": "/(tabs)/documents/123",
      "is_read": false,
      "created_at": "2025-12-03T10:30:00Z"
    }
  ],
  "unread_count": 5
}
```

### 3. Mark Notification as Read

**POST** `/mark-read/`

Mark a single notification as read.

**Request Body:**

```json
{
  "notification_id": 1
}
```

### 4. Mark All Notifications as Read

**POST** `/mark-all-read/`

Mark all notifications for a user as read.

**Request Body:**

```json
{
  "user_type": "RESIDENT",
  "resident_id": 1
}
```

## 🚀 Usage Examples

### Backend - Send Notification to Resident

```python
from notifications.service import notify_certificate_approved, notify_new_announcement

# When certificate is approved
notify_certificate_approved(
    resident_id=123,
    certificate_type="Barangay Clearance",
    application_id=456
)

# Send announcement to all residents
notify_new_announcement(
    title="Community Meeting",
    message="Please attend the barangay meeting on Dec 5, 2025 at 2PM",
    deep_link="/(tabs)/announcement"
)
```

### Mobile - Handling Notifications

The notification system automatically handles:

- ✅ Token registration on login
- ✅ Badge count updates
- ✅ Deep linking when tapping notifications
- ✅ Real-time notification updates
- ✅ Foreground notification display

Users can:

- View all notifications in the notifications screen
- See unread count badge on bell icon and tab bar
- Tap notifications to navigate to related content
- Mark individual or all notifications as read
- Pull to refresh notification list

## 🔔 Deep Linking

Notifications can include a `deep_link` field to navigate users to specific screens:

```python
# Examples of deep links
"/(tabs)/documents/123"           # Document details
"/(tabs)/transactions/456"        # Transaction details
"/(tabs)/profile/profile"         # Profile page
"/(tabs)/announcement"            # Announcements page
"/(tabs)/health/health"           # Health records
```

## 🧪 Testing

### Test Push Notification Manually (Backend)

```python
# In Django shell (python manage.py shell)
from notifications.service import NotificationService

service = NotificationService()
service.send_to_resident(
    resident_id=1,
    title="Test Notification",
    body="This is a test push notification",
    deep_link="/(tabs)/notifications"
)
```

### Test on Physical Device

1. Build and install app on physical device (push notifications don't work on emulator)
2. Login as a resident
3. Check that token is registered in `push_device` table
4. Send test notification from backend
5. Verify notification appears on device

## 📱 Next Steps

### For Personnel (BHW/Nurse)

- [ ] Update BHW/Nurse layouts to include notification bell
- [ ] Add notifications screen to personnel routes
- [ ] Send notifications for:
  - New household assignments
  - Health record updates
  - Task reminders

### Additional Features

- [ ] Notification preferences (allow users to enable/disable types)
- [ ] Scheduled notifications
- [ ] In-app notification sound customization
- [ ] Notification categories (certificates, health, announcements)

## 🐛 Troubleshooting

### Push tokens not saving

- Check that user is logged in before token registration
- Verify `resident_id` exists in database
- Check console logs for errors

### Notifications not received

- Ensure testing on physical device (not emulator)
- Check Expo push token is valid format
- Verify device has internet connection
- Check notification permissions are granted

### Badge count not updating

- The bell icon refreshes every 30 seconds
- It also refreshes when screen comes into focus
- You can force refresh by navigating away and back

## 📝 Files Created

### Backend

- `notifications/__init__.py`
- `notifications/apps.py`
- `notifications/models.py`
- `notifications/admin.py`
- `notifications/repo.py` ⭐ (Core database operations)
- `notifications/service.py` ⭐ (Push notification logic)
- `notifications/views.py` ⭐ (REST API)
- `notifications/urls.py`
- `notifications/tests.py`

### Mobile

- `utils/pushNotifications.ts` ⭐
- `utils/notificationService.ts` ⭐
- `app/(tabs)/notifications.tsx` ⭐ (Main screen)
- `components/NotificationBell.tsx` ⭐
- `context/notificationContext.tsx` ⭐

## ✨ Features

✅ Real-time push notifications
✅ Badge count on bell icon
✅ Deep linking to specific screens
✅ Mark individual/all as read
✅ Pull to refresh
✅ Automatic token registration on login
✅ Beautiful UI with unread indicators
✅ Time formatting (e.g., "2h ago", "Just now")
✅ Empty state design
✅ Error handling
✅ Broadcast to all residents
✅ Admin panel for managing notifications

---

**Status:** ✅ Complete and ready to test!
**Next:** Create database tables and test on physical device
