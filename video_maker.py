# =============================================================
# AUTO VIDEO EMAS - FULL AUTOMATION
# Update Emas Nusantara
# =============================================================
import sys
import subprocess
import os
import glob
import random
import re
import json
import shutil
import time
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Auto-install dependencies ────────────────────────────────
def pastikan_library_terinstall():
    cek = ['requests', 'beautifulsoup4', 'edge-tts',
           'google-api-python-client', 'google-auth-oauthlib']
    try:
        import requests
        from bs4 import BeautifulSoup
        import edge_tts
        from googleapiclient.discovery import build
    except ImportError:
        print("Menginstal library yang dibutuhkan...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", *cek])

pastikan_library_terinstall()

import requests
from bs4 import BeautifulSoup

# ============================================================
# !! PENGATURAN UTAMA - ISI BAGIAN INI !!
# ============================================================
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY",  "AIzaSyByVL2l_ztr8Qar1jXMN3iwa07kB8SEUsA")
PEXELS_API_KEY    = os.environ.get("PEXELS_API_KEY",  "NWTuol4cK2LArc6FynRtRFwg9i9dySJxFe1yYiCqi6Eobu0UR0oTeNOR")
NAMA_CHANNEL      = "Sobat Emas"
FFMPEG_LOG        = "ffmpeg_log.txt"
YOUTUBE_CATEGORY  = "25"   # 25 = News & Politics
YOUTUBE_TAGS      = ["harga emas", "emas antam", "investasi emas",
                     "logam mulia", "harga emas hari ini", "emas antam hari ini"]
KATA_KUNCI_GAMBAR = ["gold bars", "gold investment", "precious metals",
                     "gold coins", "financial gold", "gold bullion"]
# ============================================================


# ── Helpers ──────────────────────────────────────────────────

def escape_ffmpeg_path(path):
    """FIX KRITIS: escape path untuk filter FFmpeg (Windows & Linux)."""
    return path.replace('\\', '/').replace(':', '\\:')


def bersihkan_teks_untuk_robot(teks):
    teks_bersih = re.sub(r'\[.*?\]|\(.*?\)|\*.*?\*', '', teks)
    return teks_bersih.strip()


def siapkan_font_lokal():
    font_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
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


# ── Step 0: Download gambar otomatis dari Pexels ─────────────

def download_gambar_pexels(jumlah=12):
    print(f"[AUTO] Download {jumlah} gambar HD dari Pexels...")
    folder = "gambar_pexels"
    os.makedirs(folder, exist_ok=True)

    # Hapus gambar lama agar tidak menumpuk
    for f in glob.glob(f"{folder}/*.jpg"):
        os.remove(f)

    headers      = {"Authorization": PEXELS_API_KEY}
    kata_kunci   = random.choice(KATA_KUNCI_GAMBAR)
    url          = (f"https://api.pexels.com/v1/search"
                    f"?query={kata_kunci}&per_page={jumlah}&orientation=landscape")
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        foto_list = resp.json().get("photos", [])

        for i, foto in enumerate(foto_list):
            img_url  = foto["src"]["large2x"]
            img_data = requests.get(img_url, timeout=30).content
            with open(f"{folder}/foto_{i+1}.jpg", "wb") as f:
                f.write(img_data)

        print(f"  -> {len(foto_list)} gambar berhasil didownload (keyword: {kata_kunci})")
        return folder
    except Exception as e:
        print(f"  -> Gagal download Pexels: {e}")
        return None


# ── Step 1: Scrape harga emas ────────────────────────────────

