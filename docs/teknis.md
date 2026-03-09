# Domain IQ — Dokumentasi Teknis

## Arsitektur

```
Browser (localhost:8000)
  │
  ▼
FastAPI (Jinja2 + HTMX)
  │
  ├── Routes:  dashboard, sources, candidates, crawl, export
  ├── Services: crawl, rdap, wayback, toxicity, scoring, export
  ├── Auth:    HTTP Basic Auth middleware
  │
  ▼
PostgreSQL (Neon cloud)
```

### Stack
| Komponen | Teknologi |
|----------|-----------|
| Backend | FastAPI 0.135+ (async) |
| ORM | SQLAlchemy 2.0 (async) + asyncpg |
| Frontend | Jinja2 + Tailwind CSS (CDN) + HTMX 2.0 |
| Database | PostgreSQL 16 |
| Proxy | Webshare datacenter proxies |
| Export | openpyxl (XLSX), csv (CSV) |
| Auth | HTTP Basic Auth (starlette middleware) |

---

## Struktur Database

### Tabel `sources`
| Kolom | Tipe | Keterangan |
|-------|------|------------|
| id | INTEGER PK | Auto increment |
| url | VARCHAR | URL sumber |
| niche | VARCHAR | Kategori niche |
| notes | TEXT | Catatan |
| is_active | BOOLEAN | Status aktif |
| created_at | DATETIME | Waktu dibuat |
| updated_at | DATETIME | Waktu diupdate |

### Tabel `crawl_jobs`
| Kolom | Tipe | Keterangan |
|-------|------|------------|
| id | INTEGER PK | Auto increment |
| source_id | INTEGER FK | Referensi ke sources |
| status | VARCHAR | pending/running/completed/failed |
| total_links | INTEGER | Total link ditemukan |
| total_candidates | INTEGER | Total kandidat domain |
| total_dead_links | INTEGER | Total dead link |
| error_message | TEXT | Pesan error (jika gagal) |
| created_at | DATETIME | Waktu mulai |
| completed_at | DATETIME | Waktu selesai |

### Tabel `candidate_domains`
| Kolom | Tipe | Keterangan |
|-------|------|------------|
| id | INTEGER PK | Auto increment |
| domain | VARCHAR | Nama domain |
| source_url | VARCHAR | URL asal |
| source_id | INTEGER FK | Referensi ke sources |
| niche | VARCHAR | Kategori niche |
| link_url | VARCHAR | URL link yang mengandung domain |
| is_domain_alive | BOOLEAN | Domain masih hidup? |
| dns_resolves | BOOLEAN | DNS resolve? |
| http_status | INTEGER | HTTP status code |
| is_parked | BOOLEAN | Domain parking? |
| availability_status | VARCHAR | available/registered/expired/dll |
| whois_registrar | VARCHAR | Nama registrar |
| whois_created_date | DATE | Tanggal registrasi |
| whois_expiry_date | DATE | Tanggal expired |
| whois_days_left | INTEGER | Sisa hari sebelum expired |
| whois_checked_at | DATETIME | Waktu cek RDAP terakhir |
| wayback_total_snapshots | INTEGER | Jumlah snapshot Wayback |
| first_seen | DATE | Tanggal pertama di Wayback |
| last_seen | DATE | Tanggal terakhir di Wayback |
| years_active | FLOAT | Lama aktif (tahun) |
| dominant_language | VARCHAR | Bahasa dominan |
| content_drift_detected | BOOLEAN | Perubahan konten terdeteksi |
| toxicity_flags | JSON | Daftar flag toxicity |
| score_availability | FLOAT | Skor availability (0-100) |
| score_continuity | FLOAT | Skor continuity (0-100) |
| score_cleanliness | FLOAT | Skor cleanliness (0-100) |
| score_total | FLOAT | Skor total (0-100) |
| label | VARCHAR | Available/Watchlist/Uncertain/Discard |
| label_reason | TEXT | Alasan label |
| owner_notes | TEXT | Catatan owner |
| created_at | DATETIME | Waktu ditemukan |
| updated_at | DATETIME | Waktu diupdate |

**Constraint**: UNIQUE(domain, source_id)

---

## Environment Variables

Buat file `.env` di root project:

```env
# Database — Neon (cloud)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname?ssl=require

# Auth
AUTH_USERNAME=admin
AUTH_PASSWORD=ganti_password_kuat

# Proxy
PROXY_ENABLED=true
PROXY_FILE=proxies.txt

# Rate limiting
CRAWL_DELAY_SECONDS=2.0
RDAP_DELAY_SECONDS=1.0
WAYBACK_DELAY_SECONDS=1.0

# Limits
MAX_CANDIDATES_PER_CRAWL=500
WAYBACK_SAMPLE_SIZE=5
```

---

## Menjalankan di Localhost

### Prasyarat
- Python 3.11+ terinstall
- Akun database Neon (gratis) — https://neon.tech
- File `.env` sudah dikonfigurasi

### Langkah Setup

```bash
# 1. Clone repo
git clone https://github.com/kikyrestu/tool-domain-intelligence-and-underwriting.git
cd tool-domain-intelligence-and-underwriting

# 2. Install dependencies
pip install -r requirements.txt

# 3. Buat .env
copy .env.example .env
# edit .env — isi DATABASE_URL dari Neon dashboard

# 4. Jalankan server
uvicorn app.main:app --reload --port 8000

# 5. Akses di browser
# http://localhost:8000
```

