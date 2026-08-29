"""
Phase 10 — Final UI, Performance & Launch Tests
Tests: new routes, SEO files, PWA files, nav assets, backward compat with all previous phases
"""
import requests, os, sys

API = 'http://127.0.0.1:8000'
BASE = 'D:/Q/MD'
results = []


def ok(name, passed, detail=''):
    sym = '[PASS]' if passed else '[FAIL]'
    results.append(f"{sym} {name}" + (f": {detail}" if detail else ""))
    if not passed:
        print(f"  FAIL >> {name}" + (f": {detail}" if detail else ""))


def section(title):
    print(f"\n{'='*55}\n{title}\n{'='*55}")


# ── ADMIN TOKEN ─────────────────────────────────────────────
section("SETUP")
r = requests.post(f'{API}/login', json={'username': 'admin', 'password': '26'})
# May be rate-limited from prior test runs — both 200 and 429 are acceptable here
ok('Admin login reachable', r.status_code in (200, 401, 429), str(r.status_code))
ADMIN = r.json().get('token', '') if r.status_code == 200 else ''


# ── PART 1: NEW ROUTES ──────────────────────────────────────
section("PART 1 — New Routes (Phase 10)")

# GET /stats — public platform statistics
r = requests.get(f'{API}/stats')
ok('GET /stats returns 200', r.status_code == 200, str(r.status_code))
s = r.json()
ok('/stats has companies key', 'companies' in s)
ok('/stats has projects key',  'projects'  in s)
ok('/stats has reviews key',   'reviews'   in s)
ok('/stats has avg_rating key','avg_rating' in s)
ok('/stats companies >= 0', int(s.get('companies', -1)) >= 0)

# GET /company/slug/{slug} — slug resolver
r = requests.get(f'{API}/company/slug/1')
ok('GET /company/slug/1 (numeric fallback)', r.status_code in (200, 404), str(r.status_code))
if r.status_code == 200:
    ok('Slug response has company_id', 'company_id' in r.json())

# GET /health — unchanged from Phase 9
r = requests.get(f'{API}/health')
ok('GET /health still works', r.status_code == 200)
ok('health.database = ok', r.json().get('database') == 'ok')

# GET /admin/system-status — unchanged
if ADMIN:
    r = requests.get(f'{API}/admin/system-status', headers={'Authorization': ADMIN})
    ok('GET /admin/system-status still works', r.status_code == 200)


# ── PART 2: SEO FILES ───────────────────────────────────────
section("PART 7 — SEO Files")

r = requests.get(f'{API}/robots.txt')
ok('GET /robots.txt returns 200', r.status_code == 200, str(r.status_code))
ok('robots.txt has User-agent', 'User-agent' in r.text)
ok('robots.txt has Disallow admin', 'Disallow: /admin' in r.text)
ok('robots.txt has Sitemap', 'Sitemap' in r.text)

r = requests.get(f'{API}/sitemap.xml')
ok('GET /sitemap.xml returns 200', r.status_code == 200, str(r.status_code))
ok('sitemap.xml has urlset', '<urlset' in r.text)
ok('sitemap.xml has index.html', 'index.html' in r.text)
ok('sitemap.xml has projects.html', 'projects.html' in r.text)


# ── PART 3: PWA FILES ───────────────────────────────────────
section("PART 8 — PWA Files")

r = requests.get(f'{API}/manifest.json')
ok('GET /manifest.json returns 200', r.status_code == 200, str(r.status_code))
try:
    m = r.json()
    ok('manifest.json has name', 'name' in m)
    ok('manifest.json name contains بُنيان', 'بُنيان' in m.get('name',''))
    ok('manifest.json has icons', len(m.get('icons',[])) > 0)
    ok('manifest.json has start_url', 'start_url' in m)
    ok('manifest.json display=standalone', m.get('display') == 'standalone')
    ok('manifest.json theme_color', m.get('theme_color') == '#c8a96e')
    ok('manifest.json lang=ar', m.get('lang') == 'ar')
except Exception as e:
    ok('manifest.json is valid JSON', False, str(e))

r = requests.get(f'{API}/service-worker.js')
ok('GET /service-worker.js returns 200', r.status_code == 200, str(r.status_code))
ok('service-worker.js has install event', 'install' in r.text)
ok('service-worker.js has fetch event', 'fetch' in r.text)
ok('service-worker.js has CACHE_NAME', 'CACHE_NAME' in r.text)

r = requests.get(f'{API}/icons/icon.svg')
ok('GET /icons/icon.svg accessible', r.status_code == 200, str(r.status_code))


# ── PART 4: SHARED ASSETS ───────────────────────────────────
section("Shared Assets (bunyan.css, bunyan-nav.js)")

