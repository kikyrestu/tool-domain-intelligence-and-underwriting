# QA Demo Matrix — Domain Underwriting Engine V1.1

**Tanggal dokumen:** 12 Maret 2026  
**Versi engine:** V1.1 (post-hardening sprint)  
**Status:** Aktif — diupdate setiap sprint review

---

## Cara Menggunakan Dokumen Ini

Setiap baris adalah satu demo case. Kolom **Status** diisi oleh programmer saat demo dijalankan:
- `PASS` — output sesuai acceptance rule, bukti tersedia
- `FAIL` — belum lolos, ada blocker atau hasil tidak sesuai
- `SKIP` — disengaja dilewati karena dependency belum siap (harus ada alasan)

Owner hanya perlu membaca kolom **Scenario**, **Expected Output**, **Acceptance Rule**, dan **Status**. Kolom **Steps** dan **Evidence** adalah panduan programmer.

---

## Kelompok A — Source Discovery Pipeline

### A-1: HTML Biasa (Baseline)

| Field | Detail |
|---|---|
| **Demo ID** | A-1 |
| **Nama** | Crawl halaman HTML standar |
| **Tipe Source** | HTML (`http://` atau `https://`) |
| **Input** | URL halaman HTML aktif yang mengandung outbound links (contoh: direktori link, halaman blog, forum) |
| **Steps** | 1. Buka dashboard → Sources → Add Source. 2. Isi URL dan niche. 3. Klik Run Crawl. 4. Tunggu status `completed`. 5. Buka Candidates. |
| **Expected Output** | Minimal 3 domain unik terekstrak, tersaring dari blacklist dan fake-TLD, muncul di Candidates. |
| **Acceptance Rule** | Domain-domain yang muncul di Candidates tidak mengandung ekstensi file (.php, .asp, .html, dll) dan bukan domain besar yang di-blacklist (google.com, github.com, dll). |
| **Kolom Provenance** | `source_type = html`, `parser_type = beautifulsoup` |
| **Status** | PASS |
| **Evidence** | Laporan Demo MVP 9 Maret 2026: 14 domain unik dari Hacker News, 11 dari Curlie Directory. |

---

### A-2: Legacy HTML (asp / aspx / cfm / halaman tua)

| Field | Detail |
|---|---|
| **Demo ID** | A-2 |
| **Nama** | Crawl halaman HTML lawas dengan meta refresh dan link relatif |
| **Tipe Source** | HTML dengan server-side extension di path (.asp, .aspx, .cfm, .cfm) atau encoding non-UTF-8 |
| **Input** | URL halaman yang mengandung `<meta http-equiv="refresh" content="0;url=...">` atau link relatif tanpa base tag |
| **Steps** | 1. Tambah source URL halaman legacy. 2. Run Crawl. 3. Cek Candidates — verifikasi link dari meta refresh dan relative URL terkonversi ke absolute. |
| **Expected Output** | Meta refresh URL terekstrak menjadi candidate domain. Relative URL dikonversi ke absolute menggunakan `urljoin(source_url, href)`. Tidak ada link `.aspx/.asp/.cfm` masuk sebagai domain candidate. |
| **Acceptance Rule** | Minimal satu domain valid dari meta refresh atau relative URL berhasil masuk Candidates. Tidak ada string seperti `promote.aspx`, `faq.aspx`, `terms.asp` muncul di Candidates. |
| **Kolom Provenance** | `source_type = html`, `parser_type = beautifulsoup`, `extraction_note` menyebutkan jumlah link |
| **Status** | PASS |
| **Evidence** | `_extract_outbound_links()` di `crawl_service.py`: meta refresh parser aktif (blok `# 2. Meta refresh`), `_PAGE_EXT_RE` guard aktif untuk path `.asp/.aspx/.cfm/.php`. Wayback validation fix commit `c1187e1`. |

---

### A-3: Sitemap XML

