# Minggu 3 — Historical Continuity + Scoring Engine

**Periode:** 23–29 Maret 2026  
**Goal:** Setiap domain punya continuity score + toxicity flags + label Buy/Review/Discard  
**Syarat Done yang dicakup:** #4  
**Prereq:** M2 selesai (availability status ada)


---


## Task List

### Day 1-2: Wayback Machine Integration

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 3.1 | Pindah Wayback logic dari demo ke `app/services/wayback.py` | Service siap | 2 jam |
| 3.2 | CDX API: ambil daftar snapshot per domain (collapse per bulan) | Snapshot list | 1 jam |
| 3.3 | Pilih 3–5 snapshot yang tersebar merata dari timeline | Selected snapshots | 1 jam |
| 3.4 | Fetch konten snapshot dari Wayback | Content retrieved | 2 jam |
| 3.5 | Extract visible text dari HTML (strip script/style/tags) | Clean text | 1 jam |
| 3.6 | Throttling + proxy support untuk Wayback requests | Rate limit aman | 1 jam |

### Day 2-3: Language Detection + Content Drift

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 3.7 | Deteksi bahasa per snapshot (langdetect) | Language per snapshot | 1 jam |
| 3.8 | Hitung language consistency (% bahasa dominan vs total) | Consistency score | 1 jam |
| 3.9 | Content drift: bandingkan ukuran + keyword overlap antar snapshot | Drift indicator | 2 jam |
| 3.10 | Tentukan bahasa dominan per domain | Dominant language | 30 menit |

### Day 3-4: Toxicity / Risk Flags

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 3.11 | Pindah toxicity logic dari demo ke `app/services/toxicity.py` | Service siap | 1 jam |
| 3.12 | Flag: parking page (keyword matching) | Flag detected | 1 jam |
| 3.13 | Flag: adult content (keyword list) | Flag detected | 30 menit |
| 3.14 | Flag: gambling (keyword list) | Flag detected | 30 menit |
| 3.15 | Flag: pharma spam (keyword list) | Flag detected | 30 menit |
| 3.16 | Flag: malware indicators (keyword list) | Flag detected | 30 menit |
| 3.17 | Flag: language mismatch (dominant lang ≠ niche target) | Flag detected | 1 jam |
| 3.18 | Flag: domain usia sangat muda (WHOIS creation < 1 tahun) | Flag detected | 30 menit |
| 3.19 | Simpan flags ke DB (array of flags per domain) | Data tersimpan | 1 jam |

### Day 4-5: Scoring Engine

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 3.20 | Buat `app/services/scoring.py` | Service siap | 1 jam |
| 3.21 | Komponen 1: Availability score (30%) | Skor 0-100 | 1 jam |

**Availability scoring:**
```
available      → 100
expired        → 90
expiring_soon  → 70
watchlist      → 50
registered     → 0
check_failed   → 30
```

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 3.22 | Komponen 2: Continuity score (40%) | Skor 0-100 | 2 jam |

**Continuity scoring:**
```
Snapshot quantity   : 5+ = 100, 3-4 = 70, 1-2 = 40, 0 = 0
Language consistency: (% dominant / total) × 100
Content drift       : low = 100, medium = 60, high = 30
Weighted average dari 3 sub-komponen
```

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 3.23 | Komponen 3: Cleanliness score (30%) | Skor 0-100 | 1 jam |

**Cleanliness scoring:**
```
No flags           → 100
Tiap ⚠️ flag       → -30
Ada 🔴 flag        → langsung 0 (auto-discard)
Minimum 0
```

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 3.24 | Total score = (Avail × 0.3) + (Cont × 0.4) + (Clean × 0.3) | Final score | 1 jam |
| 3.25 | Label mapping: ≥70 = Buy, 40-69 = Review, <40 atau 🔴 = Discard | Label | 30 menit |
| 3.26 | Generate "reason" text (1 kalimat explainable) | Alasan | 1 jam |
| 3.27 | Simpan score + breakdown + label + reason ke DB | Data tersimpan | 1 jam |

### Day 5-6: Dashboard v2 — Domain Card

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 3.28 | Domain card component: skor besar + breakdown bar + label warna | Card di browser | 3 jam |
| 3.29 | Badge flags pada domain card (⚠️ Parking, 🔴 Adult, dll) | Flags tampil | 1 jam |
| 3.30 | Reason text di bawah skor ("Available, 5yr history, clean") | Alasan tampil | 1 jam |
| 3.31 | Halaman detail domain: info lengkap (WHOIS + snapshot + flags + score breakdown) | Detail page | 3 jam |
| 3.32 | Timeline snapshots di halaman detail (tanggal + bahasa + size) | Timeline tampil | 1 jam |

### Day 7: Buffer + Demo Prep

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 3.33 | Fix bugs, polish scoring edge cases | Stabil | 2 jam |
| 3.34 | Update progress tracker | Updated | 30 menit |


---


## Demo M3 — Jumat 28 Maret

**Scenario:**
1. Buka dashboard → kandidat sudah punya skor
2. Lihat domain card: skor 85 🟢 Buy Candidate — "Available, 6yr English history, no flags"
3. Lihat domain card: skor 45 🟡 Review — "Watchlist, 2yr history, ⚠️ parking detected"
4. Lihat domain card: skor 12 🔴 Discard — "Registered, 🔴 adult content detected"
5. Klik domain → halaman detail → breakdown skor + timeline snapshot

**Bukti selesai:**
- [ ] Wayback snapshot diambil dan dianalisis
- [ ] Language detection berjalan per snapshot
- [ ] Toxicity flags terdeteksi dan tampil sebagai badge
- [ ] Scoring engine menghasilkan skor + label + reason
- [ ] Domain card menampilkan skor, breakdown, flags, reason
- [ ] Halaman detail domain menampilkan info lengkap


---


## Risiko Minggu 3

| Risiko | Mitigasi |
|--------|----------|
| Wayback CDX rate limit | Proxy rotate + throttle 1 req/detik + cache |
| Snapshot content kosong / unavailable | Tandai "insufficient data", skor partial |
| Toxicity false positive | Keyword list ketat, review manual tetap ada via label "Review" |
| Scoring edge cases | Test dengan data real dari M1/M2, adjust threshold |
