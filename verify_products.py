import requests
BASE = "https://crm-fittree.up.railway.app"

# Test products endpoint
r = requests.get(f"{BASE}/api/v1/products", timeout=15)
print(f"Products endpoint: {r.status_code}")
if r.status_code == 200:
    products = r.json()
    print(f"Product count: {len(products)}")
    for p in products[:5]:
        print(f"  {p['name']} ({p['category']})")
    if len(products) > 5:
        print(f"  ... and {len(products) - 5} more")

# Test lead creation with product
r2 = requests.post(f"{BASE}/api/v1/auth/login", json={"username": "vaidehi", "password": "Vaidehi123"}, timeout=15)
token = r2.json()["access_token"]
h = {"Authorization": f"Bearer {token}"}

r3 = requests.post(f"{BASE}/api/v1/leads", headers=h, json={
    "company_name": "Product Test Corp",
    "contact_person": "Test User",
    "country": "India",
    "lead_source": "Website",
    "lead_category": "B",
    "product_ids": [1, 3],
    "next_action_plan": "Test product linking",
    "next_follow_up": "2026-07-10",
}, timeout=15)
print(f"\nCreate lead with products: {r3.status_code}")
if r3.status_code == 201:
    lead_id = r3.json()["lead_id"]
    print(f"Lead ID: {lead_id}")
    # Verify lead has product_interest populated
    r4 = requests.get(f"{BASE}/api/v1/leads/{lead_id}", headers=h, timeout=15)
    if r4.status_code == 200:
        lead = r4.json()
        print(f"Product interest: {lead.get('product_interest')}")
        print(f"Product IDs: {lead.get('product_ids')}")
    # Clean up
    requests.delete(f"{BASE}/api/v1/leads/{lead_id}", headers=h, timeout=15)
else:
    print(f"Error: {r3.text[:200]}")
