# Domain IQ — Panduan Maintenance

Dokumen ini mapping setiap fitur/flow ke file yang perlu diedit.
Kalau ada update, cari fitur di bawah → edit file yang tertera.

---

## Struktur Project

```
app/
├── main.py              ← Entry point, middleware, router registration
├── config.py            ← Semua environment variables & default values
├── database.py          ← Database connection & session factory
├── auth.py              ← HTTP Basic Auth middleware
│
├── models/
│   ├── source.py        ← Tabel sources
│   ├── crawl_job.py     ← Tabel crawl_jobs
│   └── candidate.py     ← Tabel candidate_domains (kolom terbanyak)
│
├── services/            ← LOGIC UTAMA (modular, 1 file = 1 concern)
│   ├── crawl_service.py     ← Crawl & extract domain dari halaman
│   ├── whois_service.py     ← RDAP lookup & availability check
│   ├── wayback_service.py   ← Wayback Machine API & content analysis
│   ├── toxicity_service.py  ← Keyword scanner & risk flags
│   ├── scoring_service.py   ← Scoring engine & label assignment
│   ├── export_service.py    ← CSV & XLSX generation
│   └── proxy_service.py     ← Proxy rotation
│
├── routes/              ← HTTP ENDPOINTS (tipis, delegate ke services)
│   ├── dashboard.py     ← GET / — stats & overview
│   ├── sources.py       ← CRUD sources
│   ├── candidates.py    ← Shortlist, detail, notes
│   ├── crawl.py         ← Trigger crawl/whois/wayback/score
│   └── export.py        ← Download CSV/XLSX
│
└── templates/           ← HTML (Jinja2 + Tailwind + HTMX)
    ├── base.html        ← Layout, navbar, flash banner
    ├── dashboard.html   ← Dashboard page
    ├── sources/         ← Source list, detail, form
    └── candidates/      ← Shortlist, detail page
```

---

## Flow → File Mapping

### 1. Crawl (menemukan domain dari source page)

| Mau update apa? | Edit file |
|-----------------|-----------|
| Cara extract link dari HTML | `app/services/crawl_service.py` → `run_crawl()` |
| Blacklist domain (google, youtube, dll) | `app/services/crawl_service.py` → `DOMAIN_BLACKLIST` |
| TLD yang diizinkan | `app/services/crawl_service.py` → `ALLOWED_TLDS` |
| Delay antar request | `app/config.py` → `CRAWL_DELAY_SECONDS` |
| Maksimum kandidat per crawl | `app/config.py` → `MAX_CANDIDATES_PER_CRAWL` |
| Tombol trigger di UI | `app/templates/sources/detail.html` |

### 2. RDAP & Availability Check

| Mau update apa? | Edit file |
|-----------------|-----------|
| Logic penentuan status (available/expired/dll) | `app/services/whois_service.py` → `_rdap_lookup()` |
| Delay antar RDAP query | `app/config.py` → `RDAP_DELAY_SECONDS` |

### 3. Wayback Machine Audit

| Mau update apa? | Edit file |
|-----------------|-----------|
| Jumlah sampel snapshot | `app/config.py` → `WAYBACK_SAMPLE_SIZE` |
| Logic content drift detection | `app/services/wayback_service.py` → `_detect_drift()` |
| Language detection | `app/services/wayback_service.py` → `_detect_language()` |
| Delay antar request | `app/config.py` → `WAYBACK_DELAY_SECONDS` |

### 4. Toxicity Scanner

| Mau update apa? | Edit file |
|-----------------|-----------|
| Tambah/hapus keyword | `app/services/toxicity_service.py` → `TOXICITY_PATTERNS` |
| Tambah kategori baru | `app/services/toxicity_service.py` → tambah key di `TOXICITY_PATTERNS` + `SEVERITY` |
| Ubah severity (high/medium) | `app/services/toxicity_service.py` → `SEVERITY` dict |
| Penalty per severity di skor | `app/services/scoring_service.py` → `_score_cleanliness()` |

### 5. Scoring & Label

