"""
Phase 8.1 — Public UX Integration Tests
Tests: conversations from profile, reviews, reply visibility, avg rating, notification badge data
"""
import requests, uuid, sys

API = 'http://127.0.0.1:8000'
results = []
uid = str(uuid.uuid4())[:8]
PASS = 'SecurePass81!'


def ok(name, passed, detail=''):
    sym = '[PASS]' if passed else '[FAIL]'
    results.append(f"{sym} {name}" + (f": {detail}" if detail else ""))
    if not passed:
        print(f"  FAIL >> {name}" + (f": {detail}" if detail else ""))


def section(title):
    print(f"\n{'='*55}\n{title}\n{'='*55}")


# ── SETUP ──────────────────────────────────────────────────
section("SETUP")

r = requests.post(f'{API}/login', json={'username': 'admin', 'password': '26'})
ok('Admin login', r.status_code == 200)
ADMIN = r.json().get('token', '')

# Client user (simulates visitor on company_profile.html)
r = requests.post(f'{API}/auth/register', json={
    'email': f'ux_client_{uid}@test.com', 'password': PASS,
    'display_name': f'زائر {uid}'
})
ok('Register client user', r.status_code == 200)
CLIENT_TOKEN = r.json().get('token', '')
CLIENT_ID    = r.json().get('user_id')

# Company
r = requests.post(f'{API}/auth/register', json={
    'email': f'ux_co_{uid}@test.com', 'password': PASS,
    'display_name': f'مالك شركة {uid}'
})
ok('Register company owner', r.status_code == 200)
CO_TOKEN = r.json().get('token', '')

r = requests.post(f'{API}/company/create', json={
    'name': f'UX_Co_{uid}', 'city': 'بغداد',
    'phone': '07711111111', 'spec': 'مقاولات'
}, headers={'Authorization': CO_TOKEN})
ok('Create company', r.status_code in (200, 201))
CO_ID = r.json().get('company_id')

r = requests.put(f'{API}/companies/{CO_ID}/status',
                 json={'status': 'approved'}, headers={'Authorization': ADMIN})
ok('Approve company', r.status_code == 200)


# ── PART 1: CONVERSATION FROM PROFILE PAGE ─────────────────
section("PART 1 — Conversation from company profile")

# Simulates clicking "تواصل مع الشركة" on company_profile.html
r = requests.post(f'{API}/conversations', json={
    'company_id': CO_ID,
    'message': 'مرحباً، أريد الاستفسار عن مشروع بناء'
}, headers={'Authorization': CLIENT_TOKEN})
ok('POST /conversations (from profile page)', r.status_code in (200, 201), str(r.status_code))
CONV_ID = r.json().get('conversation_id')
ok('Conversation ID returned', bool(CONV_ID))

# Idempotent — same conversation returned on second click
r2 = requests.post(f'{API}/conversations', json={
    'company_id': CO_ID,
    'message': 'رسالة ثانية'
}, headers={'Authorization': CLIENT_TOKEN})
ok('Second click returns same conversation', r2.json().get('conversation_id') == CONV_ID)

# Client sends a real message
r = requests.post(f'{API}/conversations/{CONV_ID}/messages', json={
    'message': 'هل يمكنكم إعطائي عرض سعر لمشروع سكني؟'
}, headers={'Authorization': CLIENT_TOKEN})
ok('Client sends message from profile page', r.status_code in (200, 201))
MSG_ID = r.json().get('message_id')

# Company sees the conversation in dashboard
r = requests.get(f'{API}/conversations', headers={'Authorization': CO_TOKEN})
ok('Company sees conversation in dashboard', r.status_code == 200)
co_convs = r.json()
ok('Company conversation list not empty', len(co_convs) > 0)
found = next((c for c in co_convs if c['id'] == CONV_ID), None)
ok('Specific conversation appears for company', found is not None)
ok('Unread count > 0 for company',
   found is not None and int(found.get('unread', 0)) > 0,
   f"unread={found.get('unread') if found else 'N/A'}")

