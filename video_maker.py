# =============================================================
# AUTO VIDEO EMAS - FULL AUTOMATION v7.0
# MULTI CHANNEL ANTI DUPLIKAT
# Ganti CHANNEL_ID sesuai channel masing-masing: 1,2,3,4,5
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
# ⚙️  GANTI CHANNEL_ID SESUAI REPO: 1, 2, 3, 4, atau 5
# ============================================================
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "1"))

# Konfigurasi unik per channel
CHANNEL_CONFIG = {
    1: {
        "nama":        "Sobat Antam",
        "voice":       "id-ID-ArdiNeural",       # Laki-laki 1
        "rate":        "+5%",
        "narasi_gaya": "formal_analitis",
        "skema_warna": "merah_emas",
        "cron":        "0 2 * * *",              # 09:00 WIB
        "keywords_img":["gold bars","gold investment","gold bullion",
                        "precious metals","gold coins"],
        "keywords_vid":["gold bars","gold investment","financial market"],
    },
    2: {
        "nama":        "Update Emas Harian",
        "voice":       "id-ID-GadisNeural",      # Perempuan
        "rate":        "+3%",
        "narasi_gaya": "santai_edukatif",
        "skema_warna": "biru_perak",
        "cron":        "0 3 * * *",              # 10:00 WIB
        "keywords_img":["gold market","wealth management","investment gold",
                        "finance money","gold trading"],
        "keywords_vid":["gold market","wealth","finance"],
    },
    3: {
        "nama":        "Info Logam Mulia",
        "voice":       "id-ID-ArdiNeural",
        "rate":        "-3%",                    # Lebih lambat = terdengar beda
        "narasi_gaya": "berita_singkat",
        "skema_warna": "hijau_platinum",
        "cron":        "0 4 * * *",              # 11:00 WIB
        "keywords_img":["gold nuggets","bank vault","financial chart",
                        "gold jewelry","economy"],
        "keywords_vid":["gold nuggets","bank vault","economy"],
    },
    4: {
        "nama":        "Harga Emas Live",
        "voice":       "id-ID-GadisNeural",
        "rate":        "+8%",                    # Lebih cepat = beda ritme
        "narasi_gaya": "energik_motivatif",
        "skema_warna": "ungu_mewah",
        "cron":        "0 5 * * *",              # 12:00 WIB
        "keywords_img":["luxury gold","gold reserve","commodity gold",
                        "gold standard","platinum gold"],
        "keywords_vid":["luxury gold","commodity","stock market"],
    },
    5: {
        "nama":        "Cek Harga Emas",
        "voice":       "id-ID-ArdiNeural",
        "rate":        "+0%",
        "narasi_gaya": "percakapan_akrab",
        "skema_warna": "oranye_tembaga",
        "cron":        "0 6 * * *",              # 13:00 WIB
        "keywords_img":["gold coin collection","antique gold","gold ring",
                        "gold necklace","yellow gold"],
        "keywords_vid":["gold coin","antique gold","jewelry gold"],
    },
}

CFG = CHANNEL_CONFIG.get(CHANNEL_ID, CHANNEL_CONFIG[1])

# ============================================================
# PENGATURAN UTAMA
# ============================================================
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY", "")
PEXELS_API_KEY    = os.environ.get("PEXELS_API_KEY", "")
NAMA_CHANNEL      = CFG["nama"]
VOICE             = CFG["voice"]
VOICE_RATE        = CFG["rate"]
NARASI_GAYA       = CFG["narasi_gaya"]
KATA_KUNCI_GAMBAR = CFG["keywords_img"]
KATA_KUNCI_VIDEO  = CFG["keywords_vid"]

FFMPEG_LOG        = "ffmpeg_log.txt"
FILE_HISTORY      = "history_harga.json"
YOUTUBE_CATEGORY  = "25"
YOUTUBE_TAGS      = [
    "harga emas", "emas antam", "investasi emas", "logam mulia",
    "harga emas hari ini", "emas antam hari ini", "harga emas antam",
    "update emas", "emas batangan",
]

VIDEO_WIDTH  = 1920
VIDEO_HEIGHT = 1080
FPS          = 30

FOLDER_GAMBAR     = "gambar_bank"
FOLDER_VIDEO      = "video_bank"
JUMLAH_GAMBAR_MIN = 40
JUMLAH_GAMBAR_MAX = 150
JUMLAH_DL_GAMBAR  = 60
JUMLAH_VIDEO_MIN  = 8
JUMLAH_VIDEO_MAX  = 30
JUMLAH_DL_VIDEO   = 15
SIMPAN_VIDEO_MAKS = 3

# ============================================================
# SKEMA WARNA THUMBNAIL PER CHANNEL (warna-warni)
# ============================================================
SKEMA_THUMBNAIL = {
    # Channel 1 — Merah & Emas klasik
    "merah_emas": {
        "Naik":   {"badge":(200,0,0),     "aksen":(255,80,0),
                   "teks_harga":(255,220,0),   "icon":"▲ NAIK",
                   "bg_overlay":(20,0,0)},
        "Turun":  {"badge":(0,140,50),    "aksen":(50,255,120),
                   "teks_harga":(180,255,180), "icon":"▼ TURUN",
                   "bg_overlay":(0,20,0)},
        "Stabil": {"badge":(140,100,0),   "aksen":(255,190,0),
                   "teks_harga":(255,230,100), "icon":"⬛ STABIL",
                   "bg_overlay":(20,15,0)},
    },
    # Channel 2 — Biru & Perak futuristik
    "biru_perak": {
        "Naik":   {"badge":(0,60,180),    "aksen":(0,160,255),
                   "teks_harga":(150,220,255), "icon":"▲ NAIK",
                   "bg_overlay":(0,5,25)},
        "Turun":  {"badge":(0,120,160),   "aksen":(0,220,200),
                   "teks_harga":(180,255,250), "icon":"▼ TURUN",
                   "bg_overlay":(0,15,20)},
        "Stabil": {"badge":(80,80,160),   "aksen":(160,160,255),
                   "teks_harga":(200,200,255), "icon":"⬛ STABIL",
                   "bg_overlay":(5,5,20)},
    },
    # Channel 3 — Hijau & Platinum modern
    "hijau_platinum": {
        "Naik":   {"badge":(0,130,60),    "aksen":(0,230,100),
                   "teks_harga":(200,255,200), "icon":"▲ NAIK",
                   "bg_overlay":(0,20,5)},
        "Turun":  {"badge":(180,140,0),   "aksen":(255,210,0),
                   "teks_harga":(255,240,150), "icon":"▼ TURUN",
                   "bg_overlay":(20,15,0)},
        "Stabil": {"badge":(60,120,60),   "aksen":(150,255,150),
                   "teks_harga":(220,255,220), "icon":"⬛ STABIL",
                   "bg_overlay":(0,15,0)},
    },
    # Channel 4 — Ungu & Mewah elegan
    "ungu_mewah": {
        "Naik":   {"badge":(120,0,180),   "aksen":(220,0,255),
                   "teks_harga":(255,180,255), "icon":"▲ NAIK",
                   "bg_overlay":(15,0,25)},
        "Turun":  {"badge":(80,0,140),    "aksen":(180,100,255),
                   "teks_harga":(230,200,255), "icon":"▼ TURUN",
                   "bg_overlay":(10,0,20)},
        "Stabil": {"badge":(100,50,150),  "aksen":(200,150,255),
                   "teks_harga":(240,220,255), "icon":"⬛ STABIL",
                   "bg_overlay":(12,5,20)},
    },
    # Channel 5 — Oranye & Tembaga hangat
    "oranye_tembaga": {
        "Naik":   {"badge":(200,80,0),    "aksen":(255,140,0),
                   "teks_harga":(255,210,100), "icon":"▲ NAIK",
                   "bg_overlay":(25,10,0)},
        "Turun":  {"badge":(160,60,0),    "aksen":(255,100,0),
                   "teks_harga":(255,180,100), "icon":"▼ TURUN",
                   "bg_overlay":(20,8,0)},
        "Stabil": {"badge":(180,100,0),   "aksen":(255,160,50),
                   "teks_harga":(255,220,150), "icon":"⬛ STABIL",
                   "bg_overlay":(22,12,0)},
    },
}

