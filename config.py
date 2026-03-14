# config.py
import os

_ch_raw    = os.environ.get("CHANNEL_ID", "1").strip()
CHANNEL_ID = int(_ch_raw) if _ch_raw.isdigit() else 1

CHANNEL_CONFIG = {
    1: {
        "nama":        "Sobat Antam",
        "sapaan":      "Sobat Antam",
        "voice":       "id-ID-ArdiNeural",
        "rate":        "+5%",
        "gaya":        "formal_analitis",
        "skema_warna": "merah_emas",
        "keywords_img": [
            "emas batang antam",
            "emas batangan logam mulia",
            "gold bar antam indonesia",
            "gold bullion bar close up",
            "gold ingot stack shiny",
            "pure gold bar 999",
            "antam logam mulia gold",
            "gold bar investment shiny",
            "gold bullion indonesia",
            "stacked gold bars",
        ],
        "keywords_vid": [
            "gold bar shiny close up",
            "gold bullion bar",
            "pure gold ingot",
            "gold bar investment",
        ],
    },
    2: {
        "nama":        "Update Emas Harian",
        "sapaan":      "teman-teman",
        "voice":       "id-ID-GadisNeural",
        "rate":        "+3%",
        "gaya":        "santai_edukatif",
        "skema_warna": "biru_perak",
        "keywords_img": [
            "emas batang antam",
            "emas batangan logam mulia",
            "gold bar stack close up",
            "gold bullion investment",
            "gold ingot pile shiny",
            "antam gold bar indonesia",
            "pure gold bullion bar",
            "gold bar shiny reflection",
            "gold ingot close up",
            "gold bullion stack",
        ],
        "keywords_vid": [
            "gold bar investment",
            "gold bullion close up",
            "gold ingot shiny",
            "stacked gold bars",
        ],
    },
    3: {
        "nama":        "Info Logam Mulia",
        "sapaan":      "pemirsa",
        "voice":       "id-ID-ArdiNeural",
        "rate":        "-3%",
        "gaya":        "berita_singkat",
        "skema_warna": "hijau_platinum",
        "keywords_img": [
            "emas batang antam",
            "emas batangan logam mulia",
            "gold bar logam mulia",
            "gold bullion bar macro",
            "stacked gold ingot",
            "pure gold bar reflection",
            "gold bar vault storage",
            "gold bullion close up",
            "gold ingot indonesia",
            "antam gold bullion",
        ],
        "keywords_vid": [
            "gold bar vault",
            "stacked gold bullion",
            "gold ingot macro",
            "pure gold bar",
        ],
    },
    4: {
        "nama":        "Harga Emas Live",
        "sapaan":      "guys",
        "voice":       "id-ID-GadisNeural",
        "rate":        "+8%",
        "gaya":        "energik_motivatif",
        "skema_warna": "ungu_mewah",
        "keywords_img": [
            "emas batang antam",
            "emas batangan logam mulia",
            "gold bar luxury close up",
            "shiny gold bullion bar",
            "gold ingot premium",
            "gold bar collection",
            "antam gold bullion bar",
            "gold bullion stack shiny",
            "gold ingot pile",
            "pure gold bar luxury",
        ],
        "keywords_vid": [
            "luxury gold bar",
            "shiny gold bullion",
            "premium gold ingot",
            "gold bar stack",
        ],
    },
    5: {
        "nama":        "Cek Harga Emas",
        "sapaan":      "sahabat",
        "voice":       "id-ID-ArdiNeural",
        "rate":        "+0%",
        "gaya":        "percakapan_akrab",
        "skema_warna": "oranye_tembaga",
        "keywords_img": [
            "emas batang antam",
            "emas batangan logam mulia",
            "gold bar antam close up",
            "gold bullion bar shiny",
            "gold ingot stack macro",
            "pure gold bar indonesia",
            "gold bullion indonesia",
            "antam gold bar close",
            "gold ingot shiny",
            "gold bar pile",
        ],
        "keywords_vid": [
            "gold bar close up",
            "gold bullion stack",
            "gold ingot indonesia",
            "antam gold bar",
        ],
    },
}

CFG               = CHANNEL_CONFIG.get(CHANNEL_ID, CHANNEL_CONFIG[1])
NAMA_CHANNEL      = CFG["nama"]
SAPAAN            = CFG["sapaan"]
VOICE             = CFG["voice"]
VOICE_RATE        = CFG["rate"]
NARASI_GAYA       = CFG["gaya"]
KATA_KUNCI_GAMBAR = CFG["keywords_img"]
KATA_KUNCI_VIDEO  = CFG["keywords_vid"]

GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY",  "")
PEXELS_API_KEY    = os.environ.get("PEXELS_API_KEY",  "")
PIXABAY_API_KEY   = os.environ.get("PIXABAY_API_KEY", "")

YOUTUBE_CATEGORY = "25"
YOUTUBE_TAGS = [
    "harga emas", "emas antam", "investasi emas",
    "logam mulia", "harga emas hari ini",
    "emas antam hari ini", "harga emas antam",
    "update emas", "emas batangan", "antam",
]

VIDEO_WIDTH  = 1920
VIDEO_HEIGHT = 1080
FPS          = 30

FOLDER_GAMBAR     = "gambar_bank"
FOLDER_VIDEO_BANK = "video_bank"

# Cukup 2 gambar per run — alternasi Ken Burns
JUMLAH_GAMBAR_MIN = 10
JUMLAH_DL_GAMBAR  = 20

JUMLAH_VIDEO_MIN  = 4
JUMLAH_DL_VIDEO   = 8
SIMPAN_VIDEO_MAKS = 3

