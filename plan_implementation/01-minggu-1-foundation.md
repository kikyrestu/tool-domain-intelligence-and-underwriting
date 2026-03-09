# Minggu 1 — Foundation + Source Discovery

**Periode:** 9–15 Maret 2026  
**Goal:** Owner bisa input URL, sistem crawl dan tampilkan tabel kandidat mentah  
**Syarat Done yang dicakup:** #1, #2


---


## Task List

### Day 1-2: Project Setup

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 1.1 | Init project structure (folders, config, Docker) | Skeleton project siap | 2 jam |
| 1.2 | Setup Docker Compose (FastAPI + PostgreSQL + Caddy) | `docker compose up` jalan | 3 jam |
| 1.3 | Setup FastAPI app skeleton (routes, templates, static) | Hello world di browser | 1 jam |
| 1.4 | Setup SQLAlchemy + Alembic + koneksi DB | Migrasi pertama jalan | 2 jam |
| 1.5 | Setup .env, config loader, logging dasar | Config terbaca dari env | 1 jam |
| 1.6 | Setup proxy rotator module (pindah dari demo/) | Proxy siap dipakai | 1 jam |

### Day 2-3: Database Schema

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 1.7 | Buat model `Source` (id, url, niche, label, created_at, status) | Tabel di DB | 1 jam |
| 1.8 | Buat model `CrawlJob` (id, source_id, status, started_at, finished_at, stats) | Tabel di DB | 1 jam |
| 1.9 | Buat model `CandidateDomain` (id, domain, source_id, crawl_job_id, url_found, link_status, created_at) | Tabel di DB | 1 jam |
| 1.10 | Migrasi Alembic + seed data test | DB ready | 1 jam |

### Day 3-4: Source Discovery — Input Form

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 1.11 | Halaman "Add Source" — form input URL + niche dropdown + label | Form di browser | 2 jam |
| 1.12 | API endpoint POST `/sources` — simpan ke DB | Source tersimpan | 1 jam |
| 1.13 | Halaman "Sources" — list semua source yang sudah di-input | Tabel source | 1 jam |
| 1.14 | Tombol "Crawl" di daftar source — trigger crawl job | Trigger jalan | 1 jam |

### Day 4-5: Crawl Engine

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 1.15 | Pindah crawl logic dari demo ke module `app/services/crawl.py` | Service siap | 2 jam |
| 1.16 | Crawl engine: fetch page → extract outbound links → dedup root domain | Daftar link | 2 jam |
| 1.17 | Dead link detection: async HTTP check + DNS resolve | Status dead/alive per link | 2 jam |
| 1.18 | SSRF protection: validasi URL, block private IP | Security layer | 1 jam |
| 1.19 | Blacklist filter: skip domain besar (google, facebook, dll) | Filter aktif | 1 jam |
| 1.20 | TLD filter: hanya loloskan .com, .net, .org, dll | Filter aktif | 30 menit |
| 1.21 | Simpan hasil ke tabel `CandidateDomain` | Data di DB | 1 jam |

### Day 5-6: Dashboard — Tabel Kandidat

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 1.22 | Halaman "Candidates" — tabel daftar domain kandidat | Tabel di browser | 2 jam |
| 1.23 | Kolom: domain, source, niche, link status, discovered at | Data ditampilkan | 1 jam |
| 1.24 | Summary bar: total kandidat, alive, dead, unresolved | Overview di atas | 1 jam |
| 1.25 | Base template (header, sidebar, layout) dengan Tailwind | UI konsisten | 2 jam |

### Day 7: Buffer + Demo Prep

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 1.26 | Fix bugs, polish UI | Stabil | 2 jam |
| 1.27 | Siapkan demo scenario untuk owner | Demo script | 1 jam |
| 1.28 | Update progress tracker | Tracker updated | 30 menit |


---


## Demo M1 — Jumat 14 Maret

**Scenario:**
1. Owner buka dashboard di browser
2. Klik "Add Source" → masukkan URL + pilih niche "Technology"
3. Klik "Crawl"
4. Tabel kandidat muncul dengan status dead/alive per link
5. Summary bar menampilkan total kandidat

**Bukti selesai:**
- [ ] Form input source URL + niche jalan
- [ ] Crawl engine extract outbound links + dedup
- [ ] Dead link terdeteksi dan ditandai
- [ ] Tabel kandidat tampil di dashboard
- [ ] Summary bar menampilkan statistik
- [ ] Docker Compose running
- [ ] Database terisi data hasil crawl


---


## Risiko Minggu 1

| Risiko | Mitigasi |
|--------|----------|
| Docker setup lambat / conflict port | Test Docker awal di Day 1, fix segera |
| Alembic migration error | Keep migration simple, test per model |
| Template/UI makan waktu | Pakai Tailwind utility classes, jangan over-design |
