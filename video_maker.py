# =============================================================
# AUTO VIDEO EMAS - FULL AUTOMATION v6.0
# Sobat Antam
# Ken Burns Effect + Video Pexels + Thumbnail Profesional
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
KATA_KUNCI_VIDEO  = [
    "gold bars", "gold investment", "financial market",
    "gold coins", "precious metals", "gold bullion",
]

# Resolusi & FPS video
VIDEO_WIDTH  = 1920
VIDEO_HEIGHT = 1080
FPS          = 30

# Manajemen storage
FOLDER_GAMBAR     = "gambar_bank"
FOLDER_VIDEO      = "video_bank"
JUMLAH_GAMBAR_MIN = 40
JUMLAH_GAMBAR_MAX = 150
JUMLAH_DL_GAMBAR  = 60
JUMLAH_VIDEO_MIN  = 10
JUMLAH_VIDEO_MAX  = 40
JUMLAH_DL_VIDEO   = 20
SIMPAN_VIDEO_MAKS = 3
# ============================================================


# ════════════════════════════════════════════════════════════
# BAGIAN 1 — MANAJEMEN STORAGE
# ════════════════════════════════════════════════════════════

def _list_gambar():
    return sorted(
        glob.glob(f"{FOLDER_GAMBAR}/*.jpg") +
        glob.glob(f"{FOLDER_GAMBAR}/*.jpeg") +
        glob.glob(f"{FOLDER_GAMBAR}/*.png")
    )

def _list_video_bank():
    return sorted(
        glob.glob(f"{FOLDER_VIDEO}/*.mp4") +
        glob.glob(f"{FOLDER_VIDEO}/*.mov")
    )


def kelola_bank_gambar():
    os.makedirs(FOLDER_GAMBAR, exist_ok=True)
    ada = _list_gambar()
    print(f"[STORAGE] Bank gambar: {len(ada)} file")

    if len(ada) < JUMLAH_GAMBAR_MIN:
        kurang = JUMLAH_DL_GAMBAR - len(ada)
        print(f"[STORAGE] Download {kurang} gambar baru dari Pexels...")
        _download_pexels_gambar(kurang)
        ada = _list_gambar()

    if len(ada) > JUMLAH_GAMBAR_MAX:
        for f in ada[:len(ada) - JUMLAH_GAMBAR_MAX]:
            try: os.remove(f)
            except: pass
        ada = _list_gambar()
        print(f"[STORAGE] Bank gambar setelah prune: {len(ada)}")

    return ada


