"""API verification test - runs all key Phase 1 & Phase 3 endpoints"""
import httpx, sys

base = 'http://127.0.0.1:8765'
client = httpx.Client(timeout=90.0)

try:
    # 1. Health
    r = client.get(f'{base}/api/health')
    print(f'[1] Health: {r.status_code} - {r.json().get("status")}')

    # 2. Login  
    r = client.post(f'{base}/api/v1/auth/login', json={'username':'admin','password':'admin123'})
    token = r.json().get('access_token', '')
    h = {'Authorization': f'Bearer {token}'}
    print(f'[2] Login: {r.status_code} - token_received={bool(token)}')

    # 3. System info
    r = client.get(f'{base}/api/v1/system/info')
    d = r.json()
    print(f'[3] System Info: {r.status_code} - company={d.get("company")}, brands={d.get("brands")}, invoices={d.get("total_invoices")}')

    # 4. Brands
    r = client.get(f'{base}/api/v1/brands/', headers=h)
    brands = r.json() if r.status_code == 200 else []
    print(f'[4] Brands: {r.status_code} - {[b["name"] for b in brands]}')

    # 5. PDF templates list
    r = client.get(f'{base}/api/v1/pdf/templates', headers=h)
    print(f'[5] PDF Templates: {r.status_code} - {r.json()}')

    # 6. ERP raw materials
    r = client.get(f'{base}/api/v1/erp/raw-materials/', headers=h)
    count = len(r.json()) if r.status_code == 200 else 'err'
    print(f'[6] Raw Materials: {r.status_code} - count={count}')

    # 7. ERP BOM list
    r = client.get(f'{base}/api/v1/erp/boms/', headers=h)
    count = len(r.json()) if r.status_code == 200 else r.text[:60]
    print(f'[7] BOM Formulas: {r.status_code} - count={count}')

    # 8. POS invoices for SARA brand_id=1
    r = client.get(f'{base}/api/v1/pos/invoices/?brand_id=1', headers=h)
    count = len(r.json()) if r.status_code == 200 else r.text[:60]
    print(f'[8] SARA Invoices: {r.status_code} - count={count}')

    # 9. Accounting P&L
    r = client.get(f'{base}/api/v1/accounting/profit-loss/', headers=h)
    keys = list(r.json().keys())[:5] if r.status_code == 200 else r.text[:60]
    print(f'[9] P&L Report: {r.status_code} - keys={keys}')

    # 10. OpenAPI docs
    r = client.get(f'{base}/api/docs')
    print(f'[10] API Docs (Swagger): {r.status_code}')

    # 11. Link SARA PDF template
    r = client.post(f'{base}/api/v1/pdf/upload/1', headers=h)
    msg = r.json().get('message', '') if r.status_code == 200 else r.text[:100]
    print(f'[11] Link SARA PDF Template: {r.status_code} - {msg}')

    # 12. Link LMN PDF template  
    r = client.post(f'{base}/api/v1/pdf/upload/2', headers=h)
    msg = r.json().get('message', '') if r.status_code == 200 else r.text[:100]
    print(f'[12] Link LMN PDF Template: {r.status_code} - {msg}')

    print()
    print("BASIC API VERIFICATION COMPLETE")

finally:
    client.close()
