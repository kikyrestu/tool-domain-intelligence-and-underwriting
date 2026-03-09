"""
Demo Historical Continuity Audit via Wayback Machine CDX API
Ambil snapshot historis, deteksi bahasa, hitung continuity score, flag toxicity.

Jalankan: python demo/demo_wayback.py domain1.com domain2.net
"""

import asyncio
import sys
import time
import re
from pathlib import Path

import httpx
from langdetect import detect, LangDetectException

sys.path.insert(0, str(Path(__file__).parent))
from proxy_rotator import ProxyRotator


# ============================================================
# KONFIGURASI
# ============================================================

WAYBACK_CDX_URL = "https://web.archive.org/cdx/search/cdx"
WAYBACK_WEB_URL = "https://web.archive.org/web"
TIMEOUT = 30
MAX_SNAPSHOTS = 5  # Ambil 3-5 titik waktu

# Toxicity keyword patterns
TOXICITY_PATTERNS = {
    "parking": [
        r"buy this domain", r"domain for sale", r"this domain is for sale",
        r"domain parking", r"parked domain", r"is available for purchase",
        r"domain may be for sale", r"hugedomains", r"sedoparking", r"godaddy",
    ],
    "adult": [
        r"porn", r"xxx", r"adult content", r"18\+", r"sex",
    ],
    "gambling": [
        r"casino", r"poker", r"slot machine", r"betting", r"gambling",
        r"roulette", r"blackjack",
    ],
    "pharma": [
        r"viagra", r"cialis", r"pharmacy", r"buy pills", r"cheap meds",
        r"prescription", r"erectile",
    ],
    "malware": [
        r"download free", r"crack", r"keygen", r"warez",
        r"free download", r"serial key",
    ],
}


# ============================================================
# WAYBACK CDX API
# ============================================================

async def get_snapshots(domain: str, client: httpx.AsyncClient) -> list[dict]:
    """Ambil daftar snapshot dari Wayback CDX API."""
    params = {
        "url": domain,
        "output": "json",
        "fl": "timestamp,statuscode,mimetype,original",
        "filter": "statuscode:200",
        "collapse": "timestamp:6",  # 1 per bulan
        "limit": 50,
    }

    try:
        response = await client.get(
            WAYBACK_CDX_URL, params=params, timeout=TIMEOUT, follow_redirects=True
        )
        if response.status_code != 200:
            return []

        data = response.json()
        if not data or len(data) < 2:
            return []

        # Baris pertama adalah header
        headers = data[0]
        snapshots = []
        for row in data[1:]:
            snap = dict(zip(headers, row))
            snapshots.append(snap)

        return snapshots

    except Exception as e:
        print(f"      ⚠️ CDX API error for {domain}: {e}")
        return []


def select_snapshots(snapshots: list[dict], count: int = MAX_SNAPSHOTS) -> list[dict]:
    """Pilih snapshot yang tersebar merata dari timeline."""
    if len(snapshots) <= count:
        return snapshots

    # Pilih yang tersebar: pertama, terakhir, dan di antara
    indices = [0]
    step = (len(snapshots) - 1) / (count - 1)
    for i in range(1, count - 1):
        indices.append(round(step * i))
    indices.append(len(snapshots) - 1)

    return [snapshots[i] for i in indices]


# ============================================================
# CONTENT FETCH & ANALYSIS
# ============================================================

async def fetch_snapshot_content(
    domain: str, timestamp: str, client: httpx.AsyncClient
) -> str | None:
    """Fetch konten snapshot dari Wayback Machine."""
    url = f"{WAYBACK_WEB_URL}/{timestamp}id_/{domain}"
    try:
        response = await client.get(url, timeout=TIMEOUT, follow_redirects=True)
        if response.status_code == 200:
            return response.text
    except Exception:
        pass
    return None


def extract_text_from_html(html: str) -> str:
    """Extract visible text dari HTML secara sederhana."""
    # Remove script & style
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Clean whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def detect_language(text: str) -> str:
    """Deteksi bahasa dari text."""
    if not text or len(text) < 50:
        return "unknown"
    try:
        return detect(text[:5000])  # Limit untuk speed
    except LangDetectException:
        return "unknown"


def check_toxicity(text: str) -> list[dict]:
    """Scan text untuk toxicity flags."""
    flags = []
    text_lower = text.lower()

    for category, patterns in TOXICITY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                flags.append({
                    "category": category,
                    "matched": pattern,
                    "severity": "high" if category in ("adult", "gambling", "pharma", "malware") else "medium",
                })
                break  # 1 match per category cukup

    return flags


# ============================================================
# CONTINUITY SCORING
# ============================================================

