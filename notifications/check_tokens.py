"""
Check registered push tokens in the database
Run with: python manage.py shell < notifications/check_tokens.py
"""

from notifications.repo import get_user_push_tokens

print("\n" + "="*60)
print("🔍 Checking Push Tokens")
print("="*60)

# Check for resident_id 57
print("\n📱 Checking tokens for resident_id: 57")
tokens = get_user_push_tokens(user_type='RESIDENT', resident_id=57, personnel_id=None)
if tokens:
    print(f"✅ Found {len(tokens)} token(s):")
    for token in tokens:
        print(f"   - {token}")
else:
    print("❌ No tokens found")
    print("\nℹ️  The mobile app needs to:")
    print("   1. Request notification permissions")
    print("   2. Get Expo push token")
    print("   3. Call POST /api/notifications/register-push-token/")
    print("\n   Check mobile app logs for 'Expo push token' messages")

print("\n" + "="*60 + "\n")