def scrape_dan_kalkulasi_harga():
    print("[1/6] Mengambil data harga emas Antam...")
    url     = "https://www.logammulia.com/id/harga-emas-hari-ini"
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup     = BeautifulSoup(response.text, 'html.parser')
        data_kasar = soup.get_text(separator=" | ", strip=True)
        tanggal  = datetime.now().strftime("%d %B %Y")

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

        file_history  = "history_harga.json"
        harga_kemarin = harga_1_gram

        if os.path.exists(file_history):
            try:
                with open(file_history) as f:
                    data_lama = json.load(f)
                # Hanya bandingkan jika data bukan dari hari ini
                if data_lama.get("tanggal") != datetime.now().strftime("%Y-%m-%d"):
                    harga_kemarin = data_lama.get("harga_1_gram", harga_1_gram)
            except Exception:
                pass

        if harga_1_gram > harga_kemarin:
            status, selisih = "Naik",   harga_1_gram - harga_kemarin
        elif harga_1_gram < harga_kemarin:
            status, selisih = "Turun",  harga_kemarin - harga_1_gram
        else:
            status, selisih = "Stabil", 0

        with open(file_history, "w") as f:
            json.dump({
                "harga_1_gram": harga_1_gram,
                "tanggal": datetime.now().strftime("%Y-%m-%d")
            }, f)

        print(f"  -> Rp {harga_1_gram:,} | {status} Rp {selisih:,}".replace(",", "."))

        info_pergerakan = {
            "harga_sekarang": harga_1_gram,
            "status":  status,
            "selisih": selisih
        }
        teks_data = f"Tanggal: {tanggal}. Data web Antam: {data_kasar[:4000]}..."
        return info_pergerakan, teks_data

    except Exception as e:
        print(f"  -> Gagal scraping: {e}")
        return None, None


# ── Step 2a: Narasi fallback lokal (tanpa AI) ────────────────

def _buat_narasi_fallback_lokal(info, harga_skrg, status_harga, selisih_harga):
    """
    Generator narasi ~800 kata tanpa AI.
    Dipakai saat semua model Gemini gagal agar video tetap bisa dibuat.
    """
    tanggal = datetime.now().strftime("%d %B %Y")
    hari_en = datetime.now().strftime("%A")
    hari    = {
        "Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu",
        "Thursday": "Kamis", "Friday": "Jumat",
        "Saturday": "Sabtu", "Sunday": "Minggu"
    }.get(hari_en, hari_en)

    h = info['harga_sekarang']
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

    def rp(x):
        return f"Rp {x:,}".replace(",", ".")

    daftar_harga_teks = " ".join(
        f"Untuk ukuran {satuan}, harganya adalah {rp(nilai)}."
        for satuan, nilai in tabel.items()
    )

    kalimat_status = {
        "Naik":   f"mengalami kenaikan sebesar Rupiah {selisih_harga} dari kemarin",
        "Turun":  f"mengalami penurunan sebesar Rupiah {selisih_harga} dari kemarin",
        "Stabil": "terpantau stabil, tidak ada perubahan dari hari sebelumnya",
    }.get(status_harga, "terpantau stabil")

    judul  = f"Harga Emas Antam Hari Ini {status_harga} - Update {tanggal}"
    narasi = f"""
Halo sobat {NAMA_CHANNEL}, selamat datang kembali di channel kita. Hari ini adalah hari {hari}, {tanggal}, \
dan kami hadir membawakan update harga emas Antam Logam Mulia terbaru untuk Anda semua.

Langsung ke informasi utama. Pada hari ini, harga emas Antam resmi dari situs Logam Mulia untuk ukuran \
satu gram adalah {harga_skrg} Rupiah. Harga tersebut {kalimat_status}. \
Informasi ini kami ambil langsung dari sumber resmi sehingga dapat Anda jadikan acuan yang terpercaya.

Berikut daftar harga lengkap emas Antam hari ini untuk semua ukuran yang tersedia. \
{daftar_harga_teks} Itulah harga lengkap emas Antam hari ini. Pastikan Anda cek harga \
terbaru sebelum membeli karena harga emas berubah setiap harinya.

Sekarang mari kita bahas kondisi pasar emas global yang mempengaruhi harga dalam negeri. \
Pertama, kebijakan suku bunga Federal Reserve Amerika sangat berpengaruh. Ketika suku bunga \
tinggi, investor cenderung meninggalkan emas. Saat suku bunga diturunkan, emas kembali menjadi \
primadona investasi karena memberikan perlindungan nilai aset yang handal. \
Kedua, kondisi geopolitik global turut mendorong permintaan emas. Ketidakpastian di berbagai \
belahan dunia selalu membuat investor berlindung pada emas sebagai safe haven. \
Ketiga, nilai tukar Rupiah terhadap Dolar secara langsung mempengaruhi harga emas dalam negeri. \
Semakin melemah Rupiah, semakin mahal harga emas yang perlu kita keluarkan.

Bagi sobat yang ingin mulai investasi emas, berikut tips yang bisa langsung dipraktekkan. \
Pertama, mulai dari ukuran kecil. Tidak perlu langsung beli besar, cukup mulai dari setengah \
gram atau satu gram untuk mengenal cara kerja investasi emas. \
Kedua, beli secara rutin setiap bulan tanpa mempedulikan kondisi harga, \
strategi ini disebut dollar cost averaging dan terbukti efektif jangka panjang. \
Ketiga, simpan dengan aman di brankas atau gunakan layanan titipan resmi dari Antam. \
Keempat, jangan panik saat harga turun karena justru itu kesempatan untuk menambah koleksi \
dengan harga lebih murah. Kelima, catat setiap pembelian agar Anda bisa melacak \
keuntungan investasi dari waktu ke waktu dengan akurat.

Demikian informasi harga emas Antam hari ini beserta tips investasi dari kami. \
Semoga bermanfaat untuk Anda dalam mengambil keputusan investasi yang tepat. \
Jangan lupa tekan tombol Subscribe dan aktifkan lonceng notifikasi agar tidak ketinggalan \
update harga emas terbaru setiap hari hanya di channel {NAMA_CHANNEL}. \
Sampai jumpa di video berikutnya. Salam sukses dan salam investasi untuk sobat semua!
""".strip()

    return judul, narasi


