"""
Phase 8 — Communication & Reputation System Tests
Parts: A=Messaging, B=Notifications, C=Reviews, D=Activity
"""
import requests, uuid, sys
import os
from dotenv import load_dotenv; load_dotenv()
ADMIN_PW = os.environ.get('ADMIN_PASSWORD', '')

API = 'http://127.0.0.1:8000'
results = []
uid = str(uuid.uuid4())[:8]
PASS = 'SecurePass8!'


def ok(name, passed, detail=''):
    sym = '[PASS]' if passed else '[FAIL]'
    results.append(f"{sym} {name}" + (f": {detail}" if detail else ""))
    if not passed:
        print(f"  FAIL >> {name}" + (f": {detail}" if detail else ""))


def section(title):
    print(f"\n{'='*55}\n{title}\n{'='*55}")


# ─── SETUP ──────────────────────────────────────────────────
section("SETUP")

# Admin login
r = requests.post(f'{API}/login', json={'username': 'admin', 'password': ADMIN_PW})
ok('Admin login', r.status_code == 200)
ADMIN = r.json().get('token', '')

# Register user
r = requests.post(f'{API}/auth/register', json={
    'email': f'p8user_{uid}@test.com',
    'password': PASS, 'display_name': f'User {uid}'
})
ok('Register user', r.status_code == 200)
USER_TOKEN = r.json().get('token', '')
USER_ID = r.json().get('user_id')

# Register + create company
r = requests.post(f'{API}/auth/register', json={
    'email': f'p8co_{uid}@test.com',
    'password': PASS, 'display_name': f'Co Owner {uid}'
})
ok('Register company owner', r.status_code == 200)
CO_USER_TOKEN = r.json().get('token', '')

r = requests.post(f'{API}/company/create', json={
    'name': f'P8Co_{uid}', 'city': 'بغداد',
    'phone': '07700000009', 'spec': 'مقاولات'
}, headers={'Authorization': CO_USER_TOKEN})
ok('Create company', r.status_code in (200, 201))
CO_ID = r.json().get('company_id')
CO_TOKEN = CO_USER_TOKEN  # dual-JWT: same token works for company

# Approve company
r = requests.put(f'{API}/companies/{CO_ID}/status',
                 json={'status': 'approved'}, headers={'Authorization': ADMIN})
ok('Approve company', r.status_code == 200)

# Create a project (user)
r = requests.post(f'{API}/projects', json={
    'title': f'TestProject_{uid}', 'city': 'بغداد',
    'category': 'بناء', 'description': 'test project',
    'budget_min': 1000, 'budget_max': 5000,
    'contact_name': 'عميل اختبار', 'contact_phone': '07700000001'
}, headers={'Authorization': USER_TOKEN})
ok('Create project', r.status_code in (200, 201))
PROJECT_ID = r.json().get('id') or r.json().get('project_id')


# ─── PART A: MESSAGING ──────────────────────────────────────
section("PART A: MESSAGING")

# Start conversation
r = requests.post(f'{API}/conversations', json={
    'company_id': CO_ID, 'message': 'مرحباً، هل يمكنكم تنفيذ مشروعي؟'
}, headers={'Authorization': USER_TOKEN})
ok('POST /conversations', r.status_code in (200, 201), str(r.status_code))
CONV_ID = r.json().get('conversation_id')

# Start conversation again (idempotent — same conv returned)
r2 = requests.post(f'{API}/conversations', json={
    'company_id': CO_ID, 'message': 'رسالة ثانية في محادثة أولى'
}, headers={'Authorization': USER_TOKEN})
ok('POST /conversations idempotent', r2.status_code in (200, 201))
ok('Same conversation returned', r2.json().get('conversation_id') == CONV_ID,
   f"got {r2.json().get('conversation_id')}, expected {CONV_ID}")

# List conversations (user)
r = requests.get(f'{API}/conversations', headers={'Authorization': USER_TOKEN})
ok('GET /conversations (user)', r.status_code == 200)
convs = r.json()
ok('User sees their conversation', any(c['id'] == CONV_ID for c in convs))

