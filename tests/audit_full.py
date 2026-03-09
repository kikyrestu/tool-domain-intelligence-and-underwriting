"""
FULL AUDIT — Domain IQ Application
Menguji semua fitur end-to-end secara menyeluruh
"""
import httpx
import re
import time
import json
import sys

BASE = "http://127.0.0.1:8000"
AUTH = ("admin", "admin")
results = []
section = ""

def header(name):
    global section
    section = name
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")

def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append({"section": section, "test": name, "status": status, "detail": detail})
    icon = "✓" if condition else "✗"
    print(f"  [{icon}] {name}")
    if detail and not condition:
        print(f"      → {detail}")

# ════════════════════════════════════════════════════════════
header("1. AUTHENTICATION")
# ════════════════════════════════════════════════════════════

# No auth → 401
r = httpx.get(f"{BASE}/", timeout=10)
check("GET / tanpa auth → 401", r.status_code == 401, f"got {r.status_code}")

r = httpx.get(f"{BASE}/candidates", timeout=10)
check("GET /candidates tanpa auth → 401", r.status_code == 401, f"got {r.status_code}")

r = httpx.get(f"{BASE}/sources", timeout=10)
check("GET /sources tanpa auth → 401", r.status_code == 401, f"got {r.status_code}")

r = httpx.get(f"{BASE}/export/csv", timeout=10)
check("GET /export/csv tanpa auth → 401", r.status_code == 401, f"got {r.status_code}")

# Wrong auth → 401
r = httpx.get(f"{BASE}/", auth=("wrong", "wrong"), timeout=10)
check("Auth salah → 401", r.status_code == 401, f"got {r.status_code}")

# Correct auth → 200
client = httpx.Client(base_url=BASE, auth=AUTH, follow_redirects=True, timeout=30)
r = client.get("/")
check("Auth benar → 200", r.status_code == 200, f"got {r.status_code}")

# ════════════════════════════════════════════════════════════
header("2. DASHBOARD")
# ════════════════════════════════════════════════════════════

r = client.get("/")
check("Dashboard load", r.status_code == 200)
check("Ada card Sources", "Sources" in r.text)
check("Ada card Candidates", "Candidates" in r.text)
check("Ada card Dead Links", "Dead Links" in r.text or "Dead" in r.text)
check("Ada label Buy", "Buy" in r.text)
check("Ada label Review", "Review" in r.text)
check("Ada label Discard", "Discard" in r.text)
check("Ada link ke label filter", "label=Buy" in r.text)
check("Ada Export XLSX button", "XLSX" in r.text)
check("Ada Export CSV button", "CSV" in r.text)
check("Ada Niche Breakdown", "Niche Breakdown" in r.text)
check("Ada Top Scored", "Top Scored" in r.text)
check("Ada Recent Crawl Jobs", "Recent Crawl" in r.text or "Crawl" in r.text)

# ════════════════════════════════════════════════════════════
header("3. SOURCES CRUD")
# ════════════════════════════════════════════════════════════

r = client.get("/sources")
check("Sources list load", r.status_code == 200)
check("Ada tombol Add Source", "Add Source" in r.text)

# Add source
r = client.get("/sources/add")
check("Form add source load", r.status_code == 200)

r = client.post("/sources", data={
    "url": "https://httpbin.org/html",
    "niche": "Technology",
    "notes": "Audit test source"
})
check("Tambah source berhasil", r.status_code == 200, f"got {r.status_code}")

# Get source ID
r = client.get("/sources")
source_ids = re.findall(r'/sources/(\d+)', r.text)
check("Source tersimpan di database", len(source_ids) > 0, f"found {len(source_ids)} sources")

if source_ids:
    sid = source_ids[-1]  # use latest
    r = client.get(f"/sources/{sid}")
    check(f"Source detail /{sid} load", r.status_code == 200)
    check("Ada tombol Run Crawl", "Run Crawl" in r.text or "Crawl" in r.text)
    check("Ada tombol Check WHOIS", "WHOIS" in r.text)
    check("Ada tombol Wayback Audit", "Wayback" in r.text)
    check("Ada tombol Score All", "Score All" in r.text or "Score" in r.text)

# ════════════════════════════════════════════════════════════
header("4. CRAWL PIPELINE")
# ════════════════════════════════════════════════════════════

# Use first source
r = client.get("/sources")
source_ids = re.findall(r'/sources/(\d+)', r.text)
sid = source_ids[0] if source_ids else "1"