def _download_pexels_gambar(jumlah_target):
    if not PEXELS_API_KEY:
        print("  -> Pexels API key kosong.")
        return 0
    headers     = {"Authorization": PEXELS_API_KEY}
    per_keyword = max(8, jumlah_target // len(KATA_KUNCI_GAMBAR))
    total_dl    = 0
    ts          = int(time.time())
    for keyword in KATA_KUNCI_GAMBAR:
        url = (f"https://api.pexels.com/v1/search"
               f"?query={keyword}&per_page={per_keyword}"
               f"&orientation=landscape&size=large")
        try:
            resp  = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            fotos = resp.json().get("photos", [])
            for i, foto in enumerate(fotos):
                fn = f"{FOLDER_GAMBAR}/pexels_{ts}_{keyword.replace(' ','_')}_{i+1}.jpg"
                if os.path.exists(fn): continue
                try:
                    data = requests.get(foto["src"]["large2x"], timeout=30).content
                    with open(fn, "wb") as f: f.write(data)
                    total_dl += 1
                except: pass
            print(f"  -> Gambar '{keyword}': {len(fotos)} OK")
            if total_dl >= jumlah_target: break
        except Exception as e:
            print(f"  -> Gagal gambar '{keyword}': {e}")
    print(f"  -> Total gambar terdownload: {total_dl}")
    return total_dl


def kelola_bank_video():
    os.makedirs(FOLDER_VIDEO, exist_ok=True)
    ada = _list_video_bank()
    print(f"[STORAGE] Bank video: {len(ada)} file")

    if len(ada) < JUMLAH_VIDEO_MIN:
        kurang = JUMLAH_DL_VIDEO - len(ada)
        print(f"[STORAGE] Download {kurang} video baru dari Pexels...")
        _download_pexels_video(kurang)
        ada = _list_video_bank()

    if len(ada) > JUMLAH_VIDEO_MAX:
        for f in ada[:len(ada) - JUMLAH_VIDEO_MAX]:
            try: os.remove(f)
            except: pass
        ada = _list_video_bank()
        print(f"[STORAGE] Bank video setelah prune: {len(ada)}")

    return ada


def _download_pexels_video(jumlah_target):
    if not PEXELS_API_KEY:
        print("  -> Pexels API key kosong.")
        return 0
    headers     = {"Authorization": PEXELS_API_KEY}
    per_keyword = max(4, jumlah_target // len(KATA_KUNCI_VIDEO))
    total_dl    = 0
    ts          = int(time.time())
    for keyword in KATA_KUNCI_VIDEO:
        url = (f"https://api.pexels.com/videos/search"
               f"?query={keyword}&per_page={per_keyword}"
               f"&orientation=landscape&size=medium")
        try:
            resp   = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            videos = resp.json().get("videos", [])
            for i, vid in enumerate(videos):
                # Ambil file HD terbaik (720p atau 1080p)
                files      = vid.get("video_files", [])
                file_terbaik = None
                for vf in sorted(files, key=lambda x: x.get("height", 0), reverse=True):
                    if vf.get("height", 0) >= 720 and vf.get("file_type") == "video/mp4":
                        file_terbaik = vf
                        break
                if not file_terbaik and files:
                    file_terbaik = files[0]
                if not file_terbaik: continue

                fn = f"{FOLDER_VIDEO}/pexels_{ts}_{keyword.replace(' ','_')}_{i+1}.mp4"
                if os.path.exists(fn): continue
                try:
                    print(f"  -> Download video '{keyword}' [{i+1}]...")
                    data = requests.get(file_terbaik["link"], timeout=60).content
                    with open(fn, "wb") as f: f.write(data)
                    total_dl += 1
                    print(f"  -> ✅ {fn} ({len(data)//1024} KB)")
                except Exception as e:
                    print(f"  -> Gagal download video: {e}")
            if total_dl >= jumlah_target: break
        except Exception as e:
            print(f"  -> Gagal video '{keyword}': {e}")
    print(f"  -> Total video terdownload: {total_dl}")
    return total_dl


def kelola_video_lama():
    videos = sorted(glob.glob("Video_Emas_*.mp4"))
    if len(videos) > SIMPAN_VIDEO_MAKS:
        for v in videos[:len(videos) - SIMPAN_VIDEO_MAKS]:
            try:
                os.remove(v)
                print(f"[STORAGE] Hapus video lama: {v}")
            except: pass


def ringkasan_storage():
    gambar = _list_gambar()
    videos = _list_video_bank()
    hasil  = glob.glob("Video_Emas_*.mp4")
    ug = sum(os.path.getsize(f) for f in gambar if os.path.exists(f))
    uv = sum(os.path.getsize(f) for f in videos if os.path.exists(f))
    uh = sum(os.path.getsize(f) for f in hasil  if os.path.exists(f))
    print(f"\n[STORAGE] Ringkasan:")
    print(f"  → Bank gambar     : {len(gambar)} file ({ug/1024/1024:.1f} MB)")
    print(f"  → Bank video      : {len(videos)} file ({uv/1024/1024:.1f} MB)")
    print(f"  → Video hasil     : {len(hasil)} file ({uh/1024/1024:.1f} MB)")
    print(f"  → Total           : {(ug+uv+uh)/1024/1024:.1f} MB")


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
        except: pass
    return {"records": []}


def simpan_history(harga):
    history  = muat_history()
    records  = history.get("records", [])
    hari_ini = datetime.now().strftime("%Y-%m-%d")
    records  = [r for r in records if r["tanggal"] != hari_ini]
    records.insert(0, {"tanggal": hari_ini, "harga": harga})
    records  = records[:365]
    with open(FILE_HISTORY, "w", encoding="utf-8") as f:
        json.dump({"records": records}, f, indent=2, ensure_ascii=False)
    return records


def cari_harga_n_hari_lalu(records, n):
    target = (datetime.now().date() - timedelta(days=n)).strftime("%Y-%m-%d")
    for r in records:
        if r["tanggal"] <= target:
            return r
    return None


def analisa_historis(harga_sekarang, records):
    periode = {"kemarin":1,"7_hari":7,"1_bulan":30,"3_bulan":90,"6_bulan":180,"1_tahun":365}
    hasil   = {}
    for label, n in periode.items():
        rec = cari_harga_n_hari_lalu(records, n)
        if rec:
            s = harga_sekarang - rec["harga"]
            p = round((s / rec["harga"]) * 100, 2)
            hasil[label] = {
                "tanggal":   rec["tanggal"],
                "harga_ref": rec["harga"],
                "selisih":   s,
                "persen":    p,
                "naik":      s > 0,
                "stabil":    s == 0,
            }
    return hasil


# ════════════════════════════════════════════════════════════
# BAGIAN 3 — JUDUL CLICKBAIT LOKAL (8 variasi per kondisi)
# ════════════════════════════════════════════════════════════

def buat_judul_clickbait_lokal(info, historis):
    h       = f"Rp {info['harga_sekarang']:,}".replace(",",".")
    status  = info['status']
    selisih = f"Rp {info['selisih']:,}".replace(",",".")
    tgl     = datetime.now().strftime("%d %b %Y")

    nama_periode = {
        "kemarin":"Kemarin","7_hari":"Seminggu","1_bulan":"Sebulan",
        "3_bulan":"3 Bulan","6_bulan":"6 Bulan","1_tahun":"Setahun",
    }
    penting = None
    for label in ["3_bulan","1_bulan","6_bulan","1_tahun","7_hari"]:
        data = historis.get(label)
        if data and abs(data["persen"]) >= 2.0:
            penting = (label, data)
            break

    if penting:
        label, data = penting
        pct = abs(data["persen"])
        pl  = nama_periode.get(label, label)
        if data["naik"]:
            pool = [
                f"🔥 NAIK {pct:.1f}% dalam {pl}! Emas Antam {h}/gram — Masih Beli?",
                f"EMAS ANTAM MELEJIT {pct:.1f}% Sejak {pl} Lalu! {h} - Jual atau Tahan?",
                f"🚀 NAIK {pct:.1f}% dari {pl} Lalu! Kapan Emas Antam Berhenti Naik?",
                f"WASPADA! Emas Sudah NAIK {pct:.1f}% dalam {pl} — Kamu Rugi Kalau Belum Beli!",
                f"Harga Emas MELEDAK {pct:.1f}%! Dari {pl} ke {h}/gram — Beli Sekarang?",
                f"💰 PROFIT {pct:.1f}% dalam {pl}! Emas Antam Makin Mahal — Update {tgl}",
                f"EMAS NAIK {pct:.1f}% Sejak {pl}! Investor Panic Buy? Harga {h}",
                f"🆘 Harga Emas Sudah NAIK {pct:.1f}% — Terlambat Beli atau Masih Peluang?",
            ]
        else:
            pool = [
                f"💥 TURUN {pct:.1f}% dalam {pl}! Emas Antam {h}/gram — Momentum Emas!",
                f"HARGA EMAS ANJLOK {pct:.1f}% dari {pl} Lalu! Saatnya Borong Murah?",
                f"🎯 DISKON {pct:.1f}%! Emas Antam Kini {h}/gram — Beli Sebelum Naik!",
                f"Emas TURUN {pct:.1f}% Sejak {pl}! Ini Harga Terbaik Beli Emas?",
                f"🔔 ALERT! Harga Emas Koreksi {pct:.1f}% — {h}/gram Murah atau Belum?",
                f"INVESTOR PANIK! Emas TURUN {pct:.1f}% dalam {pl} — Apa yang Terjadi?",
                f"💸 Emas Antam TERKOREKSI {pct:.1f}%! Update Harga {h}/gram — {tgl}",
                f"KESEMPATAN EMAS! Harga Turun {pct:.1f}% Sejak {pl} — Jangan Lewatkan!",
            ]
    elif status == "Naik":
        pool = [
            f"🚨 EMAS NAIK {selisih} HARI INI! Antam {h}/gram — Masih Layak Beli?",
            f"NAIK LAGI! Emas Antam {h}/gram — Sudah {selisih} Lebih Mahal dari Kemarin",
            f"💥 ALERT! Emas Antam Naik {selisih} Jadi {h}/gram — Jual atau Tahan?",
            f"Harga Emas MERANGKAK NAIK {selisih}! Kapan Berhenti? Antam {h}/gram",
            f"🔴 EMAS NAIK {selisih} — Rugi Kalau Belum Punya Emas Sekarang!",
            f"HARGA EMAS ANTAM NAIK {selisih} HARI INI! {h}/gram — Analisa Lengkap",
            f"⚠️ Emas Antam Naik Lagi! {selisih} Lebih Mahal — Update Harga {tgl}",
            f"Sinyal Bullish! Emas Antam {h}/gram Naik {selisih} — Beli Sekarang atau Nyesel?",
        ]
    elif status == "Turun":
        pool = [
            f"🎯 EMAS TURUN {selisih}! Saat Terbaik Borong Emas Antam {h}/gram?",
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
            f"SINYAL APA INI? Emas Antam {h}/gram — Naik atau Turun Selanjutnya?",
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
        "channel anda", "naskah video", "konten youtube", "sobat emas!",
    ]
    if any(k in judul_raw.lower() for k in KATA_BOCOR) or len(judul_raw.strip()) < 10:
        fix = buat_judul_clickbait_lokal(info, historis)
        print(f"  -> [FIX JUDUL] Bocor → diganti: {fix}")
        return fix
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
                tk = cells[0].text.strip().lower()
                if tk in ('1 gr', '1 gram'):
                    a = re.sub(r'[^\d]', '', cells[1].text)
                    if a:
                        harga_1_gram = int(a)
                        break

        if harga_1_gram == 0:
            print("  -> ERROR: Gagal parse harga.")
            return None, None

        history_data = muat_history()
        records      = history_data.get("records", [])
        historis     = analisa_historis(harga_1_gram, records)

        kmrn = historis.get("kemarin")
        if kmrn:
            s      = kmrn["selisih"]
            status = "Naik" if s > 0 else ("Turun" if s < 0 else "Stabil")
            selisih = abs(s)
        else:
            status, selisih = "Stabil", 0

        records_baru = simpan_history(harga_1_gram)

        ringkasan = [
            f"{lb}:{'↑' if d['naik'] else ('↓' if not d['stabil'] else '→')}"
            f"{abs(d['persen']):.1f}%"
            for lb, d in historis.items() if d
        ]
        print(f"  -> Rp {harga_1_gram:,} | {status} Rp {selisih:,} | "
              f"{len(records_baru)} hari".replace(",","."))
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
        teks_data = f"Tanggal: {tanggal}. Historis: {konteks}. Data: {data_kasar[:2500]}..."
        return info, teks_data

    except Exception as e:
        print(f"  -> Gagal scraping: {e}")
        return None, None


# ════════════════════════════════════════════════════════════
# BAGIAN 5 — NARASI & JUDUL
# ════════════════════════════════════════════════════════════

def _buat_narasi_fallback_lokal(info, harga_skrg, status_harga, selisih_harga):
    tanggal = datetime.now().strftime("%d %B %Y")
    hari    = {"Monday":"Senin","Tuesday":"Selasa","Wednesday":"Rabu",
               "Thursday":"Kamis","Friday":"Jumat",
               "Saturday":"Sabtu","Sunday":"Minggu"
               }.get(datetime.now().strftime("%A"), "")
    h       = info['harga_sekarang']
    tabel   = {
        "setengah gram":h//2,"satu gram":h,"dua gram":h*2,"tiga gram":h*3,
        "lima gram":h*5,"sepuluh gram":h*10,"dua puluh lima gram":h*25,
        "lima puluh gram":h*50,"seratus gram":h*100,
        "dua ratus lima puluh gram":h*250,"lima ratus gram":h*500,"seribu gram":h*1000,
    }
    rp     = lambda x: f"Rp {x:,}".replace(",",".")
    daftar = " ".join(f"Untuk {s}, harganya {rp(v)}." for s,v in tabel.items())
    kalimat_status = {
        "Naik":  f"mengalami kenaikan sebesar Rupiah {selisih_harga} dari kemarin",
        "Turun": f"mengalami penurunan sebesar Rupiah {selisih_harga} dari kemarin",
        "Stabil":"terpantau stabil dari hari sebelumnya",
    }.get(status_harga, "terpantau stabil")

    historis = info.get("historis", {})
    kalimat_historis = ""
    for label, data in historis.items():
        if data and abs(data["persen"]) >= 1.0:
            arah = "naik" if data["naik"] else "turun"
            nama = {"kemarin":"kemarin","7_hari":"seminggu lalu","1_bulan":"sebulan lalu",
                    "3_bulan":"tiga bulan lalu","6_bulan":"enam bulan lalu",
                    "1_tahun":"setahun lalu"}.get(label, label)
            kalimat_historis = (
                f" Jika dibandingkan dengan {nama}, harga emas telah {arah} "
                f"sebesar {abs(data['persen']):.1f} persen dari "
                f"{rp(data['harga_ref'])} menjadi {rp(h)}."
            )
            break

    return f"""Halo sobat {NAMA_CHANNEL}, selamat datang kembali di channel kita tercinta. Hari ini hari {hari}, tanggal {tanggal}, dan seperti biasa kami hadir membawakan update terbaru harga emas Antam Logam Mulia untuk Anda semua.

Langsung kita masuk ke informasi utama. Harga emas Antam resmi hari ini untuk ukuran satu gram adalah {harga_skrg} Rupiah. Harga ini {kalimat_status}.{kalimat_historis} Informasi ini kami ambil langsung dari situs resmi Logam Mulia sehingga dapat dijadikan acuan yang akurat dan terpercaya.

Berikut daftar lengkap harga emas Antam hari ini untuk semua ukuran yang tersedia. {daftar} Itulah harga lengkap emas Antam hari ini. Pastikan selalu cek harga terbaru sebelum memutuskan membeli karena harga emas bergerak dinamis setiap harinya mengikuti pasar global.

Sekarang mari kita bahas faktor-faktor yang mempengaruhi pergerakan harga emas saat ini. Pertama, kebijakan suku bunga bank sentral Amerika Serikat Federal Reserve menjadi penentu utama arah harga emas global. Ketika suku bunga tinggi, dolar menguat dan emas cenderung tertekan karena investor beralih ke aset berbunga. Sebaliknya, penurunan suku bunga selalu menjadi katalis positif bagi harga emas. Kedua, ketidakpastian geopolitik global terus mendorong permintaan emas sebagai safe haven. Konflik di berbagai belahan dunia membuat investor mencari perlindungan nilai aset di emas yang sudah teruji selama ribuan tahun. Ketiga, nilai tukar Rupiah terhadap Dolar Amerika secara langsung menentukan harga emas dalam negeri. Pelemahan Rupiah otomatis mendorong harga emas dalam Rupiah menjadi lebih tinggi. Keempat, permintaan fisik dari India dan Tiongkok sebagai konsumen emas terbesar dunia turut mempengaruhi harga secara signifikan terutama menjelang musim perayaan dan hari besar keagamaan.

Bagi sobat yang ingin memulai atau menambah portofolio investasi emas, ada beberapa strategi yang telah terbukti efektif. Pertama, mulailah dari ukuran kecil seperti setengah gram atau satu gram agar tidak memberatkan keuangan Anda. Kedua, terapkan strategi dollar cost averaging yaitu membeli rutin setiap bulan dengan jumlah tetap tanpa peduli kondisi harga. Ketiga, manfaatkan momen penurunan harga sebagai kesempatan menambah koleksi karena emas secara historis selalu pulih dan mencetak rekor baru. Keempat, simpan emas fisik Anda di tempat yang aman baik di brankas khusus maupun menggunakan layanan titipan resmi dari Antam. Kelima, pisahkan emas investasi dari emas perhiasan karena emas batangan memiliki biaya produksi yang jauh lebih rendah sehingga lebih efisien sebagai instrumen investasi murni.

Demikian informasi lengkap harga emas Antam hari ini beserta analisa dan tips investasi dari kami di channel {NAMA_CHANNEL}. Semoga informasi ini bermanfaat dan membantu Anda mengambil keputusan investasi yang tepat. Jangan lupa tekan tombol Subscribe dan aktifkan lonceng notifikasi agar tidak pernah ketinggalan update harga emas terbaru setiap hari. Sampai jumpa di video berikutnya. Salam sukses dan salam investasi untuk sobat semua!""".strip()


def buat_narasi_dan_judul(info, data_harga):
    print("[2/6] Membuat judul + meminta Gemini menulis script...")

    status_harga  = info['status']
    selisih_harga = f"{info['selisih']:,}".replace(",",".")
    harga_skrg    = f"{info['harga_sekarang']:,}".replace(",",".")
    historis      = info.get("historis", {})

    judul = buat_judul_clickbait_lokal(info, historis)
    print(f"  -> Judul: {judul}")

    ringkasan_h = []
    for label, data in historis.items():
        if data:
            arah = "naik" if data["naik"] else ("turun" if not data["stabil"] else "stabil")
            nama = {"kemarin":"kemarin","7_hari":"seminggu lalu","1_bulan":"sebulan lalu",
                    "3_bulan":"3 bulan lalu","6_bulan":"6 bulan lalu","1_tahun":"setahun lalu"
                    }.get(label, label)
            ringkasan_h.append(f"{nama}: {arah} {abs(data['persen']):.1f}% dari Rp {data['harga_ref']:,}".replace(",","."))
    konteks = " | ".join(ringkasan_h) or "Data historis belum tersedia."

    prompt = f"""Kamu adalah scriptwriter YouTube profesional. Tulis HANYA script narasi video.

BARIS PERTAMA HARUS PERSIS: "Halo sobat {NAMA_CHANNEL}," — tidak boleh ada teks apapun sebelumnya.

DATA:
- Channel: {NAMA_CHANNEL}
- Harga emas 1 gram: Rp {harga_skrg}
- Status: {status_harga} Rp {selisih_harga} vs kemarin
- Historis: {konteks}
- Data Antam: {data_harga[:2000]}

STRUKTUR (TARGET 900-1000 KATA):
1. Pembuka (100 kata): Sapa penonton, sebut harga Rp {harga_skrg}, status {status_harga}
2. Daftar harga (200 kata): Semua ukuran 0.5g sampai 1000g
3. Analisa historis & global (300 kata): Bahas {konteks}, kaitkan ekonomi dunia
4. Edukasi & penutup (300 kata): Tips investasi emas, ajakan subscribe {NAMA_CHANNEL}

ATURAN KERAS:
- MULAI LANGSUNG "Halo sobat {NAMA_CHANNEL}," — DILARANG tulis kata pengantar apapun
- Semua angka ditulis dengan HURUF
- Paragraf narasi murni, TANPA bullet, TANPA nomor, TANPA simbol
- Bahasa Indonesia natural seperti presenter berita"""

    MODEL_CHAIN = ["gemini-2.0-flash-lite","gemini-2.0-flash","gemini-2.5-flash-lite"]

    for model_name in MODEL_CHAIN:
        for attempt in range(3):
            try:
                url_api = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                           f"{model_name}:generateContent?key={GEMINI_API_KEY}")
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": 8192, "temperature": 0.85}
                }
                print(f"  -> {model_name} attempt {attempt+1}...")
                resp = requests.post(url_api, json=payload, timeout=90)
                if resp.status_code == 429:
                    t = int(resp.headers.get('Retry-After', (2**attempt)*10))
                    print(f"  -> 429. Tunggu {t}s...")
                    time.sleep(t)
                    continue
                resp.raise_for_status()
                script_raw = resp.json()['candidates'][0]['content']['parts'][0]['text'].strip()

                baris      = script_raw.split('\n')
                baris_baru = []
                skip       = True
                for idx, b in enumerate(baris):
                    bl = b.lower().strip()
                    if skip:
                        if bl.startswith("halo sobat"):
                            skip = False
                            baris_baru.append(b)
                        elif idx > 4:
                            skip = False
                            baris_baru.append(b)
                    else:
                        if not (bl.startswith("[judul]") or bl.startswith("[script]")):
                            baris_baru.append(b)

                script = '\n'.join(baris_baru).strip() or script_raw
                print(f"  -> ✅ Script OK ({len(script.split())} kata) dari {model_name}")
                judul = _validasi_judul(judul, info, historis)
                return judul, script

            except Exception as e:
                if "429" not in str(e):
                    print(f"  -> Error {model_name}: {e}")
                    break
                time.sleep((2**attempt)*10)
        print(f"  -> {model_name} gagal.")

    print("  -> [FALLBACK] Pakai narasi lokal...")
    narasi = _buat_narasi_fallback_lokal(info, harga_skrg, status_harga, selisih_harga)
    judul  = _validasi_judul(judul, info, historis)
    return judul, narasi


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
# BAGIAN 7 — KEN BURNS EFFECT + RENDER KLIP
# ════════════════════════════════════════════════════════════

