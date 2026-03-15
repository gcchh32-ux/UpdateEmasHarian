# video_maker.py
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
    cek = [
        "requests", "beautifulsoup4", "edge-tts",
        "google-api-python-client", "google-auth-oauthlib",
    ]
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

# ── Import dari modul terpisah ────────────────────────────────
from narasi import buat_narasi_dan_judul
from store  import kelola_bank_gambar, kelola_bank_video, kelola_video_lama

# ============================================================
# !! PENGATURAN UTAMA - ISI BAGIAN INI !!
# ============================================================
from config import (
    GEMINI_API_KEY,
    PEXELS_API_KEY,
    NAMA_CHANNEL,
    YOUTUBE_CATEGORY,
    YOUTUBE_TAGS,
)

FFMPEG_LOG = "ffmpeg_log.txt"
# ============================================================


# ── Helpers ──────────────────────────────────────────────────

def escape_ffmpeg_path(path):
    return path.replace("\\", "/").replace(":", "\\:")


def bersihkan_teks_untuk_robot(teks):
    teks_bersih = re.sub(r"\[.*?\]|\(.*?\)|\*.*?\*", "", teks)
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


# ── Step 1: Scrape harga emas ────────────────────────────────

def scrape_dan_kalkulasi_harga():
    print("[1/6] Scraping harga emas...")
    url     = "https://www.logammulia.com/id/harga-emas-hari-ini"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup     = BeautifulSoup(response.text, "html.parser")
        tanggal  = datetime.now().strftime("%d %B %Y")

        harga_1_gram = 0
        for row in soup.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                teks_kol = cells[0].text.strip().lower()
                if teks_kol in ("1 gr", "1 gram"):
                    angka_str = re.sub(r"[^\d]", "", cells[1].text)
                    if angka_str:
                        harga_1_gram = int(angka_str)
                        break

        if harga_1_gram == 0:
            print("  -> ERROR: Gagal parse harga dari website Antam.")
            return None

        print(f"  -> [logammulia] 1 gr = Rp {harga_1_gram:,}".replace(",", "."))

        file_history  = "history_harga.json"
        harga_kemarin = harga_1_gram

        if os.path.exists(file_history):
            try:
                with open(file_history) as f:
                    data_lama = json.load(f)
                if data_lama.get("tanggal") != datetime.now().strftime("%Y-%m-%d"):
                    harga_kemarin = data_lama.get("harga_1_gram", harga_1_gram)
            except Exception:
                pass

        if harga_1_gram > harga_kemarin:
            status, selisih = "naik",   harga_1_gram - harga_kemarin
        elif harga_1_gram < harga_kemarin:
            status, selisih = "turun",  harga_kemarin - harga_1_gram
        else:
            status, selisih = "stabil", 0

        persen = (selisih / harga_kemarin * 100) if harga_kemarin else 0.0

        with open(file_history, "w") as f:
            json.dump(
                {"harga_1_gram": harga_1_gram,
                 "tanggal": datetime.now().strftime("%Y-%m-%d")},
                f,
            )

        waktu = datetime.now().strftime("%H:%M WIB")
        print(f"  -> ✅ Harga ditemukan: Rp {harga_1_gram:,}".replace(",", "."))
        print(f"  -> Harga   : Rp {harga_1_gram:,}".replace(",", "."))
        print(f"  -> Kemarin : Rp {harga_kemarin:,}".replace(",", "."))
        print(f"  -> Status  : {status.title()} ({persen:+.2f}%)")
        print(f"  -> Selisih : Rp {selisih:,}".replace(",", "."))

        return {
            "harga_sekarang": harga_1_gram,
            "harga_kemarin":  harga_kemarin,
            "status":         status,
            "selisih":        selisih,
            "persen":         persen,
            "tanggal":        tanggal,
            "waktu":          waktu,
            "historis":       {},
        }

    except Exception as e:
        print(f"  -> Gagal scraping: {e}")
        return None


# ── Step 3: Generate suara ────────────────────────────────────

def buat_suara(teks, output_audio):
    print("[3/6] Generate suara...")
    teks_bersih = bersihkan_teks_untuk_robot(teks)
    print(f"  -> Panjang teks: {len(teks_bersih)} karakter")

    for attempt in range(1, 5):
        print(f"  -> edge-tts attempt {attempt}/4...")
        try:
            subprocess.run(
                [
                    sys.executable, "-m", "edge_tts",
                    "--voice", "id-ID-ArdiNeural",
                    "--rate",  "+5%",
                    "--text",  teks_bersih,
                    "--write-media", output_audio,
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if os.path.exists(output_audio) and os.path.getsize(output_audio) > 1000:
                break
        except Exception as e:
            print(f"  -> edge-tts error: {e}")
            time.sleep(3)

    if not os.path.exists(output_audio) or os.path.getsize(output_audio) < 1000:
        raise FileNotFoundError("File audio gagal dibuat oleh edge-tts!")

    hasil_dur = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            output_audio,
        ],
        capture_output=True,
        text=True,
    )
    try:
        durasi = float(hasil_dur.stdout.strip())
        if durasi < 30:
            raise ValueError(
                f"Audio terlalu pendek ({durasi:.1f}s). "
                "Kemungkinan narasi terlalu singkat!"
            )
        size_kb = os.path.getsize(output_audio) // 1024
        print(
            f"  -> ✅ Audio OK: {durasi:.0f}s "
            f"({durasi/60:.1f} menit) — {size_kb} KB"
        )
        return durasi
    except ValueError as e:
        raise ValueError(str(e))


