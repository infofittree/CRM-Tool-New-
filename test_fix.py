import requests
BASE = "https://crm-fittree.up.railway.app"
r = requests.post(f"{BASE}/api/v1/auth/login", json={"username": "vaidehi", "password": "Vaidehi123"}, timeout=15)
token = r.json()["access_token"]
h = {"Authorization": f"Bearer {token}"}
r2 = requests.post(f"{BASE}/api/v1/leads", headers=h, json={
    "company_name": "Test Fix Verify",
    "contact_person": "Test User",
    "lead_source": "Website",
    "lead_category": "B",
    "next_action_plan": "Test",
    "next_follow_up": "2026-07-10"
}, timeout=15)
print(f"Create: {r2.status_code}")
if r2.status_code == 201:
    lid = r2.json()["lead_id"]
    print(f"Created: {lid}")
    requests.delete(f"{BASE}/api/v1/leads/{lid}", headers=h, timeout=15)
    print("Cleaned up")
else:
    print(f"Error: {r2.text[:300]}")