def _get_ken_burns_filter(durasi=10.0):
    """6 mode Ken Burns effect: zoom in/out + pan 4 arah."""
    try:
        dur = max(5.0, float(durasi))
    except:
        dur = 10.0

    d_frames = int(FPS * dur)
    mode     = random.randint(1, 6)

    if mode == 1:
        z = "if(eq(on,1),1.0,min(zoom+0.0004,1.15))"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    elif mode == 2:
        z = "if(eq(on,1),1.15,max(zoom-0.0004,1.0))"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    elif mode == 3:
        z = "if(eq(on,1),1.02,min(zoom+0.0003,1.15))"
        x = f"(iw-ow)*(on/{d_frames})*0.6"
        y = "ih/2-(ih/zoom/2)"
    elif mode == 4:
        z = "if(eq(on,1),1.02,min(zoom+0.0003,1.15))"
        x = f"(iw-ow)*(1-on/{d_frames})*0.6"
        y = "ih/2-(ih/zoom/2)"
    elif mode == 5:
        z = "if(eq(on,1),1.02,min(zoom+0.0003,1.15))"
        x = "iw/2-(iw/zoom/2)"
        y = f"(ih-oh)*(on/{d_frames})*0.6"
    else:
        z = "if(eq(on,1),1.02,min(zoom+0.0003,1.15))"
        x = "iw/2-(iw/zoom/2)"
        y = f"(ih-oh)*(1-on/{d_frames})*0.6"

    zoompan = (
        f"zoompan=z='{z}':x='{x}':y='{y}':"
        f"d={d_frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={FPS}"
    )
    vf = (
        f"scale={VIDEO_WIDTH*2}:{VIDEO_HEIGHT*2}:"
        f"force_original_aspect_ratio=increase,"
        f"crop={VIDEO_WIDTH*2}:{VIDEO_HEIGHT*2},"
        f"{zoompan},"
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
        f"fade=t=in:st=0:d=0.5,fade=t=out:st={dur-0.5:.1f}:d=0.5"
    )
    return vf


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
            except: continue
    print("  -> PERINGATAN: Font tidak ditemukan.")
    return None


