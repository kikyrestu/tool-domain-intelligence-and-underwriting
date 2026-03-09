# Minggu 4 — Dashboard Polish + Export Final + Dokumentasi

**Periode:** 30 Maret – 10 April 2026  
**Goal:** Dashboard lengkap, export XLSX, demo end-to-end, dokumentasi  
**Syarat Done yang dicakup:** #5, #6  
**Prereq:** M3 selesai (scoring + domain card)


---


## Task List

### Day 1-2: Dashboard Shortlist

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 4.1 | Halaman shortlist utama — daftar domain card dengan skor | Shortlist page | 2 jam |
| 4.2 | Filter by label: All / Buy Candidate / Manual Review / Discard | Filter 1-klik | 2 jam |
| 4.3 | Filter by niche | Niche filter | 1 jam |
| 4.4 | Filter by availability status | Status filter | 1 jam |
| 4.5 | Search by domain name | Search box | 1 jam |
| 4.6 | Sort by: skor (tinggi-rendah), domain, tanggal | Sort aktif | 1 jam |
| 4.7 | Pagination | Halaman navigasi | 1 jam |

### Day 2-3: Summary + Homepage

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 4.8 | Summary bar di atas: total, buy count, review count, discard count | Overview | 1 jam |
| 4.9 | Homepage dashboard: ringkasan keseluruhan | Landing page | 2 jam |
| 4.10 | Statistik per niche | Niche breakdown | 1 jam |
| 4.11 | Recent activity: crawl terakhir, domain terbaru | Activity feed | 1 jam |

### Day 3-4: Export XLSX + CSV Final

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 4.12 | Endpoint export XLSX (openpyxl) | File XLSX | 2 jam |
| 4.13 | XLSX formatting: header bold, warna per label, auto-width | File rapi | 2 jam |
| 4.14 | Kolom XLSX: domain, niche, availability, score, label, reason, flags, registrar, created, expires, days_left, source_url, first_seen_wayback, last_seen_wayback, dominant_language | Data lengkap | 1 jam |
| 4.15 | Update CSV export (samakan kolom dengan XLSX) | CSV updated | 1 jam |
| 4.16 | Tombol "Export XLSX" + "Export CSV" di dashboard | Download 1-klik | 1 jam |
| 4.17 | Filter export: export hanya Buy, hanya Review, atau semua | Export filtered | 1 jam |

### Day 4-5: Polish + Edge Cases

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 4.18 | Responsive layout (tablet-friendly minimal) | UI responsive | 2 jam |
| 4.19 | Loading states: saat crawl, saat WHOIS check, saat audit | UX smooth | 1 jam |
| 4.20 | Empty states: "No candidates yet", "No sources added" | UX lengkap | 1 jam |
| 4.21 | Error handling UI: kalau crawl gagal, WHOIS timeout | Error tampil rapi | 1 jam |
| 4.22 | Owner notes: field "catatan" per domain (manual input owner) | Input notes | 2 jam |
| 4.23 | Basic auth: username/password sederhana untuk akses dashboard | Security | 1 jam |

### Day 5-6: Dokumentasi

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 4.24 | Dokumentasi cara pakai (untuk owner non-teknis): | File docs | 3 jam |

**Isi dokumentasi:**
```
1. Cara akses dashboard (URL + login)
2. Cara tambah source URL baru
3. Cara trigger crawl
4. Cara baca shortlist (arti warna + skor)
5. Cara filter dan cari domain
6. Cara export XLSX
7. Cara tambah catatan di domain
8. FAQ sederhana
```

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 4.25 | Dokumentasi teknis (untuk developer/maintenance): | File docs | 2 jam |

**Isi dokumentasi teknis:**
```
1. Cara deploy (Docker Compose)
2. Cara update proxy list
3. Cara tambah domain ke blacklist
4. Cara adjust scoring threshold
5. Cara tambah toxicity keyword baru
6. Struktur database
7. Environment variables
8. Troubleshooting umum
```

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 4.26 | Update progress tracker final | Tracker final | 30 menit |

### Day 7: Demo Final

| # | Task | Output | Estimasi |
|---|------|--------|----------|
| 4.27 | Siapkan demo end-to-end scenario | Demo script | 1 jam |
| 4.28 | Test full pipeline: input → crawl → check → audit → score → dashboard → export | Semua jalan | 2 jam |
| 4.29 | Fix last-minute bugs | Stabil | 2 jam |


---


## Demo Final — Jumat 10 April (atau sebelumnya)

**Scenario end-to-end:**
1. Owner buka dashboard → login
2. Klik "Add Source" → masukkan URL blog teknologi + pilih niche "Technology"
3. Klik "Crawl" → loading indicator → kandidat muncul
4. Sistem otomatis: WHOIS check → Wayback audit → scoring
5. Shortlist tampil: 3 hijau, 8 kuning, 25 merah
6. Filter "Buy Candidate" → 3 domain tampil
7. Klik domain → detail card: skor 92, breakdown, timeline 6 tahun, no flags
8. Tambah catatan: "Hubungi registrar minggu depan"
9. Klik "Export XLSX" → file terdownload
10. Buka file → data lengkap, formatted, siap dibawa ke tim

**Bukti selesai (6 Syarat Done):**
- [ ] ✅ #1 — Owner bisa input source URL + niche via form
- [ ] ✅ #2 — Candidate queue dihasilkan dari crawl
- [ ] ✅ #3 — Availability status tampil (available/registered/expiring)
- [ ] ✅ #4 — Continuity score + red flags + reason tampil
- [ ] ✅ #5 — Shortlist dengan filter Buy/Review/Discard berfungsi
- [ ] ✅ #6 — Dokumentasi cara pakai diserahkan


---


## Risiko Minggu 4

| Risiko | Mitigasi |
|--------|----------|
| Waktu habis untuk polish | Prioritaskan: export > filter > polish visual |
| Edge case scoring | Test dengan data real dari M1-M3, adjust |
| Dokumentasi terlupakan | Schedule khusus Day 5-6 untuk docs |
| Scope creep terakhir | Strict: semua request baru → backlog-fase2.md |