# ── Step 4: Render klip & proses gambar ──────────────────────

def render_satu_klip(args):
    i, img, font_sistem, output_klip = args

    base = (
        "scale=1920:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30"
    )
    pilihan_filter = [
        f"{base},fade=t=in:st=0:d=1,fade=t=out:st=9:d=1",
        (
            f"{base},boxblur=luma_radius='max(0,15*(1-t/1.5))':luma_power=1,"
            "fade=t=in:st=0:d=1,fade=t=out:st=9:d=1"
        ),
        f"{base},hue=s='min(1,t/1.5)',fade=t=in:st=0:d=1,fade=t=out:st=9:d=1",
    ]
    filter_vf = random.choice(pilihan_filter)

    if font_sistem:
        font_esc = escape_ffmpeg_path(font_sistem)
        x, y = random.choice([
            ("30", "30"), ("w-tw-30", "30"),
            ("30", "h-th-30"), ("w-tw-30", "h-th-30"),
        ])
        filter_vf += (
            f",drawtext=fontfile='{font_esc}'"
            f":text='{NAMA_CHANNEL}'"
            f":fontcolor=white@0.7:fontsize=30:x={x}:y={y}"
        )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", "30", "-i", img,
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-vf", filter_vf,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-t", "10",
        output_klip,
    ]

    with open(FFMPEG_LOG, "a", encoding="utf-8") as log:
        log.write(f"\n=== Klip {i}: {img} ===\n")
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=log)

    if (
        result.returncode != 0
        or not os.path.exists(output_klip)
        or os.path.getsize(output_klip) < 1000
    ):
        print(f"  -> [GAGAL] Klip {i} ({os.path.basename(img)}). Cek {FFMPEG_LOG}")
        return None
    return i, output_klip


