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
# FALLBACK TEMPLATES — POOL PER CHANNEL
# Setiap channel punya 5 variasi opening, 5 tren, 5 tips,
# 5 historis, 5 penutup, dan 5 judul — dipilih random.
# ════════════════════════════════════════════════════════════

def _pool_ch1(info, harga, kemarin, selisih, persen,
              status, tgl, hist):
    """Channel 1: Sobat Antam — formal analitis"""
    openings = [
        f"Halo {SAPAAN}, selamat datang kembali di channel {NAMA_CHANNEL}. Pada kesempatan hari ini, {tgl}, kami hadir membawa analisis lengkap pergerakan harga emas Antam yang perlu Anda cermati sebelum mengambil keputusan investasi.",
        f"Halo {SAPAAN}, salam investasi cerdas dari channel {NAMA_CHANNEL}. Hari ini, {tgl}, kami akan mengulas secara mendalam perkembangan harga emas Antam beserta implikasinya bagi portofolio investasi Anda.",
        f"Halo {SAPAAN}, selamat berjumpa kembali bersama channel {NAMA_CHANNEL}. Di penghujung analisis pasar hari ini, {tgl}, kami sajikan data terkini harga emas Antam yang harus masuk radar investasi Anda.",
        f"Halo {SAPAAN}, terima kasih telah bergabung kembali di channel {NAMA_CHANNEL}. Pada sesi analisis hari ini, {tgl}, kami akan membahas pergerakan harga emas Antam secara komprehensif dan objektif.",
        f"Halo {SAPAAN}, selamat datang di sesi analisis emas harian bersama channel {NAMA_CHANNEL}. Tanggal {tgl} mencatatkan pergerakan harga yang penting untuk disimak oleh setiap investor emas di Indonesia.",
    ]
    tren_naik = [
        f"Berdasarkan data terkini, harga emas Antam per hari ini tercatat berada di posisi {harga} per gram, mengalami kenaikan sebesar {selisih} atau {persen} persen dibandingkan harga kemarin yang berada di {kemarin}. Kenaikan ini merupakan sinyal positif bagi pasar emas nasional dan mengindikasikan sentimen bullish yang perlu dicermati oleh para investor.",
        f"Data pasar hari ini menunjukkan bahwa harga emas Antam telah bergerak ke level {harga} per gram, naik {selisih} atau setara {persen} persen dari posisi kemarin di {kemarin}. Pergerakan positif ini sejalan dengan tren penguatan harga emas di pasar global yang dipicu oleh meningkatnya permintaan sebagai aset safe haven.",
        f"Pada penutupan sesi hari ini, harga emas Antam berada di angka {harga} per gram, mencatatkan kenaikan {persen} persen atau setara {selisih} dari harga sebelumnya {kemarin}. Momentum kenaikan ini mencerminkan kepercayaan investor terhadap emas sebagai instrumen lindung nilai yang andal.",
        f"Analisis data harian menunjukkan harga emas Antam hari ini menyentuh {harga} per gram, menguat {selisih} atau {persen} persen dari {kemarin}. Dari sudut pandang teknikal, kenaikan ini mengkonfirmasi tren uptrend jangka menengah yang sedang berlangsung di pasar emas.",
        f"Harga emas Antam hari ini tercatat di level {harga} per gram, naik sebesar {persen} persen atau {selisih} dibandingkan kemarin yang sebesar {kemarin}. Penguatan ini didukung oleh faktor fundamental yang solid, termasuk permintaan yang konsisten dari segmen investasi dan perhiasan.",
    ]
    tren_turun = [
        f"Berdasarkan data terkini, harga emas Antam hari ini tercatat di posisi {harga} per gram, mengalami koreksi sebesar {selisih} atau {persen} persen dari harga kemarin yang berada di {kemarin}. Koreksi ini merupakan hal yang wajar dalam siklus pasar dan tidak serta-merta mencerminkan tren bearish jangka panjang.",
        f"Data pasar hari ini menunjukkan harga emas Antam bergerak ke level {harga} per gram, turun {selisih} atau {persen} persen dari posisi kemarin di {kemarin}. Secara analitis, koreksi harga seperti ini kerap menjadi peluang akumulasi yang menarik bagi investor jangka panjang.",
        f"Pada sesi hari ini, harga emas Antam terkoreksi ke angka {harga} per gram, turun {persen} persen atau setara {selisih} dari {kemarin}. Penurunan ini kemungkinan dipicu oleh aksi profit taking dari investor jangka pendek dan penguatan sementara dolar Amerika di pasar global.",
        f"Analisis data menunjukkan harga emas Antam hari ini berada di {harga} per gram, melemah {selisih} atau {persen} persen dari {kemarin}. Dari perspektif investasi jangka panjang, koreksi seperti ini justru bisa menjadi momen yang tepat untuk melakukan pembelian bertahap.",
        f"Harga emas Antam hari ini tercatat {harga} per gram, mengalami tekanan turun sebesar {persen} persen atau {selisih} dari kemarin di {kemarin}. Kondisi ini perlu direspons dengan tenang oleh investor, mengingat tren jangka panjang emas secara historis selalu menunjukkan kenaikan.",
    ]
    tren_stabil = [
        f"Data pasar hari ini menunjukkan harga emas Antam berada di level {harga} per gram, relatif stabil dibandingkan kemarin yang sebesar {kemarin}. Kondisi konsolidasi seperti ini umumnya terjadi saat pasar sedang menunggu katalis baru untuk menentukan arah pergerakan harga berikutnya.",
        f"Harga emas Antam hari ini tercatat di {harga} per gram, tidak jauh berbeda dari posisi kemarin di {kemarin}. Stabilitas harga ini mencerminkan keseimbangan antara tekanan jual dan beli di pasar, yang menandakan pasar sedang dalam fase akumulasi.",
        f"Pada sesi hari ini, harga emas Antam bergerak sideways di kisaran {harga} per gram, hampir sama dengan harga kemarin {kemarin}. Konsolidasi ini bisa menjadi tanda penguatan sebelum pergerakan harga yang lebih signifikan terjadi.",
        f"Harga emas Antam hari ini berada di posisi {harga} per gram, stabil dari kemarin di {kemarin}. Fase konsolidasi seperti ini dalam analisis teknikal sering kali mendahului pergerakan harga yang lebih besar, baik ke atas maupun ke bawah.",
        f"Data terkini menunjukkan harga emas Antam hari ini di level {harga} per gram, relatif tidak berubah dari {kemarin}. Dalam perspektif analisis fundamental, stabilitas ini bisa diartikan sebagai keseimbangan sementara sebelum faktor makroekonomi mendorong harga ke arah baru.",
    ]
    tips = [
        "Dalam konteks investasi emas, para analis umumnya merekomendasikan alokasi sebesar 10 hingga 20 persen dari total portofolio untuk instrumen emas. Proporsi ini dinilai optimal untuk memberikan perlindungan terhadap inflasi sekaligus menjaga keseimbangan risiko dan imbal hasil portofolio secara keseluruhan. Emas Antam dengan sertifikasi LBMA merupakan pilihan yang sangat tepat untuk memenuhi alokasi tersebut karena diakui secara internasional dan memiliki likuiditas yang tinggi di pasar.",
        "Bagi investor yang ingin memaksimalkan keuntungan dari investasi emas, penting untuk memahami siklus harga emas yang dipengaruhi oleh beberapa faktor utama. Pertama adalah nilai tukar dolar Amerika terhadap rupiah, di mana pelemahan dolar cenderung mendorong harga emas naik. Kedua adalah tingkat inflasi global, di mana inflasi tinggi biasanya membuat harga emas menguat sebagai instrumen lindung nilai. Ketiga adalah kebijakan suku bunga The Fed, di mana suku bunga rendah umumnya bersifat positif bagi harga emas.",
        "Strategi investasi emas yang paling terbukti efektif adalah pendekatan jangka panjang dengan horizon investasi minimal tiga hingga lima tahun. Data historis menunjukkan bahwa dalam periode tersebut, emas secara konsisten memberikan imbal hasil yang positif dan mampu mengalahkan tingkat inflasi. Untuk mengoptimalkan hasil investasi, kombinasikan strategi beli rutin bulanan dengan memanfaatkan momen koreksi harga untuk melakukan pembelian tambahan.",
        "Diversifikasi adalah kunci dalam manajemen portofolio investasi yang sehat. Emas Antam dapat berperan sebagai komponen defensif yang menstabilkan portofolio Anda saat instrumen investasi lain seperti saham atau reksa dana mengalami tekanan. Pastikan Anda menyimpan bukti kepemilikan emas, termasuk sertifikat keaslian dan nota pembelian, di tempat yang aman sebagai dokumentasi penting untuk kebutuhan perpajakan dan perencanaan warisan.",
        "Dari perspektif analisis teknikal, pergerakan harga emas sering kali mengikuti pola tertentu yang dapat diidentifikasi menggunakan berbagai indikator. Support dan resistance harga merupakan konsep paling dasar yang perlu dipahami oleh setiap investor emas. Ketika harga mendekati level support, itu umumnya menjadi momen yang baik untuk melakukan pembelian. Sebaliknya, ketika harga mendekati level resistance, investor perlu lebih berhati-hati dan mempertimbangkan untuk merealisasikan keuntungan sebagian.",
    ]
    historis_list = [
        f"Jika kita telusuri data historis, {hist} Rangkaian data ini memberikan gambaran yang komprehensif mengenai tren pergerakan harga emas Antam dalam berbagai horizon waktu, yang sangat berguna untuk memformulasikan strategi investasi yang tepat.",
        f"Untuk memberikan konteks yang lebih lengkap, berikut adalah rekam jejak pergerakan harga emas Antam. {hist} Dari data tersebut dapat disimpulkan bahwa emas Antam secara konsisten menunjukkan ketahanan nilai yang baik meskipun terdapat volatilitas jangka pendek.",
        f"Data historis pergerakan harga memberikan wawasan berharga bagi investor. {hist} Mencermati pola-pola historis ini membantu investor untuk mengidentifikasi siklus pasar dan menentukan waktu yang optimal untuk melakukan akumulasi maupun realisasi keuntungan.",
        f"Analisis retrospektif terhadap pergerakan harga emas Antam menunjukkan gambaran sebagai berikut. {hist} Memahami konteks historis ini sangat penting agar investor tidak bereaksi berlebihan terhadap fluktuasi jangka pendek dan tetap fokus pada tujuan investasi jangka panjang.",
        f"Tinjauan data historis pergerakan harga emas Antam memberikan perspektif yang penting. {hist} Kumpulan data ini menegaskan bahwa emas adalah instrumen investasi yang memiliki rekam jejak panjang dalam mempertahankan dan meningkatkan nilai kekayaan investor.",
    ]
    penutup = [
        f"Demikian analisis harga emas Antam hari ini dari channel {NAMA_CHANNEL}. Kami berharap informasi ini dapat menjadi landasan yang solid untuk keputusan investasi Anda. Jangan lupa untuk menekan tombol like jika analisis ini bermanfaat, berikan komentar untuk diskusi lebih lanjut, dan subscribe agar Anda selalu mendapatkan update analisis terkini setiap harinya. Sampai jumpa di sesi berikutnya, tetap bijak dalam berinvestasi.",
        f"Itulah ulasan lengkap pergerakan harga emas Antam pada hari ini dari channel {NAMA_CHANNEL}. Kami senantiasa berkomitmen untuk menghadirkan analisis yang akurat dan terpercaya untuk mendukung perjalanan investasi Anda. Klik tombol subscribe, aktifkan notifikasi, dan bagikan video ini kepada rekan-rekan yang juga peduli dengan investasi emas. Salam sukses dan sampai jumpa besok.",
        f"Sekian analisis mendalam harga emas Antam hari ini. Channel {NAMA_CHANNEL} akan terus hadir setiap hari dengan data dan analisis terkini yang dapat Anda andalkan. Berikan like sebagai apresiasi, tulis komentar jika ada pertanyaan, dan jangan lupa subscribe untuk tidak melewatkan satu pun sesi analisis kami. Terima kasih atas kepercayaan Anda.",
        f"Demikianlah laporan analisis harga emas Antam hari ini dari channel {NAMA_CHANNEL}. Informasi akurat adalah fondasi investasi yang cerdas, dan kami berkomitmen untuk selalu menyajikannya untuk Anda. Jangan lewatkan update harian kami dengan menekan tombol subscribe dan mengaktifkan lonceng notifikasi. Sampai jumpa di analisis berikutnya.",
        f"Channel {NAMA_CHANNEL} mengucapkan terima kasih atas waktu dan perhatian Anda. Semoga analisis harga emas hari ini memberikan nilai tambah nyata bagi strategi investasi Anda. Tetap ikuti kami untuk analisis harian yang konsisten, akurat, dan terpercaya. Like, comment, dan subscribe adalah dukungan terbaik yang dapat Anda berikan untuk pertumbuhan channel ini.",
    ]
    judul_list = [
        f"Analisis Harga Emas Antam {tgl} | {status} {persen}",
        f"Harga Emas Antam {tgl} - {status} {persen} | {NAMA_CHANNEL}",
        f"Update Emas Antam {tgl} | {harga} per Gram | Analisis Lengkap",
        f"Harga Emas {status} {persen} - {tgl} | Data & Analisis Terkini",
        f"Emas Antam {tgl}: {harga} per Gram | Tren {status}",
    ]
    return openings, (tren_naik if status=="naik" else tren_turun if status=="turun" else tren_stabil), tips, historis_list, penutup, judul_list


