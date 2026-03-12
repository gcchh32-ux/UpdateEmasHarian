# =============================================================
# AUTO VIDEO EMAS v7.1 - MULTI CHANNEL ANTI DUPLIKAT
# Fix: render final, debug lengkap, thumbnail warna-warni
# CHANNEL_ID diset via GitHub Secret: 1,2,3,4,5
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
        from PIL import Image, ImageDraw, ImageFont, ImageEnhance
    except ImportError:
        print("Menginstal library...")
        subprocess.check_call([sys.executable, "-m", "pip", "install",
            "requests", "beautifulsoup4", "edge-tts",
            "google-api-python-client", "google-auth-oauthlib", "Pillow"])

pastikan_library_terinstall()
import requests
from bs4 import BeautifulSoup

# ============================================================
# CHANNEL CONFIG
# ============================================================
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "1"))

CHANNEL_CONFIG = {
    1: {
        "nama":        "Sobat Antam",
        "voice":       "id-ID-ArdiNeural",
        "rate":        "+5%",
        "gaya":        "formal_analitis",
        "skema_warna": "merah_emas",
        "keywords_img":["gold bars","gold investment","gold bullion",
                        "precious metals","gold coins","gold market"],
        "keywords_vid":["gold bars","gold investment","financial market"],
    },
    2: {
        "nama":        "Info Logam Mulia",
        "voice":       "id-ID-GadisNeural",
        "rate":        "+3%",
        "gaya":        "santai_edukatif",
        "skema_warna": "biru_perak",
        "keywords_img":["gold market","wealth management","investment finance",
                        "money saving","bank gold","financial growth"],
        "keywords_vid":["gold market","wealth","finance"],
    },
    3: {
        "nama":        "Info Logam Mulia",
        "voice":       "id-ID-ArdiNeural",
        "rate":        "-3%",
        "gaya":        "berita_singkat",
        "skema_warna": "hijau_platinum",
        "keywords_img":["gold nuggets","bank vault","financial chart",
                        "economy growth","commodity trading","gold jewelry"],
        "keywords_vid":["gold nuggets","bank vault","economy"],
    },
    4: {
        "nama":        "Harga Emas Live",
        "voice":       "id-ID-GadisNeural",
        "rate":        "+8%",
        "gaya":        "energik_motivatif",
        "skema_warna": "ungu_mewah",
        "keywords_img":["luxury gold","gold reserve","commodity gold",
                        "platinum gold","gold standard","gold trophy"],
        "keywords_vid":["luxury gold","commodity","stock market"],
    },
    5: {
        "nama":        "Cek Harga Emas",
        "voice":       "id-ID-ArdiNeural",
        "rate":        "+0%",
        "gaya":        "percakapan_akrab",
        "skema_warna": "oranye_tembaga",
        "keywords_img":["gold coin collection","antique gold","gold ring",
                        "gold necklace","yellow gold","gold bracelet"],
        "keywords_vid":["gold coin","antique gold","jewelry gold"],
    },
}

CFG               = CHANNEL_CONFIG.get(CHANNEL_ID, CHANNEL_CONFIG[1])
NAMA_CHANNEL      = CFG["nama"]
VOICE             = CFG["voice"]
VOICE_RATE        = CFG["rate"]
NARASI_GAYA       = CFG["gaya"]
KATA_KUNCI_GAMBAR = CFG["keywords_img"]
KATA_KUNCI_VIDEO  = CFG["keywords_vid"]

GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY", "")
PEXELS_API_KEY    = os.environ.get("PEXELS_API_KEY", "")
FFMPEG_LOG        = "ffmpeg_log.txt"
FILE_HISTORY      = "history_harga.json"
YOUTUBE_CATEGORY  = "25"
YOUTUBE_TAGS      = [
    "harga emas","emas antam","investasi emas","logam mulia",
    "harga emas hari ini","emas antam hari ini","harga emas antam",
    "update emas","emas batangan",
]

VIDEO_WIDTH       = 1920
VIDEO_HEIGHT      = 1080
FPS               = 30

FOLDER_GAMBAR     = "gambar_bank"
FOLDER_VIDEO_BANK = "video_bank"
JUMLAH_GAMBAR_MIN = 30
JUMLAH_DL_GAMBAR  = 50
JUMLAH_VIDEO_MIN  = 6
JUMLAH_DL_VIDEO   = 12
SIMPAN_VIDEO_MAKS = 3

# ============================================================
# SKEMA WARNA THUMBNAIL
# ============================================================
SKEMA_THUMBNAIL = {
    "merah_emas": {
        "Naik":  {"badge":(200,0,0),    "aksen":(255,80,0),   "teks":(255,220,0),
                  "sub":(255,200,150),  "hl_teks":(255,255,255),"icon":"▲ NAIK",
                  "bg_grad_atas":(60,0,0),"bg_grad_bawah":(20,0,0)},
        "Turun": {"badge":(0,140,50),   "aksen":(0,230,80),   "teks":(180,255,160),
                  "sub":(200,255,200),  "hl_teks":(255,255,255),"icon":"▼ TURUN",
                  "bg_grad_atas":(0,40,10),"bg_grad_bawah":(0,15,5)},
        "Stabil":{"badge":(140,100,0),  "aksen":(255,190,0),  "teks":(255,230,100),
                  "sub":(255,240,180),  "hl_teks":(255,255,255),"icon":"⬛ STABIL",
                  "bg_grad_atas":(40,30,0),"bg_grad_bawah":(15,10,0)},
    },
    "biru_perak": {
        "Naik":  {"badge":(0,60,180),   "aksen":(0,160,255),  "teks":(150,220,255),
                  "sub":(200,230,255),  "hl_teks":(255,255,255),"icon":"▲ NAIK",
                  "bg_grad_atas":(0,20,60),"bg_grad_bawah":(0,5,25)},
        "Turun": {"badge":(0,120,160),  "aksen":(0,220,200),  "teks":(180,255,250),
                  "sub":(200,255,255),  "hl_teks":(255,255,255),"icon":"▼ TURUN",
                  "bg_grad_atas":(0,35,45),"bg_grad_bawah":(0,15,20)},
        "Stabil":{"badge":(80,80,160),  "aksen":(160,160,255),"teks":(200,200,255),
                  "sub":(220,220,255),  "hl_teks":(255,255,255),"icon":"⬛ STABIL",
                  "bg_grad_atas":(20,20,50),"bg_grad_bawah":(5,5,20)},
    },
    "hijau_platinum": {
        "Naik":  {"badge":(0,130,60),   "aksen":(0,230,100),  "teks":(200,255,200),
                  "sub":(220,255,220),  "hl_teks":(0,50,0),   "icon":"▲ NAIK",
                  "bg_grad_atas":(0,40,15),"bg_grad_bawah":(0,15,5)},
        "Turun": {"badge":(180,140,0),  "aksen":(255,210,0),  "teks":(255,240,150),
                  "sub":(255,245,180),  "hl_teks":(50,30,0),  "icon":"▼ TURUN",
                  "bg_grad_atas":(50,40,0),"bg_grad_bawah":(20,15,0)},
        "Stabil":{"badge":(60,120,60),  "aksen":(150,255,150),"teks":(220,255,220),
                  "sub":(230,255,230),  "hl_teks":(0,50,0),   "icon":"⬛ STABIL",
                  "bg_grad_atas":(15,35,15),"bg_grad_bawah":(5,15,5)},
    },
    "ungu_mewah": {
        "Naik":  {"badge":(120,0,180),  "aksen":(220,0,255),  "teks":(255,180,255),
                  "sub":(240,200,255),  "hl_teks":(255,255,255),"icon":"▲ NAIK",
                  "bg_grad_atas":(40,0,60),"bg_grad_bawah":(15,0,25)},
        "Turun": {"badge":(80,0,140),   "aksen":(180,100,255),"teks":(230,200,255),
                  "sub":(240,220,255),  "hl_teks":(255,255,255),"icon":"▼ TURUN",
                  "bg_grad_atas":(25,0,45),"bg_grad_bawah":(10,0,20)},
        "Stabil":{"badge":(100,50,150), "aksen":(200,150,255),"teks":(240,220,255),
                  "sub":(245,230,255),  "hl_teks":(255,255,255),"icon":"⬛ STABIL",
                  "bg_grad_atas":(30,15,50),"bg_grad_bawah":(12,5,20)},
    },
    "oranye_tembaga": {
        "Naik":  {"badge":(200,80,0),   "aksen":(255,140,0),  "teks":(255,210,100),
                  "sub":(255,225,150),  "hl_teks":(50,20,0),  "icon":"▲ NAIK",
                  "bg_grad_atas":(60,25,0),"bg_grad_bawah":(25,10,0)},
        "Turun": {"badge":(160,60,0),   "aksen":(255,100,0),  "teks":(255,180,100),
                  "sub":(255,200,150),  "hl_teks":(50,15,0),  "icon":"▼ TURUN",
                  "bg_grad_atas":(50,20,0),"bg_grad_bawah":(20,8,0)},
        "Stabil":{"badge":(180,100,0),  "aksen":(255,160,50), "teks":(255,220,150),
                  "sub":(255,235,180),  "hl_teks":(50,25,0),  "icon":"⬛ STABIL",
                  "bg_grad_atas":(55,30,0),"bg_grad_bawah":(22,12,0)},
    },
}

SKEMA_AKTIF = SKEMA_THUMBNAIL.get(CFG["skema_warna"], SKEMA_THUMBNAIL["merah_emas"])

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ════════════════════════════════════════════════════════════
# BAGIAN 1 — STORAGE
# ════════════════════════════════════════════════════════════

def _list_gambar():
    return sorted(
        glob.glob(f"{FOLDER_GAMBAR}/*.jpg") +
        glob.glob(f"{FOLDER_GAMBAR}/*.jpeg") +
        glob.glob(f"{FOLDER_GAMBAR}/*.png")
    )

def _list_video_bank():
    return sorted(glob.glob(f"{FOLDER_VIDEO_BANK}/*.mp4"))

def kelola_bank_gambar():
    os.makedirs(FOLDER_GAMBAR, exist_ok=True)
    ada = _list_gambar()
    log(f"[STORAGE] Bank gambar: {len(ada)} file")
    if len(ada) < JUMLAH_GAMBAR_MIN:
        log(f"[STORAGE] Download gambar dari Pexels (butuh {JUMLAH_DL_GAMBAR - len(ada)} lagi)...")
        _download_pexels_gambar(JUMLAH_DL_GAMBAR - len(ada))
        ada = _list_gambar()
        log(f"[STORAGE] Bank gambar sekarang: {len(ada)}")
    return ada

