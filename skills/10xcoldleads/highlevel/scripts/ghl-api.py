#!/usr/bin/env python3
"""GoHighLevel API v2 Helper — supports all 39 endpoint groups.
Usage: python3 ghl-api.py <command> [args...]

Environment:
  HIGHLEVEL_TOKEN       — Private Integration Bearer token (required)
  HIGHLEVEL_LOCATION_ID — Sub-account Location ID (required)

Base URL: https://services.leadconnectorhq.com
All requests include: Authorization: Bearer <token>, Version: 2021-07-28
"""

import json, os, sys, time, urllib.request, urllib.error, urllib.parse

BASE = "https://services.leadconnectorhq.com"
VERSION = "2021-07-28"
MAX_RETRIES = 3

# Load credentials from secure storage
def _load_creds():
    """Load credentials from secure storage."""
    cred_path = "/data/.openclaw/credentials/image-generation-keys.json"
    try:
        with open(cred_path, 'r') as f:
            creds = json.load(f)
        hl = creds.get('highlevel', {})
        return hl.get('api_key', ''), hl.get('location_id', '')
    except:
        # Fallback to env vars
        return os.environ.get("HIGHLEVEL_TOKEN", ""), os.environ.get("HIGHLEVEL_LOCATION_ID", "")

TOKEN, LOC_ID = _load_creds()


def _headers():
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Version": VERSION,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _request(method, path, body=None, retries=MAX_RETRIES):
    """Make API request using curl (avoids Cloudflare blocks)."""
    import subprocess
    url = f"{BASE}{path}" if path.startswith("/") else f"{BASE}/{path}"
    
    cmd = [
        "curl", "-s", "-L",
        "-H", f"Authorization: Bearer {TOKEN}",
        "-H", f"Version: {VERSION}",
        "-H", "Content-Type: application/json",
        "-H", "Accept: application/json",
        "-H", "User-Agent: curl/7.68.0"
    ]
    
    if body:
        cmd.extend(["-d", json.dumps(body)])
    cmd.extend(["-X", method, url])
    
    for attempt in range(retries):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"error": "Invalid JSON response", "raw": result.stdout[:200]}
            else:
                if attempt < retries - 1:
                    time.sleep(1)
                    continue
                return {"error": result.returncode, "message": result.stderr}
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
                continue
            return {"error": str(e)}
    
    return {"error": "Max retries exceeded"}

# Old urllib implementation (kept for reference, not used)
def _request_old_urllib(method, path, body=None, retries=MAX_RETRIES):
    """Make API request with retry logic for 429/5xx errors. (Deprecated - use curl)"""
    url = f"{BASE}{path}" if path.startswith("/") else f"{BASE}/{path}"
    data = json.dumps(body).encode() if body else None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=_headers(), method=method)
            with urllib.request.urlopen(req) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else {"status": resp.status}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode() if e.fp else ""
            if e.code == 429 and attempt < retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"Rate limited (429). Retrying in {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            if e.code >= 500 and attempt < retries - 1:
                time.sleep(2)
                continue
            return {"error": e.code, "message": err_body}
        except Exception as ex:
            return {"error": str(ex)}
    return {"error": "Max retries exceeded"}


def _get(path):
    return _request("GET", path)


def _post(path, body=None):
    return _request("POST", path, body)


def _put(path, body=None):
    return _request("PUT", path, body)


def _delete(path):
    return _request("DELETE", path)