def _pool_ch2(info, harga, kemarin, selisih, persen,
              status, tgl, hist):
    """Channel 2: Update Emas Harian — santai edukatif"""
    openings = [
        f"Halo {SAPAAN}, selamat datang lagi di channel {NAMA_CHANNEL}. Yuk kita bahas bareng-bareng harga emas Antam hari ini, {tgl}, biar kamu makin pinter soal investasi emas.",
        f"Halo {SAPAAN}, ketemu lagi nih sama channel {NAMA_CHANNEL}. Hari ini, {tgl}, kita bakal update harga emas Antam terbaru plus ada tips investasi yang berguna banget buat kamu.",
        f"Halo {SAPAAN}, hai-hai, selamat datang di channel {NAMA_CHANNEL}. Kamu yang tiap hari setia nonton update emas kita, makasih ya. Yuk langsung kita cek gimana pergerakan harga emas Antam hari ini, {tgl}.",
        f"Halo {SAPAAN}, balik lagi ke channel {NAMA_CHANNEL}, tempat kamu bisa dapat info harga emas Antam setiap hari. Tanggal {tgl} ini ada update menarik yang perlu kamu tahu nih.",
        f"Halo {SAPAAN}, hei kamu yang lagi scroll-scroll video investasi, pas banget mampir ke channel {NAMA_CHANNEL}. Hari ini kita bahas update harga emas Antam tanggal {tgl} yang wajib kamu simak.",
    ]
    tren_naik = [
        f"Jadi guys, hari ini harga emas Antam naik nih. Sekarang harganya ada di {harga} per gram, naik {selisih} atau sekitar {persen} dari kemarin yang {kemarin}. Kabar bagus buat kamu yang sudah punya emas ya, nilai investasinya ikut naik juga.",
        f"Update terbaru nih, harga emas Antam hari ini berhasil menguat ke {harga} per gram. Kenaikannya lumayan, {selisih} atau {persen} dari harga kemarin di {kemarin}. Buat yang sudah investasi emas, ini kabar yang bikin senyum.",
        f"Berita baik nih buat kamu investor emas. Hari ini harga emas Antam naik ke level {harga} per gram, meningkat {persen} atau sebesar {selisih} dari kemarin yang di {kemarin}. Kenaikan ini menunjukkan permintaan emas lagi bagus.",
        f"Sesuai pantauan kita hari ini, harga emas Antam berhasil menguat ya. Posisinya sekarang di {harga} per gram, naik {selisih} alias {persen} dari kemarin yang sebesar {kemarin}. Tren positif ini perlu kamu manfaatkan dengan bijak.",
        f"Hari ini harga emas Antam kasih kabar gembira nih. Harganya naik ke {harga} per gram, tumbuh {persen} atau {selisih} dari posisi kemarin di {kemarin}. Momen naik seperti ini bisa jadi pertanda tren bullish yang menarik untuk dicermati.",
    ]
    tren_turun = [
        f"Jadi update hari ini, harga emas Antam mengalami penurunan. Sekarang harganya di {harga} per gram, turun {selisih} atau sekitar {persen} dari kemarin yang {kemarin}. Tapi tenang, ini justru bisa jadi peluang emas buat kamu yang mau beli.",
        f"Nah hari ini ada koreksi harga emas Antam. Harganya sekarang di {harga} per gram, turun {selisih} atau {persen} dari kemarin yang sebesar {kemarin}. Buat kamu yang mau mulai investasi, ini momen yang sayang dilewatkan.",
        f"Update harga emas hari ini, ada penurunan tipis nih. Harga emas Antam sekarang di {harga} per gram, koreksi {persen} atau {selisih} dari kemarin di {kemarin}. Dalam dunia investasi, koreksi seperti ini hal yang sangat normal.",
        f"Hari ini harga emas Antam mengalami sedikit penurunan, berada di {harga} per gram, turun {selisih} atau {persen} dari harga kemarin {kemarin}. Buat investor jangka panjang, ini bukan sesuatu yang perlu dikhawatirkan sama sekali.",
        f"Harga emas Antam hari ini turun ke {harga} per gram, koreksi sebesar {persen} atau {selisih} dari kemarin di {kemarin}. Penurunan ini normal dalam siklus pasar dan sering jadi momen terbaik untuk menambah kepemilikan emas.",
    ]
    tren_stabil = [
        f"Jadi hari ini harga emas Antam terpantau stabil ya. Harganya ada di {harga} per gram, nggak jauh berbeda dari kemarin yang {kemarin}. Kondisi stabil begini sebenarnya bagus karena menunjukkan pasar emas lagi sehat.",
        f"Update hari ini, harga emas Antam bergerak sideways di {harga} per gram, hampir sama dengan kemarin di {kemarin}. Buat kamu yang lagi nunggu waktu yang tepat beli emas, kondisi stabil ini bisa jadi momen yang menarik.",
        f"Harga emas Antam hari ini terpantau flat di kisaran {harga} per gram, relatif sama dengan kemarin yang {kemarin}. Stabilitas ini menunjukkan pasar sedang dalam keseimbangan, dan biasanya mendahului pergerakan yang lebih besar.",
        f"Hari ini harga emas Antam bergerak stabil di level {harga} per gram, tidak banyak berubah dari kemarin di {kemarin}. Dalam bahasa investasi, fase sideways seperti ini adalah waktu yang baik untuk akumulasi secara bertahap.",
        f"Update harga emas hari ini, Antam berada di posisi {harga} per gram, stabil dari kemarin yang {kemarin}. Kondisi ini menunjukkan emas sedang dalam fase konsolidasi yang sehat sebelum bergerak ke arah berikutnya.",
    ]
    tips = [
        "Nah, buat kamu yang masih baru dalam dunia investasi emas, ada beberapa tips penting yang perlu kamu tahu. Pertama, selalu beli emas di tempat resmi ya, jangan tergiur harga murah dari sumber yang tidak jelas. Kedua, simpan sertifikat emas kamu dengan baik karena itu penting saat kamu mau jual kembali. Ketiga, jangan panik kalau harga turun sedikit, karena investasi emas itu untuk jangka panjang dan historisnya selalu cenderung naik.",
        "Tips investasi emas yang perlu kamu tahu hari ini adalah soal metode cicil emas. Daripada beli emas dalam jumlah besar sekaligus, lebih bijak kalau kamu cicil setiap bulan meski sedikit. Misalnya beli setengah gram atau satu gram tiap bulan. Dengan cara ini kamu bisa dapat rata-rata harga yang lebih baik dan nggak perlu pusing mikirin timing yang sempurna.",
        "Kamu tahu nggak, kenapa emas Antam jadi pilihan favorit investor Indonesia? Karena emas Antam sudah tersertifikasi oleh LBMA atau London Bullion Market Association, jadi diakui kualitasnya secara internasional. Selain itu, emas Antam juga mudah dijual kembali karena market-nya sudah sangat likuid di Indonesia. Ini yang membuat emas Antam jadi instrumen investasi yang sangat terpercaya.",
        "Salah satu kesalahan yang sering dilakukan investor emas pemula adalah menjual emas terlalu cepat saat harga naik sedikit. Padahal kalau kamu tahan lebih lama, potensi keuntungannya jauh lebih besar. Data historis menunjukkan emas yang disimpan lebih dari lima tahun hampir selalu memberikan return positif yang signifikan. Jadi, sabar itu kunci utama dalam investasi emas.",
        "Perlu kamu ketahui juga bahwa selain sebagai investasi, emas juga berfungsi sebagai asuransi terhadap ketidakpastian ekonomi. Ketika kondisi ekonomi tidak menentu, nilai emas cenderung naik karena banyak investor yang beralih ke aset safe haven. Inilah kenapa punya emas dalam portofolio itu penting, bukan hanya untuk cari keuntungan tapi juga untuk melindungi kekayaan kamu dari risiko sistemik.",
    ]
    historis_list = [
        f"Nah buat gambaran lebih lengkap, yuk kita tengok data historis pergerakan harga emas Antam. {hist} Data-data ini berguna banget buat kamu yang mau tahu tren jangka panjang sebelum memutuskan investasi.",
        f"Biar makin paham kondisi pasar emas secara keseluruhan, kita intip data historisnya dulu ya. {hist} Dari sini kamu bisa lihat sendiri bagaimana emas selalu punya nilai yang terjaga dari waktu ke waktu.",
        f"Supaya kamu nggak cuma lihat data hari ini tapi juga punya perspektif yang lebih luas, coba kita cek tren historis harga emas Antam. {hist} Menarik kan, gimana emas terus menunjukkan ketangguhannya sebagai instrumen investasi.",
        f"Untuk melengkapi analisis kita hari ini, mari kita lihat bagaimana pergerakan harga emas di masa-masa sebelumnya. {hist} Dengan memahami pola historis ini, kamu bisa lebih confident dalam mengambil keputusan investasi.",
        f"Data historis selalu jadi bahan bakar penting buat keputusan investasi yang cerdas. Ini dia rekap pergerakan harga emas Antam belakangan ini. {hist} Sekarang kamu punya gambaran yang jauh lebih komprehensif kan.",
    ]
    penutup = [
        f"Oke deh, segitu dulu update harga emas Antam hari ini dari channel {NAMA_CHANNEL}. Semoga infonya bermanfaat buat perjalanan investasi kamu ya. Kalau kamu suka video ini, jangan lupa like dan subscribe biar nggak ketinggalan update emas setiap harinya. Ketemu lagi besok.",
        f"Nah itu tadi update lengkap harga emas Antam hari ini dari {NAMA_CHANNEL}. Terus belajar, terus investasi, dan jangan pernah berhenti mengembangkan diri. Like video ini kalau bermanfaat, tulis pertanyaan di kolom komentar, dan subscribe ya. Sampai jumpa besok.",
        f"Gimana, sudah dapat insight berharga dari update hari ini? Channel {NAMA_CHANNEL} akan terus hadir setiap hari buat kasih kamu informasi terkini harga emas Antam. Tinggalkan like, komentar, dan jangan lupa subscribe. Salam cuan.",
        f"Itu dia update harga emas Antam hari ini. Terima kasih sudah nonton sampai habis, itu tandanya kamu serius dalam berinvestasi. Channel {NAMA_CHANNEL} bangga punya penonton seperti kamu. Subscribe dan aktifkan notifikasi biar nggak ketinggalan ya.",
        f"Yuk terus semangat investasi emasnya. Channel {NAMA_CHANNEL} bakal terus menemani perjalanan investasi kamu setiap hari. Share video ini ke teman-teman kamu yang mau mulai investasi emas, dan jangan lupa subscribe. Sampai jumpa di update berikutnya.",
    ]
    judul_list = [
        f"Update Harga Emas Antam {tgl} | {harga} per Gram",
        f"Emas Antam Hari Ini {tgl} | {status.title()} {persen}",
        f"Harga Emas {tgl} Terbaru | Antam {harga} per Gram",
        f"Cek Harga Emas Antam {tgl} | Update Harian",
        f"Emas Naik atau Turun? Update {tgl} | {NAMA_CHANNEL}",
    ]
    return openings, (tren_naik if status=="naik" else tren_turun if status=="turun" else tren_stabil), tips, historis_list, penutup, judul_list