def _download_pexels_gambar(jumlah):
    if not PEXELS_API_KEY:
        log("  -> ERROR: PEXELS_API_KEY kosong! Set di GitHub Secrets.")
        return
    headers     = {"Authorization": PEXELS_API_KEY}
    per_keyword = max(6, jumlah // len(KATA_KUNCI_GAMBAR))
    total       = 0
    ts          = int(time.time())
    for kw in KATA_KUNCI_GAMBAR:
        try:
            resp = requests.get(
                f"https://api.pexels.com/v1/search?query={kw}"
                f"&per_page={per_keyword}&orientation=landscape&size=large",
                headers=headers, timeout=15)
            resp.raise_for_status()
            fotos = resp.json().get("photos",[])
            for i, foto in enumerate(fotos):
                fn = f"{FOLDER_GAMBAR}/px_{ts}_{kw.replace(' ','_')}_{i}.jpg"
                if os.path.exists(fn): continue
                try:
                    data = requests.get(foto["src"]["large2x"], timeout=30).content
                    with open(fn,"wb") as f: f.write(data)
                    total += 1
                except: pass
            log(f"  -> Gambar '{kw}': {len(fotos)} foto OK")
        except Exception as e:
            log(f"  -> Gagal download gambar '{kw}': {e}")
    log(f"  -> Total download: {total} gambar")

def kelola_bank_video():
    os.makedirs(FOLDER_VIDEO_BANK, exist_ok=True)
    ada = _list_video_bank()
    log(f"[STORAGE] Bank video: {len(ada)} file")
    if len(ada) < JUMLAH_VIDEO_MIN:
        log(f"[STORAGE] Download video dari Pexels...")
        _download_pexels_video(JUMLAH_DL_VIDEO - len(ada))
        ada = _list_video_bank()
        log(f"[STORAGE] Bank video sekarang: {len(ada)}")
    return ada

def _download_pexels_video(jumlah):
    if not PEXELS_API_KEY:
        log("  -> ERROR: PEXELS_API_KEY kosong!")
        return
    headers     = {"Authorization": PEXELS_API_KEY}
    per_keyword = max(3, jumlah // len(KATA_KUNCI_VIDEO))
    total       = 0
    ts          = int(time.time())
    for kw in KATA_KUNCI_VIDEO:
        try:
            resp = requests.get(
                f"https://api.pexels.com/videos/search?query={kw}"
                f"&per_page={per_keyword}&orientation=landscape",
                headers=headers, timeout=15)
            resp.raise_for_status()
            videos = resp.json().get("videos",[])
            for i, vid in enumerate(videos):
                files = vid.get("video_files",[])
                best  = None
                for vf in sorted(files, key=lambda x: x.get("height",0), reverse=True):
                    if vf.get("height",0) >= 720 and vf.get("file_type") == "video/mp4":
                        best = vf; break
                if not best and files: best = files[0]
                if not best: continue
                fn = f"{FOLDER_VIDEO_BANK}/px_{ts}_{kw.replace(' ','_')}_{i}.mp4"
                if os.path.exists(fn): continue
                try:
                    data = requests.get(best["link"], timeout=90).content
                    with open(fn,"wb") as f: f.write(data)
                    total += 1
                    log(f"  -> Video '{kw}' [{i+1}] OK ({len(data)//1024} KB)")
                except Exception as e:
                    log(f"  -> Gagal download video: {e}")
            if total >= jumlah: break
        except Exception as e:
            log(f"  -> Gagal video '{kw}': {e}")
    log(f"  -> Total download: {total} video")

def kelola_video_lama():
    videos = sorted(glob.glob("Video_Emas_*.mp4"))
    for v in videos[:max(0, len(videos)-SIMPAN_VIDEO_MAKS)]:
        try: os.remove(v); log(f"[STORAGE] Hapus lama: {v}")
        except: pass

def debug_storage():
    log("=== DEBUG STORAGE ===")
    log(f"  Folder gambar_bank: {len(_list_gambar())} file")
    log(f"  Folder video_bank : {len(_list_video_bank())} file")
    log(f"  Video hasil       : {len(glob.glob('Video_Emas_*.mp4'))} file")
    log(f"  Thumbnail         : {len(glob.glob('thumbnail_*.jpg'))} file")
    log(f"  Upload history    : {'Ada' if os.path.exists('upload_history.json') else 'Belum ada'}")
    log(f"  GEMINI_API_KEY    : {'✅ Set' if GEMINI_API_KEY else '❌ KOSONG!'}")
    log(f"  PEXELS_API_KEY    : {'✅ Set' if PEXELS_API_KEY else '❌ KOSONG!'}")
    log(f"  CHANNEL_ID        : {CHANNEL_ID} ({NAMA_CHANNEL})")
    log(f"  NARASI_GAYA       : {NARASI_GAYA}")
    log(f"  SKEMA_WARNA       : {CFG['skema_warna']}")
    log("=====================")


# ════════════════════════════════════════════════════════════
# BAGIAN 2 — HISTORY HARGA
# ════════════════════════════════════════════════════════════

def muat_history():
    if os.path.exists(FILE_HISTORY):
        try:
            with open(FILE_HISTORY, encoding="utf-8") as f:
                d = json.load(f)
            if "records" not in d and "harga_1_gram" in d:
                return {"records":[{"tanggal":d.get("tanggal","2000-01-01"),
                                    "harga":d["harga_1_gram"]}]}
            return d
        except Exception as e:
            log(f"  -> Gagal muat history: {e}")
    return {"records":[]}

def simpan_history(harga):
    hist    = muat_history()
    records = hist.get("records",[])
    today   = datetime.now().strftime("%Y-%m-%d")
    records = [r for r in records if r["tanggal"] != today]
    records.insert(0, {"tanggal":today,"harga":harga})
    records = records[:365]
    with open(FILE_HISTORY,"w",encoding="utf-8") as f:
        json.dump({"records":records}, f, indent=2, ensure_ascii=False)
    return records

def cari_harga_n_hari_lalu(records, n):
    target = (datetime.now().date()-timedelta(days=n)).strftime("%Y-%m-%d")
    for r in records:
        if r["tanggal"] <= target: return r
    return None

def analisa_historis(harga_skrg, records):
    hasil = {}
    for label, n in {"kemarin":1,"7_hari":7,"1_bulan":30,
                     "3_bulan":90,"6_bulan":180,"1_tahun":365}.items():
        rec = cari_harga_n_hari_lalu(records, n)
        if rec:
            s = harga_skrg - rec["harga"]
            p = round((s/rec["harga"])*100, 2)
            hasil[label] = {"tanggal":rec["tanggal"],"harga_ref":rec["harga"],
                            "selisih":s,"persen":p,"naik":s>0,"stabil":s==0}
    return hasil


# ════════════════════════════════════════════════════════════
# BAGIAN 3 — JUDUL CLICKBAIT (8 variasi × 5 gaya × 3 status)
# ════════════════════════════════════════════════════════════

def buat_judul_clickbait_lokal(info, historis):
    h   = f"Rp {info['harga_sekarang']:,}".replace(",",".")
    st  = info['status']
    sel = f"Rp {info['selisih']:,}".replace(",",".")
    tgl = datetime.now().strftime("%d %b %Y")
    np  = {"kemarin":"Kemarin","7_hari":"Seminggu","1_bulan":"Sebulan",
           "3_bulan":"3 Bulan","6_bulan":"6 Bulan","1_tahun":"Setahun"}

    penting = None
    for lb in ["3_bulan","1_bulan","6_bulan","1_tahun","7_hari"]:
        d = historis.get(lb)
        if d and abs(d["persen"]) >= 2.0:
            penting = (lb, d); break

    if penting:
        lb, d = penting
        pct   = abs(d["persen"])
        pl    = np.get(lb, lb)
        if d["naik"]:
            pool = {
                "formal_analitis":[
                    f"📊 Analisa: Emas Antam NAIK {pct:.1f}% dalam {pl} — Proyeksi {tgl}",
                    f"Sinyal Bullish! Emas Antam +{pct:.1f}% Sejak {pl} — Harga {h}/gram",
                    f"Data Kenaikan {pct:.1f}% dalam {pl}! Emas Antam {h}/gram — Beli?",
                    f"Momentum NAIK {pct:.1f}%! Emas Antam {h}/gram — Analisa {tgl}",
                    f"Tren Naik {pct:.1f}% dalam {pl} — Emas Antam {h}/gram Berapa Lagi?",
                    f"📈 Emas Antam Menguat {pct:.1f}% dari {pl} Lalu — Analisa Teknikal",
                    f"Investor Siap! Emas Antam +{pct:.1f}% dalam {pl} — Target {h}/gram",
                    f"Fundamental Kuat! Emas Antam NAIK {pct:.1f}% Sejak {pl} — {tgl}",
                ],
                "santai_edukatif":[
                    f"Eh Emas Naik {pct:.1f}% lho dalam {pl}! Masih Mau Beli? {h}/gram",
                    f"Kamu Sudah Tau? Emas Antam Udah Naik {pct:.1f}% dari {pl} Lalu!",
                    f"💡 Emas Naik {pct:.1f}% dalam {pl} — Apa Artinya Buat Kamu?",
                    f"Emas Antam Naik {pct:.1f}%! {h}/gram — Yuk Pelajari Bareng!",
                    f"Wow Naik {pct:.1f}% dalam {pl}! Emas Antam {h}/gram Worth It?",
                    f"Baru Tau Emas Naik {pct:.1f}%? Antam {h}/gram — Simak Ini!",
                    f"Naik {pct:.1f}% tapi Masih Bagus Beli? Emas Antam {h}/gram",
                    f"💡 Belajar dari Kenaikan {pct:.1f}% Emas dalam {pl} — Yuk!",
                ],
                "berita_singkat":[
                    f"BREAKING: Emas Antam +{pct:.1f}% dalam {pl}! Harga {h}/gram",
                    f"UPDATE {tgl}: Emas Antam Naik {pct:.1f}% dari {pl} — {h}/gram",
                    f"🔴 NAIK {pct:.1f}% dari {pl}! Emas Antam {h}/gram — Update Resmi",
                    f"TERBARU: Kenaikan {pct:.1f}% Emas Antam {h}/gram — {tgl}",
                    f"LIVE {tgl}: Emas Antam {h}/gram Naik {pct:.1f}% dari {pl}",
                    f"INFO RESMI: Emas Antam +{pct:.1f}% Sejak {pl} — {h}/gram",
                    f"WASPADA: Emas Antam Sudah Naik {pct:.1f}% dalam {pl}! {h}",
                    f"TERKINI: Emas Antam {h}/gram — Naik {pct:.1f}% dari {pl}",
                ],
                "energik_motivatif":[
                    f"🚀 EMAS MELEJIT {pct:.1f}%! {pl} Lalu Beli = UNTUNG BESAR!",
                    f"NAIK {pct:.1f}% dalam {pl}!! BUKTI Emas Investasi TERBAIK! {h}",
                    f"💥 PROFIT {pct:.1f}% dalam {pl}! Masih Ragu Beli Emas?!",
                    f"EMAS ANTAM TERBANG {pct:.1f}%!! Jangan Menyesal! Harga {h}/gram",
                    f"WOW {pct:.1f}% KEUNTUNGAN dalam {pl}!! Emas Antam {h}/gram!!",
                    f"🔥 NAIK {pct:.1f}%!! Bukti Nyata Emas = Investasi TERBAIK!!",
                    f"ALERT NAIK {pct:.1f}%! Emas Antam {h}/gram — Beli SEKARANG!",
                    f"JANGAN LEWATKAN! Emas +{pct:.1f}% dalam {pl} — {h}/gram!!",
                ],
                "percakapan_akrab":[
                    f"Bro, Emas Udah Naik {pct:.1f}% nih dari {pl} — Gimana?",
                    f"Guys! Emas Naik {pct:.1f}% dalam {pl}! Worth It Beli? {h}",
                    f"Jujur nih, Emas Antam {pct:.1f}% Naik dari {pl} — {h}/gram",
                    f"Serius? Emas Naik {pct:.1f}% dalam {pl}! Yuk Bahas — {h}",
                    f"Eh, Coba Liat Nih! Emas Naik {pct:.1f}% dari {pl} — Wow!",
                    f"Kalian Tau Gak? Emas Udah +{pct:.1f}% dari {pl} — Keren!",
                    f"Wah Serius Nih! Emas {h}/gram — Naik {pct:.1f}% dari {pl}",
                    f"Ngobrol Bareng: Emas Naik {pct:.1f}% dalam {pl} — Gimana?",
                ],
            }
        else:
            pool = {
                "formal_analitis":[
                    f"📊 Koreksi {pct:.1f}% dalam {pl} — Emas Antam {h}/gram Beli?",
                    f"Teknikal Oversold! Emas -{pct:.1f}% dari {pl} — {h}/gram",
                    f"Data Koreksi {pct:.1f}% Sejak {pl} — Akumulasi Sekarang?",
                    f"Support Level! Emas Antam Turun {pct:.1f}% dari {pl} — {h}",
                    f"Analisa Koreksi {pct:.1f}%: Emas Antam {h}/gram — Entry Point?",
                    f"📉 Emas -{pct:.1f}% dalam {pl} — Rekomendasi Analis {tgl}",
                    f"Pullback {pct:.1f}%! Emas Antam {h}/gram — Beli atau Tunggu?",
                    f"Reversal Signal? Emas Antam Turun {pct:.1f}% dari {pl} — {h}",
                ],
                "santai_edukatif":[
                    f"Emas Turun {pct:.1f}% dari {pl} — Waktu Terbaik Beli Nih!",
                    f"💡 Koreksi {pct:.1f}% = Kesempatan! Emas Antam {h}/gram",
                    f"Mau Beli Emas Murah? Turun {pct:.1f}% dari {pl} — Ayo!",
                    f"Tenang! Turun {pct:.1f}% itu Normal — Antam {h}/gram",
                    f"Eh Emas Turun {pct:.1f}% nih! Justru Bagus Buat Nabung!",
                    f"💡 Koreksi {pct:.1f}% = Sale Emas! Yuk Pelajari Strateginya",
                    f"Emas Murah {pct:.1f}% dari {pl} — {h}/gram — Beli Dulu!",
                    f"Penjelasan Koreksi {pct:.1f}%: Emas Antam {h}/gram Normal!",
                ],
                "berita_singkat":[
                    f"UPDATE: Emas Antam -{pct:.1f}% dari {pl} — {h}/gram {tgl}",
                    f"TERBARU {tgl}: Koreksi {pct:.1f}% — Emas Antam {h}/gram",
                    f"🟢 TURUN {pct:.1f}% dari {pl}! Emas Antam {h}/gram Hari Ini",
                    f"INFO: Emas -{pct:.1f}% dalam {pl} — {h}/gram — Beli Gak?",
                    f"LIVE: Emas Antam Koreksi {pct:.1f}% dari {pl} — {h}/gram",
                    f"TERKINI {tgl}: Emas {h}/gram Turun {pct:.1f}% dari {pl}",
                    f"INFO RESMI: Koreksi Emas {pct:.1f}% — Harga {h}/gram {tgl}",
                    f"DATA: Emas Antam -{pct:.1f}% Sejak {pl} — {h}/gram Now",
                ],
                "energik_motivatif":[
                    f"💰 DISKON {pct:.1f}%!! EMAS ANTAM {h}/gram — BORONG NOW!",
                    f"KESEMPATAN LANGKA! Emas -{pct:.1f}% dari {pl} — ACTION!",
                    f"🎯 HARGA TERBAIK! Koreksi {pct:.1f}% dalam {pl} — BELI!",
                    f"SALE EMAS {pct:.1f}%! Antam {h}/gram — Kapan Lagi Murah?!",
                    f"ALERT MURAH! Emas Turun {pct:.1f}% — {h}/gram BELI NOW!!",
                    f"🔥 DISKON EMAS {pct:.1f}%! Harga {h}/gram — Jangan Tunggu!",
                    f"BORONG SEKARANG! Emas -{pct:.1f}% = {h}/gram — LAST CHANCE!",
                    f"💸 PROFIT WAITING! Emas Koreksi {pct:.1f}% — {h}/gram BUY!",
                ],
                "percakapan_akrab":[
                    f"Wah Emas Turun {pct:.1f}% nih dari {pl} — Udah Borong?",
                    f"Guys, Waktu Beli Emas! Turun {pct:.1f}% — {h}/gram Nih",
                    f"Serius Emas Turun {pct:.1f}%? Yuk Analisa Bareng — {h}",
                    f"Bro, Emas {h}/gram — Turun {pct:.1f}% dari {pl}, Beli?",
                    f"Kalian Udah Beli? Emas Turun {pct:.1f}% dari {pl} — {h}",
                    f"Lagi Murah Nih! Emas -{pct:.1f}% dari {pl} — Gimana?",
                    f"Eh Emas Turun {pct:.1f}%! {h}/gram — Mau Borong Bareng?",
                    f"Diskusi Yuk! Emas -{pct:.1f}% dari {pl} — Worth It Beli?",
                ],
            }
        return random.choice(pool.get(NARASI_GAYA, pool["formal_analitis"]))[:100]

    # Pool per status per gaya (tanpa historis signifikan)
    pools = {
        "Naik": {
            "formal_analitis":[
                f"Emas Antam {h}/gram Naik {sel} — Analisa & Proyeksi {tgl}",
                f"Kenaikan {sel} pada Emas Antam {h}/gram — Rekomendasi Analis",
                f"📈 Emas Antam Terkerek {sel} Jadi {h}/gram — Sinyal Beli?",
                f"Momentum Naik! Emas Antam +{sel} Jadi {h}/gram Hari Ini",
                f"Emas Antam {h}/gram Naik {sel} — Fundamental Masih Kuat?",
                f"🔴 Emas Antam Menguat {sel} ke {h}/gram — Update Resmi {tgl}",
                f"Harga Emas Antam Naik {sel} — Tren Berlanjut? {h}/gram",
                f"Update: Emas Antam +{sel} ke {h}/gram — Rekomendasi {tgl}",
            ],
            "santai_edukatif":[
                f"Emas Naik Lagi {sel}! Jadi {h}/gram — Masih Oke Buat Invest?",
                f"Harga Emas Antam Naik {sel} — Yuk Pahami Kenapa! {h}/gram",
                f"💡 Kenapa Emas Naik {sel}? Penjelasan Mudahnya! {h}/gram",
                f"Emas Antam {h}/gram Naik {sel} — 5 Hal yang Perlu Kamu Tau",
                f"Naik {sel}! Emas Antam {h}/gram — Tips Investor Pemula",
                f"Update Emas: Naik {sel} ke {h}/gram — Santai, Ini Normal!",
                f"Eh Emas Naik {sel} lho! Jadi {h}/gram — Mau Tau Kenapa?",
                f"Emas Antam {h}/gram — Naik {sel}, Waktu Tepat Nabung?",
            ],
            "berita_singkat":[
                f"BREAKING: Emas Antam Naik {sel} Jadi {h}/gram — {tgl}",
                f"UPDATE {tgl}: Naik {sel} ke {h}/gram — Cek Sekarang!",
                f"🔴 NAIK {sel}! Emas Antam {h}/gram — Update Resmi Hari Ini",
                f"TERBARU: Emas Antam {h}/gram Naik {sel} dari Kemarin",
                f"INFO {tgl}: Emas Antam Naik {sel} — Harga Lengkap di Sini",
                f"LIVE: Emas Antam {h}/gram Naik {sel} Hari Ini!",
                f"WASPADA: Emas Antam Naik {sel} ke {h}/gram — {tgl}",
                f"TERKINI: Emas Antam {h}/gram Naik {sel} — Jual atau Tahan?",
            ],
            "energik_motivatif":[
                f"🚨 EMAS NAIK {sel}!! Antam {h}/gram — Masih Mau Diam Aja?!",
                f"NAIK {sel}! Emas Antam {h}/gram — INI TANDA NAIK TERUS?!",
                f"💥 EMAS ANTAM MELEJIT {sel}! {h}/gram — Kapan Lagi Beli?!",
                f"ALERT! Emas Naik {sel}! {h}/gram — Jangan Sampai Nyesel!",
                f"🔥 EMAS NAIK {sel} HARI INI! {h}/gram — ACTION SEKARANG!",
                f"WOW! Emas Antam Naik {sel} ke {h}/gram — Ini Buktinya!",
                f"NAIK TERUS! Emas Antam +{sel} Jadi {h}/gram — Beli Gak?!",
                f"EMAS ANTAM {h}/gram NAIK {sel}!! Mau Untung? Tonton Ini!",
            ],
            "percakapan_akrab":[
                f"Guys Emas Naik Lagi {sel}! Antam {h}/gram — Kalian Gimana?",
                f"Bro Emas Naik {sel} nih! Jadi {h}/gram — Worth It Beli?",
                f"Serius Emas Naik {sel}? Antam {h}/gram — Yuk Bahas!",
                f"Wah Emas Antam Naik {sel}! {h}/gram — Mau Beli atau Tunggu?",
                f"Eh Tau Gak? Emas Naik {sel} Hari Ini! Antam {h}/gram nih",
                f"Nabung Emas Gak? Antam Naik {sel} jadi {h}/gram hari ini!",
                f"Emas Antam {h}/gram — Naik {sel}, Gimana Strategi Kamu?",
                f"Sip! Emas Naik {sel} ke {h}/gram — Share ke Temenmu Juga!",
            ],
        },
        "Turun": {
            "formal_analitis":[
                f"Koreksi Emas Antam {sel} ke {h}/gram — Analisa Support Level",
                f"Teknikal: Emas Antam Turun {sel} ke {h}/gram — Beli atau Wait?",
                f"📉 Emas Antam Terkoreksi {sel} ke {h}/gram — Rekomendasi {tgl}",
                f"Data Koreksi: Emas Antam {h}/gram Turun {sel} — Fundamentals?",
                f"Emas Antam Melemah {sel} ke {h}/gram — Analisa {tgl}",
                f"Update: Emas Antam -{sel} Jadi {h}/gram — Momentum Akumulasi?",
                f"🟢 Emas Antam Koreksi {sel} — {h}/gram Titik Masuk Terbaik?",
                f"Harga Emas Antam {h}/gram Turun {sel} — Oversold atau Lanjut?",
            ],
            "santai_edukatif":[
                f"Emas Turun {sel} jadi {h}/gram — Tenang, Ini Waktu Nabung!",
                f"💡 Emas Antam Turun {sel}! {h}/gram — Manfaatin Momen Ini",
                f"Emas Antam {h}/gram Turun {sel} — 3 Alasan Ini Justru Bagus",
                f"Turun {sel}? Emas Antam {h}/gram Tetap Investasi Terbaik!",
                f"Eh Emas Turun {sel} lho! {h}/gram — Ini Artinya Apa buat Kamu?",
                f"Emas Antam Turun {sel} ke {h}/gram — Tips Beli Harga Murah",
                f"Santai! Turun {sel} Itu Normal — Emas Antam {h}/gram Hari Ini",
                f"Mau Beli Emas Murah? {h}/gram Turun {sel} — Yuk Simak!",
            ],
            "berita_singkat":[
                f"UPDATE: Emas Antam Turun {sel} ke {h}/gram — {tgl}",
                f"TERBARU: Emas Antam {h}/gram Koreksi {sel} Hari Ini",
                f"🟢 TURUN {sel}! Emas Antam {h}/gram — Update Resmi {tgl}",
                f"INFO {tgl}: Emas Antam Melemah {sel} ke {h}/gram",
                f"LIVE: Harga Emas Antam {h}/gram Koreksi {sel} — Cek Di Sini",
                f"TERKINI: Emas Antam -{sel} Jadi {h}/gram — Saatnya Beli?",
                f"UPDATE EMAS {tgl}: Turun {sel} ke {h}/gram — Data Lengkap",
                f"INFO HARGA: Emas Antam {h}/gram Turun {sel} dari Kemarin",
            ],
            "energik_motivatif":[
                f"🎯 EMAS TURUN {sel}!! {h}/gram — INI WAKTU BELI TERBAIK!",
                f"DISKON {sel}! Emas Antam {h}/gram — BORONG SEBELUM NAIK!",
                f"💰 HARGA MURAH! Emas Turun {sel} ke {h}/gram — BURUAN!",
                f"KESEMPATAN EMAS! Turun {sel} ke {h}/gram — Jangan Ragu!",
                f"🔥 SALE EMAS! Antam -{sel} = {h}/gram — Kapan Lagi?!",
                f"EMAS MURAH {sel}! {h}/gram — BELI SEBELUM TERLAMBAT!",
                f"WOW TURUN {sel}!! Emas Antam {h}/gram — Sinyal Kuat Beli!",
                f"ALERT MURAH! Emas -{sel} ke {h}/gram — ACTION NOW!",
            ],
            "percakapan_akrab":[
                f"Bro Emas Turun {sel}! {h}/gram — Udah Beli Belum Nih?",
                f"Guys! Emas Antam {h}/gram Turun {sel} — Mau Borong Gak?",
                f"Eh Emas Murah {sel}! Antam {h}/gram — Yuk Nabung Bareng!",
                f"Serius Emas Turun {sel}? {h}/gram — Kalian Beli Gak Nih?",
                f"Wah Emas Antam {h}/gram Turun {sel} — Worth It Banget Beli!",
                f"Emas Turun {sel} nih! Antam {h}/gram — Gimana Pendapatmu?",
                f"Nabung Emas Yuk! Antam Turun {sel} jadi {h}/gram Hari Ini",
                f"Beli Emas Sekarang! Turun {sel} ke {h}/gram — Mumpung Murah!",
            ],
        },
        "Stabil": {
            "formal_analitis":[
                f"Analisa: Emas Antam Konsolidasi di {h}/gram — Arah Selanjutnya?",
                f"Sideways! Emas Antam {h}/gram — Sinyal Teknikal & Proyeksi {tgl}",
                f"📊 Emas Antam Stagnan {h}/gram — Kapan Break Out? Analisa {tgl}",
                f"Consolidation Phase: Emas Antam {h}/gram — Beli atau Tunggu?",
                f"Emas Antam {h}/gram Flat — Analisa Fundamental & Teknikal {tgl}",
                f"Update Harga Emas Antam {h}/gram — Stabil, Menuju Tren Mana?",
                f"Harga Emas Antam {h}/gram Konsolidasi — Rekomendasi Investor",
                f"⬛ Emas Antam {h}/gram — Koreksi Dulu atau Mau Naik? Analisa",
            ],
            "santai_edukatif":[
                f"Emas Antam {h}/gram Hari Ini — Stabil, tapi Tunggu Dulu Nih!",
                f"💡 Emas Antam Stagnan di {h}/gram — Apa yang Harus Dilakukan?",
                f"Harga Emas {h}/gram Gak Bergerak — Ini Penjelasan Lengkapnya!",
                f"Emas Antam {h}/gram Masih Flat — 4 Strategi Investasi Tepat",
                f"Tenang Emas Antam {h}/gram Stabil — Yuk Belajar Cara Invest!",
                f"Emas Antam Stagnan {h}/gram — Waktu Terbaik Belajar Investasi",
                f"Eh Emas {h}/gram Stabil Nih! Buat Kamu yang Mau Mulai Invest",
                f"Emas Antam {h}/gram Flat — 3 Hal yang Perlu Kamu Persiapkan",
            ],
            "berita_singkat":[
                f"UPDATE {tgl}: Emas Antam Stabil di {h}/gram — Harga Lengkap",
                f"TERBARU: Emas Antam {h}/gram — Stagnan, Ini Data Resminya!",
                f"⬛ STABIL! Emas Antam {h}/gram — Update Resmi {tgl}",
                f"INFO HARGA {tgl}: Emas Antam {h}/gram Tidak Berubah Hari Ini",
                f"LIVE: Emas Antam {h}/gram Konsolidasi — Update Terkini {tgl}",
                f"TERKINI: Harga Emas Antam {h}/gram — Flat, Ini Penyebabnya!",
                f"INFO: Emas Antam {h}/gram Stabil — Daftar Harga Lengkap {tgl}",
                f"UPDATE EMAS {tgl}: Antam {h}/gram Stagnan — Naik atau Turun?",
            ],
            "energik_motivatif":[
                f"😲 EMAS ANTAM DIAM di {h}/gram — INI PERTANDA MENARIK!!",
                f"🤔 Kenapa Emas {h}/gram Gak Bergerak?! Ini Jawabannya!!",
                f"⚡ STAGNAN = KESEMPATAN! Emas Antam {h}/gram — Beli Sekarang!",
                f"WASPADA! Emas Antam {h}/gram Tenang — BADAI AKAN DATANG?!",
                f"🎯 EMAS ANTAM {h}/gram STAGNAN — STRATEGI PROFIT TERBAIK!",
                f"SINYAL KUAT! Emas {h}/gram Konsolidasi — MAU NAIK BESAR?!",
                f"EMAS ANTAM {h}/gram FLAT — TAPI INI JUSTRU WAKTU BELI!",
                f"⚠️ ALERT! Emas {h}/gram Tidak Bergerak — Ini Berbahaya?!",
            ],
            "percakapan_akrab":[
                f"Guys Emas Antam {h}/gram Hari Ini — Stabil, Gimana Menurutmu?",
                f"Bro, Emas Antam {h}/gram Gak Kemana-mana — Beli atau Tunggu?",
                f"Eh Emas Antam Masih {h}/gram Nih — Kalian Gimana Strateginya?",
                f"Emas Antam {h}/gram Stagnan — Yuk Diskusi di Kolom Komentar!",
                f"Serius Emas {h}/gram Flat? — Curhat Dong, Kalian Beli Gak?",
                f"Wah Emas Antam {h}/gram Masih Sama — Enak nih Buat Nabung!",
                f"Emas {h}/gram Tenang Banget — Kalian Bakal Beli Gak?",
                f"Emas Antam {h}/gram — Stagnan Bro, tapi Worth It Tetap Nabung!",
            ],
        },
    }

    pool_status = pools.get(st, pools["Stabil"])
    pool_gaya   = pool_status.get(NARASI_GAYA, list(pool_status.values())[0])
    return random.choice(pool_gaya)[:100]

def _validasi_judul(judul_raw, info, historis):
    BOCOR = ["tentu","berikut","ini dia","mari kita","baik,","oke,","siap,",
             "scriptwriter","naskah video","konten youtube"]
    if any(k in judul_raw.lower() for k in BOCOR) or len(judul_raw.strip()) < 10:
        fix = buat_judul_clickbait_lokal(info, historis)
        log(f"  -> [FIX JUDUL]: {fix}")
        return fix
    return judul_raw.strip()[:100]


# ════════════════════════════════════════════════════════════
# BAGIAN 4 — SCRAPING HARGA EMAS
# ════════════════════════════════════════════════════════════

def scrape_dan_kalkulasi_harga():
    log("[1/6] Scraping harga emas Antam dari logammulia.com...")
    try:
        resp = requests.get(
            "https://www.logammulia.com/id/harga-emas-hari-ini",
            headers={'User-Agent':'Mozilla/5.0'}, timeout=15)
        log(f"  -> HTTP status: {resp.status_code}")
        soup = BeautifulSoup(resp.text, 'html.parser')
        raw  = soup.get_text(separator=" | ", strip=True)
        log(f"  -> Raw text length: {len(raw)} chars")

        harga = 0
        for row in soup.find_all('tr'):
            cells = row.find_all(['td','th'])
            if len(cells) >= 2 and cells[0].text.strip().lower() in ('1 gr','1 gram'):
                a = re.sub(r'[^\d]','',cells[1].text)
                if a: harga = int(a); break

        if harga == 0:
            log("  -> ERROR: Gagal parse harga! Coba parse fallback...")
            # Fallback: cari pola angka besar di raw text
            matches = re.findall(r'1\.?\d{3}\.?\d{3}', raw.replace('.',''))
            if matches:
                harga = int(matches[0])
                log(f"  -> Fallback harga: {harga}")
            else:
                log("  -> FATAL: Tidak bisa parse harga sama sekali.")
                return None, None

        log(f"  -> Harga 1 gram: Rp {harga:,}".replace(",","."))

        hist     = muat_history()
        records  = hist.get("records",[])
        historis = analisa_historis(harga, records)

        kmrn = historis.get("kemarin")
        if kmrn:
            s       = kmrn["selisih"]
            status  = "Naik" if s>0 else ("Turun" if s<0 else "Stabil")
            selisih = abs(s)
        else:
            status, selisih = "Stabil", 0

        records_baru = simpan_history(harga)
        log(f"  -> Status: {status} Rp {selisih:,} | History: {len(records_baru)} hari".replace(",","."))

        for lb, d in historis.items():
            if d:
                arah = "↑" if d["naik"] else ("↓" if not d["stabil"] else "→")
                log(f"  -> {lb}: {arah} {abs(d['persen']):.1f}% dari Rp {d['harga_ref']:,}".replace(",","."))

        info = {"harga_sekarang":harga,"status":status,"selisih":selisih,
                "historis":historis,"total_record":len(records_baru)}
        konteks = "; ".join([
            f"{lb}: {'naik' if d['naik'] else ('turun' if not d['stabil'] else 'stabil')} "
            f"{abs(d['persen']):.1f}% dari Rp {d['harga_ref']:,}".replace(",",".")
            for lb,d in historis.items() if d
        ])
        return info, f"Tanggal:{datetime.now().strftime('%d %B %Y')}. Historis:{konteks}. Data:{raw[:2500]}..."

    except Exception as e:
        log(f"  -> EXCEPTION scraping: {type(e).__name__}: {e}")
        return None, None


# ════════════════════════════════════════════════════════════
# BAGIAN 5 — NARASI FALLBACK (5 GAYA BERBEDA)
# ════════════════════════════════════════════════════════════

def _buat_narasi_fallback_lokal(info, harga_skrg, status_harga, selisih_harga):
    tgl  = datetime.now().strftime("%d %B %Y")
    hari = {"Monday":"Senin","Tuesday":"Selasa","Wednesday":"Rabu",
            "Thursday":"Kamis","Friday":"Jumat",
            "Saturday":"Sabtu","Sunday":"Minggu"
            }.get(datetime.now().strftime("%A"),"")
    h    = info['harga_sekarang']
    rp   = lambda x: f"Rp {x:,}".replace(",",".")
    tabel= {
        "setengah gram":h//2,"satu gram":h,"dua gram":h*2,"tiga gram":h*3,
        "lima gram":h*5,"sepuluh gram":h*10,"dua puluh lima gram":h*25,
        "lima puluh gram":h*50,"seratus gram":h*100,
        "dua ratus lima puluh gram":h*250,"lima ratus gram":h*500,"seribu gram":h*1000,
    }
    daftar = " ".join(f"Untuk {s}, harganya {rp(v)}." for s,v in tabel.items())
    ks     = {"Naik":f"mengalami kenaikan sebesar {selisih_harga} Rupiah dari kemarin",
              "Turun":f"mengalami penurunan sebesar {selisih_harga} Rupiah dari kemarin",
              "Stabil":"terpantau stabil tidak berubah dari hari sebelumnya"
              }.get(status_harga,"terpantau stabil")
    kh = ""
    for lb, d in info.get("historis",{}).items():
        if d and abs(d["persen"]) >= 1.0:
            arah = "naik" if d["naik"] else "turun"
            nama = {"kemarin":"kemarin","7_hari":"seminggu lalu","1_bulan":"sebulan lalu",
                    "3_bulan":"tiga bulan lalu","6_bulan":"enam bulan lalu",
                    "1_tahun":"setahun lalu"}.get(lb,lb)
            kh = (f" Jika dibandingkan {nama}, harga emas telah {arah} {abs(d['persen']):.1f}% "
                  f"dari {rp(d['harga_ref'])} menjadi {rp(h)}.")
            break

    templates = {
        "formal_analitis": f"""Halo sobat {NAMA_CHANNEL}, selamat datang kembali di channel kami yang menyajikan analisa dan informasi investasi emas terkini. Pada hari {hari} tanggal {tgl} ini, kami hadir dengan update komprehensif mengenai pergerakan harga emas Antam Logam Mulia.

Berdasarkan data resmi yang kami himpun dari situs Logam Mulia, harga emas Antam untuk ukuran satu gram pada hari ini tercatat di angka {rp(h)}. Harga ini {ks}.{kh} Data ini penting sebagai acuan bagi Anda yang sedang mempertimbangkan keputusan investasi emas.

Berikut kami sajikan daftar harga lengkap emas Antam untuk seluruh ukuran yang tersedia secara resmi. {daftar} Daftar harga di atas merupakan harga jual resmi Antam yang dapat berubah sewaktu-waktu mengikuti dinamika pasar global.

Dari perspektif analisa fundamental, beberapa faktor makroekonomi saat ini berpengaruh signifikan terhadap pergerakan harga emas. Pertama, kebijakan moneter Federal Reserve Amerika Serikat tetap menjadi variabel paling dominan yang menentukan arah harga emas global. Ekspektasi pasar terhadap arah suku bunga Fed Funds Rate menjadi katalis utama pergerakan harga. Kedua, indeks dolar Amerika Serikat memiliki korelasi negatif dengan harga emas. Ketiga, situasi geopolitik global terus mendorong permintaan emas sebagai instrumen safe haven yang telah teruji ketangguhannya selama ribuan tahun. Keempat, data inflasi global yang masih di atas target bank sentral turut memberikan dukungan positif bagi harga emas sebagai instrumen lindung nilai.

Dari sisi strategi investasi, kami merekomendasikan pendekatan systematic investment plan sebagai metode yang paling efektif untuk membangun portofolio emas jangka panjang. Diversifikasi alokasi antara emas fisik batangan dan instrumen emas digital dapat menjadi pilihan yang bijaksana. Pastikan Anda membeli melalui gerai resmi Antam atau platform terpercaya untuk menghindari risiko pemalsuan. Simpan emas fisik Anda dengan aman menggunakan layanan Safe Deposit Box bank atau titipan resmi Antam.

Demikian analisa dan update harga emas Antam hari ini dari {NAMA_CHANNEL}. Jika informasi ini bermanfaat, silakan berikan like dan subscribe untuk mendukung channel kami. Aktifkan notifikasi agar Anda tidak ketinggalan update harga dan analisa emas terbaru setiap hari. Terima kasih dan salam investasi cerdas!""",

        "santai_edukatif": f"""Halo sobat {NAMA_CHANNEL}! Selamat datang lagi di channel kita yang selalu hadir kasih update harga emas Antam paling fresh setiap harinya. Hari ini hari {hari} tanggal {tgl}, dan seperti biasa kita bakal bahas bareng semua info penting seputar emas Antam.

Nah langsung aja ya, harga emas Antam resmi hari ini untuk ukuran satu gram ada di angka {rp(h)}. Harga ini {ks}.{kh} Info ini diambil langsung dari website resmi Logam Mulia, jadi bisa dipercaya dan dijadikan patokan.

Oke sekarang kita lihat daftar harga lengkapnya buat semua ukuran yang tersedia. {daftar} Nah itulah harga-harga resminya. Perlu diingat ya, harga ini bisa berubah setiap saat mengikuti kondisi pasar, jadi selalu cek sebelum beli.

Sekarang yuk kita pahami bersama kenapa harga emas bisa naik turun. Pertama, emas itu harganya sangat dipengaruhi oleh kebijakan bank sentral Amerika, terutama soal suku bunga. Kalau suku bunga naik, biasanya emas agak tertekan karena orang lebih pilih aset berbunga. Sebaliknya kalau suku bunga turun atau ada ekspektasi pemangkasan, emas biasanya langsung menguat. Kedua, kondisi global seperti perang atau krisis ekonomi selalu bikin orang lari ke emas sebagai tempat berlindung yang paling aman. Ketiga, nilai tukar Rupiah terhadap Dolar sangat menentukan harga emas dalam Rupiah.

Buat teman-teman yang mau mulai investasi emas, ada beberapa tips simpel yang bisa langsung dipraktekkan. Satu, mulai dari yang kecil dulu. Dua, beli secara rutin setiap bulan berapapun jumlahnya. Tiga, jangan panik kalau harga turun, justru itu saat bagus untuk menambah koleksi. Empat, simpan emas dengan aman dan pastikan beli di tempat terpercaya.

Oke itu tadi update lengkap dari {NAMA_CHANNEL} hari ini! Kalau ada pertanyaan, langsung tulis di kolom komentar ya. Jangan lupa subscribe dan nyalakan lonceng notifikasinya. Sampai jumpa di video berikutnya, salam investasi!""",

        "berita_singkat": f"""Halo sobat {NAMA_CHANNEL}, berikut update harga emas Antam Logam Mulia hari {hari} tanggal {tgl}.

Harga emas Antam resmi hari ini untuk ukuran satu gram adalah {rp(h)}. Harga ini {ks}.{kh}

Daftar harga lengkap emas Antam semua ukuran hari ini sebagai berikut. {daftar}

Kondisi pasar emas global hari ini dipengaruhi oleh beberapa faktor utama. Pertama, arah kebijakan suku bunga Federal Reserve Amerika Serikat yang masih menjadi perhatian pelaku pasar global. Kedua, pergerakan indeks dolar AS yang berkorelasi negatif dengan harga emas dunia. Ketiga, sentimen risiko global terkait situasi geopolitik di berbagai kawasan yang mendorong permintaan safe haven. Data inflasi dari negara-negara ekonomi utama juga menjadi pertimbangan investor dalam menentukan porsi alokasi emas.

Tips investasi emas hari ini: beli rutin setiap bulan, manfaatkan harga turun sebagai momentum akumulasi, dan selalu beli melalui gerai resmi Antam. Emas batangan lebih efisien dibanding perhiasan karena tidak ada ongkos pembuatan yang mahal.

Itulah update harga emas Antam hari ini dari {NAMA_CHANNEL}. Subscribe dan aktifkan notifikasi untuk update harga emas setiap hari. Terima kasih sudah menonton!""",

        "energik_motivatif": f"""Halo halo halo sobat {NAMA_CHANNEL}!! Selamat datang kembali di channel paling update soal harga emas Antam di seluruh Indonesia!! Hari ini hari {hari} tanggal {tgl}, dan kita punya berita penting banget buat kamu semua!!

Langsung gas ya!! Harga emas Antam resmi hari ini untuk ukuran satu gram adalah {rp(h)}!! Harga ini {ks}!!{kh} Ini bukan informasi sembarangan, ini data RESMI langsung dari Logam Mulia!!

Sekarang simak baik-baik harga lengkap semua ukuran emas Antam hari ini!! {daftar} Catat baik-baik angka-angka ini!!

Guys, ada beberapa hal penting banget yang harus kamu ketahui soal kondisi pasar emas saat ini!! Pertama, Federal Reserve Amerika Serikat sedang dalam sorotan tajam para investor global!! Setiap keputusan soal suku bunga bisa langsung mempengaruhi harga emas secara signifikan!! Kedua, ketidakpastian geopolitik global masih tinggi dan ini justru MENGUNTUNGKAN kamu yang sudah pegang emas!! Emas adalah satu-satunya aset yang terbukti bertahan di kondisi krisis apapun!! Ketiga, pelemahan mata uang mendorong kenaikan harga emas dalam jangka panjang!!

PENTING BANGET!! Buat kamu yang belum punya emas, mulai dari satu gram pun tidak masalah!! Yang penting MULAI SEKARANG!! Beli rutin setiap bulan, tidak perlu banyak yang penting KONSISTEN!! Emas adalah investasi yang sudah teruji ribuan tahun dan tidak akan pernah bernilai nol!!

Itu tadi informasi super penting dari {NAMA_CHANNEL}!! Kalau video ini bermanfaat, LIKE sekarang, SUBSCRIBE sekarang, dan SHARE ke semua orang yang kamu sayangi!! Aktifkan notifikasi biar kamu selalu yang pertama dapat update!! Sampai jumpa dan SALAM KAYA RAYA!!""",

        "percakapan_akrab": f"""Hei hei hei, apa kabar semua? Selamat datang kembali di {NAMA_CHANNEL}! Hari ini hari {hari} tanggal {tgl}, yuk langsung kita bahas bareng harga emas Antam hari ini!

Jadi gini guys, harga emas Antam buat ukuran satu gram hari ini ada di angka {rp(h)}. Nah harga ini {ks}.{kh} Infonya dari website resmi Logam Mulia ya, jadi bisa dipercaya kok!

Oke buat yang mau tau harga lengkap semua ukuran, ini dia guys! {daftar} Gimana, udah catat belum? Harga bisa berubah lho, jadi pastiin selalu cek sebelum pergi ke gerai!

Nah aku mau kasih tau juga nih kenapa emas itu selalu menarik buat dibahas. Pertama, emas itu beneran gak ada matinya sebagai investasi. Selama ribuan tahun manusia udah pegang emas dan sampai sekarang masih tetap bernilai. Kedua, kondisi global yang lagi gak pasti justru bikin emas makin bersinar, karena semua orang lari ke emas kalau situasi gak aman. Ketiga, emas itu gampang dicairin kalau butuh dana darurat. Keempat, mulai belinya bisa dari ukuran kecil, jadi beneran bisa dijangkau semua kalangan.

Buat kalian yang udah lama invest emas, good job ya! Buat yang baru mau mulai, jangan takut, mulai aja dulu dari yang kecil. Beli tiap bulan rutin, gak usah dipusingin naik turunnya harga jangka pendek!

Oke segitu dulu update dari aku hari ini! Kalau ada yang mau diskusi, yuk tulis di kolom komentar! Jangan lupa subscribe ya biar kita bisa ketemu terus tiap hari! Bye bye dan sampai jumpa besok!""",
    }

    return templates.get(NARASI_GAYA, templates["formal_analitis"]).strip()


# ════════════════════════════════════════════════════════════
# BAGIAN 6 — NARASI & JUDUL VIA GEMINI
# ════════════════════════════════════════════════════════════

def buat_narasi_dan_judul(info, data_harga):
    log("[2/6] Membuat narasi dan judul...")
    status_harga  = info['status']
    selisih_harga = f"{info['selisih']:,}".replace(",",".")
    harga_skrg    = f"{info['harga_sekarang']:,}".replace(",",".")
    historis      = info.get("historis",{})

    judul = buat_judul_clickbait_lokal(info, historis)
    log(f"  -> Judul lokal: {judul}")

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
        "formal_analitis":  "profesional dan analitis seperti analis keuangan senior, gunakan istilah investasi",
        "santai_edukatif":  "santai tapi informatif, bahasa sehari-hari yang mudah dipahami, edukatif",
        "berita_singkat":   "singkat padat jelas seperti reporter berita profesional, to the point",
        "energik_motivatif":"sangat energik dan semangat, banyak tanda seru, membakar semangat penonton",
        "percakapan_akrab": "akrab seperti ngobrol dengan teman dekat, casual, gunakan kata guys bro dll",
    }
    gaya_desc = GAYA_DESC.get(NARASI_GAYA, GAYA_DESC["formal_analitis"])

    prompt = f"""Kamu adalah scriptwriter YouTube profesional.
Gaya narasi WAJIB: {gaya_desc}
Channel: {NAMA_CHANNEL}

BARIS PERTAMA HARUS PERSIS: "Halo sobat {NAMA_CHANNEL}," — tidak boleh ada teks apapun sebelumnya.

DATA HARI INI:
- Harga 1 gram: Rp {harga_skrg}
- Status: {status_harga} Rp {selisih_harga} vs kemarin
- Historis: {konteks}
- Data Antam: {data_harga[:2000]}

STRUKTUR (900-1000 KATA, konsisten gaya {NARASI_GAYA}):
1. Pembuka (100 kata): Sapa penonton, umumkan harga, status harga hari ini
2. Daftar harga (200 kata): Semua ukuran 0.5g hingga 1000g ditulis lengkap
3. Analisa & konteks global (300 kata): Bahas historis + faktor ekonomi global
4. Edukasi & penutup (300 kata): Tips investasi emas, ajakan subscribe {NAMA_CHANNEL}

ATURAN KERAS:
- MULAI LANGSUNG "Halo sobat {NAMA_CHANNEL}," tanpa kata pengantar apapun
- Semua angka ditulis dengan HURUF
- Paragraf narasi murni, TANPA bullet, TANPA nomor, TANPA simbol markdown
- Konsisten gaya {NARASI_GAYA} dari awal sampai akhir"""

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
                log(f"  -> {model_name} attempt {attempt+1}...")
                resp = requests.post(url_api, json=payload, timeout=90)
                if resp.status_code == 429:
                    t = int(resp.headers.get('Retry-After',(2**attempt)*10))
                    log(f"  -> Rate limit 429. Tunggu {t}s...")
                    time.sleep(t)
                    continue
                if resp.status_code != 200:
                    log(f"  -> HTTP {resp.status_code}: {resp.text[:200]}")
                    break
                resp.raise_for_status()
                script_raw = resp.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                baris, baru, skip = script_raw.split('\n'), [], True
                for idx, b in enumerate(baris):
                    bl = b.lower().strip()
                    if skip:
                        if bl.startswith("halo sobat"):
                            skip = False; baru.append(b)
                        elif idx > 4:
                            skip = False; baru.append(b)
                    elif not (bl.startswith("[judul]") or bl.startswith("[script]")):
                        baru.append(b)
                script = '\n'.join(baru).strip() or script_raw
                log(f"  -> ✅ Gemini OK ({len(script.split())} kata) model: {model_name}")
                judul = _validasi_judul(judul, info, historis)
                return judul, script
            except Exception as e:
                if "429" not in str(e):
                    log(f"  -> Exception {model_name}: {type(e).__name__}: {e}")
                    break
                time.sleep((2**attempt)*10)
        log(f"  -> {model_name} semua attempt gagal.")

    if not GEMINI_API_KEY:
        log("  -> GEMINI_API_KEY kosong! Set di GitHub Secrets.")

    log("  -> [FALLBACK] Menggunakan narasi template lokal...")
    narasi = _buat_narasi_fallback_lokal(info, harga_skrg, status_harga, selisih_harga)
    judul  = _validasi_judul(judul, info, historis)
    return judul, narasi


# ════════════════════════════════════════════════════════════
# BAGIAN 7 — GENERATE SUARA
# ════════════════════════════════════════════════════════════

def buat_suara(teks, output_audio):
    log(f"[3/6] Generate suara — voice:{VOICE} rate:{VOICE_RATE}...")
    teks_bersih = re.sub(r'\[.*?\]|\(.*?\)|\*.*?\*','',teks).strip()
    log(f"  -> Panjang teks: {len(teks_bersih)} karakter")

    cmd = [sys.executable,'-m','edge_tts',
           '--voice', VOICE, '--rate', VOICE_RATE,
           '--text', teks_bersih, '--write-media', output_audio]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log(f"  -> edge-tts stderr: {result.stderr[:300]}")
        raise RuntimeError(f"edge-tts gagal: {result.stderr[:200]}")

    if not os.path.exists(output_audio) or os.path.getsize(output_audio) < 1000:
        raise FileNotFoundError("File audio tidak terbuat atau terlalu kecil!")

    hasil = subprocess.run(
        ['ffprobe','-v','error','-show_entries','format=duration',
         '-of','default=noprint_wrappers=1:nokey=1',output_audio],
        capture_output=True, text=True)
    durasi = float(hasil.stdout.strip())
    log(f"  -> ✅ Audio OK: {durasi:.0f}s ({durasi/60:.1f} menit) — {os.path.getsize(output_audio)//1024} KB")
    if durasi < 30:
        raise ValueError(f"Audio terlalu pendek ({durasi:.1f}s)! Narasi mungkin terlalu singkat.")
    return durasi

# ════════════════════════════════════════════════════════════
# BAGIAN 8 — KEN BURNS EFFECT
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
        name = "ZoomIn_Center"
    elif mode == 2:
        z = "if(eq(on,1),1.15,max(zoom-0.0004,1.0))"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
        name = "ZoomOut_Center"
    elif mode == 3:
        z = "if(eq(on,1),1.02,min(zoom+0.0003,1.15))"
        x = f"(iw-ow)*(on/{d_frames})*0.6"
        y = "ih/2-(ih/zoom/2)"
        name = "PanLeft_Right"
    elif mode == 4:
        z = "if(eq(on,1),1.02,min(zoom+0.0003,1.15))"
        x = f"(iw-ow)*(1-on/{d_frames})*0.6"
        y = "ih/2-(ih/zoom/2)"
        name = "PanRight_Left"
    elif mode == 5:
        z = "if(eq(on,1),1.02,min(zoom+0.0003,1.15))"
        x = "iw/2-(iw/zoom/2)"
        y = f"(ih-oh)*(on/{d_frames})*0.6"
        name = "PanTop_Bottom"
    else:
        z = "if(eq(on,1),1.02,min(zoom+0.0003,1.15))"
        x = "iw/2-(iw/zoom/2)"
        y = f"(ih-oh)*(1-on/{d_frames})*0.6"
        name = "PanBottom_Top"

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
        f"fade=t=in:st=0:d=0.5,"
        f"fade=t=out:st={dur-0.5:.1f}:d=0.5"
    )
    return vf, name


