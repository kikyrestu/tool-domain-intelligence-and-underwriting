# Jawaban Programmer — Hari Pertama

Dokumen ini menjawab 4 pertanyaan wajib dari briefing (Bagian 9).  
Tanggal: 9 Maret 2026


---


## 1. Stack Final yang Dipilih

| Komponen | Pilihan | Alasan |
|----------|---------|--------|
| **Backend** | FastAPI (Python 3.11+) | Async-ready, auto-generate API docs (Swagger), ringan, cocok untuk crawl jobs |
| **Database** | PostgreSQL 16 | Lebih robust dari SQLite untuk concurrent access dashboard + crawl jobs bersamaan |
| **ORM** | SQLAlchemy 2.x + Alembic | Migrasi schema terstruktur, mature, type-safe |
| **Dashboard** | Jinja2 + HTMX + Tailwind CSS | Server-side rendering, cepat develop, interaktif tanpa complexity SPA |
| **Crawling** | httpx (async) + BeautifulSoup4 | Async HTTP client + HTML parser yang battle-tested |
| **Domain Check** | RDAP (via rdap.org) + dnspython + tldextract | RDAP lookup (HTTP-based, no dependency), DNS resolution, domain parsing |
| **Historical Data** | Wayback Machine CDX API | Gratis, cukup untuk ambil 3–5 snapshot timestamps |
| **Language Detection** | langdetect | Deteksi bahasa dominan dari snapshot content |
| **Toxicity Flags** | Custom rules + regex patterns | Deteksi parking page, adult content, gambling, pharma, malware indicators |
| **Export** | openpyxl + csv (stdlib) | XLSX dan CSV export |
| **Task Runner** | APScheduler | Background jobs ringan, cukup untuk MVP tanpa Celery |
| **Reverse Proxy** | Caddy | Auto HTTPS/TLS, config minimal |
| **Container** | Docker + Docker Compose | Reproducible environment, mudah deploy ke VPS |

### Kenapa Python, bukan JavaScript?

- Ekosistem crawling/scraping paling matang (httpx, BeautifulSoup, Scrapy).
- Library domain intelligence (python-whois, dnspython) lebih stabil.
- Data processing (pandas, openpyxl) jauh di atas JS.
- NLP/language detection lebih kuat.
- Dependency tree lebih dangkal = supply chain lebih aman.
- Jinja2 auto-escape by default = XSS protection bawaan.
- Tidak ada risiko prototype pollution.
- Lebih cepat prototyping dalam timeline 30 hari.


---


## 2. Output Minggu Pertama yang Bisa Didemokan

### Deliverable M1

1. **Project structure** lengkap dengan Docker Compose (FastAPI + PostgreSQL + Caddy).
2. **Database schema** untuk tabel: `sources`, `crawl_jobs`, `candidate_domains`.
3. **Form input source URL** — owner bisa masukkan URL + label niche via browser.
4. **Crawl engine dasar** — sistem fetch halaman source, extract semua outbound links, deduplikasi root domain.
5. **Dead link detection** — setiap outbound link dicek HTTP status + DNS resolve. Yang dead/unresolved langsung ditandai sebagai kandidat awal (reverse footprint).
6. **Tabel kandidat mentah** — dashboard menampilkan daftar domain hasil crawl dengan status awal (dead/alive/unresolved).

### Demo Scenario

```
Owner buka dashboard → klik "Add Source" → masukkan URL artikel Wikipedia/blog 
→ klik "Crawl" → sistem extract outbound links → cek dead/alive tiap link
→ tabel kandidat muncul dengan kolom: domain, source URL, niche, 
  link status (dead/alive/unresolved), timestamp
```

### Bukti Selesai

- [ ] Demo input source URL via form
- [ ] Dead link / unresolved host terdeteksi dan ditandai otomatis
- [ ] Tabel kandidat mentah ditampilkan di dashboard (dengan status dead/alive)
- [ ] Database terisi data hasil crawl
- [ ] Docker Compose berjalan di VPS


---


## 3. Risiko dan Blocker

### Risiko Tinggi

| Risiko | Dampak | Mitigasi |
|--------|--------|----------|
| **Wayback Machine rate limit / data kosong** | Continuity score tidak bisa dihitung untuk sebagian domain | Fallback: tandai "insufficient data", skor partial, jangan block pipeline |
| **WHOIS rate limiting** | Availability check lambat untuk batch besar (>50 domain sekaligus) | Batch throttling (max 5 req/menit), cache hasil 24 jam, queue system |
| **SSRF via user input URL** | Server bisa diarahkan fetch internal network | Validasi URL ketat: block private IP, localhost, cloud metadata endpoints |

### Risiko Sedang