def proses_gambar(durasi_total_detik):
    max_workers = min(4, os.cpu_count() or 2)
    print(f"[4/6] Menyiapkan klip visual (target:{durasi_total_detik:.0f}s)...")
    os.makedirs("temp_clips", exist_ok=True)

    # Kumpulkan dari semua folder yang mungkin
    gambar_list = []
    folder_cari = ["gambar_bank", "gambar_static", "gambar_pexels", "."]
    for folder in folder_cari:
        for ext in ("*.jpg", "*.jpeg", "*.png"):
            gambar_list.extend(glob.glob(os.path.join(folder, ext)))

    # Hapus duplikat path
    gambar_list = list(set(os.path.abspath(g) for g in gambar_list))

    if not gambar_list:
        print(
            "ERROR: Tidak ada gambar ditemukan! "
            "Pastikan folder gambar_static/ terisi atau Pexels API key valid."
        )
        return None

    # FIX: shuffle sebelum apapun agar variasi tiap run
    random.shuffle(gambar_list)

    jumlah_klip = int(durasi_total_detik / 10) + 2
    print(f"  -> Bank: {len(gambar_list)} gambar, 0 video")
    print(f"  -> Target klip: {jumlah_klip}")

    # FIX: spread merata pakai modulo — semua gambar dipakai dulu
    # sebelum ada yang diulang, TIDAK seperti extend() yang dobel dari awal
    gambar_terpilih = [
        gambar_list[i % len(gambar_list)]
        for i in range(jumlah_klip)
    ]

    unik = len(set(gambar_terpilih))
    print(f"  -> Gambar unik dipakai: {unik} dari {len(gambar_list)} tersedia")

    font_sistem = siapkan_font_lokal()
    tasks = [
        (i, img, font_sistem, os.path.abspath(f"temp_clips/klip_{i}.mp4"))
        for i, img in enumerate(gambar_terpilih)
    ]

    klip_berhasil = {}
    print(f"  -> Render {jumlah_klip} klip ({max_workers} thread)...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(render_satu_klip, t): t[0] for t in tasks}
        for future in as_completed(futures):
            hasil = future.result()
            if hasil:
                idx, path = hasil
                klip_berhasil[idx] = path
                print(
                    f"  -> {len(klip_berhasil)}/{jumlah_klip} klip selesai",
                    end="\r",
                )

    print(f"\n  -> {len(klip_berhasil)}/{jumlah_klip} klip berhasil dirender.")

    if not klip_berhasil:
        print(f"FATAL: Semua klip gagal! Buka '{FFMPEG_LOG}' untuk detail.")
        return None

    # Tulis concat file dengan PATH ABSOLUT & forward slash
    list_txt = os.path.abspath("concat_videos.txt")
    with open(list_txt, "w", encoding="utf-8") as f:
        for i in sorted(klip_berhasil.keys()):
            path_aman = klip_berhasil[i].replace("\\", "/")
            f.write(f"file '{path_aman}'\n")

    return list_txt


# ── Step 5: Render video final ────────────────────────────────

def render_video_final(file_list, audio, output, durasi):
    print("[5/6] Merender video final...")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", file_list,
        "-i", audio,
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-t", str(durasi),
        output,
    ]
    with open(FFMPEG_LOG, "a", encoding="utf-8") as log:
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

        token_env = os.environ.get("YOUTUBE_TOKEN_JSON")
        if token_env:
            with open(creds_file, "w") as f:
                f.write(token_env)
            print("  -> Token dari environment variable OK.")

        if not os.path.exists(creds_file):
            print(f"  -> ERROR: File '{creds_file}' tidak ditemukan!")
            print("     Jalankan 'python setup_youtube_auth.py' di komputer lokal.")
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
        body = {
            "snippet": {
                "title":           judul[:100],
                "description":     deskripsi,
                "tags":            tags,
                "categoryId":      YOUTUBE_CATEGORY,
                "defaultLanguage": "id",
            },
            "status": {
                "privacyStatus":          "public",
                "selfDeclaredMadeForKids": False,
            },
        }
        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=5 * 1024 * 1024,
        )
        request = youtube.videos().insert(
            part="snippet,status", body=body, media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"  -> Upload: {int(status.progress() * 100)}%", end="\r")

        video_id = response.get("id")
        print(f"\n  -> ✅ Upload sukses! https://youtu.be/{video_id}")

        with open("upload_history.json", "a", encoding="utf-8") as f:
            json.dump(
                {
                    "tanggal":  datetime.now().isoformat(),
                    "video_id": video_id,
                    "judul":    judul,
                },
                f,
                ensure_ascii=False,
            )
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
    with open(FFMPEG_LOG, "w", encoding="utf-8") as f:
        f.write(f"Log FFmpeg - {datetime.now()}\n{'='*60}\n")

    audio_temp   = "suara.mp3"
    tanggal_str  = datetime.now().strftime("%Y%m%d")
    video_hasil  = f"Video_Emas_{tanggal_str}.mp4"

    print(f"\n{'='*60}")
    print(f" AUTO VIDEO EMAS - Info Logam Mulia")
    print(f" {datetime.now().strftime('%d %B %Y, %H:%M WIB')}")
    print(f"{'='*60}\n")

    # 0. Kelola bank gambar (static → pexels → pixabay → duplikasi)
    kelola_bank_gambar()
    kelola_video_lama()

    # 1. Scrape harga emas
    info = scrape_dan_kalkulasi_harga()
    if not info:
        print("Scraping gagal. Menghentikan proses.")
        return

    # 2. Buat narasi (Gemini AI + fallback lokal)
    print("Membuat narasi...")
    judul, narasi = buat_narasi_dan_judul(info)
    print(f"\n{'='*60}")
    print(f" JUDUL: {judul}")
    print(f"{'='*60}\n")

    # 3. Generate suara
    try:
        durasi = buat_suara(narasi, audio_temp)
    except Exception as e:
        print(f"  -> ERROR audio: {e}")
        return

    # 4. Proses gambar & render klip
    file_list = proses_gambar(durasi)
    if not file_list:
        return

    # 5. Render video final
    sukses = render_video_final(file_list, audio_temp, video_hasil, durasi)
    bersihkan_temp(file_list, audio_temp)

    if sukses and os.path.exists(video_hasil):
        ukuran_mb = os.path.getsize(video_hasil) // 1024 // 1024
        print(f"\n✅ VIDEO SELESAI: {video_hasil} ({ukuran_mb} MB)")

        if ukuran_mb < 5:
            print(f"⚠️ PERINGATAN: Ukuran video terlalu kecil. Buka '{FFMPEG_LOG}' untuk debug.")
            return

        # 6. Upload ke YouTube
        deskripsi = (
            f"Update harga emas Antam hari ini "
            f"{datetime.now().strftime('%d %B %Y')}.\n\n"
            f"Harga 1 gram : Rp {info['harga_sekarang']:,}\n"
            f"Status       : {info['status'].title()}\n\n"
            f"Informasi diambil langsung dari situs resmi Logam Mulia.\n\n"
            f"#HargaEmas #EmasAntam #InvestasiEmas #LogamMulia #EmasHariIni\n\n"
            f"Jangan lupa SUBSCRIBE dan aktifkan notifikasi!"
        ).replace(",", ".")

        upload_ke_youtube(video_hasil, judul, deskripsi, YOUTUBE_TAGS)
    else:
        print(f"\n❌ GAGAL membuat video. Buka '{FFMPEG_LOG}' untuk detail.")


if __name__ == "__main__":
    asyncio.run(main())
    print("\n" + "=" * 60)
