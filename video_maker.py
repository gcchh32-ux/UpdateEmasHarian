# =============================================================
# AUTO VIDEO EMAS - FULL AUTOMATION v3.0
# =============================================================
import sys, subprocess, os, glob, random, re, json, shutil, time
from datetime import datetime, timedelta
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

def pastikan_library_terinstall():
    try:
        import requests
        from bs4 import BeautifulSoup
        import edge_tts
        from googleapiclient.discovery import build
    except ImportError:
        print("Menginstal library...")
        subprocess.check_call([sys.executable, "-m", "pip", "install",
            "requests", "beautifulsoup4", "edge-tts",
            "google-api-python-client", "google-auth-oauthlib"])

pastikan_library_terinstall()
import requests
from bs4 import BeautifulSoup

# ============================================================
# PENGATURAN UTAMA
# ============================================================
GEMINI_API_KEY   = os.environ.get("GEMINI_API_KEY",  "")
PEXELS_API_KEY   = os.environ.get("PEXELS_API_KEY",  "")
NAMA_CHANNEL     = "Sobat Antam"
FFMPEG_LOG       = "ffmpeg_log.txt"
FILE_HISTORY     = "history_harga.json"
YOUTUBE_CATEGORY = "25"
YOUTUBE_TAGS     = ["harga emas", "emas antam", "investasi emas",
                    "logam mulia", "harga emas hari ini", "emas antam hari ini"]
KATA_KUNCI_GAMBAR = ["gold bars", "gold investment", "precious metals",
                     "gold coins", "financial gold", "gold bullion",
                     "gold price", "gold trading", "gold market", "wealth gold"]

# ── Manajemen storage ─────────────────────────────────────────
FOLDER_GAMBAR     = "gambar_bank"     # folder bank gambar permanen
JUMLAH_GAMBAR_MIN = 50                # download ulang jika di bawah angka ini
JUMLAH_GAMBAR_MAX = 200               # hapus gambar lama jika melebihi ini
JUMLAH_DL_SEKALI  = 80               # jumlah gambar didownload sekali jalan
SIMPAN_VIDEO_MAKS = 3                 # simpan maksimal N video terakhir secara lokal
# ============================================================


# ════════════════════════════════════════════════════════════
# BAGIAN 1: MANAJEMEN STORAGE
# ════════════════════════════════════════════════════════════

def kelola_bank_gambar():
    """
    Kelola folder gambar_bank:
    - Jika gambar < JUMLAH_GAMBAR_MIN → download batch baru dari Pexels
    - Jika gambar > JUMLAH_GAMBAR_MAX → hapus gambar paling lama
    - Return list path gambar yang tersedia
    """
    os.makedirs(FOLDER_GAMBAR, exist_ok=True)
    gambar_ada = sorted(glob.glob(f"{FOLDER_GAMBAR}/*.jpg") +
                        glob.glob(f"{FOLDER_GAMBAR}/*.jpeg") +
                        glob.glob(f"{FOLDER_GAMBAR}/*.png"))

    print(f"[STORAGE] Bank gambar: {len(gambar_ada)} file di '{FOLDER_GAMBAR}/'")

    # Download batch jika kurang
    if len(gambar_ada) < JUMLAH_GAMBAR_MIN:
        kurang = JUMLAH_DL_SEKALI - len(gambar_ada)
        print(f"[STORAGE] Gambar kurang dari {JUMLAH_GAMBAR_MIN}. Download {kurang} gambar baru...")
        gambar_baru = _download_pexels_batch(kurang)
        gambar_ada  = sorted(glob.glob(f"{FOLDER_GAMBAR}/*.jpg") +
                             glob.glob(f"{FOLDER_GAMBAR}/*.jpeg") +
                             glob.glob(f"{FOLDER_GAMBAR}/*.png"))
        print(f"[STORAGE] Bank gambar sekarang: {len(gambar_ada)} file")
    else:
        print(f"[STORAGE] Bank gambar cukup. Tidak perlu download.")

    # Hapus gambar terlama jika melebihi batas
    if len(gambar_ada) > JUMLAH_GAMBAR_MAX:
        jumlah_hapus = len(gambar_ada) - JUMLAH_GAMBAR_MAX
        to_hapus     = gambar_ada[:jumlah_hapus]  # hapus yang paling lama (sort by name)
        for f in to_hapus:
            try:
                os.remove(f)
            except Exception:
                pass
        print(f"[STORAGE] Hapus {jumlah_hapus} gambar lama. Bank tersisa: {JUMLAH_GAMBAR_MAX}")
        gambar_ada = gambar_ada[jumlah_hapus:]

    return gambar_ada


