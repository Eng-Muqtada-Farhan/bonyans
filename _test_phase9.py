"""
Phase 9 — Security & Production Readiness Tests
Tests: rate limiting, spam protection, permission hardening, audit log, health, system-status
"""
import requests, uuid, sys, time
import os
from dotenv import load_dotenv; load_dotenv()
ADMIN_PW = os.environ.get('ADMIN_PASSWORD', '')

API = 'http://127.0.0.1:8000'
results = []
uid = str(uuid.uuid4())[:8]
PASS = 'SecurePass9!'


def ok(name, passed, detail=''):
    sym = '[PASS]' if passed else '[FAIL]'
    results.append(f"{sym} {name}" + (f": {detail}" if detail else ""))
    if not passed:
        print(f"  FAIL >> {name}" + (f": {detail}" if detail else ""))


def section(title):
    print(f"\n{'='*55}\n{title}\n{'='*55}")


# ── SETUP ──────────────────────────────────────────────────
section("SETUP")

r = requests.post(f'{API}/login', json={'username': 'admin', 'password': ADMIN_PW})
ok('Admin login works', r.status_code == 200, str(r.status_code))
ADMIN = r.json().get('token', '')

r = requests.post(f'{API}/auth/register', json={
    'email': f'sec_user_{uid}@test.com', 'password': PASS,
    'display_name': f'Security Test User {uid}'
})
ok('Register user', r.status_code == 200)
USER_TOKEN = r.json().get('token', '')
USER_ID    = r.json().get('user_id')

r = requests.post(f'{API}/auth/register', json={
    'email': f'sec_co_{uid}@test.com', 'password': PASS,
    'display_name': f'Company Owner {uid}'
})
ok('Register company owner', r.status_code == 200)
CO_TOKEN = r.json().get('token', '')

r = requests.post(f'{API}/company/create', json={
    'name': f'SecCo_{uid}', 'city': 'بغداد',
    'phone': '07722222222', 'spec': 'مقاولات'
}, headers={'Authorization': CO_TOKEN})
ok('Create company', r.status_code in (200, 201))
CO_ID = r.json().get('company_id')

r = requests.put(f'{API}/companies/{CO_ID}/status',
                 json={'status': 'approved'}, headers={'Authorization': ADMIN})
ok('Approve company', r.status_code == 200)


# ── PART A: RATE LIMITING — LOGIN ───────────────────────────
section("PART A — Rate Limiting: Login")

# Test admin /login rate limit — 5 attempts allowed, 6th should be blocked
# Use wrong password to avoid changing rate limit key while actually logging in
for i in range(5):
    requests.post(f'{API}/login', json={'username': 'admin', 'password': 'WRONG'})

r = requests.post(f'{API}/login', json={'username': 'admin', 'password': 'WRONG'})
ok('Admin login rate limit (6th attempt = 429)', r.status_code == 429, str(r.status_code))

# Verify error message is correct
ok('Rate limit message present', 'Too many' in r.text or '429' in str(r.status_code))

# Test user /auth/login rate limit
for i in range(5):
    requests.post(f'{API}/auth/login', json={'email': f'rl_{uid}@x.com', 'password': 'wrong'})
r = requests.post(f'{API}/auth/login', json={'email': f'rl_{uid}@x.com', 'password': 'wrong'})
ok('User auth/login rate limit (6th = 429)', r.status_code == 429, str(r.status_code))

# Test company /company/login rate limit (different IP bucket simulated by different email)
for i in range(5):
    requests.post(f'{API}/company/login', json={'email': f'co_rl_{uid}@x.com', 'password': 'wrong'})
r = requests.post(f'{API}/company/login', json={'email': f'co_rl_{uid}@x.com', 'password': 'wrong'})
ok('Company login rate limit (6th = 429)', r.status_code == 429, str(r.status_code))


# ── PART A: RATE LIMITING — ACTIONS ─────────────────────────
section("PART A — Rate Limiting: Actions")

