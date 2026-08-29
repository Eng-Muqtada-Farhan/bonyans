"""Phase 5 comprehensive tests — Steps 2,4,5,6,7,8,9"""
import requests
import base64

API = 'http://127.0.0.1:8000'
results = []

def ok(name, passed, detail=''):
    sym = '[PASS]' if passed else '[FAIL]'
    results.append(f"{sym} {name}" + (f": {detail}" if detail else ""))

# ── Get an approved company to claim ─────────────────────────────────────────
r = requests.get(f'{API}/admin/companies')
companies = r.json()
approved = [c for c in companies if c['status'] == 'approved']
ok('GET /admin/companies — has approved companies', len(approved) > 0, f'{len(approved)} approved')

if not approved:
    print("No approved companies — some tests will be skipped")
    for t in results: print(t)
    raise SystemExit(1)

target_id = approved[0]['id']
TEST_EMAIL = f'test_claim_{target_id}@bunyan.test'
TEST_PASS  = 'SecurePass123!'

# ── Admin still works ─────────────────────────────────────────────────────────
r = requests.post(f'{API}/login', json={'username': 'admin', 'password': '26'})
ok('POST /login (admin)', r.status_code == 200)
admin_token = r.json().get('token', '')

# ── STEP 4a: Cannot claim pending company ────────────────────────────────────
pending = [c for c in companies if c['status'] == 'pending']
if pending:
    r = requests.post(f'{API}/company/register', json={
        'company_id': pending[0]['id'], 'email': 'x@x.com', 'password': 'xxx'
    })
    ok('Cannot claim pending company (403)', r.status_code == 403, r.json().get('detail'))

# ── STEP 4b: Register / claim approved company ───────────────────────────────
# Clean up previous test run if any
import os; from dotenv import load_dotenv; load_dotenv()
from sqlalchemy import create_engine, text as sqlt
_engine = create_engine(os.getenv('DATABASE_URL'), pool_pre_ping=True)
with _engine.begin() as c:
    c.execute(sqlt("DELETE FROM company_users WHERE email=:e"), {'e': TEST_EMAIL})

r = requests.post(f'{API}/company/register', json={
    'company_id': target_id,
    'email':      TEST_EMAIL,
    'password':   TEST_PASS,
})
ok('POST /company/register', r.status_code == 200, r.json().get('message'))
company_token = r.json().get('token', '') if r.ok else ''
ok('Company JWT returned', bool(company_token))

# ── STEP 4c: Duplicate claim rejected ────────────────────────────────────────
r2 = requests.post(f'{API}/company/register', json={
    'company_id': target_id,
    'email':      'other@bunyan.test',
    'password':   'pass123',
})
ok('Duplicate company claim rejected (409)', r2.status_code == 409, r2.json().get('detail'))

# ── STEP 4d: Duplicate email rejected ────────────────────────────────────────
# Need a second approved company
approved2 = [c for c in approved if c['id'] != target_id]
if approved2:
    r3 = requests.post(f'{API}/company/register', json={
        'company_id': approved2[0]['id'],
        'email':      TEST_EMAIL,
        'password':   TEST_PASS,
    })
    ok('Duplicate email rejected (409)', r3.status_code == 409, r3.json().get('detail'))

# ── STEP 4e: Login ────────────────────────────────────────────────────────────
r = requests.post(f'{API}/company/login', json={'email': TEST_EMAIL, 'password': TEST_PASS})
ok('POST /company/login', r.status_code == 200)
company_token = r.json().get('token', '') if r.ok else company_token

r = requests.post(f'{API}/company/login', json={'email': TEST_EMAIL, 'password': 'wrong'})
ok('Wrong password rejected (401)', r.status_code == 401)

ch = {'Authorization': company_token}

# ── STEP 4f: GET /company/me ──────────────────────────────────────────────────
r = requests.get(f'{API}/company/me', headers=ch)
ok('GET /company/me', r.status_code == 200, r.json().get('name'))

# ── STEP 4g: PUT /company/me ──────────────────────────────────────────────────
r = requests.put(f'{API}/company/me', json={'desc': 'وصف تجريبي للمرحلة 5'}, headers=ch)
ok('PUT /company/me', r.status_code == 200, r.json().get('desc'))