def _download_pexels_batch(jumlah_target):
    """Download gambar dari Pexels, tersebar dari berbagai keyword."""
    if not PEXELS_API_KEY:
        print("  -> Pexels API key kosong. Skip download.")
        return []

    headers     = {"Authorization": PEXELS_API_KEY}
    per_keyword = max(10, jumlah_target // len(KATA_KUNCI_GAMBAR))
    total_dl    = 0
    ts_base     = int(time.time())

    for keyword in KATA_KUNCI_GAMBAR:
        url = (f"https://api.pexels.com/v1/search"
               f"?query={keyword}&per_page={per_keyword}&orientation=landscape&size=large")
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            fotos = resp.json().get("photos", [])

            for i, foto in enumerate(fotos):
                img_url  = foto["src"]["large2x"]
                filename = f"{FOLDER_GAMBAR}/pexels_{ts_base}_{keyword.replace(' ','_')}_{i+1}.jpg"

                # Skip jika sudah ada file serupa (cegah duplikat keyword)
                if os.path.exists(filename):
                    continue

                try:
                    img_data = requests.get(img_url, timeout=30).content
                    with open(filename, "wb") as f:
                        f.write(img_data)
                    total_dl += 1
                except Exception as e:
                    print(f"  -> Gagal download {img_url}: {e}")

            print(f"  -> '{keyword}': {len(fotos)} gambar OK")
            if total_dl >= jumlah_target:
                break

        except Exception as e:
            print(f"  -> Gagal fetch keyword '{keyword}': {e}")

    print(f"  -> Total download: {total_dl} gambar baru ke '{FOLDER_GAMBAR}/'")
    return total_dl


def kelola_video_lama():
    """
    Hapus video lama, simpan hanya SIMPAN_VIDEO_MAKS video terbaru.
    Panggil SEBELUM render agar tidak memenuhi storage.
    """
    videos = sorted(glob.glob("Video_Emas_*.mp4"))
    if len(videos) > SIMPAN_VIDEO_MAKS:
        hapus  = videos[:len(videos) - SIMPAN_VIDEO_MAKS]
        for v in hapus:
            try:
                os.remove(v)
                print(f"[STORAGE] Hapus video lama: {v}")
            except Exception:
                pass


def ringkasan_storage():
    """Tampilkan ringkasan penggunaan storage."""
    gambar_ada = (glob.glob(f"{FOLDER_GAMBAR}/*.jpg") +
                  glob.glob(f"{FOLDER_GAMBAR}/*.jpeg") +
                  glob.glob(f"{FOLDER_GAMBAR}/*.png"))
    videos     = glob.glob("Video_Emas_*.mp4")

    ukuran_gambar = sum(os.path.getsize(f) for f in gambar_ada if os.path.exists(f))
    ukuran_video  = sum(os.path.getsize(f) for f in videos if os.path.exists(f))

    print(f"\n[STORAGE] Ringkasan:")
    print(f"  → Bank gambar : {len(gambar_ada)} file ({ukuran_gambar/1024/1024:.1f} MB)")
    print(f"  → Video lokal : {len(videos)} file ({ukuran_video/1024/1024:.1f} MB)")
    print(f"  → Total       : {(ukuran_gambar+ukuran_video)/1024/1024:.1f} MB")


# ════════════════════════════════════════════════════════════
# BAGIAN 2: HISTORY HARGA (365 HARI)
# ════════════════════════════════════════════════════════════

def muat_history():
    if os.path.exists(FILE_HISTORY):
        try:
            with open(FILE_HISTORY, encoding="utf-8") as f:
                data = json.load(f)
            # Konversi format lama ke format baru
            if "records" not in data and "harga_1_gram" in data:
                return {"records": [{"tanggal": data["tanggal"], "harga": data["harga_1_gram"]}]}
            return data
        except Exception:
            pass
    return {"records": []}


def simpan_history(harga_hari_ini):
    history  = muat_history()
    records  = history.get("records", [])
    hari_ini = datetime.now().strftime("%Y-%m-%d")
    records  = [r for r in records if r["tanggal"] != hari_ini]
    records.insert(0, {"tanggal": hari_ini, "harga": harga_hari_ini})
    records  = records[:365]
    with open(FILE_HISTORY, "w", encoding="utf-8") as f:
        json.dump({"records": records}, f, indent=2, ensure_ascii=False)
    return records


def cari_harga_n_hari_lalu(records, n_hari):
    target = (datetime.now().date() - timedelta(days=n_hari)).strftime("%Y-%m-%d")
    for rec in records:
        if rec["tanggal"] <= target:
            return rec
    return None


def analisa_historis(harga_sekarang, records):
    periode = {"kemarin":1, "7_hari":7, "1_bulan":30,
               "3_bulan":90, "6_bulan":180, "1_tahun":365}
    hasil = {}
    for label, n in periode.items():
        rec = cari_harga_n_hari_lalu(records, n)
        if rec:
            selisih = harga_sekarang - rec["harga"]
            pct     = round((selisih / rec["harga"]) * 100, 2)
            hasil[label] = {
                "tanggal":   rec["tanggal"],
                "harga_ref": rec["harga"],
                "selisih":   selisih,
                "persen":    pct,
                "naik":      selisih > 0,
                "stabil":    selisih == 0,
            }
    return hasil


# ════════════════════════════════════════════════════════════
# BAGIAN 3: JUDUL CLICKBAIT LOKAL
# ════════════════════════════════════════════════════════════

def buat_judul_clickbait_lokal(info, historis):
    h       = f"Rp {info['harga_sekarang']:,}".replace(",", ".")
    status  = info['status']
    selisih = f"Rp {info['selisih']:,}".replace(",", ".")

    nama_periode = {
        "kemarin":"Kemarin", "7_hari":"Seminggu",
        "1_bulan":"Sebulan", "3_bulan":"3 Bulan",
        "6_bulan":"6 Bulan", "1_tahun":"Setahun",
    }

    # Cari perubahan signifikan historis (≥ 2%)
    penting = None
    for label in ["3_bulan", "1_bulan", "6_bulan", "1_tahun", "7_hari"]:
        data = historis.get(label)
        if data and abs(data["persen"]) >= 2.0:
            penting = (label, data)
            break

    if penting:
        label, data   = penting
        pct           = abs(data["persen"])
        arah          = "NAIK" if data["naik"] else "TURUN"
        periode_label = nama_periode.get(label, label)
        pool = [
            f"NAIK {pct:.1f}% dari {periode_label} Lalu! Emas Antam {h}/gram Hari Ini",
            f"WASPADA! Emas Sudah {arah} {pct:.1f}% dalam {periode_label} - {h}",
            f"Harga Emas {arah} {pct:.1f}% Sejak {periode_label} Lalu! Masih Beli?",
            f"{arah} {pct:.1f}% dalam {periode_label}! Emas Antam Kini {h}/gram",
        ] if data["naik"] else [
            f"TURUN {pct:.1f}% dari {periode_label} Lalu! Saatnya Borong Emas {h}?",
            f"EMAS ANJLOK {pct:.1f}% dalam {periode_label}! Peluang Beli di {h}",
            f"Harga Emas TURUN {pct:.1f}% Sejak {periode_label} - Tunggu Apa Lagi?",
            f"DISKON {pct:.1f}%! Emas Antam Kini {h}/gram - Beli atau Tunggu?",
        ]

    elif status == "Naik":
        pool = [
            f"🚨 EMAS NAIK {selisih} HARI INI! Antam {h}/gram - Masih Mau Beli?",
            f"NAIK LAGI! Emas Antam {h}/gram - Sudah {selisih} Lebih Mahal",
            f"ALERT! Harga Emas Naik {selisih} - Sekarang {h} per Gram",
            f"Harga Emas MERANGKAK NAIK {selisih}! Antam {h}/gram Hari Ini",
        ]
    elif status == "Turun":
        pool = [
            f"🎯 EMAS TURUN {selisih}! Ini Saat Tepat Beli Emas Antam {h}?",
            f"DISKON EMAS! Antam Turun {selisih} Jadi {h}/gram - Borong Sekarang?",
            f"HARGA EMAS MELEMAH {selisih}! Antam {h}/gram - Kapan Balik Naik?",
            f"Emas Antam KOREKSI {selisih} ke {h}/gram - Momentum Beli Terbaik?",
        ]
    else:
        pool = [
            f"Harga Emas Antam STAGNAN di {h}/gram - Kapan Akan Bergerak?",
            f"SINYAL APA INI? Emas Antam Bertahan di {h}/gram - Analisa Lengkap",
            f"Emas Antam Hari Ini {h}/gram - Naik atau Turun Selanjutnya?",
            f"KONSOLIDASI? Emas Antam {h}/gram - Ini Kata Para Analis",
        ]

    judul = random.choice(pool)
    return judul[:100]


# ════════════════════════════════════════════════════════════
# BAGIAN 4: SCRAPING HARGA EMAS
# ════════════════════════════════════════════════════════════

def scrape_dan_kalkulasi_harga():
    print("[1/6] Mengambil data harga emas Antam...")
    url     = "https://www.logammulia.com/id/harga-emas-hari-ini"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response   = requests.get(url, headers=headers, timeout=15)
        soup       = BeautifulSoup(response.text, 'html.parser')
        data_kasar = soup.get_text(separator=" | ", strip=True)
        tanggal    = datetime.now().strftime("%d %B %Y")

        harga_1_gram = 0
        for row in soup.find_all('tr'):
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                teks_kol = cells[0].text.strip().lower()
                if teks_kol in ('1 gr', '1 gram'):
                    angka_str = re.sub(r'[^\d]', '', cells[1].text)
                    if angka_str:
                        harga_1_gram = int(angka_str)
                        break

        if harga_1_gram == 0:
            print("  -> ERROR: Gagal parse harga dari website Antam.")
            return None, None

        history_data = muat_history()
        records      = history_data.get("records", [])
        historis     = analisa_historis(harga_1_gram, records)

        kemarin_data = historis.get("kemarin")
        if kemarin_data:
            selisih = kemarin_data["selisih"]
            status  = "Naik" if selisih > 0 else ("Turun" if selisih < 0 else "Stabil")
            selisih = abs(selisih)
        else:
            status, selisih = "Stabil", 0

        records_baru = simpan_history(harga_1_gram)

        ringkasan = []
        for label, data in historis.items():
            if data:
                arah = "↑" if data["naik"] else ("↓" if not data["stabil"] else "→")
                ringkasan.append(
                    f"{label}: {arah}{abs(data['persen']):.1f}% "
                    f"({data['harga_ref']:,}→{harga_1_gram:,})".replace(",", ".")
                )

        print(f"  -> Rp {harga_1_gram:,} | {status} Rp {selisih:,} | {len(records_baru)} hari history".replace(",", "."))
        if ringkasan:
            print(f"  -> Historis: {' | '.join(ringkasan[:4])}")

        info = {
            "harga_sekarang": harga_1_gram,
            "status":         status,
            "selisih":        selisih,
            "historis":       historis,
            "total_record":   len(records_baru),
        }
        konteks = "; ".join(ringkasan)
        teks_data = (f"Tanggal: {tanggal}. Historis: {konteks}. "
                     f"Data Antam: {data_kasar[:2500]}...")
        return info, teks_data

    except Exception as e:
        print(f"  -> Gagal scraping: {e}")
        return None, None


# ════════════════════════════════════════════════════════════
# BAGIAN 5: NARASI & JUDUL (GEMINI + FALLBACK)
# ════════════════════════════════════════════════════════════

def _buat_narasi_fallback_lokal(info, harga_skrg, status_harga, selisih_harga):
    tanggal = datetime.now().strftime("%d %B %Y")
    hari    = {"Monday":"Senin","Tuesday":"Selasa","Wednesday":"Rabu",
               "Thursday":"Kamis","Friday":"Jumat",
               "Saturday":"Sabtu","Sunday":"Minggu"
               }.get(datetime.now().strftime("%A"), "")

    h     = info['harga_sekarang']
    tabel = {
        "setengah gram":             h // 2,
        "satu gram":                 h,
        "dua gram":                  h * 2,
        "tiga gram":                 h * 3,
        "lima gram":                 h * 5,
        "sepuluh gram":              h * 10,
        "dua puluh lima gram":       h * 25,
        "lima puluh gram":           h * 50,
        "seratus gram":              h * 100,
        "dua ratus lima puluh gram": h * 250,
        "lima ratus gram":           h * 500,
        "seribu gram":               h * 1000,
    }
    rp      = lambda x: f"Rp {x:,}".replace(",", ".")
    daftar  = " ".join(f"Untuk {s}, harganya {rp(v)}." for s, v in tabel.items())

    kalimat_status = {
        "Naik":   f"mengalami kenaikan sebesar Rupiah {selisih_harga} dari kemarin",
        "Turun":  f"mengalami penurunan sebesar Rupiah {selisih_harga} dari kemarin",
        "Stabil": "terpantau stabil dari hari sebelumnya",
    }.get(status_harga, "terpantau stabil")

    historis = info.get("historis", {})
    kalimat_historis = ""
    for label, data in historis.items():
        if data and abs(data["persen"]) >= 1.0:
            arah  = "naik" if data["naik"] else "turun"
            nama  = {"kemarin":"kemarin","7_hari":"seminggu lalu",
                     "1_bulan":"sebulan lalu","3_bulan":"tiga bulan lalu",
                     "6_bulan":"enam bulan lalu","1_tahun":"setahun lalu"}.get(label, label)
            kalimat_historis = (
                f" Jika dibandingkan dengan {nama}, harga emas telah {arah} "
                f"sebesar {abs(data['persen']):.1f} persen dari "
                f"{rp(data['harga_ref'])} menjadi {rp(h)}."
            )
            break

    judul  = buat_judul_clickbait_lokal(info, historis)
    narasi = f"""Halo sobat {NAMA_CHANNEL}, selamat datang kembali di channel kita tercinta. Hari ini hari {hari}, tanggal {tanggal}, dan seperti biasa kami hadir membawakan update terbaru harga emas Antam Logam Mulia untuk Anda semua.

Langsung kita masuk ke informasi utama. Harga emas Antam resmi hari ini untuk ukuran satu gram adalah {harga_skrg} Rupiah. Harga ini {kalimat_status}.{kalimat_historis} Informasi ini kami ambil langsung dari situs resmi Logam Mulia sehingga dapat dijadikan acuan yang akurat dan terpercaya.

Berikut daftar lengkap harga emas Antam hari ini untuk semua ukuran yang tersedia. {daftar} Itulah harga lengkap emas Antam hari ini. Pastikan selalu cek harga terbaru sebelum memutuskan membeli karena harga emas bergerak dinamis setiap harinya mengikuti pasar global.

Sekarang mari kita bahas faktor-faktor yang mempengaruhi pergerakan harga emas saat ini. Pertama, kebijakan suku bunga bank sentral Amerika Serikat Federal Reserve menjadi penentu utama arah harga emas global. Ketika suku bunga tinggi, dolar menguat dan emas cenderung tertekan karena investor beralih ke aset berbunga. Sebaliknya, penurunan suku bunga selalu menjadi katalis positif bagi harga emas. Kedua, ketidakpastian geopolitik global terus mendorong permintaan emas sebagai safe haven. Konflik di berbagai belahan dunia membuat investor mencari perlindungan nilai aset di emas yang sudah teruji selama ribuan tahun. Ketiga, nilai tukar Rupiah terhadap Dolar Amerika secara langsung menentukan harga emas dalam negeri. Pelemahan Rupiah otomatis akan mendorong harga emas dalam Rupiah menjadi lebih tinggi. Keempat, permintaan fisik dari India dan Tiongkok sebagai konsumen emas terbesar dunia turut mempengaruhi harga secara signifikan, terutama menjelang musim perayaan dan hari besar keagamaan.

Bagi sobat yang ingin memulai atau menambah portofolio investasi emas, ada beberapa strategi yang telah terbukti efektif. Pertama, mulailah dari ukuran kecil seperti setengah gram atau satu gram agar tidak memberatkan keuangan Anda. Kedua, terapkan strategi dollar cost averaging yaitu membeli rutin setiap bulan dengan jumlah tetap tanpa peduli kondisi harga. Strategi ini terbukti menghasilkan harga rata-rata yang lebih baik dalam jangka panjang. Ketiga, manfaatkan momen penurunan harga sebagai kesempatan menambah koleksi karena emas secara historis selalu pulih dan mencetak rekor baru. Keempat, simpan emas fisik Anda di tempat yang aman, baik di brankas khusus maupun menggunakan layanan titipan resmi dari Antam yang sudah terjamin keamanannya. Kelima, pisahkan emas investasi dari emas perhiasan karena emas batangan memiliki biaya produksi yang jauh lebih rendah sehingga lebih efisien sebagai instrumen investasi murni.

Demikian informasi lengkap harga emas Antam hari ini beserta analisa dan tips investasi dari kami di channel {NAMA_CHANNEL}. Semoga informasi ini bermanfaat dan membantu Anda dalam mengambil keputusan investasi yang tepat dan menguntungkan. Jangan lupa tekan tombol Subscribe dan aktifkan lonceng notifikasi agar tidak pernah ketinggalan update harga emas terbaru setiap hari. Bagikan video ini kepada keluarga dan teman yang membutuhkan informasi seputar investasi emas. Sampai jumpa di video berikutnya. Salam sukses dan salam investasi untuk sobat semua!""".strip()

    return judul, narasi


def buat_narasi_dan_judul(info, data_harga):
    print("[2/6] Membuat judul + meminta Gemini menulis script...")

    status_harga  = info['status']
    selisih_harga = f"{info['selisih']:,}".replace(",", ".")
    harga_skrg    = f"{info['harga_sekarang']:,}".replace(",", ".")
    historis      = info.get("historis", {})

    # Judul dibuat lokal — 100% reliable & selalu clickbait
    judul = buat_judul_clickbait_lokal(info, historis)
    print(f"  -> Judul: {judul}")

    ringkasan_historis = []
    for label, data in historis.items():
        if data:
            arah = "naik" if data["naik"] else ("turun" if not data["stabil"] else "stabil")
            nama = {"kemarin":"kemarin","7_hari":"seminggu lalu","1_bulan":"sebulan lalu",
                    "3_bulan":"3 bulan lalu","6_bulan":"6 bulan lalu","1_tahun":"setahun lalu"
                    }.get(label, label)
            ringkasan_historis.append(
                f"{nama}: {arah} {abs(data['persen']):.1f}% dari "
                f"Rp {data['harga_ref']:,}".replace(",", ".")
            )
    konteks_historis = " | ".join(ringkasan_historis) or "Data historis belum tersedia."

    prompt = f"""Kamu adalah scriptwriter YouTube profesional. Tulis HANYA script narasi video. Langsung mulai dengan "Halo sobat..." tanpa kata pengantar apapun.

DATA:
- Channel: {NAMA_CHANNEL}
- Harga emas 1 gram hari ini: Rp {harga_skrg}
- Status vs kemarin: {status_harga} Rp {selisih_harga}
- Perbandingan historis: {konteks_historis}
- Data tabel Antam: {data_harga[:2000]}

STRUKTUR SCRIPT (TARGET 900-1000 KATA):
1. Pembuka (100 kata): Sapa penonton {NAMA_CHANNEL}, umumkan harga Rp {harga_skrg}, status {status_harga}
2. Daftar harga (200 kata): Semua ukuran 0.5g sampai 1000g
3. Analisa historis & global (300 kata): Bahas data {konteks_historis}, kaitkan kondisi ekonomi dunia
4. Edukasi & penutup (300 kata): Tips investasi emas, ajakan subscribe {NAMA_CHANNEL}

ATURAN KERAS:
- MULAI LANGSUNG "Halo sobat..." — DILARANG tulis "Tentu", "Berikut", "Ini dia" atau kata pengantar apapun
- Semua angka ditulis dengan HURUF
- Paragraf narasi murni, TANPA bullet, TANPA nomor, TANPA simbol
- Bahasa Indonesia natural seperti presenter berita"""

    MODEL_CHAIN = [
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash",
        "gemini-2.5-flash-lite",
    ]

    for model_name in MODEL_CHAIN:
        for attempt in range(3):
            try:
                url_api = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                           f"{model_name}:generateContent?key={GEMINI_API_KEY}")
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "maxOutputTokens": 8192,
                        "temperature":     0.85,
                    }
                }
                print(f"  -> {model_name} attempt {attempt+1}...")
                resp = requests.post(url_api, json=payload, timeout=90)

                if resp.status_code == 429:
                    tunggu = int(resp.headers.get('Retry-After', (2**attempt)*10))
                    print(f"  -> 429 rate limit. Tunggu {tunggu}s...")
                    time.sleep(tunggu)
                    continue

                resp.raise_for_status()
                script = resp.json()['candidates'][0]['content']['parts'][0]['text'].strip()

                # Bersihkan kata pengantar jika Gemini masih menambahkan
                kata_buang = ["tentu,", "tentu ", "berikut,", "berikut ",
                              "ini dia", "baik,", "oke,", "siap,", "dengan senang"]
                baris1     = script.split('\n')[0].lower()
                for kata in kata_buang:
                    if kata in baris1:
                        script = '\n'.join(script.split('\n')[1:]).strip()
                        break

                jumlah_kata = len(script.split())
                print(f"  -> ✅ Script OK ({jumlah_kata} kata) dari {model_name}")
                return judul, script

            except Exception as e:
                if "429" not in str(e):
                    print(f"  -> Error {model_name}: {e}")
                    break
                time.sleep((2**attempt)*10)

        print(f"  -> {model_name} gagal. Coba berikutnya...")

    print("  -> [FALLBACK] Pakai narasi template lokal...")
    _, narasi_fallback = _buat_narasi_fallback_lokal(info, harga_skrg, status_harga, selisih_harga)
    return judul, narasi_fallback