| Risiko | Dampak | Mitigasi |
|--------|--------|----------|
| **Source page blocking crawler** | Gagal extract links dari beberapa source | Rotate user-agent, respectful delay (2-5 detik), manual input fallback |
| **Domain candidate noise** | Terlalu banyak domain tidak relevan (CDN, social media, tracking) | Blacklist domain umum (google.com, facebook.com, cloudflare.com, dll) |
| **Scope creep** | MVP tidak selesai 30 hari | Strict scope per minggu, fitur tambahan langsung masuk backlog fase 2 |

### Risiko Rendah

| Risiko | Dampak | Mitigasi |
|--------|--------|----------|
| **VPS resource tidak cukup** | App lambat atau crash | Monitoring sederhana, VPS 4 GB RAM cukup untuk MVP |
| **Data export error** | File XLSX corrupt | Unit test untuk export, fallback ke CSV |


---


## 4. Yang Sengaja Tidak Dikerjakan di Fase 1

Berikut fitur yang **secara sadar ditunda** agar MVP selesai dalam 30 hari:

### Tidak Dikerjakan

| Fitur | Alasan Tunda |
|-------|-------------|
| **Backlink intelligence** (jumlah backlink, referring domains, anchor text analysis) | Butuh integrasi API berbayar (Ahrefs/Moz), kompleksitas tinggi |
| **Legal exposure engine** (trademark similarity, UDRP risk) | Butuh dataset trademark + NLP matching yang serius |
| **Monetization fit engine** (estimasi revenue, niche value scoring) | Butuh data historis monetisasi yang belum tersedia |
| **Desktop app** | Web dashboard lebih aman dan cepat develop |
| **Multi-user & permission system** | MVP untuk 1 owner + 1 programmer, tidak perlu role management |
| **Scheduler skala besar** (Celery, Redis queue) | APScheduler cukup untuk volume MVP |
| **Notifikasi otomatis** (email, Telegram, webhook) | Owner cukup cek dashboard |
| **Chart & analytics advance** | Tabel + filter cukup untuk fase 1 |
| **Audit log detail** | Logging dasar cukup, audit trail lengkap di fase 2 |
| **Deep content analysis** (topical relevance scoring, content quality) | Scope terlalu besar untuk 30 hari |
| **Automated purchasing** (API registrar) | Terlalu berisiko untuk MVP, keputusan beli tetap manual |

### Prinsip

> **Fase 1 = tool yang jalan dan berguna.**  
> Bukan platform lengkap. Setiap fitur yang tidak langsung membantu owner membuat keputusan Buy/Review/Discard ditunda ke fase berikutnya.

### Apa yang Akan Jadi di Fase 1

```
Source URL → Crawl → Extract Domains → Check Availability 
→ Check History → Score → Dashboard Shortlist → Export
```

Pipeline ini end-to-end, fungsional, dan cukup untuk owner mulai melakukan review domain secara harian.


---


## 5. Toxicity / Basic Risk Flags

Sesuai goals.md, toxicity flags menjadi komponen terpisah yang feed ke Scoring Engine.

### Flag yang Dicek di Fase 1

| Flag | Cara Deteksi | Label |
|------|-------------|-------|
| **Parking page** | Keyword matching di snapshot content ("buy this domain", "domain for sale", dll) | ⚠️ Parking |
| **Adult content** | Keyword list + regex pattern di title/body snapshot | 🔴 Adult |
| **Gambling/casino** | Keyword list ("casino", "poker", "betting", dll) | 🔴 Gambling |
| **Pharma spam** | Keyword list ("viagra", "cialis", "pharmacy", dll) | 🔴 Pharma |
| **Malware indicators** | Cek Google Safe Browsing API (gratis) jika tersedia, atau keyword ("download free", "crack", dll) | 🔴 Malware |
| **Non-English dominan** | langdetect pada snapshot → bahasa dominan bukan English (jika niche target English) | ⚠️ Language Mismatch |
| **Domain usia sangat muda** | WHOIS creation date < 1 tahun sebelum expire | ⚠️ Young Domain |

### Cara Kerja

1. Setiap domain yang masuk pipeline, snapshot content-nya di-scan terhadap semua flag.
2. Hasilnya disimpan sebagai array of flags di tabel `candidate_domains`.
3. Scoring Engine membaca flags ini: setiap flag menurunkan skor. Flag 🔴 langsung auto-Discard, flag ⚠️ menurunkan skor tapi tetap bisa Review.
4. Dashboard menampilkan flags sebagai badge di domain card agar owner langsung lihat alasan.


---


## 6. Explainable Scoring

Brief menyebut skor harus **explainable** — owner harus paham kenapa domain dapat label tertentu.

### Breakdown Skor

Setiap domain mendapat skor dari 3 komponen:

| Komponen | Bobot | Nilai | Keterangan |
|----------|-------|-------|------------|
| **Availability** | 30% | 0–100 | 100 = available, 50 = expiring soon, 0 = registered aktif |
| **Continuity** | 40% | 0–100 | Berdasarkan jumlah snapshot, konsistensi bahasa, stable content vs drift |
| **Cleanliness** | 30% | 0–100 | 100 = no flags, berkurang per flag. Flag 🔴 = langsung 0 |

**Skor Final** = (Availability × 0.3) + (Continuity × 0.4) + (Cleanliness × 0.3)

### Mapping ke Label

| Skor | Label | Warna |
|------|-------|-------|
| 70–100 | **Buy Candidate** | 🟢 Hijau |
| 40–69 | **Manual Review** | 🟡 Kuning |
| 0–39 | **Discard** | 🔴 Merah |
| Ada flag 🔴 | **Auto-Discard** | 🔴 Merah (regardless of skor) |

### Tampilan di Dashboard

Setiap domain card menampilkan:
- **Skor total** (angka besar)
- **Breakdown bar** (3 komponen visual)
- **Alasan** (teks pendek: "High continuity, clean history" atau "Flagged: parking page detected")
- **Badge flags** jika ada

Owner non-teknis bisa langsung baca: "Domain ini dapat 78 karena available, histori konsisten 5 tahun, tidak ada flag" — tanpa perlu paham teknis.


---


## 7. Progress Tracker & Ritme Kerja

Sesuai brief bagian 8, berikut komitmen ritme kerja:

### Update Progress

| Ritme | Frekuensi | Format |
|-------|-----------|--------|
| **Update programmer** | Minimal 2x per minggu (Senin & Kamis) | Update di progress tracker (docs/progress-tracker.md) |
| **Review owner** | Minimal 1x per minggu (Jumat) | Demo singkat + update status di tracker |
| **Blocker report** | Segera saat ditemukan | Chat / update tracker dengan label BLOCKER |

### Format Progress Tracker

Progress tracker akan dibuat sebagai dokumen hidup (`docs/progress-tracker.md`) dengan format:

```
## Minggu 1 (9–15 Mar 2026)

### Update 1 — Senin 9 Mar
- [x] Setup project structure
- [x] Docker Compose running
- [ ] Database schema — in progress
- Blocker: (tidak ada)

### Update 2 — Kamis 12 Mar
- [x] Database schema selesai
- [x] Form input source URL jalan
- [ ] Crawl engine — in progress
- Blocker: (tidak ada)

### Review Owner — Jumat 13 Mar
- Demo: input URL + tabel kandidat
- Status: ✅ On track / ⚠️ Behind / 🔴 Blocked
- Owner decision: Approve / Revisi
```

Tracker ini menjadi **single source of truth** untuk status project.


---


## 8. Dashboard untuk Owner Non-Teknis

Goals.md menyebut hasil harus "mudah dipantau owner non-teknis". Berikut prinsip desain dashboard:

### Prinsip UX

1. **Tidak ada jargon teknis** — label menggunakan bahasa bisnis: "Buy Candidate", bukan "score >= 70".
2. **Warna sebagai sinyal** — hijau (buy), kuning (review), merah (discard). Owner langsung paham tanpa baca angka.
3. **Skor besar + penjelasan pendek** — setiap domain card menampilkan angka skor + satu kalimat alasan.
4. **Filter 1-klik** — tombol filter status: "Show Buy Candidates", "Show Needs Review", "Show All".
5. **Summary bar di atas** — total kandidat, berapa buy, berapa review, berapa discard. Overview langsung.
6. **Export 1-klik** — tombol "Download Shortlist" langsung generate XLSX/CSV yang rapi.
7. **Tidak perlu login rumit** — basic auth cukup, 1 user, tanpa role management.

### Contoh Layout Dashboard

```
┌─────────────────────────────────────────────────────┐
│  Domain Underwriting Dashboard         [Export XLSX] │
├─────────────────────────────────────────────────────┤
│  Total: 142  │  🟢 Buy: 12  │  🟡 Review: 35  │  🔴 Discard: 95  │
├─────────────────────────────────────────────────────┤
│  Filter: [All] [Buy] [Review] [Discard]  Search: [__________] │
├─────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────┐               │
│  │ example.com              🟢 78  │               │
│  │ Available · 5yr history · Clean │               │
│  │ Niche: Technology               │               │
│  │ [View Detail]                   │               │
│  └──────────────────────────────────┘               │
│  ┌──────────────────────────────────┐               │
│  │ sample.org               🟡 52  │               │
│  │ Expiring · 2yr history · ⚠️ Parking │            │
│  │ Niche: Finance                  │               │
│  │ [View Detail]                   │               │
│  └──────────────────────────────────┘               │
└─────────────────────────────────────────────────────┘
```


---


*Dokumen ini akan diupdate jika ada perubahan keputusan selama development.*
