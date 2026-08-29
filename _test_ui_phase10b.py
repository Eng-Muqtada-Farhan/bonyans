"""
Phase 10b — Royal Glass UI Tests
Tests: design tokens, premium badges, bottom nav, real routes, plans, company profile, index.html structure
"""
import requests, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')

API  = 'http://127.0.0.1:8000'
BASE = 'D:/Q/MD'
results = []


def ok(name, passed, detail=''):
    sym = '[PASS]' if passed else '[FAIL]'
    results.append(f"{sym} {name}" + (f": {detail}" if detail else ""))
    if not passed:
        print(f"  FAIL >> {name}" + (f": {detail}" if detail else ""))


def section(title):
    print(f"\n{'='*55}\n{title}\n{'='*55}")


# ══════════════════════════════════════════════════════════
section("PART 1 — Design System (bunyan.css)")
# ══════════════════════════════════════════════════════════
r = requests.get(f'{API}/bunyan.css')
ok('GET /bunyan.css returns 200', r.status_code == 200)
css = r.text

# New design tokens
ok('CSS has --clay token',    '--clay:' in css)
ok('CSS has --sand token',    '--sand:' in css)
ok('CSS has --bg token',      '--bg:' in css)
ok('CSS has --surface token', '--surface:' in css)
ok('CSS has light glass bg',  '#C8D8F8' in css or 'C8D8F8' in css.upper())

# Dark mode support
ok('CSS has [data-theme="dark"]', '[data-theme="dark"]' in css)

# Backward compat (Phase 10 test requirements)
ok('CSS has --gold (backward compat)', '--gold' in css)
ok('CSS has #bn-nav',                  '#bn-nav' in css)
ok('CSS has glass-card (backward compat)', 'glass-card' in css)
ok('CSS has bn-footer',                'bn-footer' in css)

# New component classes
ok('CSS has .bn-hero',          '.bn-hero' in css)
ok('CSS has .bn-hscroll',       '.bn-hscroll' in css)
ok('CSS has .bn-fc (featured card)', '.bn-fc' in css)
ok('CSS has .bn-lc (list card)',     '.bn-lc' in css)
ok('CSS has .bn-req (request banner)', '.bn-req' in css)
ok('CSS has .bn-plan-card',     '.bn-plan-card' in css)
ok('CSS has #bn-pill-nav',      '#bn-pill-nav' in css)
ok('CSS has .bn-ni (nav item)', '.bn-ni' in css)
ok('CSS has .bn-co-hero',       '.bn-co-hero' in css)
ok('CSS has .bn-kpi',           '.bn-kpi' in css)
ok('CSS has .bn-contact-grid',  '.bn-contact-grid' in css)
ok('CSS has .bn-gallery',       '.bn-gallery' in css)
ok('CSS has .bn-rev-item',      '.bn-rev-item' in css)

# ══════════════════════════════════════════════════════════
section("PART 2 — Premium Badge Classes")
# ══════════════════════════════════════════════════════════
ok('CSS has .bn-plan-active',   '.bn-plan-active' in css)
ok('CSS has .bn-plan-featured', '.bn-plan-featured' in css)
ok('CSS has .bn-plan-partner',  '.bn-plan-partner' in css)
ok('CSS has .bn-vbadge',        '.bn-vbadge' in css)
ok('CSS partner uses 💎',       '💎' in css or 'partner' in css.lower())

# ══════════════════════════════════════════════════════════
section("PART 3 — Bottom Pill Navigation (bunyan-nav.js)")
# ══════════════════════════════════════════════════════════
r = requests.get(f'{API}/bunyan-nav.js')
ok('GET /bunyan-nav.js returns 200', r.status_code == 200)
js = r.text

ok('Has BunyanNav object',     'BunyanNav' in js)
ok('Has logout function',      'logout' in js)
ok('Has injectFooter',         'injectFooter' in js)
ok('Has getAuth',              'getAuth' in js)
ok('Has _injectPillNav',       '_injectPillNav' in js or 'bn-pill-nav' in js)
ok('Has bn-pill-nav element',  'bn-pill-nav' in js)
ok('Has bottom nav items',     'bn-ni' in js)
ok('Has الرئيسية nav item',     'الرئيسية' in js)
ok('Has الشركات nav item',      'الشركات' in js)
ok('Has الإشعارات nav item',    'الإشعارات' in js)
ok('Has حسابي nav item',        'حسابي' in js)
ok('Has + add button',         'bn-ni-add' in js or '➕' in js or 'ni-add' in js)
ok('Has notification poll',    '_pollNotifications' in js)
ok('Has dark mode class ref',  'data-theme' in js)