| Mau update apa? | Edit file |
|-----------------|-----------|
| Bobot komponen (availability/continuity/cleanliness) | `app/services/scoring_service.py` → `calculate_score()` (0.3/0.4/0.3) |
| Logic label (Available/Watchlist/Uncertain/Discard) | `app/services/scoring_service.py` → `_determine_label()` |
| Skor per availability status | `app/services/scoring_service.py` → `AVAILABILITY_SCORES` dict |
| Warna label di UI | Cari `Available.*green`, `Watchlist.*blue`, `Uncertain.*yellow`, `Discard.*red` di templates |
| Warna label di XLSX | `app/services/export_service.py` → `_LABEL_FILLS` dict |
| Reason text | `app/services/scoring_service.py` → bagian `# Build reason` |

### 6. Dashboard

| Mau update apa? | Edit file |
|-----------------|-----------|
| Cards/stats yang ditampilkan | `app/routes/dashboard.py` + `app/templates/dashboard.html` |
| Top scored table | `app/templates/dashboard.html` → section "Top Scored" |
| Niche breakdown | `app/routes/dashboard.py` → `niche_stats` query |

### 7. Export (CSV/XLSX)

| Mau update apa? | Edit file |
|-----------------|-----------|
| Kolom yang di-export | `app/services/export_service.py` → `EXPORT_COLUMNS` list |
| Format XLSX (warna, font, freeze) | `app/services/export_service.py` → `generate_xlsx()` |
| Filter export | `app/routes/export.py` |
| Nama file download | `app/routes/export.py` → `Content-Disposition` header |

### 8. Auth

| Mau update apa? | Edit file |
|-----------------|-----------|
| Username & password | `.env` → `AUTH_USERNAME`, `AUTH_PASSWORD` |
| Path yang di-skip auth | `app/auth.py` → `SKIP_PATHS` |
| Ganti auth method (misal token) | `app/auth.py` → `BasicAuthMiddleware` class |

### 9. Proxy

| Mau update apa? | Edit file |
|-----------------|-----------|
| Daftar proxy | `proxies.txt` (1 proxy per baris) |
| Enable/disable proxy | `.env` → `PROXY_ENABLED` |
| Rotation logic | `app/services/proxy_service.py` |

### 10. Database / Model

| Mau update apa? | Edit file |
|-----------------|-----------|
| Tambah kolom di candidate | `app/models/candidate.py` → tambah field, lalu restart server (auto create_all) |
| Tambah kolom di source | `app/models/source.py` |
| Connection string | `.env` → `DATABASE_URL` |
| Niche dropdown options | `app/routes/sources.py` → `NICHES` list |

---

## Checklist Update Fitur

Kalau mau update salah satu flow, ikuti langkah ini:

1. **Cari flow** di tabel di atas → tahu file mana yang perlu diedit
2. **Edit service** (logic) di `app/services/`
3. **Edit model** (kalau perlu kolom baru) di `app/models/`
4. **Edit route** (kalau perlu endpoint baru) di `app/routes/`
5. **Edit template** (kalau perlu UI update) di `app/templates/`
6. **Restart server** — kalau pakai `--reload`, otomatis
7. **Jalankan scoring ulang** — kalau ubah scoring logic, trigger Score All

### Contoh: Menambah kategori toxicity "crypto"

```python
# 1. Edit app/services/toxicity_service.py

TOXICITY_PATTERNS = {
    ...
    "crypto": [r"\bcrypto\b", r"\bbitcoin\b", r"\bnft\b", r"\bweb3\b"],  # tambah
}

SEVERITY = {
    ...
    "crypto": "medium",  # tambah
}

# 2. Restart server → Score All → selesai
```

### Contoh: Mengubah label logic

```python
# Edit app/services/scoring_service.py → _determine_label()
# Lalu update warna di 4 template files:
#   - dashboard.html
#   - candidates/shortlist.html
#   - candidates/detail.html
#   - sources/detail.html
# Dan di export_service.py → _LABEL_FILLS
```

---

## Tips

- **Semua logic bisnis** ada di `app/services/` — route dan template cuma "kulit"
- **1 service = 1 concern** — jangan campur logic antar service
- **Config selalu di `.env`** — jangan hardcode value konfigurasi
- **Template pakai Tailwind class** — tidak perlu file CSS terpisah
- Kalau tambah kolom database, cukup tambah di model → restart → SQLAlchemy `create_all` otomatis bikin kolom baru (tapi tidak alter kolom existing)