# Company replies
r = requests.post(f'{API}/conversations/{CONV_ID}/messages', json={
    'message': 'أهلاً، يسعدنا تقديم العرض. هل يمكنك إعطائنا تفاصيل أكثر؟'
}, headers={'Authorization': CO_TOKEN})
ok('Company replies from dashboard', r.status_code in (200, 201))

# Client reads messages (simulates opening chat drawer on profile page)
r = requests.get(f'{API}/conversations/{CONV_ID}/messages',
                 headers={'Authorization': CLIENT_TOKEN})
ok('Client reads messages (chat drawer)', r.status_code == 200)
msgs = r.json()
real_msgs = [m for m in msgs if m.get('message','').strip() not in ('', ' ')]
ok('Messages contain client and company messages', len(real_msgs) >= 2)
ok('Last message is from company', real_msgs[-1]['sender_type'] == 'company')


# ── PART 2 & 3: REVIEWS + REPLIES ─────────────────────────
section("PART 2 & 3 — Reviews and replies")

# Submit review (no auth required — public form on company_profile.html)
r = requests.post(f'{API}/reviews', json={
    'company_id': CO_ID, 'client_name': f'عميل راضٍ {uid}',
    'rating': 5, 'comment': 'خدمة ممتازة وسرعة في التنفيذ'
})
ok('POST /reviews (public form, no auth)', r.status_code in (200, 201))
REV1_ID = r.json().get('review_id')
ok('Review status is pending', r.json().get('status') == 'pending')

r = requests.post(f'{API}/reviews', json={
    'company_id': CO_ID, 'client_name': f'عميل آخر {uid}',
    'rating': 4, 'comment': 'جيد جداً'
})
ok('Second review submitted', r.status_code in (200, 201))
REV2_ID = r.json().get('review_id')

# Pending reviews NOT visible on profile page
r = requests.get(f'{API}/company/{CO_ID}/reviews')
ok('GET /company/{id}/reviews (profile page load)', r.status_code == 200)
ok('Pending reviews hidden from profile page', len(r.json()) == 0)

# Admin approves both
r = requests.put(f'{API}/admin/reviews/{REV1_ID}/approve',
                 headers={'Authorization': ADMIN})
ok('Admin approves review 1', r.status_code == 200)
r = requests.put(f'{API}/admin/reviews/{REV2_ID}/approve',
                 headers={'Authorization': ADMIN})
ok('Admin approves review 2', r.status_code == 200)

# Now visible on profile page
r = requests.get(f'{API}/company/{CO_ID}/reviews')
ok('Approved reviews visible on profile page', r.status_code == 200)
reviews = r.json()
ok('Both reviews appear', len(reviews) == 2)
ok('Reviews have rating field', all('rating' in rv for rv in reviews))
ok('Reviews have client_name field', all('client_name' in rv for rv in reviews))
ok('Reviews have comment field', all('comment' in rv for rv in reviews))

# Average rating calculation
ratings = [rv['rating'] for rv in reviews]
avg = sum(ratings) / len(ratings)
ok('Average rating is correct (4.5)', abs(avg - 4.5) < 0.01, f"avg={avg}")

# Company adds reply (Part 3)
r = requests.post(f'{API}/reviews/{REV1_ID}/reply', json={
    'reply': 'شكراً جزيلاً على تقييمكم الكريم، يسعدنا خدمتكم دائماً.'
}, headers={'Authorization': CO_TOKEN})
ok('Company adds reply to review', r.status_code == 200)

# Reply visible on profile page
r = requests.get(f'{API}/company/{CO_ID}/reviews')
reviews_with_reply = r.json()
review1 = next((rv for rv in reviews_with_reply if rv['id'] == REV1_ID), None)
ok('Reply appears in profile page reviews', review1 is not None and review1.get('reply') is not None)
ok('Reply text is correct',
   review1 and 'شكراً' in (review1.get('reply') or ''))