def calculate_continuity_score(analysis: dict) -> dict:
    """Hitung continuity score dari analysis results."""
    score_details = {
        "snapshot_score": 0,
        "language_score": 0,
        "toxicity_score": 100,
        "total_score": 0,
        "label": "Discard",
        "reasons": [],
    }

    snapshots = analysis.get("snapshots_analyzed", [])
    if not snapshots:
        score_details["reasons"].append("No snapshots available")
        return score_details

    # 1. Snapshot quantity score (0-100)
    count = len(snapshots)
    if count >= 5:
        score_details["snapshot_score"] = 100
    elif count >= 3:
        score_details["snapshot_score"] = 70
    elif count >= 1:
        score_details["snapshot_score"] = 40
    else:
        score_details["snapshot_score"] = 0

    # 2. Language consistency score (0-100)
    languages = [s.get("language", "unknown") for s in snapshots if s.get("language") != "unknown"]
    if languages:
        most_common = max(set(languages), key=languages.count)
        consistency = languages.count(most_common) / len(languages)
        score_details["language_score"] = round(consistency * 100)
        if consistency < 0.5:
            score_details["reasons"].append(f"Language inconsistent ({len(set(languages))} different languages detected)")
    else:
        score_details["language_score"] = 50  # Unknown = neutral
        score_details["reasons"].append("Could not determine language")

    # 3. Toxicity score (start at 100, reduce per flag)
    all_flags = []
    for s in snapshots:
        all_flags.extend(s.get("toxicity_flags", []))

    unique_categories = set(f["category"] for f in all_flags)
    for cat in unique_categories:
        severity = next(f["severity"] for f in all_flags if f["category"] == cat)
        if severity == "high":
            score_details["toxicity_score"] = 0  # Auto-kill
            score_details["reasons"].append(f"🔴 Toxic: {cat} content detected")
        else:
            score_details["toxicity_score"] -= 30
            score_details["reasons"].append(f"⚠️ Flag: {cat} detected")

    score_details["toxicity_score"] = max(0, score_details["toxicity_score"])

    # Total weighted score
    total = (
        score_details["snapshot_score"] * 0.3
        + score_details["language_score"] * 0.3
        + score_details["toxicity_score"] * 0.4
    )
    score_details["total_score"] = round(total)

    # Label
    if score_details["toxicity_score"] == 0:
        score_details["label"] = "Auto-Discard"
    elif total >= 70:
        score_details["label"] = "Buy Candidate"
        score_details["reasons"].append("Good continuity, clean history")
    elif total >= 40:
        score_details["label"] = "Manual Review"
    else:
        score_details["label"] = "Discard"

    return score_details


# ============================================================
# MAIN AUDIT
# ============================================================

async def audit_domain(domain: str, client: httpx.AsyncClient) -> dict:
    """Full historical audit untuk satu domain."""
    print(f"\n   {'─'*60}")
    print(f"   🔍 Auditing: {domain}")

    result = {
        "domain": domain,
        "total_snapshots": 0,
        "first_seen": None,
        "last_seen": None,
        "years_active": 0,
        "dominant_language": None,
        "snapshots_analyzed": [],
        "toxicity_flags": [],
        "continuity_score": {},
    }

    # Step 1: Get snapshot list
    print(f"      📡 Fetching snapshot list from Wayback CDX...")
    all_snapshots = await get_snapshots(domain, client)
    result["total_snapshots"] = len(all_snapshots)

    if not all_snapshots:
        print(f"      ❌ No snapshots found")
        result["continuity_score"] = calculate_continuity_score(result)
        return result

    # Timeline info
    first_ts = all_snapshots[0]["timestamp"]
    last_ts = all_snapshots[-1]["timestamp"]
    result["first_seen"] = f"{first_ts[:4]}-{first_ts[4:6]}-{first_ts[6:8]}"
    result["last_seen"] = f"{last_ts[:4]}-{last_ts[4:6]}-{last_ts[6:8]}"
    result["years_active"] = int(last_ts[:4]) - int(first_ts[:4])

    print(f"      📊 Found {len(all_snapshots)} snapshots ({result['first_seen']} → {result['last_seen']})")
    print(f"      📅 Active ~{result['years_active']} years")

    # Step 2: Select & analyze snapshots
    selected = select_snapshots(all_snapshots, MAX_SNAPSHOTS)
    print(f"      🎯 Analyzing {len(selected)} key snapshots...")

    for snap in selected:
        ts = snap["timestamp"]
        ts_display = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"

        content = await fetch_snapshot_content(domain, ts, client)
        snap_result = {
            "timestamp": ts_display,
            "language": "unknown",
            "toxicity_flags": [],
            "content_length": 0,
        }

        if content:
            text = extract_text_from_html(content)
            snap_result["content_length"] = len(text)

            # Language detection
            lang = detect_language(text)
            snap_result["language"] = lang

            # Toxicity scan
            flags = check_toxicity(text)
            snap_result["toxicity_flags"] = flags

            flag_str = ""
            if flags:
                flag_str = " | Flags: " + ", ".join(f["category"] for f in flags)
                result["toxicity_flags"].extend(flags)

            print(f"         {ts_display}: lang={lang}, size={len(text):,} chars{flag_str}")
        else:
            print(f"         {ts_display}: ❌ content unavailable")

        result["snapshots_analyzed"].append(snap_result)
        await asyncio.sleep(1)  # Respectful delay

    # Dominant language
    languages = [s["language"] for s in result["snapshots_analyzed"] if s["language"] != "unknown"]
    if languages:
        result["dominant_language"] = max(set(languages), key=languages.count)

    # Step 3: Calculate score
    result["continuity_score"] = calculate_continuity_score(result)

    return result


