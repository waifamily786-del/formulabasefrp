"""Discover actual API routes from OpenAPI spec"""
import httpx, json

base = 'http://127.0.0.1:8765'
client = httpx.Client(timeout=30.0, follow_redirects=True)

r = client.post(f'{base}/api/v1/auth/login', json={'username':'admin','password':'admin123'})
token = r.json().get('access_token', '')
h = {'Authorization': f'Bearer {token}'}

r = client.get(f'{base}/api/openapi.json')
spec = r.json()
paths = list(spec.get('paths', {}).keys())

print("All API paths:")
for p in sorted(paths):
    print(f"  {p}")

# Test key paths
print("\n--- Key endpoint tests ---")
tests = [
    ('GET', '/api/v1/pos/invoices/'),
    ('GET', '/api/v1/pos/quick-invoice/'),
    ('GET', '/api/v1/accounting/profit-loss'),
    ('GET', '/api/v1/accounting/reports/profit-loss'),
    ('GET', '/api/v1/erp/boms/'),
    ('GET', '/api/v1/erp/bom/'),
    ('GET', '/api/v1/erp/production/'),
]
for method, path in tests:
    r = client.get(f'{base}{path}', headers=h)
    print(f"  {method} {path}: {r.status_code}")

client.close()
