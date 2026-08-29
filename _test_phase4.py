import requests, base64

API = 'http://127.0.0.1:8000'
results = []

def ok(name, passed, detail=''):
    sym = 'PASS' if passed else 'FAIL'
    suffix = (': ' + str(detail)) if detail else ''
    results.append(f'[{sym}] {name}{suffix}')

# 1. Login
r = requests.post(f'{API}/login', json={'username': 'admin', 'password': '26'})
ok('Login', r.status_code == 200, r.status_code)
token = r.json().get('token', '') if r.ok else ''
ok('JWT token returned', bool(token), (token[:40] + '...') if token else 'NONE')

# 2. GET /companies
r = requests.get(f'{API}/companies')
ok('GET /companies', r.status_code == 200, f'{len(r.json())} companies')
if r.ok and r.json():
    ok('image_url in GET /companies response', 'image_url' in r.json()[0], list(r.json()[0].keys()))

# 3. GET /admin/companies
r = requests.get(f'{API}/admin/companies')
ok('GET /admin/companies', r.status_code == 200, f'{len(r.json())} companies')
if r.ok and r.json():
    ok('image_url in GET /admin/companies response', 'image_url' in r.json()[0])

# 4. POST /upload (1x1 PNG)
png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')
r = requests.post(f'{API}/upload', files={'file': ('test.png', png, 'image/png')})
ok('POST /upload', r.status_code == 200, r.json())
img_url = r.json().get('url', '') if r.ok else ''
ok('ImageKit CDN URL returned', img_url.startswith('http'), img_url)

# 5. POST /companies with image_url
payload = {
    'name': 'Test Co Phase4',
    'city': 'Baghdad',
    'phone': '07700000001',
    'spec': 'عامة',
    'desc': 'اختبار المرحلة 4',
    'image_url': img_url
}
r = requests.post(f'{API}/companies', json=payload)
ok('POST /companies (with image_url)', r.status_code == 200, r.json().get('id'))
new_id = r.json().get('id') if r.ok else None
ok('image_url persisted in DB', r.ok and r.json().get('image_url') == img_url)

# 6. Approve
if new_id and token:
    r = requests.put(f'{API}/companies/{new_id}/status',
                     json={'status': 'approved'},
                     headers={'Authorization': token})
    ok('Approve company', r.status_code == 200, r.json())

# 7. Reject
if new_id and token:
    r = requests.put(f'{API}/companies/{new_id}/status',
                     json={'status': 'rejected'},
                     headers={'Authorization': token})
    ok('Reject company', r.status_code == 200, r.json())

# 8. Invalid token → 401
r = requests.put(f'{API}/companies/1/status',
                 json={'status': 'approved'},
                 headers={'Authorization': 'bad_token_xyz'})
ok('Invalid token rejected (401)', r.status_code == 401, r.status_code)

# 9. Upload wrong content type → 400
r = requests.post(f'{API}/upload', files={'file': ('bad.txt', b'hello', 'text/plain')})
ok('Upload wrong type rejected (400)', r.status_code == 400, r.status_code)

# --- Report ---
print()
for line in results:
    print(line)
passed = sum(1 for l in results if '[PASS]' in l)
failed = sum(1 for l in results if '[FAIL]' in l)
print(f'\nTotal: {passed} passed, {failed} failed')