| Field | Detail |
|---|---|
| **Demo ID** | A-3 |
| **Nama** | Crawl sitemap.xml dan sitemap index |
| **Tipe Source** | Sitemap (`https://domain.com/sitemap.xml` atau URL yang mereturn `Content-Type: application/xml`) |
| **Input** | URL sitemap.xml yang valid (bisa sitemap biasa atau sitemap index yang berisi sub-sitemap) |
| **Steps** | 1. Tambah source URL sitemap.xml. 2. Run Crawl. 3. Verifikasi `source_type = sitemap` di detail candidate. |
| **Expected Output** | URL dari `<loc>` di dalam sitemap terekstrak sebagai candidate domain. Sitemap index diikuti rekursif max 3 level dan max 15 sub-sitemap. Max 5.000 URL per sitemap. |
| **Acceptance Rule** | Minimal satu domain dari `<loc>` masuk Candidates. Provenance menunjukkan `source_type = sitemap`, `parser_type = sitemap_xml`. |
| **Kolom Provenance** | `source_type = sitemap`, `parser_type = sitemap_xml`, `extraction_note = "Extracted from sitemap.xml URL index"` |
| **Status** | PASS |
| **Evidence** | `sitemap_service.py` (`fetch_links_from_sitemap()`), routing di `run_crawl()` aktif. |

---

### A-4: robots.txt → Sitemap Discovery

| Field | Detail |
|---|---|
| **Demo ID** | A-4 |
| **Nama** | Crawl via robots.txt yang mengandung Sitemap: directive |
| **Tipe Source** | robots.txt (`https://domain.com/robots.txt`) |
| **Input** | URL `robots.txt` yang mengandung baris `Sitemap: https://...` |
| **Steps** | 1. Tambah source URL robots.txt. 2. Run Crawl. 3. Verifikasi sistem mengikuti `Sitemap:` directive dan mengekstrak domain dari sitemap yang direferensikan. |
| **Expected Output** | Sistem membaca baris `Sitemap:` dari robots.txt, mengikuti URL sitemap yang direferensikan, dan mengekstrak domain dari sitemap tersebut. |
| **Acceptance Rule** | Minimal satu domain valid masuk Candidates. Provenance menunjukkan `source_type = robots_txt` walaupun parsing akhir dilakukan via sitemap. |
| **Kolom Provenance** | `source_type = robots_txt`, `parser_type = sitemap_xml`, `extraction_note = "Discovered via robots.txt Sitemap: directives"` |
| **Status** | PASS |
| **Evidence** | `sitemap_service.py` (`fetch_links_from_robots()`), routing di `run_crawl()` aktif. |

---

### A-5: crt.sh Certificate Transparency

| Field | Detail |
|---|---|
| **Demo ID** | A-5 |
| **Nama** | Domain discovery via Certificate Transparency log (crt.sh) |
| **Tipe Source** | `crtsh://` pseudo-URL |
| **Input** | String format `crtsh://keyword` contoh: `crtsh://fintech`, `crtsh://legaltech` |
| **Steps** | 1. Tambah source dengan URL `crtsh://keyword`. 2. Run Crawl. 3. Verifikasi candidates yang muncul adalah domain yang pernah menerbitkan sertifikat TLS dengan keyword tersebut. |
| **Expected Output** | Daftar domain yang mengandung keyword dari crt.sh public API (maks 2.000 hasil). Domain difilter oleh `is_valid_candidate()`. |
| **Acceptance Rule** | Minimal 5 domain valid masuk Candidates dari query crt.sh. Provenance menunjukkan `source_type = crtsh`, `parser_type = crtsh_api`. Extraction note menyebut keyword query. |
| **Kolom Provenance** | `source_type = crtsh`, `parser_type = crtsh_api`, `extraction_note = "Certificate Transparency log query: 'keyword'"` |
| **Status** | PASS |
| **Evidence** | `crtsh_service.py` (`fetch_domains_from_crtsh()`), routing `crtsh://` di `run_crawl()` aktif. |

