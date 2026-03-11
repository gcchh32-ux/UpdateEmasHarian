# =============================================================
# AUTO VIDEO EMAS - FULL AUTOMATION v5.0
# Sobat Antam
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
        from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    except ImportError:
        print("Menginstal library...")
        subprocess.check_call([sys.executable, "-m", "pip", "install",
            "requests", "beautifulsoup4", "edge-tts",
            "google-api-python-client", "google-auth-oauthlib", "Pillow"])

pastikan_library_terinstall()
import requests
from bs4 import BeautifulSoup

# ============================================================
# PENGATURAN UTAMA
# ============================================================
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY",  "")
PEXELS_API_KEY    = os.environ.get("PEXELS_API_KEY",  "")
NAMA_CHANNEL      = "Sobat Antam"
FFMPEG_LOG        = "ffmpeg_log.txt"
FILE_HISTORY      = "history_harga.json"
YOUTUBE_CATEGORY  = "25"
YOUTUBE_TAGS      = [
    "harga emas", "emas antam", "investasi emas", "logam mulia",
    "harga emas hari ini", "emas antam hari ini", "harga emas antam",
    "update emas", "emas batangan", "harga logam mulia",
]
KATA_KUNCI_GAMBAR = [
    "gold bars", "gold investment", "precious metals", "gold coins",
    "financial gold", "gold bullion", "gold price", "gold trading",
    "gold market", "wealth gold",
]

# Manajemen storage
FOLDER_GAMBAR     = "gambar_bank"
JUMLAH_GAMBAR_MIN = 50
JUMLAH_GAMBAR_MAX = 200
JUMLAH_DL_SEKALI  = 80
SIMPAN_VIDEO_MAKS = 3
# ============================================================


# ════════════════════════════════════════════════════════════
# BAGIAN 1 — MANAJEMEN STORAGE
# ════════════════════════════════════════════════════════════

def kelola_bank_gambar():
    os.makedirs(FOLDER_GAMBAR, exist_ok=True)
    gambar_ada = sorted(
        glob.glob(f"{FOLDER_GAMBAR}/*.jpg") +
        glob.glob(f"{FOLDER_GAMBAR}/*.jpeg") +
        glob.glob(f"{FOLDER_GAMBAR}/*.png")
    )
    print(f"[STORAGE] Bank gambar: {len(gambar_ada)} file di '{FOLDER_GAMBAR}/'")

    if len(gambar_ada) < JUMLAH_GAMBAR_MIN:
        kurang = JUMLAH_DL_SEKALI - len(gambar_ada)
        print(f"[STORAGE] Kurang dari {JUMLAH_GAMBAR_MIN}. Download {kurang} gambar baru...")
        _download_pexels_batch(kurang)
        gambar_ada = sorted(
            glob.glob(f"{FOLDER_GAMBAR}/*.jpg") +
            glob.glob(f"{FOLDER_GAMBAR}/*.jpeg") +
            glob.glob(f"{FOLDER_GAMBAR}/*.png")
        )
        print(f"[STORAGE] Bank gambar sekarang: {len(gambar_ada)} file")
    else:
        print(f"[STORAGE] Bank gambar cukup.")

    if len(gambar_ada) > JUMLAH_GAMBAR_MAX:
        jumlah_hapus = len(gambar_ada) - JUMLAH_GAMBAR_MAX
        for f in gambar_ada[:jumlah_hapus]:
            try:
                os.remove(f)
            except Exception:
                pass
        print(f"[STORAGE] Hapus {jumlah_hapus} gambar lama.")
        gambar_ada = gambar_ada[jumlah_hapus:]

    return gambar_ada