# ── Step 2b: Narasi via Gemini AI ────────────────────────────

def buat_narasi_dan_judul(info, data_harga):
    print("[2/6] Meminta Gemini menulis script narasi...")

    status_harga  = info['status']
    selisih_harga = f"{info['selisih']:,}".replace(",", ".")
    harga_skrg    = f"{info['harga_sekarang']:,}".replace(",", ".")

    prompt = f"""
Kamu adalah pakar ekonomi makro dan scriptwriter YouTube profesional untuk channel "{NAMA_CHANNEL}".

DATA HARGA HARI INI:
- Harga 1 gram: Rp {harga_skrg}
- Status: {status_harga.upper()} sebesar Rp {selisih_harga} dibandingkan kemarin
- Data mentah website Antam: {data_harga}

TUGASMU:
1. Buat JUDUL YouTube clickbait (MAKSIMAL 100 karakter). WAJIB cantumkan "{status_harga.upper()} Rp {selisih_harga}".
2. Buat SCRIPT NARASI VIDEO (TARGET: 800 HINGGA 1000 KATA) dalam 4 bagian:
   - BAGIAN 1: Sapa penonton channel "{NAMA_CHANNEL}", umumkan harga 1 gram dengan tegas
   - BAGIAN 2: Bacakan daftar harga lengkap dari 0.5 gram sampai 1000 gram
   - BAGIAN 3 (PANJANG): Analisa ekonomi makro, isu global terkini (suku bunga, inflasi, geopolitik)
   - BAGIAN 4 (PANJANG): Edukasi cara menabung emas yang benar, akhiri dengan ajakan subscribe

ATURAN WAJIB:
- Tulis semua angka dengan huruf (contoh: "satu juta dua ratus ribu rupiah")
- Tulis dalam paragraf narasi murni — JANGAN gunakan bullet list, nomor, atau simbol apapun
- Bahasa Indonesia yang natural dan mengalir seperti presenter berita

FORMAT BALASAN:
[JUDUL]
(tulis judul di sini)

[SCRIPT]
(tulis narasi di sini)
"""

    # Model chain: dari kuota terbanyak ke terkecil (free tier 2026)
    MODEL_CHAIN = [
        "gemini-2.0-flash-lite",   # 30 RPM, 3.000 RPD  ← utama
        "gemini-2.0-flash",        # 15 RPM, 1.500 RPD  ← backup
        "gemini-2.5-flash-lite",   # 15 RPM, 1.000 RPD  ← last resort
    ]

    for model_name in MODEL_CHAIN:
        MAX_RETRY = 3
        for attempt in range(MAX_RETRY):
            try:
                url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                       f"{model_name}:generateContent?key={GEMINI_API_KEY}")
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "maxOutputTokens": 8192,
                        "temperature": 0.8
                    }
                }
                print(f"  -> {model_name} (attempt {attempt+1}/{MAX_RETRY})...")
                resp = requests.post(url, json=payload, timeout=90)

                # Tangani 429 dengan exponential backoff
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get('Retry-After', 0))
                    tunggu = retry_after if retry_after > 0 else (2 ** attempt) * 10
                    print(f"  -> Rate limit 429. Tunggu {tunggu}s...")
                    time.sleep(tunggu)
                    continue

                resp.raise_for_status()
                hasil = resp.json()['candidates'][0]['content']['parts'][0]['text']

                judul  = f"Harga Emas Hari Ini {status_harga} Rp {selisih_harga}"
                script = hasil
                if "[JUDUL]" in hasil and "[SCRIPT]" in hasil:
                    bagian = hasil.split("[SCRIPT]")
                    judul  = bagian[0].replace("[JUDUL]", "").strip()
                    script = bagian[1].strip()

                print(f"  -> Berhasil dengan model: {model_name}")
                return judul, script

            except Exception as e:
                if "429" not in str(e):
                    print(f"  -> Error pada {model_name}: {e}")
                    break  # Error bukan rate-limit → langsung coba model berikutnya
                tunggu = (2 ** attempt) * 10
                print(f"  -> 429 exception. Tunggu {tunggu}s...")
                time.sleep(tunggu)

        print(f"  -> {model_name} gagal semua attempt. Coba model berikutnya...")

    # ── FALLBACK: Semua Gemini gagal → pakai template lokal ──
    print("  -> [FALLBACK] Menggunakan narasi template lokal (tanpa AI)...")
    return _buat_narasi_fallback_lokal(info, harga_skrg, status_harga, selisih_harga)