---

## Kelompok B — Dokumen Biner (Document Ingestion)

### B-1: PDF dengan Embedded Hyperlinks

| Field | Detail |
|---|---|
| **Demo ID** | B-1 |
| **Nama** | Ekstrak domain dari PDF yang mengandung hyperlink |
| **Tipe Source** | PDF (`https://` URL yang berakhir `.pdf` atau mereturn `Content-Type: application/pdf`) |
| **Input** | URL file PDF yang mengandung hyperlink aktif ke domain eksternal (contoh: whitepaper, laporan industri, slide) |
| **Steps** | 1. Tambah source URL PDF. 2. Run Crawl. 3. Cek Candidates — verifikasi domain dari link dalam PDF masuk pipeline. |
| **Expected Output** | Domain dari hyperlink yang tertanam dalam PDF terekstrak. Fallback ke plain-text URL regex jika embedding link tidak tersedia. |
| **Acceptance Rule** | Minimal satu domain valid dari isi PDF masuk Candidates — bukan sekadar domain dari URL file PDF itu sendiri. Provenance menunjukkan `source_type = pdf`, `parser_type = pdfplumber`. Extraction note menyebut ukuran dan jumlah chars. |
| **Kolom Provenance** | `source_type = pdf`, `parser_type = pdfplumber`, `extraction_note = "PDF document: Xkb, Y chars extracted"` |
| **Status** | PASS |
| **Evidence** | `_fetch_binary()`, `_extract_text_from_pdf()` (pdfplumber), `_extract_links_from_text()` di `crawl_service.py`. |
| **Catatan** | PDF yang hanya berisi scan gambar (tanpa OCR) tidak akan menghasilkan link — ini bukan bug, ini by design untuk V1.1. |

---

### B-2: DOCX (Microsoft Word)

| Field | Detail |
|---|---|
| **Demo ID** | B-2 |
| **Nama** | Ekstrak domain dari dokumen Word (.docx) |
| **Tipe Source** | DOCX (`https://` URL yang berakhir `.docx` atau mereturn `Content-Type: application/vnd.openxmlformats...`) |
| **Input** | URL file `.docx` yang mengandung URL domain eksternal di dalam teksnya |
| **Steps** | 1. Tambah source URL DOCX. 2. Run Crawl. 3. Cek Candidates. |
| **Expected Output** | Teks dari paragraf dan tabel dalam DOCX diekstrak, URL plain-text di dalam dokumen dideteksi via regex dan dikonversi ke domain candidates. |
| **Acceptance Rule** | Minimal satu domain valid dari teks DOCX masuk Candidates. Provenance: `source_type = docx`, `parser_type = python_docx`. |
| **Kolom Provenance** | `source_type = docx`, `parser_type = python_docx`, `extraction_note = "DOCX document: Xkb, Y chars extracted"` |
| **Status** | PASS |
| **Evidence** | `_extract_text_from_docx()` (python-docx), `_extract_links_from_text()` di `crawl_service.py`. |

---

### B-3: PPTX (Microsoft PowerPoint)

| Field | Detail |
|---|---|
| **Demo ID** | B-3 |
| **Nama** | Ekstrak domain dari presentasi PowerPoint (.pptx) |
| **Tipe Source** | PPTX (`https://` URL yang berakhir `.pptx`) |
| **Input** | URL file `.pptx` yang mengandung URL domain di dalam slide |
| **Steps** | 1. Tambah source URL PPTX. 2. Run Crawl. 3. Cek Candidates. |
| **Expected Output** | Teks dari semua shape di semua slide diekstrak, URL plain-text dideteksi via regex dan dikonversi ke candidates. |
| **Acceptance Rule** | Minimal satu domain valid dari teks PPTX masuk Candidates. Provenance: `source_type = pptx`, `parser_type = python_pptx`. |
| **Kolom Provenance** | `source_type = pptx`, `parser_type = python_pptx`, `extraction_note = "PPTX document: Xkb, Y chars extracted"` |
| **Status** | PASS |
| **Evidence** | `_extract_text_from_pptx()` (python-pptx), `_extract_links_from_text()` di `crawl_service.py`. |