# Trigger crawl
r = client.post(f"/crawl/{sid}")
check("Trigger crawl accepted", r.status_code == 200, f"got {r.status_code}")
print("  ⏳ Menunggu crawl selesai (15s)...")
time.sleep(15)

# Check candidates exist
r = client.get("/candidates")
check("Candidates page load setelah crawl", r.status_code == 200)
candidate_ids = re.findall(r'/candidates/(\d+)', r.text)
candidate_count = len(set(candidate_ids))
check(f"Ada kandidat domain ({candidate_count} found)", candidate_count > 0, f"found {candidate_count}")

# ════════════════════════════════════════════════════════════
header("5. WHOIS CHECK")
# ════════════════════════════════════════════════════════════

r = client.post(f"/whois/{sid}")
check("Trigger WHOIS per source accepted", r.status_code == 200)
print("  ⏳ Menunggu WHOIS selesai (20s)...")
time.sleep(20)

r = client.get("/candidates")
has_avail = "available" in r.text.lower() or "registered" in r.text.lower() or "expired" in r.text.lower() or "check_failed" in r.text.lower()
check("Availability status muncul di shortlist", has_avail)

# ════════════════════════════════════════════════════════════
header("6. WAYBACK AUDIT")
# ════════════════════════════════════════════════════════════

r = client.post(f"/wayback/{sid}")
check("Trigger Wayback per source accepted", r.status_code == 200)
print("  ⏳ Menunggu Wayback selesai (25s)...")
time.sleep(25)

r = client.get("/candidates")
has_snapshots = "Snapshots" in r.text or "snapshot" in r.text.lower()
check("Kolom Snapshots muncul di shortlist", has_snapshots)

# ════════════════════════════════════════════════════════════
header("7. SCORING")
# ════════════════════════════════════════════════════════════

r = client.post(f"/score/{sid}")
check("Trigger Score per source accepted", r.status_code == 200)
print("  ⏳ Menunggu scoring selesai (10s)...")
time.sleep(10)

r = client.get("/candidates")
has_score = "Score" in r.text
has_label = "Buy" in r.text or "Review" in r.text or "Discard" in r.text
check("Kolom Score muncul", has_score)
check("Label Buy/Review/Discard muncul", has_label)

# ════════════════════════════════════════════════════════════
header("8. DOMAIN DETAIL PAGE")
# ════════════════════════════════════════════════════════════

r = client.get("/candidates")
cids = list(set(re.findall(r'/candidates/(\d+)', r.text)))
if cids:
    cid = cids[0]
    r = client.get(f"/candidates/{cid}")
    check("Domain detail page load", r.status_code == 200)
    check("Ada Score Breakdown", "Score Breakdown" in r.text or "Breakdown" in r.text)
    check("Ada Availability section", "Availability" in r.text)
    check("Ada Historical Continuity", "Historical" in r.text or "Continuity" in r.text)
    check("Ada Owner Notes form", "Owner Notes" in r.text)
    check("Ada Save Notes button", "Save Notes" in r.text)
    check("Ada Meta section", "Meta" in r.text or "Discovered" in r.text)
    
    # Check score circle exists
    has_circle = "score-circle" in r.text or "score_total" in r.text or re.search(r'\d+\.\d+', r.text)
    check("Ada skor numerik", has_circle)
else:
    check("Found candidate for detail test", False, "No candidates found")

# ════════════════════════════════════════════════════════════
header("9. OWNER NOTES")
# ════════════════════════════════════════════════════════════

if cids:
    cid = cids[0]
    test_note = f"Audit note {int(time.time())}"
    r = client.post(f"/candidates/{cid}/notes", data={"owner_notes": test_note})
    check("Save notes → redirect/200", r.status_code == 200)
    check("Note tersimpan & tampil", test_note in r.text, f"looking for '{test_note}'")
else:
    check("Notes test skipped (no candidates)", False)

# ════════════════════════════════════════════════════════════
header("10. FILTERS & SEARCH")
# ════════════════════════════════════════════════════════════

r = client.get("/candidates?label=Buy")
check("Filter label=Buy works", r.status_code == 200)

r = client.get("/candidates?label=Review")
check("Filter label=Review works", r.status_code == 200)

r = client.get("/candidates?label=Discard")
check("Filter label=Discard works", r.status_code == 200)

r = client.get("/candidates?status=dead")
check("Filter status=dead works", r.status_code == 200)

r = client.get("/candidates?availability=registered")
check("Filter availability=registered works", r.status_code == 200)

r = client.get("/candidates?sort=score")
check("Sort by score works", r.status_code == 200)