SKEMA_AKTIF = SKEMA_THUMBNAIL.get(CFG["skema_warna"], SKEMA_THUMBNAIL["merah_emas"])


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
        print(f"[STORAGE] Download {kurang} gambar...")
        _download_pexels_gambar(kurang)
        ada = _list_gambar()
    if len(ada) > JUMLAH_GAMBAR_MAX:
        for f in ada[:len(ada)-JUMLAH_GAMBAR_MAX]:
            try: os.remove(f)
            except: pass
        ada = _list_gambar()
    return ada

def _download_pexels_gambar(jumlah_target):
    if not PEXELS_API_KEY:
        print("  -> Pexels key kosong.")
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
            print(f"  -> Gagal '{keyword}': {e}")
    print(f"  -> Total: {total_dl} gambar")
    return total_dl

def kelola_bank_video():
    os.makedirs(FOLDER_VIDEO, exist_ok=True)
    ada = _list_video_bank()
    print(f"[STORAGE] Bank video: {len(ada)} file")
    if len(ada) < JUMLAH_VIDEO_MIN:
        kurang = JUMLAH_DL_VIDEO - len(ada)
        print(f"[STORAGE] Download {kurang} video...")
        _download_pexels_video(kurang)
        ada = _list_video_bank()
    if len(ada) > JUMLAH_VIDEO_MAX:
        for f in ada[:len(ada)-JUMLAH_VIDEO_MAX]:
            try: os.remove(f)
            except: pass
        ada = _list_video_bank()
    return ada

def _download_pexels_video(jumlah_target):
    if not PEXELS_API_KEY:
        print("  -> Pexels key kosong.")
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
                files        = vid.get("video_files", [])
                file_terbaik = None
                for vf in sorted(files, key=lambda x: x.get("height",0), reverse=True):
                    if vf.get("height",0) >= 720 and vf.get("file_type") == "video/mp4":
                        file_terbaik = vf
                        break
                if not file_terbaik and files:
                    file_terbaik = files[0]
                if not file_terbaik: continue
                fn = f"{FOLDER_VIDEO}/pexels_{ts}_{keyword.replace(' ','_')}_{i+1}.mp4"
                if os.path.exists(fn): continue
                try:
                    data = requests.get(file_terbaik["link"], timeout=60).content
                    with open(fn, "wb") as f: f.write(data)
                    total_dl += 1
                    print(f"  -> ✅ Video '{keyword}' [{i+1}]")
                except Exception as e:
                    print(f"  -> Gagal video: {e}")
            if total_dl >= jumlah_target: break
        except Exception as e:
            print(f"  -> Gagal '{keyword}': {e}")
    print(f"  -> Total: {total_dl} video")
    return total_dl

def kelola_video_lama():
    videos = sorted(glob.glob("Video_Emas_*.mp4"))
    if len(videos) > SIMPAN_VIDEO_MAKS:
        for v in videos[:len(videos)-SIMPAN_VIDEO_MAKS]:
            try:
                os.remove(v)
                print(f"[STORAGE] Hapus: {v}")
            except: pass

def ringkasan_storage():
    g  = _list_gambar()
    v  = _list_video_bank()
    h  = glob.glob("Video_Emas_*.mp4")
    ug = sum(os.path.getsize(f) for f in g if os.path.exists(f))
    uv = sum(os.path.getsize(f) for f in v if os.path.exists(f))
    uh = sum(os.path.getsize(f) for f in h if os.path.exists(f))
    print(f"\n[STORAGE] Gambar:{len(g)} ({ug/1024/1024:.1f}MB) | "
          f"Video:{len(v)} ({uv/1024/1024:.1f}MB) | "
          f"Hasil:{len(h)} ({uh/1024/1024:.1f}MB)")


# ════════════════════════════════════════════════════════════
# BAGIAN 2 — HISTORY HARGA
# ════════════════════════════════════════════════════════════

def muat_history():
    if os.path.exists(FILE_HISTORY):
        try:
            with open(FILE_HISTORY, encoding="utf-8") as f:
                data = json.load(f)
            if "records" not in data and "harga_1_gram" in data:
                return {"records":[{"tanggal":data["tanggal"],"harga":data["harga_1_gram"]}]}
            return data
        except: pass
    return {"records":[]}

def simpan_history(harga):
    history  = muat_history()
    records  = history.get("records", [])
    hari_ini = datetime.now().strftime("%Y-%m-%d")
    records  = [r for r in records if r["tanggal"] != hari_ini]
    records.insert(0, {"tanggal":hari_ini, "harga":harga})
    records  = records[:365]
    with open(FILE_HISTORY, "w", encoding="utf-8") as f:
        json.dump({"records":records}, f, indent=2, ensure_ascii=False)
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
            p = round((s/rec["harga"])*100, 2)
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
# BAGIAN 3 — JUDUL CLICKBAIT (8 variasi × 5 gaya = 40 pool)
# ════════════════════════════════════════════════════════════

