"""E2E test for Week 3: Wayback + Toxicity + Scoring + Domain Detail"""
import httpx
import time
import sys

BASE = "http://127.0.0.1:8000"
client = httpx.Client(base_url=BASE, follow_redirects=True, timeout=30)
ok = True

def check(name, condition):
    global ok
    status = "PASS" if condition else "FAIL"
    if not condition:
        ok = False
    print(f"  [{status}] {name}")


# 1. Dashboard
r = client.get("/")
check("Dashboard loads", r.status_code == 200)

# 2. Candidates page with new columns
r = client.get("/candidates")
check("Candidates page loads", r.status_code == 200)
check("Has Score column", "Score" in r.text)
check("Has Label column", "Label" in r.text)
check("Has Wayback All button", "Wayback All" in r.text)
check("Has Score All button", "Score All" in r.text)

# 3. Trigger Score (no Wayback needed for basic scoring)
r = client.post("/score-all")
check("Score All trigger accepted", r.status_code == 200)
print("  Waiting 5s for scoring...")
time.sleep(5)

# 4. Check scored candidates
r = client.get("/candidates")
has_label = "Buy" in r.text or "Review" in r.text or "Discard" in r.text
check("Labels appear after scoring", has_label)

# 5. Label filter
r = client.get("/candidates?label=Review")
check("Label filter works", r.status_code == 200)

r = client.get("/candidates?label=Discard")
check("Label filter Discard works", r.status_code == 200)

# 6. Sort by score
r = client.get("/candidates?sort=score")
check("Sort by score works", r.status_code == 200)

# 7. Domain detail page
# Get the first candidate ID from the page
import re
match = re.search(r'/candidates/(\d+)', r.text)
if match:
    cid = match.group(1)
    r = client.get(f"/candidates/{cid}")
    check("Domain detail page loads", r.status_code == 200)
    check("Has Score Breakdown", "Score Breakdown" in r.text)
    check("Has Availability section", "Availability" in r.text)
    check("Has Historical Continuity", "Historical Continuity" in r.text)
    check("Has Meta section", "Meta" in r.text)
else:
    check("Found candidate ID for detail", False)

# 8. Source detail has new buttons
r = client.get("/sources/1")
check("Source detail loads", r.status_code == 200)
check("Has Wayback Audit button", "Wayback Audit" in r.text)
check("Has Score All button on source", "Score All" in r.text)

# 9. New routes exist
r = client.post("/wayback-all")
check("Wayback All trigger accepted", r.status_code == 200)

r = client.post("/score/1")
check("Score per source trigger", r.status_code == 200)

r = client.post("/wayback/1")
check("Wayback per source trigger", r.status_code == 200)

# 10. Summary cards
r = client.get("/candidates")
check("Has Buy count card", "Buy" in r.text)
check("Has Review count card", "Review" in r.text)
check("Has Discard count card", "Discard" in r.text)

print()
if ok:
    print("ALL WEEK 3 TESTS PASSED")
else:
    print("SOME TESTS FAILED")
    sys.exit(1)
