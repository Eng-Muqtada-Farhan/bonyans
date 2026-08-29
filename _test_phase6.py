"""Phase 6 — Project Marketplace comprehensive tests"""
import requests, uuid

API = 'http://127.0.0.1:8000'
results = []

def ok(name, passed, detail=''):
    sym = '[PASS]' if passed else '[FAIL]'
    results.append(f"{sym} {name}" + (f": {detail}" if detail else ""))

print("="*60)
print("PHASE 6 TESTS — PROJECT MARKETPLACE")
print("="*60)

uid = str(uuid.uuid4())[:8]

# ── 0. Admin token ─────────────────────────────────────────────
r = requests.post(f'{API}/login', json={'username':'admin','password':'26'})
ok('Admin login', r.status_code == 200)
ADMIN = r.json().get('token','')

# ── 1. Phase 5 backward compat ────────────────────────────────
r = requests.get(f'{API}/companies')
ok('GET /companies still works (Phase 5)', r.status_code == 200)

r = requests.get(f'{API}/admin/companies', headers={'Authorization':ADMIN})
ok('GET /admin/companies still works', r.status_code == 200)

# ── 2. Create test user + company ─────────────────────────────
EMAIL = f'p6_{uid}@bunyan.test'
PASS  = 'SecurePass6!'

r = requests.post(f'{API}/auth/register', json={
    'email': EMAIL, 'password': PASS, 'display_name': f'مستخدم 6 {uid}'
})
ok('POST /auth/register (user)', r.status_code == 200)
USER_TOKEN = r.json().get('token','')
USER_ID    = r.json().get('user_id')

# Create company
r = requests.post(f'{API}/company/create', json={
    'name': f'شركة Phase 6 {uid}', 'city': 'بغداد',
    'phone': '07700000001', 'spec': 'مقاولات عامة',
}, headers={'Authorization': USER_TOKEN})
ok('POST /company/create', r.status_code == 200)
COMPANY_ID = r.json().get('company_id')

# Approve the company (so it can bid)
r = requests.put(f'{API}/companies/{COMPANY_ID}/status',
    json={'status':'approved'}, headers={'Authorization': ADMIN})
ok('Admin approves company', r.status_code == 200)

# ── 3. Create second user (project owner) ─────────────────────
EMAIL2 = f'owner_{uid}@bunyan.test'
r = requests.post(f'{API}/auth/register', json={
    'email': EMAIL2, 'password': PASS, 'display_name': f'صاحب مشروع {uid}'
})
ok('POST /auth/register (owner)', r.status_code == 200)
OWNER_TOKEN = r.json().get('token','')
OWNER_ID    = r.json().get('user_id')

# ── 4. GET /projects — empty initially ────────────────────────
r = requests.get(f'{API}/projects')
ok('GET /projects (public)', r.status_code == 200)
ok('GET /projects returns list', isinstance(r.json(), list))

# ── 5. POST /projects — requires auth ─────────────────────────
r = requests.post(f'{API}/projects', json={
    'title': 'مشروع اختبار 6', 'category': 'مقاولات عامة',
    'city': 'بغداد', 'contact_name': 'علي محمد', 'contact_phone': '07700000002'
})
ok('POST /projects without auth → 401', r.status_code == 401)

# Create project as owner
r = requests.post(f'{API}/projects', json={
    'title': f'مشروع Phase 6 {uid}', 'category': 'مقاولات عامة',
    'city': 'بغداد', 'country': 'IQ',
    'budget_min': 5000000, 'budget_max': 15000000,
    'description': 'مشروع بناء فيلا سكنية للاختبار',
    'contact_name': 'صاحب المشروع', 'contact_phone': '07700000002',
    'contact_email': 'owner@test.com',
}, headers={'Authorization': OWNER_TOKEN})
ok('POST /projects (authenticated)', r.status_code == 200, r.json().get('status',''))
ok('Project created as published', r.json().get('status') == 'published')
ok('Project has correct title', uid in r.json().get('title',''))
ok('Project has budget_min', r.json().get('budget_min') == 5000000.0)
ok('Project has bids_count=0', r.json().get('bids_count') == 0)
PROJECT_ID = r.json().get('id')

# ── 6. GET /projects — project appears ────────────────────────
r = requests.get(f'{API}/projects')
ok('GET /projects — new project visible', any(p['id']==PROJECT_ID for p in r.json()))

# ── 7. GET /projects filter by city ───────────────────────────
r = requests.get(f'{API}/projects?city=بغداد')
ok('GET /projects?city=بغداد', r.status_code == 200 and len(r.json()) > 0)

r = requests.get(f'{API}/projects?city=لا_توجد')
ok('GET /projects?city=nonexistent → empty', r.status_code == 200 and r.json() == [])

# ── 8. GET /projects/{id} ─────────────────────────────────────
r = requests.get(f'{API}/projects/{PROJECT_ID}')
ok('GET /projects/{id}', r.status_code == 200)
ok('Project has correct fields', r.json().get('id') == PROJECT_ID)
ok('Project has bids_count', 'bids_count' in r.json())

