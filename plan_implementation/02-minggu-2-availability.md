# Minggu 2 — Availability Check + Export

**Periode:** 16–22 Maret 2026  
**Goal:** Setiap domain kandidat punya status availability, bisa di-export CSV  
**Syarat Done yang dicakup:** #3  
**Prereq:** M1 selesai (crawl + tabel kandidat)


---


## Task List

### Day 1-2: WHOIS Engine

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 2.1 | Pindah WHOIS logic dari demo ke `app/services/whois_checker.py` | Service siap | 2 jam |
| 2.2 | WHOIS lookup: registrar, creation_date, expiration_date, name_servers | Data WHOIS | 2 jam |
| 2.3 | Throttling + cache: max 5 req/menit, cache hasil 24 jam di DB | Rate limit aman | 2 jam |
| 2.4 | Proxy support untuk WHOIS (via proxy rotator) | Bypass rate limit | 1 jam |

### Day 2-3: DNS + Status Tagging

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 2.5 | DNS resolution check (dnspython): resolve / no-resolve / timeout | DNS status | 2 jam |
| 2.6 | Status tagging logic — gabungkan WHOIS + DNS: | Label status | 2 jam |

**Status tagging rules:**

```
WHOIS: no record + DNS: no resolve     → "available"       🟢
WHOIS: expired                         → "expired"         🔥
WHOIS: expiring < 30 hari              → "expiring_soon"   ⚡
WHOIS: expiring < 90 hari              → "watchlist"       👀
WHOIS: registered + DNS: resolve       → "registered"      🔒
WHOIS: error                           → "check_failed"    ⚠️
```

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 2.7 | Update model `CandidateDomain` — tambah field availability | Schema updated | 1 jam |
| 2.8 | Background job: batch WHOIS check untuk kandidat baru | Auto-check | 2 jam |

### Day 3-4: Database Update + Dashboard v1

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 2.9 | Simpan semua WHOIS result ke DB (registrar, dates, status) | Data tersimpan | 1 jam |
| 2.10 | Update tabel kandidat — tambah kolom status + expiry | Kolom baru tampil | 1 jam |
| 2.11 | Warna status di tabel (hijau=available, merah=registered, dll) | Visual signal | 1 jam |
| 2.12 | Filter dropdown: All / Available / Watchlist / Registered | Filter aktif | 2 jam |
| 2.13 | Sort by: domain, status, expiry date | Sort aktif | 1 jam |

### Day 4-5: Export CSV

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 2.14 | Endpoint GET `/export/csv` — export data filtered ke CSV | File CSV | 2 jam |
| 2.15 | Tombol "Export CSV" di dashboard | Download 1-klik | 1 jam |
| 2.16 | Kolom export: domain, status, registrar, created, expires, days_left, source, niche | Data lengkap | 1 jam |

### Day 5-6: Halaman Source Detail

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 2.17 | Halaman detail per source: info source + list kandidat dari source itu | Page baru | 2 jam |
| 2.18 | Statistik per source: total crawled, available, watchlist, registered | Summary | 1 jam |
| 2.19 | Tombol "Re-crawl" di halaman source detail | Trigger ulang | 1 jam |

### Day 7: Buffer + Demo Prep

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 2.20 | Fix bugs, polish | Stabil | 2 jam |
| 2.21 | Update progress tracker | Updated | 30 menit |


---


## Demo M2 — Jumat 21 Maret

**Scenario:**
1. Buka dashboard → lihat kandidat dari M1
2. Status availability sudah terisi otomatis (available/registered/watchlist)
3. Filter: klik "Available" → hanya tampil domain yang bisa dibeli
4. Klik "Export CSV" → file terdownload
5. Buka file CSV → data lengkap

**Bukti selesai:**
- [ ] WHOIS check jalan untuk semua kandidat
- [ ] Status availability tampil di tabel (warna + label)
- [ ] Filter by status berfungsi
- [ ] Export CSV berfungsi dan data lengkap
- [ ] Halaman source detail berfungsi


---


## Risiko Minggu 2

| Risiko | Mitigasi |
|--------|----------|
| WHOIS rate limit dari provider | Throttle 5 req/mnt + cache 24 jam + proxy rotate |
| WHOIS data format tidak konsisten | Error handling per registrar, fallback ke "check_failed" |
| Batch job timeout | Chunk ke batch 10 domain, process sequential |