def escape_ffmpeg_path(path):
    return path.replace('\\','/').replace(':','\\:')


def siapkan_font_lokal():
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    font_lokal = os.path.abspath("font_temp.ttf")
    for path in font_paths:
        if os.path.exists(path):
            try:
                shutil.copy(path, font_lokal)
                log(f"  -> Font: {path}")
                return font_lokal
            except: continue
    log("  -> WARNING: Font tidak ditemukan, watermark dinonaktifkan.")
    return None


# ════════════════════════════════════════════════════════════
# BAGIAN 9 — RENDER KLIP GAMBAR (KEN BURNS)
# ════════════════════════════════════════════════════════════

def _render_klip_gambar(args):
    i, img_path, font_sistem, output_klip = args
    durasi_klip = random.choice([8, 10, 12])
    vf, mode    = _get_ken_burns_filter(durasi_klip)

    if font_sistem:
        fe   = escape_ffmpeg_path(font_sistem)
        x, y = random.choice([("30","30"),("w-tw-30","30"),
                               ("30","h-th-30"),("w-tw-30","h-th-30")])
        ch_esc = NAMA_CHANNEL.replace("'","\\'")
        vf += f",drawtext=fontfile='{fe}':text='{ch_esc}':fontcolor=white@0.5:fontsize=26:x={x}:y={y}"

    cmd = [
        'ffmpeg','-y',
        '-loop','1','-framerate',str(FPS),'-i', img_path,
        '-f','lavfi','-i','anullsrc=channel_layout=stereo:sample_rate=44100',
        '-vf', vf,
        '-map','0:v','-map','1:a',
        '-c:v','libx264','-preset','faster','-pix_fmt','yuv420p','-crf','23',
        '-c:a','aac',
        '-t', str(durasi_klip),
        output_klip
    ]
    with open(FFMPEG_LOG,'a',encoding='utf-8') as log_f:
        log_f.write(f"\n=== KLIP-IMG {i} [{mode}]: {os.path.basename(img_path)} ===\n")
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=log_f)

    ok = (result.returncode == 0
          and os.path.exists(output_klip)
          and os.path.getsize(output_klip) > 10000)
    if not ok:
        log(f"  -> [GAGAL] Klip-IMG {i} ({os.path.basename(img_path)})")
        return None
    return i, output_klip, durasi_klip