def _render_klip_gambar(args):
    """Render 1 klip dari gambar dengan Ken Burns effect."""
    i, img, font_sistem, output_klip = args
    durasi_klip = random.choice([8, 10, 12])
    vf          = _get_ken_burns_filter(durasi_klip)

    if font_sistem:
        font_esc = escape_ffmpeg_path(font_sistem)
        x, y    = random.choice([("30","30"),("w-tw-30","30"),
                                  ("30","h-th-30"),("w-tw-30","h-th-30")])
        vf += (f",drawtext=fontfile='{font_esc}'"
               f":text='{NAMA_CHANNEL}'"
               f":fontcolor=white@0.6:fontsize=28:x={x}:y={y}")

    cmd = [
        'ffmpeg', '-y',
        '-loop', '1', '-framerate', str(FPS), '-i', img,
        '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
        '-vf', vf,
        '-map', '0:v', '-map', '1:a',
        '-c:v', 'libx264', '-preset', 'faster',
        '-pix_fmt', 'yuv420p', '-crf', '23',
        '-c:a', 'aac',
        '-t', str(durasi_klip), output_klip
    ]
    with open(FFMPEG_LOG, 'a', encoding='utf-8') as log:
        log.write(f"\n=== Klip-IMG {i}: {os.path.basename(img)} ===\n")
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=log)

    if result.returncode != 0 or not os.path.exists(output_klip) or os.path.getsize(output_klip) < 1000:
        return None
    return i, output_klip


