# narasi.py
import re, random
import requests
from datetime import datetime
from config import (
    NAMA_CHANNEL, NARASI_GAYA,
    GEMINI_API_KEY, CHANNEL_ID, SAPAAN,
)
from utils import log, rp

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.0-flash:generateContent"
)

# ════════════════════════════════════════════════════════════
# PROMPT PER GAYA
# ════════════════════════════════════════════════════════════

def _build_prompt(info):
    harga   = rp(info["harga_sekarang"])
    kemarin = rp(info["harga_kemarin"])
    selisih = rp(info["selisih"])
    status  = info["status"]
    persen  = f"{info['persen']:.2f}%"
    tgl     = info["tanggal"]
    waktu   = info["waktu"]

    hist_txt = ""
    lbl_map  = [
        ("kemarin", "kemarin"),
        ("7_hari",  "7 hari lalu"),
        ("1_bulan", "1 bulan lalu"),
        ("3_bulan", "3 bulan lalu"),
        ("6_bulan", "6 bulan lalu"),
        ("1_tahun", "1 tahun lalu"),
    ]
    for key, label in lbl_map:
        d = info["historis"].get(key)
        if d:
            ar = "naik"   if d["naik"]        else \
                 "turun"  if not d["stabil"]   else \
                 "stabil"
            hist_txt += (
                f"- {label}: {ar} "
                f"{abs(d['persen']):.2f}% "
                f"({rp(abs(d['selisih']))})\n"
            )

    gaya_map = {
        "formal_analitis": (
            "Gunakan gaya bahasa FORMAL dan ANALITIS. "
            "Jelaskan data dengan detail, berikan analisis "
            "singkat tren, dan saran investasi yang bijak."
        ),
        "santai_edukatif": (
            "Gunakan gaya bahasa SANTAI dan EDUKATIF. "
            "Ramah, mudah dipahami semua kalangan, "
            "sisipkan tips ringan tentang investasi emas."
        ),
        "berita_singkat": (
            "Gunakan gaya bahasa BERITA SINGKAT seperti "
            "reporter TV. Padat, jelas, informatif, "
            "tidak bertele-tele."
        ),
        "energik_motivatif": (
            "Gunakan gaya bahasa ENERGIK dan MOTIVATIF. "
            "Semangati penonton untuk bijak berinvestasi, "
            "gunakan kalimat yang membangkitkan antusias."
        ),
        "percakapan_akrab": (
            "Gunakan gaya bahasa PERCAKAPAN AKRAB seperti "
            "ngobrol dengan teman. Santai, natural, "
            "sesekali gunakan kata sehari-hari."
        ),
    }
    gaya_instruksi = gaya_map.get(
        NARASI_GAYA, gaya_map["santai_edukatif"]
    )

    return f"""Kamu adalah narrator video YouTube channel "{NAMA_CHANNEL}".
{gaya_instruksi}

DATA HARGA EMAS ANTAM HARI INI:
- Tanggal     : {tgl}
- Waktu update: {waktu}
- Harga/gram  : {harga}
- Kemarin     : {kemarin}
- Perubahan   : {status} {persen} ({selisih})

HISTORIS PERUBAHAN:
{hist_txt if hist_txt else "- Belum ada data historis"}

TUGAS:
1. Buat JUDUL video yang menarik (maksimal 80 karakter)
2. Buat NARASI video berdurasi 3-4 menit (450-550 kata)

FORMAT OUTPUT (WAJIB IKUTI PERSIS):
JUDUL: [judul video di sini]
NARASI:
[narasi lengkap di sini]

ATURAN NARASI:
- Kalimat pertama WAJIB: "Halo {SAPAAN},"
- Sebutkan harga, status naik/turun/stabil, dan selisihnya
- Bahas historis perubahan harga (minimal 3 periode)
- Berikan tips/insight investasi emas yang relevan
- Tutup dengan ajakan subscribe dan like
- JANGAN gunakan emoji, simbol, atau karakter khusus
- JANGAN gunakan tanda bintang atau markdown
- Gunakan angka dalam format: satu juta enam ratus ribu rupiah
- Pastikan natural saat dibaca/didengar (untuk text-to-speech)"""


# ════════════════════════════════════════════════════════════
# CALL GEMINI API
# ════════════════════════════════════════════════════════════

