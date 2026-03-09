# Architecture Plan — Domain Intelligence & Underwriting Engine

## Prinsip Arsitektur

1. **Monolith dulu** — Satu aplikasi FastAPI, bukan microservice
2. **Server-side rendering** — Jinja2 + HTMX, bukan SPA
3. **Service layer** — Logic di service, bukan di route handler
4. **Async pipeline** — Crawl + check berjalan background, dashboard tetap responsif
5. **Modular** — Setiap engine (crawl, whois, wayback, scoring) bisa dipanggil independen


---


## Folder Structure

```
domain-underwriting/
│
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app factory, lifespan
│   ├── config.py                  # Settings dari .env (pydantic-settings)
│   ├── database.py                # SQLAlchemy engine, session factory
│   │
│   ├── models/                    # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── source.py              # Source (URL sumber + niche)
│   │   ├── crawl_job.py           # CrawlJob (log per crawl run)
│   │   ├── candidate.py           # CandidateDomain (domain kandidat)
│   │   ├── snapshot.py            # WaybackSnapshot (data per snapshot)
│   │   └── toxicity_flag.py       # ToxicityFlag (flag per snapshot)
│   │
│   ├── schemas/                   # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── source.py
│   │   ├── candidate.py
│   │   └── export.py
│   │
│   ├── services/                  # Business logic layer
│   │   ├── __init__.py
│   │   ├── crawl_service.py       # Crawl engine: fetch page → extract links
│   │   ├── whois_service.py       # WHOIS + DNS availability check
│   │   ├── wayback_service.py     # Wayback CDX fetch + content analysis
│   │   ├── scoring_service.py     # 3-component scoring engine
│   │   ├── export_service.py      # CSV + XLSX generation
│   │   └── proxy_service.py       # Proxy rotation
│   │
│   ├── routes/                    # FastAPI route handlers (thin)
│   │   ├── __init__.py
│   │   ├── dashboard.py           # GET / — homepage dashboard
│   │   ├── sources.py             # CRUD source URLs
│   │   ├── candidates.py          # Shortlist, detail, notes
│   │   ├── crawl.py               # Trigger crawl, status
│   │   └── export.py              # Download CSV/XLSX
│   │
│   ├── templates/                 # Jinja2 HTML templates
│   │   ├── base.html              # Layout: header, nav, footer
│   │   ├── dashboard.html         # Homepage summary
│   │   ├── sources/
│   │   │   ├── list.html          # Daftar source
│   │   │   ├── add.html           # Form tambah source
│   │   │   └── detail.html        # Detail source + hasil crawl
│   │   ├── candidates/
│   │   │   ├── shortlist.html     # Shortlist + filter + search
│   │   │   └── detail.html        # Domain detail card
│   │   └── partials/              # HTMX partial fragments
│   │       ├── candidate_row.html
│   │       ├── candidate_card.html
│   │       ├── crawl_status.html
│   │       └── filter_results.html
│   │
│   ├── static/                    # Static assets
│   │   ├── css/
│   │   │   └── app.css            # Tailwind output
│   │   ├── js/
│   │   │   └── htmx.min.js        # HTMX library
│   │   └── img/
│   │
│   └── utils/                     # Shared utilities
│       ├── __init__.py
│       ├── ssrf_guard.py          # URL validation (anti-SSRF)
│       ├── domain_filter.py       # Blacklist + TLD filter
│       └── text_analysis.py       # Language detect + toxicity keywords
│
├── migrations/                    # Alembic migrations
│   ├── env.py
│   ├── versions/
│   └── alembic.ini
│
├── tests/                         # Pytest tests
│   ├── conftest.py
│   ├── test_crawl_service.py
│   ├── test_whois_service.py
│   ├── test_wayback_service.py
│   ├── test_scoring_service.py
│   └── test_routes.py
│
├── docs/                          # Dokumentasi
│   ├── brief.md
│   ├── goals.md
│   ├── jawaban-hari-pertama.md
│   ├── laporan-demo.md
│   ├── panduan-pengguna.md        # User guide (M4)
│   └── panduan-teknis.md          # Tech guide (M4)
│
├── demo/                          # Proof-of-concept (existing)
│
├── docker-compose.yml             # PostgreSQL + App
├── Dockerfile                     # Python app image
├── Caddyfile                      # Reverse proxy config
├── .env                           # Environment variables
├── .env.example
├── .gitignore
├── proxies.txt                    # Proxy list
├── requirements.txt               # Python dependencies
├── tailwind.config.js             # Tailwind CSS config
└── README.md
```


---


## Module Responsibilities

