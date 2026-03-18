"""E2E test for Week 2: WHOIS availability + CSV export"""
import httpx
import time
import sys

BASE = "http://127.0.0.1:8888"
client = httpx.Client(base_url=BASE, follow_redirects=True, timeout=30)
ok = True

def check(name, condition):
    global ok
    status = "PASS" if condition else "FAIL"
    if not condition:
        ok = False
    print(f"  [{status}] {name}")

# 1. Homepage
r = client.get("/")
check("Dashboard loads", r.status_code == 200)

# 2. Check existing candidates (from Week 1 test)
r = client.get("/candidates")
check("Candidates page loads", r.status_code == 200)
has_candidates = "No candidates" not in r.text and "domain" in r.text.lower()
print(f"  Has existing candidates: {has_candidates}")

# 3. Sources page
r = client.get("/sources")
check("Sources page loads", r.status_code == 200)

# 4. Test WHOIS on source 1 (if exists)
r = client.post("/whois/1")
check("WHOIS trigger accepted", r.status_code == 200)

print("  Waiting 35s for WHOIS checks...")
time.sleep(35)

# 5. Check availability data
r = client.get("/candidates")
has_avail = "Available" in r.text or "Registered" in r.text or "Expired" in r.text or "check_failed" in r.text.lower()
check("Availability data populated", has_avail)

# 6. CSV export
r = client.get("/export/csv")
check("CSV export status 200", r.status_code == 200)
lines = r.text.strip().split("\n")
check(f"CSV has data ({len(lines)} rows)", len(lines) > 1)
print(f"  CSV header: {lines[0][:80]}")
if len(lines) > 1:
    print(f"  CSV row 1: {lines[1][:100]}")

# 7. Availability filter
for f in ["registered", "available", "unchecked"]:
    r = client.get(f"/candidates?availability={f}")
    check(f"Filter '{f}' loads", r.status_code == 200)

# 8. Source detail
r = client.get("/sources/1")
check("Source detail page loads", r.status_code == 200)

print()
if ok:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
    sys.exit(1)