def buat_judul_clickbait_lokal(info, historis):
    h       = f"Rp {info['harga_sekarang']:,}".replace(",",".")
    status  = info['status']
    selisih = f"Rp {info['selisih']:,}".replace(",",".")
    tgl     = datetime.now().strftime("%d %b %Y")
    ch      = NAMA_CHANNEL

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
            pool = {
                "formal_analitis": [
                    f"Analisa: Emas Antam NAIK {pct:.1f}% dalam {pl} — Proyeksi ke Depan",
                    f"Sinyal Teknikal Bullish! Emas Antam +{pct:.1f}% Sejak {pl} — {h}/gram",
                    f"📊 NAIK {pct:.1f}% dalam {pl}! Kapan Emas Antam Puncak? Analisa {tgl}",
                    f"Data Menunjukkan Kenaikan {pct:.1f}%! Emas Antam {h}/gram — Layak Beli?",
                ],
                "santai_edukatif": [
                    f"Eh, Emas Naik {pct:.1f}% lho dalam {pl}! Masih Mau Beli? {h}/gram",
                    f"Kamu Sudah Tau? Emas Antam Udah Naik {pct:.1f}% Sejak {pl} Lalu!",
                    f"💡 Pelajaran Investasi: Emas Naik {pct:.1f}% dalam {pl} — Apa Artinya?",
                    f"Baru Tau Emas Naik {pct:.1f}%? Ini Penjelasan Lengkapnya! Antam {h}/gram",
                ],
                "berita_singkat": [
                    f"BREAKING: Emas Antam Naik {pct:.1f}% dari {pl} Lalu! Harga {h}/gram",
                    f"UPDATE {tgl}: Emas Antam +{pct:.1f}% sejak {pl} — Harga {h}/gram",
                    f"🔴 LIVE: Emas Antam {h}/gram — Naik {pct:.1f}% dalam {pl}",
                    f"TERBARU: Kenaikan Emas {pct:.1f}% dari {pl} — Cek Harga Lengkap!",
                ],
                "energik_motivatif": [
                    f"🚀 EMAS MELEJIT {pct:.1f}%! {pl} Lalu Beli = UNTUNG BESAR Sekarang!",
                    f"NAIK {pct:.1f}% dalam {pl}! Ini BUKTI Emas Investasi TERBAIK! {h}/gram",
                    f"💥 {pct:.1f}% PROFIT dalam {pl}! Masih Ragu Beli Emas? Lihat ini!",
                    f"EMAS ANTAM TERBANG {pct:.1f}%! Jangan Sampai Menyesal! Harga {h}/gram",
                ],
                "percakapan_akrab": [
                    f"Bro, Emas Udah Naik {pct:.1f}% nih dari {pl} Lalu — Gimana Menurutmu?",
                    f"Guys! Emas Antam Naik {pct:.1f}% dalam {pl}! Masih Worth It Beli?",
                    f"Jujur nih, Emas Antam Udah {pct:.1f}% Naik dari {pl} — {h}/gram",
                    f"Serius? Emas Naik {pct:.1f}% dalam {pl}! Yuk Bahas Bareng — {h}/gram",
                ],
            }
        else:
            pool = {
                "formal_analitis": [
                    f"Analisa Koreksi: Emas Antam Turun {pct:.1f}% dalam {pl} — Beli Sekarang?",
                    f"📊 Koreksi {pct:.1f}% dalam {pl}! Support Level Emas Antam {h}/gram",
                    f"Data Koreksi Emas {pct:.1f}% Sejak {pl} — Momentum Akumulasi Terbaik?",
                    f"Teknikal Oversold! Emas Antam -{pct:.1f}% dari {pl} — Reversal Kapan?",
                ],
                "santai_edukatif": [
                    f"Emas Turun {pct:.1f}% nih dari {pl} Lalu — Ini Waktu Beli yang Tepat!",
                    f"💡 Koreksi {pct:.1f}% = Kesempatan! Emas Antam {h}/gram Sekarang",
                    f"Mau Beli Emas Murah? Turun {pct:.1f}% dari {pl} Lalu — Ini Saatnya!",
                    f"Tenang! Turun {pct:.1f}% itu Normal — Emas Antam {h}/gram, Yuk Nabung",
                ],
                "berita_singkat": [
                    f"UPDATE: Emas Antam Terkoreksi {pct:.1f}% dari {pl} — Harga {h}/gram",
                    f"TERBARU {tgl}: Koreksi Emas {pct:.1f}% Sejak {pl} — Cek Sekarang!",
                    f"🟢 Emas Antam Koreksi {pct:.1f}% dari {pl} — Harga {h}/gram Hari Ini",
                    f"INFO: Emas -{pct:.1f}% dalam {pl} — {h}/gram — Beli atau Tunggu?",
                ],
                "energik_motivatif": [
                    f"💰 DISKON {pct:.1f}%! EMAS ANTAM {h}/gram — BORONG SEKARANG!",
                    f"KESEMPATAN LANGKA! Emas Turun {pct:.1f}% dari {pl} — Jangan Lewatkan!",
                    f"🎯 HARGA TERBAIK! Emas Koreksi {pct:.1f}% dalam {pl} — ACTION NOW!",
                    f"Turun {pct:.1f}% = SALE EMAS! Antam {h}/gram — Kapan Lagi Murah?!",
                ],
                "percakapan_akrab": [
                    f"Wah Emas Turun {pct:.1f}% nih dari {pl} — Kamu Udah Borong Belum?",
                    f"Guys, Ini Waktu Beli Emas! Turun {pct:.1f}% dari {pl} — {h}/gram",
                    f"Serius nih Emas Turun {pct:.1f}%? Yuk Analisa Bareng — {h}/gram",
                    f"Bro, Emas Antam {h}/gram — Turun {pct:.1f}% dari {pl}, Worth It Beli?",
                ],
            }
        pool_aktif = pool.get(NARASI_GAYA, pool["formal_analitis"])
        return random.choice(pool_aktif)[:100]

    # Pool tanpa historis signifikan
    if status == "Naik":
        pool = {
            "formal_analitis": [
                f"Emas Antam {h}/gram Naik {selisih} — Analisa & Proyeksi {tgl}",
                f"Kenaikan {selisih} pada Emas Antam {h}/gram — Rekomendasi Analis",
                f"📈 Emas Antam Terkerek {selisih} Jadi {h}/gram — Sinyal Beli?",
                f"Update Harga: Emas Antam Naik {selisih} ke {h}/gram — Analisa {tgl}",
                f"Momentum Naik! Emas Antam +{selisih} Jadi {h}/gram Hari Ini",
                f"Emas Antam {h}/gram: Naik {selisih} — Fundamental Masih Kuat?",
                f"🔴 Emas Antam Menguat {selisih} ke {h}/gram — Update Resmi {tgl}",
                f"Harga Emas Antam Naik {selisih} — Apakah Tren Berlanjut? {h}/gram",
            ],
            "santai_edukatif": [
                f"Emas Naik Lagi {selisih}! Jadi {h}/gram — Masih Oke Buat Invest?",
                f"Harga Emas Antam Naik {selisih} Hari ini — Yuk Pahami Kenapa!",
                f"💡 Kenapa Emas Naik {selisih}? Ini Penjelasan Mudahnya! {h}/gram",
                f"Emas Antam {h}/gram Naik {selisih} — 5 Hal yang Perlu Kamu Tau",
                f"Naik {selisih}! Emas Antam Jadi {h}/gram — Tips Buat Investor Pemula",
                f"Update Emas: Naik {selisih} ke {h}/gram — Santai, Ini Normal Kok!",
                f"Eh Emas Naik {selisih} lho! Jadi {h}/gram — Mau Tau Alasannya?",
                f"Emas Antam {h}/gram — Naik {selisih}, Waktu Tepat Nabung Emas?",
            ],
            "berita_singkat": [
                f"BREAKING: Emas Antam Naik {selisih} Jadi {h}/gram — {tgl}",
                f"UPDATE EMAS {tgl}: Naik {selisih} ke {h}/gram — Cek Sekarang!",
                f"🔴 NAIK {selisih}! Emas Antam {h}/gram — Update Resmi Hari Ini",
                f"TERBARU: Harga Emas Antam {h}/gram Naik {selisih} dari Kemarin",
                f"INFO {tgl}: Emas Antam Naik {selisih} — Harga Lengkap Ada di Sini",
                f"LIVE UPDATE: Emas Antam {h}/gram, Naik {selisih} Hari Ini!",
                f"WASPADA! Emas Antam Naik {selisih} ke {h}/gram — {tgl}",
                f"TERKINI: Emas Antam {h}/gram Naik {selisih} — Jual atau Tahan?",
            ],
            "energik_motivatif": [
                f"🚨 EMAS NAIK {selisih}!! Antam {h}/gram — Masih Mau Diam Aja?!",
                f"NAIK {selisih}! Emas Antam {h}/gram — INI TANDA NAIK TERUS?!",
                f"💥 EMAS ANTAM MELEJIT {selisih}! {h}/gram — Kapan Lagi Beli?!",
                f"ALERT! Emas Naik {selisih}! {h}/gram — Jangan Sampai Nyesel!",
                f"🔥 EMAS NAIK {selisih} HARI INI! {h}/gram — ACTION SEKARANG!",
                f"WOW! Emas Antam Naik {selisih} ke {h}/gram — Ini Buktinya!",
                f"NAIK TERUS! Emas Antam +{selisih} Jadi {h}/gram — Beli Gak?!",
                f"EMAS ANTAM {h}/gram NAIK {selisih}!! Mau Untung? Tonton Ini!",
            ],
            "percakapan_akrab": [
                f"Guys Emas Naik Lagi {selisih}! Antam {h}/gram — Kalian Gimana?",
                f"Bro Emas Naik {selisih} nih! Jadi {h}/gram — Worth It Beli?",
                f"Serius Emas Naik {selisih}? Antam {h}/gram — Yuk Bahas Bareng!",
                f"Wah Emas Antam Naik {selisih}! {h}/gram — Mau Beli atau Tunggu?",
                f"Eh Tau Gak? Emas Naik {selisih} Hari Ini! Antam {h}/gram nih",
                f"Nabung Emas Gak? Antam Naik {selisih} jadi {h}/gram hari ini!",
                f"Emas Antam {h}/gram — Naik {selisih}, Gimana Strategi Kamu?",
                f"Sip! Emas Naik {selisih} ke {h}/gram — Share ke Temenmu Juga!",
            ],
        }
    elif status == "Turun":
        pool = {
            "formal_analitis": [
                f"Koreksi Emas Antam -{selisih} ke {h}/gram — Analisa Support Level",
                f"Teknikal: Emas Antam Turun {selisih} ke {h}/gram — Beli atau Wait?",
                f"📉 Emas Antam Terkoreksi {selisih} ke {h}/gram — Rekomendasi {tgl}",
                f"Data Koreksi: Emas Antam {h}/gram Turun {selisih} — Fundamentals?",
                f"Emas Antam Melemah {selisih} ke {h}/gram — Analisa Teknikal {tgl}",
                f"Update: Emas Antam -{selisih} Jadi {h}/gram — Momentum Akumulasi?",
                f"🟢 Emas Antam Koreksi {selisih} — {h}/gram Titik Masuk Terbaik?",
                f"Harga Emas Antam {h}/gram Turun {selisih} — Oversold atau Lanjut?",
            ],
            "santai_edukatif": [
                f"Emas Turun {selisih} jadi {h}/gram — Tenang, Ini Waktu Nabung!",
                f"💡 Emas Antam Turun {selisih}! {h}/gram — Yuk Manfaatin Momen Ini",
                f"Emas Antam {h}/gram Turun {selisih} — 3 Alasan Kenapa Ini Bagus",
                f"Turun {selisih}? Emas Antam {h}/gram Tetap Investasi Terbaik!",
                f"Eh Emas Turun {selisih} lho! {h}/gram — Ini Artinya Apa buat Kamu?",
                f"Emas Antam Turun {selisih} ke {h}/gram — Tips Beli di Harga Murah",
                f"Santai! Turun {selisih} Itu Normal — Emas Antam {h}/gram Hari Ini",
                f"Mau Beli Emas Murah? {h}/gram Turun {selisih} — Yuk Simak Dulu!",
            ],
            "berita_singkat": [
                f"UPDATE: Emas Antam Turun {selisih} ke {h}/gram — {tgl}",
                f"TERBARU: Emas Antam {h}/gram Koreksi {selisih} Hari Ini",
                f"🟢 TURUN {selisih}! Emas Antam {h}/gram — Update Resmi {tgl}",
                f"INFO {tgl}: Emas Antam Melemah {selisih} ke {h}/gram",
                f"LIVE: Harga Emas Antam {h}/gram Koreksi {selisih} — Cek di Sini",
                f"TERKINI: Emas Antam -{selisih} Jadi {h}/gram — Saatnya Beli?",
                f"UPDATE EMAS {tgl}: Turun {selisih} ke {h}/gram — Data Lengkap",
                f"INFO HARGA: Emas Antam {h}/gram Turun {selisih} dari Kemarin",
            ],
            "energik_motivatif": [
                f"🎯 EMAS TURUN {selisih}!! {h}/gram — INI WAKTU BELI TERBAIK!",
                f"DISKON {selisih}! Emas Antam {h}/gram — BORONG SEBELUM NAIK!",
                f"💰 HARGA MURAH! Emas Antam Turun {selisih} ke {h}/gram — BURUAN!",
                f"KESEMPATAN EMAS! Turun {selisih} ke {h}/gram — Jangan Ragu!",
                f"🔥 SALE EMAS! Antam -{selisih} = {h}/gram — Kapan Lagi Sebegini?",
                f"EMAS MURAH {selisih}! {h}/gram — BELI SEKARANG SEBELUM TERLAMBAT!",
                f"WOW TURUN {selisih}!! Emas Antam {h}/gram — Ini Sinyal Kuat Beli!",
                f"ALERT HARGA MURAH! Emas -{selisih} ke {h}/gram — ACTION NOW!",
            ],
            "percakapan_akrab": [
                f"Bro Emas Turun {selisih}! {h}/gram — Udah Beli Belum Nih?",
                f"Guys! Emas Antam {h}/gram Turun {selisih} — Mau Borong Gak?",
                f"Eh Emas Murah {selisih}! Antam {h}/gram — Yuk Nabung Bareng!",
                f"Serius Emas Turun {selisih}? {h}/gram — Kalian Beli Gak Nih?",
                f"Wah Emas Antam {h}/gram Turun {selisih} — Worth It Banget Beli!",
                f"Emas Turun {selisih} nih! Antam {h}/gram — Gimana Pendapatmu?",
                f"Nabung Emas Yuk! Antam Turun {selisih} jadi {h}/gram Hari Ini",
                f"Beli Emas Sekarang! Turun {selisih} ke {h}/gram — Mumpung Murah!",
            ],
        }
    else:  # Stabil
        pool = {
            "formal_analitis": [
                f"Analisa: Emas Antam Konsolidasi di {h}/gram — Arah Selanjutnya?",
                f"Sideways! Emas Antam {h}/gram — Sinyal Teknikal & Proyeksi {tgl}",
                f"📊 Emas Antam Stagnan {h}/gram — Kapan Break Out? Analisa {tgl}",
                f"Consolidation Phase: Emas Antam {h}/gram — Beli atau Tunggu?",
                f"Emas Antam {h}/gram Flat — Analisa Fundamental & Teknikal {tgl}",
                f"Update Harga Emas Antam {h}/gram — Stabil Menuju Tren Mana?",
                f"Harga Emas Antam {h}/gram Konsolidasi — Rekomendasi Investor",
                f"⬛ Emas Antam {h}/gram — Koreksi Dulu atau Mau Naik? Analisa",
            ],
            "santai_edukatif": [
                f"Emas Antam {h}/gram Hari Ini — Stabil, tapi Tunggu Dulu Nih!",
                f"💡 Emas Antam Stagnan di {h}/gram — Apa yang Harus Dilakukan?",
                f"Harga Emas {h}/gram Gak Bergerak — Ini Penjelasan Lengkapnya!",
                f"Emas Antam {h}/gram Masih Flat — 4 Strategi Investasi Tepat",
                f"Tenang Emas Antam {h}/gram Stabil — Yuk Pelajari Cara Invest!",
                f"Emas Antam Stagnan {h}/gram — Waktu Terbaik Belajar Investasi",
                f"Eh Emas {h}/gram Stabil Nih! Buat Kamu yang Mau Mulai Invest",
                f"Emas Antam {h}/gram Flat — 3 Hal yang Perlu Kamu Persiapkan",
            ],
            "berita_singkat": [
                f"UPDATE {tgl}: Emas Antam Stabil di {h}/gram — Cek Harga Lengkap",
                f"TERBARU: Emas Antam {h}/gram — Stagnan, Ini Data Resminya!",
                f"⬛ STABIL! Emas Antam {h}/gram — Update Resmi {tgl}",
                f"INFO HARGA {tgl}: Emas Antam {h}/gram Tidak Berubah Hari Ini",
                f"LIVE: Emas Antam {h}/gram Konsolidasi — Update Terkini {tgl}",
                f"TERKINI: Harga Emas Antam {h}/gram — Flat, Ini Penyebabnya!",
                f"INFO: Emas Antam {h}/gram Stabil — Daftar Harga Lengkap {tgl}",
                f"UPDATE EMAS {tgl}: Antam {h}/gram Stagnan — Naik atau Turun?",
            ],
            "energik_motivatif": [
                f"😲 EMAS ANTAM DIAM di {h}/gram — INI PERTANDA MENARIK!",
                f"🤔 Kenapa Emas {h}/gram Gak Bergerak?! Ini Jawabannya!!",
                f"⚡ STAGNAN = KESEMPATAN! Emas Antam {h}/gram — Beli Sekarang!",
                f"WASPADA! Emas Antam {h}/gram Tenang — Badai Akan Datang?!",
                f"🎯 EMAS ANTAM {h}/gram STAGNAN — STRATEGI PROFIT TERBAIK!",
                f"SINYAL KUAT! Emas {h}/gram Konsolidasi — Mau NAIK BESAR?!",
                f"EMAS ANTAM {h}/gram FLAT — TAPI INI JUSTRU WAKTU BELI!",
                f"⚠️ ALERT! Emas {h}/gram Tidak Bergerak — Ini Berbahaya?!",
            ],
            "percakapan_akrab": [
                f"Guys Emas Antam {h}/gram Hari Ini — Stabil, Gimana Menurutmu?",
                f"Bro, Emas Antam {h}/gram Gak Kemana-mana — Beli atau Tunggu?",
                f"Eh Emas Antam Masih {h}/gram Nih — Kalian Gimana Strateginya?",
                f"Emas Antam {h}/gram Stagnan — Yuk Diskusi Bareng di Kolom Komen!",
                f"Serius Emas {h}/gram Flat? — Curhat Dong, Kalian Beli Gak?",
                f"Wah Emas Antam {h}/gram Masih Sama — Enak nih Buat Nabung!",
                f"Emas {h}/gram Tenang Banget Hari Ini — Kalian Bakal Beli Gak?",
                f"Emas Antam {h}/gram — Stagnan Bro, tapi Worth It Tetap Nabung!",
            ],
        }

    pool_aktif = pool.get(NARASI_GAYA, list(pool.values())[0])
    return random.choice(pool_aktif)[:100]