# List conversations (company)
r = requests.get(f'{API}/conversations', headers={'Authorization': CO_TOKEN})
ok('GET /conversations (company)', r.status_code == 200)
ok('Company sees conversation', any(c['id'] == CONV_ID for c in r.json()))

# GET /conversations/{id}
r = requests.get(f'{API}/conversations/{CONV_ID}', headers={'Authorization': USER_TOKEN})
ok('GET /conversations/{id} (user)', r.status_code == 200)
ok('Conversation has company_id', r.json().get('company_id') == CO_ID)

# 403 if different user tries
r = requests.get(f'{API}/conversations/{CONV_ID}', headers={'Authorization': ADMIN})
ok('GET /conversations/{id} admin gets 401/403', r.status_code in (401, 403))

# GET messages
r = requests.get(f'{API}/conversations/{CONV_ID}/messages',
                 headers={'Authorization': USER_TOKEN})
ok('GET /conversations/{id}/messages (user)', r.status_code == 200)
msgs = r.json()
ok('Messages list not empty', len(msgs) > 0)
ok('First message from client', msgs[0]['sender_type'] == 'client')

# Company sends reply
r = requests.post(f'{API}/conversations/{CONV_ID}/messages',
                  json={'message': 'نعم يمكننا تنفيذ مشروعكم'},
                  headers={'Authorization': CO_TOKEN})
ok('Company sends message', r.status_code in (200, 201))
MSG_ID = r.json().get('message_id')

# User reads messages (marks company msg read)
r = requests.get(f'{API}/conversations/{CONV_ID}/messages',
                 headers={'Authorization': USER_TOKEN})
ok('GET messages (user) after company reply', r.status_code == 200)
all_msgs = r.json()
ok('Both messages present', len(all_msgs) >= 2)

# PUT /messages/{id}/read
r = requests.put(f'{API}/messages/{MSG_ID}/read',
                 headers={'Authorization': USER_TOKEN})
ok('PUT /messages/{id}/read', r.status_code == 200)

# 403 — wrong user can't mark read
r2 = requests.post(f'{API}/auth/register', json={
    'email': f'p8other_{uid}@test.com', 'password': PASS, 'display_name': 'Other'
})
OTHER_TOKEN = r2.json().get('token', '')
r = requests.put(f'{API}/messages/{MSG_ID}/read',
                 headers={'Authorization': OTHER_TOKEN})
ok('PUT /messages/{id}/read forbidden for other user', r.status_code in (403, 404))

# Company can't send to conversation they don't own
r2_co = requests.post(f'{API}/auth/register', json={
    'email': f'p8co2_{uid}@test.com', 'password': PASS, 'display_name': 'Co2'
})
CO2_TOKEN = r2_co.json().get('token', '')
r2_co2 = requests.post(f'{API}/company/create', json={
    'name': f'P8Co2_{uid}', 'city': 'بصرة', 'phone': '07700000010', 'spec': 'مقاولات'
}, headers={'Authorization': CO2_TOKEN})
CO2_ID = r2_co2.json().get('company_id')
requests.put(f'{API}/companies/{CO2_ID}/status',
             json={'status': 'approved'}, headers={'Authorization': ADMIN})
r = requests.post(f'{API}/conversations/{CONV_ID}/messages',
                  json={'message': 'أحاول الاختراق'},
                  headers={'Authorization': CO2_TOKEN})
ok('Wrong company cannot send message', r.status_code in (403, 401))


# ─── PART B: NOTIFICATIONS ──────────────────────────────────
section("PART B: NOTIFICATIONS")

# Company should have notifications from new messages
r = requests.get(f'{API}/notifications', headers={'Authorization': CO_TOKEN})
ok('GET /notifications (company)', r.status_code == 200)
notifs = r.json()
ok('Company has notifications', len(notifs) > 0)
NOTIF_ID = notifs[0]['id'] if notifs else None

# User should have notification (company replied)
r = requests.get(f'{API}/notifications', headers={'Authorization': USER_TOKEN})
ok('GET /notifications (user)', r.status_code == 200)
user_notifs = r.json()
ok('User has notifications', len(user_notifs) > 0)

