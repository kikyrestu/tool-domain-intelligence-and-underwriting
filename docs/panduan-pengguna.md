# Domain IQ — Panduan Pengguna

## Cara Akses Dashboard

1. Buka browser, akses: `http://localhost:8000`
2. Login dengan username dan password yang diberikan
3. Dashboard utama akan tampil otomatis

---

## Cara Tambah Source URL

1. Dari dashboard, klik **"+ Add Source"**
2. Isi form:
   - **URL**: masukkan URL halaman yang ingin dicrawl (contoh: `https://news.ycombinator.com`)
   - **Niche**: pilih kategori niche (Technology, Finance, Health, dll)
   - **Notes** (opsional): catatan tambahan tentang sumber ini
3. Klik **Submit**
4. URL akan muncul di daftar Sources

---

## Cara Trigger Crawl

1. Buka halaman **Sources** (klik "Sources" di navbar)
2. Klik **"Run Crawl"** pada source yang diinginkan
3. Banner biru akan muncul: "Processing in background..."
4. Tunggu 15-30 detik, lalu refresh halaman
5. Hasil crawl akan muncul: jumlah link ditemukan, kandidat domain, dan dead links

---

## Cara Baca Shortlist

### Warna Label:
| Label | Warna | Arti |
|-------|-------|------|
| **Available** | 🟢 Hijau | Domain bisa dibeli — dead + available/expired |
| **Watchlist** | 🔵 Biru | Perlu dipantau — expiring soon / dead + registered |
| **Uncertain** | 🟡 Kuning | Data belum cukup — belum ada cek availability |
| **Discard** | 🔴 Merah | Tidak direkomendasikan — masih aktif + registered, atau toxic |

### Skor (0-100):
Skor terdiri dari 3 komponen:
- **Availability (30%)** — Apakah domain bisa dibeli? Available = skor tinggi
- **Continuity (40%)** — Berapa lama domain aktif di internet? History panjang = skor tinggi
- **Cleanliness (30%)** — Apakah domain pernah dipakai untuk konten bermasalah?

### Status Availability:
| Status | Arti |
|--------|------|
| Available | Domain bisa dibeli sekarang |
| Expired | Domain sudah expired, bisa diregistrasi |
| Expiring Soon | Akan expired dalam 30 hari |
| Watchlist | Akan expired dalam 90 hari |
| Registered | Masih didaftarkan oleh pemilik lain |

---

## Cara Filter dan Cari Domain

1. Buka halaman **Candidates** (klik "Candidates" di navbar)
2. Gunakan filter bar di atas tabel:
   - **Search**: ketik nama domain
   - **Availability**: filter berdasarkan status (Available, Registered, dll)
   - **Label**: filter berdasarkan rekomendasi (Available, Watchlist, Uncertain, Discard)
   - **Domain Status**: filter Dead atau Alive
   - **Niche**: filter berdasarkan kategori
   - **Sort**: urutkan berdasarkan Newest, Domain, atau Score
3. Klik **Filter** untuk menerapkan
4. Klik **Reset** untuk mereset semua filter

### Klik Summary Cards:
- Klik card **Available/Watchlist/Uncertain/Discard** di atas tabel untuk langsung filter

---

## Cara Lihat Detail Domain

1. Di halaman Candidates, klik nama domain (teks biru)
2. Halaman detail akan tampil:
   - **Score circle** — skor besar + label warna
   - **Score Breakdown** — bar chart 3 komponen
   - **Toxicity Flags** — badge peringatan (jika ada)
   - **RDAP Info** — registrar, tanggal kadaluarsa, DNS
   - **Historical Continuity** — total snapshot, tahun aktif, bahasa dominan
   - **Owner Notes** — catatan pribadi Anda

---

## Cara Export XLSX / CSV

### Export semua data:
1. Di dashboard atau halaman Candidates, klik **"Export XLSX"** atau **"Export CSV"**
2. File akan otomatis terdownload

### Export dengan filter:
1. Di halaman Candidates, set filter yang diinginkan (misal: Label = Available)
2. Klik **"Export CSV"** di bagian atas
3. Atau buka URL langsung:
   - `http://localhost:8000/export/xlsx?label=Available`
   - `http://localhost:8000/export/csv?label=Available`

### Isi file export:
Domain, Niche, Availability, Link Status, Score, Label, Reason, Registrar, Created, Expires, Days Left, DNS, Snapshots, First Seen, Last Seen, Language, Source URL, Notes, Discovered

File XLSX sudah diformat: header biru bold, baris hijau (Available), biru (Watchlist), kuning (Uncertain), merah (Discard).

---

## Cara Tambah Catatan di Domain

1. Buka halaman detail domain (klik nama domain)
2. Scroll ke bagian **"Owner Notes"**
3. Ketik catatan di text area (contoh: "Hubungi registrar minggu depan")
4. Klik **Save Notes**

---

## Pipeline Lengkap

Urutan operasi yang direkomendasikan:

1. **Add Source** → masukkan URL target
2. **Run Crawl** → sistem menemukan domain dari link yang rusak, dead domain langsung dicek availability via RDAP
3. **Check RDAP** → cek availability untuk domain yang belum dicek
4. **Wayback Audit** → analisis sejarah domain
5. **Score All** → hitung skor dan label
6. **Review shortlist** → filter Available candidates
7. **Export XLSX** → download untuk tim

Tombol aksi tersedia di halaman Source detail dan halaman Candidates.

---

## FAQ

**Q: Berapa lama proses crawl?**
A: 15-60 detik tergantung jumlah link di halaman target.

**Q: Berapa lama RDAP check?**
A: Sekitar 1-3 detik per domain. Dead domain langsung dicek saat crawl.

**Q: Kenapa ada domain yang "check_failed"?**
A: Beberapa domain RDAP server timeout atau tidak support. Domain tetap bisa di-review manual.

**Q: Bisa menambah domain secara manual?**
A: Saat ini domain hanya ditemukan via crawl otomatis. Fitur manual entry bisa ditambahkan di fase 2.

**Q: Bagaimana skor dihitung?**
A: Skor = (Availability × 30%) + (Continuity × 40%) + (Cleanliness × 30%). Label ditentukan berdasarkan status domain (alive/dead) dan availability (available/registered).
