import requests, json
BASE = 'https://crm-fittree.up.railway.app'
for user, pw in [('vaidehi','Vaidehi123'),('shiksha','Shiksha123'),('rahul','Rahul123')]:
    r = requests.post(f'{BASE}/api/v1/auth/login', json={'username': user, 'password': pw}, timeout=15)
    token = r.json()['access_token']
    h = {'Authorization': f'Bearer {token}'}
    r2 = requests.get(f'{BASE}/api/v1/followups/tasks?upcoming_days=7&max_today=5', headers=h, timeout=15)
    tasks = r2.json()
    overdue = tasks.get('overdue', [])[:2]
    print(f'--- {user} ---')
    for t in overdue:
        print(f'  lead={t.get("lead_id")} followup={t.get("followup_id")} assigned={t.get("assigned_to")} company={t.get("company_name","")[:20]}')