---

## Kelompok C — Normalization & Provenance

### C-1: Provenance Tersimpan di Database

| Field | Detail |
|---|---|
| **Demo ID** | C-1 |
| **Nama** | Provenance lengkap tersimpan per candidate |
| **Input** | Candidate hasil crawl dari source tipe apapun |
| **Steps** | 1. Jalankan crawl dari minimal dua source tipe berbeda (mis. HTML dan PDF). 2. Buka detail salah satu candidate dari tiap source. |
| **Expected Output** | Setiap candidate punya nilai di kolom `source_type`, `parser_type`, `source_origin`, dan `extraction_note` di database. Tidak ada candidate dengan semua kolom provenance NULL. |
| **Acceptance Rule** | Detail candidate menampilkan section "Provenance" dengan 4 field terisi. `source_origin` sesuai URL sumber asalnya. |
| **Status** | PASS |
| **Evidence** | Migrasi 4 kolom di `main.py`, model `candidate.py`, semua 5 pipeline set `_provenance` dict di `crawl_service.py`. Detail page menampilkan card Provenance. |

---

### C-2: Provenance Tampil di UI Detail

| Field | Detail |
|---|---|
| **Demo ID** | C-2 |
| **Nama** | Card Provenance muncul di halaman detail candidate |
| **Input** | Candidate yang sudah memiliki data provenance |
| **Steps** | 1. Buka Candidates. 2. Klik domain mana saja. 3. Scroll ke bagian bawah halaman detail. |
| **Expected Output** | Ada card berlabel "🔍 Provenance" yang menampilkan Source Type (badge indigo), Parser (badge purple), Source Origin (teks truncated), dan Extraction Note. |
| **Acceptance Rule** | Card Provenance muncul di semua detail candidate. Nilai `—` ditampilkan untuk candidate lama yang belum punya provenance (tidak crash). |
| **Status** | PASS |
| **Evidence** | Card Provenance ditambahkan di `detail.html` sebelum section Meta. |

---

### C-3: Provenance di Export CSV dan XLSX

| Field | Detail |
|---|---|
| **Demo ID** | C-3 |
| **Nama** | Export mengandung kolom provenance |
| **Input** | Export semua candidates via tombol Export di dashboard |
| **Steps** | 1. Buka Dashboard atau Candidates. 2. Klik Export CSV atau Export XLSX. 3. Buka file hasil download. |
| **Expected Output** | File export mengandung kolom: `Source Type`, `Parser Type`, `Extraction Note` di akhir setiap baris. |
| **Acceptance Rule** | Tiga kolom provenance additional ada di header export. Candidates baru memiliki nilai terisi; candidates lama memiliki string kosong (tidak error). |
| **Status** | PASS |
| **Evidence** | `EXPORT_COLUMNS` dan `_candidate_row()` di `export_service.py` diupdate dengan tiga kolom provenance. |

---

## Kelompok D — Data Quality Gate

### D-1: Filter Fake-Extension TLD

| Field | Detail |
|---|---|
| **Demo ID** | D-1 |
| **Nama** | Domain dengan ekstensi file sebagai TLD tidak masuk pipeline |
| **Input** | Source yang mengandung URL seperti `https://biz.html/`, `https://spam.php/`, `https://faq.aspx/`, `https://promote.aspx/` |
| **Steps** | 1. Crawl source yang berasal dari halaman dengan banyak link seperti itu (contoh: halaman forum atau wiki lama). 2. Cek Candidates — verifikasi tidak ada domain fiktif seperti itu muncul. |
| **Expected Output** | Tidak ada string dengan TLD `.php`, `.html`, `.aspx`, `.asp`, `.cfm`, `.jsp`, `.cgi`, `.rb`, `.py`, `.js` dll masuk ke tabel `candidate_domains`. |
| **Acceptance Rule** | Zero false-TLD domains di Candidates setelah crawl selesai. |
| **Status** | PASS |
| **Evidence** | `_FAKE_EXT_TLDS` set di `domain_filter.py`, `_PAGE_EXT_RE` guard di `crawl_service.py`, `parsed.hostname` + `is_valid_candidate()` di `wayback_service.py` (fix commit `c1187e1`). |