### Routes (Thin Controllers)

Routes hanya:
1. Parse request
2. Panggil service
3. Return response / render template

```
POST /sources          → SourceService.create()
GET  /sources          → SourceService.list()
GET  /sources/{id}     → SourceService.get_detail()

POST /crawl/{source_id} → CrawlService.run()
GET  /crawl/status/{job_id} → CrawlService.get_status()

GET  /candidates       → CandidateService.list(filters)
GET  /candidates/{id}  → CandidateService.get_detail()
PATCH /candidates/{id}/notes → CandidateService.update_notes()

GET  /export/xlsx      → ExportService.to_xlsx(filters)
GET  /export/csv       → ExportService.to_csv(filters)

GET  /                 → DashboardService.get_summary()
```

### Services (Business Logic)

| Service | Tanggung Jawab |
|---------|----------------|
| `CrawlService` | Fetch source page, extract links, filter domain, detect dead links, simpan ke DB |
| `WhoisService` | WHOIS lookup, DNS resolve, determine availability status (6 rules) |
| `WaybackService` | CDX API fetch, sample snapshots, analyze content, detect language, detect toxicity |
| `ScoringService` | Calculate 3-component score, assign label (Buy/Review/Discard), generate reason |
| `ExportService` | Query DB, format ke CSV/XLSX dengan kolom lengkap |
| `ProxyService` | Load proxies, rotate, provide httpx client with proxy |


---


## Pipeline Flow

```
[Owner Input]
     │
     ▼
┌─────────────────┐
│  Source URL +    │
│  Niche stored   │
│  to DB          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  CrawlService   │  ← ProxyService
│  - Fetch page   │
│  - Extract links│
│  - Filter domain│
│  - Dead link    │
│  - Save to DB   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  WhoisService   │
│  - WHOIS lookup │
│  - DNS resolve  │
│  - Status tag   │
│  - Save to DB   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  WaybackService │  ← ProxyService
│  - CDX fetch    │
│  - Sample 5     │
│  - Analyze      │
│  - Toxicity     │
│  - Save to DB   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ScoringService │
│  - Calc score   │
│  - Assign label │
│  - Reason text  │
│  - Save to DB   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Dashboard      │
│  - Shortlist    │
│  - Filter/Sort  │
│  - Detail card  │
│  - Export       │
└─────────────────┘
```


---


## Integrasi HTMX

Dashboard menggunakan HTMX untuk interaksi tanpa full page reload:

| Aksi | HTMX Pattern |
|------|-------------|
| Trigger crawl | `hx-post="/crawl/{id}"` → swap status indicator |
| Filter shortlist | `hx-get="/candidates?label=buy"` → swap table |
| Search domain | `hx-get="/candidates?q=..."` → swap table |
| Sort | `hx-get="/candidates?sort=score"` → swap table |
| Load detail | `hx-get="/candidates/{id}"` → modal / new page |
| Crawl progress | `hx-get="/crawl/status/{id}" hx-trigger="every 3s"` → poll status |


---


## Config Management

Semua config via environment variables:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/domain_intel

# App
APP_HOST=0.0.0.0
APP_PORT=8000
SECRET_KEY=random-secret-key
AUTH_USERNAME=admin
AUTH_PASSWORD=secure-password

# Proxy
PROXY_FILE=proxies.txt

# Scoring thresholds
SCORE_BUY_THRESHOLD=80
SCORE_DISCARD_THRESHOLD=40

# Rate limiting
CRAWL_DELAY_SECONDS=2
WHOIS_DELAY_SECONDS=1.5
WAYBACK_DELAY_SECONDS=1

# Limits
MAX_CANDIDATES_PER_CRAWL=500
WAYBACK_SAMPLE_SIZE=5
```


---


## Deployment Architecture

```
[Internet] → [Caddy :443] → [FastAPI :8000] → [PostgreSQL :5432]
                  │
                  └── Auto TLS (Let's Encrypt)
```

Docker Compose:
- `app` — FastAPI container (Python 3.11-slim)
- `db` — PostgreSQL 16 container (with volume)
- `caddy` — Caddy container (reverse proxy, TLS)

Semua dalam satu VPS (2 vCPU, 4GB RAM).


---


## Batasan Phase 1

**TIDAK DIBANGUN di Phase 1:**
- REST API publik
- Multi-user / role-based access
- Auto-scheduling crawl (manual trigger only)
- Domain marketplace integration
- Mobile app
- AI/ML scoring (rule-based only)
- Notification system
- Bulk upload (1 URL per input)

Semua request di luar scope → `docs/backlog-fase2.md`
