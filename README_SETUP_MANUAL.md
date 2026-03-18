# Domain IQ — Panduan Setup Manual

Panduan ini untuk menjalankan app di komputer lokal dengan PostgreSQL lokal.
Ikuti langkah-langkah di bawah secara berurutan.

---

## Daftar Isi

1. [Install PostgreSQL](#1-install-postgresql)
2. [Buat User & Database](#2-buat-user--database)
3. [Setup Project](#3-setup-project)
4. [Konfigurasi File .env](#4-konfigurasi-file-env)
5. [Jalankan Aplikasi](#5-jalankan-aplikasi)
6. [Login ke Aplikasi](#6-login-ke-aplikasi)
7. [Troubleshooting Koneksi Database](#7-troubleshooting-koneksi-database)

---

## 1. Install PostgreSQL

1. Download installer dari **https://www.postgresql.org/download/windows/**
2. Jalankan installer, klik **Next** terus sampai selesai.
3. Saat diminta password untuk superuser `postgres` — **catat password ini**, butuh di langkah berikutnya.
4. Port biarkan default: **5432**.
5. Setelah selesai, pastikan PostgreSQL berjalan:
   - Tekan **Win + R** → ketik `services.msc` → Enter
   - Cari service bernama **postgresql-x64-XX** → pastikan status **Running**

---

## 2. Buat User & Database

Buka **Command Prompt sebagai Administrator**, lalu jalankan:

```bash
psql -U postgres
```

Masukkan password `postgres` yang tadi dicatat saat install. Setelah masuk ke prompt `postgres=#`, copy-paste semua perintah berikut sekaligus:

```sql
CREATE USER domainiq_user WITH PASSWORD 'passwordkuat';
CREATE DATABASE domainiq_db OWNER domainiq_user;
GRANT ALL PRIVILEGES ON DATABASE domainiq_db TO domainiq_user;
\q
```

> Ganti `passwordkuat` dengan password apapun yang Anda mau — tapi catat karena dipakai di langkah 4.

---

## 3. Setup Project

1. Ekstrak folder project ke lokasi mana saja.
2. Buka Command Prompt / PowerShell di dalam folder tersebut.
3. Jalankan:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## 4. Konfigurasi File .env

1. Di folder project, jalankan:

   ```bash
   copy .env.example .env
   ```

2. Buka file `.env` (bisa pakai Notepad), ubah bagian ini:

   ```env
   # Ganti user/password/dbname sesuai yang dibuat di langkah 2
   DATABASE_URL=postgresql+asyncpg://domainiq_user:passwordkuat@localhost:5432/domainiq_db

   AUTH_USERNAME=admin
   AUTH_PASSWORD=PasswordLoginDashboard!

   SECRET_KEY=ganti-dengan-string-acak-panjang
   ```

3. Simpan dan tutup.

---

## 5. Jalankan Aplikasi

Double-click file **`start-server.bat`** di folder project.

Atau lewat terminal (pastikan venv aktif):

```bash
python -m uvicorn app.main:app --port 8888
```

Buka browser ke: **http://localhost:8888**

---

## 6. Login ke Aplikasi

Browser akan minta username & password:

- **Username**: `admin` (atau sesuai `AUTH_USERNAME` di `.env`)
- **Password**: sesuai `AUTH_PASSWORD` di `.env`

> Jika tidak muncul popup login, coba buka di tab incognito.

---

## 7. Troubleshooting Koneksi Database

### Error: `could not connect to server` / `Connection refused`

**Penyebab:** Service PostgreSQL tidak jalan.

Buka **Services** (Win+R → `services.msc`) → cari `postgresql` → klik **Start**.

---

### Error: `password authentication failed for user "domainiq_user"`

**Penyebab:** Password di `DATABASE_URL` salah atau user belum dibuat.

1. Periksa kembali password di `DATABASE_URL` dalam file `.env`.
2. Reset password user di PostgreSQL:

   ```bash
   psql -U postgres
   ```
   ```sql
   ALTER USER domainiq_user WITH PASSWORD 'password-baru';
   \q
   ```
3. Update `DATABASE_URL` di `.env` sesuai password baru.

---

### Error: `database "domainiq_db" does not exist`

**Penyebab:** Database belum dibuat.

```bash
psql -U postgres
```
```sql
CREATE DATABASE domainiq_db OWNER domainiq_user;
GRANT ALL PRIVILEGES ON DATABASE domainiq_db TO domainiq_user;
\q
```

---

### Error: `role "domainiq_user" does not exist`

**Penyebab:** User PostgreSQL belum dibuat.

```bash
psql -U postgres
```
```sql
CREATE USER domainiq_user WITH PASSWORD 'passwordkuat';
CREATE DATABASE domainiq_db OWNER domainiq_user;
GRANT ALL PRIVILEGES ON DATABASE domainiq_db TO domainiq_user;
\q
```

---

### Error: `SSL connection has been closed unexpectedly`

Hapus `?ssl=require` dari `DATABASE_URL` — itu hanya untuk cloud, bukan lokal:

```env
DATABASE_URL=postgresql+asyncpg://domainiq_user:passwordkuat@localhost:5432/domainiq_db
```

---

### Error: `ModuleNotFoundError` saat start server

**Penyebab:** Dependencies belum terinstall atau virtual environment belum aktif.

```bash
# Aktifkan venv terlebih dahulu, lalu:
pip install -r requirements.txt
```

---

### Cek Koneksi Database Secara Manual

Jalankan perintah ini untuk memastikan semua konfigurasi sudah benar sebelum start server:

```bash
python -c "
import asyncio, asyncpg, os
from dotenv import load_dotenv
load_dotenv()
url = os.getenv('DATABASE_URL', '').replace('postgresql+asyncpg://', 'postgresql://')
async def test():
    conn = await asyncpg.connect(url)
    ver = await conn.fetchval('SELECT version()')
    print('OK — Terhubung ke:', ver[:50])
    await conn.close()
asyncio.run(test())
"
```

Jika output menampilkan `OK — Terhubung ke: PostgreSQL ...`, koneksi berhasil.

---

*Dokumen ini dibuat untuk Domain IQ — versi Maret 2026.*