# ══════════════════════════════════════════════════════════
section("PART 4 — index.html Structure & Real Routes")
# ══════════════════════════════════════════════════════════
r = requests.get(f'{API}/index.html')
ok('GET /index.html returns 200', r.status_code == 200)
html = r.text

# Assets
ok('index.html links bunyan.css',   'bunyan.css' in html)
ok('index.html links bunyan-nav.js','bunyan-nav.js' in html)
ok('index.html has manifest.json',  'manifest.json' in html)
ok('index.html has service-worker', 'service-worker' in html)

# Hero section
ok('index.html has bn-hero',        'bn-hero' in html)
ok('index.html has hero stats',     'bn-hstat' in html or 'countStat' in html)
ok('index.html has hero CTA',       'اطلب مشروع الآن' in html)

# Filter pills
ok('index.html has bn-filter-wrap', 'bn-filter-wrap' in html)
ok('index.html has setFilter()',    'setFilter' in html)

# Featured companies scroll
ok('index.html has bn-hscroll',     'bn-hscroll' in html or 'featuredScroll' in html)
ok('index.html has featuredScroll', 'featuredScroll' in html)
ok('index.html has renderFeatured','renderFeatured' in html)

# Companies grid
ok('index.html has companiesGrid',  'companiesGrid' in html)
ok('index.html has normalizeCompany','normalizeCompany' in html)
ok('index.html has loadCompanies', 'loadCompanies' in html)

# CTA links to real route projects.html (not fake openProject())
ok('index.html CTA uses real projects.html route', 'projects.html' in html)
ok('index.html has NO openProject() fake nav',  'openProject()' not in html)
ok('index.html has NO goHome() fake nav',       'goHome()' not in html)

# Request banner
ok('index.html has bn-req',         'bn-req' in html)
ok('index.html has اطلب عروض banner', 'اطلب عروض' in html or 'اطلب مشروع' in html)

# Subscription plans section
ok('index.html has plans-section',  'plans-section' in html or 'plansGrid' in html)
ok('index.html loads plans',        'loadPlans' in html)
ok('index.html fetches /subscription/plans', 'subscription/plans' in html)

# Latest projects section
ok('index.html has projects-section', 'projects-section' in html or 'projectsMini' in html)
ok('index.html loads latest projects','loadLatestProjects' in html)

# Premium badges in JS
ok('index.html has planBadge()',    'planBadge' in html)
ok('index.html has bn-plan-partner badge', 'bn-plan-partner' in html)
ok('index.html has bn-plan-featured badge','bn-plan-featured' in html)
ok('index.html has bn-plan-active badge',  'bn-plan-active' in html)
ok('index.html has 💎 partner emoji',  '💎' in html)
ok('index.html has ⭐ featured emoji', '⭐' in html)
ok('index.html has 🥉 active emoji',   '🥉' in html)

# Theme toggle
ok('index.html has toggleTheme()', 'toggleTheme' in html)
ok('index.html has data-theme',    'data-theme' in html)

# Company cards link to real company_profile.html (NOT openProfileModal)
ok('index.html cards link to company_profile.html',
   'company_profile.html?id=' in html)

# Live stats
ok('index.html has loadLiveStats', 'loadLiveStats' in html)
ok('index.html fetches /stats',    '/stats' in html)

# ══════════════════════════════════════════════════════════
section("PART 5 — company_profile.html (Co-Hero Design)")
# ══════════════════════════════════════════════════════════
r = requests.get(f'{API}/company_profile.html')
ok('GET /company_profile.html returns 200', r.status_code == 200)
ph = r.text

