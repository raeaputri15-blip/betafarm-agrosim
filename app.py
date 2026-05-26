"""
AgroSIM - Sistem Informasi Manajemen Perkebunan BetaFarm
Versi 2.0 - Sistem Akuntansi Terintegrasi
"""

from flask import Flask, render_template, request, jsonify
from datetime import datetime, date, timedelta
import sqlite3, os

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), 'kebun.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db(); c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS produksi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tanggal TEXT NOT NULL, komoditas TEXT NOT NULL, blok TEXT,
        jumlah_buah REAL NOT NULL, kualitas TEXT DEFAULT 'A',
        harga_per_buah REAL DEFAULT 0, catatan TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS karyawan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama TEXT NOT NULL, jabatan TEXT NOT NULL, upah_harian REAL NOT NULL,
        no_hp TEXT, status TEXT DEFAULT 'aktif',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS absensi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        karyawan_id INTEGER NOT NULL, tanggal TEXT NOT NULL, status TEXT NOT NULL,
        lembur_jam REAL DEFAULT 0, catatan TEXT,
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

    # Jurnal Umum - inti dari sistem akuntansi
    c.execute('''CREATE TABLE IF NOT EXISTS jurnal_umum (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tanggal TEXT NOT NULL, no_referensi TEXT,
        keterangan TEXT NOT NULL, akun_debit TEXT NOT NULL,
        akun_kredit TEXT NOT NULL, nominal REAL NOT NULL,
        kategori TEXT, sumber TEXT DEFAULT 'manual',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')

    # Akun/Chart of Accounts
    c.execute('''CREATE TABLE IF NOT EXISTS akun (
        kode TEXT PRIMARY KEY, nama TEXT NOT NULL,
        tipe TEXT NOT NULL, kelompok TEXT NOT NULL)''')

    # Ekuitas/Modal
    c.execute('''CREATE TABLE IF NOT EXISTS ekuitas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tanggal TEXT NOT NULL, keterangan TEXT NOT NULL,
        jenis TEXT NOT NULL, nominal REAL NOT NULL)''')

    # Seed akun jika kosong
    c.execute("SELECT COUNT(*) FROM akun")
    if c.fetchone()[0] == 0:
        akun_data = [
            ('1-001','Kas','Aset','Aset Lancar'),
            ('1-002','Piutang Dagang','Aset','Aset Lancar'),
            ('1-003','Persediaan Benih','Aset','Aset Lancar'),
            ('1-004','Persediaan Pupuk & Pestisida','Aset','Aset Lancar'),
            ('1-101','Genset','Aset','Aset Tetap'),
            ('1-102','Peralatan Kebun','Aset','Aset Tetap'),
            ('1-103','Bangunan/Gedung','Aset','Aset Tetap'),
            ('2-001','Hutang Dagang','Kewajiban','Kewajiban Lancar'),
            ('2-002','Hutang Gaji','Kewajiban','Kewajiban Lancar'),
            ('3-001','Modal Benny','Ekuitas','Ekuitas'),
            ('3-002','Prive Benny','Ekuitas','Ekuitas'),
            ('4-001','Pendapatan Panen Grade A','Pendapatan','Pendapatan'),
            ('4-002','Pendapatan Panen Grade B','Pendapatan','Pendapatan'),
            ('4-003','Pendapatan Panen Grade C','Pendapatan','Pendapatan'),
            ('5-001','Beban Gaji Karyawan','Beban','Beban Operasional'),
            ('5-002','Beban Benih','Beban','Beban Operasional'),
            ('5-003','Beban Pupuk & Nutrisi','Beban','Beban Operasional'),
            ('5-004','Beban Pestisida','Beban','Beban Operasional'),
            ('5-005','Beban Perawatan Alat','Beban','Beban Operasional'),
            ('5-006','Beban Operasional Lain','Beban','Beban Operasional'),
        ]
        c.executemany("INSERT INTO akun VALUES (?,?,?,?)", akun_data)

    c.execute("SELECT COUNT(*) FROM karyawan")
    if c.fetchone()[0] == 0:
        seed_data(c)

    conn.commit(); conn.close()

def seed_data(c):
    UMR = 2467488
    UMR_H = round(UMR / 26)
    c.executemany("INSERT INTO karyawan (nama,jabatan,upah_harian,no_hp) VALUES (?,?,?,?)", [
        ('Benny','Owner / Pengelola Keuangan',0,'-'),
        ('Karyawan 1','Petugas Gedung (1.000 populasi)',UMR_H,'-'),
        ('Karyawan 2','Petugas Gedung (1.000 populasi)',UMR_H,'-'),
        ('Karyawan 3','Petugas Umum & Koordinator Panen',UMR_H,'-'),
    ])
    c.executemany("INSERT INTO gudang (nama_barang,kategori,satuan,stok_awal,stok_sekarang,harga_satuan,stok_minimum) VALUES (?,?,?,?,?,?,?)", [
        ('Benih Melon SW9 Thailand','Benih','Pack',10,7,500000,2),
        ('Benih Melon Lokal (Uji Coba)','Benih','Pack',5,3,500000,1),
        ('Nutrisi Abemix Komponen A','Pupuk','Liter',40,22,85000,8),
        ('Nutrisi Abemix Komponen B','Pupuk','Liter',40,20,85000,8),
        ('Pupuk Daun (Foliar Spray)','Pupuk','Liter',20,12,75000,4),
        ('Insektisida Anti Kutu Kebul','Pestisida','Botol',20,10,95000,4),
        ('Fungisida (Anti Jamur)','Pestisida','Botol',15,8,85000,3),
        ('Obat Semprot Daun','Pestisida','Liter',10,6,70000,2),
        ('Sprayer / Alat Semprot','Alat','Unit',4,3,600000,1),
        ('Genset','Alat','Unit',1,1,60000000,1),
        ('Tali Rambatan Melon','Alat','Meter',500,320,1500,100),
        ('Pralon / Pipa Irigasi','Alat','Meter',200,200,8000,0),
        ('Spare Part Desle / Diesel','Alat','Set',2,1,6000000,1),
    ])
    POPULASI = 2000
    buah = int(POPULASI * 0.85)
    gA = int(buah*0.6); gB = int(buah*0.3); gC = buah-gA-gB
    p1 = (date.today()-timedelta(days=120)).isoformat()
    p2 = (date.today()-timedelta(days=60)).isoformat()
    for tgl,siklus in [(p1,'Siklus 1'),(p2,'Siklus 2')]:
        for jml,kual,harga in [(gA,'A',25000),(gB,'B',20000),(gC,'C',15000)]:
            c.execute("INSERT INTO produksi (tanggal,komoditas,blok,jumlah_buah,kualitas,harga_per_buah,catatan) VALUES (?,?,?,?,?,?,?)",
                      (tgl,'Melon SW9 Thailand','Gedung 1 & 2',jml,kual,harga,f'{siklus} — {jml} buah Grade {kual}'))
            c.execute("INSERT INTO jurnal_umum (tanggal,no_referensi,keterangan,akun_debit,akun_kredit,nominal,kategori,sumber) VALUES (?,?,?,?,?,?,?,?)",
                      (tgl,f'BF-P-{kual}',f'Penjualan Melon Grade {kual} {jml} buah × Rp{harga:,}',
                       'Kas',f'Pendapatan Panen Grade {kual}',jml*harga,'Pendapatan','produksi'))

    jurnal = [
        ((date.today()-timedelta(days=185)).isoformat(),'BF-B101','Pembelian Benih SW9 Thailand 10 pack','Beban Benih','Kas',5000000,'Beban','manual'),
        ((date.today()-timedelta(days=185)).isoformat(),'BF-B102','Pembelian Benih Lokal Uji Coba 5 pack','Beban Benih','Kas',2500000,'Beban','manual'),
        ((date.today()-timedelta(days=170)).isoformat(),'BF-B103','Pembelian Nutrisi Abemix & Pupuk Daun Siklus 1 Bln 1','Beban Pupuk & Nutrisi','Kas',980000,'Beban','gudang'),
        ((date.today()-timedelta(days=140)).isoformat(),'BF-B104','Pembelian Nutrisi Abemix & Pupuk Daun Siklus 1 Bln 2','Beban Pupuk & Nutrisi','Kas',980000,'Beban','gudang'),
        ((date.today()-timedelta(days=110)).isoformat(),'BF-B105','Pembelian Nutrisi Abemix & Pupuk Daun Siklus 2 Bln 1','Beban Pupuk & Nutrisi','Kas',980000,'Beban','gudang'),
        ((date.today()-timedelta(days=80)).isoformat(),'BF-B106','Pembelian Nutrisi Abemix & Pupuk Daun Siklus 2 Bln 2','Beban Pupuk & Nutrisi','Kas',980000,'Beban','gudang'),
        ((date.today()-timedelta(days=165)).isoformat(),'BF-B107','Pembelian Insektisida & Fungisida Siklus 1','Beban Pestisida','Kas',1100000,'Beban','gudang'),
        ((date.today()-timedelta(days=105)).isoformat(),'BF-B108','Pembelian Insektisida & Fungisida Siklus 2','Beban Pestisida','Kas',1100000,'Beban','gudang'),
        ((date.today()-timedelta(days=150)).isoformat(),'BF-G101',f'Gaji 3 Karyawan Bulan 1 (UMR Rp{UMR:,})','Beban Gaji Karyawan','Kas',3*UMR,'Beban','sdm'),
        ((date.today()-timedelta(days=120)).isoformat(),'BF-G102',f'Gaji 3 Karyawan Bulan 2 (UMR Rp{UMR:,})','Beban Gaji Karyawan','Kas',3*UMR,'Beban','sdm'),
        ((date.today()-timedelta(days=90)).isoformat(),'BF-G103',f'Gaji 3 Karyawan Bulan 3 (UMR Rp{UMR:,})','Beban Gaji Karyawan','Kas',3*UMR,'Beban','sdm'),
        ((date.today()-timedelta(days=60)).isoformat(),'BF-G104',f'Gaji 3 Karyawan Bulan 4 (UMR Rp{UMR:,})','Beban Gaji Karyawan','Kas',3*UMR,'Beban','sdm'),
        (p1,'BF-T101','Upah Tenaga Panen Lepas Siklus 1','Beban Gaji Karyawan','Kas',750000,'Beban','sdm'),
        (p2,'BF-T102','Upah Tenaga Panen Lepas Siklus 2','Beban Gaji Karyawan','Kas',750000,'Beban','sdm'),
        ((date.today()-timedelta(days=30)).isoformat(),'BF-A101','Beli Sprayer Baru (beli online)','Beban Perawatan Alat','Kas',600000,'Beban','gudang'),
        ((date.today()-timedelta(days=15)).isoformat(),'BF-A102','Servis Desle/Diesel Genset','Beban Perawatan Alat','Kas',6000000,'Beban','gudang'),
        ((date.today()-timedelta(days=10)).isoformat(),'BF-M101','Modal awal Benny','Kas','Modal Benny',50000000,'Modal','manual'),
    ]
    c.executemany("INSERT INTO jurnal_umum (tanggal,no_referensi,keterangan,akun_debit,akun_kredit,nominal,kategori,sumber) VALUES (?,?,?,?,?,?,?,?)", jurnal)
    c.execute("INSERT INTO ekuitas (tanggal,keterangan,jenis,nominal) VALUES (?,?,?,?)",
              (date.today().isoformat(),'Modal Awal Benny — BetaFarm','Modal',50000000))

# ── ROUTES ──
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

# ── API DASHBOARD ──
@app.route('/api/dashboard')
def api_dashboard():
    conn = get_db(); c = conn.cursor()
    # Support filter periode
    periode = request.args.get('periode','bulan_ini')
    tgl_mulai = request.args.get('tgl_mulai','')
    tgl_akhir = request.args.get('tgl_akhir','')
    today = date.today()

    if periode == '7hari':
        d_from = (today-timedelta(days=7)).isoformat(); d_to = today.isoformat()
    elif periode == '30hari':
        d_from = (today-timedelta(days=30)).isoformat(); d_to = today.isoformat()
    elif periode == 'bulan_lalu':
        first_this = today.replace(day=1)
        last_month = first_this - timedelta(days=1)
        d_from = last_month.replace(day=1).isoformat(); d_to = last_month.isoformat()
    elif periode == 'tahun_ini':
        d_from = today.replace(month=1,day=1).isoformat(); d_to = today.isoformat()
    elif periode == 'custom' and tgl_mulai and tgl_akhir:
        d_from = tgl_mulai; d_to = tgl_akhir
    else:  # bulan_ini default
        d_from = today.replace(day=1).isoformat(); d_to = today.isoformat()

    c.execute("SELECT COALESCE(SUM(jumlah_buah),0) FROM produksi WHERE tanggal BETWEEN ? AND ?", (d_from,d_to))
    total_panen = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(jumlah_buah*harga_per_buah),0) FROM produksi WHERE tanggal BETWEEN ? AND ?", (d_from,d_to))
    total_nilai_panen = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE kategori='Pendapatan' AND tanggal BETWEEN ? AND ?", (d_from,d_to))
    total_pendapatan = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE kategori='Beban' AND tanggal BETWEEN ? AND ?", (d_from,d_to))
    total_beban = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM karyawan WHERE status='aktif'")
    jumlah_karyawan = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM gudang WHERE stok_sekarang <= stok_minimum AND stok_minimum > 0")
    stok_kritis = c.fetchone()[0]

    # Grafik produksi sesuai periode
    grafik_produksi = []
    if periode in ['7hari','bulan_ini']:
        days = 7 if periode == '7hari' else 30
        for i in range(days-1,-1,-1):
            tgl = (today-timedelta(days=i)).isoformat()
            c.execute("SELECT COALESCE(SUM(jumlah_buah),0) FROM produksi WHERE tanggal=?", (tgl,))
            grafik_produksi.append({'tanggal':tgl,'berat':c.fetchone()[0]})
    else:
        # Group by bulan untuk periode panjang
        c.execute("""SELECT substr(tanggal,1,7) as bln, COALESCE(SUM(jumlah_buah),0) as total
                     FROM produksi WHERE tanggal BETWEEN ? AND ? GROUP BY bln ORDER BY bln""", (d_from,d_to))
        for r in c.fetchall():
            grafik_produksi.append({'tanggal':r['bln'],'berat':r['total']})

    # Grafik keuangan 6 bulan
    grafik_keuangan = []
    for i in range(5,-1,-1):
        bln = (today.replace(day=1)-timedelta(days=i*28)).strftime('%Y-%m')
        c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE kategori='Pendapatan' AND tanggal LIKE ?", (f'{bln}%',))
        pend = c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE kategori='Beban' AND tanggal LIKE ?", (f'{bln}%',))
        beban = c.fetchone()[0]
        grafik_keuangan.append({'bulan':bln,'pendapatan':pend,'beban':beban})

    c.execute("""SELECT 'Panen' as jenis, tanggal, komoditas||' '||jumlah_buah||' buah' as deskripsi FROM produksi
                 UNION ALL SELECT 'Jurnal', tanggal, keterangan FROM jurnal_umum
                 ORDER BY tanggal DESC LIMIT 8""")
    aktivitas = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify({'total_panen':total_panen,'total_nilai_panen':total_nilai_panen,
                    'total_pendapatan':total_pendapatan,'total_beban':total_beban,
                    'laba_bersih':total_pendapatan-total_beban,'jumlah_karyawan':jumlah_karyawan,
                    'stok_kritis':stok_kritis,'grafik_produksi':grafik_produksi,
                    'grafik_keuangan':grafik_keuangan,'aktivitas':aktivitas,
                    'periode':periode,'d_from':d_from,'d_to':d_to})

# ── API PRODUKSI ──
@app.route('/api/produksi', methods=['GET'])
def api_produksi_list():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM produksi ORDER BY tanggal DESC LIMIT 100")
    rows = [dict(r) for r in c.fetchall()]
    c.execute("SELECT COALESCE(SUM(jumlah_buah),0), COALESCE(SUM(jumlah_buah*harga_per_buah),0), COUNT(*) FROM produksi")
    s = c.fetchone(); conn.close()
    return jsonify({'data':rows,'total_kg':s[0],'total_nilai':s[1],'total_transaksi':s[2]})

@app.route('/api/produksi', methods=['POST'])
def api_produksi_add():
    d = request.json; conn = get_db()
    jumlah = float(d['berat_kg']); harga = float(d.get('harga_per_kg',0))
    kual = d.get('kualitas','A')
    conn.execute("INSERT INTO produksi (tanggal,komoditas,blok,jumlah_buah,kualitas,harga_per_buah,catatan) VALUES (?,?,?,?,?,?,?)",
                 (d['tanggal'],d['komoditas'],d.get('blok',''),jumlah,kual,harga,d.get('catatan','')))
    nilai = jumlah * harga
    if nilai > 0:
        conn.execute("INSERT INTO jurnal_umum (tanggal,keterangan,akun_debit,akun_kredit,nominal,kategori,sumber) VALUES (?,?,?,?,?,?,?)",
                     (d['tanggal'],f"Penjualan {d['komoditas']} Grade {kual} {jumlah} buah",
                      'Kas',f'Pendapatan Panen Grade {kual}',nilai,'Pendapatan','produksi'))
    conn.commit(); conn.close()
    return jsonify({'success':True})

@app.route('/api/produksi/<int:id>', methods=['DELETE'])
def api_produksi_delete(id):
    conn = get_db(); conn.execute("DELETE FROM produksi WHERE id=?",(id,)); conn.commit(); conn.close()
    return jsonify({'success':True})

# ── API SDM ──
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
        conn.execute("UPDATE absensi SET status=?,lembur_jam=? WHERE karyawan_id=? AND tanggal=?",
                     (d['status'],float(d.get('lembur_jam',0)),d['karyawan_id'],d['tanggal']))
    else:
        conn.execute("INSERT INTO absensi (karyawan_id,tanggal,status,lembur_jam) VALUES (?,?,?,?)",
                     (d['karyawan_id'],d['tanggal'],d['status'],float(d.get('lembur_jam',0))))
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
        hari = ab['hari_kerja'] or 0; lembur = ab['total_lembur'] or 0
        upah_pokok = hari * k['upah_harian']
        upah_lembur = lembur * (k['upah_harian']/8) * 1.5
        result.append({'nama':k['nama'],'jabatan':k['jabatan'],'upah_harian':k['upah_harian'],
                       'hari_kerja':hari,'lembur_jam':lembur,'upah_pokok':upah_pokok,
                       'upah_lembur':upah_lembur,'total_gaji':upah_pokok+upah_lembur,'id':k['id']})
    conn.close()
    return jsonify({'data':result,'bulan':bulan})

@app.route('/api/gaji/bayar', methods=['POST'])
def api_bayar_gaji():
    d = request.json; conn = get_db()
    bulan = d['bulan']; total = float(d['total'])
    # Otomatis buat jurnal saat gaji dibayar
    conn.execute("INSERT INTO jurnal_umum (tanggal,no_referensi,keterangan,akun_debit,akun_kredit,nominal,kategori,sumber) VALUES (?,?,?,?,?,?,?,?)",
                 (date.today().isoformat(), f'GAJI-{bulan}',
                  f'Pembayaran Gaji Karyawan Bulan {bulan}',
                  'Beban Gaji Karyawan','Kas',total,'Beban','sdm'))
    conn.commit(); conn.close()
    return jsonify({'success':True})

# ── API GUDANG ──
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
    c.execute("SELECT stok_sekarang, nama_barang, kategori FROM gudang WHERE id=?", (d['barang_id'],))
    barang = c.fetchone()
    if not barang: return jsonify({'success':False,'error':'Barang tidak ditemukan'})
    stok_baru = barang['stok_sekarang']+jumlah if jenis=='masuk' else barang['stok_sekarang']-jumlah
    conn.execute("UPDATE gudang SET stok_sekarang=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (stok_baru,d['barang_id']))
    conn.execute("INSERT INTO transaksi_gudang (barang_id,tanggal,jenis,jumlah,harga_satuan,total,keterangan) VALUES (?,?,?,?,?,?,?)",
                 (d['barang_id'],d['tanggal'],jenis,jumlah,harga,jumlah*harga,d.get('keterangan','')))
    if jenis=='masuk' and jumlah*harga > 0:
        kat = barang['kategori']
        akun_beban = 'Beban Pupuk & Nutrisi' if kat=='Pupuk' else 'Beban Pestisida' if kat=='Pestisida' else 'Beban Benih' if kat=='Benih' else 'Beban Perawatan Alat'
        conn.execute("INSERT INTO jurnal_umum (tanggal,keterangan,akun_debit,akun_kredit,nominal,kategori,sumber) VALUES (?,?,?,?,?,?,?)",
                     (d['tanggal'],f"Pembelian {barang['nama_barang']} {jumlah} {d.get('satuan','')}",
                      akun_beban,'Kas',jumlah*harga,'Beban','gudang'))
    conn.commit(); conn.close()
    return jsonify({'success':True,'stok_baru':stok_baru})

# ── API KEUANGAN - JURNAL UMUM ──
@app.route('/api/jurnal', methods=['GET'])
def api_jurnal_list():
    bulan = request.args.get('bulan', date.today().strftime('%Y-%m'))
    sumber = request.args.get('sumber','semua')
    conn = get_db(); c = conn.cursor()
    if sumber == 'semua':
        c.execute("SELECT * FROM jurnal_umum WHERE tanggal LIKE ? ORDER BY tanggal DESC,id DESC", (f'{bulan}%',))
    else:
        c.execute("SELECT * FROM jurnal_umum WHERE tanggal LIKE ? AND sumber=? ORDER BY tanggal DESC,id DESC", (f'{bulan}%',sumber))
    rows = [dict(r) for r in c.fetchall()]
    c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE kategori='Pendapatan' AND tanggal LIKE ?", (f'{bulan}%',))
    pend = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE kategori='Beban' AND tanggal LIKE ?", (f'{bulan}%',))
    beban = c.fetchone()[0]
    conn.close()
    return jsonify({'data':rows,'pendapatan':pend,'beban':beban,'laba':pend-beban})

@app.route('/api/jurnal', methods=['POST'])
def api_jurnal_add():
    d = request.json; conn = get_db()
    conn.execute("INSERT INTO jurnal_umum (tanggal,no_referensi,keterangan,akun_debit,akun_kredit,nominal,kategori,sumber) VALUES (?,?,?,?,?,?,?,?)",
                 (d['tanggal'],d.get('no_referensi',''),d['keterangan'],d['akun_debit'],d['akun_kredit'],
                  float(d['nominal']),d.get('kategori','Lainnya'),'manual'))
    conn.commit(); conn.close()
    return jsonify({'success':True})

@app.route('/api/jurnal/<int:id>', methods=['DELETE'])
def api_jurnal_delete(id):
    conn = get_db(); conn.execute("DELETE FROM jurnal_umum WHERE id=?",(id,)); conn.commit(); conn.close()
    return jsonify({'success':True})

# ── API BUKU BESAR ──
@app.route('/api/buku_besar')
def api_buku_besar():
    akun_nama = request.args.get('akun','Kas')
    bulan = request.args.get('bulan', date.today().strftime('%Y-%m'))
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT * FROM jurnal_umum 
                 WHERE (akun_debit=? OR akun_kredit=?) AND tanggal LIKE ?
                 ORDER BY tanggal, id""", (akun_nama,akun_nama,f'{bulan}%'))
    rows = []
    saldo = 0
    for r in c.fetchall():
        r = dict(r)
        if r['akun_debit'] == akun_nama:
            r['posisi'] = 'Debit'; saldo += r['nominal']
        else:
            r['posisi'] = 'Kredit'; saldo -= r['nominal']
        r['saldo'] = saldo
        rows.append(r)
    # Daftar semua akun yang pernah muncul
    c.execute("SELECT DISTINCT akun_debit as akun FROM jurnal_umum UNION SELECT DISTINCT akun_kredit FROM jurnal_umum ORDER BY akun")
    semua_akun = [r['akun'] for r in c.fetchall()]
    conn.close()
    return jsonify({'data':rows,'akun':akun_nama,'saldo_akhir':saldo,'semua_akun':semua_akun})

# ── API NERACA SALDO ──
@app.route('/api/neraca_saldo')
def api_neraca_saldo():
    bulan = request.args.get('bulan', date.today().strftime('%Y-%m'))
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT DISTINCT akun_debit as akun FROM jurnal_umum WHERE tanggal LIKE ? UNION SELECT DISTINCT akun_kredit FROM jurnal_umum WHERE tanggal LIKE ? ORDER BY akun", (f'{bulan}%',f'{bulan}%'))
    akun_list = [r['akun'] for r in c.fetchall()]
    result = []
    for akun in akun_list:
        c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE akun_debit=? AND tanggal LIKE ?", (akun,f'{bulan}%'))
        debit = c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE akun_kredit=? AND tanggal LIKE ?", (akun,f'{bulan}%'))
        kredit = c.fetchone()[0]
        result.append({'akun':akun,'debit':debit,'kredit':kredit,'saldo':debit-kredit})
    conn.close()
    return jsonify({'data':result,'bulan':bulan})

# ── API LAPORAN ──
@app.route('/api/laporan/laba_rugi')
def api_laba_rugi():
    bulan = request.args.get('bulan', date.today().strftime('%Y-%m'))
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT akun_kredit as akun, SUM(nominal) as total FROM jurnal_umum WHERE kategori='Pendapatan' AND tanggal LIKE ? GROUP BY akun_kredit", (f'{bulan}%',))
    pendapatan = [dict(r) for r in c.fetchall()]
    c.execute("SELECT akun_debit as akun, SUM(nominal) as total FROM jurnal_umum WHERE kategori='Beban' AND tanggal LIKE ? GROUP BY akun_debit", (f'{bulan}%',))
    beban = [dict(r) for r in c.fetchall()]
    tot_pend = sum(p['total'] for p in pendapatan)
    tot_beban = sum(b['total'] for b in beban)
    conn.close()
    return jsonify({'bulan':bulan,'pendapatan':pendapatan,'beban':beban,
                    'total_pendapatan':tot_pend,'total_beban':tot_beban,'laba_bersih':tot_pend-tot_beban})

@app.route('/api/laporan/neraca')
def api_neraca():
    conn = get_db(); c = conn.cursor()
    # Aset = semua debit akun aset
    c.execute("SELECT akun_debit as akun, SUM(nominal) as total FROM jurnal_umum WHERE akun_debit LIKE 'Kas%' OR akun_debit LIKE 'Piutang%' OR akun_debit LIKE 'Persediaan%' GROUP BY akun_debit")
    aset_lancar = [dict(r) for r in c.fetchall()]
    # Kewajiban
    c.execute("SELECT akun_kredit as akun, SUM(nominal) as total FROM jurnal_umum WHERE akun_kredit LIKE 'Hutang%' GROUP BY akun_kredit")
    kewajiban = [dict(r) for r in c.fetchall()]
    # Ekuitas
    c.execute("SELECT SUM(nominal) FROM ekuitas WHERE jenis='Modal'")
    modal = c.fetchone()[0] or 0
    c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE kategori='Pendapatan'")
    pend_total = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE kategori='Beban'")
    beban_total = c.fetchone()[0]
    laba = pend_total - beban_total
    tot_aset = sum(a['total'] for a in aset_lancar)
    tot_kwj = sum(k['total'] for k in kewajiban)
    conn.close()
    return jsonify({'aset_lancar':aset_lancar,'total_aset':tot_aset+laba,
                    'kewajiban':kewajiban,'total_kewajiban':tot_kwj,
                    'modal':modal,'laba_ditahan':laba,'total_ekuitas':modal+laba,
                    'total_kewajiban_ekuitas':tot_kwj+modal+laba})

@app.route('/api/laporan/arus_kas')
def api_arus_kas():
    bulan = request.args.get('bulan', date.today().strftime('%Y-%m'))
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM jurnal_umum WHERE (akun_debit='Kas' OR akun_kredit='Kas') AND tanggal LIKE ? ORDER BY tanggal", (f'{bulan}%',))
    rows = [dict(r) for r in c.fetchall()]
    kas_masuk = [r for r in rows if r['akun_debit']=='Kas']
    kas_keluar = [r for r in rows if r['akun_kredit']=='Kas']
    tot_masuk = sum(r['nominal'] for r in kas_masuk)
    tot_keluar = sum(r['nominal'] for r in kas_keluar)
    conn.close()
    return jsonify({'bulan':bulan,'kas_masuk':kas_masuk,'kas_keluar':kas_keluar,
                    'total_masuk':tot_masuk,'total_keluar':tot_keluar,'saldo_kas':tot_masuk-tot_keluar})

@app.route('/api/laporan/ekuitas')
def api_ekuitas():
    bulan = request.args.get('bulan', date.today().strftime('%Y-%m'))
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM ekuitas ORDER BY tanggal")
    rows = [dict(r) for r in c.fetchall()]
    c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE kategori='Pendapatan' AND tanggal LIKE ?", (f'{bulan}%',))
    pend = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE kategori='Beban' AND tanggal LIKE ?", (f'{bulan}%',))
    beban = c.fetchone()[0]
    modal_awal = sum(r['nominal'] for r in rows if r['jenis']=='Modal')
    prive = sum(r['nominal'] for r in rows if r['jenis']=='Prive')
    conn.close()
    return jsonify({'bulan':bulan,'modal_awal':modal_awal,'laba_periode':pend-beban,
                    'prive':prive,'modal_akhir':modal_awal+(pend-beban)-prive,'detail':rows})

@app.route('/api/akun')
def api_akun_list():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM akun ORDER BY kode")
    rows = [dict(r) for r in c.fetchall()]; conn.close()
    return jsonify({'data':rows})

if __name__ == '__main__':
    init_db()
    print("\n" + "="*50)
    print("  AgroSIM v2.0 — BetaFarm")
    print("  http://localhost:5000")
    print("="*50 + "\n")
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
