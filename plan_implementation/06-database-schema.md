# Database Schema Plan — Domain Intelligence & Underwriting Engine

**Database:** PostgreSQL 16  
**ORM:** SQLAlchemy 2.x (async)  
**Migrations:** Alembic  


---


## Entity Relationship Diagram

```
Source (1) ──────< (N) CrawlJob
Source (1) ──────< (N) CandidateDomain
CrawlJob (1) ───< (N) CandidateDomain
CandidateDomain (1) ──< (N) WaybackSnapshot
WaybackSnapshot (1) ──< (N) ToxicityFlag
```


---


## Tabel 1: `sources`

Sumber URL yang di-input owner untuk di-crawl.

| Kolom | Tipe | Constraint | Keterangan |
|-------|------|-----------|------------|
| `id` | `SERIAL` | PK | Auto increment |
| `url` | `VARCHAR(2048)` | NOT NULL, UNIQUE | URL halaman sumber |
| `niche` | `VARCHAR(100)` | NOT NULL | Kategori niche (Technology, Finance, dll) |
| `notes` | `TEXT` | NULLABLE | Catatan owner tentang source |
| `is_active` | `BOOLEAN` | DEFAULT true | Masih aktif di-crawl atau tidak |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() | Waktu ditambahkan |
| `updated_at` | `TIMESTAMPTZ` | DEFAULT now() | Waktu terakhir diubah |

**Index:**
- `idx_sources_niche` ON `niche`
- `idx_sources_active` ON `is_active`

```sql
CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    url VARCHAR(2048) NOT NULL UNIQUE,
    niche VARCHAR(100) NOT NULL,
    notes TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```


---


## Tabel 2: `crawl_jobs`

Log setiap kali crawl dijalankan.

| Kolom | Tipe | Constraint | Keterangan |
|-------|------|-----------|------------|
| `id` | `SERIAL` | PK | Auto increment |
| `source_id` | `INTEGER` | FK → sources.id, NOT NULL | Source yang di-crawl |
| `status` | `VARCHAR(20)` | NOT NULL, DEFAULT 'pending' | pending / running / completed / failed |
| `total_links_found` | `INTEGER` | DEFAULT 0 | Total link ditemukan di halaman |
| `total_candidates` | `INTEGER` | DEFAULT 0 | Total domain kandidat setelah filter |
| `total_dead_links` | `INTEGER` | DEFAULT 0 | Total dead link terdeteksi |
| `error_message` | `TEXT` | NULLABLE | Pesan error kalau gagal |
| `started_at` | `TIMESTAMPTZ` | NULLABLE | Waktu mulai crawl |
| `completed_at` | `TIMESTAMPTZ` | NULLABLE | Waktu selesai crawl |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() | Waktu job dibuat |

**Index:**
- `idx_crawl_jobs_source` ON `source_id`
- `idx_crawl_jobs_status` ON `status`

```sql
CREATE TABLE crawl_jobs (
    id SERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    total_links_found INTEGER DEFAULT 0,
    total_candidates INTEGER DEFAULT 0,
    total_dead_links INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);
```


---


## Tabel 3: `candidate_domains`

Domain kandidat hasil extract + filter dari crawl.

| Kolom | Tipe | Constraint | Keterangan |
|-------|------|-----------|------------|
| `id` | `SERIAL` | PK | Auto increment |
| `domain` | `VARCHAR(253)` | NOT NULL | Domain name (contoh: example.com) |
| `source_id` | `INTEGER` | FK → sources.id, NOT NULL | Sumber asal |
| `crawl_job_id` | `INTEGER` | FK → crawl_jobs.id, NOT NULL | Job crawl yang menemukan |
| `source_url_found` | `VARCHAR(2048)` | NULLABLE | URL spesifik tempat link ditemukan |
| `original_link` | `VARCHAR(2048)` | NULLABLE | Link asli dari halaman source |
| `niche` | `VARCHAR(100)` | NOT NULL | Inherited dari source |
| **— Link Status —** | | | |
| `http_status` | `INTEGER` | NULLABLE | HTTP status code saat check |
| `is_dead_link` | `BOOLEAN` | DEFAULT false | True jika 4xx/5xx/timeout |
| **— Availability —** | | | |
| `availability_status` | `VARCHAR(30)` | NULLABLE | available / expired / expiring_soon / expiring_watchlist / registered / unknown |
| `whois_registrar` | `VARCHAR(255)` | NULLABLE | Registrar saat ini |
| `whois_created_date` | `DATE` | NULLABLE | Tanggal domain pertama didaftarkan |
| `whois_expiry_date` | `DATE` | NULLABLE | Tanggal expired |
| `whois_days_left` | `INTEGER` | NULLABLE | Hari tersisa sampai expired |
| `dns_has_records` | `BOOLEAN` | NULLABLE | Ada DNS record atau tidak |
| `whois_checked_at` | `TIMESTAMPTZ` | NULLABLE | Kapan WHOIS terakhir dicek |
| **— History —** | | | |
| `wayback_total_snapshots` | `INTEGER` | DEFAULT 0 | Total snapshot di Wayback |
| `wayback_first_seen` | `DATE` | NULLABLE | Tanggal pertama di Wayback |
| `wayback_last_seen` | `DATE` | NULLABLE | Tanggal terakhir di Wayback |
| `wayback_years_active` | `INTEGER` | NULLABLE | Berapa tahun aktif |
| `dominant_language` | `VARCHAR(10)` | NULLABLE | Bahasa dominan (en, id, dll) |
| `content_drift_detected` | `BOOLEAN` | DEFAULT false | True jika konten berubah drastis |
| `wayback_checked_at` | `TIMESTAMPTZ` | NULLABLE | Kapan Wayback terakhir dicek |
| **— Scoring —** | | | |
| `score_availability` | `FLOAT` | NULLABLE | Skor komponen availability (0-100) |
| `score_continuity` | `FLOAT` | NULLABLE | Skor komponen continuity (0-100) |
| `score_cleanliness` | `FLOAT` | NULLABLE | Skor komponen cleanliness (0-100) |
| `score_total` | `FLOAT` | NULLABLE | Skor akhir weighted (0-100) |
| `label` | `VARCHAR(20)` | NULLABLE | buy_candidate / manual_review / auto_discard |
| `label_reason` | `TEXT` | NULLABLE | Alasan readable kenapa label ini |
| **— Owner —** | | | |
| `owner_notes` | `TEXT` | NULLABLE | Catatan manual dari owner |
| **— Meta —** | | | |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() | Pertama kali ditemukan |
| `updated_at` | `TIMESTAMPTZ` | DEFAULT now() | Terakhir diubah |

