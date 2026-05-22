╔════════════════════════════════════════════════╗
║       AgroSIM — Sistem Manajemen Perkebunan    ║
╚════════════════════════════════════════════════╝

CARA MENJALANKAN
─────────────────
1. Pastikan Python 3.8+ sudah terinstall
   → cek: python3 --version

2. Install Flask (hanya sekali):
   pip install flask

3. Jalankan aplikasi:
   cd kebun
   python3 app.py

4. Buka browser, ketik:
   http://localhost:5000

FITUR APLIKASI
──────────────
🌿 Dashboard     → Ringkasan & grafik real-time
🌾 Produksi      → Catat panen harian + jurnal otomatis
👷 SDM & Gaji   → Absensi + hitung gaji otomatis
📦 Gudang        → Stok pupuk, alat, peringatan kritis
💰 Keuangan      → Jurnal double-entry bookkeeping
📊 Laporan       → Laba Rugi + analisis rasio otomatis

STRUKTUR FILE
─────────────
kebun/
├── app.py              ← Backend Flask + SQLite
└── templates/
    ├── base.html       ← Layout & komponen UI
    ├── dashboard.html  ← Halaman Dashboard
    ├── produksi.html   ← Manajemen Panen
    ├── sdm.html        ← SDM & Penggajian
    ├── gudang.html     ← Gudang & Stok
    ├── keuangan.html   ← Jurnal Keuangan
    └── laporan.html    ← Laporan Laba Rugi

DATABASE
────────
SQLite otomatis dibuat saat pertama kali dijalankan.
File: kebun/kebun.db (data tersimpan permanen di sini)

Dibuat untuk mata kuliah Sistem Informasi Manajemen