### Menjalankan di background (Windows)
```powershell
# Start server di background
Start-Process -NoNewWindow uvicorn -ArgumentList "app.main:app","--reload","--port","8000"

# Atau pakai pythonw
pythonw -m uvicorn app.main:app --port 8000
```

### Auto-start saat boot (opsional)
1. Buat shortcut file `.bat`:
```bat
@echo off
cd /d D:\PROJECT\client-10
python -m uvicorn app.main:app --port 8000
```
2. Taruh shortcut di folder Startup: `shell:startup`

---

## Konfigurasi Proxy

1. Edit file `proxies.txt` di root project
2. Format per baris: `http://user:pass@host:port`
3. Sistem akan round-robin semua proxy
4. Set `PROXY_ENABLED=false` di `.env` untuk disable

```
http://user1:pass1@proxy1.webshare.io:80
http://user2:pass2@proxy2.webshare.io:80
```

---

## Kustomisasi Scoring

### Label Logic
Label ditentukan berdasarkan status domain dan availability:
- **Available**: domain dead + RDAP menunjukkan available/expired
- **Watchlist**: domain dead + registered (atau expiring soon)
- **Uncertain**: belum ada data RDAP
- **Discard**: domain alive + registered, atau ada toxicity flag berat

### Bobot komponen skor
Edit `app/services/scoring_service.py`:
```python
WEIGHT_AVAILABILITY = 0.30   # 30% — bonus jika bisa dibeli
WEIGHT_CONTINUITY  = 0.40   # 40% — history panjang = bagus
WEIGHT_CLEANLINESS = 0.30   # 30% — bersih dari konten buruk
```

### Cara hitung skor:
- **Availability**: available/expired = 100, expiring_soon = 80, watchlist = 50, registered = 20, check_failed = 40
- **Continuity**: berdasarkan years_active (max 10 tahun = 100) + jumlah snapshot (max 50 = bonus 20)
- **Cleanliness**: 100 dikurangi penalty per toxicity flag (high = -30, medium = -15)

---

## Kustomisasi Toxicity Keywords

Edit `app/services/toxicity_service.py`:

```python
TOXICITY_PATTERNS = {
    "parking": [r"buy this domain", r"domain for sale", ...],
    "adult": [r"\bporn\b", r"\bxxx\b", ...],
    "gambling": [r"\bcasino\b", r"\bpoker\b", ...],
    "pharma": [r"\bviagra\b", r"\bcialis\b", ...],
    "malware": [r"keygen", r"warez", ...],
}

# Severity per kategori
SEVERITY = {
    "parking": "medium",    # penalty -15
    "adult": "high",        # penalty -30
    "gambling": "high",     # penalty -30
    "pharma": "high",       # penalty -30
    "malware": "high",      # penalty -30
    "language_mismatch": "medium",  # penalty -15
    "young_domain": "medium",       # penalty -15
}
```

Untuk menambah kategori baru:
1. Tambahkan key + patterns di `TOXICITY_PATTERNS`
2. Tambahkan severity di `SEVERITY`
3. Restart server

---

## Blacklist Domain

Edit `app/services/crawl_service.py`, cari `DOMAIN_BLACKLIST`:

```python
DOMAIN_BLACKLIST = {
    "google.com", "youtube.com", "facebook.com",
    "twitter.com", "instagram.com", "linkedin.com",
    # Tambahkan domain besar yang tidak relevan
    "amazon.com", "reddit.com",
}
```

---

## API Endpoints

| Method | Path | Fungsi |
|--------|------|--------|
| GET | `/` | Dashboard utama |
| GET | `/sources` | Daftar sources |
| POST | `/sources` | Tambah source baru |
| GET | `/sources/{id}` | Detail source + kandidat |
| POST | `/sources/{id}/edit` | Edit source |
| POST | `/sources/{id}/delete` | Hapus source |
| GET | `/candidates` | Shortlist kandidat (filter) |
| GET | `/candidates/{id}` | Detail kandidat domain |
| POST | `/candidates/{id}/notes` | Update catatan owner |
| POST | `/crawl/{source_id}` | Trigger crawl |
| POST | `/crawl/whois/{source_id}` | RDAP check per source |
| POST | `/crawl/whois-all` | RDAP check semua domain |
| POST | `/crawl/wayback/{source_id}` | Wayback audit per source |
| POST | `/crawl/wayback-all` | Wayback audit semua |
| POST | `/crawl/score/{source_id}` | Scoring per source |
| POST | `/crawl/score-all` | Scoring semua domain |
| GET | `/export/csv` | Export CSV (query: status, niche, label) |
| GET | `/export/xlsx` | Export XLSX (query: status, niche, label) |

---

## Troubleshooting

### Server tidak mau start
```
Error: Connection refused to database
```
→ Cek DATABASE_URL di `.env`. Pastikan PostgreSQL running.

### RDAP check_failed untuk banyak domain
→ Normal untuk TLD tertentu yang RDAP server-nya tidak stabil. Dead domain dicek otomatis saat crawl.

### Wayback audit tidak menemukan snapshot
→ Domain mungkin belum pernah diindeks Wayback Machine. Ini bukan error.

### Proxy error
```
Error: ProxyError
```
→ Cek `proxies.txt`. Pastikan format benar dan proxy masih aktif. Set `PROXY_ENABLED=false` untuk disable.

### Skor semua 0
→ Jalankan pipeline secara berurutan: Crawl → RDAP → Wayback → Score. Dead domain sudah otomatis dicek RDAP saat crawl. Scoring memerlukan data RDAP dan Wayback.

### Memory error pada crawl besar
→ Kurangi `MAX_CANDIDATES_PER_CRAWL` di `.env` (default: 500).
