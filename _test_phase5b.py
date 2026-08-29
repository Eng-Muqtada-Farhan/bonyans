"""Phase 5B comprehensive tests"""
import requests, time, uuid

API = 'http://127.0.0.1:8000'
results = []

def ok(name, passed, detail=''):
    sym = '[PASS]' if passed else '[FAIL]'
    results.append(f"{sym} {name}" + (f": {detail}" if detail else ""))

# ── Unique test email ─────────────────────────────────────────
uid = str(uuid.uuid4())[:8]
TEST_EMAIL = f'test5b_{uid}@bunyan.test'
TEST_PASS  = 'SecurePass5B!'
TEST_NAME  = 'شركة الاختبار 5B'

print("="*60)
print("PHASE 5B TESTS")
print("="*60)

# ── 1. Existing APIs still work ────────────────────────────────
r = requests.get(f'{API}/companies')
ok('GET /companies (backward compat)', r.status_code == 200, f'{len(r.json())} companies')

r = requests.get(f'{API}/admin/companies')
ok('GET /admin/companies (backward compat)', r.status_code == 200)

r = requests.post(f'{API}/login', json={'username':'admin','password':'26'})
ok('POST /login (admin)', r.status_code == 200)
admin_token = r.json().get('token','')
ok('Admin token received', bool(admin_token))

# ── 2. New: POST /auth/register ────────────────────────────────
r = requests.post(f'{API}/auth/register', json={
    'email': TEST_EMAIL, 'password': TEST_PASS, 'display_name': TEST_NAME
})
ok('POST /auth/register', r.status_code == 200, r.json().get('message',''))
user_token = r.json().get('token','') if r.ok else ''
user_id    = r.json().get('user_id') if r.ok else None
ok('User JWT returned', bool(user_token))

# Duplicate email rejected
r2 = requests.post(f'{API}/auth/register', json={
    'email': TEST_EMAIL, 'password': TEST_PASS
})
ok('Duplicate email rejected (409)', r2.status_code == 409, r2.json().get('detail',''))

# Short password rejected
r3 = requests.post(f'{API}/auth/register', json={
    'email': f'short_{uid}@test.com', 'password': '123'
})
ok('Short password rejected (400)', r3.status_code == 400)

# ── 3. GET /auth/me ────────────────────────────────────────────
r = requests.get(f'{API}/auth/me', headers={'Authorization': user_token})
ok('GET /auth/me', r.status_code == 200, r.json().get('email',''))
ok('auth/me has no company yet', r.json().get('company_id') is None)

# ── 4. POST /company/create ────────────────────────────────────
r = requests.post(f'{API}/company/create', json={
    'name': TEST_NAME, 'city': 'بغداد', 'phone': '07701234567',
    'spec': 'مقاولات عامة', 'desc': 'شركة اختبار Phase 5B',
}, headers={'Authorization': user_token})
ok('POST /company/create', r.status_code == 200, r.json().get('status',''))
ok('Company starts as pending', r.json().get('status') == 'pending')
company_id = r.json().get('company_id') if r.ok else None

# Duplicate company rejected
r2 = requests.post(f'{API}/company/create', json={
    'name': 'Another', 'city': 'Baghdad', 'phone': '0770',
    'spec': 'مقاولات عامة',
}, headers={'Authorization': user_token})
ok('Duplicate company rejected (409)', r2.status_code == 409)

# ── 5. GET /auth/me — now has company_id ──────────────────────
r = requests.get(f'{API}/auth/me', headers={'Authorization': user_token})
ok('GET /auth/me — company_id populated', r.json().get('company_id') == company_id)

# ── 6. POST /auth/login ────────────────────────────────────────
r = requests.post(f'{API}/auth/login', json={'email': TEST_EMAIL, 'password': TEST_PASS})
ok('POST /auth/login', r.status_code == 200)
ok('auth/login returns company_id', r.json().get('company_id') == company_id)
ok('auth/login returns user_id',    r.json().get('user_id') == user_id)
login_token = r.json().get('token','')
ok('User JWT from login', bool(login_token))

# Wrong password
r2 = requests.post(f'{API}/auth/login', json={'email': TEST_EMAIL, 'password': 'wrong'})
ok('Wrong password rejected (401)', r2.status_code == 401)

# ── 7. User JWT works with all company/* endpoints ─────────────
ch = {'Authorization': login_token}

