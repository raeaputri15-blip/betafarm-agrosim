"""
AgroSIM - Sistem Informasi Manajemen Perkebunan
Aplikasi manajemen kebun berbasis web menggunakan Flask + SQLite
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
import json
from datetime import datetime, date, timedelta
import os

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), 'kebun.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS produksi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tanggal TEXT NOT NULL, komoditas TEXT NOT NULL, blok TEXT,
        berat_kg REAL NOT NULL, kualitas TEXT DEFAULT 'A',
        harga_per_kg REAL DEFAULT 0, catatan TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS karyawan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama TEXT NOT NULL, jabatan TEXT NOT NULL, upah_harian REAL NOT NULL,
        no_hp TEXT, status TEXT DEFAULT 'aktif',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS absensi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        karyawan_id INTEGER NOT NULL, tanggal TEXT NOT NULL, status TEXT NOT NULL,
        jam_masuk TEXT, jam_keluar TEXT, lembur_jam REAL DEFAULT 0, catatan TEXT,
        FOREIGN KEY (karyawan_id) REFERENCES karyawan(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS gudang (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama_barang TEXT NOT NULL, kategori TEXT NOT NULL, satuan TEXT NOT NULL,
        stok_awal REAL DEFAULT 0, stok_sekarang REAL DEFAULT 0,
        harga_satuan REAL DEFAULT 0, stok_minimum REAL DEFAULT 0,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS transaksi_gudang (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barang_id INTEGER NOT NULL, tanggal TEXT NOT NULL, jenis TEXT NOT NULL,
        jumlah REAL NOT NULL, harga_satuan REAL DEFAULT 0, total REAL DEFAULT 0,
        keterangan TEXT, FOREIGN KEY (barang_id) REFERENCES gudang(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS jurnal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tanggal TEXT NOT NULL, no_referensi TEXT, keterangan TEXT NOT NULL,
        akun_debit TEXT NOT NULL, akun_kredit TEXT NOT NULL, nominal REAL NOT NULL,
        kategori TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    c.execute("SELECT COUNT(*) FROM karyawan")
    if c.fetchone()[0] == 0:
        seed_demo_data(c)
    conn.commit()
    conn.close()

def seed_demo_data(c):
    UMR_BULANAN = 2467488
    UMR_HARIAN  = round(UMR_BULANAN / 26)
    karyawan_data = [
        ('Benny',      'Owner / Pengelola Keuangan',        0,          '-'),
        ('Karyawan 1', 'Petugas Gedung (1.000 populasi)',   UMR_HARIAN, '-'),
        ('Karyawan 2', 'Petugas Gedung (1.000 populasi)',   UMR_HARIAN, '-'),
        ('Karyawan 3', 'Petugas Umum & Koordinator Panen',  UMR_HARIAN, '-'),
    ]
    c.executemany("INSERT INTO karyawan (nama, jabatan, upah_harian, no_hp) VALUES (?,?,?,?)", karyawan_data)
    gudang_data = [
        ('Benih Melon SW9 Thailand',         'Benih',     'Pack',  10,  7,  500000, 2),
        ('Benih Melon Lokal (Uji Coba)',     'Benih',     'Pack',   5,  3,  500000, 1),
        ('Nutrisi Abemix Komponen A',        'Pupuk',     'Liter', 40, 22,   85000, 8),
        ('Nutrisi Abemix Komponen B',        'Pupuk',     'Liter', 40, 20,   85000, 8),
        ('Pupuk Daun (Foliar Spray)',         'Pupuk',     'Liter', 20, 12,   75000, 4),
        ('Insektisida Anti Kutu Kebul',      'Pestisida', 'Botol', 20, 10,   95000, 4),
        ('Fungisida (Anti Jamur)',            'Pestisida', 'Botol', 15,  8,   85000, 3),
        ('Obat Semprot Daun (umum)',          'Pestisida', 'Liter', 10,  6,   70000, 2),
        ('Sprayer / Alat Semprot',           'Alat',      'Unit',   4,  3,  600000, 1),
        ('Genset',                           'Alat',      'Unit',   1,  1,60000000, 1),
        ('Tali Rambatan Melon',              'Alat',      'Meter', 500,320,    1500,100),
        ('Pralon / Pipa Irigasi',            'Alat',      'Meter', 200,200,    8000, 0),
        ('Spare Part Desle / Diesel',        'Alat',      'Set',    2,  1, 6000000, 1),
        ('Kemasan (by distributor)',         'Kemasan',   'Lembar', 0,  0,       0, 0),
    ]
    c.executemany("INSERT INTO gudang (nama_barang, kategori, satuan, stok_awal, stok_sekarang, harga_satuan, stok_minimum) VALUES (?,?,?,?,?,?,?)", gudang_data)
    POPULASI_AKTIF = 2000
    buah_berhasil  = int(POPULASI_AKTIF * 0.85)
    grade_a = int(buah_berhasil * 0.60)
    grade_b = int(buah_berhasil * 0.30)
    grade_c = buah_berhasil - grade_a - grade_b
    tgl_panen1 = (date.today() - timedelta(days=120)).isoformat()
    tgl_panen2 = (date.today() - timedelta(days=60)).isoformat()
    for tgl_p, siklus in [(tgl_panen1,'Siklus 1'),(tgl_panen2,'Siklus 2')]:
        c.execute("INSERT INTO produksi (tanggal,komoditas,blok,berat_kg,kualitas,harga_per_kg,catatan) VALUES (?,?,?,?,?,?,?)",
                  (tgl_p,'Melon SW9 Thailand','Gedung 1 & 2',grade_a,'A',25000,f'{siklus} — {grade_a} buah Grade A'))
        c.execute("INSERT INTO produksi (tanggal,komoditas,blok,berat_kg,kualitas,harga_per_kg,catatan) VALUES (?,?,?,?,?,?,?)",
                  (tgl_p,'Melon SW9 Thailand','Gedung 1 & 2',grade_b,'B',20000,f'{siklus} — {grade_b} buah Grade B'))
        c.execute("INSERT INTO produksi (tanggal,komoditas,blok,berat_kg,kualitas,harga_per_kg,catatan) VALUES (?,?,?,?,?,?,?)",
                  (tgl_p,'Melon SW9 Thailand','Gedung 1 & 2',grade_c,'C',15000,f'{siklus} — {grade_c} buah Grade C'))
    pA=grade_a*25000; pB=grade_b*20000; pC=grade_c*15000
    jurnal_data = [
        (tgl_panen1,'BF-P101',f'Penjualan Melon Grade A — {grade_a} buah × Rp25.000','Kas','Pendapatan Panen',pA,'Pendapatan'),
        (tgl_panen1,'BF-P102',f'Penjualan Melon Grade B — {grade_b} buah × Rp20.000','Kas','Pendapatan Panen',pB,'Pendapatan'),
        (tgl_panen1,'BF-P103',f'Penjualan Melon Grade C — {grade_c} buah × Rp15.000','Kas','Pendapatan Panen',pC,'Pendapatan'),
        (tgl_panen2,'BF-P201',f'Penjualan Melon Grade A — {grade_a} buah × Rp25.000','Kas','Pendapatan Panen',pA,'Pendapatan'),
        (tgl_panen2,'BF-P202',f'Penjualan Melon Grade B — {grade_b} buah × Rp20.000','Kas','Pendapatan Panen',pB,'Pendapatan'),
        (tgl_panen2,'BF-P203',f'Penjualan Melon Grade C — {grade_c} buah × Rp15.000','Kas','Pendapatan Panen',pC,'Pendapatan'),
        ((date.today()-timedelta(days=185)).isoformat(),'BF-B101','Pembelian Benih SW9 Thailand — 10 pack (Pemasok Benih)','Beban Benih','Kas',5000000,'Beban'),
        ((date.today()-timedelta(days=185)).isoformat(),'BF-B102','Pembelian Benih Melon Lokal Uji Coba — 5 pack','Beban Benih','Kas',2500000,'Beban'),
        ((date.today()-timedelta(days=170)).isoformat(),'BF-B103','Pembelian Nutrisi Abemix A+B & Pupuk Daun — Siklus 1 Bulan 1','Beban Pupuk','Kas',980000,'Beban'),
        ((date.today()-timedelta(days=140)).isoformat(),'BF-B104','Pembelian Nutrisi Abemix A+B & Pupuk Daun — Siklus 1 Bulan 2','Beban Pupuk','Kas',980000,'Beban'),
        ((date.today()-timedelta(days=110)).isoformat(),'BF-B105','Pembelian Nutrisi Abemix A+B & Pupuk Daun — Siklus 2 Bulan 1','Beban Pupuk','Kas',980000,'Beban'),
        ((date.today()-timedelta(days=80)).isoformat(),'BF-B106','Pembelian Nutrisi Abemix A+B & Pupuk Daun — Siklus 2 Bulan 2','Beban Pupuk','Kas',980000,'Beban'),
        ((date.today()-timedelta(days=165)).isoformat(),'BF-B107','Pembelian Insektisida Kutu Kebul + Fungisida — Siklus 1','Beban Pestisida','Kas',1100000,'Beban'),
        ((date.today()-timedelta(days=105)).isoformat(),'BF-B108','Pembelian Insektisida Kutu Kebul + Fungisida — Siklus 2','Beban Pestisida','Kas',1100000,'Beban'),
        ((date.today()-timedelta(days=150)).isoformat(),'BF-G101',f'Gaji 3 Karyawan Tetap — Bulan 1 (UMR Rp{UMR_BULANAN:,})','Beban Gaji','Kas',3*UMR_BULANAN,'Beban'),
        ((date.today()-timedelta(days=120)).isoformat(),'BF-G102',f'Gaji 3 Karyawan Tetap — Bulan 2 (UMR Rp{UMR_BULANAN:,})','Beban Gaji','Kas',3*UMR_BULANAN,'Beban'),
        ((date.today()-timedelta(days=90)).isoformat(),'BF-G103',f'Gaji 3 Karyawan Tetap — Bulan 3 (UMR Rp{UMR_BULANAN:,})','Beban Gaji','Kas',3*UMR_BULANAN,'Beban'),
        ((date.today()-timedelta(days=60)).isoformat(),'BF-G104',f'Gaji 3 Karyawan Tetap — Bulan 4 (UMR Rp{UMR_BULANAN:,})','Beban Gaji','Kas',3*UMR_BULANAN,'Beban'),
        (tgl_panen1,'BF-T101','Upah Tenaga Panen Lepas — Siklus 1 (borongan)','Beban Gaji','Kas',750000,'Beban'),
        (tgl_panen2,'BF-T102','Upah Tenaga Panen Lepas — Siklus 2 (borongan)','Beban Gaji','Kas',750000,'Beban'),
        ((date.today()-timedelta(days=30)).isoformat(),'BF-A101','Beli Sprayer Baru (rusak, beli online)','Beban Perawatan','Kas',600000,'Beban'),
        ((date.today()-timedelta(days=15)).isoformat(),'BF-A102','Servis Desle/Diesel Genset ke Toko Pertanian','Beban Perawatan','Kas',6000000,'Beban'),
    ]
    for j in jurnal_data:
        c.execute("INSERT INTO jurnal (tanggal,no_referensi,keterangan,akun_debit,akun_kredit,nominal,kategori) VALUES (?,?,?,?,?,?,?)", j)

@app.route('/') 
def dashboard(): return render_template('dashboard.html')
@app.route('/produksi') 
def produksi(): return render_template('produksi.html')
@app.route('/sdm') 
def sdm(): return render_template('sdm.html')
@app.route('/gudang') 
def gudang(): return render_template('gudang.html')
@app.route('/keuangan') 
def keuangan(): return render_template('keuangan.html')
@app.route('/laporan') 
def laporan(): return render_template('laporan.html')

@app.route('/api/dashboard')
def api_dashboard():
    conn = get_db(); c = conn.cursor()
    bulan_ini = date.today().strftime('%Y-%m')
    c.execute("SELECT COALESCE(SUM(berat_kg),0) FROM produksi WHERE tanggal LIKE ?", (f'{bulan_ini}%',))
    total_panen = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal WHERE kategori='Pendapatan' AND tanggal LIKE ?", (f'{bulan_ini}%',))
    total_pendapatan = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal WHERE kategori='Beban' AND tanggal LIKE ?", (f'{bulan_ini}%',))
    total_beban = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM karyawan WHERE status='aktif'")
    jumlah_karyawan = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM gudang WHERE stok_sekarang <= stok_minimum")
    stok_kritis = c.fetchone()[0]
    grafik_produksi = []
    for i in range(6,-1,-1):
        tgl = (date.today()-timedelta(days=i)).isoformat()
        c.execute("SELECT COALESCE(SUM(berat_kg),0) FROM produksi WHERE tanggal=?", (tgl,))
        grafik_produksi.append({'tanggal':tgl,'berat':c.fetchone()[0]})
    grafik_keuangan = []
    for i in range(5,-1,-1):
        bln = (date.today().replace(day=1)-timedelta(days=i*28)).strftime('%Y-%m')
        c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal WHERE kategori='Pendapatan' AND tanggal LIKE ?", (f'{bln}%',))
        pend = c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal WHERE kategori='Beban' AND tanggal LIKE ?", (f'{bln}%',))
        beban = c.fetchone()[0]
        grafik_keuangan.append({'bulan':bln,'pendapatan':pend,'beban':beban})
    c.execute("""SELECT 'Panen' as jenis, tanggal, komoditas || ' ' || berat_kg || ' buah' as deskripsi FROM produksi
                 UNION ALL SELECT 'Jurnal', tanggal, keterangan FROM jurnal ORDER BY tanggal DESC LIMIT 8""")
    aktivitas = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify({'total_panen':total_panen,'total_pendapatan':total_pendapatan,'total_beban':total_beban,
                    'laba_bersih':total_pendapatan-total_beban,'jumlah_karyawan':jumlah_karyawan,
                    'stok_kritis':stok_kritis,'grafik_produksi':grafik_produksi,'grafik_keuangan':grafik_keuangan,'aktivitas':aktivitas})

@app.route('/api/produksi', methods=['GET'])
def api_produksi_list():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM produksi ORDER BY tanggal DESC LIMIT 100")
    rows = [dict(r) for r in c.fetchall()]
    c.execute("SELECT COALESCE(SUM(berat_kg),0), COALESCE(SUM(berat_kg*harga_per_kg),0), COUNT(*) FROM produksi")
    s = c.fetchone(); conn.close()
    return jsonify({'data':rows,'total_kg':s[0],'total_nilai':s[1],'total_transaksi':s[2]})

@app.route('/api/produksi', methods=['POST'])
def api_produksi_add():
    d = request.json; conn = get_db()
    conn.execute("INSERT INTO produksi (tanggal,komoditas,blok,berat_kg,kualitas,harga_per_kg,catatan) VALUES (?,?,?,?,?,?,?)",
                 (d['tanggal'],d['komoditas'],d.get('blok',''),float(d['berat_kg']),d.get('kualitas','A'),float(d.get('harga_per_kg',0)),d.get('catatan','')))
    nilai = float(d['berat_kg'])*float(d.get('harga_per_kg',0))
    if nilai > 0:
        conn.execute("INSERT INTO jurnal (tanggal,keterangan,akun_debit,akun_kredit,nominal,kategori) VALUES (?,?,?,?,?,?)",
                     (d['tanggal'],f"Penjualan {d['komoditas']} {d['berat_kg']} buah",'Kas','Pendapatan Panen',nilai,'Pendapatan'))
    conn.commit(); conn.close()
    return jsonify({'success':True})

@app.route('/api/produksi/<int:id>', methods=['DELETE'])
def api_produksi_delete(id):
    conn = get_db(); conn.execute("DELETE FROM produksi WHERE id=?",(id,)); conn.commit(); conn.close()
    return jsonify({'success':True})

@app.route('/api/karyawan', methods=['GET'])
def api_karyawan_list():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM karyawan ORDER BY nama")
    rows = [dict(r) for r in c.fetchall()]; conn.close()
    return jsonify({'data':rows})

@app.route('/api/karyawan', methods=['POST'])
def api_karyawan_add():
    d = request.json; conn = get_db()
    conn.execute("INSERT INTO karyawan (nama,jabatan,upah_harian,no_hp) VALUES (?,?,?,?)",
                 (d['nama'],d['jabatan'],float(d['upah_harian']),d.get('no_hp','')))
    conn.commit(); conn.close()
    return jsonify({'success':True})

@app.route('/api/karyawan/<int:id>', methods=['DELETE'])
def api_karyawan_delete(id):
    conn = get_db(); conn.execute("DELETE FROM karyawan WHERE id=?",(id,)); conn.commit(); conn.close()
    return jsonify({'success':True})

@app.route('/api/absensi', methods=['GET'])
def api_absensi_list():
    tanggal = request.args.get('tanggal', date.today().isoformat())
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT a.*, k.nama, k.jabatan, k.upah_harian FROM absensi a
                 JOIN karyawan k ON a.karyawan_id=k.id WHERE a.tanggal=? ORDER BY k.nama""", (tanggal,))
    rows = [dict(r) for r in c.fetchall()]; conn.close()
    return jsonify({'data':rows})