# ════════════════════════════════════════════════════════════
# BAGIAN 6: GENERATE SUARA
# ════════════════════════════════════════════════════════════

def buat_suara(teks, output_audio):
    print("[3/6] Men-generate Suara AI (edge-tts)...")
    teks_bersih = re.sub(r'\[.*?\]|\(.*?\)|\*.*?\*', '', teks).strip()
    subprocess.run([
        sys.executable, '-m', 'edge_tts',
        '--voice', 'id-ID-ArdiNeural',
        '--rate', '+5%',
        '--text', teks_bersih,
        '--write-media', output_audio
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    if not os.path.exists(output_audio) or os.path.getsize(output_audio) < 1000:
        raise FileNotFoundError("File audio gagal dibuat!")

    hasil_dur = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', output_audio],
        capture_output=True, text=True
    )
    durasi = float(hasil_dur.stdout.strip())
    if durasi < 30:
        raise ValueError(f"Audio terlalu pendek ({durasi:.1f}s). Narasi terlalu singkat!")
    print(f"  -> ✅ Audio OK: {durasi:.0f} detik ({durasi/60:.1f} menit)")
    return durasi


# ════════════════════════════════════════════════════════════
# BAGIAN 7: RENDER VIDEO
# ════════════════════════════════════════════════════════════

def escape_ffmpeg_path(path):
    return path.replace('\\', '/').replace(':', '\\:')


def siapkan_font_lokal():
    font_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
    ]
    font_lokal = os.path.abspath("font_temp.ttf")
    for path in font_paths:
        if os.path.exists(path):
            try:
                shutil.copy(path, font_lokal)
                print(f"  -> Font: {path}")
                return font_lokal
            except Exception:
                continue
    print("  -> PERINGATAN: Font tidak ditemukan. Watermark dinonaktifkan.")
    return None