def _validasi_judul(judul_raw, info, historis):
    KATA_BOCOR = [
        "tentu","berikut","ini dia","mari kita","dengan senang",
        "baik,","oke,","siap,","kamu adalah","scriptwriter",
        "channel anda","naskah video","konten youtube",
    ]
    if any(k in judul_raw.lower() for k in KATA_BOCOR) or len(judul_raw.strip()) < 10:
        fix = buat_judul_clickbait_lokal(info, historis)
        print(f"  -> [FIX JUDUL]: {fix}")
        return fix
    return judul_raw.strip()[:100]


# ════════════════════════════════════════════════════════════
# BAGIAN 4 — SCRAPING HARGA EMAS
# ════════════════════════════════════════════════════════════

def scrape_dan_kalkulasi_harga():
    print("[1/6] Mengambil data harga emas Antam...")
    url     = "https://www.logammulia.com/id/harga-emas-hari-ini"
    headers = {'User-Agent':'Mozilla/5.0'}
    try:
        response   = requests.get(url, headers=headers, timeout=15)
        soup       = BeautifulSoup(response.text, 'html.parser')
        data_kasar = soup.get_text(separator=" | ", strip=True)
        tanggal    = datetime.now().strftime("%d %B %Y")

        harga_1_gram = 0
        for row in soup.find_all('tr'):
            cells = row.find_all(['td','th'])
            if len(cells) >= 2:
                tk = cells[0].text.strip().lower()
                if tk in ('1 gr','1 gram'):
                    a = re.sub(r'[^\d]','',cells[1].text)
                    if a:
                        harga_1_gram = int(a)
                        break

        if harga_1_gram == 0:
            print("  -> ERROR: Gagal parse harga.")
            return None, None

        history_data = muat_history()
        records      = history_data.get("records",[])
        historis     = analisa_historis(harga_1_gram, records)

        kmrn = historis.get("kemarin")
        if kmrn:
            s       = kmrn["selisih"]
            status  = "Naik" if s > 0 else ("Turun" if s < 0 else "Stabil")
            selisih = abs(s)
        else:
            status, selisih = "Stabil", 0

        records_baru = simpan_history(harga_1_gram)
        ringkasan    = [
            f"{lb}:{'↑' if d['naik'] else ('↓' if not d['stabil'] else '→')}"
            f"{abs(d['persen']):.1f}%"
            for lb,d in historis.items() if d
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
            for lb,d in historis.items() if d
        ])
        teks_data = f"Tanggal:{tanggal}. Historis:{konteks}. Data:{data_kasar[:2500]}..."
        return info, teks_data

    except Exception as e:
        print(f"  -> Gagal scraping: {e}")
        return None, None


