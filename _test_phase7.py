"""Phase 7 — Subscriptions & Monetization comprehensive tests"""
import requests, uuid
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text
import os
import os
from dotenv import load_dotenv; load_dotenv()
ADMIN_PW = os.environ.get('ADMIN_PASSWORD', '')

API    = 'http://127.0.0.1:8000'
engine = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True)
results = []

def ok(name, passed, detail=''):
    sym = '[PASS]' if passed else '[FAIL]'
    results.append(f"{sym} {name}" + (f": {detail}" if detail else ""))

def db_exec(sql, params=None):
    with engine.begin() as c:
        return c.execute(text(sql), params or {})

def db_scalar(sql, params=None):
    with engine.connect() as c:
        return c.execute(text(sql), params or {}).scalar()

print("="*60)
print("PHASE 7 TESTS — SUBSCRIPTIONS & MONETIZATION")
print("="*60)

uid = str(uuid.uuid4())[:8]

# ── 0. Admin token ─────────────────────────────────────────────
r = requests.post(f'{API}/login', json={'username':'admin','password':ADMIN_PW})
ok('Admin login', r.status_code == 200)
ADMIN = r.json().get('token','')

# ── 1. Backward compat ────────────────────────────────────────
r = requests.get(f'{API}/companies')
ok('GET /companies still works (Phase 5)', r.status_code == 200)
r = requests.get(f'{API}/projects')
ok('GET /projects still works (Phase 6)', r.status_code == 200)

# ── 2. Plans endpoint ─────────────────────────────────────────
r = requests.get(f'{API}/subscription/plans')
ok('GET /subscription/plans (public)', r.status_code == 200)
plans = r.json()
ok('4 plans exist', len(plans) == 4)
codes = [p['code'] for p in plans]
ok('starter plan exists', 'starter' in codes)
ok('active plan exists',  'active'  in codes)
ok('featured plan exists','featured' in codes)
ok('partner plan exists', 'partner' in codes)

starter  = next(p for p in plans if p['code']=='starter')
active   = next(p for p in plans if p['code']=='active')
featured = next(p for p in plans if p['code']=='featured')
partner  = next(p for p in plans if p['code']=='partner')

ok('starter price = 0',      starter['monthly_price']  == 0)
ok('active price = 10',      active['monthly_price']   == 10)
ok('featured price = 20',    featured['monthly_price'] == 20)
ok('partner price = 40',     partner['monthly_price']  == 40)
ok('starter max_images = 3', starter['max_images']     == 3)
ok('active max_images = 15', active['max_images']      == 15)
ok('partner unlimited images', partner['max_images']   == -1)
ok('starter max_leads = 1',  starter['max_project_leads'] == 1)
ok('partner unlimited leads', partner['max_project_leads'] == -1)
ok('featured is_verified',   featured['is_verified']   == True)
ok('featured is_featured',   featured['is_featured']   == True)

# ── 3. Create test company (STARTER by default) ───────────────
EMAIL = f'sub7_{uid}@bunyan.test'
PASS  = 'SecurePass7!'

r = requests.post(f'{API}/auth/register',
    json={'email': EMAIL, 'password': PASS, 'display_name': f'شركة 7 {uid}'})
ok('Register user', r.status_code == 200)
USER_TOKEN = r.json().get('token','')
USER_ID    = r.json().get('user_id')

r = requests.post(f'{API}/company/create', json={
    'name': f'شركة Phase 7 {uid}', 'city': 'بغداد',
    'phone': '07700007007', 'spec': 'مقاولات عامة',
}, headers={'Authorization': USER_TOKEN})
ok('Create company', r.status_code == 200)
COMPANY_ID = r.json().get('company_id')

r = requests.put(f'{API}/companies/{COMPANY_ID}/status',
    json={'status':'approved'}, headers={'Authorization': ADMIN})
ok('Admin approves company', r.status_code == 200)

# ── 4. Default subscription = STARTER ─────────────────────────
r = requests.get(f'{API}/company/subscription', headers={'Authorization': USER_TOKEN})
ok('GET /company/subscription', r.status_code == 200)
sub = r.json()
ok('Default plan is starter', sub.get('plan_code') == 'starter')
ok('Default price is 0',      sub.get('monthly_price') == 0)
ok('Not founder by default',  sub.get('is_founder') == False)
ok('expires_at is None',      sub.get('expires_at') is None)
ok('founder_slots in response', 'founder_slots_remaining' in sub)