# ════════════════════════════════════════════════════════════
# BAGIAN 10 — RENDER KLIP VIDEO BANK (PEXELS VIDEO)
# ════════════════════════════════════════════════════════════

def _render_klip_video(args):
    i, vid_path, font_sistem, output_klip = args
    durasi_klip = random.choice([8, 10, 12])

    # Cek durasi video sumber
    try:
        res     = subprocess.run(
            ['ffprobe','-v','error','-show_entries','format=duration',
             '-of','default=noprint_wrappers=1:nokey=1', vid_path],
            capture_output=True, text=True, timeout=10)
        dur_src = float(res.stdout.strip())
    except:
        dur_src = 30.0

    # Pilih titik mulai random agar tiap render beda
    max_start = max(0, dur_src - durasi_klip - 1)
    start     = round(random.uniform(0, max_start), 1) if max_start > 0 else 0.0

    vf = (f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
          f"force_original_aspect_ratio=decrease,"
          f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
          f"fade=t=in:st=0:d=0.5,"
          f"fade=t=out:st={durasi_klip-0.5:.1f}:d=0.5")

    if font_sistem:
        fe   = escape_ffmpeg_path(font_sistem)
        x, y = random.choice([("30","30"),("w-tw-30","30"),
                               ("30","h-th-30"),("w-tw-30","h-th-30")])
        ch_esc = NAMA_CHANNEL.replace("'","\\'")
        vf += f",drawtext=fontfile='{fe}':text='{ch_esc}':fontcolor=white@0.5:fontsize=26:x={x}:y={y}"

    cmd = [
        'ffmpeg','-y',
        '-ss', str(start),
        '-i', vid_path,
        '-t', str(durasi_klip),
        '-vf', vf,
        '-c:v','libx264','-preset','faster','-pix_fmt','yuv420p','-crf','23',
        '-c:a','aac','-ar','44100','-ac','2',
        output_klip
    ]
    with open(FFMPEG_LOG,'a',encoding='utf-8') as log_f:
        log_f.write(f"\n=== KLIP-VID {i}: {os.path.basename(vid_path)} (ss={start}) ===\n")
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=log_f)

    ok = (result.returncode == 0
          and os.path.exists(output_klip)
          and os.path.getsize(output_klip) > 10000)
    if not ok:
        log(f"  -> [GAGAL] Klip-VID {i} ({os.path.basename(vid_path)})")
        return None
    return i, output_klip, durasi_klip