def render_satu_klip(args):
    i, img, font_sistem, output_klip = args
    base = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
            "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30")
    pilihan_filter = [
        f"{base},fade=t=in:st=0:d=1,fade=t=out:st=9:d=1",
        (f"{base},boxblur=luma_radius='max(0,15*(1-t/1.5))':luma_power=1,"
         "fade=t=in:st=0:d=1,fade=t=out:st=9:d=1"),
        f"{base},hue=s='min(1,t/1.5)',fade=t=in:st=0:d=1,fade=t=out:st=9:d=1",
    ]
    filter_vf = random.choice(pilihan_filter)

    if font_sistem:
        font_esc = escape_ffmpeg_path(font_sistem)
        x, y    = random.choice([("30","30"),("w-tw-30","30"),
                                  ("30","h-th-30"),("w-tw-30","h-th-30")])
        filter_vf += (f",drawtext=fontfile='{font_esc}'"
                      f":text='{NAMA_CHANNEL}'"
                      f":fontcolor=white@0.7:fontsize=30:x={x}:y={y}")

    cmd = [
        'ffmpeg', '-y',
        '-loop', '1', '-framerate', '30', '-i', img,
        '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
        '-vf', filter_vf,
        '-map', '0:v', '-map', '1:a',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-t', '10', output_klip
    ]
    with open(FFMPEG_LOG, 'a', encoding='utf-8') as log:
        log.write(f"\n=== Klip {i}: {os.path.basename(img)} ===\n")
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=log)

    if (result.returncode != 0 or not os.path.exists(output_klip)
            or os.path.getsize(output_klip) < 1000):
        return None
    return i, output_klip