def _render_klip_video(args):
    """Render 1 klip dari video Pexels (potong ke durasi random)."""
    i, vid_path, font_sistem, output_klip = args
    durasi_klip = random.choice([8, 10, 12])

    # Cek durasi video sumber
    try:
        res = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', vid_path],
            capture_output=True, text=True, timeout=10
        )
        dur_src = float(res.stdout.strip())
    except:
        dur_src = 30.0

    # Random start agar tiap pakai berbeda
    max_start = max(0, dur_src - durasi_klip - 1)
    start     = random.uniform(0, max_start) if max_start > 0 else 0

    vf = (
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
        f"force_original_aspect_ratio=decrease,"
        f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
        f"fps={FPS},"
        f"fade=t=in:st=0:d=0.5,"
        f"fade=t=out:st={durasi_klip-0.5:.1f}:d=0.5"
    )
    if font_sistem:
        font_esc = escape_ffmpeg_path(font_sistem)
        x, y    = random.choice([("30","30"),("w-tw-30","30"),
                                  ("30","h-th-30"),("w-tw-30","h-th-30")])
        vf += (f",drawtext=fontfile='{font_esc}'"
               f":text='{NAMA_CHANNEL}'"
               f":fontcolor=white@0.6:fontsize=28:x={x}:y={y}")

    cmd = [
        'ffmpeg', '-y',
        '-ss', str(start), '-i', vid_path,
        '-vf', vf,
        '-c:v', 'libx264', '-preset', 'faster',
        '-pix_fmt', 'yuv420p', '-crf', '23',
        '-an',  # audio dari video dibuang, nanti diganti narasi
        '-t', str(durasi_klip), output_klip
    ]
    with open(FFMPEG_LOG, 'a', encoding='utf-8') as log:
        log.write(f"\n=== Klip-VID {i}: {os.path.basename(vid_path)} ===\n")
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=log)

    if result.returncode != 0 or not os.path.exists(output_klip) or os.path.getsize(output_klip) < 1000:
        return None
    return i, output_klip