# Admin token cannot access company/me
r = requests.get(f'{API}/company/me', headers={'Authorization': admin_token})
ok('Admin token rejected on /company/me (401)', r.status_code == 401)

# ── STEP 6: Projects ─────────────────────────────────────────────────────────
r = requests.post(f'{API}/company/projects', json={
    'title': 'مشروع تجريبي', 'location': 'بغداد', 'completion_date': '2025-01'
}, headers=ch)
ok('POST /company/projects', r.status_code == 200, r.json().get('id'))
proj_id = r.json().get('id') if r.ok else None

r = requests.get(f'{API}/company/projects', headers=ch)
ok('GET /company/projects', r.status_code == 200, f'{len(r.json())} projects')

if proj_id:
    r = requests.put(f'{API}/company/projects/{proj_id}',
                     json={'title': 'مشروع معدّل'}, headers=ch)
    ok('PUT /company/projects/{id}', r.status_code == 200 and r.json()['title'] == 'مشروع معدّل')

    r = requests.delete(f'{API}/company/projects/{proj_id}', headers=ch)
    ok('DELETE /company/projects/{id}', r.status_code == 200)

# ── STEP 5: Gallery ───────────────────────────────────────────────────────────
# Upload an image first
png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')
r = requests.post(f'{API}/company/upload',
                  files={'file': ('gallery.png', png, 'image/png')}, headers=ch)
ok('POST /company/upload', r.status_code == 200, r.json().get('url','')[:50])
img_url = r.json().get('url', 'https://example.com/img.png') if r.ok else 'https://example.com/img.png'

r = requests.post(f'{API}/company/gallery',
                  json={'image_url': img_url, 'title': 'صورة تجريبية'}, headers=ch)
ok('POST /company/gallery', r.status_code == 200, r.json().get('id'))
gal_id = r.json().get('id') if r.ok else None

r = requests.get(f'{API}/company/gallery', headers=ch)
ok('GET /company/gallery', r.status_code == 200, f'{len(r.json())} images')

if gal_id:
    r = requests.delete(f'{API}/company/gallery/{gal_id}', headers=ch)
    ok('DELETE /company/gallery/{id}', r.status_code == 200)

# ── STEP 7: Public company page ───────────────────────────────────────────────
r = requests.get(f'{API}/company/{target_id}')
ok('GET /company/{id} (public)', r.status_code == 200)
if r.ok:
    data = r.json()
    ok('Public page has company', 'company' in data)
    ok('Public page has projects', 'projects' in data)
    ok('Public page has gallery', 'gallery' in data)

# ── STEP 8: verification_status ───────────────────────────────────────────────
r = requests.put(
    f'{API}/admin/companies/{target_id}/verification',
    json={'verification_status': 'verified'},
    headers={'Authorization': admin_token}
)
ok('PUT /admin/companies/{id}/verification', r.status_code == 200, r.json())

r = requests.put(
    f'{API}/admin/companies/{target_id}/verification',
    json={'verification_status': 'bad_value'},
    headers={'Authorization': admin_token}
)
ok('Invalid verification_status rejected (400)', r.status_code == 400)

# ── STEP 9: Views ─────────────────────────────────────────────────────────────
r = requests.get(f'{API}/company/{target_id}/views', headers=ch)
ok('GET /company/{id}/views', r.status_code == 200, r.json().get('total_views'))

# ── Old endpoints unaffected ──────────────────────────────────────────────────
r = requests.get(f'{API}/companies')
ok('GET /companies still works', r.status_code == 200)
r = requests.get(f'{API}/admin/companies')
ok('GET /admin/companies still works', r.status_code == 200)
r = requests.put(f'{API}/companies/{target_id}/status',
                 json={'status': 'approved'}, headers={'Authorization': admin_token})
ok('Admin approve still works', r.status_code == 200)

# ── Report ────────────────────────────────────────────────────────────────────
print()
for t in results:
    print(t)
passed = sum(1 for t in results if '[PASS]' in t)
failed = sum(1 for t in results if '[FAIL]' in t)
print(f'\nTotal: {passed} passed, {failed} failed')