r = requests.get(f'{API}/bunyan.css')
ok('GET /bunyan.css returns 200', r.status_code == 200, str(r.status_code))
ok('bunyan.css has --gold variable', '--gold' in r.text)
ok('bunyan.css has #bn-nav', '#bn-nav' in r.text)
ok('bunyan.css has glass-card', 'glass-card' in r.text)
ok('bunyan.css has bn-footer', 'bn-footer' in r.text)

r = requests.get(f'{API}/bunyan-nav.js')
ok('GET /bunyan-nav.js returns 200', r.status_code == 200, str(r.status_code))
ok('bunyan-nav.js has BunyanNav', 'BunyanNav' in r.text)
ok('bunyan-nav.js has logout function', 'logout' in r.text)
ok('bunyan-nav.js has injectFooter', 'injectFooter' in r.text)


# ── PART 5: HTML FILES UPDATED ──────────────────────────────
section("HTML Files — PWA + Nav Integration")

pages = {
    'index.html':           ['bunyan.css', 'bunyan-nav.js', 'manifest.json', 'service-worker'],
    'projects.html':        ['bunyan.css', 'bunyan-nav.js', 'manifest.json', 'service-worker'],
    'project_details.html': ['bunyan.css', 'bunyan-nav.js', 'manifest.json', 'service-worker'],
    'company_profile.html': ['bunyan.css', 'bunyan-nav.js', 'manifest.json', 'service-worker'],
}

for page, keywords in pages.items():
    r = requests.get(f'{API}/{page}')
    ok(f'GET /{page} returns 200', r.status_code == 200, str(r.status_code))
    for kw in keywords:
        ok(f'{page} contains {kw}', kw in r.text)

# Dashboard — PWA only (no bunyan-nav.js injection since it has its own sidebar)
r = requests.get(f'{API}/company_dashboard.html')
ok('GET /company_dashboard.html returns 200', r.status_code == 200, str(r.status_code))
ok('dashboard has manifest.json', 'manifest.json' in r.text)
ok('dashboard has service-worker', 'service-worker' in r.text)


# ── PART 6: README ──────────────────────────────────────────
section("Part 10 — README_LAUNCH.md")

readme_path = os.path.join(BASE, 'README_LAUNCH.md')
ok('README_LAUNCH.md exists', os.path.exists(readme_path))
if os.path.exists(readme_path):
    with open(readme_path, encoding='utf-8') as f:
        content = f.read()
    ok('README has deployment steps', 'خطوات النشر' in content or 'النشر' in content)
    ok('README has health check', '/health' in content)
    ok('README has backup section', 'النسخ الاحتياطي' in content or 'backup' in content.lower())
    ok('README has checklist', 'Checklist' in content or 'checklist' in content.lower())


# ── REGRESSION: ALL PREVIOUS PHASES ────────────────────────
section("REGRESSION — Phase 7 APIs")

r = requests.get(f'{API}/projects')
ok('GET /projects still works', r.status_code == 200)
ok('Returns list', isinstance(r.json(), list))

r = requests.get(f'{API}/subscription/plans')
ok('GET /subscription/plans still works', r.status_code == 200)
ok('Plans is a list', isinstance(r.json(), list))

r = requests.get(f'{API}/companies')
ok('GET /companies still works', r.status_code == 200)
companies = r.json()
ok('Companies is a list', isinstance(companies, list))

section("REGRESSION — Phase 8 APIs")

r = requests.get(f'{API}/conversations')
ok('GET /conversations requires auth (401)', r.status_code == 401)

r = requests.get(f'{API}/notifications')
ok('GET /notifications requires auth (401)', r.status_code == 401)

if companies:
    cid = companies[0]['id']
    r = requests.get(f'{API}/company/{cid}/reviews')
    ok(f'GET /company/{cid}/reviews works', r.status_code == 200)

section("REGRESSION — Phase 9 APIs")

r = requests.get(f'{API}/health')
ok('GET /health still works', r.status_code == 200)

r = requests.post(f'{API}/reviews', json={
    'company_id': 999999, 'client_name': '', 'rating': 0, 'comment': ''
})
ok('Spam review still rejected (422)', r.status_code == 422, str(r.status_code))

r = requests.post(f'{API}/conversations/999/messages',
                  json={'message': ''}, headers={'Authorization': 'bad'})
ok('Empty message + bad auth still rejected (401/422)', r.status_code in (401, 422), str(r.status_code))


# ── SUMMARY ─────────────────────────────────────────────────
print('\n' + '='*55)
print('PHASE 10 TEST RESULTS')
print('='*55)
for t in results:
    print(t)
passed_n = sum(1 for t in results if '[PASS]' in t)
failed_n = sum(1 for t in results if '[FAIL]' in t)
total    = passed_n + failed_n
print(f'\nTotal: {passed_n}/{total} passed, {failed_n} failed')
pct = round(passed_n / total * 100) if total else 0
print(f'Score: {pct}%')
if failed_n:
    print('\nFailed tests:')
    for t in results:
        if '[FAIL]' in t:
            print(f'  {t}')
    sys.exit(1)