# ── 5. Usage endpoint ─────────────────────────────────────────
r = requests.get(f'{API}/company/subscription/usage', headers={'Authorization': USER_TOKEN})
ok('GET /company/subscription/usage', r.status_code == 200)
usage = r.json()
ok('images_used field',        'images_used' in usage)
ok('leads_used_this_month',    'leads_used_this_month' in usage)
ok('images_max = 3 (starter)', usage.get('images_max') == 3)
ok('leads_max = 1 (starter)',  usage.get('leads_max') == 1)

# ── 6. POST /subscription/request ────────────────────────────
r = requests.post(f'{API}/subscription/request',
    json={'plan_code': 'active', 'notes': 'دفع نقدي'},
    headers={'Authorization': USER_TOKEN})
ok('POST /subscription/request', r.status_code == 200)
ok('Request status=pending', r.json().get('status') == 'pending')
ok('Request has request_id', bool(r.json().get('request_id')))
REQ_ID = r.json().get('request_id')

# Duplicate pending request rejected
r2 = requests.post(f'{API}/subscription/request',
    json={'plan_code': 'featured'},
    headers={'Authorization': USER_TOKEN})
ok('Duplicate pending → 409', r2.status_code == 409)

# Invalid plan code
r3 = requests.post(f'{API}/subscription/request',
    json={'plan_code': 'gold_ultra'},
    headers={'Authorization': USER_TOKEN})
ok('Invalid plan code → 400', r3.status_code == 400)

# Unauthenticated
r4 = requests.post(f'{API}/subscription/request', json={'plan_code': 'active'})
ok('No auth → 401', r4.status_code == 401)

# ── 7. GET /subscription/request ─────────────────────────────
r = requests.get(f'{API}/subscription/request', headers={'Authorization': USER_TOKEN})
ok('GET /subscription/request', r.status_code == 200)
ok('Returns pending request', r.json().get('status') == 'pending')
ok('plan_code correct', r.json().get('plan_code') == 'active')

# ── 8. ADMIN: GET /admin/subscription-requests ────────────────
r = requests.get(f'{API}/admin/subscription-requests', headers={'Authorization': ADMIN})
ok('GET /admin/subscription-requests', r.status_code == 200)
ok('Contains our request', any(x['id']==REQ_ID for x in r.json()))
ok('Has company_name field', 'company_name' in r.json()[0])

# Filter by status
r = requests.get(f'{API}/admin/subscription-requests?status=pending',
    headers={'Authorization': ADMIN})
ok('Filter by status=pending', r.status_code == 200 and len(r.json()) >= 1)

# Non-admin cannot access
r = requests.get(f'{API}/admin/subscription-requests',
    headers={'Authorization': USER_TOKEN})
ok('Non-admin → 401/403', r.status_code in (401, 403))

# ── 9. ADMIN: APPROVE ─────────────────────────────────────────
r = requests.put(f'{API}/admin/subscription-requests/{REQ_ID}/approve',
    json={'months': 2}, headers={'Authorization': ADMIN})
ok('PUT /approve', r.status_code == 200)
ok('Response has plan=active', r.json().get('plan') == 'active')
ok('Response has expires_at',  bool(r.json().get('expires_at')))
ok('Response has months=2',    r.json().get('months') == 2)
IS_FOUNDER = r.json().get('is_founder', False)
ok('is_founder is bool', isinstance(IS_FOUNDER, bool))

# Approve already-approved → 400
r2 = requests.put(f'{API}/admin/subscription-requests/{REQ_ID}/approve',
    json={}, headers={'Authorization': ADMIN})
ok('Re-approve → 400', r2.status_code == 400)

# ── 10. Verify subscription is active after approval ──────────
r = requests.get(f'{API}/company/subscription', headers={'Authorization': USER_TOKEN})
ok('Plan is now active', r.json().get('plan_code') == 'active')
ok('expires_at is set',  r.json().get('expires_at') is not None)
ok('monthly_price = 10', r.json().get('monthly_price') == 10.0)

r = requests.get(f'{API}/company/subscription/usage', headers={'Authorization': USER_TOKEN})
ok('images_max = 15 after upgrade', r.json().get('images_max') == 15)
ok('leads_max = 5 after upgrade',   r.json().get('leads_max') == 5)

# ── 11. Founder Pricing ───────────────────────────────────────
# Create a second paid company and check founder tracking
EMAIL2 = f'founder7_{uid}@bunyan.test'
r = requests.post(f'{API}/auth/register',
    json={'email': EMAIL2, 'password': PASS})
T2 = r.json().get('token','')
r = requests.post(f'{API}/company/create', json={
    'name': f'Founder Co {uid}', 'city': 'البصرة',
    'phone': '07700007008', 'spec': 'أخرى',
}, headers={'Authorization': T2})
C2 = r.json().get('company_id')
requests.put(f'{API}/companies/{C2}/status',
    json={'status':'approved'}, headers={'Authorization': ADMIN})