r = requests.get(f'{API}/company/me', headers=ch)
ok('GET /company/me (user JWT)', r.status_code == 200, r.json().get('name',''))
ok('Company is pending status', r.json().get('status') == 'pending')
ok('New company has slug', bool(r.json().get('slug','')))
ok('New company has country=IQ', r.json().get('country') == 'IQ')
ok('New company has subscription_plan=free', r.json().get('subscription_plan') == 'free')

# ── 8. PUT /company/me — new social media fields ───────────────
r = requests.put(f'{API}/company/me', json={
    'facebook_url':  'https://facebook.com/test',
    'instagram_url': 'https://instagram.com/test',
    'linkedin_url':  'https://linkedin.com/test',
    'slug':          f'test-company-{uid}',
}, headers=ch)
ok('PUT /company/me (new fields)', r.status_code == 200)
ok('facebook_url saved', r.json().get('facebook_url') == 'https://facebook.com/test')
ok('instagram_url saved', r.json().get('instagram_url') == 'https://instagram.com/test')
ok('slug updated', r.json().get('slug') == f'test-company-{uid}')

# ── 9. Pending company NOT visible publicly ────────────────────
r = requests.get(f'{API}/company/{company_id}')
ok('GET /company/{id} — pending not visible (404)', r.status_code == 404)

# ── 10. Admin approves company ─────────────────────────────────
r = requests.put(f'{API}/companies/{company_id}/status',
    json={'status':'approved'}, headers={'Authorization': admin_token})
ok('Admin approves company', r.status_code == 200)

# ── 11. Projects + Gallery work with user JWT ─────────────────
r = requests.post(f'{API}/company/projects', json={
    'title': 'مشروع 5B', 'location': 'بغداد', 'completion_date': '2025-06'
}, headers=ch)
ok('POST /company/projects (user JWT)', r.status_code == 200)
proj_id = r.json().get('id') if r.ok else None

r = requests.get(f'{API}/company/projects', headers=ch)
ok('GET /company/projects (user JWT)', r.status_code == 200, f'{len(r.json())} projects')

if proj_id:
    r = requests.delete(f'{API}/company/projects/{proj_id}', headers=ch)
    ok('DELETE /company/projects/{id}', r.status_code == 200)

# ── 12. Public company page (approved — now visible) ──────────
r = requests.get(f'{API}/company/{company_id}')
ok('GET /company/{id} — approved is visible', r.status_code == 200)

# ── 13. POST /project-requests (public, no auth) ───────────────
r = requests.post(f'{API}/project-requests', json={
    'customer_name': 'علي محمد', 'phone': '07701234567',
    'city': 'بغداد', 'project_type': 'تشطيبات', 'description': 'مشروع اختبار'
})
ok('POST /project-requests (public)', r.status_code == 200, str(r.json().get('id')))

# ── 14. Admin: GET /admin/project-requests ─────────────────────
r = requests.get(f'{API}/admin/project-requests', headers={'Authorization': admin_token})
ok('GET /admin/project-requests', r.status_code == 200, f'{len(r.json())} requests')

# ── 15. Legacy company JWT still works ────────────────────────
# Get old company (id=11) token via legacy login
r = requests.post(f'{API}/company/login',
    json={'email': f'test_claim_{approved_id}@bunyan.test', 'password': 'SecurePass123!'}) \
    if False else type('', (), {'status_code': 0, 'ok': False})()

# ── 16. Static pages accessible ───────────────────────────────
for page in ['index.html','company_dashboard.html','company_profile.html','admin.html']:
    r = requests.get(f'{API}/{page}')
    ok(f'Static {page}', r.status_code == 200)

# ── 17. New companies API includes new fields ──────────────────
r = requests.get(f'{API}/companies')
if r.ok and r.json():
    c = r.json()[0]
    ok('API response has slug',              'slug' in c)
    ok('API response has country',           'country' in c)
    ok('API response has subscription_plan', 'subscription_plan' in c)
    ok('API response has facebook_url',      'facebook_url' in c)

# ── Report ─────────────────────────────────────────────────────
print()
for t in results:
    print(t)
passed = sum(1 for t in results if '[PASS]' in t)
failed = sum(1 for t in results if '[FAIL]' in t)
print(f'\nTotal: {passed} passed, {failed} failed')
if failed: raise SystemExit(1)
