import requests
BASE = 'https://crm-fittree.up.railway.app'
r = requests.post(f'{BASE}/api/v1/auth/login', json={'username': 'vaidehi', 'password': 'Vaidehi123'}, timeout=15)
token = r.json()['access_token']
h = {'Authorization': f'Bearer {token}'}
r2 = requests.get(f'{BASE}/api/v1/users', headers=h, timeout=15)
print(f'Status: {r2.status_code}')
if r2.status_code == 200:
    users = r2.json()
    for u in users:
        name = u['full_name']
        role = u['role']
        active = u.get('is_active', '?')
        print(f'  {name} ({role}) active={active}')
    print(f'\nTotal users: {len(users)}')
    non_proc = [u for u in users if u['role'] != 'Procurement']
    print(f'Non-Procurement: {len(non_proc)}')