# Unauthorized
r = requests.get(f'{API}/notifications', headers={'Authorization': 'bad'})
ok('GET /notifications 401 without auth', r.status_code == 401)

if NOTIF_ID:
    r = requests.put(f'{API}/notifications/{NOTIF_ID}/read',
                     headers={'Authorization': CO_TOKEN})
    ok('PUT /notifications/{id}/read', r.status_code == 200)

# PUT /notifications/read-all
r = requests.put(f'{API}/notifications/read-all', headers={'Authorization': CO_TOKEN})
ok('PUT /notifications/read-all', r.status_code == 200)

# After read-all, notifications should still exist but be read
r = requests.get(f'{API}/notifications', headers={'Authorization': CO_TOKEN})
ok('Notifications still exist after read-all', r.status_code == 200)
all_read = all(n['is_read'] for n in r.json())
ok('All notifications marked read', all_read)

# read-all route not confused with /{id}/read
r = requests.put(f'{API}/notifications/read-all', headers={'Authorization': USER_TOKEN})
ok('PUT /notifications/read-all user (no 422)', r.status_code == 200)


# ─── PART C: REVIEWS ────────────────────────────────────────
section("PART C: REVIEWS")

# Submit review
r = requests.post(f'{API}/reviews', json={
    'company_id': CO_ID,
    'client_name': 'عميل اختبار',
    'rating': 5,
    'comment': 'شركة ممتازة'
})
ok('POST /reviews (public, no auth)', r.status_code in (200, 201))
REVIEW_ID = r.json().get('review_id')
ok('Review in pending', r.json().get('status') == 'pending')

# With project_id (unique per project)
r = requests.post(f'{API}/reviews', json={
    'company_id': CO_ID,
    'client_name': 'عميل 2',
    'project_id': PROJECT_ID,
    'rating': 4,
    'comment': 'جيد'
})
ok('POST /reviews with project_id', r.status_code in (200, 201))
REV2_ID = r.json().get('review_id')

# Duplicate project review
r = requests.post(f'{API}/reviews', json={
    'company_id': CO_ID, 'client_name': 'عميل 3',
    'project_id': PROJECT_ID, 'rating': 3
})
ok('Duplicate project review rejected (409/500)', r.status_code in (409, 422, 500))

# Rating validation
r = requests.post(f'{API}/reviews', json={
    'company_id': CO_ID, 'client_name': 'test', 'rating': 6
})
ok('Rating > 5 rejected', r.status_code == 422)

r = requests.post(f'{API}/reviews', json={
    'company_id': CO_ID, 'client_name': 'test', 'rating': 0
})
ok('Rating < 1 rejected', r.status_code == 422)

# Pending review not visible on public endpoint
r = requests.get(f'{API}/company/{CO_ID}/reviews')
ok('GET /company/{id}/reviews (public)', r.status_code == 200)
ok('Pending review NOT in public list', not any(rv.get('id') == REVIEW_ID for rv in r.json()))

# Admin list reviews
r = requests.get(f'{API}/admin/reviews', headers={'Authorization': ADMIN})
ok('GET /admin/reviews', r.status_code == 200)
ok('Admin sees pending reviews', len(r.json()) > 0)

# Admin approve
r = requests.put(f'{API}/admin/reviews/{REVIEW_ID}/approve',
                 headers={'Authorization': ADMIN})
ok('PUT /admin/reviews/{id}/approve', r.status_code == 200)

# Now visible publicly
r = requests.get(f'{API}/company/{CO_ID}/reviews')
ok('Approved review visible publicly', any(rv.get('id') == REVIEW_ID for rv in r.json()))

# Company reply
r = requests.post(f'{API}/reviews/{REVIEW_ID}/reply',
                  json={'reply': 'شكراً جزيلاً على تقييمكم الكريم'},
                  headers={'Authorization': CO_TOKEN})
ok('POST /reviews/{id}/reply (company)', r.status_code == 200)