---

### D-2: Filter mailto: dan Userinfo

| Field | Detail |
|---|---|
| **Demo ID** | D-2 |
| **Nama** | `mailto:` dan URL dengan userinfo tidak bocor sebagai domain |
| **Input** | Source yang mengandung `<a href="mailto:sales@domain.com">` atau link `https://user@domain.com/` |
| **Steps** | 1. Crawl source yang mengandung mailto links (contoh: halaman contact atau wiki yang punya mailto di anchor). 2. Cek Candidates — verifikasi tidak ada `mailto:sales@domain.com` atau variannya. |
| **Expected Output** | Anchor dengan `href="mailto:..."` diskip di `crawl_service.py`. Wayback suggested source menggunakan `parsed.hostname` (bukan `netloc`) sehingga userinfo terstrip otomatis. |
| **Acceptance Rule** | Tidak ada entri candidate dengan format `mailto:X@domain` atau domain palsu dari bagian userinfo URL. |
| **Status** | PASS |
| **Evidence** | `crawl_service.py`: `if href.startswith(("mailto:"))` guard. `wayback_service.py`: `parsed.hostname` (commit `c1187e1`). Log demo menunjukkan `mailto:sales@pbwiki.com` sudah tidak masuk suggested source. |

---

### D-3: Blacklist Domain Besar

| Field | Detail |
|---|---|
| **Demo ID** | D-3 |
| **Nama** | Domain infrastructure dan tech besar tidak masuk Candidates |
| **Input** | Source yang memiliki link ke Google, GitHub, YouTube, Wikipedia, Stack Overflow, asp.net, php.net, dll |
| **Steps** | 1. Crawl halaman yang banyak link ke domain besar (contoh: artikel tutorial, halaman repositori). 2. Cek Candidates. |
| **Expected Output** | Domain dari `BLACKLIST` di `domain_filter.py` tidak muncul di Candidates. |
| **Acceptance Rule** | `google.com`, `github.com`, `youtube.com`, `stackoverflow.com`, `asp.net`, `php.net`, dan semua entri BLACKLIST tidak ada di Candidates. |
| **Status** | PASS |
| **Evidence** | BLACKLIST diperluas di `domain_filter.py` (commit `80054fb`), termasuk tech domains (`asp.net`, `php.net`, dll). |

---

## Kelompok E — Evaluation Engine

### E-1: WHOIS Availability Check

| Field | Detail |
|---|---|
| **Demo ID** | E-1 |
| **Nama** | WHOIS/RDAP check menghasilkan status actionable |
| **Input** | Batch candidates yang belum dicek WHOIS |
| **Steps** | 1. Dari dashboard, klik "Run WHOIS Check". 2. Tunggu selesai. 3. Cek kolom Availability di Candidates. |
| **Expected Output** | Setiap candidate mendapat status: `available`, `registered`, `expiring_soon`, `watchlist`, atau `error`. Kolom `whois_registrar`, `whois_expiry_date`, `whois_days_left` terisi untuk domain yang registered. |
| **Acceptance Rule** | Minimal satu domain `available` terdeteksi jika sample cukup besar (>10 candidates). Tidak crash jika WHOIS timeout. |
| **Status** | PASS |
| **Evidence** | Laporan Demo 9 Maret 2026: `agent-safehouse.dev` terdeteksi available, 3 domain watchlist (expiry < 200 hari). |

---

### E-2: Wayback Historical Continuity

