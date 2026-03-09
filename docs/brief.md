BRIEFING DEVELOPER  
MVP 30 HARI

Digital Asset Underwriting Engine  
untuk reverse footprint, audit historis, dan shortlist domain berkualitas


## Tujuan
Membangun MVP internal untuk menemukan, menilai, dan menampilkan kandidat domain yang layak dibeli atau direview.

## Output utama
Dashboard internal + progress tracker + shortlist domain dengan status Buy Candidate / Manual Review / Discard.

## Stack preferensi
Python-first, web dashboard internal sederhana, database ringan, deployment aman, bukan desktop app pada fase 1.

## Batas fase 1
Fokus pada discovery, availability, historical continuity dasar, scoring awal, dan tracking owner-programmer.



# 1. Objective

Membangun sistem internal yang dapat menemukan broken-link domain candidates dari source terpilih, memvalidasi availability, membaca histori dasar domain, lalu memberi skor awal yang explainable sehingga owner hanya melihat domain yang layak direview.

MVP 30 hari tidak mengejar platform penuh. Fokusnya adalah tool kerja internal yang usable, stabil, dan mudah ditambah modul pada fase berikutnya.


# 2. Scope MVP 30 Hari

- Input daftar source URL dan label niche secara manual.
- Crawl source page lalu ekstrak outbound links dan root domain.
- Tandai dead link / unresolved host untuk kandidat awal.
- Cek availability atau status actionable sederhana untuk kandidat.
- Tarik snapshot historis dasar untuk 3–5 titik waktu jika tersedia.
- Hitung continuity score dasar dan tampilkan red flags awal.
- Simpan semua kandidat, status, skor, dan catatan ke database.
- Tampilkan dashboard internal sederhana untuk shortlist dan review queue.
- Sediakan export CSV/XLSX untuk shortlist hasil harian atau mingguan.


# 3. Fitur Wajib

| Modul | Minimal yang harus jadi | Output | Prioritas |
|------|-------------------------|-------|-----------|
| Source Discovery | Input source URL, crawl sederhana, ekstrak outbound links, dedup root domain | Daftar kandidat mentah | Wajib |
| Availability Check | Status tersedia / watchlist / tidak actionable | Queue yang bisa ditindaklanjuti | Wajib |
| Historical Continuity | Ambil snapshot dasar, bahasa dominan, drift kasar, skor dasar | Continuity report | Wajib |
| Scoring Engine | Gabungkan skor continuity + flag sederhana + status | Buy / Review / Discard | Wajib |
| Dashboard Internal | Tampilan daftar kandidat, filter status, detail domain card | Review harian | Wajib |
| Export | CSV/XLSX export dari shortlist | File hasil | Wajib |


# 4. Fitur Tunda

- Backlink intelligence yang matang dan detail per referring domain.
- Legal exposure engine yang serius dengan trademark similarity.
- Monetization fit engine yang cerdas dan semi-otomatis.
- Desktop app lokal.
- Scheduler skala besar, queue worker kompleks, multi-user permission.
- Integrasi notifikasi otomatis, chart advance, dan audit log tingkat lanjut.


# 5. Arsitektur Sederhana

| Komponen | Pilihan fase 1 |
|---------|----------------|
| Frontend | Web dashboard internal sederhana |
| Backend | Python web app (mis. FastAPI/Flask) |
| Database | SQLite atau PostgreSQL ringan |
| Jobs | Script / worker sederhana untuk crawl dan audit |
| Storage | Folder project + export file mingguan |
| Owner View | Dashboard ringkas + sheet progress bersama |

Catatan owner: fase 1 tidak perlu desktop app. Lebih aman dan cepat bila MVP dibuat sebagai web dashboard internal yang bisa dibuka dari browser.


# 6. Deliverable Mingguan

| Minggu | Target utama | Bukti selesai | Status review owner |
|------|--------------|---------------|---------------------|
| M1 | Setup proyek, struktur database, input source URL, crawl awal, dedup root domain | Demo input source + tabel kandidat mentah | Approve / Revisi |
| M2 | Availability/status engine + penyimpanan kandidat actionable | Daftar actionable domains + export dasar | Approve / Revisi |
| M3 | Historical continuity dasar + scoring awal + detail domain card | Skor continuity + red flags + status awal | Approve / Revisi |
| M4 | Dashboard shortlist, filter status, export final, dokumentasi penggunaan | Demo end-to-end + file dokumentasi singkat | Approve / Revisi |


# 7. Definisi Selesai (Done)

- Owner bisa input source URL dan niche melalui cara yang jelas.
- Sistem bisa menghasilkan candidate queue dari source terpilih.
- Sistem bisa menampilkan minimal status availability sederhana.
- Sistem bisa memberi continuity score dan red flags dasar.
- Sistem bisa menampilkan shortlist dengan filter Buy / Review / Discard.
- Programmer menyerahkan dokumentasi cara pakai singkat dan cara update data.


# 8. Flow Owner dan Programmer

| Peran | Tanggung jawab |
|------|----------------|
| Owner | Menentukan tujuan, niche target, prioritas mingguan, dan approval tiap milestone. |
| Programmer | Mengerjakan task per minggu, update progress tracker, melaporkan blocker, dan demo hasil. |
| Ritme | Update progress minimal 2 kali per minggu. Review owner minimal 1 kali per minggu. |
| Dokumen bersama | Briefing disimpan tetap; progress tracker menjadi dokumen hidup untuk update harian/mingguan. |


# 9. Pertanyaan yang Harus Dijawab Programmer di Hari Pertama

- Stack final apa yang dipilih untuk backend, database, dan dashboard?
- Output minggu pertama yang bisa didemokan apa?
- Bagian mana yang dianggap risiko atau blocker?
- Apa yang sengaja tidak dikerjakan di fase 1 agar MVP tetap selesai 30 hari?

Dokumen ini adalah briefing eksekusi MVP 30 hari untuk 1 developer. Versi owner-friendly dan tracker progress terpisah ada pada spreadsheet pendamping.