# ════════════════════════════════════════════════════════════
# BAGIAN 11 — PROSES SEMUA KLIP (PARALEL)
# ════════════════════════════════════════════════════════════

def proses_semua_klip(durasi_total_detik):
    log(f"[4/6] Menyiapkan klip visual (target durasi: {durasi_total_detik:.0f}s)...")
    os.makedirs("temp_clips", exist_ok=True)

    gambar_list = _list_gambar()
    video_list  = _list_video_bank()

    log(f"  -> Tersedia: {len(gambar_list)} gambar, {len(video_list)} video di bank")

    if not gambar_list and not video_list:
        log("  -> FATAL: Tidak ada gambar maupun video di bank!")
        log(f"  -> Pastikan PEXELS_API_KEY valid dan folder {FOLDER_GAMBAR}/ atau {FOLDER_VIDEO_BANK}/ ada.")
        return None

    jumlah_klip_target = int(durasi_total_detik / 10) + 3
    log(f"  -> Target klip: {jumlah_klip_target}")

    # Proporsi: 60% video bank, 40% gambar (jika keduanya ada)
    tasks   = []
    counter = 0

    if video_list and gambar_list:
        n_video = int(jumlah_klip_target * 0.6)
        n_gambar= jumlah_klip_target - n_video
    elif video_list:
        n_video = jumlah_klip_target
        n_gambar = 0
    else:
        n_video = 0
        n_gambar = jumlah_klip_target

    font_sistem = siapkan_font_lokal()

    # Duplikasi list jika kurang
    def repeat_list(lst, n):
        result = []
        while len(result) < n:
            result.extend(lst)
        return result[:n]

    if n_video > 0 and video_list:
        vids = repeat_list(random.sample(video_list, min(len(video_list), n_video)), n_video)
        random.shuffle(vids)
        for vid in vids:
            out = os.path.abspath(f"temp_clips/klip_{counter:04d}.mp4")
            tasks.append(('video', counter, vid, font_sistem, out))
            counter += 1

    if n_gambar > 0 and gambar_list:
        imgs = repeat_list(random.sample(gambar_list, min(len(gambar_list), n_gambar)), n_gambar)
        random.shuffle(imgs)
        for img in imgs:
            out = os.path.abspath(f"temp_clips/klip_{counter:04d}.mp4")
            tasks.append(('gambar', counter, img, font_sistem, out))
            counter += 1

    # Acak urutan agar video & gambar bercampur
    random.shuffle(tasks)

    log(f"  -> Render {len(tasks)} klip paralel ({min(3, os.cpu_count() or 2)} thread)...")
    klip_berhasil = {}
    max_workers   = min(3, os.cpu_count() or 2)

    def run_task(task):
        tipe = task[0]
        if tipe == 'video':
            _, i, path, font, out = task
            return _render_klip_video((i, path, font, out))
        else:
            _, i, path, font, out = task
            return _render_klip_gambar((i, path, font, out))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(run_task, t): t[1] for t in tasks}
        for future in as_completed(futures):
            hasil = future.result()
            if hasil:
                idx, path, dur = hasil
                klip_berhasil[idx] = (path, dur)
                print(f"  -> {len(klip_berhasil)}/{len(tasks)} klip selesai", end='\r', flush=True)
    print()

    log(f"  -> {len(klip_berhasil)}/{len(tasks)} klip berhasil")

    if not klip_berhasil:
        log(f"  -> FATAL: Semua klip gagal! Cek {FFMPEG_LOG} untuk detail error.")
        return None

    # Tulis concat list — urutan berdasarkan index
    list_txt = os.path.abspath('concat_videos.txt')
    with open(list_txt,'w',encoding='utf-8') as f:
        for idx in sorted(klip_berhasil.keys()):
            path_aman = klip_berhasil[idx][0].replace('\\','/')
            f.write(f"file '{path_aman}'\n")

    total_dur_klip = sum(d for _, d in klip_berhasil.values())
    log(f"  -> Total durasi klip: {total_dur_klip:.0f}s (audio: {durasi_total_detik:.0f}s)")
    return list_txt


