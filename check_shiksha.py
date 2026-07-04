import requests
BASE = 'https://crm-fittree.up.railway.app'

# Test creating followup as shiksha (Admin) for vaidehi's lead
r = requests.post(f'{BASE}/api/v1/auth/login', json={'username': 'shiksha', 'password': 'Shiksha123'}, timeout=15)
token = r.json()['access_token']
h = {'Authorization': f'Bearer {token}'}

# Create followup for lead assigned to vaidehi
r2 = requests.post(f'{BASE}/api/v1/followups', headers=h, json={
    'lead_id': 'FT-2026-0199',
    'followup_date': '2026-07-02',
    'next_followup': '2026-07-04',
    'discussion': 'Test',
    'next_action': 'Call Again',
}, timeout=15)
print(f'Shiksha create followup: {r2.status_code} {r2.text[:300]}')

if r2.status_code == 201:
    fid = r2.json()['followup_id']
    r3 = requests.post(f'{BASE}/api/v1/followups/{fid}/complete-activity', headers=h, json={
        'actions': ['call'],
        'call_outcome': 'connected',
        'customer_interest': 'interested',
        'notes': 'Test completion',
        'followup_date': '2026-07-05',
        'next_followup_mode': 'call',
    }, timeout=15)
    print(f'Shiksha complete activity: {r3.status_code} {r3.text[:300]}')
