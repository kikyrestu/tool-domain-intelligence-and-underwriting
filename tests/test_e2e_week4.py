"""E2E test for Week 4: Dashboard Polish, XLSX, Notes, Auth"""
import httpx
import re
import sys
import time

BASE = "http://127.0.0.1:8888"
AUTH = ("admin", "admin")
ok = True


def check(name, condition):
    global ok
    status = "PASS" if condition else "FAIL"
    if not condition:
        ok = False
    print(f"  [{status}] {name}")


# ── 1. Auth ──────────────────────────────────────────────

r = httpx.get(f"{BASE}/", follow_redirects=True, timeout=10)
check("GET / without auth returns 401", r.status_code == 401)

r = httpx.get(f"{BASE}/candidates", follow_redirects=True, timeout=10)
check("GET /candidates without auth returns 401", r.status_code == 401)

client = httpx.Client(base_url=BASE, auth=AUTH, follow_redirects=True, timeout=30)

r = client.get("/")
check("GET / with auth returns 200", r.status_code == 200)

# ── 2. Enhanced Dashboard ────────────────────────────────

check("Dashboard has Sources card", "Sources" in r.text)
check("Dashboard has Candidates card", "Candidates" in r.text)
check("Dashboard has Buy label card", ">Buy<" in r.text or "Buy" in r.text)
check("Dashboard has Review label card", "Review" in r.text)
check("Dashboard has Discard label card", "Discard" in r.text)
check("Dashboard has Export XLSX button", "XLSX" in r.text)
check("Dashboard has Export CSV button", "CSV" in r.text)
check("Dashboard has Niche Breakdown section", "Niche Breakdown" in r.text)
check("Dashboard has Top Scored section", "Top Scored" in r.text)

# ── 3. XLSX Export ────────────────────────────────────────

r = client.get("/export/xlsx")
check("XLSX export returns 200", r.status_code == 200)
ct = r.headers.get("content-type", "")
check("XLSX content-type is spreadsheet", "spreadsheet" in ct or "xlsx" in ct)
check("XLSX file not empty", len(r.content) > 100)

# Verify it starts with PK (ZIP) magic bytes
check("XLSX is valid ZIP (PK header)", r.content[:2] == b"PK")

# ── 4. CSV Export (19 columns) ────────────────────────────

r = client.get("/export/csv")
check("CSV export returns 200", r.status_code == 200)
lines = r.text.strip().split("\n")
check("CSV has header row", len(lines) >= 1)
headers = lines[0].split(",")
check("CSV has 19 columns", len(headers) == 19)
check("CSV has Domain column", "Domain" in lines[0])
check("CSV has Score column", "Score" in lines[0])
check("CSV has Label column", "Label" in lines[0])
check("CSV has Reason column", "Reason" in lines[0])
check("CSV has Language column", "Language" in lines[0])

# ── 5. Export with label filter ───────────────────────────

r = client.get("/export/csv?label=Buy")
check("CSV export with label=Buy works", r.status_code == 200)

r = client.get("/export/xlsx?label=Buy")
check("XLSX export with label=Buy works", r.status_code == 200)

# ── 6. Owner Notes ────────────────────────────────────────

# Find a candidate ID
r = client.get("/candidates")
check("Candidates page loads", r.status_code == 200)

match = re.search(r"/candidates/(\d+)", r.text)
if match:
    cid = match.group(1)

    # Detail page has notes form
    r = client.get(f"/candidates/{cid}")
    check("Detail page loads", r.status_code == 200)
    check("Detail page has Owner Notes section", "Owner Notes" in r.text)
    check("Detail page has Save Notes button", "Save Notes" in r.text)

    # Save notes
    r = client.post(f"/candidates/{cid}/notes", data={"owner_notes": "E2E test note"})
    check("Save notes returns redirect/200", r.status_code == 200)
    check("Saved note appears on page", "E2E test note" in r.text)
else:
    check("Found candidate ID for notes test", False)

# ── 7. Dashboard label clickable links ────────────────────

r = client.get("/")
check("Dashboard Buy card links to candidates", "label=Buy" in r.text)
check("Dashboard Review card links", "label=Review" in r.text)
check("Dashboard Discard card links", "label=Discard" in r.text)

# ── 8. All pages accessible with auth ────────────────────

r = client.get("/sources")
check("Sources page with auth OK", r.status_code == 200)

r = client.get("/sources/1")
check("Source detail with auth OK", r.status_code == 200)

r = client.get("/candidates?label=Review")
check("Candidates label filter with auth OK", r.status_code == 200)

r = client.get("/candidates?sort=score")
check("Candidates sort by score with auth OK", r.status_code == 200)

# ── Summary ───────────────────────────────────────────────

print()
if ok:
    print("ALL WEEK 4 TESTS PASSED")
else:
    print("SOME TESTS FAILED")
    sys.exit(1)