def _pool_ch3(info, harga, kemarin, selisih, persen,
              status, tgl, hist):
    """Channel 3: Info Logam Mulia — berita singkat"""
    openings = [
        f"Halo {SAPAAN}, selamat menyaksikan Info Logam Mulia bersama channel {NAMA_CHANNEL}. Inilah laporan harga emas Antam terkini untuk hari ini, {tgl}.",
        f"Halo {SAPAAN}, ini adalah {NAMA_CHANNEL}. Kami hadir dengan laporan singkat dan informatif mengenai pergerakan harga emas Antam pada hari ini, {tgl}.",
        f"Halo {SAPAAN}, Anda menyaksikan channel {NAMA_CHANNEL}. Berikut kami sampaikan laporan terkini harga emas Antam tanggal {tgl} yang penting untuk diketahui.",
        f"Halo {SAPAAN}, selamat bergabung di channel {NAMA_CHANNEL}. Hari ini, {tgl}, kami melaporkan perkembangan terbaru harga emas Antam langsung dari sumber resmi.",
        f"Halo {SAPAAN}, Anda bersama channel {NAMA_CHANNEL}. Berikut laporan harga logam mulia hari ini, {tgl}, yang kami rangkum secara singkat dan akurat untuk Anda.",
    ]
    tren_naik = [
        f"Laporan: Harga emas Antam hari ini tercatat naik ke level {harga} per gram. Kenaikan sebesar {selisih} atau {persen} dari harga kemarin di {kemarin}. Penguatan ini seiring meningkatnya minat investor terhadap aset safe haven.",
        f"Data terkini: Emas Antam menguat ke {harga} per gram hari ini, naik {persen} atau {selisih} dari sesi sebelumnya di {kemarin}. Momentum positif ini didukung oleh permintaan yang solid dari pasar domestik.",
        f"Breaking update: Harga emas Antam hari ini bergerak naik ke posisi {harga} per gram. Kenaikan {selisih} atau {persen} dari kemarin yang sebesar {kemarin} mencerminkan sentimen pasar yang bullish terhadap emas.",
        f"Informasi terbaru: Emas Antam hari ini menguat {persen} ke level {harga} per gram, meningkat {selisih} dari penutupan kemarin di {kemarin}. Penguatan ini konsisten dengan tren regional pasar emas.",
        f"Update pasar: Emas Antam mencatatkan kenaikan hari ini, berada di {harga} per gram, naik {selisih} atau {persen} dari kemarin di {kemarin}. Investor emas domestik mencatat keuntungan dari pergerakan positif ini.",
    ]
    tren_turun = [
        f"Laporan: Harga emas Antam hari ini tercatat turun ke {harga} per gram. Koreksi sebesar {selisih} atau {persen} dari harga kemarin di {kemarin}. Penurunan ini dipandang sebagai koreksi teknikal yang wajar.",
        f"Data terkini: Emas Antam terkoreksi ke {harga} per gram hari ini, turun {persen} atau {selisih} dari sesi sebelumnya di {kemarin}. Koreksi ini membuka peluang bagi investor untuk melakukan akumulasi.",
        f"Update pasar: Harga emas Antam hari ini mengalami tekanan ke posisi {harga} per gram, turun {selisih} atau {persen} dari kemarin yang sebesar {kemarin}. Analis melihat ini sebagai koreksi sehat dalam tren jangka panjang.",
        f"Informasi terbaru: Emas Antam melemah {persen} ke level {harga} per gram hari ini, turun {selisih} dari penutupan kemarin di {kemarin}. Meski terkoreksi, fundamental emas jangka panjang tetap positif.",
        f"Laporan harian: Emas Antam hari ini berada di {harga} per gram, turun {selisih} atau {persen} dari kemarin di {kemarin}. Penurunan ini wajar dan tidak mengubah tren jangka panjang emas yang cenderung positif.",
    ]
    tren_stabil = [
        f"Laporan: Harga emas Antam hari ini bergerak stabil di level {harga} per gram, hampir tidak berubah dari kemarin di {kemarin}. Pasar emas berada dalam fase konsolidasi.",
        f"Data terkini: Emas Antam hari ini terpantau flat di {harga} per gram, relatif sama dengan kemarin di {kemarin}. Kondisi ini mencerminkan keseimbangan pasar yang sementara.",
        f"Update pasar: Harga emas Antam hari ini sideways di {harga} per gram, tidak banyak berubah dari sesi sebelumnya di {kemarin}. Pasar menunggu katalis baru untuk arah selanjutnya.",
        f"Informasi terbaru: Emas Antam bergerak konsolidasi di {harga} per gram hari ini, stabil dari kemarin di {kemarin}. Fase sideways ini normal dalam siklus pasar emas.",
        f"Laporan harian: Emas Antam hari ini di posisi {harga} per gram, stabil dibandingkan kemarin di {kemarin}. Konsolidasi harga mengindikasikan pasar sedang mencari arah baru.",
    ]
    tips = [
        "Perlu diketahui oleh masyarakat, emas Antam tersedia dalam berbagai ukuran mulai dari setengah gram hingga seribu gram. Bagi investor pemula, ukuran satu gram hingga sepuluh gram paling direkomendasikan karena lebih terjangkau dan mudah dicairkan kembali saat dibutuhkan.",
        "Informasi penting bagi investor: Harga emas Antam yang dilaporkan adalah harga buyback resmi dari PT Antam. Selisih antara harga beli dan harga jual kembali perlu diperhitungkan dalam kalkulasi keuntungan investasi Anda.",
        "Masyarakat perlu mengetahui bahwa investasi emas fisik berbeda dengan investasi emas digital. Emas fisik memberikan ketenangan bagi investor yang menginginkan aset nyata yang dapat dipegang, sementara emas digital lebih likuid dan mudah ditransaksikan kapan saja.",
        "Catatan penting: Harga emas Antam diperbarui setiap hari kerja. Pada hari libur dan weekend, harga mengacu pada harga terakhir yang berlaku. Pantau terus channel ini untuk mendapatkan informasi harga terkini setiap harinya.",
        "Edukasi investasi: Emas adalah salah satu dari sedikit aset yang memiliki nilai intrinsik. Berbeda dengan mata uang yang nilainya ditentukan oleh kebijakan pemerintah, nilai emas ditentukan oleh pasar global yang tidak dapat dimanipulasi oleh satu pihak manapun.",
    ]
    historis_list = [
        f"Data historis untuk referensi: {hist} Informasi ini dapat digunakan sebagai acuan dalam menentukan strategi investasi emas Anda.",
        f"Rekap pergerakan historis: {hist} Data-data ini penting untuk memahami tren jangka menengah dan panjang pasar emas Antam.",
        f"Untuk konteks yang lebih lengkap, berikut data historis pergerakan: {hist} Tren ini mencerminkan dinamika pasar emas yang perlu dipahami setiap investor.",
        f"Laporan historis: {hist} Rangkaian data ini memberikan gambaran komprehensif mengenai volatilitas dan tren pasar emas Antam.",
        f"Sebagai referensi, berikut rekam jejak harga: {hist} Data ini menjadi bukti ketahanan emas sebagai instrumen investasi jangka panjang.",
    ]
    penutup = [
        f"Demikian laporan harga logam mulia hari ini dari channel {NAMA_CHANNEL}. Pantau terus channel ini untuk update harga emas Antam setiap hari. Berikan like, subscribe, dan bagikan kepada rekan yang membutuhkan informasi ini. Terima kasih.",
        f"Itulah laporan singkat harga emas Antam hari ini. Channel {NAMA_CHANNEL} hadir setiap hari memberikan informasi akurat dan terpercaya. Jangan lupa subscribe untuk mendapatkan notifikasi update terbaru. Sampai jumpa.",
        f"Sekian laporan harga logam mulia dari channel {NAMA_CHANNEL}. Untuk informasi investasi terpercaya setiap hari, tetap ikuti channel kami. Tekan tombol subscribe dan aktifkan notifikasi. Terima kasih telah menyaksikan.",
        f"Laporan hari ini dari {NAMA_CHANNEL} sampai di sini. Kami berkomitmen menyajikan informasi harga emas yang akurat dan tepat waktu setiap hari. Subscribe, like, dan bagikan untuk mendukung channel ini. Sampai besok.",
        f"Dari {NAMA_CHANNEL}, demikian laporan harga emas Antam hari ini. Kami hadir konsisten setiap hari untuk Anda. Dukung kami dengan like dan subscribe. Informasi ini gratis dan selalu akurat. Terima kasih dan sampai jumpa.",
    ]
    judul_list = [
        f"Harga Emas Antam {tgl} | {status.title()} {persen} | Info Logam Mulia",
        f"Laporan Emas {tgl} | Antam {harga} per Gram",
        f"Info Logam Mulia {tgl} | Harga Emas {status.title()}",
        f"Update Harga Emas {tgl} | {harga} per Gram | Antam",
        f"Emas Antam {tgl}: {harga} | {status.title()} {persen}",
    ]
    return openings, (tren_naik if status=="naik" else tren_turun if status=="turun" else tren_stabil), tips, historis_list, penutup, judul_list