# ════════════════════════════════════════════════════════════
# BAGIAN 5 — NARASI FALLBACK (5 GAYA BERBEDA)
# ════════════════════════════════════════════════════════════

def _buat_narasi_fallback_lokal(info, harga_skrg, status_harga, selisih_harga):
    tanggal = datetime.now().strftime("%d %B %Y")
    hari    = {"Monday":"Senin","Tuesday":"Selasa","Wednesday":"Rabu",
               "Thursday":"Kamis","Friday":"Jumat",
               "Saturday":"Sabtu","Sunday":"Minggu"
               }.get(datetime.now().strftime("%A"),"")
    h       = info['harga_sekarang']
    rp      = lambda x: f"Rp {x:,}".replace(",",".")
    tabel   = {
        "setengah gram":h//2, "satu gram":h, "dua gram":h*2, "tiga gram":h*3,
        "lima gram":h*5, "sepuluh gram":h*10, "dua puluh lima gram":h*25,
        "lima puluh gram":h*50, "seratus gram":h*100,
        "dua ratus lima puluh gram":h*250, "lima ratus gram":h*500, "seribu gram":h*1000,
    }
    daftar = " ".join(f"Untuk {s}, harganya {rp(v)}." for s,v in tabel.items())
    kalimat_status = {
        "Naik":  f"mengalami kenaikan sebesar {selisih_harga} Rupiah dari hari kemarin",
        "Turun": f"mengalami penurunan sebesar {selisih_harga} Rupiah dari hari kemarin",
        "Stabil":"terpantau stabil tidak berubah dari hari sebelumnya",
    }.get(status_harga,"terpantau stabil")

    historis         = info.get("historis",{})
    kalimat_historis = ""
    for label, data in historis.items():
        if data and abs(data["persen"]) >= 1.0:
            arah = "naik" if data["naik"] else "turun"
            nama = {"kemarin":"kemarin","7_hari":"seminggu yang lalu",
                    "1_bulan":"sebulan yang lalu","3_bulan":"tiga bulan yang lalu",
                    "6_bulan":"enam bulan yang lalu","1_tahun":"setahun yang lalu"
                    }.get(label,label)
            kalimat_historis = (
                f" Apabila dibandingkan dengan {nama}, harga emas telah {arah} "
                f"sebesar {abs(data['persen']):.1f} persen dari {rp(data['harga_ref'])} "
                f"menjadi {rp(h)}."
            )
            break

    # 5 template narasi berbeda per gaya
    templates = {
        "formal_analitis": f"""Halo sobat {NAMA_CHANNEL}, selamat datang kembali di channel kami yang menyajikan analisa dan informasi investasi emas terkini. Pada hari {hari} tanggal {tanggal} ini, kami hadir dengan update komprehensif mengenai pergerakan harga emas Antam Logam Mulia.

Berdasarkan data resmi yang kami himpun dari situs Logam Mulia, harga emas Antam untuk ukuran satu gram pada hari ini tercatat di angka {rp(h)}. Harga ini {kalimat_status}.{kalimat_historis} Data ini penting sebagai acuan bagi Anda yang sedang mempertimbangkan keputusan investasi emas.

Berikut kami sajikan daftar harga lengkap emas Antam untuk seluruh ukuran yang tersedia secara resmi. {daftar} Daftar harga di atas merupakan harga jual resmi Antam yang dapat berubah sewaktu-waktu mengikuti dinamika pasar global.

Dari perspektif analisa fundamental, beberapa faktor makroekonomi saat ini berpengaruh signifikan terhadap pergerakan harga emas. Pertama, kebijakan moneter Federal Reserve Amerika Serikat tetap menjadi variabel paling dominan yang menentukan arah harga emas global. Ekspektasi pasar terhadap arah suku bunga Fed Funds Rate menjadi katalis utama pergerakan harga. Kedua, indeks dolar Amerika Serikat atau yang dikenal dengan DXY memiliki korelasi negatif dengan harga emas, dimana penguatan dolar umumnya menekan harga emas dan sebaliknya. Ketiga, situasi geopolitik global termasuk ketegangan di berbagai kawasan strategis dunia terus mendorong permintaan emas sebagai instrumen safe haven yang telah teruji ketangguhannya selama ribuan tahun. Keempat, data inflasi global yang masih di atas target bank sentral di berbagai negara turut memberikan dukungan positif bagi harga emas sebagai instrumen lindung nilai.

Dari sisi strategi investasi, kami merekomendasikan pendekatan systematic investment plan atau pembelian rutin berkala sebagai metode yang paling efektif untuk membangun portofolio emas jangka panjang. Diversifikasi alokasi antara emas fisik batangan dan instrumen emas digital dapat menjadi pilihan yang bijaksana. Pastikan Anda membeli melalui gerai resmi Antam atau platform terpercaya untuk menghindari risiko pemalsuan. Simpan emas fisik Anda dengan aman menggunakan layanan Safe Deposit Box bank atau titipan resmi Antam.

Demikian analisa dan update harga emas Antam hari ini dari {NAMA_CHANNEL}. Jika informasi ini bermanfaat, silakan berikan like dan subscribe untuk mendukung channel kami. Aktifkan notifikasi agar Anda tidak ketinggalan update harga dan analisa emas terbaru setiap hari. Terima kasih dan salam investasi cerdas!""",

        "santai_edukatif": f"""Halo sobat {NAMA_CHANNEL}! Selamat datang lagi di channel kita yang selalu hadir buat kasih update harga emas Antam paling fresh setiap harinya. Hari ini hari {hari} tanggal {tanggal}, dan seperti biasa kita bakal bahas bareng semua info penting seputar emas Antam.

Nah langsung aja ya, harga emas Antam resmi hari ini untuk ukuran satu gram ada di angka {rp(h)}. Harga ini {kalimat_status}.{kalimat_historis} Info ini diambil langsung dari website resmi Logam Mulia, jadi bisa dipercaya dan dijadikan patokan.

Oke sekarang kita lihat daftar harga lengkapnya buat semua ukuran yang tersedia. {daftar} Nah itulah harga-harga resminya. Perlu diingat ya, harga ini bisa berubah setiap saat mengikuti kondisi pasar, jadi selalu cek sebelum beli.

Sekarang yuk kita pahami bersama kenapa harga emas bisa naik turun. Pertama, emas itu harganya sangat dipengaruhi oleh kebijakan bank sentral Amerika, terutama soal suku bunga. Kalau suku bunga naik, biasanya emas agak tertekan karena orang lebih pilih aset berbunga. Sebaliknya kalau suku bunga turun atau ada ekspektasi pemangkasan, emas biasanya langsung menguat. Kedua, kondisi global seperti perang, ketegangan antar negara, atau krisis ekonomi selalu bikin orang lari ke emas sebagai tempat berlindung yang paling aman. Ketiga, nilai tukar Rupiah terhadap Dolar sangat menentukan harga emas dalam Rupiah. Kalau Rupiah melemah, harga emas dalam Rupiah otomatis naik meskipun harga globalnya tidak berubah.

Buat teman-teman yang mau mulai investasi emas, ada beberapa tips simpel yang bisa langsung dipraktekkan. Satu, mulai dari yang kecil dulu, tidak harus langsung beli ukuran besar. Dua, beli secara rutin setiap bulan berapapun jumlahnya, yang penting konsisten. Tiga, jangan panik kalau harga turun, justru itu saat yang bagus untuk menambah koleksi. Empat, simpan emas dengan aman dan pastikan beli di tempat yang sudah terpercaya.

Oke itu tadi update lengkap dari {NAMA_CHANNEL} hari ini! Kalau ada pertanyaan, langsung tulis di kolom komentar ya, pasti kita balas. Jangan lupa subscribe dan nyalakan lonceng notifikasinya biar gak ketinggalan update setiap hari. Sampai jumpa di video berikutnya, salam investasi!""",

        "berita_singkat": f"""Halo sobat {NAMA_CHANNEL}, berikut update harga emas Antam Logam Mulia hari {hari} tanggal {tanggal}.

Harga emas Antam resmi hari ini untuk ukuran satu gram adalah {rp(h)}. Harga ini {kalimat_status}.{kalimat_historis}

Daftar harga lengkap emas Antam semua ukuran hari ini sebagai berikut. {daftar}

Kondisi pasar emas global hari ini dipengaruhi oleh beberapa faktor utama. Pertama, arah kebijakan suku bunga Federal Reserve Amerika Serikat yang masih menjadi perhatian pelaku pasar global. Kedua, pergerakan indeks dolar AS yang berkorelasi negatif dengan harga emas dunia. Ketiga, sentimen risiko global terkait situasi geopolitik di berbagai kawasan yang mendorong permintaan safe haven. Data inflasi dari negara-negara ekonomi utama juga menjadi pertimbangan investor dalam menentukan porsi alokasi emas di portofolio investasi mereka.

Tips investasi emas hari ini: beli rutin setiap bulan, manfaatkan harga turun sebagai momentum akumulasi, dan selalu beli melalui gerai resmi Antam. Emas batangan lebih efisien dibanding perhiasan karena tidak ada ongkos pembuatan yang mahal.

Itulah update harga emas Antam hari ini dari {NAMA_CHANNEL}. Subscribe dan aktifkan notifikasi untuk update harga emas setiap hari. Terima kasih sudah menonton!""",

        "energik_motivatif": f"""Halo halo halo sobat {NAMA_CHANNEL}!! Selamat datang kembali di channel paling update soal harga emas Antam di seluruh Indonesia!! Hari ini hari {hari} tanggal {tanggal}, dan kita punya berita penting banget buat kamu semua!!

Langsung gas ya!! Harga emas Antam resmi hari ini untuk ukuran satu gram adalah {rp(h)}!! Harga ini {kalimat_status}!!{kalimat_historis} Ini bukan informasi sembarangan, ini data RESMI langsung dari Logam Mulia!!

Sekarang simak baik-baik harga lengkap semua ukuran emas Antam hari ini!! {daftar} Catat baik-baik angka-angka ini dan jadikan patokan sebelum kamu memutuskan untuk beli!!

Guys, ada beberapa hal penting banget yang harus kamu ketahui soal kondisi pasar emas saat ini!! Pertama, Federal Reserve Amerika Serikat sedang dalam sorotan tajam para investor global!! Setiap keputusan soal suku bunga bisa langsung mempengaruhi harga emas secara signifikan!! Kedua, ketidakpastian geopolitik global masih tinggi dan ini justru MENGUNTUNGKAN kamu yang sudah pegang emas!! Emas adalah satu-satunya aset yang terbukti bertahan di kondisi krisis apapun!! Ketiga, pelemahan mata uang di banyak negara termasuk kondisi Rupiah kita turut mendorong kenaikan harga emas dalam jangka panjang!!

PENTING BANGET!! Buat kamu yang belum punya emas, ini pesan keras dari kami!! Jangan tunda lagi!! Mulai dari satu gram pun tidak masalah!! Yang penting MULAI SEKARANG!! Beli rutin setiap bulan, tidak perlu banyak yang penting KONSISTEN!! Emas adalah investasi yang sudah teruji ribuan tahun dan tidak akan pernah bernilai nol!!

Itu tadi informasi super penting dari {NAMA_CHANNEL}!! Kalau video ini bermanfaat, LIKE sekarang, SUBSCRIBE sekarang, dan SHARE ke semua orang yang kamu sayangi!! Aktifkan notifikasi biar kamu selalu yang pertama dapat update!! Sampai jumpa dan SALAM KAYA RAYA!!""",

        "percakapan_akrab": f"""Hei hei hei, apa kabar semua? Selamat datang kembali di {NAMA_CHANNEL}! Udah lama ya kita gak ketemu, eh tapi kita ketemu tiap hari ding di sini! Hari ini hari {hari} tanggal {tanggal}, yuk langsung kita bahas bareng harga emas Antam hari ini!

Jadi gini guys, harga emas Antam buat ukuran satu gram hari ini ada di angka {rp(h)}. Nah harga ini {kalimat_status}.{kalimat_historis} Infonya dari website resmi Logam Mulia ya, jadi bisa dipercaya kok!

Oke buat yang mau tau harga lengkap semua ukuran, ini dia guys! {daftar} Gimana, udah catat belum? Harga bisa berubah lho, jadi pastiin selalu cek sebelum pergi ke gerai!

Nah aku mau kasih tau juga nih kenapa emas itu selalu menarik buat dibahas. Pertama, emas itu beneran gak ada matinya sebagai investasi. Selama ribuan tahun manusia udah pegang emas dan sampai sekarang masih tetap bernilai. Kedua, kondisi global yang lagi gak pasti seperti sekarang ini justru bikin emas makin bersinar, karena semua orang lari ke emas kalau situasi gak aman. Ketiga, emas itu gampang dicairin kalau butuh dana darurat, beda sama properti yang harus nunggu pembeli. Keempat, mulai belinya bisa dari ukuran kecil, jadi beneran bisa dijangkau semua kalangan.

Buat kalian yang udah lama invest emas, good job ya udah jalan di track yang bener! Buat yang baru mau mulai, jangan takut, mulai aja dulu dari yang kecil. Beli tiap bulan rutin, gak usah dipusingin naik turunnya harga jangka pendek karena dalam jangka panjang emas selalu menang!

Oke segitu dulu update dari aku hari ini! Kalau ada yang mau diskusi atau nanya, yuk tulis di kolom komentar, aku bacain semua kok! Jangan lupa subscribe ya biar kita bisa ketemu terus tiap hari! Bye bye dan sampai jumpa besok!""",
    }

    return templates.get(NARASI_GAYA, templates["formal_analitis"]).strip()


