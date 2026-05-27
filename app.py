"""
AgroSIM v3.0 - BetaFarm
Auto-Posting Double Entry Accounting System
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

# ═══════════════════════════════════════════════
# CHART OF ACCOUNTS (COA)
# ═══════════════════════════════════════════════
COA = {
    # ASET
    '1-100': ('Kas',                          'Aset',      'Aset Lancar',    'D'),
    '1-110': ('Piutang Usaha',                'Aset',      'Aset Lancar',    'D'),
    '1-120': ('Persediaan Benih',             'Aset',      'Aset Lancar',    'D'),
    '1-130': ('Persediaan Pupuk & Nutrisi',   'Aset',      'Aset Lancar',    'D'),
    '1-140': ('Persediaan Pestisida',         'Aset',      'Aset Lancar',    'D'),
    '1-150': ('Beban Dibayar Dimuka',         'Aset',      'Aset Lancar',    'D'),
    '1-200': ('Genset',                       'Aset',      'Aset Tetap',     'D'),
    '1-210': ('Peralatan Kebun',              'Aset',      'Aset Tetap',     'D'),
    '1-211': ('Akum. Penyusutan Peralatan',   'Aset',      'Aset Tetap',     'K'),
    '1-220': ('Bangunan/Gedung',              'Aset',      'Aset Tetap',     'D'),
    # KEWAJIBAN
    '2-100': ('Hutang Usaha',                 'Kewajiban', 'Kewajiban Lancar','K'),
    '2-110': ('Hutang Gaji',                  'Kewajiban', 'Kewajiban Lancar','K'),
    '2-120': ('Pendapatan Diterima Dimuka',   'Kewajiban', 'Kewajiban Lancar','K'),
    # EKUITAS
    '3-100': ('Modal Benny',                  'Ekuitas',   'Ekuitas',        'K'),
    '3-200': ('Prive Benny',                  'Ekuitas',   'Ekuitas',        'D'),
    '3-300': ('Ikhtisar Laba Rugi',           'Ekuitas',   'Ekuitas',        'K'),
    # PENDAPATAN
    '4-100': ('Pendapatan Panen Grade A',     'Pendapatan','Pendapatan',     'K'),
    '4-110': ('Pendapatan Panen Grade B',     'Pendapatan','Pendapatan',     'K'),
    '4-120': ('Pendapatan Panen Grade C',     'Pendapatan','Pendapatan',     'K'),
    '4-200': ('Pendapatan Lain-lain',         'Pendapatan','Pendapatan',     'K'),
    # BEBAN
    '5-100': ('Beban Gaji Karyawan',          'Beban',     'Beban Operasional','D'),
    '5-110': ('Beban Upah Panen Lepas',       'Beban',     'Beban Operasional','D'),
    '5-200': ('Beban Benih',                  'Beban',     'Beban Produksi', 'D'),
    '5-210': ('Beban Pupuk & Nutrisi',        'Beban',     'Beban Produksi', 'D'),
    '5-220': ('Beban Pestisida',              'Beban',     'Beban Produksi', 'D'),
    '5-300': ('Beban Penyusutan Peralatan',   'Beban',     'Beban Operasional','D'),
    '5-400': ('Beban Perawatan & Servis',     'Beban',     'Beban Operasional','D'),
    '5-500': ('Beban Operasional Lain',       'Beban',     'Beban Operasional','D'),
}

def kode_akun(nama):
    for k,v in COA.items():
        if v[0] == nama:
            return k
    return '9-999'

# ═══════════════════════════════════════════════
# AUTO-POSTING ENGINE
# Mapping jenis transaksi → [[(debit_akun, kredit_akun)], kategori, sumber]
# ═══════════════════════════════════════════════
POSTING_RULES = {
    # PEMBELIAN CASH
    'beli_pupuk_cash':      [('Persediaan Pupuk & Nutrisi', 'Kas'), 'Beban', 'gudang'],
    'beli_pestisida_cash':  [('Persediaan Pestisida',       'Kas'), 'Beban', 'gudang'],
    'beli_benih_cash':      [('Persediaan Benih',           'Kas'), 'Beban', 'gudang'],
    'beli_alat_cash':       [('Peralatan Kebun',            'Kas'), 'Beban', 'gudang'],
    # PEMBELIAN KREDIT
    'beli_pupuk_kredit':    [('Persediaan Pupuk & Nutrisi', 'Hutang Usaha'), 'Beban', 'gudang'],
    'beli_pestisida_kredit':[('Persediaan Pestisida',       'Hutang Usaha'), 'Beban', 'gudang'],
    'beli_benih_kredit':    [('Persediaan Benih',           'Hutang Usaha'), 'Beban', 'gudang'],
    'beli_alat_kredit':     [('Peralatan Kebun',            'Hutang Usaha'), 'Beban', 'gudang'],
    # PENJUALAN CASH
    'jual_a_cash':          [('Kas',           'Pendapatan Panen Grade A'), 'Pendapatan', 'produksi'],
    'jual_b_cash':          [('Kas',           'Pendapatan Panen Grade B'), 'Pendapatan', 'produksi'],
    'jual_c_cash':          [('Kas',           'Pendapatan Panen Grade C'), 'Pendapatan', 'produksi'],
    # PENJUALAN KREDIT
    'jual_a_kredit':        [('Piutang Usaha', 'Pendapatan Panen Grade A'), 'Pendapatan', 'produksi'],
    'jual_b_kredit':        [('Piutang Usaha', 'Pendapatan Panen Grade B'), 'Pendapatan', 'produksi'],
    'jual_c_kredit':        [('Piutang Usaha', 'Pendapatan Panen Grade C'), 'Pendapatan', 'produksi'],
    # PENERIMAAN PIUTANG
    'terima_piutang':       [('Kas',           'Piutang Usaha'),            'Aset',       'manual'],
    # BAYAR HUTANG
    'bayar_hutang':         [('Hutang Usaha',  'Kas'),                      'Kewajiban',  'manual'],
    # GAJI CASH
    'gaji_cash':            [('Beban Gaji Karyawan', 'Kas'),                'Beban',      'sdm'],
    'upah_panen_cash':      [('Beban Upah Panen Lepas', 'Kas'),             'Beban',      'sdm'],
    # GAJI AKRUAL (hutang gaji)
    'gaji_akrual':          [('Beban Gaji Karyawan', 'Hutang Gaji'),        'Beban',      'sdm'],
    'bayar_hutang_gaji':    [('Hutang Gaji',   'Kas'),                      'Kewajiban',  'sdm'],
    # PEMAKAIAN PERSEDIAAN (stok keluar)
    'pakai_pupuk':          [('Beban Pupuk & Nutrisi', 'Persediaan Pupuk & Nutrisi'), 'Beban', 'gudang'],
    'pakai_pestisida':      [('Beban Pestisida', 'Persediaan Pestisida'),   'Beban',      'gudang'],
    'pakai_benih':          [('Beban Benih',   'Persediaan Benih'),         'Beban',      'gudang'],
    # PERAWATAN & SERVIS
    'servis_cash':          [('Beban Perawatan & Servis', 'Kas'),           'Beban',      'gudang'],
    'biaya_lain_cash':      [('Beban Operasional Lain',   'Kas'),           'Beban',      'manual'],
    # PENYUSUTAN
    'penyusutan':           [('Beban Penyusutan Peralatan','Akum. Penyusutan Peralatan'),'Beban','manual'],
    # MODAL & PRIVE
    'modal_masuk':          [('Kas',           'Modal Benny'),              'Ekuitas',    'manual'],
    'prive':                [('Prive Benny',   'Kas'),                      'Ekuitas',    'manual'],
}

def auto_post(conn, tanggal, ref, keterangan, kode_jenis, nominal):
    """Engine utama: 1 transaksi → otomatis posting ke semua jurnal"""
    if kode_jenis not in POSTING_RULES:
        return False
    rule = POSTING_RULES[kode_jenis]
    debit_akun, kredit_akun = rule[0]
    kategori = rule[1]
    sumber = rule[2]
    conn.execute("""INSERT INTO jurnal_umum
        (tanggal,no_referensi,keterangan,akun_debit,akun_kredit,nominal,kategori,sumber,jenis_transaksi)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (tanggal, ref, keterangan, debit_akun, kredit_akun, nominal, kategori, sumber, kode_jenis))
    return True