# ============================================================
# DISPLAY
# ============================================================

LABEL_ICONS = {
    "Buy Candidate": "🟢",
    "Manual Review": "🟡",
    "Discard": "🔴",
    "Auto-Discard": "🔴",
}


def display_results(results: list[dict]):
    """Tampilkan hasil audit."""
    print(f"\n{'='*70}")
    print(f"📜 HISTORICAL CONTINUITY AUDIT — RESULTS")
    print(f"{'='*70}")

    buy = [r for r in results if r["continuity_score"].get("label") == "Buy Candidate"]
    review = [r for r in results if r["continuity_score"].get("label") == "Manual Review"]
    discard = [r for r in results if r["continuity_score"].get("label") in ("Discard", "Auto-Discard")]

    print(f"\n   🟢 Buy Candidate  : {len(buy)}")
    print(f"   🟡 Manual Review  : {len(review)}")
    print(f"   🔴 Discard        : {len(discard)}")

    for r in results:
        score = r["continuity_score"]
        icon = LABEL_ICONS.get(score.get("label", ""), "❓")

        print(f"\n   {'─'*60}")
        print(f"   {icon} {r['domain']}  →  {score.get('label', '?')}  (Score: {score.get('total_score', 0)}/100)")
        print(f"      Snapshots      : {r['total_snapshots']} total, {len(r['snapshots_analyzed'])} analyzed")
        if r["first_seen"]:
            print(f"      Timeline       : {r['first_seen']} → {r['last_seen']} (~{r['years_active']} years)")
        print(f"      Language       : {r.get('dominant_language', 'unknown')}")
        print(f"      Score breakdown:")
        print(f"         Snapshot qty : {score.get('snapshot_score', 0)}/100")
        print(f"         Language     : {score.get('language_score', 0)}/100")
        print(f"         Cleanliness  : {score.get('toxicity_score', 0)}/100")
        if score.get("reasons"):
            print(f"      Reasons:")
            for reason in score["reasons"]:
                print(f"         • {reason}")

        # Toxicity flags
        if r["toxicity_flags"]:
            unique_flags = set(f["category"] for f in r["toxicity_flags"])
            print(f"      ⚠️  Toxicity flags: {', '.join(unique_flags)}")


# ============================================================
# MAIN
# ============================================================

async def main(domains: list[str]):
    proxy_file = Path(__file__).parent.parent / "proxies.txt"
    rotator = ProxyRotator(str(proxy_file))

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    print(f"\n{'='*70}")
    print(f"📜 HISTORICAL CONTINUITY AUDIT — {len(domains)} domains")
    print(f"{'='*70}")
    print(f"   Using Wayback Machine CDX API")
    print(f"   Max {MAX_SNAPSHOTS} snapshots per domain")
    print(f"   Checking: language, toxicity, content drift")

    results = []

    # Coba proxy dulu, fallback direct
    for proxy in [rotator.get_random(), None]:
        try:
            async with httpx.AsyncClient(headers=headers, proxy=proxy) as client:
                # Test koneksi ke Wayback
                test = await client.get(WAYBACK_CDX_URL, params={"url": "example.com", "output": "json", "limit": 1}, timeout=15)
                if test.status_code == 200:
                    label = "proxy" if proxy else "direct"
                    print(f"   ✅ Connection OK ({label})\n")
                    for domain in domains:
                        r = await audit_domain(domain, client)
                        results.append(r)
                    break
        except Exception as e:
            if proxy:
                print(f"   ⚠️ Proxy failed, trying direct...")
                continue
            else:
                print(f"   ❌ Connection failed: {e}")
                return

    display_results(results)
    print(f"\n✅ Historical audit selesai!")
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python demo/demo_wayback.py domain1.com domain2.net ...")
        sys.exit(1)

    domains = sys.argv[1:]
    asyncio.run(main(domains))
