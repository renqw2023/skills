#!/usr/bin/env python3
"""Fixed GoHighLevel API Test — reads credentials from secure storage.
Tests connection using contacts endpoint (most reliable)."""

import json
import urllib.request
import urllib.error
import sys

# Load credentials from secure storage
CREDENTIALS_PATH = "/data/.openclaw/credentials/image-generation-keys.json"

print("🔧 GoHighLevel Connection Test (Fixed)")
print("=" * 50)

# Load credentials
try:
    with open(CREDENTIALS_PATH, 'r') as f:
        creds = json.load(f)
    
    if 'highlevel' not in creds:
        print("❌ HIGHLEVEL credentials not found in storage")
        sys.exit(1)
    
    token = creds['highlevel']['api_key']
    location_id = creds['highlevel']['location_id']
    
    print(f"✓ Credentials loaded from secure storage")
    print(f"✓ Location ID: {location_id[:8]}...")
    
except Exception as e:
    print(f"❌ Error loading credentials: {e}")
    sys.exit(1)

# Test 1: List contacts (most reliable endpoint)
print("\n📝 Test 1: List Contacts")
print("-" * 50)

try:
    req = urllib.request.Request(
        f'https://services.leadconnectorhq.com/contacts/?locationId={location_id}&limit=1',
        headers={
            'Authorization': f'Bearer {token}',
            'Version': '2021-07-28'
        }
    )
    
    response = urllib.request.urlopen(req, timeout=10)
    data = json.loads(response.read())
    
    total_contacts = data.get('total', 0)
    print(f"✅ SUCCESS! Found {total_contacts} contacts")
    
except urllib.error.HTTPError as e:
    if e.code == 403:
        print("❌ 403 Forbidden - Token needs scopes enabled in GHL")
        print("\n🔧 TO FIX:")
        print("1. Go to app.gohighlevel.com")
        print("2. Settings → Private Integrations")
        print("3. Find 'Claude AI Assistant' integration")
        print("4. Click 'Edit Scopes'")
        print("5. ENABLE: contacts.readonly (and others you need)")
        print("6. Save - no need to regenerate token")
        sys.exit(1)
    elif e.code == 401:
        print("❌ 401 Unauthorized - Token is invalid or expired")
        sys.exit(1)
    else:
        print(f"❌ HTTP Error {e.code}: {e.reason}")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# Test 2: List calendars
print("\n📅 Test 2: List Calendars")
print("-" * 50)

try:
    req = urllib.request.Request(
        f'https://services.leadconnectorhq.com/calendars/?locationId={location_id}',
        headers={
            'Authorization': f'Bearer {token}',
            'Version': '2021-07-28'
        }
    )
    
    response = urllib.request.urlopen(req, timeout=10)
    data = json.loads(response.read())
    
    calendars = data.get('calendars', [])
    print(f"✅ SUCCESS! Found {len(calendars)} calendars")
    
except Exception as e:
    print(f"⚠️  Calendars test failed (may need calendars.readonly scope): {e}")

# Test 3: List opportunities
print("\n💼 Test 3: List Opportunities (Pipelines)")
print("-" * 50)

try:
    req = urllib.request.Request(
        f'https://services.leadconnectorhq.com/opportunities/?locationId={location_id}&limit=1',
        headers={
            'Authorization': f'Bearer {token}',
            'Version': '2021-07-28'
        }
    )
    
    response = urllib.request.urlopen(req, timeout=10)
    data = json.loads(response.read())
    
    total_opp = data.get('total', 0)
    print(f"✅ SUCCESS! Found {total_opp} opportunities")
    
except Exception as e:
    print(f"⚠️  Opportunities test failed (may need opportunities.readonly scope): {e}")

print("\n" + "=" * 50)
print("🎉 GoHighLevel API connection test complete!")
print("\n📋 Summary:")
print("- Contacts endpoint: WORKING ✅")
print("- If calendars/opportunities failed, enable those scopes in GHL")
print("\n💡 Next steps:")
print("- Use: python3 ghl-api.py search_contacts 'john'")
print("- Or: python3 ghl-api.py list_calendars")