r2 = requests.get(f'{API}/projects/9999999')
ok('GET /projects/nonexistent → 404', r2.status_code == 404)

# ── 9. POST /projects/{id}/bid — requires company auth ────────
r = requests.post(f'{API}/projects/{PROJECT_ID}/bid',
    json={'price': 8000000, 'duration_days': 90, 'message': 'نحن متخصصون في هذا النوع'})
ok('POST bid without auth → 401/403', r.status_code in (401, 403))

# Submit bid as company
r = requests.post(f'{API}/projects/{PROJECT_ID}/bid',
    json={'price': 8000000, 'duration_days': 90, 'message': 'عرضنا الأفضل'},
    headers={'Authorization': USER_TOKEN})
ok('POST /projects/{id}/bid (company)', r.status_code == 200)
ok('Bid has price', r.json().get('price') == 8000000.0)
ok('Bid has status=submitted', r.json().get('status') == 'submitted')
ok('Bid has company_name', bool(r.json().get('company_name','')))
BID_ID = r.json().get('id')

# ── 10. Duplicate bid rejected ────────────────────────────────
r = requests.post(f'{API}/projects/{PROJECT_ID}/bid',
    json={'price': 7000000}, headers={'Authorization': USER_TOKEN})
ok('Duplicate bid → 409', r.status_code == 409)

# ── 11. bids_count updated after bid ──────────────────────────
r = requests.get(f'{API}/projects/{PROJECT_ID}')
ok('bids_count incremented to 1', r.json().get('bids_count') == 1)

# ── 12. GET /projects/{id}/bids — access control ──────────────
r = requests.get(f'{API}/projects/{PROJECT_ID}/bids')
ok('GET /bids without auth → 401', r.status_code == 401)

# Owner sees all bids
r = requests.get(f'{API}/projects/{PROJECT_ID}/bids',
    headers={'Authorization': OWNER_TOKEN})
ok('Project owner sees all bids', r.status_code == 200 and len(r.json()) == 1)
ok('Bid has company_name', bool(r.json()[0].get('company_name','')))

# Company sees own bid
r = requests.get(f'{API}/projects/{PROJECT_ID}/bids',
    headers={'Authorization': USER_TOKEN})
ok('Company sees own bid', r.status_code == 200 and len(r.json()) == 1)

# Admin sees all bids
r = requests.get(f'{API}/projects/{PROJECT_ID}/bids',
    headers={'Authorization': ADMIN})
ok('Admin sees all bids', r.status_code == 200 and len(r.json()) >= 1)

# ── 13. PUT /bids/{id} — update bid ──────────────────────────
r = requests.put(f'{API}/bids/{BID_ID}',
    json={'price': 9000000, 'message': 'تعديل العرض'},
    headers={'Authorization': USER_TOKEN})
ok('PUT /bids/{id} (update)', r.status_code == 200)
ok('Price updated', r.json().get('price') == 9000000.0)

# Cannot update another company's bid
r = requests.put(f'{API}/bids/{BID_ID}',
    json={'price': 1000}, headers={'Authorization': OWNER_TOKEN})
ok('Cannot update others bid → 401/403/404', r.status_code in (401, 403, 404))

# ── 14. Company permissions check ─────────────────────────────
r = requests.post(f'{API}/auth/register', json={
    'email': f'unapp_{uid}@test.com', 'password': PASS
})
UNAPP_TOKEN = r.json().get('token','')
r = requests.post(f'{API}/company/create', json={
    'name': f'غير معتمدة {uid}', 'city': 'البصرة',
    'phone': '07700000003', 'spec': 'أخرى',
}, headers={'Authorization': UNAPP_TOKEN})
r2 = requests.post(f'{API}/projects/{PROJECT_ID}/bid',
    json={'price': 1000000}, headers={'Authorization': UNAPP_TOKEN})
ok('Unapproved company cannot bid → 403', r2.status_code == 403)

# ── 15. POST /projects/{id}/select-company ────────────────────
# Owner selects the bid
r = requests.post(f'{API}/projects/{PROJECT_ID}/select-company',
    json={'bid_id': BID_ID}, headers={'Authorization': OWNER_TOKEN})
ok('POST /select-company (owner)', r.status_code == 200)
ok('Project status = contracted', r.json().get('status') == 'contracted')
ok('accepted_bid_id matches', r.json().get('accepted_bid_id') == BID_ID)

# Verify project is now contracted
r = requests.get(f'{API}/projects/{PROJECT_ID}')
ok('Project status contracted after selection', r.json().get('status') == 'contracted')

# Verify bid is accepted
r = requests.get(f'{API}/projects/{PROJECT_ID}/bids',
    headers={'Authorization': OWNER_TOKEN})
bid = next((b for b in r.json() if b['id']==BID_ID), None)
ok('Winning bid status = accepted', bid and bid.get('status') == 'accepted')

