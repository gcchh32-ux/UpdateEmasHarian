# narasi.py
import re, random, time
import requests
from datetime import datetime
from config import (
    NAMA_CHANNEL, NARASI_GAYA,
    GEMINI_API_KEY, CHANNEL_ID, SAPAAN,
)
from utils import log, rp

import os
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.0-pro",
]
GEMINI_BASE = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/{model}:generateContent"
)

OPENROUTER_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "deepseek/deepseek-r1:free",
    "mistralai/mistral-7b-instruct:free",
]

# ════════════════════════════════════════════════════════════
# PROMPT
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
            ar = "naik"  if d["naik"]       else \
                 "turun" if not d["stabil"]  else \
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
            "reporter TV. Padat, jelas, informatif."
        ),
        "energik_motivatif": (
            "Gunakan gaya bahasa ENERGIK dan MOTIVATIF. "
            "Semangati penonton untuk bijak berinvestasi."
        ),
        "percakapan_akrab": (
            "Gunakan gaya bahasa PERCAKAPAN AKRAB seperti "
            "ngobrol dengan teman. Santai dan natural."
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
1. Buat JUDUL video menarik (maksimal 80 karakter)
2. Buat NARASI video berdurasi 3-4 menit (450-550 kata)

FORMAT OUTPUT (WAJIB IKUTI PERSIS):
JUDUL: [judul video di sini]
NARASI:
[narasi lengkap di sini]

ATURAN NARASI:
- Kalimat pertama WAJIB: "Halo {SAPAAN},"
- Sebutkan harga, status naik/turun/stabil, selisihnya
- Bahas historis perubahan harga (minimal 3 periode)
- Berikan tips/insight investasi emas yang relevan
- Tutup dengan ajakan subscribe dan like
- JANGAN gunakan emoji, simbol, atau karakter khusus
- JANGAN gunakan tanda bintang atau markdown
- Tulis angka dalam kata: satu juta enam ratus ribu rupiah
- Natural saat dibaca/didengar (text-to-speech)
- WAJIB minimal 450 kata, jangan singkat"""

# ════════════════════════════════════════════════════════════
# CALL GEMINI
# ════════════════════════════════════════════════════════════

def _call_gemini(prompt):
    if not GEMINI_API_KEY:
        log("  -> GEMINI_API_KEY kosong, skip Gemini")
        return None

    for model in GEMINI_MODELS:
        url = GEMINI_BASE.format(model=model)
        for attempt in range(1, 4):
            try:
                log(f"  -> Gemini [{model}] "
                    f"attempt {attempt}/3...")
                resp = requests.post(
                    url,
                    params={"key": GEMINI_API_KEY},
                    json={
                        "contents": [{
                            "parts": [{"text": prompt}]
                        }],
                        "generationConfig": {
                            "temperature":     0.8,
                            "maxOutputTokens": 1500,
                            "topP":            0.9,
                        },
                    },
                    timeout=45,
                )
                if resp.status_code == 429:
                    wait = attempt * 20
                    log(f"  -> Rate limit 429, "
                        f"tunggu {wait}s...")
                    time.sleep(wait)
                    continue
                if resp.status_code == 503:
                    wait = attempt * 10
                    log(f"  -> 503, tunggu {wait}s...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                text = (data["candidates"][0]
                            ["content"]["parts"][0]
                            ["text"])
                log(f"  -> Gemini [{model}] OK!")
                return text
            except requests.exceptions.HTTPError as e:
                log(f"  -> HTTP error: {e}")
                if attempt < 3:
                    time.sleep(attempt * 15)
            except Exception as e:
                log(f"  -> Error: {e}")
                if attempt < 3:
                    time.sleep(attempt * 10)
        log(f"  -> [{model}] gagal, coba model lain...")
        time.sleep(5)

    log("  -> Semua model Gemini gagal")
    return None

# ════════════════════════════════════════════════════════════
# CALL OPENROUTER
# ════════════════════════════════════════════════════════════

def _call_openrouter(prompt):
    if not OPENROUTER_API_KEY:
        log("  -> OPENROUTER_API_KEY kosong, skip")
        return None

    for model in OPENROUTER_MODELS:
        for attempt in range(1, 3):
            try:
                log(f"  -> OpenRouter [{model}] "
                    f"attempt {attempt}/2...")
                resp = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization":
                            f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com",
                        "X-Title": NAMA_CHANNEL,
                    },
                    json={
                        "model": model,
                        "messages": [{
                            "role":    "user",
                            "content": prompt,
                        }],
                        "max_tokens":  1500,
                        "temperature": 0.8,
                    },
                    timeout=60,
                )
                if resp.status_code == 429:
                    wait = attempt * 15
                    log(f"  -> Rate limit 429, "
                        f"tunggu {wait}s...")
                    time.sleep(wait)
                    continue
                if resp.status_code in (500, 502, 503):
                    wait = attempt * 10
                    log(f"  -> Server error "
                        f"{resp.status_code}, "
                        f"tunggu {wait}s...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                text = (data["choices"][0]
                            ["message"]["content"])
                if text and len(text.strip()) > 100:
                    log(f"  -> OpenRouter [{model}] OK!")
                    return text
                else:
                    log(f"  -> [{model}] respon kosong")
            except requests.exceptions.HTTPError as e:
                log(f"  -> HTTP error: {e}")
                if attempt < 2:
                    time.sleep(attempt * 10)
            except Exception as e:
                log(f"  -> Error: {e}")
                if attempt < 2:
                    time.sleep(attempt * 10)
        log(f"  -> [{model}] gagal, coba model lain...")
        time.sleep(3)

    log("  -> Semua model OpenRouter gagal")
    return None

# ════════════════════════════════════════════════════════════
# PARSE OUTPUT
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
# FALLBACK NARASI PANJANG ~500 kata
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
            f"berinvestasi emas. "
            f"Harga emas Antam hari ini mengalami "
            f"kenaikan sebesar {selisih} "
            f"atau {persen} persen. "
            f"Harga kini berada di angka {harga} per gram. "
            f"Kenaikan ini tentu menjadi berita positif "
            f"bagi para investor yang sudah memegang emas "
            f"dalam portofolio investasi mereka."
        ),
        "turun": (
            f"Ada informasi penting untuk Anda "
            f"para investor emas. "
            f"Harga emas Antam hari ini mengalami "
            f"penurunan sebesar {selisih} "
            f"atau {persen} persen. "
            f"Harga kini berada di angka {harga} per gram. "
            f"Penurunan ini bisa menjadi peluang menarik "
            f"bagi Anda yang sedang menunggu momen "
            f"untuk membeli emas dengan harga lebih murah."
        ),
        "stabil": (
            f"Harga emas Antam hari ini terpantau "
            f"relatif stabil di angka {harga} per gram. "
            f"Tidak banyak perubahan dari harga kemarin "
            f"yang berada di {kemarin}. "
            f"Kondisi stabil seperti ini menunjukkan "
            f"bahwa pasar emas sedang dalam fase "
            f"konsolidasi, dan bisa menjadi momen yang "
            f"baik untuk mempertimbangkan investasi emas "
            f"jangka panjang."
        ),
    }
    paragraf_tren = tren_map.get(status, tren_map["stabil"])

    historis_txt = ""
    lbl_map = [
        ("7_hari",  "tujuh hari terakhir"),
        ("1_bulan", "satu bulan terakhir"),
        ("3_bulan", "tiga bulan terakhir"),
        ("6_bulan", "enam bulan terakhir"),
        ("1_tahun", "satu tahun terakhir"),
    ]
    for key, label in lbl_map:
        d = info["historis"].get(key)
        if d:
            ar = "naik"  if d["naik"]      else \
                 "turun" if not d["stabil"] else \
                 "stabil"
            historis_txt += (
                f"Dalam {label}, harga emas Antam "
                f"tercatat {ar} sebesar "
                f"{abs(d['persen']):.2f} persen "
                f"dengan selisih "
                f"{rp(abs(d['selisih']))}. "
            )

    tips_list = [
        (
            "Bagi Anda yang berencana membeli emas, "
            "ada beberapa hal yang perlu diperhatikan. "
            "Pertama, selalu beli emas di tempat resmi "
            "seperti butik Antam atau platform terpercaya "
            "agar keaslian emas terjamin. "
            "Kedua, simpan emas di tempat yang aman "
            "seperti brankas atau safe deposit box. "
            "Ketiga, jangan terpengaruh fluktuasi harga "
            "jangka pendek karena emas adalah instrumen "
            "investasi jangka panjang yang terbukti "
            "mempertahankan nilainya dari waktu ke waktu."
        ),
        (
            "Investasi emas memiliki banyak keunggulan "
            "dibandingkan instrumen investasi lainnya. "
            "Emas adalah aset nyata yang tidak terpengaruh "
            "inflasi dalam jangka panjang. "
            "Selain itu, emas mudah dicairkan kapan saja "
            "jika Anda membutuhkan dana darurat. "
            "Emas Antam khususnya sangat diminati karena "
            "sudah bersertifikat resmi dan diakui secara "
            "internasional oleh London Bullion Market "
            "Association atau yang dikenal dengan LBMA."
        ),
        (
            "Salah satu strategi investasi emas yang "
            "populer adalah metode cicil atau yang dikenal "
            "dengan istilah dollar cost averaging. "
            "Dengan metode ini, Anda membeli emas secara "
            "rutin setiap bulan dalam jumlah yang sama, "
            "tanpa terlalu memperhatikan fluktuasi harga. "
            "Strategi ini terbukti efektif mengurangi "
            "risiko membeli di harga puncak, dan secara "
            "bertahap membangun portofolio emas yang "
            "solid untuk masa depan finansial Anda."
        ),
    ]
    tips = random.choice(tips_list)

    judul_list = [
        f"Harga Emas Antam Hari Ini {tgl} - "
        f"{status.title()} {persen}%",
        f"Update Harga Emas {tgl} | "
        f"Antam {harga} per Gram",
        f"Harga Emas Antam {status.title()} {persen}%"
        f" - {tgl}",
        f"Info Harga Emas Hari Ini {tgl} | "
        f"{harga} per Gram",
    ]
    judul  = random.choice(judul_list)

    narasi = f"""Halo {SAPAAN},
Selamat datang kembali di channel {NAMA_CHANNEL}, channel yang selalu hadir setiap hari memberikan update harga emas Antam terkini untuk Anda.

Hari ini, {tgl}, kami kembali hadir dengan informasi harga emas terbaru yang sayang untuk Anda lewatkan.

{paragraf_tren}

Sebagai perbandingan, harga emas kemarin tercatat di {kemarin} per gram. {historis_txt}

Melihat tren pergerakan harga emas ini, tentu banyak dari Anda yang bertanya-tanya, apakah sekarang waktu yang tepat untuk membeli atau menjual emas?

{tips}

Selain itu, penting juga untuk selalu mengikuti perkembangan faktor-faktor yang mempengaruhi harga emas dunia, seperti nilai tukar dolar Amerika terhadap rupiah, tingkat inflasi global, kebijakan suku bunga bank sentral Amerika atau The Fed, serta kondisi geopolitik dunia. Semua faktor tersebut dapat mempengaruhi pergerakan harga emas baik di tingkat global maupun di Indonesia.

Untuk Anda yang baru pertama kali ingin berinvestasi emas, kami sarankan untuk memulai dengan gram kecil terlebih dahulu, misalnya setengah gram atau satu gram. Hal ini untuk membiasakan diri dengan mekanisme jual beli emas sebelum berinvestasi dalam jumlah yang lebih besar.

Demikianlah update harga emas Antam hari ini dari channel {NAMA_CHANNEL}. Semoga informasi ini bermanfaat untuk keputusan investasi Anda.

Jangan lupa untuk like video ini jika bermanfaat, tinggalkan komentar jika ada pertanyaan, dan subscribe channel ini agar Anda tidak ketinggalan update harga emas setiap harinya.

Sampai jumpa di video berikutnya, tetap semangat berinvestasi dan salam sukses untuk kita semua."""

    return judul, narasi

# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════

def buat_narasi_dan_judul(info):
    log("[2/6] Membuat narasi & judul...")
    prompt = _build_prompt(info)

    # ── Coba Gemini dulu ──────────────────────────────────
    raw = _call_gemini(prompt)
    if raw:
        judul, narasi = _parse_output(raw)
        if len(narasi.split()) >= 350:
            log(f"  -> Gemini OK — "
                f"{len(narasi.split())} kata")
            log(f"  -> Judul: {judul[:60]}...")
            return judul, narasi
        else:
            log(f"  -> Narasi Gemini terlalu pendek "
                f"({len(narasi.split())} kata), "
                f"coba OpenRouter...")

    # ── Coba OpenRouter sebagai fallback ─────────────────
    raw = _call_openrouter(prompt)
    if raw:
        judul, narasi = _parse_output(raw)
        if len(narasi.split()) >= 350:
            log(f"  -> OpenRouter OK — "
                f"{len(narasi.split())} kata")
            log(f"  -> Judul: {judul[:60]}...")
            return judul, narasi
        else:
            log(f"  -> Narasi OpenRouter terlalu pendek "
                f"({len(narasi.split())} kata), "
                f"pakai fallback lokal...")

    # ── Fallback lokal jika semua API gagal ──────────────
    log("  -> Pakai narasi fallback lokal...")
    judul, narasi = _buat_narasi_fallback(info)
    log(f"  -> Fallback OK — "
        f"{len(narasi.split())} kata")
    log(f"  -> Judul: {judul[:60]}...")
    return judul, narasi