# ── Step 3: Generate suara ────────────────────────────────────

def buat_suara(teks, output_audio):
    print("[3/6] Men-generate Suara AI (edge-tts)...")
    teks_bersih = bersihkan_teks_untuk_robot(teks)
    subprocess.run([
        sys.executable, '-m', 'edge_tts',
        '--voice', 'id-ID-ArdiNeural',
        '--rate', '+5%',
        '--text', teks_bersih,
        '--write-media', output_audio
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    if not os.path.exists(output_audio) or os.path.getsize(output_audio) < 1000:
        raise FileNotFoundError("File audio gagal dibuat oleh edge-tts!")

    # Cek durasi audio — minimal harus > 30 detik
    hasil_dur = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', output_audio],
        capture_output=True, text=True
    )
    try:
        durasi = float(hasil_dur.stdout.strip())
        if durasi < 30:
            raise ValueError(
                f"Audio terlalu pendek ({durasi:.1f}s). "
                "Kemungkinan narasi dari Gemini/fallback terlalu singkat!"
            )
        print(f"  -> Durasi audio: {durasi:.0f} detik ({durasi/60:.1f} menit)")
        return durasi
    except ValueError as e:
        raise ValueError(str(e))


# ── Step 4: Proses gambar & render klip ──────────────────────

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

    # Watermark dengan font ter-escape (fix utama video blank)
    if font_sistem:
        font_esc = escape_ffmpeg_path(font_sistem)
        x, y = random.choice([
            ("30", "30"), ("w-tw-30", "30"),
            ("30", "h-th-30"), ("w-tw-30", "h-th-30")
        ])
        filter_vf += (
            f",drawtext=fontfile='{font_esc}'"
            f":text='{NAMA_CHANNEL}'"
            f":fontcolor=white@0.7:fontsize=30:x={x}:y={y}"
        )

    cmd = [
        'ffmpeg', '-y',
        '-loop', '1', '-framerate', '30', '-i', img,
        '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
        '-vf', filter_vf,
        '-map', '0:v', '-map', '1:a',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac',
        '-t', '10',
        output_klip
    ]

    with open(FFMPEG_LOG, 'a', encoding='utf-8') as log:
        log.write(f"\n=== Klip {i}: {img} ===\n")
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=log)

    # Validasi klip benar-benar terbuat
    if (result.returncode != 0
            or not os.path.exists(output_klip)
            or os.path.getsize(output_klip) < 1000):
        print(f"  -> [GAGAL] Klip {i} ({os.path.basename(img)}). Cek {FFMPEG_LOG}")
        return None
    return i, output_klip