# Review without reply has no reply field or null
review2 = next((rv for rv in reviews_with_reply if rv['id'] == REV2_ID), None)
ok('Review without reply has null reply', review2 and review2.get('reply') is None)


# ── PART 4: REVIEW STATS ON COMPANY LIST ──────────────────
section("PART 4 — Review stats in GET /companies")

r = requests.get(f'{API}/companies')
ok('GET /companies returns 200', r.status_code == 200)
companies = r.json()
our_co = next((c for c in companies if c['id'] == CO_ID), None)
ok('Our company appears in list', our_co is not None)
ok('review_count field present', 'review_count' in (our_co or {}),
   str(list(our_co.keys()) if our_co else 'not found'))
ok('review_avg field present', 'review_avg' in (our_co or {}))
ok('review_count is 2', (our_co or {}).get('review_count') == 2,
   f"got {(our_co or {}).get('review_count')}")
ok('review_avg is 4.5', abs(float((our_co or {}).get('review_avg') or 0) - 4.5) < 0.1,
   f"got {(our_co or {}).get('review_avg')}")

# Verify existing fields not broken
for field in ['id', 'name', 'city', 'phone', 'spec', 'status', 'verified']:
    ok(f'Existing field {field} still present', field in (our_co or {}))


# ── PART 5: NOTIFICATION BADGE DATA ───────────────────────
section("PART 5 — Notification badge data")

# Company should have notifications from: new message, new review (x2)
r = requests.get(f'{API}/notifications', headers={'Authorization': CO_TOKEN})
ok('GET /notifications for company', r.status_code == 200)
notifs = r.json()
ok('Company has notifications', len(notifs) > 0)

unread = [n for n in notifs if not n['is_read']]
ok('Company has unread notifications (badge should show)',
   len(unread) > 0, f"{len(unread)} unread")

types = {n['type'] for n in notifs}
ok('new_message notification exists', 'new_message' in types)
ok('new_review notification exists', 'new_review' in types)

# Client should have notification (company replied)
r = requests.get(f'{API}/notifications', headers={'Authorization': CLIENT_TOKEN})
ok('GET /notifications for client user', r.status_code == 200)
client_notifs = r.json()
ok('Client has new_message notification', any(n['type'] == 'new_message' for n in client_notifs))

# Conversations unread count (drives message badge)
r = requests.get(f'{API}/conversations', headers={'Authorization': CO_TOKEN})
ok('Conversations unread count available', r.status_code == 200)
conv_list = r.json()
total_unread = sum(int(c.get('unread', 0)) for c in conv_list)
ok('Total unread messages > 0 (badge data)', total_unread > 0, f"total_unread={total_unread}")


# ── BACKWARD COMPAT ────────────────────────────────────────
section("BACKWARD COMPATIBILITY")

r = requests.get(f'{API}/companies')
ok('GET /companies still works', r.status_code == 200)
ok('Returns list', isinstance(r.json(), list))

r = requests.get(f'{API}/company/{CO_ID}')
ok('GET /company/{id} still works', r.status_code == 200)
data = r.json()
ok('company profile has company key', 'company' in data)
ok('company profile has projects key', 'projects' in data)
ok('company profile has gallery key', 'gallery' in data)

r = requests.get(f'{API}/projects')
ok('GET /projects still works', r.status_code == 200)

r = requests.get(f'{API}/subscription/plans')
ok('GET /subscription/plans still works', r.status_code == 200)


# ── SUMMARY ────────────────────────────────────────────────
print('\n' + '='*55)
print('PHASE 8.1 TEST RESULTS')
print('='*55)
for t in results:
    print(t)
passed = sum(1 for t in results if '[PASS]' in t)
failed = sum(1 for t in results if '[FAIL]' in t)
total  = passed + failed
print(f'\nTotal: {passed}/{total} passed, {failed} failed')
if failed:
    print('\nFailed tests:')
    for t in results:
        if '[FAIL]' in t:
            print(f'  {t}')
    sys.exit(1)
