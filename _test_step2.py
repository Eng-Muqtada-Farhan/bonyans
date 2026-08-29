import requests
import os
from dotenv import load_dotenv; load_dotenv()
ADMIN_PW = os.environ.get('ADMIN_PASSWORD', '')

API = 'http://127.0.0.1:8000'
tests = []

def ok(name, passed, detail=''):
    sym = '[PASS]' if passed else '[FAIL]'
    tests.append(f"{sym} {name}" + (f": {detail}" if detail else ""))

# POST /login
r = requests.post(f'{API}/login', json={'username': 'admin', 'password': ADMIN_PW})
ok('POST /login', r.status_code == 200)
token = r.json().get('token', '') if r.ok else ''

# GET /companies
r = requests.get(f'{API}/companies')
ok('GET /companies', r.status_code == 200, f'{len(r.json())} results')

# GET /admin/companies
r = requests.get(f'{API}/admin/companies')
ok('GET /admin/companies', r.status_code == 200, f'{len(r.json())} results')

# verification_status in companies response
if r.ok and r.json():
    ok('verification_status in companies response', 'verification_status' in r.json()[0])
    cid = r.json()[0]['id']

    # PUT /companies/{id}/status
    r2 = requests.put(
        f'{API}/companies/{cid}/status',
        json={'status': 'approved'},
        headers={'Authorization': token}
    )
    ok('PUT /companies/{id}/status (approve)', r2.status_code == 200, r2.json())

    # PUT /companies/{id} (edit)
    r3 = requests.put(
        f'{API}/companies/{cid}',
        json={'city': 'Baghdad'},
        headers={'Authorization': token}
    )
    ok('PUT /companies/{id} (edit)', r3.status_code == 200)

# POST /upload (1x1 PNG)
import base64
png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')
r = requests.post(f'{API}/upload', files={'file': ('t.png', png, 'image/png')})
ok('POST /upload (ImageKit)', r.status_code == 200 and 'url' in r.json())

# Invalid token still rejected
r = requests.put(f'{API}/companies/1/status', json={'status': 'approved'}, headers={'Authorization': 'bad'})
ok('Invalid token still rejected', r.status_code == 401)

for t in tests:
    print(t)

passed = sum(1 for t in tests if '[PASS]' in t)
print(f'\nResult: {passed}/{len(tests)} passed')
