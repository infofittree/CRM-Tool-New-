import requests, json
BASE = 'https://crm-fittree.up.railway.app'
token = requests.post(f'{BASE}/api/v1/auth/login', json={'username': 'vaidehi', 'password': 'Vaidehi123'}, timeout=15).json()['access_token']
h = {'Authorization': f'Bearer {token}'}

r1 = requests.get(f'{BASE}/api/v1/followups/tasks?upcoming_days=7&max_today=5', headers=h, timeout=15)
tasks_before = r1.json()
overdue_before = len(tasks_before.get('overdue', []))
today_before = len(tasks_before.get('today_capped', []))
completed_before = len(tasks_before.get('completed', []))
print(f'Before: overdue={overdue_before}, today={today_before}, completed={completed_before}')

overdue = tasks_before.get('overdue', [])
if overdue:
    t = overdue[0]
    fid = t.get('followup_id')
    if fid:
        r2 = requests.post(f'{BASE}/api/v1/followups/{fid}/complete-activity', headers=h, json={
            'actions': ['call'], 'call_outcome': 'connected', 'customer_interest': 'interested',
            'notes': 'Test completion', 'followup_date': '2026-07-08', 'next_followup_mode': 'call'
        }, timeout=15)
        print(f'Complete: {r2.status_code}')
        if r2.status_code != 200:
            print(f'Error: {r2.text[:200]}')

r3 = requests.get(f'{BASE}/api/v1/followups/tasks?upcoming_days=7&max_today=5', headers=h, timeout=15)
tasks_after = r3.json()
overdue_after = len(tasks_after.get('overdue', []))
today_after = len(tasks_after.get('today_capped', []))
completed_after = len(tasks_after.get('completed', []))
print(f'After: overdue={overdue_after}, today={today_after}, completed={completed_after}')

# Show completed tasks
for ct in tasks_after.get('completed', [])[:5]:
    print(f'  Completed: lead={ct.get("lead_id")}, followup={ct.get("followup_id")}, company={str(ct.get("company_name",""))[:20]}, completed_by={ct.get("completed_by")}')
