# Domain IQ — Domain Intelligence & Underwriting Tool

Platform otomatis untuk **menemukan, menganalisis, dan menilai domain bekas** yang berpotensi bernilai tinggi. Mencakup crawling multi-provider, pengecekan RDAP/WHOIS, analisis riwayat Wayback Machine, deteksi toksisitas konten, dan scoring domain berbasis multi-kriteria.

---

## Fitur Utama

| Fitur | Deskripsi |
|---|---|
| **Multi-provider Crawling** | ZenRows → ScraperAPI → Scrapingbee → Crawlbase, round-robin otomatis |
| **RDAP / WHOIS** | Cek ketersediaan domain via IANA Bootstrap + ccTLD authoritative endpoints |
| **Wayback Machine** | Analisis riwayat domain: total snapshot, bahasa, content drift, first/last seen |
| **Toxicity Detection** | Scan konten historis: adult, gambling, pharma, malware, dsb. |
| **Domain Scoring** | Skor 0–100 dari 3 komponen: availability, continuity, cleanliness |
| **Parking Detection** | Deteksi live domain yang sedang diparkir |
| **MX Record Check** | Cek apakah domain punya email aktif |
| **Auto Source Discovery** | Domain outbound dari Wayback otomatis ditambah sebagai source crawl |
| **Export** | Export kandidat ke CSV / Excel |
| **Dashboard Web** | UI berbasis HTMX — real-time crawl status tanpa refresh |

---

## Tech Stack

- **Backend:** FastAPI + SQLAlchemy 2.0 async + asyncpg
- **Database:** PostgreSQL (Neon cloud atau lokal)
- **Frontend:** Jinja2 + HTMX + TailwindCSS
- **Scraping:** httpx async + multi-provider API

---

## Cara Setup

### 1. Clone & Install Dependencies

```bash
git clone https://github.com/kikyrestu/tool-domain-intelligence-and-underwriting.git
cd tool-domain-intelligence-and-underwriting
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Konfigurasi Environment

```bash
cp .env.example .env
```

Edit `.env` — isi minimal koneksi database dan satu API provider scraping:

```env
# Opsi A: field terpisah (direkomendasikan)
DB_HOST=your_database_host
DB_PORT=5432
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_SSL=true

# Opsi B: URL langsung
# DATABASE_URL=postgresql+asyncpg://user:password@host/dbname?ssl=require
```

> Lihat [.env.example](.env.example) untuk daftar lengkap semua variable.

### 3. Jalankan

```bash
# Windows (one-click)
start-server.bat

# Atau manual
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Buka browser: **http://localhost:8000**

Login default: `admin` / `DomainIQ#2026!` *(ganti di `.env`)*

### 4. Docker (opsional)

```bash
docker-compose up --build
```

---

## Setup Database Lokal (PostgreSQL)

Lihat panduan lengkap di [README_SETUP_MANUAL.md](README_SETUP_MANUAL.md).

---

## Struktur Project

```
app/
├── models/         # SQLAlchemy ORM models
├── routes/         # FastAPI route handlers
├── schemas/        # Pydantic schemas
├── services/       # Business logic (crawl, RDAP, Wayback, scoring, dll.)
├── templates/      # Jinja2 HTML templates
├── utils/          # Helper: domain filter, SSRF guard
├── config.py       # Settings dari .env
└── main.py         # FastAPI app entry point
scripts/            # Utility scripts (pipeline, recheck, debug)
tests/              # E2E tests
docs/               # Dokumentasi teknis & user guide
```

---

## API Scraping Providers

Semua provider optional — isi minimal satu. Dirotasi otomatis round-robin:

| Provider | Free Tier | Env Variable |
|---|---|---|
| ZenRows | 1.000 credits/bulan | `ZENROWS_API_KEYS` |
| ScraperAPI | 5.000 req/bulan | `SCRAPERAPI_KEYS` |
| Scrapingbee | 150 req/bulan | `SCRAPINGBEE_KEYS` |
| Crawlbase | berbayar | `CRAWLBASE_KEYS` |
| ScrapeGraphAI | berbayar | `SCRAPEGRAPHAI_KEY` |

Semua mendukung multi-key comma-separated: `KEY1,KEY2,KEY3`

---

## Catatan Keamanan

- **Jangan commit `.env`** — sudah ada di `.gitignore`
- Ganti `SECRET_KEY` dan `AUTH_PASSWORD` sebelum deploy ke server publik
- SSRF guard aktif: request ke IP internal/lokal diblokir otomatis
