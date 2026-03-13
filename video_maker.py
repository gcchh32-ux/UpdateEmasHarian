# video_maker.py — MAIN
import os, glob
from datetime import datetime
from config import (
    NAMA_CHANNEL, CHANNEL_ID, NARASI_GAYA,
    CFG, FFMPEG_LOG, YOUTUBE_TAGS,
)
from utils     import log
from store     import (kelola_bank_gambar, kelola_bank_video,
                       kelola_video_lama, debug_storage)
from scrape    import scrape_dan_kalkulasi_harga
from narasi    import buat_narasi_dan_judul
from render    import (buat_suara, proses_semua_klip,
                       render_video_final)
from thumb     import buat_thumbnail
from uploader  import upload_ke_youtube

def main():
    log("=" * 60)
    log(f" AUTO VIDEO EMAS — {NAMA_CHANNEL}")
    log(f" Channel ID : {CHANNEL_ID}")
    log(f" Gaya       : {NARASI_GAYA}")
    log(f" Waktu      : "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 60)

    # Debug awal
    debug_storage()

    # ── Step 1: Siapkan bank gambar & video ──────────────
    log("[1/6] Kelola bank media...")
    kelola_bank_gambar()
    kelola_bank_video()

    # ── Step 2: Scraping harga ───────────────────────────
    info = scrape_dan_kalkulasi_harga()

    # ── Step 3: Buat narasi & judul ──────────────────────
    judul, narasi = buat_narasi_dan_judul(info)

    # ── Nama file output ─────────────────────────────────
    ts         = datetime.now().strftime("%Y%m%d_%H%M")
    audio_file = f"audio_{ts}.mp3"
    video_file = f"Video_Emas_{ts}.mp4"
    thumb_file = f"thumbnail_{ts}.jpg"

    # ── Step 4: Generate suara ───────────────────────────
    try:
        durasi_audio = buat_suara(narasi, audio_file)
    except Exception as e:
        log(f"  -> ERROR buat suara: {e}")
        return

    # ── Step 5: Render klip visual ───────────────────────
    file_list = proses_semua_klip(durasi_audio)
    if not file_list:
        log("  -> FATAL: Tidak ada klip visual!")
        _cleanup(audio_file)
        return

    # ── Step 6: Render video final ───────────────────────
    ok = render_video_final(
        file_list, audio_file,
        video_file, durasi_audio,
    )
    if not ok:
        log("  -> FATAL: Render video final gagal!")
        _cleanup(audio_file, file_list)
        return

    # ── Step 7: Buat thumbnail ───────────────────────────
    try:
        buat_thumbnail(info, judul, thumb_file)
    except Exception as e:
        log(f"  -> WARNING thumbnail error: {e}")
        thumb_file = None

    # ── Step 8: Upload YouTube ───────────────────────────
    video_id = upload_ke_youtube(
        video_path=video_file,
        judul=judul,
        narasi=narasi,
        tags=YOUTUBE_TAGS,
        info=info,
        thumbnail_path=thumb_file,
    )

    # ── Step 9: Cleanup ──────────────────────────────────
    _cleanup(audio_file, file_list)
    kelola_video_lama()

    # ── Ringkasan ────────────────────────────────────────
    log("=" * 60)
    log(f"  Video    : {video_file} "
        f"({os.path.getsize(video_file)//1024//1024} MB)"
        if os.path.exists(video_file) else
        f"  Video    : TIDAK ADA")
    log(f"  Thumbnail: "
        f"{thumb_file if thumb_file else 'GAGAL'}")
    log(f"  YouTube  : "
        f"{'https://youtu.be/'+video_id if video_id else 'GAGAL'}")
    log("=" * 60)

def _cleanup(audio_file=None, file_list=None):
    import shutil
    if audio_file and os.path.exists(audio_file):
        try:
            os.remove(audio_file)
            log(f"  -> Hapus audio temp: {audio_file}")
        except:
            pass
    if os.path.exists("temp_clips"):
        try:
            shutil.rmtree("temp_clips")
            log("  -> Hapus temp_clips/")
        except:
            pass
    if file_list and os.path.exists(file_list):
        try:
            os.remove(file_list)
        except:
            pass

if __name__ == "__main__":
    main()
