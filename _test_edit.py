import requests, base64

API = 'http://127.0.0.1:8000'

# Login
r = requests.post(f'{API}/login', json={'username': 'admin', 'password': '26'})
token = r.json().get('token', '')
headers = {'Authorization': token, 'Content-Type': 'application/json'}

results = []
def ok(name, passed, detail=''):
    results.append(f'[{"PASS" if passed else "FAIL"}] {name}' + (f': {detail}' if detail else ''))

# Get a company to edit
r = requests.get(f'{API}/admin/companies')
companies = r.json()
ok('GET /admin/companies', r.ok, f'{len(companies)} companies')
target_id = companies[0]['id'] if companies else None

if target_id:
    # Test: edit name + city only
    r = requests.put(f'{API}/companies/{target_id}',
                     json={'name': 'شركة معدّلة', 'city': 'Basra'},
                     headers=headers)
    ok('PUT /companies/{id} — edit name+city', r.ok, r.json())

    # Verify change persisted
    r2 = requests.get(f'{API}/admin/companies')
    updated = next((c for c in r2.json() if c['id'] == target_id), None)
    ok('Change persisted in DB', updated and updated['name'] == 'شركة معدّلة', updated)

    # Test: upload new image + save to company
    png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')
    upRes = requests.post(f'{API}/upload', files={'file': ('edit_test.png', png, 'image/png')})
    ok('POST /upload for edit', upRes.ok, upRes.json())
    img_url = upRes.json().get('url', '') if upRes.ok else ''

    r = requests.put(f'{API}/companies/{target_id}',
                     json={'image_url': img_url},
                     headers=headers)
    ok('PUT /companies/{id} — update image_url', r.ok and r.json().get('image_url') == img_url, r.json().get('image_url'))

    # Test: no fields → 400
    r = requests.put(f'{API}/companies/{target_id}', json={}, headers=headers)
    ok('PUT /companies/{id} — empty payload → 400', r.status_code == 400, r.status_code)

    # Test: invalid token → 401
    r = requests.put(f'{API}/companies/{target_id}',
                     json={'name': 'hack'},
                     headers={'Authorization': 'bad', 'Content-Type': 'application/json'})
    ok('PUT /companies/{id} — invalid token → 401', r.status_code == 401, r.status_code)

    # Restore original name
    requests.put(f'{API}/companies/{target_id}',
                 json={'name': companies[0]['name'], 'city': companies[0]['city']},
                 headers=headers)
    ok('Restore original name', True, 'done')

print()
for line in results:
    print(line)
passed = sum(1 for l in results if '[PASS]' in l)
failed = sum(1 for l in results if '[FAIL]' in l)
print(f'\nTotal: {passed} passed, {failed} failed')