FFMPEG_LOG   = "ffmpeg_log.txt"
FILE_HISTORY = "history_harga.json"

SKEMA_THUMBNAIL = {
    "merah_emas": {
        "Naik": {
            "badge":        (200, 0, 0),
            "aksen":        (255, 80, 0),
            "teks":         (255, 220, 0),
            "sub":          (255, 200, 150),
            "hl_teks":      (255, 255, 255),
            "icon":         "▲ NAIK",
            "bg_grad_atas": (60, 0, 0),
        },
        "Turun": {
            "badge":        (0, 140, 50),
            "aksen":        (0, 230, 80),
            "teks":         (180, 255, 160),
            "sub":          (200, 255, 200),
            "hl_teks":      (255, 255, 255),
            "icon":         "▼ TURUN",
            "bg_grad_atas": (0, 40, 10),
        },
        "Stabil": {
            "badge":        (140, 100, 0),
            "aksen":        (255, 190, 0),
            "teks":         (255, 230, 100),
            "sub":          (255, 240, 180),
            "hl_teks":      (255, 255, 255),
            "icon":         "= STABIL",
            "bg_grad_atas": (40, 30, 0),
        },
    },
    "biru_perak": {
        "Naik": {
            "badge":        (0, 60, 180),
            "aksen":        (0, 160, 255),
            "teks":         (150, 220, 255),
            "sub":          (200, 230, 255),
            "hl_teks":      (255, 255, 255),
            "icon":         "▲ NAIK",
            "bg_grad_atas": (0, 20, 60),
        },
        "Turun": {
            "badge":        (0, 120, 160),
            "aksen":        (0, 220, 200),
            "teks":         (180, 255, 250),
            "sub":          (200, 255, 255),
            "hl_teks":      (255, 255, 255),
            "icon":         "▼ TURUN",
            "bg_grad_atas": (0, 35, 45),
        },
        "Stabil": {
            "badge":        (80, 80, 160),
            "aksen":        (160, 160, 255),
            "teks":         (200, 200, 255),
            "sub":          (220, 220, 255),
            "hl_teks":      (255, 255, 255),
            "icon":         "= STABIL",
            "bg_grad_atas": (20, 20, 50),
        },
    },
    "hijau_platinum": {
        "Naik": {
            "badge":        (0, 130, 60),
            "aksen":        (0, 230, 100),
            "teks":         (200, 255, 200),
            "sub":          (220, 255, 220),
            "hl_teks":      (0, 50, 0),
            "icon":         "▲ NAIK",
            "bg_grad_atas": (0, 40, 15),
        },
        "Turun": {
            "badge":        (180, 140, 0),
            "aksen":        (255, 210, 0),
            "teks":         (255, 240, 150),
            "sub":          (255, 245, 180),
            "hl_teks":      (50, 30, 0),
            "icon":         "▼ TURUN",
            "bg_grad_atas": (50, 40, 0),
        },
        "Stabil": {
            "badge":        (60, 120, 60),
            "aksen":        (150, 255, 150),
            "teks":         (220, 255, 220),
            "sub":          (230, 255, 230),
            "hl_teks":      (0, 50, 0),
            "icon":         "= STABIL",
            "bg_grad_atas": (15, 35, 15),
        },
    },
    "ungu_mewah": {
        "Naik": {
            "badge":        (120, 0, 180),
            "aksen":        (220, 0, 255),
            "teks":         (255, 180, 255),
            "sub":          (240, 200, 255),
            "hl_teks":      (255, 255, 255),
            "icon":         "▲ NAIK",
            "bg_grad_atas": (40, 0, 60),
        },
        "Turun": {
            "badge":        (80, 0, 140),
            "aksen":        (180, 100, 255),
            "teks":         (230, 200, 255),
            "sub":          (240, 220, 255),
            "hl_teks":      (255, 255, 255),
            "icon":         "▼ TURUN",
            "bg_grad_atas": (25, 0, 45),
        },
        "Stabil": {
            "badge":        (100, 50, 150),
            "aksen":        (200, 150, 255),
            "teks":         (240, 220, 255),
            "sub":          (245, 230, 255),
            "hl_teks":      (255, 255, 255),
            "icon":         "= STABIL",
            "bg_grad_atas": (30, 15, 50),
        },
    },
    "oranye_tembaga": {
        "Naik": {
            "badge":        (200, 80, 0),
            "aksen":        (255, 140, 0),
            "teks":         (255, 210, 100),
            "sub":          (255, 225, 150),
            "hl_teks":      (50, 20, 0),
            "icon":         "▲ NAIK",
            "bg_grad_atas": (60, 25, 0),
        },
        "Turun": {
            "badge":        (160, 60, 0),
            "aksen":        (255, 100, 0),
            "teks":         (255, 180, 100),
            "sub":          (255, 200, 150),
            "hl_teks":      (50, 15, 0),
            "icon":         "▼ TURUN",
            "bg_grad_atas": (50, 20, 0),
        },
        "Stabil": {
            "badge":        (180, 100, 0),
            "aksen":        (255, 160, 50),
            "teks":         (255, 220, 150),
            "sub":          (255, 235, 180),
            "hl_teks":      (50, 25, 0),
            "icon":         "= STABIL",
            "bg_grad_atas": (55, 30, 0),
        },
    },
}

SKEMA_AKTIF = SKEMA_THUMBNAIL.get(
    CFG["skema_warna"],
    SKEMA_THUMBNAIL["merah_emas"]
)


def log(msg):
    from datetime import datetime
    print(
        f"[{datetime.now().strftime('%H:%M:%S')}] {msg}",
        flush=True,
    )