def _pool_ch4(info, harga, kemarin, selisih, persen,
              status, tgl, hist):
    """Channel 4: Harga Emas Live — energik motivatif"""
    openings = [
        f"Halo {SAPAAN}! Selamat datang di channel {NAMA_CHANNEL}, channel paling update soal harga emas di Indonesia! Hari ini, {tgl}, ada update harga emas Antam yang WAJIB kamu tahu!",
        f"Halo {SAPAAN}! Yeay, ketemu lagi di channel {NAMA_CHANNEL}! Tanggal {tgl} ini ada kabar terbaru soal harga emas Antam yang bakal bikin kamu makin semangat berinvestasi!",
        f"Halo {SAPAAN}! Welcome back di channel {NAMA_CHANNEL}! Siap-siap dapat informasi harga emas Antam terbaru hari ini, {tgl}, yang sudah kami rangkum khusus buat kamu!",
        f"Halo {SAPAAN}! Ini dia channel {NAMA_CHANNEL}, one stop solution buat informasi harga emas harian kamu! Langsung aja kita bahas update seru harga emas Antam hari ini, {tgl}!",
        f"Halo {SAPAAN}! Kamu udah di tempat yang tepat! Channel {NAMA_CHANNEL} hadir lagi hari ini, {tgl}, dengan update harga emas Antam terkini yang akan bikin langkah investasimu makin mantap!",
    ]
    tren_naik = [
        f"NAIK! Harga emas Antam hari ini MENGUAT ke level {harga} per gram! Kenaikannya mencapai {selisih} atau {persen} dari kemarin yang berada di {kemarin}! Ini sinyal positif yang luar biasa buat para investor emas!",
        f"KABAR BAGUS! Emas Antam hari ini berhasil naik ke {harga} per gram, menguat {persen} atau {selisih} dari kemarin di {kemarin}! Buat kamu yang sudah pegang emas, selamat, nilai investasimu sedang bertumbuh!",
        f"POSITIF! Harga emas Antam hari ini ada di {harga} per gram, naik {selisih} atau {persen} dari kemarin yang sebesar {kemarin}! Momentum ini harus dimanfaatkan dengan strategi yang tepat!",
        f"WOW, emas naik! Hari ini emas Antam mencatatkan penguatan ke {harga} per gram, naik {persen} alias {selisih} dari {kemarin}! Tren positif ini membuktikan emas adalah investasi yang tidak pernah mengecewakan!",
        f"MANTAP! Emas Antam hari ini kembali menunjukkan tajinya dengan naik ke {harga} per gram! Kenaikan {selisih} atau {persen} dari kemarin di {kemarin} ini membuktikan emas selalu punya cara untuk bertumbuh!",
    ]
    tren_turun = [
        f"KOREKSI! Harga emas Antam hari ini turun ke {harga} per gram, terkoreksi {selisih} atau {persen} dari kemarin di {kemarin}. Tapi JANGAN PANIK! Ini justru peluang EMAS yang tidak boleh kamu lewatkan!",
        f"ADA KOREKSI! Emas Antam hari ini berada di {harga} per gram, turun {persen} atau {selisih} dari kemarin yang sebesar {kemarin}. Buat investor cerdas, ini adalah SINYAL BELI yang ditunggu-tunggu!",
        f"TURUN SEDIKIT! Emas Antam hari ini di {harga} per gram, koreksi {selisih} atau {persen} dari {kemarin}. Tapi ingat, setiap penurunan adalah KESEMPATAN EMAS bagi mereka yang berani berinvestasi!",
        f"KOREKSI SEHAT! Harga emas Antam hari ini terkoreksi ke {harga} per gram, turun {persen} atau {selisih} dari kemarin di {kemarin}. Investor cerdas tahu bahwa koreksi adalah HADIAH dari pasar!",
        f"DISKON EMAS! Hari ini emas Antam ada di {harga} per gram, turun {selisih} atau {persen} dari kemarin yang {kemarin}. Mau dapat emas di harga lebih murah? Sekarang waktunya untuk bergerak!",
    ]
    tren_stabil = [
        f"STABIL! Harga emas Antam hari ini berada di {harga} per gram, relatif sama dengan kemarin di {kemarin}. Kondisi sideways seperti ini adalah MOMEN TERBAIK untuk akumulasi sebelum harga bergerak lagi!",
        f"KONSOLIDASI! Emas Antam hari ini sideways di {harga} per gram, hampir sama dengan {kemarin}. Buat investor jangka panjang, ini adalah WAKTU EMAS untuk menambah kepemilikan!",
        f"FLAT TAPI KUAT! Emas Antam hari ini di {harga} per gram, stabil dari kemarin di {kemarin}. Jangan remehkan kondisi sideways karena ini sering menjadi MEDAN PERSIAPAN sebelum kenaikan besar!",
        f"TENANG SEBELUM BADAI! Emas Antam hari ini stabil di {harga} per gram, tidak banyak berubah dari {kemarin}. Fase konsolidasi ini bisa jadi tanda KENAIKAN BESAR yang akan segera datang!",
        f"SIDEWAYS! Emas Antam hari ini ada di {harga} per gram, stabil dari kemarin yang {kemarin}. Kondisi ini adalah peluang LUAR BIASA buat kamu yang mau mulai atau menambah investasi emas!",
    ]
    tips = [
        "Kamu tahu nggak, orang-orang yang berhasil membangun kekayaan jangka panjang hampir selalu punya emas dalam portofolio mereka? Emas bukan cuma perhiasan, ini adalah ASET SEJATI yang nilainya terus terjaga dari generasi ke generasi. Mulai sekarang, jadikan emas sebagai bagian dari rencana keuangan jangka panjang kamu!",
        "Tips investasi emas dari para ahli: Jangan pernah investasi dengan uang yang kamu butuhkan dalam waktu dekat. Emas adalah investasi jangka panjang minimal tiga hingga lima tahun. Tapi kalau kamu konsisten, hasilnya bisa luar biasa! Data historis membuktikan emas mampu memberikan return rata-rata 10 hingga 15 persen per tahun dalam jangka panjang.",
        "Satu hal yang membedakan investor sukses dari yang biasa adalah KONSISTENSI! Beli emas rutin setiap bulan, meski sedikit. Namanya strategi dollar cost averaging, dan ini TERBUKTI efektif mengurangi risiko dan memaksimalkan keuntungan jangka panjang. Mulai dari satu gram per bulan pun sudah luar biasa!",
        "Emas Antam adalah pilihan terbaik untuk investasi emas fisik di Indonesia karena sudah tersertifikasi LBMA, diakui internasional, dan sangat mudah dijual kembali. Jangan mau rugi dengan beli emas yang tidak bersertifikat resmi! Pastikan setiap gram emas yang kamu beli punya sertifikat yang valid.",
        "Motivasi hari ini: Warren Buffett bilang harga terbaik untuk mulai berinvestasi adalah SEKARANG, bukan besok, bukan minggu depan. Kalau kamu masih nunda-nunda mulai investasi emas, kamu sedang membiarkan inflasi memakan nilai uangmu. Jangan biarkan itu terjadi! Mulai investasi emas hari ini, sekecil apapun jumlahnya.",
    ]
    historis_list = [
        f"Data historis MEMBUKTIKAN ketangguhan emas sebagai investasi! {hist} Angka-angka ini bukan sekadar data, ini BUKTI NYATA bahwa emas selalu memberikan nilai terbaik dari waktu ke waktu!",
        f"Mau tahu betapa konsistennya emas sebagai investasi? Lihat data historis ini! {hist} LUAR BIASA kan? Inilah mengapa emas selalu menjadi pilihan cerdas para investor di seluruh dunia!",
        f"Fakta historis yang harus kamu tahu sebelum berinvestasi. {hist} Data ini membuktikan bahwa emas bukan sekadar logam, tapi MESIN PENGHASIL KEKAYAAN yang teruji oleh waktu!",
        f"Biar makin yakin untuk berinvestasi emas, simak rekap historis pergerakan harga berikut. {hist} Data ini harusnya makin membakar semangat investasi kamu!",
        f"Rekam jejak emas yang tidak pernah berbohong! {hist} Ini bukan teori, ini FAKTA berdasarkan data yang bisa kamu verifikasi sendiri. Emas adalah investasi terbaik sepanjang masa!",
    ]
    penutup = [
        f"Itulah update harga emas Antam hari ini dari channel {NAMA_CHANNEL}! Semoga informasi ini menyalakan semangat investasi kamu makin membara! Jangan lupa LIKE, COMMENT, dan SUBSCRIBE untuk tetap update! Salam sukses dan sampai jumpa di video berikutnya!",
        f"Oke guys, itu tadi update terkini harga emas dari channel {NAMA_CHANNEL}! Tetap semangat, tetap konsisten, dan tetap investasi! Kalau bermanfaat, sebarkan ke teman-teman kamu ya! LIKE dan SUBSCRIBE sekarang! Sampai jumpa!",
        f"Mantap sekali perjalanan investasi kamu hari ini bersama channel {NAMA_CHANNEL}! Ingat, kesuksesan finansial dimulai dari satu langkah kecil yang konsisten. SUBSCRIBE sekarang dan jadilah bagian dari komunitas investor emas cerdas bersama kami!",
        f"Terima kasih sudah nonton sampai habis, itu tandanya kamu SERIUS dalam berinvestasi! Channel {NAMA_CHANNEL} bangga punya penonton seperti kamu. Jangan lupa LIKE, SUBSCRIBE, dan share ke teman yang butuh info ini!",
        f"Update hari ini dari {NAMA_CHANNEL} sampai di sini! Terus semangat investasinya ya, masa depan finansial yang cerah menunggu kamu! Tekan SUBSCRIBE dan LONCENG notifikasi agar tidak ketinggalan satu pun update dari kami! Sampai jumpa!",
    ]
    judul_list = [
        f"HARGA EMAS ANTAM {tgl} | {status.upper()} {persen} | Live Update",
        f"Emas Antam {status.title()} {persen} Hari Ini {tgl} | Harga Emas Live",
        f"UPDATE EMAS {tgl} | {harga} per Gram | {status.title()} {persen}",
        f"Harga Emas LIVE {tgl} | Antam {harga} | {status.title()}",
        f"NAIK ATAU TURUN? Harga Emas Antam {tgl} | Update Live",
    ]
    return openings, (tren_naik if status=="naik" else tren_turun if status=="turun" else tren_stabil), tips, historis_list, penutup, judul_list