**Index:**
- `idx_candidates_domain` ON `domain`
- `idx_candidates_source` ON `source_id`
- `idx_candidates_label` ON `label`
- `idx_candidates_score` ON `score_total DESC NULLS LAST`
- `idx_candidates_availability` ON `availability_status`
- `idx_candidates_niche` ON `niche`
- `uq_candidates_domain_source` UNIQUE ON (`domain`, `source_id`) — satu domain per source

```sql
CREATE TABLE candidate_domains (
    id SERIAL PRIMARY KEY,
    domain VARCHAR(253) NOT NULL,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    crawl_job_id INTEGER NOT NULL REFERENCES crawl_jobs(id) ON DELETE CASCADE,
    source_url_found VARCHAR(2048),
    original_link VARCHAR(2048),
    niche VARCHAR(100) NOT NULL,

    -- Link Status
    http_status INTEGER,
    is_dead_link BOOLEAN DEFAULT false,

    -- Availability
    availability_status VARCHAR(30),
    whois_registrar VARCHAR(255),
    whois_created_date DATE,
    whois_expiry_date DATE,
    whois_days_left INTEGER,
    dns_has_records BOOLEAN,
    whois_checked_at TIMESTAMPTZ,

    -- History
    wayback_total_snapshots INTEGER DEFAULT 0,
    wayback_first_seen DATE,
    wayback_last_seen DATE,
    wayback_years_active INTEGER,
    dominant_language VARCHAR(10),
    content_drift_detected BOOLEAN DEFAULT false,
    wayback_checked_at TIMESTAMPTZ,

    -- Scoring
    score_availability FLOAT,
    score_continuity FLOAT,
    score_cleanliness FLOAT,
    score_total FLOAT,
    label VARCHAR(20),
    label_reason TEXT,

    -- Owner
    owner_notes TEXT,

    -- Meta
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT uq_candidates_domain_source UNIQUE (domain, source_id)
);
```


---


## Tabel 4: `wayback_snapshots`

Sample snapshot yang di-fetch dan dianalisis per domain.

| Kolom | Tipe | Constraint | Keterangan |
|-------|------|-----------|------------|
| `id` | `SERIAL` | PK | Auto increment |
| `candidate_id` | `INTEGER` | FK → candidate_domains.id, NOT NULL | Domain pemilik |
| `timestamp` | `VARCHAR(14)` | NOT NULL | Wayback timestamp (YYYYMMDDHHmmss) |
| `snapshot_url` | `VARCHAR(2048)` | NOT NULL | URL snapshot di Wayback |
| `http_status` | `INTEGER` | NULLABLE | HTTP status dari Wayback |
| `content_length` | `INTEGER` | NULLABLE | Panjang content (bytes) |
| `detected_language` | `VARCHAR(10)` | NULLABLE | Bahasa terdeteksi dari content |
| `content_summary` | `VARCHAR(500)` | NULLABLE | Ringkasan singkat (title + excerpt) |
| `has_toxicity` | `BOOLEAN` | DEFAULT false | Ada flag toxicity atau tidak |
| `fetched_at` | `TIMESTAMPTZ` | DEFAULT now() | Kapan snapshot di-fetch |

**Index:**
- `idx_snapshots_candidate` ON `candidate_id`