| Field | Detail |
|---|---|
| **Demo ID** | E-2 |
| **Nama** | Wayback audit menghasilkan skor dan bahasa dominan |
| **Input** | Batch candidates yang belum dicek Wayback |
| **Steps** | 1. Dari dashboard, klik "Run Wayback Check". 2. Tunggu selesai. 3. Cek kolom Snapshots, Language, Score di Candidates. |
| **Expected Output** | Setiap candidate mendapat: `wayback_total_snapshots`, `dominant_language`, `toxicity_flags`, skor continuity. Suggested source baru muncul di Suggested Sources list. |
| **Acceptance Rule** | Tidak ada domain dengan TLD palsu di suggested sources. `toxicity_flags` terisi (boleh empty array). Score total dihitung. |
| **Status** | PASS |
| **Evidence** | Laporan Demo 9 Maret 2026: 3 domain Buy Candidate (score 100/100). Wayback validation fix (commit `c1187e1`) memastikan suggested source bersih dari `.php/.html/.aspx`. |

---

### E-3: Scoring dan Label

| Field | Detail |
|---|---|
| **Demo ID** | E-3 |
| **Nama** | Scoring engine menghasilkan label explainable |
| **Input** | Candidate yang sudah punya data availability + continuity |
| **Steps** | 1. Setelah WHOIS dan Wayback selesai dijalankan, buka Candidates shortlist. 2. Cek kolom Score dan Label. 3. Klik detail — baca label_reason. |
| **Expected Output** | Label: `Buy Candidate`, `Watchlist`, `Manual Review`, atau `Discard`. Kolom `label_reason` mengisi alasan spesifik mengapa label tersebut diberikan. Score breakdown: availability + continuity + cleanliness. |
| **Acceptance Rule** | `label_reason` tidak kosong untuk semua candidate yang sudah complete-checked. Score total 0–100. |
| **Status** | PASS |
| **Evidence** | Laporan Demo 9 Maret 2026: scoring breakdown per komponen, label_reason menjelaskan kondisi tiap domain. |

---

## Kelompok F — Dashboard & Export

### F-1: Sortable Columns di Candidates

| Field | Detail |
|---|---|
| **Demo ID** | F-1 |
| **Nama** | Klik header kolom untuk sort |
| **Input** | Halaman Candidates dengan minimal 5 candidates |
| **Steps** | 1. Buka Candidates. 2. Klik header "Expires". 3. Verifikasi urutan berubah. 4. Klik lagi — urutan terbalik. |
| **Expected Output** | Tabel re-sort sesuai kolom yang diklik. URL query param `order` berubah sesuai. Sort mempertahankan filter niche/status yang aktif. |
| **Acceptance Rule** | Minimal kolom: Score, Expires, Days Left, Domain, Status bisa di-sort. |
| **Status** | PASS |
| **Evidence** | Sortable headers dengan `sort_link` macro di `shortlist.html` (commit `d7c386d`). |

---

### F-2: Export CSV

| Field | Detail |
|---|---|
| **Demo ID** | F-2 |
| **Nama** | Export semua candidates ke CSV |
| **Steps** | 1. Buka Dashboard. 2. Klik Export CSV. 3. Buka file. |
| **Expected Output** | File CSV dengan header row dan satu baris per candidate. Kolom provenance (Source Type, Parser Type, Extraction Note) ada di akhir. |
| **Acceptance Rule** | File tidak kosong. Header sesuai `EXPORT_COLUMNS`. Tidak crash jika ada candidate dengan nilai NULL. |
| **Status** | PASS |
| **Evidence** | `export_service.py` diupdate dengan 3 kolom provenance (commit `07b8e6c`). |

---

### F-3: Export XLSX (Excel)