# Create a conversation for messaging tests
r = requests.post(f'{API}/conversations', json={
    'company_id': CO_ID,
    'message': ' '
}, headers={'Authorization': USER_TOKEN})
ok('Create conversation for rate limit test', r.status_code in (200, 201))
CONV_ID = r.json().get('conversation_id')

# Send 30 messages (the limit) — each must succeed
sent = 0
for i in range(30):
    r = requests.post(f'{API}/conversations/{CONV_ID}/messages',
                      json={'message': f'رسالة اختبار {i+1}'},
                      headers={'Authorization': USER_TOKEN})
    if r.status_code in (200, 201):
        sent += 1

ok('30 messages sent successfully (within limit)', sent == 30, f"sent={sent}")

# 31st message should be rate-limited
r = requests.post(f'{API}/conversations/{CONV_ID}/messages',
                  json={'message': 'رسالة زائدة'},
                  headers={'Authorization': USER_TOKEN})
ok('31st message is rate-limited (429)', r.status_code == 429, str(r.status_code))


# ── PART B: SPAM PROTECTION ──────────────────────────────────
section("PART B — Spam Protection")

# Empty message rejected
r = requests.post(f'{API}/conversations/{CONV_ID}/messages',
                  json={'message': ''},
                  headers={'Authorization': CO_TOKEN})
ok('Empty message rejected (422)', r.status_code == 422, str(r.status_code))

# Whitespace-only message rejected
r = requests.post(f'{API}/conversations/{CONV_ID}/messages',
                  json={'message': '   '},
                  headers={'Authorization': CO_TOKEN})
ok('Whitespace-only message rejected (422)', r.status_code == 422, str(r.status_code))

# Review spam: empty client_name rejected
r = requests.post(f'{API}/reviews', json={
    'company_id': CO_ID, 'client_name': '',
    'rating': 5, 'comment': 'test'
})
ok('Review with empty client_name rejected (422)', r.status_code == 422, str(r.status_code))

# Review spam: whitespace client_name rejected
r = requests.post(f'{API}/reviews', json={
    'company_id': CO_ID, 'client_name': '   ',
    'rating': 5, 'comment': 'test'
})
ok('Review with whitespace client_name rejected (422)', r.status_code == 422, str(r.status_code))

# Review spam: invalid rating (0)
r = requests.post(f'{API}/reviews', json={
    'company_id': CO_ID, 'client_name': 'عميل',
    'rating': 0, 'comment': 'test'
})
ok('Review with rating=0 rejected (422)', r.status_code == 422, str(r.status_code))

# Review spam: invalid rating (6)
r = requests.post(f'{API}/reviews', json={
    'company_id': CO_ID, 'client_name': 'عميل',
    'rating': 6, 'comment': 'test'
})
ok('Review with rating=6 rejected (422)', r.status_code == 422, str(r.status_code))

# Valid review still works
r = requests.post(f'{API}/reviews', json={
    'company_id': CO_ID, 'client_name': f'عميل تجربة {uid}',
    'rating': 4, 'comment': 'جيد'
})
ok('Valid review accepted (200/201)', r.status_code in (200, 201), str(r.status_code))


# ── PART C: PERMISSION HARDENING ────────────────────────────
section("PART C — Permission Hardening")

# Unauthenticated access to protected endpoints
r = requests.get(f'{API}/conversations')
ok('GET /conversations requires auth (401)', r.status_code == 401, str(r.status_code))

r = requests.get(f'{API}/notifications')
ok('GET /notifications requires auth (401)', r.status_code == 401, str(r.status_code))

r = requests.get(f'{API}/company/me')
ok('GET /company/me requires auth (401)', r.status_code == 401, str(r.status_code))

# User cannot access company-only endpoints
r = requests.get(f'{API}/company/me', headers={'Authorization': USER_TOKEN})
ok('User cannot access /company/me (401/403)', r.status_code in (401, 403), str(r.status_code))

# Admin-only endpoints require admin token
r = requests.get(f'{API}/admin/system-status')
ok('GET /admin/system-status requires admin auth (401)', r.status_code == 401, str(r.status_code))