def proses_gambar(durasi_total_detik, gambar_bank):
    print(f"[4/6] Proses gambar paralel ({min(4, os.cpu_count() or 2)} thread)...")
    os.makedirs("temp_clips", exist_ok=True)

    if not gambar_bank:
        print("ERROR: Bank gambar kosong!")
        return None

    random.shuffle(gambar_bank)
    jumlah_klip = int(durasi_total_detik / 10) + 2
    while len(gambar_bank) < jumlah_klip:
        gambar_bank.extend(gambar_bank)
    gambar_terpilih = gambar_bank[:jumlah_klip]

    font_sistem = siapkan_font_lokal()
    tasks = [(i, img, font_sistem, os.path.abspath(f"temp_clips/klip_{i}.mp4"))
             for i, img in enumerate(gambar_terpilih)]

    klip_berhasil = {}
    with ThreadPoolExecutor(max_workers=min(4, os.cpu_count() or 2)) as executor:
        futures = {executor.submit(render_satu_klip, t): t[0] for t in tasks}
        for future in as_completed(futures):
            hasil = future.result()
            if hasil:
                idx, path = hasil
                klip_berhasil[idx] = path
            print(f"  -> {len(klip_berhasil)}/{jumlah_klip} klip selesai", end='\r')

    print(f"\n  -> {len(klip_berhasil)}/{jumlah_klip} klip berhasil.")
    if not klip_berhasil:
        return None

    list_txt = os.path.abspath('concat_videos.txt')
    with open(list_txt, 'w', encoding='utf-8') as f:
        for i in sorted(klip_berhasil.keys()):
            f.write(f"file '{klip_berhasil[i].replace(chr(92),'/')}'\n")
    return list_txt