def _pool_ch5(info, harga, kemarin, selisih, persen,
              status, tgl, hist):
    """Channel 5: Cek Harga Emas — percakapan akrab"""
    openings = [
        f"Halo {SAPAAN}, eh kamu dateng juga nih ke channel {NAMA_CHANNEL}. Asyik deh, berarti kamu juga peduli sama investasi emas kayak aku. Yuk, kita ngobrol santai soal harga emas Antam hari ini, {tgl}.",
        f"Halo {SAPAAN}, hei hei, welcome back di channel {NAMA_CHANNEL}! Gimana hari ini, udah cek harga emas belum? Belum? Pas banget nih, hari ini, {tgl}, kita bahas bareng-bareng yuk.",
        f"Halo {SAPAAN}, seneng banget kamu mampir ke channel {NAMA_CHANNEL}. Hari ini, {tgl}, kita ngobrol santai soal harga emas Antam terbaru. Duduk yang nyaman dulu ya, karena ada banyak info seru.",
        f"Halo {SAPAAN}, hai, kamu yang lagi penasaran sama harga emas Antam hari ini, {tgl}, kamu udah di tempat yang bener nih. Channel {NAMA_CHANNEL} siap kasih semua info yang kamu butuhin.",
        f"Halo {SAPAAN}, apa kabar nih? Semoga lagi baik-baik aja ya. Channel {NAMA_CHANNEL} hadir lagi hari ini, {tgl}, buat nemenin kamu ngecek harga emas Antam terbaru. Yuk langsung kita mulai.",
    ]
    tren_naik = [
        f"Jadi begini ceritanya, harga emas Antam hari ini naik nih sahabat. Sekarang harganya ada di {harga} per gram, naik {selisih} dari kemarin yang {kemarin}. Persentasenya {persen}. Lumayan kan? Buat kamu yang sudah punya emas, pasti seneng banget nih nilai investasinya bertambah.",
        f"Nah ini dia kabar yang ditunggu-tunggu, harga emas Antam hari ini naik ke {harga} per gram. Dari kemarin yang {kemarin}, naik {selisih} alias {persen} nih. Sebenernya sih ini bukan kejutan, karena emas memang punya tren jangka panjang yang positif.",
        f"Harga emas Antam hari ini lagi bagus-bagusnya nih, berada di {harga} per gram. Naik {persen} atau {selisih} dari kemarin yang di {kemarin}. Kalau aku jadi kamu, aku bakal seneng banget lihat angka ini. Artinya investasi emas kita lagi berbuah manis.",
        f"Sahabat, harga emas Antam hari ini menguat ke {harga} per gram ya. Dari kemarin {kemarin}, naik {selisih} atau {persen}. Tipis memang, tapi setiap kenaikan itu berarti nilai tabungan emas kamu bertambah. Itu yang namanya efek compounding dalam investasi emas.",
        f"Hari ini emas Antam kasih kabar baik, harganya naik ke {harga} per gram. Kenaikan sebesar {selisih} atau {persen} dari kemarin di {kemarin}. Buat teman-teman yang baru mau mulai investasi emas, hari ini juga masih saat yang bagus kok.",
    ]
    tren_turun = [
        f"Jujur aja nih, hari ini harga emas Antam turun sedikit. Ada di {harga} per gram, turun {selisih} dari kemarin yang {kemarin}. Persentasenya {persen}. Tapi hey, santai aja, ini bukan sesuatu yang perlu dipanikkan. Justru ini momen buat kamu yang mau tambah koleksi emas.",
        f"Harga emas Antam hari ini ada di {harga} per gram, turun {persen} atau {selisih} dari kemarin yang {kemarin}. Aku ngerti kalau kamu mungkin sedikit khawatir. Tapi percaya deh, dalam investasi jangka panjang, penurunan seperti ini itu hal yang sangat normal.",
        f"Nah hari ini harga emas Antam turun nih, ke level {harga} per gram. Turunnya {selisih} atau {persen} dari kemarin di {kemarin}. Tapi kalau boleh aku share perspektif, penurunan harga emas itu artinya kamu bisa beli lebih banyak gram dengan uang yang sama.",
        f"Harga emas Antam hari ini koreksi sedikit ke {harga} per gram, dari kemarin yang {kemarin}, turun {selisih} alias {persen}. Jangan langsung patah semangat ya, karena trader dan investor kawakan justru nunggu momen kayak gini untuk beli lebih banyak.",
        f"Update hari ini, harga emas Antam ada di {harga} per gram nih, turun {persen} atau {selisih} dari kemarin di {kemarin}. Buat aku pribadi, setiap penurunan harga emas itu kayak diskon belanja. Momen terbaik untuk tambah koleksi.",
    ]
    tren_stabil = [
        f"Harga emas Antam hari ini anteng nih sahabat, ada di {harga} per gram. Hampir sama dengan kemarin yang {kemarin}. Kalau kata orang investasi, kondisi sideways begini itu sebenarnya bagus untuk akumulasi perlahan-lahan.",
        f"Hari ini harga emas Antam adem ayem di {harga} per gram, nggak jauh dari kemarin yang {kemarin}. Buat aku ini malah enak, artinya nggak ada fluktuasi besar yang bikin bingung. Waktu yang pas buat nabung emas rutin.",
        f"Nah update hari ini, harga emas Antam stabil di {harga} per gram, hampir sama kayak kemarin di {kemarin}. Kondisi flat seperti ini sebenarnya friendly banget buat investor jangka panjang yang pengen beli tanpa khawatir beli di puncak harga.",
        f"Harga emas Antam hari ini kalem nih, di {harga} per gram, relatif sama dengan kemarin {kemarin}. Kalau kamu nanya kapan waktu terbaik beli emas, menurutku kondisi sideways seperti sekarang adalah salah satu waktu yang paling aman.",
        f"Cerita harga emas hari ini, Antam ada di {harga} per gram, stabil dari kemarin yang {kemarin}. Nggak naik nggak turun, tapi justru ini yang aku suka. Harga yang stabil itu bikin kita lebih mudah merencanakan investasi secara teratur.",
    ]
    tips = [
        "Oh iya, aku mau share satu tips yang menurut aku paling penting dalam investasi emas. Jangan pernah bandingkan harga emas hari ini dengan harga seminggu lalu dan langsung panik. Yang harus kamu bandingkan adalah harga emas sekarang dengan harga emas setahun atau lima tahun lalu. Di situ kamu bakal lihat betapa konsistennya emas dalam menjaga dan menumbuhkan nilai.",
        "Ngomong-ngomong soal investasi emas, ada hal yang sering ditanyain ke aku. Mending beli emas fisik atau emas digital? Jawabannya tergantung tujuan kamu. Kalau mau pegangan fisik dan tidak masalah bayar biaya cetak, emas Antam fisik adalah pilihan terbaik. Kalau mau lebih fleksibel dan mudah ditransaksikan, emas digital bisa jadi alternatif. Tapi untuk proteksi jangka panjang, emas fisik selalu jadi pilihan utamaku.",
        "Aku mau cerita sesuatu yang aku pelajari dari pengalaman investasi emas. Kunci suksesnya bukan di timing yang sempurna, tapi di konsistensi dan kesabaran. Orang yang beli emas rutin selama sepuluh tahun, tidak peduli harga naik atau turun, hampir pasti meraih keuntungan yang signifikan. Konsistensi mengalahkan kecerdasan dalam investasi jangka panjang.",
        "Tips praktis nih dari aku, kalau mau mulai investasi emas tapi bingung mulai dari mana, coba target satu gram per bulan dulu. Dengan harga sekitar tiga juta rupiah, itu setara dengan seratus ribu rupiah per hari. Lebih murah dari secangkir kopi di kafe mahal, tapi dampaknya buat masa depan finansial kamu jauh lebih besar.",
        "Satu hal yang bikin emas berbeda dari instrumen investasi lain adalah sifatnya sebagai aset universal. Emas dihargai di seluruh penjuru dunia, dari Indonesia sampai Amerika, dari Asia sampai Eropa. Tidak ada mata uang atau aset lain yang punya pengakuan universal seperti emas. Ini yang membuat emas tetap relevan sebagai investasi bahkan di tengah ketidakpastian ekonomi global sekalipun.",
    ]
    historis_list = [
        f"Biar kamu punya gambaran yang lebih utuh, kita tengok dulu yuk pergerakan harga emas di masa lalu. {hist} Kalau dilihat dari data ini, kamu bisa makin yakin bahwa emas itu memang bisa diandalkan sebagai instrumen investasi jangka panjang.",
        f"Aku mau ajak kamu lihat data historis harga emas supaya kamu tidak cuma fokus ke pergerakan hari ini. {hist} Menarik kan? Setiap periode punya ceritanya sendiri, tapi kesimpulannya tetap sama, emas itu investasi yang solid.",
        f"Yuk kita lihat bareng-bareng rekap harga emas di periode sebelumnya, biar kamu dapat perspektif yang lebih luas. {hist} Dari data ini kamu bisa lihat sendiri betapa tangguhnya emas dalam menghadapi berbagai kondisi ekonomi.",
        f"Nggak lengkap kalau kita bahas harga hari ini tanpa lihat konteks historisnya juga. Ini dia datanya. {hist} Gimana menurut kamu? Menurutku ini membuktikan bahwa emas adalah teman setia dalam perjalanan investasi jangka panjang.",
        f"Data historis ini aku bagikan bukan untuk bikin kamu pusing, tapi justru untuk kasih kamu keyakinan lebih dalam berinvestasi emas. {hist} Setelah lihat data ini, kamu harusnya makin mantap dan percaya diri dengan pilihan investasi emas kamu.",
    ]
    penutup = [
        f"Nah, segitu dulu obrolan kita hari ini tentang harga emas Antam di channel {NAMA_CHANNEL}. Semoga ngobrol santai ini bermanfaat dan makin memantapkan langkah investasi kamu. Kalau ada pertanyaan, tulis di kolom komentar ya, aku baca semua. Jangan lupa like dan subscribe biar kita bisa ngobrol lagi besok.",
        f"Makasih banget udah nemenin aku ngobrol soal emas hari ini di channel {NAMA_CHANNEL}. Semoga obrolan santai ini ngasih insight baru buat investasi kamu. Sampai besok ya, jaga kesehatan dan tetap semangat berinvestasi. Like dan subscribe dulu sebelum pergi.",
        f"Oke sahabat, kita tutup obrolan hari ini sampai di sini dulu. Channel {NAMA_CHANNEL} akan balik lagi besok dengan update harga emas dan obrolan seru lainnya. Kalau bermanfaat, share ke teman yang lagi galau mau mulai investasi emas. Sampai jumpa.",
        f"Itulah cerita emas hari ini dari channel {NAMA_CHANNEL}. Aku harap kamu dapet value yang nyata dari obrolan kita hari ini. Jangan sungkan subscribe dan aktifkan notifikasi ya, biar kita bisa terus ngobrol bareng setiap hari. Salam hangat dan sampai jumpa.",
        f"Hari ini kita udah ngobrol panjang lebar soal harga emas Antam bersama channel {NAMA_CHANNEL}. Terima kasih sudah jadi bagian dari komunitas investor emas yang cerdas dan konsisten. Tinggalkan like, subscribe, dan bagikan ke sesama sahabat investor. Sampai ketemu di obrolan berikutnya.",
    ]
    judul_list = [
        f"Cek Harga Emas Antam {tgl} | {harga} per Gram",
        f"Harga Emas Hari Ini {tgl} | {status.title()} {persen} | Antam",
        f"Ngecek Emas Antam {tgl} | Update Harga Terbaru",
        f"Harga Emas Antam {tgl}: {harga} per Gram | {status.title()}",
        f"Update Santai Harga Emas {tgl} | Antam {harga}",
    ]
    return openings, (tren_naik if status=="naik" else tren_turun if status=="turun" else tren_stabil), tips, historis_list, penutup, judul_list