# ═══════════════════════════════════════════════
# DATABASE INIT
# ═══════════════════════════════════════════════
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
        no_hp TEXT, status TEXT DEFAULT 'aktif')''')

    c.execute('''CREATE TABLE IF NOT EXISTS absensi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        karyawan_id INTEGER NOT NULL, tanggal TEXT NOT NULL,
        status TEXT NOT NULL, lembur_jam REAL DEFAULT 0,
        FOREIGN KEY (karyawan_id) REFERENCES karyawan(id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS gudang (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama_barang TEXT NOT NULL, kategori TEXT NOT NULL, satuan TEXT NOT NULL,
        stok_awal REAL DEFAULT 0, stok_sekarang REAL DEFAULT 0,
        harga_satuan REAL DEFAULT 0, stok_minimum REAL DEFAULT 0,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS transaksi_gudang (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barang_id INTEGER NOT NULL, tanggal TEXT NOT NULL,
        jenis TEXT NOT NULL, jumlah REAL NOT NULL,
        harga_satuan REAL DEFAULT 0, total REAL DEFAULT 0,
        keterangan TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS jurnal_umum (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tanggal TEXT NOT NULL, no_referensi TEXT,
        keterangan TEXT NOT NULL,
        akun_debit TEXT NOT NULL, akun_kredit TEXT NOT NULL,
        nominal REAL NOT NULL, kategori TEXT,
        sumber TEXT DEFAULT 'manual',
        jenis_transaksi TEXT,
        posted INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS akun_saldo (
        akun TEXT PRIMARY KEY,
        saldo REAL DEFAULT 0,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS jurnal_penyesuaian (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tanggal TEXT NOT NULL, keterangan TEXT NOT NULL,
        akun_debit TEXT NOT NULL, akun_kredit TEXT NOT NULL,
        nominal REAL NOT NULL, jenis TEXT,
        periode TEXT, is_reversed INTEGER DEFAULT 0)''')

    c.execute("SELECT COUNT(*) FROM karyawan")
    if c.fetchone()[0] == 0:
        _seed(c)

    conn.commit(); conn.close()

def _seed(c):
    UMR = 2467488; UMR_H = round(UMR/26)
    c.executemany("INSERT INTO karyawan (nama,jabatan,upah_harian,no_hp) VALUES (?,?,?,?)", [
       ('Beni Supriyatno','Owner / Pengelola Keuangan',0,'-'),
        ('Aditya Kholifatus Sabil','Supervisor',UMR_H,'-'),
        ('Mohammad Faizin','Petugas Kebun',UMR_H,'-'),
        ('Ali Rahmadhani','Petugas Kebun',UMR_H,'-'),
    ])
    c.executemany("INSERT INTO gudang (nama_barang,kategori,satuan,stok_awal,stok_sekarang,harga_satuan,stok_minimum) VALUES (?,?,?,?,?,?,?)", [
        ('Benih Melon SW9 Thailand','Benih','Pack',10,7,500000,2),
        ('Benih Melon Lokal (Uji Coba)','Benih','Pack',5,3,500000,1),
        ('Nutrisi Abemix Komponen A','Pupuk','Liter',40,22,85000,8),
        ('Nutrisi Abemix Komponen B','Pupuk','Liter',40,20,85000,8),
        ('Pupuk Daun (Foliar Spray)','Pupuk','Liter',20,12,75000,4),
        ('Insektisida Anti Kutu Kebul','Pestisida','Botol',20,10,95000,4),
        ('Fungisida (Anti Jamur)','Pestisida','Botol',15,8,85000,3),
        ('Sprayer / Alat Semprot','Alat','Unit',4,3,600000,1),
        ('Genset','Alat','Unit',1,1,60000000,1),
        ('Tali Rambatan Melon','Alat','Meter',500,320,1500,100),
        ('Spare Part Desle / Diesel','Alat','Set',2,1,6000000,1),
    ])
    # Seed jurnal pakai auto_post engine
    today = date.today()
    p1 = (today-timedelta(days=120)).isoformat()
    p2 = (today-timedelta(days=60)).isoformat()
    POPULASI=2000; buah=int(POPULASI*0.85)
    gA=int(buah*0.6); gB=int(buah*0.3); gC=buah-gA-gB

    entries = [
        # Modal awal
        ((today-timedelta(days=200)).isoformat(),'BF-M001','Modal awal Benny','modal_masuk',50000000),
        # Beli benih
        ((today-timedelta(days=185)).isoformat(),'BF-B001','Pembelian Benih SW9 10 pack','beli_benih_cash',5000000),
        ((today-timedelta(days=185)).isoformat(),'BF-B002','Pembelian Benih Lokal 5 pack','beli_benih_cash',2500000),
        # Beli pupuk siklus 1
        ((today-timedelta(days=170)).isoformat(),'BF-P001','Beli Nutrisi Abemix & Pupuk Daun Siklus 1 Bln 1','beli_pupuk_cash',980000),
        ((today-timedelta(days=140)).isoformat(),'BF-P002','Beli Nutrisi Abemix & Pupuk Daun Siklus 1 Bln 2','beli_pupuk_cash',980000),
        # Beli pestisida siklus 1
        ((today-timedelta(days=165)).isoformat(),'BF-O001','Beli Insektisida & Fungisida Siklus 1','beli_pestisida_cash',1100000),
        # Gaji siklus 1 & 2
        ((today-timedelta(days=150)).isoformat(),'BF-G001',f'Gaji 3 Karyawan Bln 1 (UMR Rp{UMR:,})','gaji_cash',3*UMR),
        ((today-timedelta(days=120)).isoformat(),'BF-G002',f'Gaji 3 Karyawan Bln 2 (UMR Rp{UMR:,})','gaji_cash',3*UMR),
        # Panen siklus 1
        (p1,'BF-J001',f'Penjualan Melon Grade A {gA} buah × Rp25.000','jual_a_cash',gA*25000),
        (p1,'BF-J002',f'Penjualan Melon Grade B {gB} buah × Rp20.000','jual_b_cash',gB*20000),
        (p1,'BF-J003',f'Penjualan Melon Grade C {gC} buah × Rp15.000','jual_c_cash',gC*15000),
        (p1,'BF-T001','Upah Tenaga Panen Lepas Siklus 1','upah_panen_cash',750000),
        # Beli pupuk siklus 2
        ((today-timedelta(days=110)).isoformat(),'BF-P003','Beli Nutrisi Abemix & Pupuk Daun Siklus 2 Bln 1','beli_pupuk_cash',980000),
        ((today-timedelta(days=80)).isoformat(),'BF-P004','Beli Nutrisi Abemix & Pupuk Daun Siklus 2 Bln 2','beli_pupuk_cash',980000),
        # Beli pestisida siklus 2
        ((today-timedelta(days=105)).isoformat(),'BF-O002','Beli Insektisida & Fungisida Siklus 2','beli_pestisida_cash',1100000),
        # Gaji siklus 2
        ((today-timedelta(days=90)).isoformat(),'BF-G003',f'Gaji 3 Karyawan Bln 3 (UMR Rp{UMR:,})','gaji_cash',3*UMR),
        ((today-timedelta(days=60)).isoformat(),'BF-G004',f'Gaji 3 Karyawan Bln 4 (UMR Rp{UMR:,})','gaji_cash',3*UMR),
        # Panen siklus 2
        (p2,'BF-J004',f'Penjualan Melon Grade A {gA} buah × Rp25.000','jual_a_cash',gA*25000),
        (p2,'BF-J005',f'Penjualan Melon Grade B {gB} buah × Rp20.000','jual_b_cash',gB*20000),
        (p2,'BF-J006',f'Penjualan Melon Grade C {gC} buah × Rp15.000','jual_c_cash',gC*15000),
        (p2,'BF-T002','Upah Tenaga Panen Lepas Siklus 2','upah_panen_cash',750000),
        # Perawatan alat
        ((today-timedelta(days=30)).isoformat(),'BF-A001','Beli Sprayer Pengganti (beli online)','servis_cash',600000),
        ((today-timedelta(days=15)).isoformat(),'BF-A002','Servis Desle/Diesel Genset','servis_cash',6000000),
    ]

    for tgl,ref,ket,jenis,nominal in entries:
        rule = POSTING_RULES[jenis]
        debit, kredit = rule[0]
        kategori = rule[1]
        sumber = rule[2]
        c.execute("""INSERT INTO jurnal_umum
            (tanggal,no_referensi,keterangan,akun_debit,akun_kredit,nominal,kategori,sumber,jenis_transaksi)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (tgl,ref,ket,debit,kredit,nominal,kategori,sumber,jenis))

    # Seed produksi
    for tgl,siklus in [(p1,'Siklus 1'),(p2,'Siklus 2')]:
        for jml,kual,harga in [(gA,'A',25000),(gB,'B',20000),(gC,'C',15000)]:
            c.execute("INSERT INTO produksi (tanggal,komoditas,blok,jumlah_buah,kualitas,harga_per_buah,catatan) VALUES (?,?,?,?,?,?,?)",
                      (tgl,'Melon SW9 Thailand','Gedung 1 & 2',jml,kual,harga,f'{siklus} — {jml} buah Grade {kual}'))

# ═══════════════════════════════════════════════
# HELPER: SALDO BUKU BESAR
# ═══════════════════════════════════════════════
def get_saldo_akun(c, akun, sampai_tanggal=None):
    if sampai_tanggal:
        c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE akun_debit=? AND tanggal<=? AND posted=1",(akun,sampai_tanggal))
        d = c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE akun_kredit=? AND tanggal<=? AND posted=1",(akun,sampai_tanggal))
        k = c.fetchone()[0]
    else:
        c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE akun_debit=? AND posted=1",(akun,))
        d = c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE akun_kredit=? AND posted=1",(akun,))
        k = c.fetchone()[0]
    return d, k

# ═══════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════
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

# ═══════════════════════════════════════════════
# API DASHBOARD
# ═══════════════════════════════════════════════
@app.route('/api/dashboard')
def api_dashboard():
    conn = get_db(); c = conn.cursor()
    periode = request.args.get('periode','bulan_ini')
    tgl_mulai = request.args.get('tgl_mulai','')
    tgl_akhir = request.args.get('tgl_akhir','')
    today = date.today()
    if periode=='7hari':
        d_from=(today-timedelta(days=7)).isoformat(); d_to=today.isoformat()
    elif periode=='30hari':
        d_from=(today-timedelta(days=30)).isoformat(); d_to=today.isoformat()
    elif periode=='bulan_lalu':
        f=today.replace(day=1); lm=f-timedelta(days=1)
        d_from=lm.replace(day=1).isoformat(); d_to=lm.isoformat()
    elif periode=='tahun_ini':
        d_from=today.replace(month=1,day=1).isoformat(); d_to=today.isoformat()
    elif periode=='custom' and tgl_mulai and tgl_akhir:
        d_from=tgl_mulai; d_to=tgl_akhir
    else:
        d_from=today.replace(day=1).isoformat(); d_to=today.isoformat()

    c.execute("SELECT COALESCE(SUM(jumlah_buah),0) FROM produksi WHERE tanggal BETWEEN ? AND ?",(d_from,d_to))
    total_panen=c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(jumlah_buah*harga_per_buah),0) FROM produksi WHERE tanggal BETWEEN ? AND ?",(d_from,d_to))
    total_nilai_panen=c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE kategori='Pendapatan' AND tanggal BETWEEN ? AND ? AND posted=1",(d_from,d_to))
    total_pendapatan=c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE kategori='Beban' AND tanggal BETWEEN ? AND ? AND posted=1",(d_from,d_to))
    total_beban=c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM karyawan WHERE status='aktif'")
    jumlah_karyawan=c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM gudang WHERE stok_sekarang<=stok_minimum AND stok_minimum>0")
    stok_kritis=c.fetchone()[0]

    grafik_produksi=[]
    if periode in ['7hari','bulan_ini']:
        days=7 if periode=='7hari' else 30
        for i in range(days-1,-1,-1):
            tgl=(today-timedelta(days=i)).isoformat()
            c.execute("SELECT COALESCE(SUM(jumlah_buah),0) FROM produksi WHERE tanggal=?",(tgl,))
            grafik_produksi.append({'tanggal':tgl,'berat':c.fetchone()[0]})
    else:
        c.execute("SELECT substr(tanggal,1,7) as bln,COALESCE(SUM(jumlah_buah),0) as total FROM produksi WHERE tanggal BETWEEN ? AND ? GROUP BY bln ORDER BY bln",(d_from,d_to))
        for r in c.fetchall():
            grafik_produksi.append({'tanggal':r['bln'],'berat':r['total']})

    grafik_keuangan=[]
    for i in range(5,-1,-1):
        bln=(today.replace(day=1)-timedelta(days=i*28)).strftime('%Y-%m')
        c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE kategori='Pendapatan' AND tanggal LIKE ? AND posted=1",(f'{bln}%',))
        pend=c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE kategori='Beban' AND tanggal LIKE ? AND posted=1",(f'{bln}%',))
        beban=c.fetchone()[0]
        grafik_keuangan.append({'bulan':bln,'pendapatan':pend,'beban':beban})

    c.execute("""SELECT 'Panen' as jenis,tanggal,komoditas||' '||jumlah_buah||' buah' as deskripsi FROM produksi
                 UNION ALL SELECT 'Jurnal',tanggal,keterangan FROM jurnal_umum WHERE posted=1
                 ORDER BY tanggal DESC LIMIT 8""")
    aktivitas=[dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify({'total_panen':total_panen,'total_nilai_panen':total_nilai_panen,
                    'total_pendapatan':total_pendapatan,'total_beban':total_beban,
                    'laba_bersih':total_pendapatan-total_beban,'jumlah_karyawan':jumlah_karyawan,
                    'stok_kritis':stok_kritis,'grafik_produksi':grafik_produksi,
                    'grafik_keuangan':grafik_keuangan,'aktivitas':aktivitas,
                    'periode':periode,'d_from':d_from,'d_to':d_to})

# ═══════════════════════════════════════════════
# API AUTO-POSTING (INTI SISTEM)
# ═══════════════════════════════════════════════
@app.route('/api/transaksi', methods=['POST'])
def api_transaksi():
    """Endpoint utama — 1 input → auto post ke semua jurnal"""
    d = request.json
    tanggal = d['tanggal']
    keterangan = d['keterangan']
    nominal = float(d['nominal'])
    jenis = d['jenis']  # e.g. 'beli_pupuk_cash'
    ref = d.get('ref','')

    if not ref:
        # Auto generate ref
        conn = get_db(); c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM jurnal_umum")
        n = c.fetchone()[0]
        conn.close()
        ref = f'TRX-{date.today().strftime("%Y%m")}-{n+1:04d}'

    if jenis not in POSTING_RULES:
        return jsonify({'success':False,'error':'Jenis transaksi tidak dikenal'})

    conn = get_db()
    ok = auto_post(conn, tanggal, ref, keterangan, jenis, nominal)
    if ok:
        conn.commit()
    conn.close()

    if ok:
        return jsonify({'success':True,'ref':ref,'message':f'Transaksi berhasil diposting ke jurnal'})
    return jsonify({'success':False,'error':'Gagal posting'})

@app.route('/api/posting_rules')
def api_posting_rules():
    """Kirim semua rules ke frontend untuk preview otomatis"""
    rules = {k: {'debit':v[0][0],'kredit':v[0][1],'kategori':v[1]} for k,v in POSTING_RULES.items()}
    return jsonify(rules)

# ═══════════════════════════════════════════════
# API JURNAL UMUM
# ═══════════════════════════════════════════════
@app.route('/api/jurnal_umum')
def api_jurnal_umum():
    bulan = request.args.get('bulan', date.today().strftime('%Y-%m'))
    sumber = request.args.get('sumber','semua')
    conn = get_db(); c = conn.cursor()
    if sumber=='semua':
        c.execute("SELECT * FROM jurnal_umum WHERE tanggal LIKE ? AND posted=1 ORDER BY tanggal,id",(f'{bulan}%',))
    else:
        c.execute("SELECT * FROM jurnal_umum WHERE tanggal LIKE ? AND sumber=? AND posted=1 ORDER BY tanggal,id",(f'{bulan}%',sumber))
    rows=[dict(r) for r in c.fetchall()]
    c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE kategori='Pendapatan' AND tanggal LIKE ? AND posted=1",(f'{bulan}%',))
    pend=c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE kategori='Beban' AND tanggal LIKE ? AND posted=1",(f'{bulan}%',))
    beban=c.fetchone()[0]
    conn.close()
    return jsonify({'data':rows,'pendapatan':pend,'beban':beban,'laba':pend-beban})

@app.route('/api/jurnal_umum/<int:id>', methods=['DELETE'])
def api_jurnal_delete(id):
    conn=get_db(); conn.execute("UPDATE jurnal_umum SET posted=0 WHERE id=?",(id,)); conn.commit(); conn.close()
    return jsonify({'success':True})

# ═══════════════════════════════════════════════
# API BUKU BESAR (real-time dari jurnal)
# ═══════════════════════════════════════════════
@app.route('/api/buku_besar')
def api_buku_besar():
    akun = request.args.get('akun','Kas')
    bulan = request.args.get('bulan', date.today().strftime('%Y-%m'))
    conn = get_db(); c = conn.cursor()
    # Saldo awal (sebelum bulan ini)
    tgl_awal = bulan + '-01'
    c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE akun_debit=? AND tanggal<? AND posted=1",(akun,tgl_awal))
    saldo_awal_d = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE akun_kredit=? AND tanggal<? AND posted=1",(akun,tgl_awal))
    saldo_awal_k = c.fetchone()[0]
    saldo_awal = saldo_awal_d - saldo_awal_k

    c.execute("""SELECT * FROM jurnal_umum WHERE (akun_debit=? OR akun_kredit=?) AND tanggal LIKE ? AND posted=1
                 ORDER BY tanggal,id""",(akun,akun,f'{bulan}%'))
    rows=[]; saldo=saldo_awal
    for r in c.fetchall():
        r=dict(r)
        if r['akun_debit']==akun:
            r['posisi']='D'; saldo+=r['nominal']
        else:
            r['posisi']='K'; saldo-=r['nominal']
        r['saldo']=saldo
        rows.append(r)

    # Daftar semua akun
    c.execute("SELECT DISTINCT akun_debit as a FROM jurnal_umum WHERE posted=1 UNION SELECT DISTINCT akun_kredit FROM jurnal_umum WHERE posted=1 ORDER BY a")
    semua_akun=[r['a'] for r in c.fetchall()]
    conn.close()
    return jsonify({'data':rows,'akun':akun,'saldo_awal':saldo_awal,'saldo_akhir':saldo,'semua_akun':semua_akun})

# ═══════════════════════════════════════════════
# API NERACA SALDO (auto dari buku besar)
# ═══════════════════════════════════════════════
@app.route('/api/neraca_saldo')
def api_neraca_saldo():
    bulan = request.args.get('bulan', date.today().strftime('%Y-%m'))
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT DISTINCT akun_debit as a FROM jurnal_umum WHERE posted=1
                 UNION SELECT DISTINCT akun_kredit FROM jurnal_umum WHERE posted=1 ORDER BY a""")
    akun_list=[r['a'] for r in c.fetchall()]
    result=[]
    for akun in akun_list:
        c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE akun_debit=? AND tanggal LIKE ? AND posted=1",(akun,f'{bulan}%'))
        d=c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE akun_kredit=? AND tanggal LIKE ? AND posted=1",(akun,f'{bulan}%'))
        k=c.fetchone()[0]
        if d>0 or k>0:
            result.append({'akun':akun,'debit':d,'kredit':k,'saldo_d':max(d-k,0),'saldo_k':max(k-d,0)})
    conn.close()
    return jsonify({'data':result,'bulan':bulan})

# ═══════════════════════════════════════════════
# API JURNAL PENYESUAIAN
# ═══════════════════════════════════════════════
@app.route('/api/penyesuaian', methods=['GET'])
def api_penyesuaian_list():
    bulan = request.args.get('bulan', date.today().strftime('%Y-%m'))
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM jurnal_penyesuaian WHERE periode LIKE ? ORDER BY tanggal",(f'{bulan}%',))
    rows=[dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify({'data':rows})

@app.route('/api/penyesuaian', methods=['POST'])
def api_penyesuaian_add():
    d = request.json; conn = get_db()
    conn.execute("INSERT INTO jurnal_penyesuaian (tanggal,keterangan,akun_debit,akun_kredit,nominal,jenis,periode) VALUES (?,?,?,?,?,?,?)",
                 (d['tanggal'],d['keterangan'],d['akun_debit'],d['akun_kredit'],float(d['nominal']),d.get('jenis',''),d['tanggal'][:7]))
    # Auto post ke jurnal umum juga
    conn.execute("INSERT INTO jurnal_umum (tanggal,keterangan,akun_debit,akun_kredit,nominal,kategori,sumber,jenis_transaksi) VALUES (?,?,?,?,?,?,?,?)",
                 (d['tanggal'],f"[Penyesuaian] {d['keterangan']}",d['akun_debit'],d['akun_kredit'],float(d['nominal']),'Penyesuaian','penyesuaian',d.get('jenis','')))
    conn.commit(); conn.close()
    return jsonify({'success':True})

# ═══════════════════════════════════════════════
# API LAPORAN (semua otomatis dari jurnal)
# ═══════════════════════════════════════════════
@app.route('/api/laporan/laba_rugi')
def api_laba_rugi():
    bulan = request.args.get('bulan', date.today().strftime('%Y-%m'))
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT akun_kredit as akun,SUM(nominal) as total FROM jurnal_umum WHERE kategori='Pendapatan' AND tanggal LIKE ? AND posted=1 GROUP BY akun_kredit",(f'{bulan}%',))
    pendapatan=[dict(r) for r in c.fetchall()]
    c.execute("SELECT akun_debit as akun,SUM(nominal) as total FROM jurnal_umum WHERE kategori='Beban' AND tanggal LIKE ? AND posted=1 GROUP BY akun_debit",(f'{bulan}%',))
    beban=[dict(r) for r in c.fetchall()]
    tp=sum(p['total'] for p in pendapatan); tb=sum(b['total'] for b in beban)
    conn.close()
    return jsonify({'bulan':bulan,'pendapatan':pendapatan,'beban':beban,'total_pendapatan':tp,'total_beban':tb,'laba_bersih':tp-tb})

@app.route('/api/laporan/neraca')
def api_neraca():
    conn = get_db(); c = conn.cursor()
    def saldo(akun):
        d,k = get_saldo_akun(c,akun)
        return d-k
    kas=saldo('Kas'); piutang=saldo('Piutang Usaha')
    pers_benih=saldo('Persediaan Benih'); pers_pupuk=saldo('Persediaan Pupuk & Nutrisi')
    pers_pest=saldo('Persediaan Pestisida'); peralatan=saldo('Peralatan Kebun')
    akum=abs(saldo('Akum. Penyusutan Peralatan'))
    hutang=abs(saldo('Hutang Usaha')); hutang_gaji=abs(saldo('Hutang Gaji'))
    modal=abs(saldo('Modal Benny')); prive=saldo('Prive Benny')
    c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE kategori='Pendapatan' AND posted=1")
    tp=c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE kategori='Beban' AND posted=1")
    tb=c.fetchone()[0]
    laba=tp-tb
    aset_lancar={'Kas':kas,'Piutang Usaha':piutang,'Persediaan Benih':pers_benih,
                 'Persediaan Pupuk & Nutrisi':pers_pupuk,'Persediaan Pestisida':pers_pest}
    aset_tetap={'Peralatan Kebun':peralatan,'Akum. Penyusutan':f'({akum})'}
    tot_aset_lancar=sum(v for v in aset_lancar.values() if isinstance(v,float))
    tot_aset_tetap=peralatan-akum
    tot_aset=tot_aset_lancar+tot_aset_tetap
    tot_kwj=hutang+hutang_gaji
    tot_ekuitas=modal+laba-prive
    conn.close()
    return jsonify({'aset_lancar':aset_lancar,'aset_tetap':{'Peralatan Kebun':peralatan,'Akum. Penyusutan':-akum},
                    'total_aset_lancar':tot_aset_lancar,'total_aset_tetap':tot_aset_tetap,'total_aset':tot_aset,
                    'hutang_usaha':hutang,'hutang_gaji':hutang_gaji,'total_kewajiban':tot_kwj,
                    'modal':modal,'laba_ditahan':laba,'prive':prive,'total_ekuitas':tot_ekuitas,
                    'total_kewajiban_ekuitas':tot_kwj+tot_ekuitas})

@app.route('/api/laporan/arus_kas')
def api_arus_kas():
    bulan = request.args.get('bulan', date.today().strftime('%Y-%m'))
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM jurnal_umum WHERE akun_debit='Kas' AND tanggal LIKE ? AND posted=1 ORDER BY tanggal",(f'{bulan}%',))
    masuk=[dict(r) for r in c.fetchall()]
    c.execute("SELECT * FROM jurnal_umum WHERE akun_kredit='Kas' AND tanggal LIKE ? AND posted=1 ORDER BY tanggal",(f'{bulan}%',))
    keluar=[dict(r) for r in c.fetchall()]
    tm=sum(r['nominal'] for r in masuk); tk=sum(r['nominal'] for r in keluar)
    conn.close()
    return jsonify({'bulan':bulan,'kas_masuk':masuk,'kas_keluar':keluar,'total_masuk':tm,'total_keluar':tk,'saldo_kas':tm-tk})

@app.route('/api/laporan/ekuitas')
def api_ekuitas():
    bulan = request.args.get('bulan', date.today().strftime('%Y-%m'))
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE akun_kredit='Modal Benny' AND posted=1")
    modal=c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE kategori='Pendapatan' AND tanggal LIKE ? AND posted=1",(f'{bulan}%',))
    pend=c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE kategori='Beban' AND tanggal LIKE ? AND posted=1",(f'{bulan}%',))
    beban=c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(nominal),0) FROM jurnal_umum WHERE akun_debit='Prive Benny' AND tanggal LIKE ? AND posted=1",(f'{bulan}%',))
    prive=c.fetchone()[0]
    laba=pend-beban
    conn.close()
    return jsonify({'bulan':bulan,'modal_awal':modal,'laba_periode':laba,'prive':prive,'modal_akhir':modal+laba-prive})

@app.route('/api/laporan/neraca_setelah_penyesuaian')
def api_neraca_setelah_penyesuaian():
    bulan = request.args.get('bulan', date.today().strftime('%Y-%m'))
    conn = get_db(); c = conn.cursor()
    c.execute("""SELECT DISTINCT akun_debit as a FROM jurnal_umum WHERE posted=1
                 UNION SELECT DISTINCT akun_kredit FROM jurnal_umum WHERE posted=1 ORDER BY a""")
    akun_list=[r['a'] for r in c.fetchall()]
    result=[]
    for akun in akun_list:
        d,k=get_saldo_akun(c,akun)
        if d>0 or k>0:
            result.append({'akun':akun,'debit':d,'kredit':k,'saldo':d-k})
    conn.close()
    return jsonify({'data':result,'bulan':bulan})

# ═══════════════════════════════════════════════
# API JURNAL PENUTUP (auto generate)
# ═══════════════════════════════════════════════
@app.route('/api/jurnal_penutup/generate', methods=['POST'])
def api_generate_penutup():
    bulan = request.json.get('bulan', date.today().strftime('%Y-%m'))
    tgl_tutup = bulan + '-30'
    conn = get_db(); c = conn.cursor()
    # Ambil semua pendapatan & beban bulan ini
    c.execute("SELECT akun_kredit as akun,SUM(nominal) as total FROM jurnal_umum WHERE kategori='Pendapatan' AND tanggal LIKE ? AND posted=1 GROUP BY akun_kredit",(f'{bulan}%',))
    pendapatan=[dict(r) for r in c.fetchall()]
    c.execute("SELECT akun_debit as akun,SUM(nominal) as total FROM jurnal_umum WHERE kategori='Beban' AND tanggal LIKE ? AND posted=1 GROUP BY akun_debit",(f'{bulan}%',))
    beban=[dict(r) for r in c.fetchall()]
    tp=sum(p['total'] for p in pendapatan); tb=sum(b['total'] for b in beban)
    laba=tp-tb
    penutup=[]
    for p in pendapatan:
        conn.execute("INSERT INTO jurnal_umum (tanggal,keterangan,akun_debit,akun_kredit,nominal,kategori,sumber,jenis_transaksi) VALUES (?,?,?,?,?,?,?,?)",
                     (tgl_tutup,f"[Penutup] Menutup {p['akun']}",p['akun'],'Ikhtisar Laba Rugi',p['total'],'Penutup','penutup','penutup_pendapatan'))
        penutup.append({'akun':p['akun'],'debit':p['total'],'kredit':0,'nominal':p['total']})
    for b in beban:
        conn.execute("INSERT INTO jurnal_umum (tanggal,keterangan,akun_debit,akun_kredit,nominal,kategori,sumber,jenis_transaksi) VALUES (?,?,?,?,?,?,?,?)",
                     (tgl_tutup,f"[Penutup] Menutup {b['akun']}",'Ikhtisar Laba Rugi',b['akun'],b['total'],'Penutup','penutup','penutup_beban'))
        penutup.append({'akun':b['akun'],'debit':0,'kredit':b['total'],'nominal':b['total']})
    if laba != 0:
        if laba > 0:
            conn.execute("INSERT INTO jurnal_umum (tanggal,keterangan,akun_debit,akun_kredit,nominal,kategori,sumber,jenis_transaksi) VALUES (?,?,?,?,?,?,?,?)",
                         (tgl_tutup,'[Penutup] Laba ke Modal Benny','Ikhtisar Laba Rugi','Modal Benny',abs(laba),'Penutup','penutup','penutup_laba'))
        else:
            conn.execute("INSERT INTO jurnal_umum (tanggal,keterangan,akun_debit,akun_kredit,nominal,kategori,sumber,jenis_transaksi) VALUES (?,?,?,?,?,?,?,?)",
                         (tgl_tutup,'[Penutup] Rugi dari Modal Benny','Modal Benny','Ikhtisar Laba Rugi',abs(laba),'Penutup','penutup','penutup_rugi'))
        penutup.append({'akun':'Modal Benny','debit':0 if laba>0 else abs(laba),'kredit':abs(laba) if laba>0 else 0,'nominal':abs(laba)})
    conn.commit(); conn.close()
    return jsonify({'success':True,'data':penutup,'laba':laba,'bulan':bulan})

# ═══════════════════════════════════════════════
# API JURNAL PEMBALIK (auto dari penyesuaian)
# ═══════════════════════════════════════════════
@app.route('/api/jurnal_pembalik/generate', methods=['POST'])
def api_generate_pembalik():
    bulan = request.json.get('bulan', date.today().strftime('%Y-%m'))
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM jurnal_penyesuaian WHERE periode LIKE ? AND is_reversed=0 AND jenis IN ('beban_byr','pend_belum')",(f'{bulan}%',))
    rows=[dict(r) for r in c.fetchall()]
    today_str=date.today().isoformat()
    pembalik=[]
    for r in rows:
        conn.execute("INSERT INTO jurnal_umum (tanggal,keterangan,akun_debit,akun_kredit,nominal,kategori,sumber,jenis_transaksi) VALUES (?,?,?,?,?,?,?,?)",
                     (today_str,f"[Pembalik] {r['keterangan']}",r['akun_kredit'],r['akun_debit'],r['nominal'],'Pembalik','pembalik','pembalik'))
        conn.execute("UPDATE jurnal_penyesuaian SET is_reversed=1 WHERE id=?",(r['id'],))
        pembalik.append(r)
    conn.commit(); conn.close()
    return jsonify({'success':True,'data':pembalik,'count':len(pembalik)})

# ═══════════════════════════════════════════════
# API PRODUKSI
# ═══════════════════════════════════════════════
@app.route('/api/produksi', methods=['GET'])
def api_produksi_list():
    conn=get_db(); c=conn.cursor()
    c.execute("SELECT * FROM produksi ORDER BY tanggal DESC LIMIT 100")
    rows=[dict(r) for r in c.fetchall()]
    c.execute("SELECT COALESCE(SUM(jumlah_buah),0),COALESCE(SUM(jumlah_buah*harga_per_buah),0),COUNT(*) FROM produksi")
    s=c.fetchone(); conn.close()
    return jsonify({'data':rows,'total_kg':s[0],'total_nilai':s[1],'total_transaksi':s[2]})

@app.route('/api/produksi', methods=['POST'])
def api_produksi_add():
    d=request.json; conn=get_db()
    jumlah=float(d['berat_kg']); harga=float(d.get('harga_per_kg',0)); kual=d.get('kualitas','A')
    conn.execute("INSERT INTO produksi (tanggal,komoditas,blok,jumlah_buah,kualitas,harga_per_buah,catatan) VALUES (?,?,?,?,?,?,?)",
                 (d['tanggal'],d['komoditas'],d.get('blok',''),jumlah,kual,harga,d.get('catatan','')))
    nilai=jumlah*harga
    if nilai>0:
        jenis_map={'A':'jual_a_cash','B':'jual_b_cash','C':'jual_c_cash'}
        jenis=jenis_map.get(kual,'jual_a_cash')
        auto_post(conn,d['tanggal'],'',f"Penjualan {d['komoditas']} Grade {kual} {jumlah} buah",jenis,nilai)
    conn.commit(); conn.close()
    return jsonify({'success':True})

@app.route('/api/produksi/<int:id>', methods=['DELETE'])
def api_produksi_delete(id):
    conn=get_db(); conn.execute("DELETE FROM produksi WHERE id=?",(id,)); conn.commit(); conn.close()
    return jsonify({'success':True})

# ═══════════════════════════════════════════════
# API SDM
# ═══════════════════════════════════════════════
@app.route('/api/karyawan', methods=['GET'])
def api_karyawan_list():
    conn=get_db(); c=conn.cursor()
    c.execute("SELECT * FROM karyawan ORDER BY nama")
    rows=[dict(r) for r in c.fetchall()]; conn.close()
    return jsonify({'data':rows})

@app.route('/api/karyawan', methods=['POST'])
def api_karyawan_add():
    d=request.json; conn=get_db()
    conn.execute("INSERT INTO karyawan (nama,jabatan,upah_harian,no_hp) VALUES (?,?,?,?)",
                 (d['nama'],d['jabatan'],float(d['upah_harian']),d.get('no_hp','')))
    conn.commit(); conn.close()
    return jsonify({'success':True})

@app.route('/api/karyawan/<int:id>', methods=['DELETE'])
def api_karyawan_delete(id):
    conn=get_db(); conn.execute("DELETE FROM karyawan WHERE id=?",(id,)); conn.commit(); conn.close()
    return jsonify({'success':True})

@app.route('/api/absensi', methods=['GET'])
def api_absensi_list():
    tanggal=request.args.get('tanggal',date.today().isoformat())
    conn=get_db(); c=conn.cursor()
    c.execute("""SELECT a.*,k.nama,k.jabatan,k.upah_harian FROM absensi a
                 JOIN karyawan k ON a.karyawan_id=k.id WHERE a.tanggal=? ORDER BY k.nama""",(tanggal,))
    rows=[dict(r) for r in c.fetchall()]; conn.close()
    return jsonify({'data':rows})

@app.route('/api/absensi', methods=['POST'])
def api_absensi_add():
    d=request.json; conn=get_db(); c=conn.cursor()
    c.execute("SELECT id FROM absensi WHERE karyawan_id=? AND tanggal=?",(d['karyawan_id'],d['tanggal']))
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
    bulan=request.args.get('bulan',date.today().strftime('%Y-%m'))
    conn=get_db(); c=conn.cursor()
    c.execute("SELECT * FROM karyawan WHERE status='aktif'")
    karyawan=[dict(r) for r in c.fetchall()]; result=[]
    for k in karyawan:
        c.execute("""SELECT SUM(CASE WHEN status='hadir' THEN 1 ELSE 0 END) as hari_kerja,
                     SUM(lembur_jam) as total_lembur FROM absensi WHERE karyawan_id=? AND tanggal LIKE ?""",
                  (k['id'],f'{bulan}%'))
        ab=c.fetchone()
        hari=ab['hari_kerja'] or 0; lembur=ab['total_lembur'] or 0
        pokok=hari*k['upah_harian']; upah_lembur=lembur*(k['upah_harian']/8)*1.5
        result.append({'id':k['id'],'nama':k['nama'],'jabatan':k['jabatan'],'upah_harian':k['upah_harian'],
                       'hari_kerja':hari,'lembur_jam':lembur,'upah_pokok':pokok,'upah_lembur':upah_lembur,'total_gaji':pokok+upah_lembur})
    conn.close()
    return jsonify({'data':result,'bulan':bulan})

@app.route('/api/gaji/bayar', methods=['POST'])
def api_bayar_gaji():
    d=request.json; conn=get_db()
    total=float(d['total']); bulan=d['bulan']; metode=d.get('metode','cash')
    jenis='gaji_cash' if metode=='cash' else 'gaji_akrual'
    auto_post(conn,date.today().isoformat(),f'GAJI-{bulan}',f'Pembayaran Gaji Karyawan Bulan {bulan}',jenis,total)
    conn.commit(); conn.close()
    return jsonify({'success':True})

# ═══════════════════════════════════════════════
# API GUDANG
# ═══════════════════════════════════════════════
@app.route('/api/gudang', methods=['GET'])
def api_gudang_list():
    conn=get_db(); c=conn.cursor()
    c.execute("SELECT * FROM gudang ORDER BY kategori,nama_barang")
    rows=[dict(r) for r in c.fetchall()]; conn.close()
    return jsonify({'data':rows})

@app.route('/api/gudang', methods=['POST'])
def api_gudang_add():
    d=request.json; conn=get_db()
    stok=float(d.get('stok_awal',0))
    conn.execute("INSERT INTO gudang (nama_barang,kategori,satuan,stok_awal,stok_sekarang,harga_satuan,stok_minimum) VALUES (?,?,?,?,?,?,?)",
                 (d['nama_barang'],d['kategori'],d['satuan'],stok,stok,float(d.get('harga_satuan',0)),float(d.get('stok_minimum',0))))
    conn.commit(); conn.close()
    return jsonify({'success':True})

@app.route('/api/gudang/transaksi', methods=['POST'])
def api_gudang_transaksi():
    d=request.json; conn=get_db(); c=conn.cursor()
    jumlah=float(d['jumlah']); harga=float(d.get('harga_satuan',0))
    jenis=d['jenis']; metode=d.get('metode','cash')
    c.execute("SELECT stok_sekarang,nama_barang,kategori FROM gudang WHERE id=?",(d['barang_id'],))
    barang=c.fetchone()
    if not barang: return jsonify({'success':False,'error':'Barang tidak ditemukan'})
    stok_baru=barang['stok_sekarang']+jumlah if jenis=='masuk' else barang['stok_sekarang']-jumlah
    conn.execute("UPDATE gudang SET stok_sekarang=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(stok_baru,d['barang_id']))
    conn.execute("INSERT INTO transaksi_gudang (barang_id,tanggal,jenis,jumlah,harga_satuan,total,keterangan) VALUES (?,?,?,?,?,?,?)",
                 (d['barang_id'],d['tanggal'],jenis,jumlah,harga,jumlah*harga,d.get('keterangan','')))
    total=jumlah*harga
    if total>0:
        kat=barang['kategori']
        if jenis=='masuk':
            suffix='_cash' if metode=='cash' else '_kredit'
            jenis_trx=('beli_pupuk'+suffix if kat=='Pupuk' else 'beli_pestisida'+suffix if kat=='Pestisida' else 'beli_benih'+suffix if kat=='Benih' else 'servis_cash')
        else:
            jenis_trx=('pakai_pupuk' if kat=='Pupuk' else 'pakai_pestisida' if kat=='Pestisida' else 'pakai_benih' if kat=='Benih' else 'biaya_lain_cash')
        auto_post(conn,d['tanggal'],'',f"{'Pembelian' if jenis=='masuk' else 'Pemakaian'} {barang['nama_barang']} {jumlah} {d.get('satuan','')}",jenis_trx,total)
    conn.commit(); conn.close()
    return jsonify({'success':True,'stok_baru':stok_baru})

if __name__ == '__main__':
    init_db()
    print("\n"+"="*50)
    print("  AgroSIM v3.0 — BetaFarm Auto-Posting")
    print("  http://localhost:5000")
    print("="*50+"\n")
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