def render_video_final(file_list, audio, output, durasi):
    print(f"[5/6] Merender video final...")
    cmd = [
        'ffmpeg', '-y',
        '-f', 'concat', '-safe', '0', '-i', file_list,
        '-i', audio,
        '-map', '0:v', '-map', '1:a',
        '-c:v', 'copy',
        '-c:a', 'aac', '-b:a', '192k',
        '-t', str(durasi), output
    ]
    with open(FFMPEG_LOG, 'a', encoding='utf-8') as log:
        log.write("\n=== RENDER FINAL ===\n")
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=log)
    if result.returncode != 0:
        print(f"  -> ERROR render! Cek {FFMPEG_LOG}")
        return False
    return True


# ════════════════════════════════════════════════════════════
# BAGIAN 8: UPLOAD YOUTUBE
# ════════════════════════════════════════════════════════════

def upload_ke_youtube(video_path, judul, deskripsi, tags):
    print("[6/6] Upload ke YouTube...")
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        creds_file = "youtube_token.json"
        token_env  = os.environ.get("YOUTUBE_TOKEN_JSON")
        if token_env:
            with open(creds_file, "w") as f:
                f.write(token_env)

        if not os.path.exists(creds_file):
            print(f"  -> ERROR: '{creds_file}' tidak ditemukan!")
            return None

        with open(creds_file) as f:
            td = json.load(f)

        creds   = Credentials(
            token=td.get("token"), refresh_token=td.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=td.get("client_id"), client_secret=td.get("client_secret"),
        )
        youtube = build("youtube", "v3", credentials=creds)
        body    = {
            "snippet": {
                "title": judul[:100], "description": deskripsi,
                "tags": tags, "categoryId": YOUTUBE_CATEGORY,
                "defaultLanguage": "id",
            },
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
        }
        media   = MediaFileUpload(video_path, mimetype="video/mp4",
                                  resumable=True, chunksize=5*1024*1024)
        request = youtube.videos().insert(part="snippet,status",
                                          body=body, media_body=media)
        response = None
        while response is None:
            status_up, response = request.next_chunk()
            if status_up:
                print(f"  -> Upload: {int(status_up.progress()*100)}%", end='\r')

        video_id = response.get("id")
        print(f"\n  -> ✅ Upload sukses! https://youtu.be/{video_id}")

        with open("upload_history.json", "a", encoding="utf-8") as f:
            json.dump({"tanggal": datetime.now().isoformat(),
                       "video_id": video_id, "judul": judul}, f, ensure_ascii=False)
            f.write("\n")
        return video_id

    except Exception as e:
        print(f"  -> Gagal upload YouTube: {e}")
        return None