# ════════════════════════════════════════════════════════════
# MAIN FALLBACK
# ════════════════════════════════════════════════════════════

def _buat_narasi_fallback(info):
    harga   = rp(info["harga_sekarang"])
    kemarin = rp(info["harga_kemarin"])
    selisih = rp(info["selisih"])
    status  = info["status"].lower()
    persen  = f"{info['persen']:.2f}"
    tgl     = info["tanggal"]

    # Bangun teks historis
    hist_parts = []
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
            hist_parts.append(
                f"Dalam {label}, harga emas Antam "
                f"tercatat {ar} sebesar "
                f"{abs(d['persen']):.2f} persen "
                f"dengan selisih {rp(abs(d['selisih']))}."
            )
    hist = " ".join(hist_parts) if hist_parts else \
           "Data historis belum tersedia saat ini."

    # Pilih pool berdasarkan CHANNEL_ID
    pool_fn = {
        1: _pool_ch1,
        2: _pool_ch2,
        3: _pool_ch3,
        4: _pool_ch4,
        5: _pool_ch5,
    }.get(CHANNEL_ID, _pool_ch1)

    openings, trens, tips, historis_list, penutup, judul_list = \
        pool_fn(info, harga, kemarin, selisih, persen,
                status, tgl, hist)

    opening      = random.choice(openings)
    tren_para    = random.choice(trens)
    tips_para    = random.choice(tips)
    historis_para = random.choice(historis_list)
    penutup_para = random.choice(penutup)
    judul        = random.choice(judul_list)

    narasi = f"""{opening}

{tren_para}

{historis_para}

{tips_para}

Sebelum kita akhiri, ada beberapa hal penting yang perlu selalu diingat dalam perjalanan investasi emas. Pertama, pastikan selalu beli emas dari sumber yang terpercaya dan resmi seperti butik Antam, platform emas digital berlisensi, atau toko emas terpercaya yang menjual emas bersertifikat. Kedua, simpan emas dan sertifikatnya di tempat yang aman karena sertifikat adalah bukti keaslian yang sangat penting. Ketiga, pantau harga emas secara rutin namun jangan terlalu sering mengambil keputusan berdasarkan fluktuasi harian yang bersifat jangka pendek.

Ingatlah bahwa investasi emas adalah maraton, bukan sprint. Kesabaran dan konsistensi adalah dua kunci utama yang membedakan investor emas yang sukses dari yang tidak. Setiap gram emas yang kamu miliki adalah langkah nyata menuju kebebasan finansial yang kamu impikan.

{penutup_para}"""

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

