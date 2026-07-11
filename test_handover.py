import requests, json

BASE = "https://crm-fittree.up.railway.app"

def login(username, password):
    r = requests.post(f"{BASE}/api/v1/auth/login", json={"username": username, "password": password}, timeout=15)
    return r.json()["access_token"] if r.status_code == 200 else None

# Login as Rahul (Salesperson)
token = login("rahul", "Rahul123")
h = {"Authorization": f"Bearer {token}"}

# Get Rahul's leads to find one to transfer
r = requests.get(f"{BASE}/api/v1/leads?page=1&page_size=3", headers=h, timeout=15)
leads = r.json().get("items", [])
print(f"Rahul has {r.json().get('total', 0)} leads")

if leads:
    lead = leads[0]
    lead_id = lead["lead_id"]
    print(f"\n--- Testing handover for {lead_id} ({lead.get('company_name', 'N/A')}) ---")

    # Create handover
    r2 = requests.post(f"{BASE}/api/v1/leads/{lead_id}/handover", headers=h, json={
        "to_user": "Vaidehi",
        "reason": "product_expertise",
        "notes": "Vaidehi has better expertise in this product category"
    }, timeout=15)
    print(f"1. Create handover: {r2.status_code}")
    if r2.status_code == 201:
        handover_id = r2.json()["id"]
        print(f"   Handover ID: {handover_id}, Status: {r2.json()['status']}")

        # Login as Vaidehi (recipient)
        token2 = login("vaidehi", "Vaidehi123")
        h2 = {"Authorization": f"Bearer {token2}"}

        # Check pending handovers
        r3 = requests.get(f"{BASE}/api/v1/me/handovers", headers=h2, timeout=15)
        print(f"2. Vaidehi pending: {r3.status_code}, count: {len(r3.json())}")

        # Accept
        r4 = requests.post(f"{BASE}/api/v1/handovers/{handover_id}/accept", headers=h2, timeout=15)
        print(f"3. Accept: {r4.status_code}, status: {r4.json().get('status', '')}")

        # Verify lead ownership changed
        r5 = requests.get(f"{BASE}/api/v1/leads/{lead_id}", headers=h, timeout=15)
        if r5.status_code == 200:
            print(f"4. Lead assigned_to: {r5.json().get('assigned_to', 'N/A')}")

        # Check handover history
        r6 = requests.get(f"{BASE}/api/v1/leads/{lead_id}/handovers", headers=h, timeout=15)
        print(f"5. Handover history: {len(r6.json())} entries")
    else:
        print(f"   Error: {r2.text[:200]}")

    # Test duplicate prevention
    r7 = requests.post(f"{BASE}/api/v1/leads/{lead_id}/handover", headers=h, json={
        "to_user": "Vaidehi", "reason": "workload"
    }, timeout=15)
    print(f"\n6. Duplicate handover: {r7.status_code} (should be 400)")