# ════════════════════════════════════════════════════════════
# BAGIAN 12 — RENDER VIDEO FINAL (FIX: re-encode, bukan copy)
# ════════════════════════════════════════════════════════════

def render_video_final(file_list, audio, output, durasi):
    log(f"[5/6] Render video final → {output}...")

    # Verifikasi concat file tidak kosong
    with open(file_list, 'r') as f:
        lines = [l.strip() for l in f if l.strip()]
    log(f"  -> Concat list: {len(lines)} entri")
    if not lines:
        log("  -> ERROR: Concat list kosong!")
        return False

    # Cek semua file di concat ada dan valid
    valid = 0
    for line in lines:
        path = line.replace("file '","").replace("'","")
        if os.path.exists(path) and os.path.getsize(path) > 10000:
            valid += 1
        else:
            log(f"  -> WARNING: File tidak valid: {path}")
    log(f"  -> File valid: {valid}/{len(lines)}")

    if valid == 0:
        log("  -> FATAL: Tidak ada klip valid sama sekali!")
        return False

    # Re-encode (BUKAN copy) agar compatible
    cmd = [
        'ffmpeg','-y',
        '-f','concat','-safe','0','-i', file_list,
        '-i', audio,
        '-map','0:v',
        '-map','1:a',
        '-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p',
        '-c:a','aac','-b:a','192k',
        '-t', str(int(durasi) + 2),
        '-movflags','+faststart',
        output
    ]
    log(f"  -> Menjalankan FFmpeg render final...")
    with open(FFMPEG_LOG,'a',encoding='utf-8') as log_f:
        log_f.write("\n=== RENDER FINAL ===\n")
        log_f.write(' '.join(cmd) + '\n')
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=log_f)

    log(f"  -> FFmpeg return code: {result.returncode}")

    if result.returncode != 0:
        log(f"  -> ERROR render final! Buka {FFMPEG_LOG} untuk detail.")
        # Tampilkan 20 baris terakhir log untuk debug
        try:
            with open(FFMPEG_LOG,'r',encoding='utf-8') as f:
                lines_log = f.readlines()
            log("  -> 20 baris terakhir ffmpeg_log.txt:")
            for l in lines_log[-20:]:
                print(f"     {l.rstrip()}", flush=True)
        except: pass
        return False

    if not os.path.exists(output):
        log(f"  -> ERROR: File output tidak terbuat!")
        return False

    ukuran = os.path.getsize(output)
    log(f"  -> ✅ Video OK: {ukuran//1024//1024} MB ({ukuran:,} bytes)".replace(",","."))

    if ukuran < 5 * 1024 * 1024:
        log(f"  -> WARNING: Ukuran video sangat kecil ({ukuran//1024} KB)! Mungkin ada masalah.")

    return True




# ════════════════════════════════════════════════════════════
# BAGIAN 13 — BUAT THUMBNAIL PROFESIONAL v2.0
# ════════════════════════════════════════════════════════════

def buat_thumbnail(info, judul, output_path="thumbnail.jpg"):
    log("[+] Membuat thumbnail...")
    TEMPLATE_MAP = {
        1: _thumb_template_bold_left,        # Harga besar kiri, foto kanan
        2: _thumb_template_center_split,     # Split 50/50 dengan diagonal
        3: _thumb_template_dark_minimal,     # Minimalis gelap, teks tengah
        4: _thumb_template_neon_energy,      # Neon glow, energik
        5: _thumb_template_warm_card,        # Kartu hangat bergaya magazine
    }
    fn = TEMPLATE_MAP.get(CHANNEL_ID, _thumb_template_bold_left)
    return fn(info, judul, output_path)