# ════════════════════════════════════════════════════════════
# BAGIAN 9: BERSIHKAN TEMP
# ════════════════════════════════════════════════════════════

def bersihkan_temp(file_list, audio):
    print("[+] Membersihkan file sementara...")
    try:
        for f in [audio, file_list, "font_temp.ttf"]:
            if f and os.path.exists(f):
                os.remove(f)
        for klip in glob.glob("temp_clips/*.mp4"):
            os.remove(klip)
        if os.path.exists("temp_clips"):
            os.rmdir("temp_clips")
    except Exception as e:
        print(f"  -> Warning: {e}")


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════

async def main():
    with open(FFMPEG_LOG, 'w', encoding='utf-8') as f:
        f.write(f"Log FFmpeg - {datetime.now()}\n{'='*60}\n")

    audio_temp  = "suara.mp3"
    tanggal_str = datetime.now().strftime('%Y%m%d')
    video_hasil = f"Video_Emas_{tanggal_str}.mp4"

    print(f"\n{'='*60}")
    print(f"  AUTO VIDEO EMAS - {NAMA_CHANNEL}")
    print(f"  {datetime.now().strftime('%d %B %Y, %H:%M WIB')}")
    print(f"{'='*60}\n")

    # ── 0. Manajemen storage ──────────────────────────────────
    kelola_video_lama()
    gambar_bank = kelola_bank_gambar()

    if not gambar_bank:
        print("FATAL: Tidak ada gambar tersedia. Proses dihentikan.")
        return

    # ── 1. Scrape harga ──────────────────────────────────────
    info, data_harga = scrape_dan_kalkulasi_harga()
    if not info:
        print("Scraping gagal. Proses dihentikan.")
        return

    # ── 2. Narasi & judul ────────────────────────────────────
    judul, narasi = buat_narasi_dan_judul(info, data_harga)
    print(f"\n{'='*60}")
    print(f"  🌟 JUDUL: {judul}")
    print(f"{'='*60}\n")

    # ── 3. Generate suara ────────────────────────────────────
    try:
        durasi = buat_suara(narasi, audio_temp)
    except Exception as e:
        print(f"  -> ERROR audio: {e}")
        return

    # ── 4. Render gambar → klip ──────────────────────────────
    file_list = proses_gambar(durasi, list(gambar_bank))
    if not file_list:
        return

    # ── 5. Render video final ────────────────────────────────
    sukses = render_video_final(file_list, audio_temp, video_hasil, durasi)
    bersihkan_temp(file_list, audio_temp)

    if sukses and os.path.exists(video_hasil):
        ukuran_mb = os.path.getsize(video_hasil) // 1024 // 1024
        print(f"\n✅ VIDEO SELESAI: {video_hasil} ({ukuran_mb} MB)")

        if ukuran_mb < 5:
            print(f"⚠️  Video terlalu kecil! Cek {FFMPEG_LOG}")
            return

        # ── 6. Upload ke YouTube ──────────────────────────────
        deskripsi = (
            f"Update harga emas Antam hari ini "
            f"{datetime.now().strftime('%d %B %Y')}.\n\n"
            f"✅ Harga 1 gram  : Rp {info['harga_sekarang']:,}\n"
            f"📊 Status        : {info['status']}\n\n"
            .replace(",", ".") +
            "Informasi diambil dari situs resmi Logam Mulia.\n\n"
            "#HargaEmas #EmasAntam #InvestasiEmas #LogamMulia #EmasHariIni\n\n"
            f"Jangan lupa SUBSCRIBE dan aktifkan 🔔 notifikasi!"
        )
        upload_ke_youtube(video_hasil, judul, deskripsi, YOUTUBE_TAGS)

    else:
        print(f"\n❌ GAGAL membuat video. Cek {FFMPEG_LOG}")

    # ── Ringkasan storage akhir ───────────────────────────────
    ringkasan_storage()


if __name__ == "__main__":
    asyncio.run(main())