r = requests.post(f'{API}/subscription/request',
    json={'plan_code': 'featured'}, headers={'Authorization': T2})
REQ2_ID = r.json().get('request_id')
r = requests.put(f'{API}/admin/subscription-requests/{REQ2_ID}/approve',
    json={'months': 1}, headers={'Authorization': ADMIN})
ok('Second company approved', r.status_code == 200)
ok('Second company is founder (< 50)', r.json().get('is_founder') == True)

# Check founder count from subscription endpoint
r = requests.get(f'{API}/company/subscription', headers={'Authorization': T2})
ok('company/subscription has is_founder', 'is_founder' in r.json())
founders_remaining = r.json().get('founder_slots_remaining', 0)
ok('Founder slots remaining < 50', founders_remaining < 50)

# ── 12. ADMIN: REJECT ─────────────────────────────────────────
EMAIL3 = f'reject7_{uid}@bunyan.test'
r = requests.post(f'{API}/auth/register', json={'email': EMAIL3, 'password': PASS})
T3 = r.json().get('token','')
r = requests.post(f'{API}/company/create', json={
    'name': f'Reject Co {uid}', 'city': 'أربيل',
    'phone': '07700007009', 'spec': 'أخرى',
}, headers={'Authorization': T3})
C3 = r.json().get('company_id')
requests.put(f'{API}/companies/{C3}/status',
    json={'status':'approved'}, headers={'Authorization': ADMIN})
r = requests.post(f'{API}/subscription/request',
    json={'plan_code': 'partner'}, headers={'Authorization': T3})
REQ3_ID = r.json().get('request_id')

r = requests.put(f'{API}/admin/subscription-requests/{REQ3_ID}/reject',
    json={'notes': 'الدفع لم يتأكد'}, headers={'Authorization': ADMIN})
ok('PUT /reject', r.status_code == 200)
ok('Status = rejected', r.json().get('status') == 'rejected')
ok('Notes returned', 'الدفع' in r.json().get('notes',''))

# Company sees rejected status
r = requests.get(f'{API}/subscription/request', headers={'Authorization': T3})
ok('Company sees rejected status', r.json().get('status') == 'rejected')

# Company can now submit new request after rejection
r = requests.post(f'{API}/subscription/request',
    json={'plan_code': 'active'}, headers={'Authorization': T3})
ok('New request after rejection', r.status_code == 200)

# ── 13. Admin direct subscription set ────────────────────────
r = requests.put(f'{API}/admin/company/{COMPANY_ID}/subscription',
    json={'plan_code': 'partner', 'months': 3, 'is_founder': True},
    headers={'Authorization': ADMIN})
ok('PUT /admin/company/{id}/subscription', r.status_code == 200)
ok('Plan set to partner', r.json().get('plan') == 'partner')
ok('is_founder forced True', r.json().get('is_founder') == True)

# Verify
r = requests.get(f'{API}/company/subscription', headers={'Authorization': USER_TOKEN})
ok('Plan is now partner', r.json().get('plan_code') == 'partner')
ok('is_founder = True',   r.json().get('is_founder') == True)

# Invalid plan
r = requests.put(f'{API}/admin/company/{COMPANY_ID}/subscription',
    json={'plan_code': 'diamond'}, headers={'Authorization': ADMIN})
ok('Invalid plan → 400', r.status_code == 400)

# Non-existent company
r = requests.put(f'{API}/admin/company/9999999/subscription',
    json={'plan_code': 'active'}, headers={'Authorization': ADMIN})
ok('Nonexistent company → 404', r.status_code == 404)

# ── 14. GALLERY LIMIT ENFORCEMENT ────────────────────────────
# Create a STARTER company (no subscription) and test image limit
EMAIL4 = f'limit7_{uid}@bunyan.test'
r = requests.post(f'{API}/auth/register', json={'email': EMAIL4, 'password': PASS})
T4 = r.json().get('token','')
r = requests.post(f'{API}/company/create', json={
    'name': f'Limit Co {uid}', 'city': 'كربلاء',
    'phone': '07700007010', 'spec': 'تشطيبات داخلية',
}, headers={'Authorization': T4})
C4 = r.json().get('company_id')
requests.put(f'{API}/companies/{C4}/status',
    json={'status':'approved'}, headers={'Authorization': ADMIN})