@app.route('/api/absensi', methods=['POST'])
def api_absensi_add():
    d = request.json; conn = get_db(); c = conn.cursor()
    c.execute("SELECT id FROM absensi WHERE karyawan_id=? AND tanggal=?", (d['karyawan_id'],d['tanggal']))
    if c.fetchone():
        conn.execute("UPDATE absensi SET status=?,lembur_jam=?,catatan=? WHERE karyawan_id=? AND tanggal=?",
                     (d['status'],float(d.get('lembur_jam',0)),d.get('catatan',''),d['karyawan_id'],d['tanggal']))
    else:
        conn.execute("INSERT INTO absensi (karyawan_id,tanggal,status,lembur_jam,catatan) VALUES (?,?,?,?,?)",
                     (d['karyawan_id'],d['tanggal'],d['status'],float(d.get('lembur_jam',0)),d.get('catatan','')))
    conn.commit(); conn.close()
    return jsonify({'success':True})

@app.route('/api/gaji/hitung')
def api_hitung_gaji():
    bulan = request.args.get('bulan', date.today().strftime('%Y-%m'))
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM karyawan WHERE status='aktif'")
    karyawan = [dict(r) for r in c.fetchall()]; result = []
    for k in karyawan:
        c.execute("""SELECT SUM(CASE WHEN status='hadir' THEN 1 ELSE 0 END) as hari_kerja,
                     SUM(lembur_jam) as total_lembur FROM absensi WHERE karyawan_id=? AND tanggal LIKE ?""",
                  (k['id'],f'{bulan}%'))
        ab = c.fetchone()
        hari_kerja = ab['hari_kerja'] or 0; lembur = ab['total_lembur'] or 0
        upah_pokok = hari_kerja*k['upah_harian']
        upah_lembur = lembur*(k['upah_harian']/8)*1.5
        result.append({'nama':k['nama'],'jabatan':k['jabatan'],'upah_harian':k['upah_harian'],
                       'hari_kerja':hari_kerja,'lembur_jam':lembur,'upah_pokok':upah_pokok,
                       'upah_lembur':upah_lembur,'total_gaji':upah_pokok+upah_lembur})
    conn.close()
    return jsonify({'data':result,'bulan':bulan})