def proses_gambar(durasi_total_detik):
    print(f"[4/6] Proses gambar paralel ({min(4, os.cpu_count() or 2)} thread)...")
    os.makedirs("temp_clips", exist_ok=True)

    # Kumpulkan semua gambar: Pexels dulu, lalu folder lokal sebagai fallback
    gambar_list = []
    for folder in ["gambar_pexels", "."]:
        for ext in ('*.jpg', '*.jpeg', '*.png'):
            gambar_list.extend(glob.glob(os.path.join(folder, ext)))
    gambar_list = list(set(gambar_list))  # hapus duplikat

    if not gambar_list:
        print("ERROR: Tidak ada gambar ditemukan! Pastikan Pexels API key valid "
              "atau taruh file .jpg/.png secara manual di folder ini.")
        return None

    random.shuffle(gambar_list)
    jumlah_klip = int(durasi_total_detik / 10) + 2

    # Duplikasi list jika gambar tidak cukup
    while len(gambar_list) < jumlah_klip:
        gambar_list.extend(gambar_list)
    gambar_terpilih = gambar_list[:jumlah_klip]

    font_sistem = siapkan_font_lokal()
    tasks = [
        (i, img, font_sistem, os.path.abspath(f"temp_clips/klip_{i}.mp4"))
        for i, img in enumerate(gambar_terpilih)
    ]

    klip_berhasil = {}
    max_workers   = min(4, os.cpu_count() or 2)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(render_satu_klip, t): t[0] for t in tasks}
        for future in as_completed(futures):
            hasil = future.result()
            if hasil:
                idx, path = hasil
                klip_berhasil[idx] = path
            print(f"  -> {len(klip_berhasil)}/{jumlah_klip} klip selesai", end='\r')

    print(f"\n  -> {len(klip_berhasil)}/{jumlah_klip} klip berhasil dirender.")

    if not klip_berhasil:
        print(f"FATAL: Semua klip gagal! Buka '{FFMPEG_LOG}' untuk detail.")
        return None

    # Tulis concat file dengan PATH ABSOLUT & forward slash
    list_txt = os.path.abspath('concat_videos.txt')
    with open(list_txt, 'w', encoding='utf-8') as f:
        for i in sorted(klip_berhasil.keys()):
            path_aman = klip_berhasil[i].replace('\\', '/')
            f.write(f"file '{path_aman}'\n")

    return list_txt


# ── Step 5: Render video final ────────────────────────────────

def render_video_final(file_list, audio, output, durasi):
    print(f"[5/6] Merender video final (Mode Kilat - copy stream)...")
    cmd = [
        'ffmpeg', '-y',
        '-f', 'concat', '-safe', '0', '-i', file_list,
        '-i', audio,
        '-map', '0:v',
        '-map', '1:a',
        '-c:v', 'copy',          # Copy stream → sangat cepat
        '-c:a', 'aac', '-b:a', '192k',
        '-t', str(durasi),
        output
    ]
    with open(FFMPEG_LOG, 'a', encoding='utf-8') as log:
        log.write("\n=== RENDER FINAL ===\n")
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=log)

    if result.returncode != 0:
        print(f"  -> ERROR saat render final! Buka '{FFMPEG_LOG}' untuk detail.")
        return False
    return True


# ── Step 6: Upload ke YouTube ─────────────────────────────────

def upload_ke_youtube(video_path, judul, deskripsi, tags):
    print("[6/6] Upload ke YouTube...")
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        creds_file = os.environ.get("YOUTUBE_TOKEN_FILE", "youtube_token.json")

        # Cek apakah token ada sebagai environment variable (untuk GitHub Actions)
        token_env = os.environ.get("YOUTUBE_TOKEN_JSON")
        if token_env:
            with open(creds_file, "w") as f:
                f.write(token_env)
            print("  -> Token dari environment variable OK.")

        if not os.path.exists(creds_file):
            print(f"  -> ERROR: File '{creds_file}' tidak ditemukan!")
            print("     Jalankan 'python setup_youtube_auth.py' di komputer lokal Anda.")
            return None

        with open(creds_file) as f:
            token_data = json.load(f)

        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
        )

        youtube = build("youtube", "v3", credentials=creds)
        body    = {
            "snippet": {
                "title":           judul[:100],
                "description":     deskripsi,
                "tags":            tags,
                "categoryId":      YOUTUBE_CATEGORY,
                "defaultLanguage": "id",
            },
            "status": {
                "privacyStatus":            "public",
                "selfDeclaredMadeForKids":  False,
            }
        }
        media   = MediaFileUpload(
            video_path, mimetype="video/mp4",
            resumable=True, chunksize=5 * 1024 * 1024
        )
        request = youtube.videos().insert(
            part="snippet,status", body=body, media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"  -> Upload: {int(status.progress() * 100)}%", end='\r')

        video_id = response.get("id")
        print(f"\n  -> ✅ Upload sukses! https://youtu.be/{video_id}")

        # Simpan riwayat upload
        with open("upload_history.json", "a", encoding="utf-8") as f:
            json.dump({
                "tanggal":  datetime.now().isoformat(),
                "video_id": video_id,
                "judul":    judul
            }, f, ensure_ascii=False)
            f.write("\n")

        return video_id

    except Exception as e:
        print(f"  -> Gagal upload YouTube: {e}")
        return None