r = client.get("/candidates?sort=domain")
check("Sort by domain works", r.status_code == 200)

r = client.get("/candidates?q=test")
check("Search query works", r.status_code == 200)

# ════════════════════════════════════════════════════════════
header("11. CSV EXPORT")
# ════════════════════════════════════════════════════════════

r = client.get("/export/csv")
check("CSV export → 200", r.status_code == 200)
ct = r.headers.get("content-type", "")
check("Content-Type text/csv", "csv" in ct or "text" in ct)

lines = r.text.strip().split("\n")
headers_csv = lines[0].split(",") if lines else []
check(f"CSV header row ({len(headers_csv)} columns)", len(headers_csv) == 19, f"got {len(headers_csv)}")
check("CSV has Domain col", "Domain" in lines[0])
check("CSV has Score col", "Score" in lines[0])
check("CSV has Label col", "Label" in lines[0])
check("CSV has Reason col", "Reason" in lines[0])
check("CSV has Language col", "Language" in lines[0])
check("CSV has Notes col", "Notes" in lines[0])

data_rows = len(lines) - 1
check(f"CSV has data rows ({data_rows})", data_rows > 0)

# Filtered export
r = client.get("/export/csv?label=Buy")
check("CSV export with label=Buy", r.status_code == 200)

r = client.get("/export/csv?label=Review")
check("CSV export with label=Review", r.status_code == 200)

# ════════════════════════════════════════════════════════════
header("12. XLSX EXPORT")
# ════════════════════════════════════════════════════════════

r = client.get("/export/xlsx")
check("XLSX export → 200", r.status_code == 200)
ct = r.headers.get("content-type", "")
check("Content-Type spreadsheet", "spreadsheet" in ct or "xlsx" in ct)
check("File > 100 bytes", len(r.content) > 100, f"got {len(r.content)} bytes")
check("Valid ZIP (PK header)", r.content[:2] == b"PK")

# Check content-disposition
cd = r.headers.get("content-disposition", "")
check("Has filename in header", "domain_iq" in cd.lower() or "filename" in cd.lower(), cd)

# Filtered XLSX
r = client.get("/export/xlsx?label=Buy")
check("XLSX export with label=Buy", r.status_code == 200)

# ════════════════════════════════════════════════════════════
header("13. BULK OPERATIONS")
# ════════════════════════════════════════════════════════════

r = client.post("/whois-all")
check("WHOIS All trigger accepted", r.status_code == 200)

r = client.post("/wayback-all")
check("Wayback All trigger accepted", r.status_code == 200)

r = client.post("/score-all")
check("Score All trigger accepted", r.status_code == 200)

# ════════════════════════════════════════════════════════════
header("14. EDGE CASES")
# ════════════════════════════════════════════════════════════

r = client.get("/candidates/99999")
check("Non-existent candidate → redirect ke list", r.status_code == 200, f"got {r.status_code}")

r = client.get("/sources/99999")
check("Non-existent source → redirect ke list", r.status_code == 200, f"got {r.status_code}")

r = client.get("/candidates?label=InvalidLabel")
check("Invalid label filter → no crash", r.status_code == 200)

r = client.get("/candidates?page=999")
check("Page beyond range → no crash", r.status_code == 200)

# ══════════════════════════════════════════════════
#  SUMMARY
# ══════════════════════════════════════════════════

print(f"\n{'='*60}")
print(f"  AUDIT SUMMARY")
print(f"{'='*60}")

passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] == "FAIL")
total = len(results)

sections = {}
for r in results:
    s = r["section"]
    if s not in sections:
        sections[s] = {"pass": 0, "fail": 0}
    if r["status"] == "PASS":
        sections[s]["pass"] += 1
    else:
        sections[s]["fail"] += 1

print()
for s, counts in sections.items():
    total_s = counts["pass"] + counts["fail"]
    icon = "✓" if counts["fail"] == 0 else "✗"
    print(f"  [{icon}] {s}: {counts['pass']}/{total_s}")

print(f"\n  TOTAL: {passed}/{total} PASSED, {failed} FAILED")

if failed > 0:
    print(f"\n  FAILED TESTS:")
    for r in results:
        if r["status"] == "FAIL":
            print(f"    ✗ [{r['section']}] {r['test']}")
            if r["detail"]:
                print(f"      → {r['detail']}")

print()
if failed == 0:
    print("  ★ SEMUA FITUR BERJALAN DENGAN BAIK ★")
else:
    print(f"  ⚠ ADA {failed} TEST YANG GAGAL")

sys.exit(0 if failed == 0 else 1)