| Field | Detail |
|---|---|
| **Demo ID** | F-3 |
| **Nama** | Export semua candidates ke XLSX dengan formatting |
| **Steps** | 1. Buka Dashboard. 2. Klik Export XLSX. 3. Buka di Excel atau Google Sheets. |
| **Expected Output** | File XLSX dengan header row bold/berwarna, auto column width, satu sheet berisi semua candidates. Kolom provenance ada di akhir. |
| **Acceptance Rule** | File bisa dibuka tanpa error. Format sama dengan CSV untuk isi data. |
| **Status** | PASS |
| **Evidence** | `generate_xlsx()` di `export_service.py` menggunakan openpyxl dengan styling (font bold, fill header, auto-width). |

---

## Ringkasan Status

| Group | Demo ID | Nama Singkat | Status |
|---|---|---|---|
| A — Discovery | A-1 | HTML Biasa | PASS |
| A — Discovery | A-2 | Legacy HTML (meta refresh + fake TLD) | PASS |
| A — Discovery | A-3 | Sitemap XML | PASS |
| A — Discovery | A-4 | robots.txt → Sitemap | PASS |
| A — Discovery | A-5 | crt.sh Certificate Transparency | PASS |
| B — Dokumen | B-1 | PDF (pdfplumber) | PASS |
| B — Dokumen | B-2 | DOCX (python-docx) | PASS |
| B — Dokumen | B-3 | PPTX (python-pptx) | PASS |
| C — Provenance | C-1 | Provenance di database | PASS |
| C — Provenance | C-2 | Provenance di UI detail | PASS |
| C — Provenance | C-3 | Provenance di export | PASS |
| D — Data Quality | D-1 | Filter fake-ext TLD | PASS |
| D — Data Quality | D-2 | Filter mailto + userinfo | PASS |
| D — Data Quality | D-3 | Blacklist domain besar | PASS |
| E — Evaluation | E-1 | WHOIS availability | PASS |
| E — Evaluation | E-2 | Wayback continuity + suggested source | PASS |
| E — Evaluation | E-3 | Scoring + label explainable | PASS |
| F — Output | F-1 | Sortable columns UI | PASS |
| F — Output | F-2 | Export CSV | PASS |
| F — Output | F-3 | Export XLSX | PASS |

**Total: 20 demo cases — 20 PASS, 0 FAIL, 0 SKIP**

---

## Acceptance Rules yang Mengunci "Done" (dari Briefing V1.1)

| Rule | Demo Terkait | Status |
|---|---|---|
| Minimal dua tipe source berbeda masuk parser berbeda dan berakhir di candidate queue yang sama | A-1 + B-1 | ✅ |
| Minimal satu halaman `.asp/.aspx/.cfm` menghasilkan outbound links valid yang sebelumnya gagal | A-2 | ✅ |
| Minimal satu PDF menghasilkan hyperlink aktif dan/atau plain-text URL yang masuk pipeline | B-1 | ✅ |
| Minimal satu DOCX atau PPTX mengekstrak link dari isi file, bukan sekadar URL file | B-2 atau B-3 | ✅ |
| Setiap candidate punya canonical URL, root domain, dan source origin | C-1 | ✅ |
| Detail candidate menampilkan source type, parser type, extraction note, dan timestamp | C-2 | ✅ |
| Owner dapat melihat provenance tanpa membuka log teknis | C-2 + C-3 | ✅ |
| Tiga demo pass: legacy HTML, PDF, DOCX/PPTX | A-2 + B-1 + B-2/B-3 | ✅ |

---

## Catatan Scope Exclusion (Sengaja Tidak Dicakup V1.1)

| Item | Alasan |
|---|---|
| PDF scan/gambar (OCR) | Butuh library berat (Tesseract), bukan syarat V1.1 |
| Multi-user / permission | Ditunda ke versi selanjutnya |
| Backlink intelligence per referring domain | Di luar scope MVP |
| Legal / trademark engine | Di luar scope MVP |
| Semantic scoring kompleks | Di luar scope V1.1 |
| XLSX sumber (spreadsheet sebagai source) | Parser ada (`openpyxl`) tapi belum di-route sebagai source type — jika diperlukan bisa diaktifkan di sprint berikutnya |