def _call_gemini(prompt):
    if not GEMINI_API_KEY:
        log("  -> GEMINI_API_KEY kosong, skip Gemini")
        return None
    try:
        resp = requests.post(
            GEMINI_URL,
            params={"key": GEMINI_API_KEY},
            json={
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature":     0.8,
                    "maxOutputTokens": 1200,
                    "topP":            0.9,
                },
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return (data["candidates"][0]
                    ["content"]["parts"][0]["text"])
    except Exception as e:
        log(f"  -> Gemini error: {e}")
        return None


# ════════════════════════════════════════════════════════════
# PARSE OUTPUT GEMINI
# ════════════════════════════════════════════════════════════

def _parse_output(raw):
    judul  = ""
    narasi = ""
    lines  = raw.strip().splitlines()

    for i, line in enumerate(lines):
        line_s = line.strip()
        if line_s.upper().startswith("JUDUL:"):
            judul = line_s[6:].strip()
        elif line_s.upper().startswith("NARASI:"):
            narasi = "\n".join(lines[i+1:]).strip()
            break

    if not judul and lines:
        judul = lines[0].strip()
    if not narasi:
        narasi = raw.strip()

    judul = re.sub(
        r'[*_`#\[\]|▲▼⬛📊📈📉💰🔥💥🚨🎯⚡😲🤔💡🛒🔴🟢⚠️📅💛]',
        '', judul
    ).strip()

    baris_bersih = []
    for bl in narasi.splitlines():
        bl = bl.strip()
        if not bl:
            baris_bersih.append("")
            continue
        bl_lower = bl.lower()
        if any(bl_lower.startswith(skip) for skip in [
            "narasi:", "judul:", "**", "##", "--",
            "catatan:", "note:", "format:"
        ]):
            continue
        if bl_lower.startswith("halo") and baris_bersih:
            continue
        baris_bersih.append(bl)

    narasi_bersih = "\n".join(baris_bersih).strip()
    narasi_bersih = re.sub(
        r'[*_`#\[\]|▲▼⬛📊📈📉💰🔥💥🚨🎯⚡😲🤔💡🛒🔴🟢⚠️📅💛]',
        '', narasi_bersih
    ).strip()

    return judul, narasi_bersih


# ════════════════════════════════════════════════════════════
# FALLBACK NARASI
# ════════════════════════════════════════════════════════════

def _buat_narasi_fallback(info):
    harga   = rp(info["harga_sekarang"])
    kemarin = rp(info["harga_kemarin"])
    selisih = rp(info["selisih"])
    status  = info["status"].lower()
    persen  = f"{info['persen']:.2f}"
    tgl     = info["tanggal"]

    tren_map = {
        "naik": (
            f"Kabar gembira bagi Anda yang sudah "
            f"berinvestasi emas! "
            f"Harga emas Antam hari ini mengalami "
            f"kenaikan sebesar {selisih} "
            f"atau {persen} persen, "
            f"sehingga kini berada di angka "
            f"{harga} per gram."
        ),
        "turun": (
            f"Ada informasi penting untuk Anda "
            f"para investor emas. "
            f"Harga emas Antam hari ini mengalami "
            f"penurunan sebesar {selisih} "
            f"atau {persen} persen, "
            f"kini berada di angka {harga} per gram."
        ),
        "stabil": (
            f"Harga emas Antam hari ini terpantau "
            f"relatif stabil di angka {harga} per gram, "
            f"tidak banyak berubah dari harga kemarin "
            f"yang berada di {kemarin}."
        ),
    }
    paragraf_tren = tren_map.get(status, tren_map["stabil"])

    historis_txt = ""
    lbl_map = [
        ("7_hari",  "7 hari terakhir"),
        ("1_bulan", "sebulan terakhir"),
        ("3_bulan", "3 bulan terakhir"),
        ("1_tahun", "setahun terakhir"),
    ]
    for key, label in lbl_map:
        d = info["historis"].get(key)
        if d:
            ar = "naik"   if d["naik"]      else \
                 "turun"  if not d["stabil"] else \
                 "stabil"
            historis_txt += (
                f"Dalam {label}, harga emas tercatat "
                f"{ar} sebesar "
                f"{abs(d['persen']):.2f} persen. "
            )

    tips_list = [
        (
            "Bagi Anda yang berencana membeli emas, "
            "saat harga sedang koreksi bisa menjadi "
            "momentum yang baik untuk menambah koleksi. "
            "Namun selalu sesuaikan dengan kemampuan "
            "finansial Anda."
        ),
        (
            "Investasi emas cocok untuk tujuan jangka "
            "panjang. Pastikan Anda menyimpan emas di "
            "tempat yang aman dan selalu pantau "
            "perkembangan harga secara rutin."
        ),
        (
            "Emas Antam adalah pilihan investasi yang "
            "terpercaya karena sudah bersertifikat resmi. "
            "Beli di tempat resmi seperti butik Antam "
            "atau platform terpercaya."
        ),
    ]
    tips  = random.choice(tips_list)
    judul_list = [
        f"Harga Emas Antam Hari Ini {tgl} - "
        f"{status.title()} {persen}%",
        f"Update Harga Emas {tgl} | Antam {harga}/gram",
        f"Harga Emas Antam {status.title()} {persen}%"
        f" - {tgl}",
        f"Info Harga Emas Hari Ini {tgl} | "
        f"{harga} per gram",
    ]
    judul  = random.choice(judul_list)
    narasi = f"""Halo {SAPAAN},
Selamat datang kembali di channel {NAMA_CHANNEL}.
Hari ini, {tgl}, kami hadir dengan update harga emas terbaru untuk Anda.

{paragraf_tren}

Sebagai perbandingan, harga emas kemarin tercatat di {kemarin} per gram.
{historis_txt}

{tips}

Itulah update harga emas Antam hari ini dari channel {NAMA_CHANNEL}.
Jangan lupa untuk selalu pantau channel ini setiap hari agar Anda tidak ketinggalan informasi harga emas terkini.
Jika video ini bermanfaat, silakan like, komen, dan subscribe.
Sampai jumpa di video berikutnya."""

    return judul, narasi


# ════════════════════════════════════════════════════════════
# MAIN — dipanggil dari video_maker.py
# ════════════════════════════════════════════════════════════

def buat_narasi_dan_judul(info):
    log("[2/6] Membuat narasi & judul...")

    prompt = _build_prompt(info)
    raw    = _call_gemini(prompt)

    if raw:
        judul, narasi = _parse_output(raw)
        if len(narasi.split()) >= 200:
            log(f"  -> ✅ Gemini OK — "
                f"{len(narasi.split())} kata")
            log(f"  -> Judul: {judul[:60]}...")
            return judul, narasi
        else:
            log(f"  -> Narasi Gemini terlalu pendek "
                f"({len(narasi.split())} kata), "
                f"pakai fallback")

    judul, narasi = _buat_narasi_fallback(info)
    log(f"  -> ✅ Fallback OK — "
        f"{len(narasi.split())} kata")
    log(f"  -> Judul: {judul[:60]}...")
    return judul, narasi