def _download_pexels_batch(jumlah_target):
    if not PEXELS_API_KEY:
        print("  -> Pexels API key kosong. Skip download.")
        return 0

    headers     = {"Authorization": PEXELS_API_KEY}
    per_keyword = max(10, jumlah_target // len(KATA_KUNCI_GAMBAR))
    total_dl    = 0
    ts_base     = int(time.time())

    for keyword in KATA_KUNCI_GAMBAR:
        url = (f"https://api.pexels.com/v1/search"
               f"?query={keyword}&per_page={per_keyword}"
               f"&orientation=landscape&size=large")
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            fotos = resp.json().get("photos", [])
            for i, foto in enumerate(fotos):
                img_url  = foto["src"]["large2x"]
                filename = (f"{FOLDER_GAMBAR}/pexels_{ts_base}_"
                            f"{keyword.replace(' ','_')}_{i+1}.jpg")
                if os.path.exists(filename):
                    continue
                try:
                    img_data = requests.get(img_url, timeout=30).content
                    with open(filename, "wb") as f:
                        f.write(img_data)
                    total_dl += 1
                except Exception:
                    pass
            print(f"  -> '{keyword}': {len(fotos)} gambar OK")
            if total_dl >= jumlah_target:
                break
        except Exception as e:
            print(f"  -> Gagal fetch '{keyword}': {e}")

    print(f"  -> Total download: {total_dl} gambar baru")
    return total_dl


def kelola_video_lama():
    videos = sorted(glob.glob("Video_Emas_*.mp4"))
    if len(videos) > SIMPAN_VIDEO_MAKS:
        for v in videos[:len(videos) - SIMPAN_VIDEO_MAKS]:
            try:
                os.remove(v)
                print(f"[STORAGE] Hapus video lama: {v}")
            except Exception:
                pass


def ringkasan_storage():
    gambar_ada = (
        glob.glob(f"{FOLDER_GAMBAR}/*.jpg") +
        glob.glob(f"{FOLDER_GAMBAR}/*.jpeg") +
        glob.glob(f"{FOLDER_GAMBAR}/*.png")
    )
    videos        = glob.glob("Video_Emas_*.mp4")
    ukuran_gambar = sum(os.path.getsize(f) for f in gambar_ada if os.path.exists(f))
    ukuran_video  = sum(os.path.getsize(f) for f in videos  if os.path.exists(f))
    print(f"\n[STORAGE] Ringkasan:")
    print(f"  → Bank gambar : {len(gambar_ada)} file ({ukuran_gambar/1024/1024:.1f} MB)")
    print(f"  → Video lokal : {len(videos)} file ({ukuran_video/1024/1024:.1f} MB)")
    print(f"  → Total       : {(ukuran_gambar+ukuran_video)/1024/1024:.1f} MB")


# ════════════════════════════════════════════════════════════
# BAGIAN 2 — HISTORY HARGA (365 HARI)
# ════════════════════════════════════════════════════════════

def muat_history():
    if os.path.exists(FILE_HISTORY):
        try:
            with open(FILE_HISTORY, encoding="utf-8") as f:
                data = json.load(f)
            if "records" not in data and "harga_1_gram" in data:
                return {"records": [{"tanggal": data["tanggal"],
                                     "harga":   data["harga_1_gram"]}]}
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
    periode = {
        "kemarin": 1, "7_hari": 7,  "1_bulan": 30,
        "3_bulan": 90,"6_bulan":180, "1_tahun": 365,
    }
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
# BAGIAN 3 — JUDUL CLICKBAIT LOKAL (8 variasi per kondisi)
# ════════════════════════════════════════════════════════════

def buat_judul_clickbait_lokal(info, historis):
    h       = f"Rp {info['harga_sekarang']:,}".replace(",", ".")
    status  = info['status']
    selisih = f"Rp {info['selisih']:,}".replace(",", ".")
    tgl     = datetime.now().strftime("%d %b %Y")

    nama_periode = {
        "kemarin":"Kemarin","7_hari":"Seminggu",
        "1_bulan":"Sebulan","3_bulan":"3 Bulan",
        "6_bulan":"6 Bulan","1_tahun":"Setahun",
    }

    penting = None
    for label in ["3_bulan","1_bulan","6_bulan","1_tahun","7_hari"]:
        data = historis.get(label)
        if data and abs(data["persen"]) >= 2.0:
            penting = (label, data)
            break

    if penting:
        label, data = penting
        pct         = abs(data["persen"])
        arah        = "NAIK" if data["naik"] else "TURUN"
        pl          = nama_periode.get(label, label)
        if data["naik"]:
            pool = [
                f"🔥 NAIK {pct:.1f}% dalam {pl}! Emas Antam {h}/gram — Masih Beli?",
                f"EMAS ANTAM MELEJIT {pct:.1f}% Sejak {pl} Lalu! Harga {h} - Jual atau Tahan?",
                f"🚀 NAIK {pct:.1f}% dari {pl} Lalu! Kapan Emas Antam Berhenti Naik?",
                f"WASPADA! Emas Sudah NAIK {pct:.1f}% dalam {pl} — Kamu Rugi Kalau Belum Beli!",
                f"Harga Emas MELEDAK {pct:.1f}%! Dari {pl} Lalu ke {h}/gram — Beli Sekarang?",
                f"💰 PROFIT {pct:.1f}% dalam {pl}! Emas Antam Makin Mahal — Update {tgl}",
                f"EMAS {arah} {pct:.1f}% Sejak {pl}! Investor Panic Buy? Harga {h}",
                f"🆘 Harga Emas Sudah NAIK {pct:.1f}% — Terlambat Beli atau Masih Ada Peluang?",
            ]
        else:
            pool = [
                f"💥 TURUN {pct:.1f}% dalam {pl}! Emas Antam {h}/gram — Momentum Emas!",
                f"HARGA EMAS ANJLOK {pct:.1f}% dari {pl} Lalu! Saatnya Borong Emas Murah?",
                f"🎯 DISKON {pct:.1f}%! Emas Antam Kini {h}/gram — Beli Sekarang Sebelum Naik!",
                f"Emas TURUN {pct:.1f}% Sejak {pl}! Ini Harga Terbaik Beli Emas Antam?",
                f"🔔 ALERT! Harga Emas Sudah Koreksi {pct:.1f}% — {h}/gram Murah atau Belum?",
                f"INVESTOR PANIK! Emas {arah} {pct:.1f}% dalam {pl} — Apa yang Terjadi?",
                f"💸 Emas Antam TERKOREKSI {pct:.1f}%! Update Harga {h}/gram — {tgl}",
                f"KESEMPATAN EMAS! Harga Turun {pct:.1f}% Sejak {pl} — Jangan Lewatkan!",
            ]
    elif status == "Naik":
        pool = [
            f"🚨 EMAS NAIK {selisih} HARI INI! Antam {h}/gram — Masih Layak Beli?",
            f"NAIK LAGI! Harga Emas Antam {h}/gram — Sudah {selisih} Lebih Mahal dari Kemarin",
            f"💥 ALERT! Emas Antam Naik {selisih} Jadi {h}/gram — Jual atau Tahan?",
            f"Harga Emas MERANGKAK NAIK {selisih}! Kapan Berhenti? Antam {h}/gram",
            f"🔴 EMAS NAIK {selisih} — Kamu Rugi Kalau Belum Punya Emas Sekarang!",
            f"HARGA EMAS ANTAM NAIK {selisih} HARI INI! {h}/gram — Analisa Lengkap",
            f"⚠️ Emas Antam Naik Lagi! {selisih} Lebih Mahal — Update Harga {tgl}",
            f"Sinyal Bullish! Emas Antam {h}/gram Naik {selisih} — Beli Sekarang atau Nyesel?",
        ]
    elif status == "Turun":
        pool = [
            f"🎯 EMAS TURUN {selisih}! Ini Saat Terbaik Borong Emas Antam {h}/gram?",
            f"💚 DISKON! Emas Antam Turun {selisih} Jadi {h}/gram — Kapan Lagi Beli Murah?",
            f"HARGA EMAS MELEMAH {selisih}! Antam {h}/gram — Kapan Balik Naik?",
            f"📉 Emas Antam Koreksi {selisih} ke {h}/gram — Momentum Beli Paling Tepat?",
            f"🛒 BORONG SEKARANG? Emas Antam Turun {selisih} Jadi {h}/gram — {tgl}",
            f"INVESTOR HAPPY! Emas Antam Murah {selisih} — Harga {h}/gram Hari Ini",
            f"⬇️ Emas Antam TURUN {selisih}! Apakah Ini Titik Terendah? Analisa {tgl}",
            f"KESEMPATAN EMAS! Harga Turun {selisih} ke {h}/gram — Jangan Sampai Nyesel!",
        ]
    else:
        pool = [
            f"🤔 Harga Emas Antam STAGNAN di {h}/gram — Kapan Akan Bergerak Lagi?",
            f"SINYAL APA INI? Emas Antam Nyaman di {h}/gram — Naik atau Turun Selanjutnya?",
            f"⚠️ Emas Antam KONSOLIDASI {h}/gram — Para Analis Bilang Ini Berbahaya!",
            f"Harga Emas Antam {h}/gram Hari Ini — Tanda-Tanda Mau NAIK BESAR?",
            f"🟡 Emas Antam FLAT di {h}/gram — Strategi Investasi yang Tepat Saat Ini",
            f"WASPADA! Emas Antam {h}/gram Stagnan — Ini Peringatan Buat Investor!",
            f"😲 MENGEJUTKAN! Emas Antam Bertahan di {h}/gram — Penjelasan Lengkapnya",
            f"Emas Antam {h}/gram — Akumulasi atau Jual? Analisa Teknikal {tgl}",
        ]

    return random.choice(pool)[:100]


def _validasi_judul(judul_raw, info, historis):
    KATA_BOCOR = [
        "tentu", "berikut", "ini dia", "mari kita", "dengan senang",
        "baik,", "oke,", "siap,", "kamu adalah", "scriptwriter",
        "channel anda", "harga emas hari ini:", "harga emas batangan",
        "sobat emas!", "konten youtube", "naskah video",
    ]
    judul_cek = judul_raw.lower().strip()
    bocor     = any(k in judul_cek for k in KATA_BOCOR)
    if bocor or len(judul_raw.strip()) < 10:
        judul_fix = buat_judul_clickbait_lokal(info, historis)
        print(f"  -> [FIX] Judul bocor → diganti: {judul_fix}")
        return judul_fix
    return judul_raw.strip()[:100]


# ════════════════════════════════════════════════════════════
# BAGIAN 4 — SCRAPING HARGA EMAS
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
                ringkasan.append(f"{label}:{arah}{abs(data['persen']):.1f}%")

        print(f"  -> Rp {harga_1_gram:,} | {status} Rp {selisih:,} | "
              f"{len(records_baru)} hari tersimpan".replace(",", "."))
        print(f"  -> Historis: {' | '.join(ringkasan[:5])}")

        info = {
            "harga_sekarang": harga_1_gram,
            "status":         status,
            "selisih":        selisih,
            "historis":       historis,
            "total_record":   len(records_baru),
        }
        konteks = "; ".join([
            f"{lb}: {'naik' if d['naik'] else ('turun' if not d['stabil'] else 'stabil')} "
            f"{abs(d['persen']):.1f}% dari Rp {d['harga_ref']:,}".replace(",",".")
            for lb, d in historis.items() if d
        ])
        teks_data = (f"Tanggal: {tanggal}. Historis: {konteks}. "
                     f"Data Antam: {data_kasar[:2500]}...")
        return info, teks_data

    except Exception as e:
        print(f"  -> Gagal scraping: {e}")
        return None, None


# ════════════════════════════════════════════════════════════
# BAGIAN 5 — NARASI & JUDUL (GEMINI + FALLBACK LOKAL)
# ════════════════════════════════════════════════════════════

def _buat_narasi_fallback_lokal(info, harga_skrg, status_harga, selisih_harga):
    tanggal = datetime.now().strftime("%d %B %Y")
    hari    = {"Monday":"Senin","Tuesday":"Selasa","Wednesday":"Rabu",
               "Thursday":"Kamis","Friday":"Jumat",
               "Saturday":"Sabtu","Sunday":"Minggu"
               }.get(datetime.now().strftime("%A"), "")
    h       = info['harga_sekarang']
    tabel   = {
        "setengah gram":             h//2,
        "satu gram":                 h,
        "dua gram":                  h*2,
        "tiga gram":                 h*3,
        "lima gram":                 h*5,
        "sepuluh gram":              h*10,
        "dua puluh lima gram":       h*25,
        "lima puluh gram":           h*50,
        "seratus gram":              h*100,
        "dua ratus lima puluh gram": h*250,
        "lima ratus gram":           h*500,
        "seribu gram":               h*1000,
    }
    rp     = lambda x: f"Rp {x:,}".replace(",",".")
    daftar = " ".join(f"Untuk {s}, harganya {rp(v)}." for s,v in tabel.items())

    kalimat_status = {
        "Naik":   f"mengalami kenaikan sebesar Rupiah {selisih_harga} dari kemarin",
        "Turun":  f"mengalami penurunan sebesar Rupiah {selisih_harga} dari kemarin",
        "Stabil": "terpantau stabil dari hari sebelumnya",
    }.get(status_harga, "terpantau stabil")

    historis         = info.get("historis", {})
    kalimat_historis = ""
    for label, data in historis.items():
        if data and abs(data["persen"]) >= 1.0:
            arah = "naik" if data["naik"] else "turun"
            nama = {"kemarin":"kemarin","7_hari":"seminggu lalu",
                    "1_bulan":"sebulan lalu","3_bulan":"tiga bulan lalu",
                    "6_bulan":"enam bulan lalu","1_tahun":"setahun lalu"
                    }.get(label, label)
            kalimat_historis = (
                f" Jika dibandingkan dengan {nama}, harga emas telah {arah} "
                f"sebesar {abs(data['persen']):.1f} persen dari "
                f"{rp(data['harga_ref'])} menjadi {rp(h)}."
            )
            break

    narasi = f"""Halo sobat {NAMA_CHANNEL}, selamat datang kembali di channel kita tercinta. Hari ini hari {hari}, tanggal {tanggal}, dan seperti biasa kami hadir membawakan update terbaru harga emas Antam Logam Mulia untuk Anda semua.

Langsung kita masuk ke informasi utama. Harga emas Antam resmi hari ini untuk ukuran satu gram adalah {harga_skrg} Rupiah. Harga ini {kalimat_status}.{kalimat_historis} Informasi ini kami ambil langsung dari situs resmi Logam Mulia sehingga dapat dijadikan acuan yang akurat dan terpercaya.

Berikut daftar lengkap harga emas Antam hari ini untuk semua ukuran yang tersedia. {daftar} Itulah harga lengkap emas Antam hari ini. Pastikan selalu cek harga terbaru sebelum memutuskan membeli karena harga emas bergerak dinamis setiap harinya mengikuti pasar global.

Sekarang mari kita bahas faktor-faktor yang mempengaruhi pergerakan harga emas saat ini. Pertama, kebijakan suku bunga bank sentral Amerika Serikat Federal Reserve menjadi penentu utama arah harga emas global. Ketika suku bunga tinggi, dolar menguat dan emas cenderung tertekan karena investor beralih ke aset berbunga. Sebaliknya, penurunan suku bunga selalu menjadi katalis positif bagi harga emas. Kedua, ketidakpastian geopolitik global terus mendorong permintaan emas sebagai safe haven. Konflik di berbagai belahan dunia membuat investor mencari perlindungan nilai aset di emas yang sudah teruji selama ribuan tahun. Ketiga, nilai tukar Rupiah terhadap Dolar Amerika secara langsung menentukan harga emas dalam negeri. Pelemahan Rupiah otomatis mendorong harga emas dalam Rupiah menjadi lebih tinggi. Keempat, permintaan fisik dari India dan Tiongkok sebagai konsumen emas terbesar dunia turut mempengaruhi harga secara signifikan terutama menjelang musim perayaan dan hari besar keagamaan.

Bagi sobat yang ingin memulai atau menambah portofolio investasi emas, ada beberapa strategi yang telah terbukti efektif. Pertama, mulailah dari ukuran kecil seperti setengah gram atau satu gram agar tidak memberatkan keuangan Anda. Kedua, terapkan strategi dollar cost averaging yaitu membeli rutin setiap bulan dengan jumlah tetap tanpa peduli kondisi harga. Strategi ini terbukti menghasilkan harga rata-rata yang lebih baik dalam jangka panjang. Ketiga, manfaatkan momen penurunan harga sebagai kesempatan menambah koleksi karena emas secara historis selalu pulih dan mencetak rekor baru. Keempat, simpan emas fisik Anda di tempat yang aman baik di brankas khusus maupun menggunakan layanan titipan resmi dari Antam yang sudah terjamin keamanannya. Kelima, pisahkan emas investasi dari emas perhiasan karena emas batangan memiliki biaya produksi yang jauh lebih rendah sehingga lebih efisien sebagai instrumen investasi murni.

Demikian informasi lengkap harga emas Antam hari ini beserta analisa dan tips investasi dari kami di channel {NAMA_CHANNEL}. Semoga informasi ini bermanfaat dan membantu Anda dalam mengambil keputusan investasi yang tepat dan menguntungkan. Jangan lupa tekan tombol Subscribe dan aktifkan lonceng notifikasi agar tidak pernah ketinggalan update harga emas terbaru setiap hari. Bagikan video ini kepada keluarga dan teman yang membutuhkan informasi seputar investasi emas. Sampai jumpa di video berikutnya. Salam sukses dan salam investasi untuk sobat semua!""".strip()

    return narasi


def buat_narasi_dan_judul(info, data_harga):
    print("[2/6] Membuat judul + meminta Gemini menulis script...")

    status_harga  = info['status']
    selisih_harga = f"{info['selisih']:,}".replace(",",".")
    harga_skrg    = f"{info['harga_sekarang']:,}".replace(",",".")
    historis      = info.get("historis", {})

    # Judul SELALU dari lokal — tidak pernah dari Gemini
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
                f"Rp {data['harga_ref']:,}".replace(",",".")
            )
    konteks_historis = " | ".join(ringkasan_historis) or "Data historis belum tersedia."

    prompt = f"""Kamu adalah scriptwriter YouTube profesional. Tulis HANYA script narasi video.

BARIS PERTAMA HARUS PERSIS: "Halo sobat {NAMA_CHANNEL}," — tidak boleh ada teks apapun sebelumnya.

DATA:
- Channel: {NAMA_CHANNEL}
- Harga emas 1 gram hari ini: Rp {harga_skrg}
- Status vs kemarin: {status_harga} Rp {selisih_harga}
- Perbandingan historis: {konteks_historis}
- Data tabel Antam: {data_harga[:2000]}

STRUKTUR SCRIPT (TARGET 900-1000 KATA):
1. Pembuka (100 kata): Sapa penonton, umumkan harga Rp {harga_skrg}, status {status_harga}
2. Daftar harga (200 kata): Semua ukuran 0.5g sampai 1000g
3. Analisa historis & global (300 kata): Bahas data {konteks_historis}, kaitkan kondisi ekonomi dunia
4. Edukasi & penutup (300 kata): Tips investasi emas, ajakan subscribe {NAMA_CHANNEL}

ATURAN KERAS:
- MULAI LANGSUNG "Halo sobat {NAMA_CHANNEL}," — DILARANG tulis "Tentu", "Berikut", "Ini dia", atau kata pengantar apapun
- Semua angka ditulis dengan HURUF
- Paragraf narasi murni, TANPA bullet, TANPA nomor, TANPA simbol
- Bahasa Indonesia natural seperti presenter berita profesional"""

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
                script_raw = resp.json()['candidates'][0]['content']['parts'][0]['text'].strip()

                # Bersihkan kata pengantar jika Gemini masih menambahkan
                baris      = script_raw.split('\n')
                baris_baru = []
                skip_awal  = True
                for idx_b, baris_item in enumerate(baris):
                    b_lower = baris_item.lower().strip()
                    if skip_awal:
                        if b_lower.startswith("halo sobat"):
                            skip_awal = False
                            baris_baru.append(baris_item)
                        elif idx_b > 4:
                            skip_awal = False
                            baris_baru.append(baris_item)
                    else:
                        if not (b_lower.startswith("[judul]") or b_lower.startswith("[script]")):
                            baris_baru.append(baris_item)

                script = '\n'.join(baris_baru).strip()
                if not script:
                    script = script_raw

                jumlah_kata = len(script.split())
                print(f"  -> ✅ Script OK ({jumlah_kata} kata) dari {model_name}")

                judul = _validasi_judul(judul, info, historis)
                return judul, script

            except Exception as e:
                if "429" not in str(e):
                    print(f"  -> Error {model_name}: {e}")
                    break
                time.sleep((2**attempt)*10)

        print(f"  -> {model_name} gagal. Coba berikutnya...")

    print("  -> [FALLBACK] Pakai narasi template lokal...")
    narasi_fallback = _buat_narasi_fallback_lokal(info, harga_skrg, status_harga, selisih_harga)
    judul = _validasi_judul(judul, info, historis)
    return judul, narasi_fallback