# Reply visible in public reviews
r = requests.get(f'{API}/company/{CO_ID}/reviews')
rev_with_reply = next((rv for rv in r.json() if rv.get('id') == REVIEW_ID), None)
ok('Reply appears in public review list',
   rev_with_reply and rev_with_reply.get('reply') is not None)

# Wrong company can't reply
r = requests.post(f'{API}/reviews/{REVIEW_ID}/reply',
                  json={'reply': 'محاولة اختراق'},
                  headers={'Authorization': CO2_TOKEN})
ok('Wrong company cannot reply', r.status_code in (403, 401))

# Admin reject
r = requests.put(f'{API}/admin/reviews/{REV2_ID}/reject',
                 headers={'Authorization': ADMIN})
ok('PUT /admin/reviews/{id}/reject', r.status_code == 200)

r = requests.get(f'{API}/company/{CO_ID}/reviews')
ok('Rejected review not visible publicly',
   not any(rv.get('id') == REV2_ID for rv in r.json()))

# Non-admin can't access admin endpoints
r = requests.get(f'{API}/admin/reviews', headers={'Authorization': USER_TOKEN})
ok('Non-admin cannot GET /admin/reviews', r.status_code in (401, 403))

r = requests.put(f'{API}/admin/reviews/{REVIEW_ID}/approve',
                 headers={'Authorization': USER_TOKEN})
ok('Non-admin cannot approve reviews', r.status_code in (401, 403))


# ─── PART D: ACTIVITY LOG ───────────────────────────────────
section("PART D: ACTIVITY LOG")

r = requests.get(f'{API}/company/activity', headers={'Authorization': CO_TOKEN})
ok('GET /company/activity', r.status_code == 200)
ok('Activity log returns list', isinstance(r.json(), list))

r = requests.get(f'{API}/admin/activity', headers={'Authorization': ADMIN})
ok('GET /admin/activity', r.status_code == 200)
ok('Admin activity log returns list', isinstance(r.json(), list))

r = requests.get(f'{API}/company/activity', headers={'Authorization': USER_TOKEN})
ok('GET /company/activity needs company auth', r.status_code in (401, 403))

r = requests.get(f'{API}/admin/activity', headers={'Authorization': USER_TOKEN})
ok('GET /admin/activity needs admin', r.status_code in (401, 403))


# ─── BACKWARD COMPATIBILITY ─────────────────────────────────
section("BACKWARD COMPATIBILITY")

r = requests.get(f'{API}/companies')
ok('GET /companies still works', r.status_code == 200)
ok('Companies list is list', isinstance(r.json(), list))

r = requests.get(f'{API}/company/{CO_ID}')
ok('GET /company/{id} still works', r.status_code == 200)
data = r.json()
ok('company/id has name field',
   'name' in data or 'name' in data.get('company', {}))

r = requests.get(f'{API}/projects')
ok('GET /projects still works', r.status_code == 200)

r = requests.get(f'{API}/subscription/plans')
ok('GET /subscription/plans still works', r.status_code == 200)

r = requests.get(f'{API}/company/subscription', headers={'Authorization': CO_TOKEN})
ok('GET /company/subscription still works', r.status_code == 200)

r = requests.get(f'{API}/company/subscription/usage', headers={'Authorization': CO_TOKEN})
ok('GET /company/subscription/usage still works', r.status_code == 200)

r = requests.get(f'{API}/company/bids', headers={'Authorization': CO_TOKEN})
ok('GET /company/bids still works', r.status_code == 200)


# ─── SUMMARY ────────────────────────────────────────────────
print('\n' + '='*55)
print('PHASE 8 TEST RESULTS')
print('='*55)
for t in results:
    print(t)
passed = sum(1 for t in results if '[PASS]' in t)
failed = sum(1 for t in results if '[FAIL]' in t)
total = passed + failed
print(f'\nTotal: {passed}/{total} passed, {failed} failed')
if failed:
    print('\nFailed tests:')
    for t in results:
        if '[FAIL]' in t:
            print(f'  {t}')
    sys.exit(1)
