# config.py — baris paling atas
import os

# Fix: handle string kosong, None, atau belum diset
_ch_raw    = os.environ.get("CHANNEL_ID", "").strip()
CHANNEL_ID = int(_ch_raw) if _ch_raw.isdigit() else 1


CHANNEL_CONFIG = {
    1: {
        "nama":        "Sobat Antam",
        "voice":       "id-ID-ArdiNeural",
        "rate":        "+5%",
        "gaya":        "formal_analitis",
        "skema_warna": "merah_emas",
        "keywords_img":["gold bullion bars close up","antam gold ingot",
                        "gold investment portfolio","precious metal gold",
                        "gold bar shiny","gold coins stack"],
        "keywords_vid":["gold bar shiny","gold coin stack","financial investment gold"],
    },
    2: {
        "nama":        "Update Emas Harian",
        "voice":       "id-ID-GadisNeural",
        "rate":        "+3%",
        "gaya":        "santai_edukatif",
        "skema_warna": "biru_perak",
        "keywords_img":["gold price chart analysis","stock market gold trading",
                        "gold investment analysis","gold coin collection close",
                        "financial chart gold","bank gold reserve"],
        "keywords_vid":["gold market trading","investment growth chart","financial gold"],
    },
    3: {
        "nama":        "Info Logam Mulia",
        "voice":       "id-ID-ArdiNeural",
        "rate":        "-3%",
        "gaya":        "berita_singkat",
        "skema_warna": "hijau_platinum",
        "keywords_img":["gold nuggets natural","bank vault gold",
                        "commodity gold trading","gold jewelry close up",
                        "platinum precious metal","gold refinery"],
        "keywords_vid":["gold nuggets","bank vault","commodity trading"],
    },
    4: {
        "nama":        "Harga Emas Live",
        "voice":       "id-ID-GadisNeural",
        "rate":        "+8%",
        "gaya":        "energik_motivatif",
        "skema_warna": "ungu_mewah",
        "keywords_img":["luxury gold collection","gold reserve central bank",
                        "gold standard bars","gold trophy award",
                        "premium gold investment","gold market floor"],
        "keywords_vid":["luxury gold","gold reserve","stock market floor"],
    },
    5: {
        "nama":        "Cek Harga Emas",
        "voice":       "id-ID-ArdiNeural",
        "rate":        "+0%",
        "gaya":        "percakapan_akrab",
        "skema_warna": "oranye_tembaga",
        "keywords_img":["gold coin collection antique","gold ring jewelry",
                        "gold necklace close up","yellow gold bracelet",
                        "gold pendant jewelry","gold earrings luxury"],
        "keywords_vid":["gold coin collection","antique gold jewelry","gold ornament"],
    },
}

CFG              = CHANNEL_CONFIG.get(CHANNEL_ID, CHANNEL_CONFIG[1])
NAMA_CHANNEL     = CFG["nama"]
VOICE            = CFG["voice"]
VOICE_RATE       = CFG["rate"]
NARASI_GAYA      = CFG["gaya"]
KATA_KUNCI_GAMBAR = CFG["keywords_img"]
KATA_KUNCI_VIDEO  = CFG["keywords_vid"]

GEMINI_API_KEY   = os.environ.get("GEMINI_API_KEY", "")
PEXELS_API_KEY   = os.environ.get("PEXELS_API_KEY", "")
FFMPEG_LOG       = "ffmpeg_log.txt"
FILE_HISTORY     = "history_harga.json"
YOUTUBE_CATEGORY = "25"
YOUTUBE_TAGS     = [
    "harga emas","emas antam","investasi emas","logam mulia",
    "harga emas hari ini","emas antam hari ini","harga emas antam",
    "update emas","emas batangan",
]

VIDEO_WIDTH      = 1920
VIDEO_HEIGHT     = 1080
FPS              = 30

FOLDER_GAMBAR     = "gambar_bank"
FOLDER_VIDEO_BANK = "video_bank"
JUMLAH_GAMBAR_MIN = 30
JUMLAH_DL_GAMBAR  = 50
JUMLAH_VIDEO_MIN  = 6
JUMLAH_DL_VIDEO   = 12
SIMPAN_VIDEO_MAKS = 3