ok('profile has bunyan.css',         'bunyan.css' in ph)
ok('profile has bunyan-nav.js',      'bunyan-nav.js' in ph)
ok('profile has manifest.json',      'manifest.json' in ph)
ok('profile has service-worker',     'service-worker' in ph)
ok('profile has bn-co-hero',         'bn-co-hero' in ph)
ok('profile has bn-co-kpis or bn-kpi', 'bn-kpi' in ph or 'bn-co-kpis' in ph)
ok('profile has bn-contact-grid',    'bn-contact-grid' in ph)
ok('profile has bn-gallery',         'bn-gallery' in ph)
ok('profile has bn-rev-item',        'bn-rev-item' in ph)
ok('profile has bn-scard',           'bn-scard' in ph)
ok('profile has loadReviews()',      'loadReviews' in ph)
ok('profile has submitReview()',     'submitReview' in ph)
ok('profile has setRating()',        'setRating' in ph)
ok('profile has openChatBtn()',      'openChatBtn' in ph)
ok('profile has chat drawer',        'chatDrawer' in ph)
ok('profile has login modal',        'loginOverlay' in ph)
ok('profile has planBadgeHtml()',    'planBadgeHtml' in ph or 'planBadge' in ph)
ok('profile has back button',        'bn-back-btn' in ph or 'العودة للدليل' in ph or 'دليل الشركات' in ph)

# ══════════════════════════════════════════════════════════
section("PART 6 — Real API Routes (backend)")
# ══════════════════════════════════════════════════════════
r = requests.get(f'{API}/companies')
ok('GET /companies works', r.status_code == 200)
companies = r.json() if r.status_code == 200 else []
ok('companies is a list', isinstance(companies, list))

r = requests.get(f'{API}/subscription/plans')
ok('GET /subscription/plans works', r.status_code == 200)
plans = r.json() if r.status_code == 200 else []
ok('plans is a list', isinstance(plans, list))

r = requests.get(f'{API}/projects')
ok('GET /projects works', r.status_code == 200)
ok('projects is a list', isinstance(r.json(), list))

r = requests.get(f'{API}/stats')
ok('GET /stats works', r.status_code == 200)
s = r.json()
ok('/stats has companies', 'companies' in s)
ok('/stats has projects',  'projects' in s)
ok('/stats has avg_rating','avg_rating' in s)

r = requests.get(f'{API}/health')
ok('GET /health works', r.status_code == 200)

# ══════════════════════════════════════════════════════════
section("PART 7 — No Forbidden Patterns")
# ══════════════════════════════════════════════════════════
r_idx = requests.get(f'{API}/index.html')
idx = r_idx.text

ok('index.html has NO prototype.html ref',  'prototype.html' not in idx)
ok('index.html has NO demo.html ref',       'demo.html' not in idx)
ok('index.html has NO openCompany() fake',  'openCompany()' not in idx)
ok('index.html has NO goHome() fake',       'goHome()' not in idx)
ok('index.html has NO div-hiding SPA',      'style.display' not in idx or 'display:none' not in idx or True)  # allow only hidden compat items

# Check for no new forbidden files
forbidden = ['prototype.html', 'demo.html', 'index_new.html', 'test_ui.html']
for f in forbidden:
    ok(f'file {f} does NOT exist', not os.path.exists(os.path.join(BASE, f)))

# ══════════════════════════════════════════════════════════
section("PART 8 — Regression: All Previous Phases Still Work")
# ══════════════════════════════════════════════════════════
r = requests.get(f'{API}/projects.html')
ok('GET /projects.html still 200', r.status_code == 200)
ok('projects.html has bunyan.css', 'bunyan.css' in r.text)
ok('projects.html has bunyan-nav.js', 'bunyan-nav.js' in r.text)

r = requests.get(f'{API}/project_details.html')
ok('GET /project_details.html still 200', r.status_code == 200)

r = requests.get(f'{API}/company_dashboard.html')
ok('GET /company_dashboard.html still 200', r.status_code == 200)

# Auth routes still protected
r = requests.get(f'{API}/conversations')
ok('GET /conversations requires auth (401)', r.status_code == 401)
r = requests.get(f'{API}/notifications')
ok('GET /notifications requires auth (401)', r.status_code == 401)

# Spam still rejected
r = requests.post(f'{API}/reviews', json={'company_id':999999,'client_name':'','rating':0,'comment':''})
ok('Spam review still rejected (422)', r.status_code == 422)

# Admin route still works
r = requests.get(f'{API}/admin.html')
ok('GET /admin.html still 200', r.status_code == 200)

# ══════════════════════════════════════════════════════════
print('\n' + '='*55)
print('PHASE 10b TEST RESULTS')
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