def proses_media(durasi_total_detik, gambar_bank, video_bank):
    print(f"[4/6] Render klip media paralel ({min(4, os.cpu_count() or 2)} thread)...")
    os.makedirs("temp_clips", exist_ok=True)

    jumlah_klip = int(durasi_total_detik / 10) + 3

    # Campur gambar dan video: 60% gambar, 40% video (jika video tersedia)
    sumber_klip = []
    if video_bank:
        jml_vid = max(1, jumlah_klip * 40 // 100)
        jml_img = jumlah_klip - jml_vid
        vid_list = list(video_bank) * (jml_vid // len(video_bank) + 1)
        img_list = list(gambar_bank) * (jml_img // max(1,len(gambar_bank)) + 1)
        random.shuffle(vid_list)
        random.shuffle(img_list)
        # Interleave: gambar, gambar, video, gambar, video, ...
        urutan = []
        vi, ii = 0, 0
        for k in range(jumlah_klip):
            if k % 3 == 2 and vi < jml_vid:
                urutan.append(('video', vid_list[vi]))
                vi += 1
            elif ii < jml_img:
                urutan.append(('gambar', img_list[ii]))
                ii += 1
            elif vi < jml_vid:
                urutan.append(('video', vid_list[vi]))
                vi += 1
    else:
        img_list = list(gambar_bank) * (jumlah_klip // max(1,len(gambar_bank)) + 1)
        random.shuffle(img_list)
        urutan = [('gambar', img_list[k]) for k in range(jumlah_klip)]

    if not urutan:
        print("ERROR: Tidak ada media!")
        return None

    font_sistem = siapkan_font_lokal()
    tasks_img   = []
    tasks_vid   = []
    for i, (tipe, path) in enumerate(urutan):
        out = os.path.abspath(f"temp_clips/klip_{i:04d}.mp4")
        if tipe == 'gambar':
            tasks_img.append((i, path, font_sistem, out))
        else:
            tasks_vid.append((i, path, font_sistem, out))

    klip_berhasil = {}
    total = len(tasks_img) + len(tasks_vid)

    with ThreadPoolExecutor(max_workers=min(4, os.cpu_count() or 2)) as executor:
        futures = {}
        for t in tasks_img:
            futures[executor.submit(_render_klip_gambar, t)] = t[0]
        for t in tasks_vid:
            futures[executor.submit(_render_klip_video, t)] = t[0]

        for future in as_completed(futures):
            hasil = future.result()
            if hasil:
                idx, path = hasil
                klip_berhasil[idx] = path
            print(f"  -> {len(klip_berhasil)}/{total} klip selesai", end='\r')

    print(f"\n  -> {len(klip_berhasil)}/{total} klip berhasil "
          f"({len(tasks_img)} gambar + {len(tasks_vid)} video).")

    if not klip_berhasil:
        return None

    # Klip video tidak punya audio — tambah audio diam agar concat tidak error
    tasks_audio = []
    for idx, path in klip_berhasil.items():
        out_a = path.replace(".mp4", "_a.mp4")
        tasks_audio.append((path, out_a))

    def tambah_audio_diam(args):
        src, dst = args
        cmd = [
            'ffmpeg', '-y', '-i', src,
            '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
            '-c:v', 'copy', '-c:a', 'aac', '-shortest', dst
        ]
        with open(FFMPEG_LOG, 'a') as log:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=log)
        if os.path.exists(dst) and os.path.getsize(dst) > 1000:
            os.replace(dst, src)

    with ThreadPoolExecutor(max_workers=2) as ex:
        list(ex.map(tambah_audio_diam, tasks_audio))

    list_txt = os.path.abspath('concat_videos.txt')
    with open(list_txt, 'w', encoding='utf-8') as f:
        for i in sorted(klip_berhasil.keys()):
            p = klip_berhasil[i].replace('\\','/')
            f.write(f"file '{p}'\n")
    return list_txt


def render_video_final(file_list, audio, output, durasi):
    print(f"[5/6] Merender video final...")
    cmd = [
        'ffmpeg', '-y',
        '-f', 'concat', '-safe', '0', '-i', file_list,
        '-i', audio,
        '-map', '0:v', '-map', '1:a',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '22',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k',
        '-t', str(durasi), output
    ]
    with open(FFMPEG_LOG, 'a', encoding='utf-8') as log:
        log.write("\n=== RENDER FINAL ===\n")
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=log)
    if result.returncode != 0:
        print(f"  -> ERROR render! Cek {FFMPEG_LOG}")
        return False
    if not os.path.exists(output) or os.path.getsize(output) < 10000:
        print(f"  -> ERROR: File output tidak valid!")
        return False
    print(f"  -> ✅ Video final: {os.path.getsize(output)//1024//1024} MB")
    return True


# ════════════════════════════════════════════════════════════
# BAGIAN 8 — THUMBNAIL PROFESIONAL
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
            except: continue
    return ImageFont.load_default()


def _teks_outline(draw, posisi, teks, font, warna_teks, tebal=4):
    x, y = posisi
    for dx in range(-tebal, tebal+1):
        for dy in range(-tebal, tebal+1):
            if dx != 0 or dy != 0:
                draw.text((x+dx, y+dy), teks, font=font, fill=(0,0,0,255))
    draw.text((x, y), teks, font=font, fill=warna_teks)


def buat_thumbnail(info, judul, gambar_bank, output_path="thumbnail.jpg"):
    from PIL import Image, ImageDraw, ImageEnhance
    W, H = 1280, 720

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

    for y in range(H):
        alpha = int(120 + 100*(y/H))
        draw.line([(0,y),(W,y)], fill=(0,0,0,alpha))
    draw.rectangle([(0,H-230),(W,H)],   fill=(0,0,0,230))
    draw.rectangle([(0,0),(W,160)],     fill=(0,0,0,160))

    status = info['status']
    SKEMA  = {
        "Naik":   {"badge":(210,0,0),   "aksen":(255,60,60),
                   "teks_harga":(255,220,0),  "icon":"▲ NAIK"},
        "Turun":  {"badge":(0,150,60),  "aksen":(0,230,100),
                   "teks_harga":(100,255,150),"icon":"▼ TURUN"},
        "Stabil": {"badge":(160,120,0), "aksen":(255,195,0),
                   "teks_harga":(255,220,100),"icon":"⬛ STABIL"},
    }
    sk = SKEMA.get(status, SKEMA["Stabil"])

    bx1,by1,bx2,by2 = 30,22,390,118
    draw.rounded_rectangle([(bx1+4,by1+4),(bx2+4,by2+4)],radius=14,fill=(0,0,0,200))
    draw.rounded_rectangle([(bx1,by1),(bx2,by2)],radius=14,fill=(*sk["badge"],255))
    draw.rectangle([(bx1,by1),(bx1+12,by2)],fill=(*sk["aksen"],255))
    draw.rounded_rectangle([(bx1,by1),(bx2,by2)],radius=14,outline=(255,255,255,180),width=2)
    font_badge = _cari_font(56)
    bbox_b     = draw.textbbox((0,0),sk["icon"],font=font_badge)
    _teks_outline(draw,
        (bx1+22+((bx2-bx1-22-(bbox_b[2]-bbox_b[0]))//2),
         by1+((by2-by1-(bbox_b[3]-bbox_b[1]))//2)),
        sk["icon"], font_badge, (255,255,255,255), tebal=3)

    tgl_str  = datetime.now().strftime("%d %B %Y")
    font_tgl = _cari_font(34)
    bbox_tgl = draw.textbbox((0,0),tgl_str,font=font_tgl)
    _teks_outline(draw,
        (W-(bbox_tgl[2]-bbox_tgl[0])-30, 42),
        tgl_str, font_tgl, (220,220,220,255), tebal=3)

    harga_str  = f"Rp {info['harga_sekarang']:,}".replace(",",".")
    font_harga = _cari_font(130)
    bbox_h     = draw.textbbox((0,0),harga_str,font=font_harga)
    while (bbox_h[2]-bbox_h[0]) > W-60 and font_harga.size > 72:
        font_harga = _cari_font(font_harga.size-6)
        bbox_h     = draw.textbbox((0,0),harga_str,font=font_harga)
    tx_h = (W-(bbox_h[2]-bbox_h[0]))//2
    ty_h = 145
    _teks_outline(draw,(tx_h,ty_h),harga_str,font_harga,(*sk["teks_harga"],255),tebal=6)

    garis_y = ty_h+(bbox_h[3]-bbox_h[1])+12
    draw.rectangle([(tx_h,garis_y),(tx_h+(bbox_h[2]-bbox_h[0]),garis_y+6)],
                   fill=(*sk["aksen"],220))

    font_sub = _cari_font(40)
    teks_sub = "/gram  ·  Emas Antam Resmi"
    bbox_sub = draw.textbbox((0,0),teks_sub,font=font_sub)
    _teks_outline(draw,
        ((W-(bbox_sub[2]-bbox_sub[0]))//2, garis_y+16),
        teks_sub, font_sub, (210,210,210,255), tebal=3)

    historis = info.get("historis", {})
    teks_hl  = ""
    for label, data in historis.items():
        if data and abs(data["persen"]) >= 1.5:
            arah = "NAIK" if data["naik"] else "TURUN"
            nama = {"kemarin":"KEMARIN","7_hari":"SEMINGGU","1_bulan":"SEBULAN",
                    "3_bulan":"3 BULAN","6_bulan":"6 BULAN","1_tahun":"SETAHUN"
                    }.get(label,label.upper())
            teks_hl = f"{arah} {abs(data['persen']):.1f}% DARI {nama} LALU!"
            break
    if not teks_hl:
        sel = f"Rp {info['selisih']:,}".replace(",",".")
        if status == "Naik":   teks_hl = f"NAIK {sel} DARI KEMARIN!"
        elif status == "Turun":teks_hl = f"TURUN {sel} — SAATNYA BELI?"
        else:                  teks_hl = "UPDATE RESMI ANTAM — HARGA TERKINI!"

    font_hl = _cari_font(62)
    bbox_hl = draw.textbbox((0,0),teks_hl,font=font_hl)
    while (bbox_hl[2]-bbox_hl[0]) > W-40 and font_hl.size > 28:
        font_hl = _cari_font(font_hl.size-4)
        bbox_hl = draw.textbbox((0,0),teks_hl,font=font_hl)
    lw,lh = bbox_hl[2]-bbox_hl[0], bbox_hl[3]-bbox_hl[1]
    tx_hl = (W-lw)//2
    ty_hl = H-200
    px,py = 22,14
    draw.rectangle([(tx_hl-px,ty_hl-py),(tx_hl+lw+px,ty_hl+lh+py)],fill=(*sk["badge"],240))
    draw.rectangle([(tx_hl-px,ty_hl-py),(tx_hl+lw+px,ty_hl-py+5)],fill=(*sk["aksen"],255))
    draw.rectangle([(tx_hl-px,ty_hl+lh+py-5),(tx_hl+lw+px,ty_hl+lh+py)],fill=(*sk["aksen"],255))
    _teks_outline(draw,(tx_hl,ty_hl),teks_hl,font_hl,(255,255,255,255),tebal=3)

    font_ch = _cari_font(38)
    teks_ch = f"▶  {NAMA_CHANNEL}"
    bbox_ch = draw.textbbox((0,0),teks_ch,font=font_ch)
    tx_ch   = W-(bbox_ch[2]-bbox_ch[0])-30
    ty_ch   = H-(bbox_ch[3]-bbox_ch[1])-22
    _teks_outline(draw,(tx_ch,ty_ch),teks_ch,font_ch,(255,255,255,220),tebal=3)
    draw.rectangle([(tx_ch,ty_ch+(bbox_ch[3]-bbox_ch[1])+5),
                    (W-28,ty_ch+(bbox_ch[3]-bbox_ch[1])+10)],fill=(*sk["aksen"],220))

    final = Image.new("RGB",(W,H))
    final.paste(canvas.convert("RGB"),(0,0))
    final.save(output_path,"JPEG",quality=95,optimize=True)
    print(f"  -> ✅ Thumbnail: {output_path} ({os.path.getsize(output_path)//1024} KB)")
    return output_path


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
    if any(d for d in hist.values() if d):
        timestamps.append(("5:00","📈 Perbandingan Harga Historis (Minggu/Bulan Lalu)"))
    timestamps.append(("6:30","💡 Tips Investasi Emas yang Benar untuk Pemula"))
    timestamps.append(("7:30","✅ Kesimpulan & Rekomendasi"))
    ts_text = "\n".join(f"{ts}  {lb}" for ts,lb in timestamps)

    hist_lines = []
    nama_map   = {
        "kemarin":"Kemarin","7_hari":"Seminggu lalu","1_bulan":"Sebulan lalu",
        "3_bulan":"3 bulan lalu","6_bulan":"6 bulan lalu","1_tahun":"Setahun lalu",
    }
    for label, data in hist.items():
        if data:
            arah = "🔺 Naik" if data["naik"] else ("🔻 Turun" if not data["stabil"] else "⬛ Stabil")
            nama = nama_map.get(label, label)
            hist_lines.append(
                f"  {arah} {abs(data['persen']):.1f}% vs {nama} "
                f"(dari Rp {data['harga_ref']:,})".replace(",",".")
            )
    hist_text = "\n".join(hist_lines) if hist_lines else "  Data historis belum tersedia."

    return f"""📅 Update harga emas Antam hari ini, {tgl}.

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

        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                print(f"  -> Upload thumbnail...")
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
                ).execute()
                print(f"  -> ✅ Thumbnail terupload!")
            except Exception as e:
                print(f"  -> ⚠️  Thumbnail gagal: {e}")

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
            try: os.remove(f)
            except: pass
    for klip in glob.glob("temp_clips/*.mp4"):
        try: os.remove(klip)
        except: pass
    if os.path.exists("temp_clips"):
        try: os.rmdir("temp_clips")
        except: pass


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
    print(f"  AUTO VIDEO EMAS v6.0 - {NAMA_CHANNEL}")
    print(f"  {datetime.now().strftime('%d %B %Y, %H:%M WIB')}")
    print(f"{'='*60}\n")

    # 0. Manajemen storage
    kelola_video_lama()
    gambar_bank = kelola_bank_gambar()
    video_bank  = kelola_bank_video()

    if not gambar_bank and not video_bank:
        print("FATAL: Tidak ada gambar maupun video tersedia.")
        return

    # 1. Scrape harga
    info, data_harga = scrape_dan_kalkulasi_harga()
    if not info:
        print("Scraping gagal.")
        return

    # 2. Narasi & judul
    judul, narasi = buat_narasi_dan_judul(info, data_harga)
    print(f"\n{'='*60}")
    print(f"  🌟 JUDUL : {judul}")
    print(f"  💰 HARGA : Rp {info['harga_sekarang']:,} | {info['status']}".replace(",","."))
    print(f"{'='*60}\n")

    # 3. Generate suara
    try:
        durasi = buat_suara(narasi, audio_temp)
    except Exception as e:
        print(f"  -> ERROR audio: {e}")
        return

    # 4. Render media → klip
    file_list = proses_media(durasi, list(gambar_bank), list(video_bank))
    if not file_list:
        print("FATAL: Render klip gagal semua.")
        return

    # 5. Render video final
    sukses = render_video_final(file_list, audio_temp, video_hasil, durasi)

    if sukses and os.path.exists(video_hasil):
        ukuran_mb = os.path.getsize(video_hasil) // 1024 // 1024
        print(f"\n✅ VIDEO SELESAI: {video_hasil} ({ukuran_mb} MB)")

        if ukuran_mb < 5:
            print(f"⚠️  Video terlalu kecil! Cek {FFMPEG_LOG}")
            bersihkan_temp(file_list, audio_temp)
            return

        # 5b. Generate thumbnail
        print("\n[THUMBNAIL] Membuat thumbnail profesional...")
        try:
            thumbnail_path = buat_thumbnail(
                info        = info,
                judul       = judul,
                gambar_bank = list(gambar_bank),
                output_path = f"thumbnail_{tanggal_str}.jpg"
            )
        except Exception as e:
            print(f"  -> ⚠️  Thumbnail gagal: {e}")

        # 6. Upload YouTube
        deskripsi = buat_deskripsi_dengan_timestamp(info, judul)
        upload_ke_youtube(video_hasil, judul, deskripsi, YOUTUBE_TAGS,
                          thumbnail_path=thumbnail_path)
    else:
        print(f"\n❌ GAGAL membuat video. Cek {FFMPEG_LOG}")

    bersihkan_temp(file_list, audio_temp, thumbnail_path)
    ringkasan_storage()


if __name__ == "__main__":
    asyncio.run(main())