@app.route('/api/gudang', methods=['GET'])
def api_gudang_list():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM gudang ORDER BY kategori, nama_barang")
    rows = [dict(r) for r in c.fetchall()]; conn.close()
    return jsonify({'data':rows})

@app.route('/api/gudang', methods=['POST'])
def api_gudang_add():
    d = request.json; conn = get_db()
    stok = float(d.get('stok_awal',0))
    conn.execute("INSERT INTO gudang (nama_barang,kategori,satuan,stok_awal,stok_sekarang,harga_satuan,stok_minimum) VALUES (?,?,?,?,?,?,?)",
                 (d['nama_barang'],d['kategori'],d['satuan'],stok,stok,float(d.get('harga_satuan',0)),float(d.get('stok_minimum',0))))
    conn.commit(); conn.close()
    return jsonify({'success':True})

@app.route('/api/gudang/transaksi', methods=['POST'])
def api_gudang_transaksi():
    d = request.json; conn = get_db(); c = conn.cursor()
    jumlah = float(d['jumlah']); harga = float(d.get('harga_satuan',0))
    jenis = d['jenis']
    c.execute("SELECT stok_sekarang, nama_barang FROM gudang WHERE id=?", (d['barang_id'],))
    barang = c.fetchone()
    if not barang: return jsonify({'success':False,'error':'Barang tidak ditemukan'})
    stok_baru = barang['stok_sekarang']+jumlah if jenis=='masuk' else barang['stok_sekarang']-jumlah
    conn.execute("UPDATE gudang SET stok_sekarang=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (stok_baru,d['barang_id']))
    conn.execute("INSERT INTO transaksi_gudang (barang_id,tanggal,jenis,jumlah,harga_satuan,total,keterangan) VALUES (?,?,?,?,?,?,?)",
                 (d['barang_id'],d['tanggal'],jenis,jumlah,harga,jumlah*harga,d.get('keterangan','')))
    if jenis=='masuk' and jumlah*harga > 0:
        conn.execute("INSERT INTO jurnal (tanggal,keterangan,akun_debit,akun_kredit,nominal,kategori) VALUES (?,?,?,?,?,?)",
                     (d['tanggal'],f"Pembelian {barang['nama_barang']} {jumlah}",'Beban Bahan','Kas',jumlah*harga,'Beban'))
    conn.commit(); conn.close()
    return jsonify({'success':True,'stok_baru':stok_baru})

@app.route('/api/jurnal', methods=['GET'])
def api_jurnal_list():
    bulan = request.args.get('bulan', date.today().strftime('%Y-%m'))
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM jurnal WHERE tanggal LIKE ? ORDER BY tanggal DESC, id DESC", (f'{bulan}%',))
    rows = [dict(r) for r in c.fetchall()]
    c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal WHERE kategori='Pendapatan' AND tanggal LIKE ?", (f'{bulan}%',))
    pendapatan = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal WHERE kategori='Beban' AND tanggal LIKE ?", (f'{bulan}%',))
    beban = c.fetchone()[0]
    conn.close()
    return jsonify({'data':rows,'pendapatan':pendapatan,'beban':beban,'laba':pendapatan-beban})

@app.route('/api/jurnal', methods=['POST'])
def api_jurnal_add():
    d = request.json; conn = get_db()
    conn.execute("INSERT INTO jurnal (tanggal,no_referensi,keterangan,akun_debit,akun_kredit,nominal,kategori) VALUES (?,?,?,?,?,?,?)",
                 (d['tanggal'],d.get('no_referensi',''),d['keterangan'],d['akun_debit'],d['akun_kredit'],float(d['nominal']),d.get('kategori','Lainnya')))
    conn.commit(); conn.close()
    return jsonify({'success':True})

@app.route('/api/jurnal/<int:id>', methods=['DELETE'])
def api_jurnal_delete(id):
    conn = get_db(); conn.execute("DELETE FROM jurnal WHERE id=?",(id,)); conn.commit(); conn.close()
    return jsonify({'success':True})

@app.route('/api/laporan/laba_rugi')
def api_laba_rugi():
    bulan = request.args.get('bulan', date.today().strftime('%Y-%m'))
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT akun_kredit as akun, SUM(nominal) as total FROM jurnal WHERE kategori='Pendapatan' AND tanggal LIKE ? GROUP BY akun_kredit", (f'{bulan}%',))
    pendapatan = [dict(r) for r in c.fetchall()]
    c.execute("SELECT akun_debit as akun, SUM(nominal) as total FROM jurnal WHERE kategori='Beban' AND tanggal LIKE ? GROUP BY akun_debit", (f'{bulan}%',))
    beban = [dict(r) for r in c.fetchall()]
    total_pend = sum(p['total'] for p in pendapatan)
    total_beban = sum(b['total'] for b in beban)
    conn.close()
    return jsonify({'bulan':bulan,'pendapatan':pendapatan,'beban':beban,
                    'total_pendapatan':total_pend,'total_beban':total_beban,'laba_bersih':total_pend-total_beban})

if __name__ == '__main__':
    init_db()
    print("\n" + "="*50)
    print("  AgroSIM — BetaFarm Manajemen Perkebunan")
    print("  Buka browser: http://localhost:5000")
    print("="*50 + "\n")
   app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))