# ── Bersihkan file temp ───────────────────────────────────────

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
        print(f"  -> Warning bersihkan: {e}")


# ── MAIN ──────────────────────────────────────────────────────

async def main():
    # Reset log
    with open(FFMPEG_LOG, 'w', encoding='utf-8') as f:
        f.write(f"Log FFmpeg - {datetime.now()}\n{'='*60}\n")

    audio_temp  = "suara.mp3"
    tanggal_str = datetime.now().strftime('%Y%m%d')
    video_hasil = f"Video_Emas_{tanggal_str}.mp4"

    print(f"\n{'='*60}")
    print(f"  AUTO VIDEO EMAS - {NAMA_CHANNEL}")
    print(f"  {datetime.now().strftime('%d %B %Y, %H:%M WIB')}")
    print(f"{'='*60}\n")

    # 0. Download gambar dari Pexels
    if PEXELS_API_KEY and PEXELS_API_KEY != "ISI_API_KEY_PEXELS_ANDA":
        download_gambar_pexels(jumlah=12)
    else:
        print("[AUTO] Pexels API key belum diisi. Menggunakan gambar lokal.")

    # 1. Scrape harga emas
    info, data_harga = scrape_dan_kalkulasi_harga()
    if not info:
        print("Scraping gagal. Menghentikan proses.")
        return

    # 2. Buat narasi (Gemini AI + fallback lokal)
    judul, narasi = buat_narasi_dan_judul(info, data_harga)
    print(f"\n{'='*60}")
    print(f"  🌟 JUDUL YOUTUBE:")
    print(f"  {judul}")
    print(f"{'='*60}\n")

    # 3. Generate suara
    try:
        buat_suara(narasi, audio_temp)
        durasi = float(subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', audio_temp],
            capture_output=True, text=True
        ).stdout.strip())
        print(f"  -> ✅ Audio OK: {durasi:.0f} detik ({durasi/60:.1f} menit)")
    except Exception as e:
        print(f"  -> ERROR audio: {e}")
        return

    # 4. Proses gambar paralel
    file_list = proses_gambar(durasi)
    if not file_list:
        return

    # 5. Render video
    sukses = render_video_final(file_list, audio_temp, video_hasil, durasi)
    bersihkan_temp(file_list, audio_temp)

    if sukses and os.path.exists(video_hasil):
        ukuran_mb = os.path.getsize(video_hasil) // 1024 // 1024
        print(f"\n✅ VIDEO SELESAI: {video_hasil} ({ukuran_mb} MB)")

        if ukuran_mb < 5:
            print("⚠️  PERINGATAN: Ukuran video terlalu kecil. Kemungkinan ada masalah.")
            print(f"   Buka '{FFMPEG_LOG}' untuk debug.")
            return

        # 6. Upload ke YouTube
        deskripsi = (
            f"Update harga emas Antam hari ini {datetime.now().strftime('%d %B %Y')}.\n\n"
            f"✅ Harga 1 gram  : Rp {info['harga_sekarang']:,}\n"
            f"📊 Status        : {info['status']}\n\n"
            f"Informasi diambil langsung dari situs resmi Logam Mulia.\n\n"
            f"#HargaEmas #EmasAntam #InvestasiEmas #LogamMulia #EmasHariIni\n\n"
            f"Jangan lupa SUBSCRIBE dan aktifkan 🔔 notifikasi!"
        ).replace(",", ".")

        upload_ke_youtube(video_hasil, judul, deskripsi, YOUTUBE_TAGS)

    else:
        print(f"\n❌ GAGAL membuat video. Buka '{FFMPEG_LOG}' untuk detail.")


if __name__ == "__main__":
    asyncio.run(main())
    print("\n" + "="*60)
    # Tidak perlu input() — script selesai otomatis di GitHub Actions


