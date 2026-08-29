"""Test: GET /companies returns companies sorted by subscription priority."""
import requests, uuid
import os
from dotenv import load_dotenv; load_dotenv()
ADMIN_PW = os.environ.get('ADMIN_PASSWORD', '')

API = 'http://127.0.0.1:8000'
results = []

def ok(name, passed, detail=''):
    sym = '[PASS]' if passed else '[FAIL]'
    results.append(f"{sym} {name}" + (f": {detail}" if detail else ""))

print("="*60)
print("SEARCH PRIORITY ENFORCEMENT TEST")
print("="*60)

uid  = str(uuid.uuid4())[:8]
PASS = 'SecurePass7!'

r = requests.post(f'{API}/login', json={'username':'admin','password':ADMIN_PW})
ADMIN = r.json().get('token','')
ok('Admin login', r.status_code == 200)

created = {}  # plan_code → company_id

for plan in ['starter', 'active', 'featured', 'partner']:
    email = f'pri_{plan}_{uid}@test.com'
    r = requests.post(f'{API}/auth/register',
        json={'email': email, 'password': PASS, 'display_name': f'Priority {plan}'})
    tok = r.json().get('token','')
    r = requests.post(f'{API}/company/create', json={
        'name': f'PRI_{plan.upper()}_{uid}', 'city': 'بغداد',
        'phone': '07700000001', 'spec': 'مقاولات عامة',
    }, headers={'Authorization': tok})
    cid = r.json().get('company_id')
    ok(f'Create {plan} company', bool(cid))
    created[plan] = {'cid': cid, 'tok': tok}
    requests.put(f'{API}/companies/{cid}/status',
        json={'status':'approved'}, headers={'Authorization': ADMIN})

# Assign paid plans to active/featured/partner via admin direct set
for plan in ['active', 'featured', 'partner']:
    cid = created[plan]['cid']
    r = requests.put(f'{API}/admin/company/{cid}/subscription',
        json={'plan_code': plan, 'months': 1},
        headers={'Authorization': ADMIN})
    ok(f'Set {plan} plan', r.status_code == 200 and r.json().get('plan') == plan)

# starter stays on default (no subscription)

# Fetch sorted list
r = requests.get(f'{API}/companies')
ok('GET /companies OK', r.status_code == 200)
companies = r.json()

# Filter only our test companies
test_names = {v['cid']: k for k, v in created.items()}
our = [c for c in companies if c['id'] in test_names]
ok('All 4 test companies visible', len(our) >= 4)

# Extract order of our companies
order = [test_names[c['id']] for c in our if c['id'] in test_names]
print(f"\n  Actual order of test companies: {order}")

# Partner must come before Featured
partner_idx  = next((i for i,n in enumerate(order) if n=='partner'),  999)
featured_idx = next((i for i,n in enumerate(order) if n=='featured'), 999)
active_idx   = next((i for i,n in enumerate(order) if n=='active'),   999)
starter_idx  = next((i for i,n in enumerate(order) if n=='starter'),  999)

ok('Partner before Featured',  partner_idx  < featured_idx)
ok('Featured before Active',   featured_idx < active_idx)
ok('Active before Starter',    active_idx   < starter_idx)

# Verify subscription_plan field in API response
partner_co = next((c for c in companies if c['id']==created['partner']['cid']), None)
active_co  = next((c for c in companies if c['id']==created['active']['cid']), None)
ok('Partner company has subscription_plan=partner',
   partner_co and partner_co.get('subscription_plan') == 'partner')
ok('Active company has subscription_plan=active',
   active_co and active_co.get('subscription_plan') == 'active')

# Verify backward compat — same fields as before
if companies:
    c = companies[0]
    for field in ['id','name','city','phone','spec','status','image_url','verified']:
        ok(f'Field {field} still present', field in c)

print()
for t in results:
    print(t)
passed = sum(1 for t in results if '[PASS]' in t)
failed = sum(1 for t in results if '[FAIL]' in t)
print(f'\nTotal: {passed} passed, {failed} failed')
if failed:
    raise SystemExit(1)
