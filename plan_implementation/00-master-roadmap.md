# Master Roadmap — MVP 30 Hari

**Project:** Digital Asset Underwriting Engine  
**Timeline:** 9 Maret – 10 April 2026  
**Developer:** 1 orang  
**Tujuan akhir:** Owner bisa input URL → sistem otomatis proses → dashboard shortlist + export XLSX


---


## Definisi Selesai (6 Syarat Wajib)

| # | Syarat | Modul Terkait |
|---|--------|--------------|
| 1 | Owner bisa input source URL dan niche melalui cara yang jelas | Source Discovery |
| 2 | Sistem bisa menghasilkan candidate queue dari source terpilih | Source Discovery |
| 3 | Sistem bisa menampilkan minimal status availability sederhana | Availability Check |
| 4 | Sistem bisa memberi continuity score dan red flags dasar | Historical Continuity + Scoring |
| 5 | Sistem bisa menampilkan shortlist dengan filter Buy / Review / Discard | Dashboard + Scoring |
| 6 | Programmer menyerahkan dokumentasi cara pakai dan cara update data | Dokumentasi |


---


## Timeline Overview

```
Minggu 1 (9-15 Mar)     Minggu 2 (16-22 Mar)     Minggu 3 (23-29 Mar)     Minggu 4 (30 Mar-10 Apr)
┌──────────────────┐    ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ FOUNDATION       │    │ AVAILABILITY     │     │ HISTORY+SCORING  │     │ DASHBOARD+POLISH │
│                  │    │                  │     │                  │     │                  │
│ • Project setup  │    │ • WHOIS engine   │     │ • Wayback engine │     │ • Filter & search│
│ • Database       │    │ • DNS check      │     │ • Language detect │     │ • Domain card    │
│ • Input form     │    │ • Status tagging │     │ • Toxicity flags │     │ • Export XLSX    │
│ • Crawl engine   │    │ • Export CSV     │     │ • Scoring engine │     │ • Dokumentasi    │
│ • Dead link      │    │ • Dashboard v1   │     │ • Dashboard v2   │     │ • Demo final     │
│ • Tabel kandidat │    │                  │     │                  │     │                  │
└──────────────────┘    └──────────────────┘     └──────────────────┘     └──────────────────┘
     Demo M1 ▲               Demo M2 ▲               Demo M3 ▲               Demo Final ▲
```


---


## Ritme Kerja

| Hari | Aktivitas |
|------|-----------|
| **Senin** | Update progress tracker (#1) |
| **Selasa–Rabu** | Development |
| **Kamis** | Update progress tracker (#2) |
| **Jumat** | Demo ke owner + review |
| **Weekend** | Buffer / catch-up jika ada blocker |


---


## Pipeline yang Harus Jadi di Akhir

```
Owner input URL + Niche
        ↓
[Source Discovery] Crawl → Extract links → Dedup → Dead link filter
        ↓
[Availability Check] WHOIS → DNS → Status tagging
        ↓
[Historical Continuity] Wayback → Language → Toxicity → Drift
        ↓
[Scoring Engine] Gabungkan semua → Skor explainable → Label
        ↓
[Dashboard] Tampilkan shortlist → Filter → Domain card → Detail
        ↓
[Export] Download XLSX / CSV
```


---


## Yang TIDAK Dikerjakan di Fase 1

- Backlink intelligence (Ahrefs-level)
- Legal/trademark engine
- Monetization prediction
- Desktop app
- Multi-user/permission
- Auto notification (email/Telegram)
- Advanced charts
- Celery/Redis queue

Ide baru → langsung masuk `docs/backlog-fase2.md`


---


*Dokumen ini adalah panduan utama. Detail task per minggu ada di file terpisah.*