def _get_paginated(endpoint_base, params=None, max_pages=50):
    """
    Automatically paginate through all results.
    
    Args:
        endpoint_base: API endpoint path (e.g., "/contacts/")
        params: Dict of query parameters (will add locationId automatically)
        max_pages: Safety limit (default 50 = 5000 records max)
    
    Returns:
        Dict with "items" (all results), "total" (count), "pages" (pages fetched)
    """
    import subprocess
    
    all_items = []
    start_after = None
    start_after_id = None
    page = 1
    item_key = None  # Will detect from first response (contacts, opportunities, etc.)
    
    # Build base params
    base_params = {"locationId": LOC_ID, "limit": 100}
    if params:
        base_params.update(params)
    
    while page <= max_pages:
        # Build URL with current pagination
        url_params = base_params.copy()
        if start_after and start_after_id:
            url_params["startAfter"] = start_after
            url_params["startAfterId"] = start_after_id
        
        query_string = urllib.parse.urlencode(url_params)
        url = f"{BASE}{endpoint_base}?{query_string}"
        
        # Make request via curl
        cmd = [
            "curl", "-s", "-L",
            "-H", f"Authorization: Bearer {TOKEN}",
            "-H", f"Version: {VERSION}",
            "-H", "Accept: application/json",
            url
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                break
            
            data = json.loads(result.stdout)
            
            # Detect item key from first response
            if item_key is None:
                for key in data.keys():
                    if key != "meta" and key != "traceId" and isinstance(data[key], list):
                        item_key = key
                        break
            
            if item_key:
                items = data.get(item_key, [])
                all_items.extend(items)
            
            # Check for next page
            meta = data.get("meta", {})
            if not meta.get("nextPageUrl"):
                break
            
            start_after = meta.get("startAfter")
            start_after_id = meta.get("startAfterId")
            page += 1
            
        except Exception:
            break
    
    return {
        item_key or "items": all_items,
        "total": len(all_items),
        "pages": page,
        "endpoint": endpoint_base
    }


def _out(data):
    print(json.dumps(data, indent=2))


# ──────────────────────────────────────────────
# Setup & Connection
# ──────────────────────────────────────────────

def test_connection():
    """Verify token and location ID are working using contacts endpoint."""
    if not TOKEN:
        return {"error": "HIGHLEVEL_TOKEN not set. Check credentials file or run /highlevel-setup"}
    if not LOC_ID:
        return {"error": "HIGHLEVEL_LOCATION_ID not set. Check credentials file or run /highlevel-setup"}
    
    # Use contacts endpoint (most reliable, requires contacts.readonly scope)
    result = _get(f"/contacts/?locationId={LOC_ID}&limit=1")
    
    if "error" in result:
        error_code = result.get("error")
        if error_code == 403:
            return {
                "error": 403,
                "message": "Token needs scopes enabled in GHL",
                "fix": [
                    "1. Go to app.gohighlevel.com",
                    "2. Settings → Private Integrations",
                    "3. Find your 'Claude AI Assistant' integration",
                    "4. Click 'Edit Scopes'",
                    "5. ENABLE: contacts.readonly (and others needed)",
                    "6. Save - no need to regenerate token"
                ]
            }
        return result
    
    total = result.get("total", 0)
    return {
        "status": "connected",
        "locationId": LOC_ID,
        "totalContacts": total,
        "message": f"Successfully connected! Found {total} contacts."
    }


# ──────────────────────────────────────────────
# Contacts
# ──────────────────────────────────────────────

def search_contacts(query="", limit=20, paginate=True):
    """Search contacts by name, email, phone, or company.
    
    Args:
        query: Search term
        limit: Max results per page (default 20, max 100) - only used if paginate=False
        paginate: If True (default), fetch ALL contacts across all pages
    """
    if not paginate:
        params = urllib.parse.urlencode({"locationId": LOC_ID, "query": query, "limit": limit})
        return _get(f"/contacts/?{params}")
    
    # Auto-paginate to get all results
    params = {"query": query} if query else {}
    return _get_paginated("/contacts/", params)


def list_all_contacts():
    """Get ALL contacts with automatic pagination (convenience wrapper)."""
    return search_contacts(query="", limit=100, paginate=True)


def get_contact(contact_id):
    """Get full contact details by ID."""
    return _get(f"/contacts/{contact_id}")


def create_contact(data):
    """Create a new contact. data = JSON with firstName, lastName, email, phone, etc."""
    if isinstance(data, str):
        data = json.loads(data)
    data["locationId"] = LOC_ID
    return _post("/contacts/", data)


def update_contact(contact_id, data):
    """Update contact fields. data = JSON with fields to update."""
    if isinstance(data, str):
        data = json.loads(data)
    return _put(f"/contacts/{contact_id}", data)


def delete_contact(contact_id):
    """Delete a contact by ID."""
    return _delete(f"/contacts/{contact_id}")


def upsert_contact(data):
    """Create or update contact by email/phone match."""
    if isinstance(data, str):
        data = json.loads(data)
    data["locationId"] = LOC_ID
    return _post("/contacts/upsert", data)


def add_contact_tags(contact_id, tags):
    """Add tags to a contact. tags = JSON array of tag strings."""
    if isinstance(tags, str):
        tags = json.loads(tags)
    return _post(f"/contacts/{contact_id}/tags", {"tags": tags})


def remove_contact_tags(contact_id, tags):
    """Remove tags from a contact."""
    if isinstance(tags, str):
        tags = json.loads(tags)
    return _delete(f"/contacts/{contact_id}/tags")


# ──────────────────────────────────────────────
# Conversations & Messaging
# ──────────────────────────────────────────────

def list_conversations(limit=20):
    """List recent conversations."""
    params = urllib.parse.urlencode({"locationId": LOC_ID, "limit": limit})
    return _get(f"/conversations/search?{params}")


def get_conversation(conversation_id):
    """Get a specific conversation."""
    return _get(f"/conversations/{conversation_id}")


def send_message(contact_id, message, msg_type="SMS"):
    """Send a message to a contact. msg_type: SMS, Email, WhatsApp, FB, IG, Live_Chat."""
    body = {
        "type": msg_type,
        "contactId": contact_id,
        "message": message,
    }
    return _post("/conversations/messages", body)


# ──────────────────────────────────────────────
# Calendars & Appointments
# ──────────────────────────────────────────────

def list_calendars():
    """List all calendars for this location."""
    params = urllib.parse.urlencode({"locationId": LOC_ID})
    return _get(f"/calendars/?{params}")


def get_free_slots(calendar_id, start_date, end_date):
    """Get available booking slots. Dates in YYYY-MM-DD format."""
    params = urllib.parse.urlencode({
        "startDate": start_date,
        "endDate": end_date,
    })
    return _get(f"/calendars/{calendar_id}/free-slots?{params}")


def create_appointment(calendar_id, data):
    """Create a calendar appointment."""
    if isinstance(data, str):
        data = json.loads(data)
    data["calendarId"] = calendar_id
    data["locationId"] = LOC_ID
    return _post("/calendars/events", data)


# ──────────────────────────────────────────────
# Opportunities & Pipelines
# ──────────────────────────────────────────────

def list_opportunities(pipeline_id=None, limit=20, paginate=True):
    """List opportunities. Optionally filter by pipeline.
    
    Args:
        pipeline_id: Filter by specific pipeline
        limit: Max per page (only if paginate=False)
        paginate: If True (default), fetch ALL opportunities
    """
    if not paginate:
        params = {"locationId": LOC_ID, "limit": limit}
        if pipeline_id:
            params["pipelineId"] = pipeline_id
        return _get(f"/opportunities/search?{urllib.parse.urlencode(params)}")
    
    params = {}
    if pipeline_id:
        params["pipelineId"] = pipeline_id
    return _get_paginated("/opportunities/search", params)


def get_opportunity(opp_id):
    """Get opportunity by ID."""
    return _get(f"/opportunities/{opp_id}")


def create_opportunity(data):
    """Create a new opportunity."""
    if isinstance(data, str):
        data = json.loads(data)
    data["locationId"] = LOC_ID
    return _post("/opportunities/", data)


def list_pipelines():
    """List all pipelines and their stages."""
    return _get(f"/opportunities/pipelines?locationId={LOC_ID}")


# ──────────────────────────────────────────────
# Workflows & Campaigns
# ──────────────────────────────────────────────

def list_workflows(paginate=True):
    """List all workflows.
    
    Args:
        paginate: If True (default), fetch ALL workflows
    """
    if not paginate:
        return _get(f"/workflows/?locationId={LOC_ID}")
    return _get_paginated("/workflows/")


def add_to_workflow(contact_id, workflow_id):
    """Add a contact to a workflow."""
    return _post(f"/contacts/{contact_id}/workflow/{workflow_id}", {
        "eventStartTime": ""
    })


def remove_from_workflow(contact_id, workflow_id):
    """Remove a contact from a workflow."""
    return _delete(f"/contacts/{contact_id}/workflow/{workflow_id}")


def list_campaigns(paginate=True):
    """List all campaigns.
    
    Args:
        paginate: If True (default), fetch ALL campaigns
    """
    if not paginate:
        return _get(f"/campaigns/?locationId={LOC_ID}")
    return _get_paginated("/campaigns/")


# ──────────────────────────────────────────────
# Invoices
# ──────────────────────────────────────────────

def list_invoices(limit=20, paginate=True):
    """List invoices.
    
    Args:
        limit: Max per page (only if paginate=False)
        paginate: If True (default), fetch ALL invoices
    """
    if not paginate:
        params = urllib.parse.urlencode({"locationId": LOC_ID, "limit": limit})
        return _get(f"/invoices/?{params}")
    return _get_paginated("/invoices/")


def get_invoice(invoice_id):
    """Get invoice details."""
    return _get(f"/invoices/{invoice_id}")


def create_invoice(data):
    """Create a new invoice."""
    if isinstance(data, str):
        data = json.loads(data)
    data["altId"] = LOC_ID
    data["altType"] = "location"
    return _post("/invoices/", data)


# ──────────────────────────────────────────────
# Payments
# ──────────────────────────────────────────────

def list_orders(limit=20, paginate=True):
    """List payment orders.
    
    Args:
        limit: Max per page (only if paginate=False)
        paginate: If True (default), fetch ALL orders
    """
    if not paginate:
        params = urllib.parse.urlencode({"locationId": LOC_ID, "limit": limit})
        return _get(f"/payments/orders/?{params}")
    return _get_paginated("/payments/orders/")


def list_transactions(limit=20, paginate=True):
    """List payment transactions.
    
    Args:
        limit: Max per page (only if paginate=False)
        paginate: If True (default), fetch ALL transactions
    """
    if not paginate:
        params = urllib.parse.urlencode({"locationId": LOC_ID, "limit": limit})
        return _get(f"/payments/transactions/?{params}")
    return _get_paginated("/payments/transactions/")


def list_subscriptions(limit=20, paginate=True):
    """List payment subscriptions.
    
    Args:
        limit: Max per page (only if paginate=False)
        paginate: If True (default), fetch ALL subscriptions
    """
    if not paginate:
        params = urllib.parse.urlencode({"locationId": LOC_ID, "limit": limit})
        return _get(f"/payments/subscriptions/?{params}")
    return _get_paginated("/payments/subscriptions/")


# ──────────────────────────────────────────────
# Products
# ──────────────────────────────────────────────

def list_products(limit=20, paginate=True):
    """List products.
    
    Args:
        limit: Max per page (only if paginate=False)
        paginate: If True (default), fetch ALL products
    """
    if not paginate:
        params = urllib.parse.urlencode({"locationId": LOC_ID, "limit": limit})
        return _get(f"/products/?{params}")
    return _get_paginated("/products/")


def get_product(product_id):
    """Get product details."""
    return _get(f"/products/{product_id}")


# ──────────────────────────────────────────────
# Forms, Surveys, Funnels
# ──────────────────────────────────────────────

def list_forms(paginate=True):
    """List all forms.
    
    Args:
        paginate: If True (default), fetch ALL forms
    """
    if not paginate:
        return _get(f"/forms/?locationId={LOC_ID}")
    return _get_paginated("/forms/")


def list_form_submissions(form_id, limit=20, paginate=True):
    """Get form submissions.
    
    Args:
        form_id: The form ID to get submissions for
        limit: Max per page (only if paginate=False)
        paginate: If True (default), fetch ALL submissions
    """
    if not paginate:
        params = urllib.parse.urlencode({"locationId": LOC_ID, "limit": limit})
        return _get(f"/forms/submissions?{params}&formId={form_id}")
    
    params = {"formId": form_id}
    return _get_paginated("/forms/submissions", params)


def list_surveys(paginate=True):
    """List all surveys.
    
    Args:
        paginate: If True (default), fetch ALL surveys
    """
    if not paginate:
        return _get(f"/surveys/?locationId={LOC_ID}")
    return _get_paginated("/surveys/")


def list_funnels(paginate=True):
    """List all funnels.
    
    Args:
        paginate: If True (default), fetch ALL funnels
    """
    if not paginate:
        return _get(f"/funnels/funnel/list?locationId={LOC_ID}")
    return _get_paginated("/funnels/funnel/list")


# ──────────────────────────────────────────────
# Social Media Planner
# ──────────────────────────────────────────────

def list_social_posts(limit=20):
    """List social media posts."""
    return _post(f"/social-media-posting/{LOC_ID}/posts/list", {
        "limit": limit, "skip": 0
    })


def create_social_post(data):
    """Create a social media post."""
    if isinstance(data, str):
        data = json.loads(data)
    return _post(f"/social-media-posting/{LOC_ID}/posts", data)


# ──────────────────────────────────────────────
# Media, Users, Links
# ──────────────────────────────────────────────

def list_media():
    """List media files."""
    return _get(f"/medias/files?locationId={LOC_ID}")


def list_users():
    """List users for this location."""
    return _get(f"/users/?locationId={LOC_ID}")


def list_trigger_links():
    """List trigger links."""
    return _get(f"/links/?locationId={LOC_ID}")


# ──────────────────────────────────────────────
# Safe Specific Functions (Replacing custom_request)
# ──────────────────────────────────────────────

def get_location_details():
    """Get current location details."""
    return _get(f"/locations/{LOC_ID}")


def list_location_custom_fields():
    """List custom fields for this location."""
    return _get(f"/locations/{LOC_ID}/customFields")


def list_location_tags():
    """List tags for this location."""
    return _get(f"/locations/{LOC_ID}/tags")


def list_location_custom_values():
    """List custom values for this location."""
    return _get(f"/locations/{LOC_ID}/customValues")


def list_courses():
    """List courses/memberships."""
    return _get(f"/courses/?locationId={LOC_ID}")


def list_snapshots():
    """List available snapshots (Agency only)."""
    return _get("/snapshots/")


def get_snapshot_status(snapshot_id):
    """Get snapshot installation status."""
    return _get(f"/snapshots/{snapshot_id}/status")


# ──────────────────────────────────────────────
# CLI Router
# ──────────────────────────────────────────────

COMMANDS = {
    "test_connection": lambda: test_connection(),
    "search_contacts": lambda: search_contacts(sys.argv[2] if len(sys.argv) > 2 else ""),
    "list_all_contacts": lambda: list_all_contacts(),
    "get_contact": lambda: get_contact(sys.argv[2]),
    "create_contact": lambda: create_contact(sys.argv[2]),
    "update_contact": lambda: update_contact(sys.argv[2], sys.argv[3]),
    "delete_contact": lambda: delete_contact(sys.argv[2]),
    "upsert_contact": lambda: upsert_contact(sys.argv[2]),
    "add_contact_tags": lambda: add_contact_tags(sys.argv[2], sys.argv[3]),
    "list_conversations": lambda: list_conversations(),
    "get_conversation": lambda: get_conversation(sys.argv[2]),
    "send_message": lambda: send_message(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "SMS"),
    "list_calendars": lambda: list_calendars(),
    "get_free_slots": lambda: get_free_slots(sys.argv[2], sys.argv[3], sys.argv[4]),
    "create_appointment": lambda: create_appointment(sys.argv[2], sys.argv[3]),
    "list_opportunities": lambda: list_opportunities(),
    "get_opportunity": lambda: get_opportunity(sys.argv[2]),
    "create_opportunity": lambda: create_opportunity(sys.argv[2]),
    "list_pipelines": lambda: list_pipelines(),
    "list_workflows": lambda: list_workflows(),
    "add_to_workflow": lambda: add_to_workflow(sys.argv[2], sys.argv[3]),
    "remove_from_workflow": lambda: remove_from_workflow(sys.argv[2], sys.argv[3]),
    "list_campaigns": lambda: list_campaigns(),
    "list_invoices": lambda: list_invoices(),
    "get_invoice": lambda: get_invoice(sys.argv[2]),
    "create_invoice": lambda: create_invoice(sys.argv[2]),
    "list_orders": lambda: list_orders(),
    "list_transactions": lambda: list_transactions(),
    "list_subscriptions": lambda: list_subscriptions(),
    "list_products": lambda: list_products(),
    "get_product": lambda: get_product(sys.argv[2]),
    "list_forms": lambda: list_forms(),
    "list_form_submissions": lambda: list_form_submissions(sys.argv[2]),
    "list_surveys": lambda: list_surveys(),
    "list_funnels": lambda: list_funnels(),
    "list_social_posts": lambda: list_social_posts(),
    "create_social_post": lambda: create_social_post(sys.argv[2]),
    "list_media": lambda: list_media(),
    "list_users": lambda: list_users(),
    "list_trigger_links": lambda: list_trigger_links(),
    "get_location_details": lambda: get_location_details(),
    "list_location_custom_fields": lambda: list_location_custom_fields(),
    "list_location_tags": lambda: list_location_tags(),
    "list_location_custom_values": lambda: list_location_custom_values(),
    "list_courses": lambda: list_courses(),
    "list_snapshots": lambda: list_snapshots(),
    "get_snapshot_status": lambda: get_snapshot_status(sys.argv[2]),
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Commands: {', '.join(sorted(COMMANDS.keys()))}")
        sys.exit(1)
    _out(COMMANDS[sys.argv[1]]())