```sql
CREATE TABLE wayback_snapshots (
    id SERIAL PRIMARY KEY,
    candidate_id INTEGER NOT NULL REFERENCES candidate_domains(id) ON DELETE CASCADE,
    timestamp VARCHAR(14) NOT NULL,
    snapshot_url VARCHAR(2048) NOT NULL,
    http_status INTEGER,
    content_length INTEGER,
    detected_language VARCHAR(10),
    content_summary VARCHAR(500),
    has_toxicity BOOLEAN DEFAULT false,
    fetched_at TIMESTAMPTZ DEFAULT now()
);
```


---


## Tabel 5: `toxicity_flags`

Flag toxicity yang ditemukan di snapshot.

| Kolom | Tipe | Constraint | Keterangan |
|-------|------|-----------|------------|
| `id` | `SERIAL` | PK | Auto increment |
| `snapshot_id` | `INTEGER` | FK → wayback_snapshots.id, NOT NULL | Snapshot yang mengandung flag |
| `candidate_id` | `INTEGER` | FK → candidate_domains.id, NOT NULL | Domain pemilik (denormalized untuk query cepat) |
| `flag_type` | `VARCHAR(30)` | NOT NULL | parking / adult / gambling / pharma / malware / redirect / cloaking |
| `evidence` | `TEXT` | NULLABLE | Keyword/pattern yang match |
| `severity` | `VARCHAR(10)` | NOT NULL, DEFAULT 'medium' | low / medium / high / critical |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() | Kapan flag dibuat |

**Severity rules:**
- `critical` → malware, cloaking (auto-discard)
- `high` → adult, gambling
- `medium` → pharma, redirect
- `low` → parking

**Index:**
- `idx_flags_candidate` ON `candidate_id`
- `idx_flags_type` ON `flag_type`

```sql
CREATE TABLE toxicity_flags (
    id SERIAL PRIMARY KEY,
    snapshot_id INTEGER NOT NULL REFERENCES wayback_snapshots(id) ON DELETE CASCADE,
    candidate_id INTEGER NOT NULL REFERENCES candidate_domains(id) ON DELETE CASCADE,
    flag_type VARCHAR(30) NOT NULL,
    evidence TEXT,
    severity VARCHAR(10) NOT NULL DEFAULT 'medium',
    created_at TIMESTAMPTZ DEFAULT now()
);
```


---


## Availability Status Rules

Referensi cepat — 6 status dari WHOIS + DNS check:

| Status | Kondisi |
|--------|---------|
| `available` | WHOIS kosong DAN DNS tidak ada record |
| `expired` | WHOIS ada tapi `expiry_date` sudah lewat |
| `expiring_soon` | days_left ≤ 30 |
| `expiring_watchlist` | 30 < days_left ≤ 90 |
| `registered` | Domain aktif, expiry masih jauh |
| `unknown` | WHOIS gagal / timeout |


---


## Scoring Formula Reference

```
score_total = (score_availability × 0.30)
            + (score_continuity  × 0.40)
            + (score_cleanliness × 0.30)
```

**Label assignment:**
- `score_total ≥ 80` → `buy_candidate` (hijau)
- `40 ≤ score_total < 80` → `manual_review` (kuning)
- `score_total < 40` → `auto_discard` (merah)
- Ada flag `critical` → `auto_discard` (override apapun)


---


## Migration Plan

```bash
# Init Alembic
alembic init migrations

# Create migration
alembic revision --autogenerate -m "initial schema"

# Apply
alembic upgrade head

# Rollback
alembic downgrade -1
```

**Migration naming convention:**
```
001_initial_schema.py
002_add_wayback_fields.py
003_add_scoring_fields.py
004_add_owner_notes.py
```

Setiap minggu, setelah tasks selesai, jalankan `alembic revision --autogenerate` untuk menangkap perubahan model.


---


## Query Patterns (Frequently Used)

```sql
-- Shortlist: semua buy candidates, sorted by score
SELECT * FROM candidate_domains
WHERE label = 'buy_candidate'
ORDER BY score_total DESC;

-- Filter by niche + status
SELECT * FROM candidate_domains
WHERE niche = 'Technology'
  AND availability_status = 'available'
ORDER BY score_total DESC;

-- Summary counts per label
SELECT label, COUNT(*) as count
FROM candidate_domains
WHERE source_id = ?
GROUP BY label;

-- Domains with critical flags
SELECT DISTINCT cd.*
FROM candidate_domains cd
JOIN toxicity_flags tf ON tf.candidate_id = cd.id
WHERE tf.severity = 'critical';

-- Export: semua data lengkap
SELECT
    cd.domain, cd.niche, cd.availability_status,
    cd.score_total, cd.label, cd.label_reason,
    cd.whois_registrar, cd.whois_created_date, cd.whois_expiry_date,
    cd.whois_days_left, cd.wayback_total_snapshots,
    cd.wayback_first_seen, cd.wayback_last_seen,
    cd.dominant_language, cd.owner_notes,
    s.url as source_url
FROM candidate_domains cd
JOIN sources s ON s.id = cd.source_id
ORDER BY cd.score_total DESC;
```