# Add 3 gallery images (STARTER limit)
for i in range(3):
    r = requests.post(f'{API}/company/gallery',
        json={'image_url': f'https://fake.cdn/{uid}/img{i}.jpg', 'title': f'Test {i}'},
        headers={'Authorization': T4})
    ok(f'Gallery upload {i+1}/3 succeeds', r.status_code == 200)

# 4th upload should fail
r = requests.post(f'{API}/company/gallery',
    json={'image_url': f'https://fake.cdn/{uid}/img4.jpg', 'title': 'Overflow'},
    headers={'Authorization': T4})
ok('Gallery limit enforced → 403', r.status_code == 403)
ok('Error mentions image limit', 'صورة' in r.json().get('detail','') or 'limit' in r.json().get('detail','').lower())

# Verify usage reports correctly
r = requests.get(f'{API}/company/subscription/usage', headers={'Authorization': T4})
ok('Usage shows 3/3 images',    r.json().get('images_used') == 3)
ok('images_max = 3 (starter)',  r.json().get('images_max')  == 3)

# ── 15. PROJECT LEADS LIMIT ENFORCEMENT ──────────────────────
# STARTER allows 1 lead/month — create owner + 2 projects, bid twice
EMAIL5 = f'leads7_{uid}@bunyan.test'
r = requests.post(f'{API}/auth/register', json={'email': EMAIL5, 'password': PASS})
T5 = r.json().get('token','')

# Create 2 projects as owner
for i in range(2):
    requests.post(f'{API}/projects', json={
        'title': f'مشروع {i} leads {uid}', 'category': 'أخرى',
        'city': 'النجف', 'contact_name': 'تجربة', 'contact_phone': '0770',
    }, headers={'Authorization': T5})

# Get project IDs
r = requests.get(f'{API}/projects')
test_projects = [p for p in r.json() if uid in p.get('title','')]
ok('Test projects created', len(test_projects) >= 2)

P_IDS = [p['id'] for p in test_projects[:2]]

# T4 company bids on project 1 (STARTER: 1/month)
r = requests.post(f'{API}/projects/{P_IDS[0]}/bid',
    json={'price': 5000000, 'message': 'أول عرض'},
    headers={'Authorization': T4})
ok('First bid succeeds (1/1 STARTER)',  r.status_code == 200)

# Second bid in same month should fail
r = requests.post(f'{API}/projects/{P_IDS[1]}/bid',
    json={'price': 4000000, 'message': 'ثاني عرض'},
    headers={'Authorization': T4})
ok('Second bid blocked → 403 (lead limit)', r.status_code == 403)
ok('Error mentions lead limit', 'فرص' in r.json().get('detail','') or 'limit' in r.json().get('detail','').lower())

# Check usage
r = requests.get(f'{API}/company/subscription/usage', headers={'Authorization': T4})
ok('leads_used_this_month = 1', r.json().get('leads_used_this_month') == 1)

# Partner (unlimited) has no lead limit
r = requests.get(f'{API}/company/subscription/usage', headers={'Authorization': USER_TOKEN})
ok('Partner leads_unlimited = True', r.json().get('leads_unlimited') == True)

# ── 16. Auth guards ───────────────────────────────────────────
r = requests.get(f'{API}/company/subscription')
ok('No auth → 401 (subscription)', r.status_code == 401)
r = requests.get(f'{API}/company/subscription/usage')
ok('No auth → 401 (usage)', r.status_code == 401)
r = requests.get(f'{API}/subscription/request')
ok('No auth → 401 (request)', r.status_code == 401)

# ── 17. Static pages ─────────────────────────────────────────
for page in ['company_dashboard.html','projects.html','project_details.html','index.html']:
    r = requests.get(f'{API}/{page}')
    ok(f'Static {page}', r.status_code == 200)

# ── 18. Phase 5 + 6 compat ───────────────────────────────────
r = requests.get(f'{API}/company/me', headers={'Authorization': USER_TOKEN})
ok('GET /company/me still works', r.status_code == 200)
r = requests.post(f'{API}/auth/login', json={'email': EMAIL, 'password': PASS})
ok('POST /auth/login still works', r.status_code == 200)
r = requests.get(f'{API}/admin/companies', headers={'Authorization': ADMIN})
ok('GET /admin/companies still works', r.status_code == 200)
r = requests.get(f'{API}/admin/projects', headers={'Authorization': ADMIN})
ok('GET /admin/projects still works', r.status_code == 200)

# ── Report ────────────────────────────────────────────────────
print()
for t in results:
    print(t)
passed = sum(1 for t in results if '[PASS]' in t)
failed = sum(1 for t in results if '[FAIL]' in t)
print(f'\nTotal: {passed} passed, {failed} failed')
if failed:
    raise SystemExit(1)