# ════════════════════════════════════════════════════════════
# BAGIAN 6 — NARASI & JUDUL (GEMINI)
# ════════════════════════════════════════════════════════════

def buat_narasi_dan_judul(info, data_harga):
    print("[2/6] Membuat narasi...")
    status_harga  = info['status']
    selisih_harga = f"{info['selisih']:,}".replace(",",".")
    harga_skrg    = f"{info['harga_sekarang']:,}".replace(",",".")
    historis      = info.get("historis",{})

    judul = buat_judul_clickbait_lokal(info, historis)
    print(f"  -> Judul: {judul}")

    ringkasan_h = []
    for label, data in historis.items():
        if data:
            arah = "naik" if data["naik"] else ("turun" if not data["stabil"] else "stabil")
            nama = {"kemarin":"kemarin","7_hari":"seminggu lalu","1_bulan":"sebulan lalu",
                    "3_bulan":"3 bulan lalu","6_bulan":"6 bulan lalu","1_tahun":"setahun lalu"
                    }.get(label,label)
            ringkasan_h.append(
                f"{nama}: {arah} {abs(data['persen']):.1f}% dari Rp {data['harga_ref']:,}".replace(",",".")
            )
    konteks = " | ".join(ringkasan_h) or "Data historis belum tersedia."

    GAYA_DESC = {
        "formal_analitis":  "profesional, analitis, gunakan istilah investasi, nada seperti analis keuangan",
        "santai_edukatif":  "santai tapi informatif, bahasa sehari-hari yang mudah dipahami, edukatif",
        "berita_singkat":   "singkat padat jelas seperti reporter berita, to the point, efisien",
        "energik_motivatif":"sangat energik dan semangat, banyak tanda seru, motivatif, membakar semangat",
        "percakapan_akrab": "akrab seperti ngobrol dengan teman, casual, gunakan kata guys bro dll",
    }
    gaya_desc = GAYA_DESC.get(NARASI_GAYA, GAYA_DESC["formal_analitis"])

    prompt = f"""Kamu adalah scriptwriter YouTube profesional.
Gaya narasi: {gaya_desc}
Channel: {NAMA_CHANNEL}

BARIS PERTAMA HARUS PERSIS: "Halo sobat {NAMA_CHANNEL}," — tidak boleh ada teks apapun sebelumnya.

DATA:
- Harga 1 gram hari ini: Rp {harga_skrg}
- Status: {status_harga} Rp {selisih_harga} vs kemarin
- Historis: {konteks}
- Data Antam: {data_harga[:2000]}

STRUKTUR (900-1000 KATA, gaya {NARASI_GAYA}):
1. Pembuka (100 kata): Sapa penonton, umumkan harga, status
2. Daftar harga (200 kata): Semua ukuran 0.5g–1000g
3. Analisa & konteks (300 kata): Historis + faktor global
4. Edukasi & penutup (300 kata): Tips investasi, ajakan subscribe

ATURAN:
- MULAI LANGSUNG "Halo sobat {NAMA_CHANNEL}," tanpa kata pengantar
- Semua angka ditulis dengan HURUF
- Paragraf murni tanpa bullet/nomor/simbol
- Konsisten dengan gaya {NARASI_GAYA} dari awal sampai akhir"""

    MODEL_CHAIN = ["gemini-2.0-flash-lite","gemini-2.0-flash","gemini-2.5-flash-lite"]
    for model_name in MODEL_CHAIN:
        for attempt in range(3):
            try:
                url_api = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                           f"{model_name}:generateContent?key={GEMINI_API_KEY}")
                payload = {
                    "contents":[{"parts":[{"text":prompt}]}],
                    "generationConfig":{"maxOutputTokens":8192,"temperature":0.9}
                }
                print(f"  -> {model_name} attempt {attempt+1}...")
                resp = requests.post(url_api, json=payload, timeout=90)
                if resp.status_code == 429:
                    t = int(resp.headers.get('Retry-After',(2**attempt)*10))
                    print(f"  -> 429. Tunggu {t}s...")
                    time.sleep(t)
                    continue
                resp.raise_for_status()
                script_raw = resp.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                baris, baru, skip = script_raw.split('\n'), [], True
                for idx,b in enumerate(baris):
                    bl = b.lower().strip()
                    if skip:
                        if bl.startswith("halo sobat"):
                            skip = False
                            baru.append(b)
                        elif idx > 4:
                            skip = False
                            baru.append(b)
                    elif not (bl.startswith("[judul]") or bl.startswith("[script]")):
                        baru.append(b)
                script = '\n'.join(baru).strip() or script_raw
                print(f"  -> ✅ Script OK ({len(script.split())} kata) — {model_name}")
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
# BAGIAN 7 — GENERATE SUARA
# ════════════════════════════════════════════════════════════