# Cannot select again (already contracted)
r = requests.post(f'{API}/projects/{PROJECT_ID}/select-company',
    json={'bid_id': BID_ID}, headers={'Authorization': OWNER_TOKEN})
ok('Cannot select again → 400', r.status_code == 400)

# Non-owner cannot select
r2 = requests.post(f'{API}/projects/{PROJECT_ID}/select-company',
    json={'bid_id': BID_ID}, headers={'Authorization': USER_TOKEN})
ok('Non-owner cannot select → 403', r2.status_code == 403)

# ── 16. DELETE /bids/{id} ─────────────────────────────────────
# Create another project for delete test
r = requests.post(f'{API}/projects', json={
    'title': f'مشروع حذف {uid}', 'category': 'أخرى',
    'city': 'أربيل', 'contact_name': 'اختبار', 'contact_phone': '0770'
}, headers={'Authorization': OWNER_TOKEN})
P2_ID = r.json().get('id')

r = requests.post(f'{API}/projects/{P2_ID}/bid',
    json={'price': 3000000}, headers={'Authorization': USER_TOKEN})
BID2_ID = r.json().get('id')
ok('Bid on second project created', bool(BID2_ID))

r = requests.delete(f'{API}/bids/{BID2_ID}', headers={'Authorization': USER_TOKEN})
ok('DELETE /bids/{id} (withdraw)', r.status_code == 200)
ok('deleted key returned', r.json().get('deleted') == BID2_ID)

# Verify bid gone
r = requests.get(f'{API}/projects/{P2_ID}/bids',
    headers={'Authorization': OWNER_TOKEN})
ok('Bid removed after delete', r.json() == [])

# ── 17. GET /my/projects ──────────────────────────────────────
r = requests.get(f'{API}/my/projects', headers={'Authorization': OWNER_TOKEN})
ok('GET /my/projects', r.status_code == 200)
ok('My projects list contains created projects',
   any(p['id'] == PROJECT_ID for p in r.json()))

r2 = requests.get(f'{API}/my/projects')
ok('GET /my/projects without auth → 401', r2.status_code == 401)

# ── 18. GET /company/bids ─────────────────────────────────────
r = requests.get(f'{API}/company/bids', headers={'Authorization': USER_TOKEN})
ok('GET /company/bids', r.status_code == 200)
ok('Company bids has project_title', bool(r.json()) and 'project_title' in r.json()[0])
ok('Company bids has project_status', 'project_status' in r.json()[0])

# ── 19. ADMIN endpoints ───────────────────────────────────────
r = requests.get(f'{API}/admin/projects', headers={'Authorization': ADMIN})
ok('GET /admin/projects', r.status_code == 200 and isinstance(r.json(), list))
ok('admin/projects has our project', any(p['id']==PROJECT_ID for p in r.json()))

r = requests.get(f'{API}/admin/bids', headers={'Authorization': ADMIN})
ok('GET /admin/bids', r.status_code == 200 and isinstance(r.json(), list))
ok('admin/bids has project_title', bool(r.json()) and 'project_title' in r.json()[0])

r = requests.put(f'{API}/admin/projects/{P2_ID}/status',
    json={'status': 'closed'}, headers={'Authorization': ADMIN})
ok('PUT /admin/projects/{id}/status', r.status_code == 200)
ok('Status changed to closed', r.json().get('status') == 'closed')

# Closed project not in public list
r = requests.get(f'{API}/projects')
ok('Closed project not in public list',
   not any(p['id']==P2_ID for p in r.json()))

# Invalid status rejected
r = requests.put(f'{API}/admin/projects/{P2_ID}/status',
    json={'status': 'invalid_status'}, headers={'Authorization': ADMIN})
ok('Invalid status → 400', r.status_code == 400)

# Non-admin cannot access admin endpoints
r = requests.get(f'{API}/admin/projects', headers={'Authorization': USER_TOKEN})
ok('Non-admin cannot access /admin/projects → 401/403', r.status_code in (401,403))

# ── 20. Static pages still work ───────────────────────────────
for page in ['index.html','admin.html','company_dashboard.html','company_profile.html','projects.html','project_details.html']:
    r = requests.get(f'{API}/{page}')
    ok(f'Static {page}', r.status_code == 200)

# ── 21. Phase 5 endpoints still work ────────────────────────────
r = requests.get(f'{API}/company/me', headers={'Authorization': USER_TOKEN})
ok('GET /company/me still works (Phase 5)', r.status_code == 200)

r = requests.get(f'{API}/company/projects', headers={'Authorization': USER_TOKEN})
ok('GET /company/projects still works', r.status_code == 200)

r = requests.post(f'{API}/auth/login', json={'email': EMAIL, 'password': PASS})
ok('POST /auth/login still works', r.status_code == 200)

# ── Report ─────────────────────────────────────────────────────
print()
for t in results:
    print(t)
passed = sum(1 for t in results if '[PASS]' in t)
failed = sum(1 for t in results if '[FAIL]' in t)
print(f'\nTotal: {passed} passed, {failed} failed')
if failed:
    raise SystemExit(1)