r = requests.get(f'{API}/admin/system-status', headers={'Authorization': USER_TOKEN})
ok('User cannot access /admin/system-status (401)', r.status_code == 401, str(r.status_code))

# Company cannot access another company's conversation
r2 = requests.post(f'{API}/auth/register', json={
    'email': f'other_co_{uid}@test.com', 'password': PASS,
    'display_name': f'Other User {uid}'
})
OTHER_TOKEN = r2.json().get('token', '')
r = requests.get(f'{API}/conversations/{CONV_ID}/messages',
                 headers={'Authorization': OTHER_TOKEN})
ok('Other user cannot read conversation messages (403/404)',
   r.status_code in (403, 404), str(r.status_code))


# ── PART D: SECURITY AUDIT LOG ──────────────────────────────
section("PART D — Security Audit Log")

# Audit log should have entries from our login tests above
r = requests.get(f'{API}/admin/system-status', headers={'Authorization': ADMIN})
ok('GET /admin/system-status returns 200', r.status_code == 200, str(r.status_code))
data = r.json()
ok('audit_log count > 0', (data.get('audit_log') or {}).get('total', 0) > 0,
   str((data.get('audit_log') or {}).get('total')))


# ── PART F: HEALTH & MONITORING ─────────────────────────────
section("PART F — Health & Monitoring")

r = requests.get(f'{API}/health')
ok('GET /health returns 200', r.status_code == 200, str(r.status_code))
h = r.json()
ok('health.database = ok', h.get('database') == 'ok', str(h))
ok('health.app = ok', h.get('app') == 'ok', str(h))

r = requests.get(f'{API}/admin/system-status', headers={'Authorization': ADMIN})
ok('GET /admin/system-status (admin)', r.status_code == 200)
s = r.json()
ok('system-status has companies key', 'companies' in s)
ok('system-status has projects key', 'projects' in s)
ok('system-status has subscriptions key', 'subscriptions' in s)
ok('system-status has messages key', 'messages' in s)
ok('system-status has reviews key', 'reviews' in s)
ok('system-status has users key', 'users' in s)
ok('system-status has audit_log key', 'audit_log' in s)
ok('companies.total >= 1', (s.get('companies') or {}).get('total', 0) >= 1)
ok('users.total >= 1', (s.get('users') or {}).get('total', 0) >= 1)


# ── BACKWARD COMPATIBILITY ───────────────────────────────────
section("BACKWARD COMPATIBILITY")

r = requests.get(f'{API}/companies')
ok('GET /companies still works', r.status_code == 200)
ok('Returns list', isinstance(r.json(), list))

r = requests.get(f'{API}/company/{CO_ID}')
ok('GET /company/{id} still works', r.status_code == 200)
ok('Has company key', 'company' in r.json())

r = requests.get(f'{API}/projects')
ok('GET /projects still works', r.status_code == 200)

r = requests.get(f'{API}/subscription/plans')
ok('GET /subscription/plans still works', r.status_code == 200)

# Valid login (admin) still works even after rate limit tests (new IP bucket in test)
r = requests.post(f'{API}/login', json={'username': 'admin', 'password': ADMIN_PW})
# This may be rate-limited since we used the same loopback IP — it's ok if it returns 429
ok('Admin login works or rate-limited (200 or 429)', r.status_code in (200, 429), str(r.status_code))


# ── SUMMARY ─────────────────────────────────────────────────
print('\n' + '='*55)
print('PHASE 9 TEST RESULTS')
print('='*55)
for t in results:
    print(t)
passed_n = sum(1 for t in results if '[PASS]' in t)
failed_n = sum(1 for t in results if '[FAIL]' in t)
total    = passed_n + failed_n
print(f'\nTotal: {passed_n}/{total} passed, {failed_n} failed')
if failed_n:
    print('\nFailed tests:')
    for t in results:
        if '[FAIL]' in t:
            print(f'  {t}')
    sys.exit(1)