SKEMA_THUMBNAIL = {
    "merah_emas": {
        "Naik":  {"badge":(200,0,0),   "aksen":(255,80,0),  "teks":(255,220,0),
                  "sub":(255,200,150), "hl_teks":(255,255,255),"icon":"▲ NAIK",
                  "bg_grad_atas":(60,0,0),"bg_grad_bawah":(20,0,0)},
        "Turun": {"badge":(0,140,50),  "aksen":(0,230,80),  "teks":(180,255,160),
                  "sub":(200,255,200), "hl_teks":(255,255,255),"icon":"▼ TURUN",
                  "bg_grad_atas":(0,40,10),"bg_grad_bawah":(0,15,5)},
        "Stabil":{"badge":(140,100,0), "aksen":(255,190,0), "teks":(255,230,100),
                  "sub":(255,240,180), "hl_teks":(255,255,255),"icon":"⬛ STABIL",
                  "bg_grad_atas":(40,30,0),"bg_grad_bawah":(15,10,0)},
    },
    "biru_perak": {
        "Naik":  {"badge":(0,60,180),  "aksen":(0,160,255), "teks":(150,220,255),
                  "sub":(200,230,255), "hl_teks":(255,255,255),"icon":"▲ NAIK",
                  "bg_grad_atas":(0,20,60),"bg_grad_bawah":(0,5,25)},
        "Turun": {"badge":(0,120,160), "aksen":(0,220,200), "teks":(180,255,250),
                  "sub":(200,255,255), "hl_teks":(255,255,255),"icon":"▼ TURUN",
                  "bg_grad_atas":(0,35,45),"bg_grad_bawah":(0,15,20)},
        "Stabil":{"badge":(80,80,160), "aksen":(160,160,255),"teks":(200,200,255),
                  "sub":(220,220,255), "hl_teks":(255,255,255),"icon":"⬛ STABIL",
                  "bg_grad_atas":(20,20,50),"bg_grad_bawah":(5,5,20)},
    },
    "hijau_platinum": {
        "Naik":  {"badge":(0,130,60),  "aksen":(0,230,100), "teks":(200,255,200),
                  "sub":(220,255,220), "hl_teks":(0,50,0),  "icon":"▲ NAIK",
                  "bg_grad_atas":(0,40,15),"bg_grad_bawah":(0,15,5)},
        "Turun": {"badge":(180,140,0), "aksen":(255,210,0), "teks":(255,240,150),
                  "sub":(255,245,180), "hl_teks":(50,30,0), "icon":"▼ TURUN",
                  "bg_grad_atas":(50,40,0),"bg_grad_bawah":(20,15,0)},
        "Stabil":{"badge":(60,120,60), "aksen":(150,255,150),"teks":(220,255,220),
                  "sub":(230,255,230), "hl_teks":(0,50,0),  "icon":"⬛ STABIL",
                  "bg_grad_atas":(15,35,15),"bg_grad_bawah":(5,15,5)},
    },
    "ungu_mewah": {
        "Naik":  {"badge":(120,0,180), "aksen":(220,0,255), "teks":(255,180,255),
                  "sub":(240,200,255), "hl_teks":(255,255,255),"icon":"▲ NAIK",
                  "bg_grad_atas":(40,0,60),"bg_grad_bawah":(15,0,25)},
        "Turun": {"badge":(80,0,140),  "aksen":(180,100,255),"teks":(230,200,255),
                  "sub":(240,220,255), "hl_teks":(255,255,255),"icon":"▼ TURUN",
                  "bg_grad_atas":(25,0,45),"bg_grad_bawah":(10,0,20)},
        "Stabil":{"badge":(100,50,150),"aksen":(200,150,255),"teks":(240,220,255),
                  "sub":(245,230,255), "hl_teks":(255,255,255),"icon":"⬛ STABIL",
                  "bg_grad_atas":(30,15,50),"bg_grad_bawah":(12,5,20)},
    },
    "oranye_tembaga": {
        "Naik":  {"badge":(200,80,0),  "aksen":(255,140,0), "teks":(255,210,100),
                  "sub":(255,225,150), "hl_teks":(50,20,0), "icon":"▲ NAIK",
                  "bg_grad_atas":(60,25,0),"bg_grad_bawah":(25,10,0)},
        "Turun": {"badge":(160,60,0),  "aksen":(255,100,0), "teks":(255,180,100),
                  "sub":(255,200,150), "hl_teks":(50,15,0), "icon":"▼ TURUN",
                  "bg_grad_atas":(50,20,0),"bg_grad_bawah":(20,8,0)},
        "Stabil":{"badge":(180,100,0), "aksen":(255,160,50),"teks":(255,220,150),
                  "sub":(255,235,180), "hl_teks":(50,25,0), "icon":"⬛ STABIL",
                  "bg_grad_atas":(55,30,0),"bg_grad_bawah":(22,12,0)},
    },
}

SKEMA_AKTIF = SKEMA_THUMBNAIL.get(CFG["skema_warna"], SKEMA_THUMBNAIL["merah_emas"])

def log(msg):
    from datetime import datetime
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)
