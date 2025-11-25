"""
Quick test script to verify get_specific_resident function works
Run with: python test_resident_detail.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lambo.settings')
django.setup()

from secretary_module.models import ResidentList

# Test with the first resident (you may need to adjust the ID)
print("Testing get_specific_resident function...")
print("=" * 60)

# Test with a few resident IDs
for resident_id in [1, 2, 3]:
    print(f"\nTesting resident_id = {resident_id}")
    try:
        result = ResidentList.sp_get_specific_resident(resident_id)
        if result:
            print(f"✓ Success! Found resident:")
            print(f"  - Resident Code: {result.get('resident_code')}")
            print(f"  - Full Name: {result.get('full_name')}")
            print(f"  - DOB: {result.get('dob')}")
            print(f"  - Age: {result.get('age')}")
            print(f"  - Sex: {result.get('sex')}")
            print(f"  - Phone: {result.get('phone_number')}")
            print(f"  - Email: {result.get('email')}")
            print(f"  - Status: {result.get('resident_status')}")
            print(f"  - Full Address: {result.get('full_address')}")
            print(f"  - Civil Status: {result.get('civil_status')}")
            print(f"  - Educational Attainment: {result.get('educational_attainment')}")
            print(f"  - Religion: {result.get('religion')}")
            print(f"  - Occupation: {result.get('occupation')}")
            print(f"  - Nationality: {result.get('nationality')}")
            print(f"  - Employment Status: {result.get('employment_status')}")
            print(f"  - Household Number: {result.get('household_number')}")
            print(f"  - Family Code: {result.get('family_code')}")
            break  # Exit after first successful result
        else:
            print(f"  ✗ Resident not found")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 60)
print("Test complete!")
