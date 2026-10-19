"""Final comprehensive Phase 1 & Phase 3 verification"""
import httpx, json

base = 'http://127.0.0.1:8765'
client = httpx.Client(timeout=60.0, follow_redirects=True)

# Login
r = client.post(f'{base}/api/v1/auth/login', json={'username':'admin','password':'admin123'})
token = r.json().get('access_token', '')
h = {'Authorization': f'Bearer {token}'}

results = []

def test(label, method, path, **kwargs):
    url = f'{base}{path}'
    r = getattr(client, method)(url, headers=h, **kwargs)
    ok = r.status_code in [200, 201]
    detail = ""
    if ok and r.text:
        try:
            d = r.json()
            if isinstance(d, list):
                detail = f"count={len(d)}"
            elif isinstance(d, dict):
                keys = list(d.keys())[:4]
                detail = f"keys={keys}"
        except:
            detail = f"text={r.text[:50]}"
    else:
        detail = r.text[:80] if not ok else ""
    results.append((ok, r.status_code, label, detail))
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {r.status_code}  {label}")
    if detail:
        print(f"           -> {detail}")

print()
print("=" * 65)
print("  FORMULABASE NEXUS — PHASE 1 & 3 FINAL VERIFICATION")
print("=" * 65)

print("\n--- AUTHENTICATION ---")
test("POST /api/v1/auth/login (admin)", "post", "/api/v1/auth/login", json={"username":"admin","password":"admin123"})
test("GET  /api/v1/auth/me", "get", "/api/v1/auth/me")

print("\n--- SYSTEM ---")
test("GET  /api/health", "get", "/api/health")
test("GET  /api/v1/system/info", "get", "/api/v1/system/info")

print("\n--- MULTI-BRAND PROFILES ---")
test("GET  /api/v1/brands/", "get", "/api/v1/brands/")
test("GET  /api/v1/brands/1 (SARA)", "get", "/api/v1/brands/1")
test("GET  /api/v1/brands/2 (LMN)", "get", "/api/v1/brands/2")

print("\n--- ERP FORMULA MODULE ---")
test("GET  /api/v1/erp/raw-materials", "get", "/api/v1/erp/raw-materials")
test("GET  /api/v1/erp/bom/1 (SARA product BOM)", "get", "/api/v1/erp/bom/1")
test("GET  /api/v1/erp/inventory/summary", "get", "/api/v1/erp/inventory/summary")
test("GET  /api/v1/erp/production-batches", "get", "/api/v1/erp/production-batches")
test("GET  /api/v1/erp/simulate-production/1", "get", "/api/v1/erp/simulate-production/1")

print("\n--- POS & INVOICE ---")
test("GET  /api/v1/pos/products/1 (SARA products)", "get", "/api/v1/pos/products/1")
test("GET  /api/v1/pos/customers/1 (SARA customers)", "get", "/api/v1/pos/customers/1")
test("GET  /api/v1/pos/invoices/1 (SARA invoices)", "get", "/api/v1/pos/invoices/1")
test("GET  /api/v1/pos/dashboard/1 (SARA dashboard)", "get", "/api/v1/pos/dashboard/1")

print("\n--- AUTO-ACCOUNTANT ENGINE ---")
test("GET  /api/v1/accounting/chart-of-accounts", "get", "/api/v1/accounting/chart-of-accounts")
test("GET  /api/v1/accounting/income-statement", "get", "/api/v1/accounting/income-statement")
test("GET  /api/v1/accounting/balance-sheet", "get", "/api/v1/accounting/balance-sheet")
test("GET  /api/v1/accounting/summary", "get", "/api/v1/accounting/summary")
test("GET  /api/v1/accounting/journal-entries", "get", "/api/v1/accounting/journal-entries")
test("GET  /api/v1/accounting/ar-aging", "get", "/api/v1/accounting/ar-aging")
test("GET  /api/v1/accounting/expenses", "get", "/api/v1/accounting/expenses")

print("\n--- SMART PDF ENGINE ---")
test("GET  /api/v1/pdf/templates", "get", "/api/v1/pdf/templates")
test("POST /api/v1/pdf/upload/1 (link SARA template)", "post", "/api/v1/pdf/upload/1")
test("POST /api/v1/pdf/upload/2 (link LMN template)", "post", "/api/v1/pdf/upload/2")
test("GET  /api/v1/pdf/template-info/1", "get", "/api/v1/pdf/template-info/1")
test("GET  /api/v1/pdf/generate/1 (generate invoice PDF)", "get", "/api/v1/pdf/generate/1")

print("\n--- API DOCS ---")
test("GET  /api/docs (Swagger UI)", "get", "/api/docs")

# Summary
passed = sum(1 for ok,*_ in results if ok)
total = len(results)
print()
print("=" * 65)
print(f"  RESULT: {passed}/{total} endpoints PASSING")
if passed == total:
    print("  STATUS: PHASE 1 & PHASE 3 COMPLETE!")
else:
    print(f"  STATUS: {total-passed} endpoints need attention")
print("=" * 65)

client.close()