# ══════════════════════════════════════════════════
# TEMPLATE 1 — Bold Left (Sobat Antam)
# Layout: Bar aksen | Harga besar kiri | Foto blur kanan
# Warna: Merah-Emas, font besar aggressive
# ══════════════════════════════════════════════════
def _thumb_template_bold_left(info, judul, output_path):
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    W, H   = 1280, 720
    sk     = SKEMA_AKTIF.get(info['status'], SKEMA_AKTIF['Stabil'])
    img    = _buat_bg_foto_blur(W, H, kanan_saja=True, brightness=0.3)
    draw   = ImageDraw.Draw(img)

    # Panel kiri solid gelap
    panel = Image.new('RGBA', (W, H), (0,0,0,0))
    pd    = ImageDraw.Draw(panel)
    pd.rectangle([0, 0, W//2+100, H], fill=(10, 5, 0, 230))
    img   = Image.alpha_composite(img.convert('RGBA'), panel).convert('RGB')
    draw  = ImageDraw.Draw(img)

    # Accent bar kiri TEBAL
    for x in range(22):
        draw.line([(x, 0), (x, H)], fill=sk["aksen"])

    fp   = _font_path()
    rp   = lambda x: f"Rp {x:,}".replace(",",".")
    h    = info['harga_sekarang']
    st   = info['status']

    # Badge naik/turun
    bw, bh = 240, 64
    _draw_rounded_rect_solid(draw, 28, 28, 28+bw, 28+bh, 16, sk["badge"])
    _draw_rounded_rect_solid(draw, 28, 28, 28+bw, 28+bh, 16, None,
                              outline=sk["aksen"], width=3)
    draw.text((46, 40), sk["icon"], font=_get_font(fp, 32), fill=(255,255,255))

    # "Rp" kecil
    draw.text((28, 110), "Rp", font=_get_font(fp, 46), fill=sk["sub"])
    # Harga BESAR
    _text_stroke(draw, 28, 148, rp(h).replace("Rp ",""),
                 _get_font(fp, 108), sk["teks"], stroke=4)
    # /gram
    draw.text((32, 268), "/ gram  ·  Antam", font=_get_font(fp, 28), fill=sk["sub"])

    # Pill selisih
    sel = info['selisih']
    if sel > 0:
        s_col = (80,255,120) if st=="Naik" else (255,100,100)
        _draw_rounded_rect_solid(draw, 28, 308, 310, 360, 26,
                                  (s_col[0]//5, s_col[1]//5, s_col[2]//5))
        _draw_rounded_rect_solid(draw, 28, 308, 310, 360, 26,
                                  None, outline=s_col, width=2)
        arah = "▲" if st=="Naik" else "▼"
        draw.text((48, 316), f"{arah} {rp(sel)}", font=_get_font(fp,34), fill=s_col)

    # Judul 2 baris
    jb = _wrap_text(re.sub(r'[^\w\s\-\.,!?%]','', judul), 24)
    _text_stroke(draw, 28, 390, jb[0] if jb else "", _get_font(fp, 42), (255,255,255), 2)
    if len(jb)>1:
        draw.text((28, 440), jb[1], font=_get_font(fp, 34), fill=sk["sub"])

    # Tanggal + channel
    draw.text((28, H-52), NAMA_CHANNEL, font=_get_font(fp, 26), fill=sk["aksen"])
    draw.text((28, H-24), datetime.now().strftime("%d %B %Y"),
              font=_get_font(fp, 20), fill=(160,160,160))

    # Panel kanan: statistik historis
    _draw_historis_panel(draw, img, info, fp, sk,
                         px=W//2+120, py=30, pw=W//2-140, ph=H-60)

    draw.rectangle([0,0,W-1,H-1], outline=sk["aksen"], width=5)
    img.save(output_path, "JPEG", quality=95)
    log(f"  -> ✅ Thumbnail T1 saved: {output_path}")
    return output_path


# ══════════════════════════════════════════════════
# TEMPLATE 2 — Center Split Diagonal (Update Emas Harian)
# Layout: Diagonal slash, kiri=harga, kanan=grafik mini
# Warna: Biru-Perak, clean modern
# ══════════════════════════════════════════════════
def _thumb_template_center_split(info, judul, output_path):
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    W, H   = 1280, 720
    sk     = SKEMA_AKTIF.get(info['status'], SKEMA_AKTIF['Stabil'])
    img    = _buat_bg_foto_blur(W, H, kanan_saja=False, brightness=0.2)
    draw   = ImageDraw.Draw(img)

    # Overlay full gelap dengan tint warna channel
    r,g,b  = sk["bg_grad_atas"] if "bg_grad_atas" in sk else (0,20,60)
    overlay= Image.new('RGBA', (W,H), (r,g,b,200))
    img    = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    draw   = ImageDraw.Draw(img)

    fp  = _font_path()
    h   = info['harga_sekarang']
    st  = info['status']
    rp  = lambda x: f"Rp {x:,}".replace(",",".")

    # ── Diagonal slash putih/aksen ──
    slash_pts = [(W//2-60, 0), (W//2+60, 0), (W//2-20, H), (W//2-140, H)]
    draw.polygon(slash_pts, fill=sk["aksen"])

    # ── Sisi KIRI: Harga ──
    # Header channel
    draw.text((30, 28), NAMA_CHANNEL.upper(),
              font=_get_font(fp, 24), fill=sk["aksen"])
    draw.line([(30, 60), (W//2-80, 60)], fill=sk["aksen"], width=2)

    # Badge
    bw, bh = 220, 56
    _draw_rounded_rect_solid(draw, 30, 75, 30+bw, 75+bh, 14, sk["badge"])
    draw.text((50, 86), sk["icon"], font=_get_font(fp, 28), fill=(255,255,255))

    # Harga besar
    draw.text((30, 145), "Harga Emas", font=_get_font(fp, 30), fill=(180,200,220))
    _text_stroke(draw, 30, 180, rp(h), _get_font(fp, 88), sk["teks"], stroke=3)
    draw.text((30, 278), "/ gram  ·  Antam", font=_get_font(fp, 26), fill=sk["sub"])

    # Selisih pill
    sel = info['selisih']
    if sel > 0:
        s_col = (80,255,150) if st=="Naik" else (255,110,110)
        arah  = "▲" if st=="Naik" else "▼"
        draw.text((30, 316), f"{arah}  {rp(sel)} dari kemarin",
                  font=_get_font(fp, 30), fill=s_col)

    # Judul bawah
    jb = _wrap_text(re.sub(r'[^\w\s\-\.,!?%]','', judul), 26)
    y_j = 380
    for idx, b in enumerate(jb[:2]):
        f_sz = 38 if idx==0 else 32
        col  = (255,255,255) if idx==0 else (180,200,220)
        _text_stroke(draw, 30, y_j, b, _get_font(fp, f_sz), col, 1)
        y_j += f_sz + 10

    # ── Sisi KANAN: Mini bar chart historis ──
    cx = W//2 + 90
    draw.text((cx, 28), "Perubahan", font=_get_font(fp, 28), fill=(200,220,255))
    draw.text((cx, 60), "Harga Emas", font=_get_font(fp, 28), fill=sk["aksen"])
    draw.line([(cx, 96), (W-30, 96)], fill=sk["aksen"], width=2)

    historis = info.get("historis",{})
    lbl_map  = [("kemarin","1H"),("7_hari","7H"),("1_bulan","1B"),
                ("3_bulan","3B"),("6_bulan","6B"),("1_tahun","1T")]

    bar_y = 110
    bar_max_w = W - cx - 50
    # Temukan max persen untuk normalisasi bar
    pcts = [abs(historis[lb]["persen"]) for lb,_ in lbl_map if historis.get(lb)]
    max_pct = max(pcts) if pcts else 1.0

    for lb, nama in lbl_map:
        d = historis.get(lb)
        if not d: continue
        pct   = d["persen"]
        warna = (80,220,120) if d["naik"] else ((255,100,100) if not d["stabil"] else (150,150,200))
        bar_w = int(abs(pct) / max_pct * (bar_max_w * 0.75)) + 20

        # Label
        draw.text((cx, bar_y+4), nama+":", font=_get_font(fp, 22), fill=(180,200,240))
        # Bar
        _draw_rounded_rect_solid(draw, cx+65, bar_y+2,
                                  cx+65+bar_w, bar_y+32, 8, warna)
        # Persen
        arah = "▲" if d["naik"] else ("▼" if not d["stabil"] else "→")
        draw.text((cx+65+bar_w+8, bar_y+4),
                  f"{arah}{abs(pct):.1f}%", font=_get_font(fp, 20), fill=warna)
        bar_y += 46
        if bar_y > H - 80: break

    # Footer
    draw.text((cx, H-36), datetime.now().strftime("%d %B %Y"),
              font=_get_font(fp, 22), fill=(140,160,200))
    draw.rectangle([0,0,W-1,H-1], outline=sk["aksen"], width=4)
    img.save(output_path, "JPEG", quality=95)
    log(f"  -> ✅ Thumbnail T2 saved: {output_path}")
    return output_path


# ══════════════════════════════════════════════════
# TEMPLATE 3 — Dark Minimal (Info Logam Mulia)
# Layout: Teks tengah, background sangat gelap, garis tipis
# Warna: Hijau-Platinum, clean newspaper style
# ══════════════════════════════════════════════════
def _thumb_template_dark_minimal(info, judul, output_path):
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    W, H   = 1280, 720
    sk     = SKEMA_AKTIF.get(info['status'], SKEMA_AKTIF['Stabil'])
    img    = Image.new('RGB', (W, H), (8, 12, 10))
    draw   = ImageDraw.Draw(img)

    fp = _font_path()
    h  = info['harga_sekarang']
    st = info['status']
    rp = lambda x: f"Rp {x:,}".replace(",",".")

    # Grid garis tipis latar
    for x in range(0, W, 80):
        draw.line([(x,0),(x,H)], fill=(20,35,25), width=1)
    for y in range(0, H, 80):
        draw.line([(0,y),(W,y)], fill=(20,35,25), width=1)

    # Foto blur kecil di pojok kanan bawah
    gb = _list_gambar()
    if gb:
        try:
            bg = Image.open(random.choice(gb)).convert('RGB')
            bg = bg.resize((500, 280), Image.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(6))
            from PIL import ImageEnhance
            bg = ImageEnhance.Brightness(bg).enhance(0.3)
            mask = Image.new('L', (500,280), 0)
            md   = ImageDraw.Draw(mask)
            # Gradient alpha dari kiri ke kanan
            for x in range(500):
                a = int(min(255, x * 0.5))
                md.line([(x,0),(x,280)], fill=a)
            img.paste(bg, (W-500, H-280), mask)
            draw = ImageDraw.Draw(img)
        except: pass

    # Top bar aksen
    draw.rectangle([0, 0, W, 6], fill=sk["aksen"])
    draw.rectangle([0, H-6, W, H], fill=sk["aksen"])

    # Nama channel top
    draw.text((40, 20), NAMA_CHANNEL.upper(),
              font=_get_font(fp, 22), fill=sk["aksen"])
    draw.text((W-240, 20), datetime.now().strftime("%d %b %Y"),
              font=_get_font(fp, 22), fill=(100,140,110))

    # Badge status
    _draw_rounded_rect_solid(draw, 40, 65, 260, 120, 12, sk["badge"])
    draw.text((58, 76), sk["icon"], font=_get_font(fp, 30), fill=(255,255,255))

    # Harga teks besar centered-left
    draw.text((40, 135), "HARGA EMAS ANTAM", font=_get_font(fp, 28),
              fill=(120,180,130))
    _text_stroke(draw, 40, 168, rp(h), _get_font(fp, 96), sk["teks"], 3)

    # Garis pemisah
    draw.line([(40, 278), (W//2+100, 278)], fill=sk["aksen"], width=3)

    # Selisih
    sel = info['selisih']
    s_col = (80,255,120) if st=="Naik" else ((255,100,100) if st=="Turun" else (160,160,160))
    arah  = "▲" if st=="Naik" else ("▼" if st=="Turun" else "→")
    if sel > 0:
        draw.text((40, 292), f"{arah} {rp(sel)} dari kemarin",
                  font=_get_font(fp, 32), fill=s_col)

    # Judul 2 baris
    jb = _wrap_text(re.sub(r'[^\w\s\-\.,!?%]','', judul), 30)
    y_j = 358
    for idx, b in enumerate(jb[:2]):
        col = (220,255,220) if idx==0 else (140,180,150)
        draw.text((40, y_j), b, font=_get_font(fp, 36 if idx==0 else 30), fill=col)
        y_j += 46

    # Kolom historis kanan
    cx = W//2 + 120
    draw.text((cx, 65), "PERUBAHAN HARGA", font=_get_font(fp, 22), fill=(100,160,110))
    draw.line([(cx, 92), (W-40, 92)], fill=(60,100,70), width=1)
    historis = info.get("historis",{})
    lbl_map  = [("kemarin","1 Hari"),("7_hari","7 Hari"),("1_bulan","1 Bulan"),
                ("3_bulan","3 Bulan"),("6_bulan","6 Bulan"),("1_tahun","1 Tahun")]
    y_h = 100
    for lb, nama in lbl_map:
        d = historis.get(lb)
        if not d: continue
        warna = (80,230,110) if d["naik"] else ((255,110,100) if not d["stabil"] else (140,140,180))
        arah_h= "▲" if d["naik"] else ("▼" if not d["stabil"] else "→")
        draw.text((cx, y_h), nama, font=_get_font(fp, 24), fill=(140,170,150))
        draw.text((cx+160, y_h), f"{arah_h} {abs(d['persen']):.1f}%",
                  font=_get_font(fp, 24), fill=warna)
        y_h += 42
        if y_h > H-80: break

    img.save(output_path, "JPEG", quality=95)
    log(f"  -> ✅ Thumbnail T3 saved: {output_path}")
    return output_path


# ══════════════════════════════════════════════════
# TEMPLATE 4 — Neon Energy (Harga Emas Live)
# Layout: Full glow neon, harga center, energik
# Warna: Ungu-Mewah, neon glow effect
# ══════════════════════════════════════════════════
def _thumb_template_neon_energy(info, judul, output_path):
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    W, H   = 1280, 720
    sk     = SKEMA_AKTIF.get(info['status'], SKEMA_AKTIF['Stabil'])
    img    = Image.new('RGB', (W,H), (5,0,15))
    draw   = ImageDraw.Draw(img)

    # Foto blur full
    gb = _list_gambar()
    if gb:
        try:
            bg = Image.open(random.choice(gb)).convert('RGB')
            bg = _crop_center_resize(bg, W, H)
            bg = bg.filter(ImageFilter.GaussianBlur(12))
            bg = ImageEnhance.Brightness(bg).enhance(0.15)
            img.paste(bg, (0,0))
            draw = ImageDraw.Draw(img)
        except: pass

    fp = _font_path()
    h  = info['harga_sekarang']
    st = info['status']
    rp = lambda x: f"Rp {x:,}".replace(",",".")

    # Radial glow center-left
    glow = Image.new('RGBA', (W,H), (0,0,0,0))
    gd   = ImageDraw.Draw(glow)
    for r_size in range(350, 0, -20):
        alpha = int(60 * (1 - r_size/350))
        rr,gg,bb = sk["aksen"]
        gd.ellipse([(300-r_size, H//2-r_size),
                    (300+r_size, H//2+r_size)],
                   fill=(rr,gg,bb,alpha))
    img = Image.alpha_composite(img.convert('RGBA'), glow).convert('RGB')
    draw = ImageDraw.Draw(img)

    # Garis neon atas & bawah
    for i in range(4):
        alpha_line = 255 - i*50
        rr,gg,bb = sk["aksen"]
        draw.line([(0,3+i),(W,3+i)], fill=(rr,gg,bb,alpha_line))
        draw.line([(0,H-3-i),(W,H-3-i)], fill=(rr,gg,bb,alpha_line))

    # Badge animasi
    _draw_rounded_rect_solid(draw, 30, 28, 290, 94, 18, sk["badge"])
    _draw_rounded_rect_solid(draw, 30, 28, 290, 94, 18, None,
                              outline=sk["aksen"], width=3)
    draw.text((50, 40), sk["icon"], font=_get_font(fp, 34), fill=(255,255,255))

    # "LIVE" badge
    _draw_rounded_rect_solid(draw, W-120, 28, W-30, 76, 10, (200,0,0))
    draw.text((W-110, 34), "LIVE", font=_get_font(fp, 28), fill=(255,255,255))
    # dot merah berkedip (simulasi)
    draw.ellipse([(W-125, 38), (W-107, 56)], fill=(255,60,60))

    # Harga BESAR dengan neon glow
    harga_str = rp(h)
    # Glow layer
    for offset in [(0,3),(0,-3),(3,0),(-3,0),(2,2),(-2,2)]:
        rr,gg,bb = sk["aksen"]
        draw.text((28+offset[0], 115+offset[1]), harga_str,
                  font=_get_font(fp, 92), fill=(rr,gg,bb,80))
    _text_stroke(draw, 28, 115, harga_str, _get_font(fp, 92), sk["teks"], 3)
    draw.text((30, 218), "/ gram  ·  Antam Logam Mulia",
              font=_get_font(fp, 28), fill=sk["sub"])

    # Selisih
    sel = info['selisih']
    if sel > 0:
        s_col = (80,255,130) if st=="Naik" else (255,100,100)
        arah  = "▲" if st=="Naik" else "▼"
        _draw_rounded_rect_solid(draw, 28, 258, 360, 308, 22,
                                  (s_col[0]//5, s_col[1]//5, s_col[2]//5))
        draw.text((48, 264), f"{arah} {rp(sel)}",
                  font=_get_font(fp, 32), fill=s_col)

    # Judul
    jb = _wrap_text(re.sub(r'[^\w\s\-\.,!?%!]','', judul), 24)
    _text_stroke(draw, 28, 330, jb[0] if jb else "", _get_font(fp, 44), (255,255,255), 2)
    if len(jb)>1:
        draw.text((28, 382), jb[1], font=_get_font(fp, 36), fill=sk["sub"])

    # Kanan: historis vertical cards
    cx   = W//2 + 80
    historis = info.get("historis",{})
    lbl_map  = [("kemarin","1H"),("7_hari","7H"),("1_bulan","1B"),
                ("3_bulan","3B"),("6_bulan","6B"),("1_tahun","1T")]
    cx_card = cx
    for lb, nama in lbl_map:
        d = historis.get(lb)
        if not d: continue
        if cx_card + 100 > W-10: break
        warna = (80,255,120) if d["naik"] else ((255,100,100) if not d["stabil"] else (160,160,200))
        arah_h= "▲" if d["naik"] else ("▼" if not d["stabil"] else "→")
        # Card mini
        _draw_rounded_rect_solid(draw, cx_card, H//2-80,
                                  cx_card+90, H//2+80, 12, (0,0,0,160))
        _draw_rounded_rect_solid(draw, cx_card, H//2-80,
                                  cx_card+90, H//2+80, 12, None,
                                  outline=warna, width=2)
        draw.text((cx_card+8, H//2-68), nama,
                  font=_get_font(fp, 22), fill=(200,200,220))
        draw.text((cx_card+8, H//2-36), arah_h,
                  font=_get_font(fp, 34), fill=warna)
        draw.text((cx_card+8, H//2+4), f"{abs(d['persen']):.1f}%",
                  font=_get_font(fp, 26), fill=warna)
        cx_card += 100

    draw.text((30, H-40), NAMA_CHANNEL, font=_get_font(fp, 24), fill=sk["aksen"])
    draw.text((W-220, H-40), datetime.now().strftime("%d %b %Y"),
              font=_get_font(fp, 22), fill=(160,130,200))
    img.save(output_path, "JPEG", quality=95)
    log(f"  -> ✅ Thumbnail T4 saved: {output_path}")
    return output_path


# ══════════════════════════════════════════════════
# TEMPLATE 5 — Warm Card / Magazine (Cek Harga Emas)
# Layout: Gaya majalah, harga di kotak card, akrab
# Warna: Oranye-Tembaga, hangat dan familiar
# ══════════════════════════════════════════════════
def _thumb_template_warm_card(info, judul, output_path):
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    W, H   = 1280, 720
    sk     = SKEMA_AKTIF.get(info['status'], SKEMA_AKTIF['Stabil'])
    fp     = _font_path()
    h      = info['harga_sekarang']
    st     = info['status']
    rp     = lambda x: f"Rp {x:,}".replace(",",".")

    # Foto full sebagai background
    img = _buat_bg_foto_blur(W, H, kanan_saja=False, brightness=0.25)
    # Warm tint overlay
    warm = Image.new('RGBA', (W,H), (60,30,0,160))
    img  = Image.alpha_composite(img.convert('RGBA'), warm).convert('RGB')
    draw = ImageDraw.Draw(img)

    # CARD utama (kiri) — kotak solid
    card_x, card_y = 30, 30
    card_w, card_h = W//2+30, H-60
    _draw_rounded_rect_solid(draw, card_x, card_y,
                              card_x+card_w, card_y+card_h, 24,
                              (0,0,0,200))
    _draw_rounded_rect_solid(draw, card_x, card_y,
                              card_x+card_w, card_y+card_h, 24,
                              None, outline=sk["aksen"], width=4)

    # Header card
    draw.text((card_x+20, card_y+16), "💛 " + NAMA_CHANNEL.upper(),
              font=_get_font(fp, 22), fill=sk["aksen"])
    draw.line([(card_x+20, card_y+46),
               (card_x+card_w-20, card_y+46)],
              fill=sk["aksen"], width=2)

    # Badge
    bx = card_x+20
    _draw_rounded_rect_solid(draw, bx, card_y+56, bx+230, card_y+112, 14, sk["badge"])
    draw.text((bx+16, card_y+66), sk["icon"],
              font=_get_font(fp, 30), fill=(255,255,255))

    # Harga besar
    draw.text((bx, card_y+124), "Harga / gram",
              font=_get_font(fp, 26), fill=(200,180,140))
    _text_stroke(draw, bx, card_y+152, rp(h),
                 _get_font(fp, 84), sk["teks"], 3)

    # Selisih
    sel = info['selisih']
    if sel > 0:
        s_col = (80,255,120) if st=="Naik" else (255,110,100)
        arah  = "▲" if st=="Naik" else "▼"
        draw.text((bx, card_y+250),
                  f"{arah} {rp(sel)} dari kemarin",
                  font=_get_font(fp, 28), fill=s_col)

    # Garis divider
    draw.line([(bx, card_y+298), (card_x+card_w-20, card_y+298)],
              fill=(80,60,30), width=2)

    # Judul bawah dalam card
    jb = _wrap_text(re.sub(r'[^\w\s\-\.,!?%]','', judul), 26)
    y_j = card_y + 314
    for idx, b in enumerate(jb[:3]):
        col = (255,240,200) if idx==0 else (200,180,140)
        draw.text((bx, y_j), b,
                  font=_get_font(fp, 34 if idx==0 else 28), fill=col)
        y_j += (44 if idx==0 else 36)

    # Tanggal di footer card
    draw.text((bx, card_y+card_h-46),
              "📅 " + datetime.now().strftime("%d %B %Y"),
              font=_get_font(fp, 22), fill=(160,140,100))

    # PANEL KANAN: historis dengan style magazine
    rx = W//2 + 80
    draw.text((rx, 38), "PERUBAHAN", font=_get_font(fp, 26), fill=sk["aksen"])
    draw.text((rx, 66), "HARGA EMAS", font=_get_font(fp, 26), fill=(220,200,160))
    draw.line([(rx, 96), (W-30, 96)], fill=sk["aksen"], width=3)

    historis = info.get("historis",{})
    lbl_map  = [("kemarin","Kemarin"),("7_hari","7 Hari"),("1_bulan","1 Bulan"),
                ("3_bulan","3 Bulan"),("6_bulan","6 Bulan"),("1_tahun","1 Tahun")]
    y_h = 108
    for lb, nama in lbl_map:
        d = historis.get(lb)
        if not d: continue
        warna = (80,255,120) if d["naik"] else ((255,120,100) if not d["stabil"] else (180,180,160))
        arah_h= "▲" if d["naik"] else ("▼" if not d["stabil"] else "→")
        draw.text((rx, y_h), nama+":", font=_get_font(fp, 26), fill=(210,190,150))
        draw.text((rx+170, y_h), f"{arah_h} {abs(d['persen']):.1f}%",
                  font=_get_font(fp, 28), fill=warna)
        draw.line([(rx, y_h+38), (W-30, y_h+38)],
                  fill=(60,45,20), width=1)
        y_h += 46
        if y_h > H-60: break

    img.save(output_path, "JPEG", quality=95)
    log(f"  -> ✅ Thumbnail T5 saved: {output_path}")
    return output_path


# ════════════════════════════════════════════════════════════
# SHARED HELPERS thumbnail
# ════════════════════════════════════════════════════════════

def _font_path():
    lokal = os.path.abspath("font_temp.ttf")
    if os.path.exists(lokal): return lokal
    for fp in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
    ]:
        if os.path.exists(fp): return fp
    return None

def _get_font(fp, size):
    from PIL import ImageFont
    if fp:
        try: return ImageFont.truetype(fp, size)
        except: pass
    return ImageFont.load_default()

def _text_stroke(draw, x, y, text, font, color, stroke=2, stroke_col=(0,0,0)):
    for dx in range(-stroke, stroke+1):
        for dy in range(-stroke, stroke+1):
            if dx or dy:
                draw.text((x+dx, y+dy), text, font=font, fill=stroke_col)
    draw.text((x, y), text, font=font, fill=color)

def _draw_rounded_rect_solid(draw, x1, y1, x2, y2, radius, fill=None, outline=None, width=2):
    try:
        if fill:
            draw.rounded_rectangle([x1,y1,x2,y2], radius=radius, fill=fill)
        if outline:
            draw.rounded_rectangle([x1,y1,x2,y2], radius=radius,
                                    outline=outline, width=width)
    except:
        if fill:
            draw.rectangle([x1,y1,x2,y2], fill=fill)
        if outline:
            draw.rectangle([x1,y1,x2,y2], outline=outline, width=width)

def _buat_bg_foto_blur(W, H, kanan_saja=False, brightness=0.25):
    from PIL import Image, ImageFilter, ImageEnhance
    gb = _list_gambar()
    if gb:
        try:
            bg = Image.open(random.choice(gb)).convert('RGB')
            bg = _crop_center_resize(bg, W, H)
            bg = bg.filter(ImageFilter.GaussianBlur(10))
            bg = ImageEnhance.Brightness(bg).enhance(brightness)
            if kanan_saja:
                # Hanya tampilkan foto di sisi kanan
                solid  = Image.new('RGB', (W, H), (8,5,0))
                mask   = Image.new('L', (W, H), 0)
                md     = ImageDraw.Draw(mask)
                for x in range(W):
                    a = max(0, int((x - W//2) / (W//2) * 255))
                    md.line([(x,0),(x,H)], fill=a)
                solid.paste(bg, (0,0), mask)
                return solid
            return bg
        except: pass
    return Image.new('RGB', (W, H), (10,8,5))

def _crop_center_resize(img, W, H):
    from PIL import Image
    ratio_src = img.width / img.height
    ratio_tgt = W / H
    if ratio_src > ratio_tgt:
        new_w = int(img.height * ratio_tgt)
        left  = (img.width - new_w) // 2
        img   = img.crop((left, 0, left+new_w, img.height))
    else:
        new_h = int(img.width / ratio_tgt)
        top   = (img.height - new_h) // 2
        img   = img.crop((0, top, img.width, top+new_h))
    return img.resize((W, H), Image.LANCZOS)

def _draw_historis_panel(draw, img_ref, info, fp, sk, px, py, pw, ph):
    historis = info.get("historis",{})
    lbl_map  = [("kemarin","Kemarin"),("7_hari","7 Hari"),("1_bulan","1 Bulan"),
                ("3_bulan","3 Bulan"),("6_bulan","6 Bulan"),("1_tahun","1 Tahun")]
    draw.text((px, py+10), "Perubahan Harga",
              font=_get_font(fp, 28), fill=sk["aksen"])
    draw.line([(px, py+46), (px+pw, py+46)], fill=sk["aksen"], width=2)
    y_item = py + 58
    for lb, nama in lbl_map:
        d = historis.get(lb)
        if not d: continue
        warna = (80,255,120) if d["naik"] else ((255,100,100) if not d["stabil"] else (180,180,180))
        arah  = "▲" if d["naik"] else ("▼" if not d["stabil"] else "→")
        draw.text((px, y_item), nama+":", font=_get_font(fp, 24), fill=(200,200,200))
        draw.text((px+pw-130, y_item), f"{arah} {abs(d['persen']):.1f}%",
                  font=_get_font(fp, 26), fill=warna)
        y_item += 44
        if y_item > py+ph-10: break

def _wrap_text(text, max_chars=26):
    words = text.split()
    baris, cur = [], ""
    for w in words:
        test = (cur+" "+w).strip()
        if len(test) <= max_chars:
            cur = test
        else:
            if cur: baris.append(cur)
            cur = w
    if cur: baris.append(cur)
    return baris[:3]



# ════════════════════════════════════════════════════════════
# BAGIAN 14 — UPLOAD KE YOUTUBE
# ════════════════════════════════════════════════════════════

def upload_ke_youtube(video_path, judul, deskripsi, tags, thumbnail_path=None):
    log("[6/6] Upload ke YouTube...")
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        creds_file = "youtube_token.json"
        token_env  = os.environ.get("YOUTUBE_TOKEN_JSON")
        if token_env:
            with open(creds_file,"w") as f: f.write(token_env)
            log("  -> Token dari env OK.")

        if not os.path.exists(creds_file):
            log(f"  -> ERROR: {creds_file} tidak ditemukan!")
            log("  -> Jalankan setup_auth.py di lokal lalu set YOUTUBE_TOKEN_JSON di Secrets.")
            return None

        with open(creds_file) as f: td = json.load(f)
        creds = Credentials(
            token=td.get("token"),
            refresh_token=td.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=td.get("client_id"),
            client_secret=td.get("client_secret"),
        )
        youtube = build("youtube","v3", credentials=creds)

        body = {
            "snippet":{
                "title":       judul[:100],
                "description": deskripsi,
                "tags":        tags,
                "categoryId":  YOUTUBE_CATEGORY,
                "defaultLanguage":"id",
            },
            "status":{
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
                pct = int(status_up.progress()*100)
                print(f"  -> Upload: {pct}%", end='\r', flush=True)
        print()

        video_id = response.get("id")
        log(f"  -> ✅ Upload sukses! https://youtu.be/{video_id}")

        # Upload thumbnail jika ada
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
                ).execute()
                log(f"  -> ✅ Thumbnail diupload!")
            except Exception as e:
                log(f"  -> WARNING thumbnail upload: {e}")

        # Simpan history upload
        with open("upload_history.json","a",encoding="utf-8") as f:
            json.dump({"tanggal":datetime.now().isoformat(),
                       "video_id":video_id,"judul":judul,
                       "channel":NAMA_CHANNEL}, f, ensure_ascii=False)
            f.write("\n")

        return video_id

    except Exception as e:
        log(f"  -> EXCEPTION upload YouTube: {type(e).__name__}: {e}")
        return None


# ════════════════════════════════════════════════════════════
# BAGIAN 15 — BERSIHKAN TEMP
# ════════════════════════════════════════════════════════════

def bersihkan_temp(file_list=None, audio=None):
    log("[+] Membersihkan file sementara...")
    for f in [audio, file_list, "font_temp.ttf"]:
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
# BAGIAN 16 — MAIN
# ════════════════════════════════════════════════════════════

async def main():
    # Reset log
    with open(FFMPEG_LOG,'w',encoding='utf-8') as f:
        f.write(f"FFmpeg Log — {datetime.now()}\n{'='*60}\n")

    audio_temp  = "suara_temp.mp3"
    tanggal_str = datetime.now().strftime('%Y%m%d_%H%M')
    video_hasil = f"Video_Emas_{tanggal_str}.mp4"

    print(f"\n{'='*60}", flush=True)
    print(f"  AUTO VIDEO EMAS v7.1 — {NAMA_CHANNEL}", flush=True)
    print(f"  Channel ID  : {CHANNEL_ID}", flush=True)
    print(f"  Gaya Narasi : {NARASI_GAYA}", flush=True)
    print(f"  Skema Warna : {CFG['skema_warna']}", flush=True)
    print(f"  Voice       : {VOICE} ({VOICE_RATE})", flush=True)
    print(f"  Waktu       : {datetime.now().strftime('%d %B %Y, %H:%M WIB')}", flush=True)
    print(f"{'='*60}\n", flush=True)

    # Debug awal
    debug_storage()

    try:
        # STEP 0 — Kelola storage
        log("\n[STEP 0] Kelola bank gambar & video...")
        kelola_bank_gambar()
        kelola_bank_video()
        kelola_video_lama()

        # STEP 1 — Scraping harga
        info, data_harga = scrape_dan_kalkulasi_harga()
        if not info:
            log("FATAL: Scraping harga gagal. Proses dihentikan.")
            return

        # STEP 2 — Narasi & judul
        judul, narasi = buat_narasi_dan_judul(info, data_harga)
        log(f"\n{'='*60}")
        log(f"JUDUL FINAL: {judul}")
        log(f"{'='*60}\n")

        # STEP 3 — Generate suara
        try:
            durasi = buat_suara(narasi, audio_temp)
        except Exception as e:
            log(f"FATAL: Generate suara gagal: {e}")
            return

        # STEP 4 — Render klip visual
        file_list = proses_semua_klip(durasi)
        if not file_list:
            log("FATAL: Tidak ada klip yang berhasil dirender.")
            bersihkan_temp(file_list, audio_temp)
            return

        # STEP 5 — Render video final
        sukses = render_video_final(file_list, audio_temp, video_hasil, durasi)
        bersihkan_temp(file_list, audio_temp)

        if not sukses or not os.path.exists(video_hasil):
            log(f"FATAL: Render video final gagal.")
            return

        ukuran_mb = os.path.getsize(video_hasil) // 1024 // 1024
        log(f"\n✅ VIDEO SELESAI: {video_hasil} ({ukuran_mb} MB)")

        if ukuran_mb < 5:
            log(f"WARNING: Video terlalu kecil ({ukuran_mb} MB)! Cek {FFMPEG_LOG}.")

        # STEP 5b — Buat thumbnail
        thumbnail_file = f"thumbnail_{tanggal_str}.jpg"
        thumbnail_path = buat_thumbnail(info, judul, thumbnail_file)

        # STEP 6 — Upload YouTube
        deskripsi = (
            f"Update harga emas Antam hari ini "
            f"{datetime.now().strftime('%d %B %Y')}.\n\n"
            f"✅ Harga 1 gram : Rp {info['harga_sekarang']:,}\n"
            f"📊 Status       : {info['status']}\n\n"
            f"Informasi diambil langsung dari situs resmi Logam Mulia.\n\n"
            f"#HargaEmas #EmasAntam #InvestasiEmas #LogamMulia\n\n"
            f"Jangan lupa SUBSCRIBE dan aktifkan 🔔 notifikasi!\n"
            f"Channel: {NAMA_CHANNEL}"
        ).replace(",",".")

        video_id = upload_ke_youtube(video_hasil, judul, deskripsi,
                                     YOUTUBE_TAGS, thumbnail_path)

        # Debug akhir
        log(f"\n{'='*60}")
        log("RINGKASAN AKHIR:")
        log(f"  Video    : {video_hasil} ({ukuran_mb} MB)")
        log(f"  Thumbnail: {thumbnail_file if thumbnail_path else 'Tidak ada'}")
        log(f"  YouTube  : {'https://youtu.be/'+video_id if video_id else 'GAGAL UPLOAD'}")
        log(f"{'='*60}")

    except Exception as e:
        log(f"\nFATAL EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        bersihkan_temp(
            "concat_videos.txt" if os.path.exists("concat_videos.txt") else None,
            audio_temp if os.path.exists(audio_temp) else None
        )


if __name__ == "__main__":
    asyncio.run(main())



