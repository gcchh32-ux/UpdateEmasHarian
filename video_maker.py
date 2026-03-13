# =============================================================
# AUTO VIDEO EMAS - MAIN ORCHESTRATOR
# =============================================================
import os
import sys
import subprocess
import glob
import json
import asyncio
from datetime import datetime

# ── Auto-install dependencies ─────────────────────────────────
def pastikan_library_terinstall():
    cek = [
        'requests', 'beautifulsoup4', 'edge-tts',
        'google-api-python-client', 'google-auth-oauthlib',
        'Pillow',
    ]
    try:
        import requests
        from bs4 import BeautifulSoup
        import edge_tts
        from googleapiclient.discovery import build
        from PIL import Image
    except ImportError:
        print("Menginstal library yang dibutuhkan...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", *cek]
        )

pastikan_library_terinstall()

# ── Import dari file yang sudah ada di repo ───────────────────
from config   import (NAMA_CHANNEL, YOUTUBE_TAGS,
                      YOUTUBE_CATEGORY, FFMPEG_LOG)
from scrape   import ambil_harga_emas
from narasi   import buat_narasi_dan_judul
from store    import kelola_bank_gambar
from render   import buat_suara, proses_semua_klip, render_video_final
from thumb    import buat_thumbnail
from uploader import upload_ke_youtube
from utils    import log, rp

# ── MAIN ──────────────────────────────────────────────────────

async def main():
    # Reset log
    with open(FFMPEG_LOG, 'w', encoding='utf-8') as f:
        f.write(
            f"Log FFmpeg - {datetime.now()}\n"
            f"{'='*60}\n"
        )

    tanggal_str = datetime.now().strftime('%Y%m%d')
    audio_temp  = "suara.mp3"
    video_hasil = f"Video_Emas_{tanggal_str}.mp4"
    thumb_hasil = f"Thumbnail_{tanggal_str}.jpg"

    log(f"\n{'='*60}")
    log(f" AUTO VIDEO EMAS - {NAMA_CHANNEL}")
    log(f" {datetime.now().strftime('%d %B %Y, %H:%M WIB')}")
    log(f"{'='*60}\n")

    # ── 0. Siapkan bank gambar ────────────────────────────────
    kelola_bank_gambar()

    # ── 1. Scrape harga emas ──────────────────────────────────
    info = ambil_harga_emas()
    if not info:
        log("❌ Scraping gagal. Proses dihentikan.")
        return

    data_harga = (
        f"Tanggal: {info['tanggal']}. "
        f"Harga 1 gram: {rp(info['harga_sekarang'])}. "
        f"Status: {info['status']} "
        f"({info['persen']:+.2f}%). "
        f"Selisih: {rp(info['selisih'])}."
    )

    # ── 2. Buat narasi & judul ────────────────────────────────
    judul, narasi = buat_narasi_dan_judul(info, data_harga)
    log(f"\n{'='*60}")
    log(f" JUDUL: {judul}")
    log(f"{'='*60}\n")

    # ── 3. Generate suara ─────────────────────────────────────
    try:
        durasi = buat_suara(narasi, audio_temp)
    except Exception as e:
        log(f"❌ Gagal generate suara: {e}")
        return

    # ── 4. Siapkan klip visual ────────────────────────────────
    file_list = proses_semua_klip(durasi)
    if not file_list:
        log("❌ Proses klip visual gagal.")
        return

    # ── 5. Render video final ─────────────────────────────────
    sukses = render_video_final(
        file_list, audio_temp, video_hasil, durasi
    )
    if not sukses:
        log("❌ Render video gagal.")
        return

    # ── 6. Buat thumbnail ─────────────────────────────────────
    try:
        buat_thumbnail(info, thumb_hasil)
    except Exception as e:
        log(f"⚠️ Thumbnail gagal (lanjut tanpa): {e}")
        thumb_hasil = None

    # ── 7. Cek ukuran video ───────────────────────────────────
    if not os.path.exists(video_hasil):
        log("❌ File video tidak ditemukan!")
        return

    ukuran_mb = os.path.getsize(video_hasil) // 1024 // 1024
    log(f"✅ VIDEO SELESAI: {video_hasil} ({ukuran_mb} MB)")

    if ukuran_mb < 5:
        log(f"⚠️ Video terlalu kecil ({ukuran_mb} MB), "
            f"cek {FFMPEG_LOG}")
        return

    # ── 8. Upload ke YouTube ──────────────────────────────────
    deskripsi = (
        f"Update harga emas Antam hari ini "
        f"{datetime.now().strftime('%d %B %Y')}.\n\n"
        f"✅ Harga 1 gram : {rp(info['harga_sekarang'])}\n"
        f"📊 Status       : {info['status']}\n\n"
        f"Informasi diambil langsung dari situs resmi "
        f"Logam Mulia.\n\n"
        f"#HargaEmas #EmasAntam #InvestasiEmas "
        f"#LogamMulia #EmasHariIni\n\n"
        f"Jangan lupa SUBSCRIBE dan aktifkan notifikasi!"
    )

    upload_ke_youtube(
        video_path=video_hasil,
        judul=judul,
        deskripsi=deskripsi,
        tags=YOUTUBE_TAGS,
        thumbnail=thumb_hasil,
    )

    # ── Bersihkan file temp ───────────────────────────────────
    for tmp in [audio_temp, "font_temp.ttf",
                "concat_videos.txt"]:
        if tmp and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass
    for klip in glob.glob("temp_clips/*.mp4"):
        try:
            os.remove(klip)
        except Exception:
            pass
    if os.path.exists("temp_clips"):
        try:
            os.rmdir("temp_clips")
        except Exception:
            pass

    log("\n" + "="*60)
    log(" PROSES SELESAI!")
    log("="*60)


if __name__ == "__main__":
    asyncio.run(main())