# ════════════════════════════════════════════════════════════
# BAGIAN 6 — GENERATE SUARA
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
        raise ValueError(f"Audio terlalu pendek ({durasi:.1f}s)!")
    print(f"  -> ✅ Audio OK: {durasi:.0f} detik ({durasi/60:.1f} menit)")
    return durasi


# ════════════════════════════════════════════════════════════
# BAGIAN 7 — THUMBNAIL PROFESIONAL (outline tebal, kontras max)
# ════════════════════════════════════════════════════════════

def _cari_font(ukuran):
    from PIL import ImageFont
    font_paths = [
        "/usr/share/fonts/truetype/open-sans/OpenSans-Bold.ttf",
        "/usr/share/fonts/opentype/open-sans/OpenSans-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "C:/Windows/Fonts/verdanab.ttf",
        "font_temp.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, ukuran)
            except Exception:
                continue
    return ImageFont.load_default()


def _teks_outline(draw, posisi, teks, font, warna_teks, tebal_outline=4):
    """Gambar teks dengan outline hitam solid tebal di semua arah."""
    x, y = posisi
    for dx in range(-tebal_outline, tebal_outline+1):
        for dy in range(-tebal_outline, tebal_outline+1):
            if dx != 0 or dy != 0:
                draw.text((x+dx, y+dy), teks, font=font, fill=(0, 0, 0, 255))
    draw.text((x, y), teks, font=font, fill=warna_teks)


def buat_thumbnail(info, judul, gambar_bank, output_path="thumbnail.jpg"):
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    W, H = 1280, 720

    # Background
    if gambar_bank:
        bg_path = random.choice(gambar_bank)
        try:
            bg    = Image.open(bg_path).convert("RGB")
            bw,bh = bg.size
            skala = max(W/bw, H/bh)
            bg    = bg.resize((int(bw*skala), int(bh*skala)), Image.LANCZOS)
            bw,bh = bg.size
            bg    = bg.crop(((bw-W)//2, (bh-H)//2, (bw-W)//2+W, (bh-H)//2+H))
            bg    = ImageEnhance.Brightness(bg).enhance(0.55)
        except Exception as e:
            print(f"  -> Fallback bg: {e}")
            bg = Image.new("RGB", (W,H), (10,10,25))
    else:
        bg = Image.new("RGB", (W,H), (10,10,25))

    canvas = bg.copy()
    draw   = ImageDraw.Draw(canvas, "RGBA")

    # Overlay gelap gradient atas → bawah
    for y in range(H):
        alpha = int(120 + 100*(y/H))
        draw.line([(0,y),(W,y)], fill=(0,0,0,alpha))

    # Panel solid bawah dan atas
    draw.rectangle([(0, H-230),(W, H)],    fill=(0,0,0,230))
    draw.rectangle([(0, 0),    (W, 160)],  fill=(0,0,0,160))

    # Skema warna per status
    status = info['status']
    SKEMA  = {
        "Naik":   {"badge":(210,0,0),    "aksen":(255,60,60),
                   "teks_harga":(255,220,0),   "icon":"▲ NAIK"},
        "Turun":  {"badge":(0,150,60),   "aksen":(0,230,100),
                   "teks_harga":(100,255,150),  "icon":"▼ TURUN"},
        "Stabil": {"badge":(160,120,0),  "aksen":(255,195,0),
                   "teks_harga":(255,220,100),  "icon":"⬛ STABIL"},
    }
    sk = SKEMA.get(status, SKEMA["Stabil"])

    # Badge status — kiri atas
    bx1,by1,bx2,by2 = 30,22,390,118
    draw.rounded_rectangle([(bx1+4,by1+4),(bx2+4,by2+4)],
                           radius=14, fill=(0,0,0,200))
    draw.rounded_rectangle([(bx1,by1),(bx2,by2)],
                           radius=14, fill=(*sk["badge"],255))
    draw.rectangle([(bx1,by1),(bx1+12,by2)], fill=(*sk["aksen"],255))
    draw.rounded_rectangle([(bx1,by1),(bx2,by2)],
                           radius=14, outline=(255,255,255,180), width=2)

    font_badge = _cari_font(56)
    bbox_b     = draw.textbbox((0,0), sk["icon"], font=font_badge)
    tx_b = bx1+22+((bx2-bx1-22-(bbox_b[2]-bbox_b[0]))//2)
    ty_b = by1+((by2-by1-(bbox_b[3]-bbox_b[1]))//2)
    _teks_outline(draw, (tx_b,ty_b), sk["icon"], font_badge,
                  warna_teks=(255,255,255,255), tebal_outline=3)

    # Tanggal — kanan atas
    tgl_str  = datetime.now().strftime("%d %B %Y")
    font_tgl = _cari_font(34)
    bbox_tgl = draw.textbbox((0,0), tgl_str, font=font_tgl)
    tx_tgl   = W-(bbox_tgl[2]-bbox_tgl[0])-30
    ty_tgl   = 42
    _teks_outline(draw, (tx_tgl,ty_tgl), tgl_str, font_tgl,
                  warna_teks=(220,220,220,255), tebal_outline=3)

    # Harga besar — tengah
    harga_str  = f"Rp {info['harga_sekarang']:,}".replace(",",".")
    font_harga = _cari_font(130)
    bbox_h     = draw.textbbox((0,0), harga_str, font=font_harga)
    while (bbox_h[2]-bbox_h[0]) > W-60 and font_harga.size > 72:
        font_harga = _cari_font(font_harga.size-6)
        bbox_h     = draw.textbbox((0,0), harga_str, font=font_harga)

    tx_h = (W-(bbox_h[2]-bbox_h[0]))//2
    ty_h = 145
    _teks_outline(draw, (tx_h,ty_h), harga_str, font_harga,
                  warna_teks=(*sk["teks_harga"],255), tebal_outline=6)

    # Garis dekorasi bawah harga
    garis_y = ty_h + (bbox_h[3]-bbox_h[1]) + 12
    draw.rectangle([(tx_h, garis_y),
                    (tx_h+(bbox_h[2]-bbox_h[0]), garis_y+6)],
                   fill=(*sk["aksen"],220))

    # Subtitle "/gram · Emas Antam Resmi"
    font_sub = _cari_font(40)
    teks_sub = "/gram  ·  Emas Antam Resmi"
    bbox_sub = draw.textbbox((0,0), teks_sub, font=font_sub)
    tx_sub   = (W-(bbox_sub[2]-bbox_sub[0]))//2
    ty_sub   = garis_y + 16
    _teks_outline(draw, (tx_sub,ty_sub), teks_sub, font_sub,
                  warna_teks=(210,210,210,255), tebal_outline=3)

    # Teks highlight historis — panel bawah
    historis = info.get("historis", {})
    teks_hl  = ""
    for label, data in historis.items():
        if data and abs(data["persen"]) >= 1.5:
            arah = "NAIK" if data["naik"] else "TURUN"
            nama = {"kemarin":"KEMARIN","7_hari":"SEMINGGU","1_bulan":"SEBULAN",
                    "3_bulan":"3 BULAN","6_bulan":"6 BULAN","1_tahun":"SETAHUN"
                    }.get(label, label.upper())
            teks_hl = f"{arah} {abs(data['persen']):.1f}% DARI {nama} LALU!"
            break
    if not teks_hl:
        if status == "Naik":
            sel     = f"Rp {info['selisih']:,}".replace(",",".")
            teks_hl = f"NAIK {sel} DARI KEMARIN!"
        elif status == "Turun":
            sel     = f"Rp {info['selisih']:,}".replace(",",".")
            teks_hl = f"TURUN {sel} — SAATNYA BELI?"
        else:
            teks_hl = "UPDATE RESMI ANTAM — HARGA TERKINI!"

    font_hl = _cari_font(62)
    bbox_hl = draw.textbbox((0,0), teks_hl, font=font_hl)
    while (bbox_hl[2]-bbox_hl[0]) > W-40 and font_hl.size > 28:
        font_hl = _cari_font(font_hl.size-4)
        bbox_hl = draw.textbbox((0,0), teks_hl, font=font_hl)

    lebar_hl  = bbox_hl[2]-bbox_hl[0]
    tinggi_hl = bbox_hl[3]-bbox_hl[1]
    tx_hl     = (W-lebar_hl)//2
    ty_hl     = H-200
    pad_x, pad_y = 22, 14

    draw.rectangle(
        [(tx_hl-pad_x, ty_hl-pad_y),
         (tx_hl+lebar_hl+pad_x, ty_hl+tinggi_hl+pad_y)],
        fill=(*sk["badge"],240)
    )
    draw.rectangle(
        [(tx_hl-pad_x, ty_hl-pad_y),
         (tx_hl+lebar_hl+pad_x, ty_hl-pad_y+5)],
        fill=(*sk["aksen"],255)
    )
    draw.rectangle(
        [(tx_hl-pad_x, ty_hl+tinggi_hl+pad_y-5),
         (tx_hl+lebar_hl+pad_x, ty_hl+tinggi_hl+pad_y)],
        fill=(*sk["aksen"],255)
    )
    _teks_outline(draw, (tx_hl,ty_hl), teks_hl, font_hl,
                  warna_teks=(255,255,255,255), tebal_outline=3)

    # Nama channel — kanan bawah
    font_ch = _cari_font(38)
    teks_ch = f"▶  {NAMA_CHANNEL}"
    bbox_ch = draw.textbbox((0,0), teks_ch, font=font_ch)
    tx_ch   = W-(bbox_ch[2]-bbox_ch[0])-30
    ty_ch   = H-(bbox_ch[3]-bbox_ch[1])-22
    _teks_outline(draw, (tx_ch,ty_ch), teks_ch, font_ch,
                  warna_teks=(255,255,255,220), tebal_outline=3)
    draw.rectangle(
        [(tx_ch, ty_ch+(bbox_ch[3]-bbox_ch[1])+5),
         (W-28,  ty_ch+(bbox_ch[3]-bbox_ch[1])+10)],
        fill=(*sk["aksen"],220)
    )

    # Simpan
    final = Image.new("RGB", (W,H))
    final.paste(canvas.convert("RGB"), (0,0))
    final.save(output_path, "JPEG", quality=95, optimize=True)
    kb = os.path.getsize(output_path)//1024
    print(f"  -> ✅ Thumbnail: {output_path} ({kb} KB, {W}×{H}px)")
    return output_path


# ════════════════════════════════════════════════════════════
# BAGIAN 8 — RENDER VIDEO
# ════════════════════════════════════════════════════════════

def escape_ffmpeg_path(path):
    return path.replace('\\','/').replace(':','\\:')


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

    gambar_list = list(gambar_bank)
    random.shuffle(gambar_list)
    jumlah_klip = int(durasi_total_detik / 10) + 2
    while len(gambar_list) < jumlah_klip:
        gambar_list.extend(gambar_list)
    gambar_terpilih = gambar_list[:jumlah_klip]

    font_sistem = siapkan_font_lokal()
    tasks = [
        (i, img, font_sistem, os.path.abspath(f"temp_clips/klip_{i}.mp4"))
        for i, img in enumerate(gambar_terpilih)
    ]

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
        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
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
# BAGIAN 9 — DESKRIPSI DENGAN TIMESTAMP
# ════════════════════════════════════════════════════════════

def buat_deskripsi_dengan_timestamp(info, judul):
    tgl  = datetime.now().strftime("%d %B %Y")
    h    = f"Rp {info['harga_sekarang']:,}".replace(",",".")
    st   = info['status']
    sel  = f"Rp {info['selisih']:,}".replace(",",".")
    hist = info.get("historis", {})

    timestamps = [
        ("0:00", f"📌 Intro — Harga Emas Antam {h} ({st} {sel})"),
        ("0:30", "💰 Harga Resmi Emas 1 Gram Hari Ini"),
        ("1:30", "📊 Daftar Harga Lengkap Semua Ukuran (0.5g–1000g)"),
        ("3:30", "🌍 Analisa Faktor Global (Suku Bunga, Geopolitik, Dolar)"),
    ]
    punya_hist = any(d for d in hist.values() if d)
    if punya_hist:
        timestamps.append(("5:00", "📈 Perbandingan Harga Historis (Minggu/Bulan Lalu)"))
    timestamps.append(("6:30", "💡 Tips Investasi Emas yang Benar untuk Pemula"))
    timestamps.append(("7:30", "✅ Kesimpulan & Rekomendasi"))

    ts_text = "\n".join(f"{ts}  {label}" for ts, label in timestamps)

    hist_lines = []
    nama_map   = {
        "kemarin":"Kemarin","7_hari":"Seminggu lalu","1_bulan":"Sebulan lalu",
        "3_bulan":"3 bulan lalu","6_bulan":"6 bulan lalu","1_tahun":"Setahun lalu",
    }
    for label, data in hist.items():
        if data:
            arah  = "🔺 Naik" if data["naik"] else ("🔻 Turun" if not data["stabil"] else "⬛ Stabil")
            nama  = nama_map.get(label, label)
            hist_lines.append(
                f"  {arah} {abs(data['persen']):.1f}% vs {nama} "
                f"(dari Rp {data['harga_ref']:,})".replace(",",".")
            )
    hist_text = "\n".join(hist_lines) if hist_lines else "  Data historis belum tersedia."

    deskripsi = f"""📅 Update harga emas Antam hari ini, {tgl}.

━━━━━━━━━━━━━━━━━━━━━━
💰 HARGA EMAS ANTAM HARI INI
━━━━━━━━━━━━━━━━━━━━━━
✅ Harga 1 gram  : {h}
📊 Status        : {st} {sel} vs kemarin

📈 PERBANDINGAN HISTORIS:
{hist_text}

━━━━━━━━━━━━━━━━━━━━━━
⏱️ TIMESTAMP VIDEO
━━━━━━━━━━━━━━━━━━━━━━
{ts_text}

━━━━━━━━━━━━━━━━━━━━━━
ℹ️ Sumber data resmi: logammulia.com
Harga dapat berubah sewaktu-waktu. Video ini hanya sebagai referensi, bukan rekomendasi investasi.

🔔 SUBSCRIBE & aktifkan notifikasi 🔔
Agar tidak ketinggalan update harga emas setiap hari!

━━━━━━━━━━━━━━━━━━━━━━
#HargaEmas #EmasAntam #InvestasiEmas #LogamMulia #EmasHariIni
#HargaEmasAntam #UpdateEmas #EmasBatangan #InvestasiEmasBatangan
━━━━━━━━━━━━━━━━━━━━━━""".strip()

    return deskripsi


# ════════════════════════════════════════════════════════════
# BAGIAN 10 — UPLOAD YOUTUBE
# ════════════════════════════════════════════════════════════

def upload_ke_youtube(video_path, judul, deskripsi, tags, thumbnail_path=None):
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

        creds = Credentials(
            token=td.get("token"), refresh_token=td.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=td.get("client_id"), client_secret=td.get("client_secret"),
        )
        youtube = build("youtube", "v3", credentials=creds)

        # Validasi judul terakhir sebelum upload
        judul_final = judul.strip()[:100]
        if len(judul_final) < 10:
            judul_final = f"Harga Emas Antam Hari Ini - {datetime.now().strftime('%d %B %Y')}"

        body = {
            "snippet": {
                "title":           judul_final,
                "description":     deskripsi,
                "tags":            tags,
                "categoryId":      YOUTUBE_CATEGORY,
                "defaultLanguage": "id",
            },
            "status": {
                "privacyStatus":           "public",
                "selfDeclaredMadeForKids": False,
            }
        }
        media   = MediaFileUpload(video_path, mimetype="video/mp4",
                                  resumable=True, chunksize=5*1024*1024)
        request = youtube.videos().insert(part="snippet,status",
                                          body=body, media_body=media)
        response = None
        while response is None:
            status_up, response = request.next_chunk()
            if status_up:
                print(f"  -> Upload video: {int(status_up.progress()*100)}%", end='\r')

        video_id = response.get("id")
        print(f"\n  -> ✅ Video terupload! https://youtu.be/{video_id}")

        # Upload thumbnail
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                print(f"  -> Upload thumbnail...")
                thumb_media = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
                youtube.thumbnails().set(videoId=video_id, media_body=thumb_media).execute()
                print(f"  -> ✅ Thumbnail terupload!")
            except Exception as e:
                print(f"  -> ⚠️  Thumbnail gagal: {e}")
                print(f"     (Pastikan channel sudah verifikasi nomor HP di YouTube)")

        with open("upload_history.json", "a", encoding="utf-8") as f:
            json.dump({
                "tanggal":  datetime.now().isoformat(),
                "video_id": video_id,
                "judul":    judul_final,
                "url":      f"https://youtu.be/{video_id}",
            }, f, ensure_ascii=False)
            f.write("\n")

        return video_id

    except Exception as e:
        print(f"  -> Gagal upload YouTube: {e}")
        return None


# ════════════════════════════════════════════════════════════
# BAGIAN 11 — BERSIHKAN TEMP
# ════════════════════════════════════════════════════════════

def bersihkan_temp(file_list=None, audio=None, thumbnail=None):
    print("[+] Membersihkan file sementara...")
    for f in [audio, file_list, "font_temp.ttf", thumbnail]:
        if f and os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass
    for klip in glob.glob("temp_clips/*.mp4"):
        try:
            os.remove(klip)
        except Exception:
            pass
    if os.path.exists("temp_clips"):
        try:
            os.rmdir("temp_clips")
        except Exception:
            pass


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════

async def main():
    with open(FFMPEG_LOG, 'w', encoding='utf-8') as f:
        f.write(f"Log FFmpeg - {datetime.now()}\n{'='*60}\n")

    audio_temp     = "suara.mp3"
    tanggal_str    = datetime.now().strftime('%Y%m%d')
    video_hasil    = f"Video_Emas_{tanggal_str}.mp4"
    thumbnail_path = None
    file_list      = None

    print(f"\n{'='*60}")
    print(f"  AUTO VIDEO EMAS - {NAMA_CHANNEL}")
    print(f"  {datetime.now().strftime('%d %B %Y, %H:%M WIB')}")
    print(f"{'='*60}\n")

    # 0. Manajemen storage
    kelola_video_lama()
    gambar_bank = kelola_bank_gambar()
    if not gambar_bank:
        print("FATAL: Tidak ada gambar tersedia.")
        return

    # 1. Scrape harga
    info, data_harga = scrape_dan_kalkulasi