def buat_suara(teks, output_audio):
    print(f"[3/6] Generate suara AI — voice:{VOICE} rate:{VOICE_RATE}...")
    teks_bersih = re.sub(r'\[.*?\]|\(.*?\)|\*.*?\*','',teks).strip()
    subprocess.run([
        sys.executable,'-m','edge_tts',
        '--voice', VOICE,
        '--rate',  VOICE_RATE,
        '--text',  teks_bersih,
        '--write-media', output_audio
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    if not os.path.exists(output_audio) or os.path.getsize(output_audio) < 1000:
        raise FileNotFoundError("File audio gagal dibuat!")

    hasil_dur = subprocess.run(
        ['ffprobe','-v','error','-show_entries','format=duration',
         '-of','default=noprint_wrappers=1:nokey=1',output_audio],
        capture_output=True, text=True
    )
    durasi = float(hasil_dur.stdout.strip())
    if durasi < 30:
        raise ValueError(f"Audio terlalu pendek ({durasi:.1f}s)!")
    print(f"  -> ✅ Audio OK: {durasi:.0f}s ({durasi/60:.1f} menit)")
    return durasi


# ════════════════════════════════════════════════════════════
# BAGIAN 8 — KEN BURNS EFFECT + RENDER KLIP
# ════════════════════════════════════════════════════════════

def _get_ken_burns_filter(durasi=10.0):
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
    return (
        f"scale={VIDEO_WIDTH*2}:{VIDEO_HEIGHT*2}:"
        f"force_original_aspect_ratio=increase,"
        f"crop={VIDEO_WIDTH*2}:{VIDEO_HEIGHT*2},"
        f"{zoompan},"
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
        f"fade=t=in:st=0:d=0.5,fade=t=out:st={dur-0.5:.1f}:d=0.5"
    )


def escape_ffmpeg_path(path):
    return path.replace('\\','/').replace(':','\\:')


def siapkan_font_lokal():
    font_paths = [
        "C:/Windows/Fonts/arial.ttf",
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
    i, img, font_sistem, output_klip = args
    durasi_klip = random.choice([8,10,12])
    vf          = _get_ken_burns_filter(durasi_klip)
    if font_sistem:
        fe = escape_ffmpeg_path(font_sistem)
        x,y = random.choice([("30","30"),("w-tw-30","30"),("30","h-th-30"),("w-tw-30","h-th-30")])
        vf += f",drawtext=fontfile='{fe}':text='{NAMA_CHANNEL}':fontcolor=white@0.6:fontsize=28:x={x}:y={y}"
    cmd = [
        'ffmpeg','-y',
        '-loop','1','-framerate',str(FPS),'-i',img,
        '-f','lavfi','-i','anullsrc=channel_layout=stereo:sample_rate=44100',
        '-vf',vf,
        '-map','0:v','-map','1:a',
        '-c:v','libx264','-preset','faster',
        '-pix_fmt','yuv420p','-crf','23',
        '-c:a','aac',
        '-t',str(durasi_klip),output_klip
    ]
    with open(FFMPEG_LOG,'a',encoding='utf-8') as log:
        log.write(f"\n=== Klip-IMG {i}: {os.path.basename(img)} ===\n")
        result = subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=log)
    if result.returncode != 0 or not os.path.exists(output_klip) or os.path.getsize(output_klip) < 1000:
        return None
    return i, output_klip


def _render_klip_video(args):
    i, vid_path, font_sistem, output_klip = args
    durasi_klip = random.choice([8,10,12])
    try:
        res = subprocess.run(
            ['ffprobe','-v','error','-show_entries','format=duration',
             '-of','default=noprint_wrappers=1:nokey=1',vid_path],
            capture_output=True,text=True,timeout=10
        )
        dur_src = float(res.stdout.strip())
    except:
        dur_src = 30.0
    max
