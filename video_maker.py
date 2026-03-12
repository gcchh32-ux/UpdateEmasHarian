# video_maker.py — MAIN ORCHESTRATOR v7.2
import os, glob, asyncio
from datetime import datetime
from config   import NAMA_CHANNEL, CHANNEL_ID, NARASI_GAYA, CFG, FFMPEG_LOG
from storage  import kelola_bank_gambar, kelola_bank_video, kelola_video_lama, debug_storage
from scraper  import scrape_dan_kalkulasi_harga
from narasi   import buat_narasi_dan_judul
from renderer import buat_suara, proses_semua_klip, render_video_final
from thumb import buat_thumbnail
from uploader  import upload_ke_youtube

def bersihkan_temp(file_list=None, audio=None):
    import shutil
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

async def main():
    with open(FFMPEG_LOG, 'w', encoding='utf-8') as f:
        f.write(f"FFmpeg Log — {datetime.now()}\n{'='*60}\n")

    audio_temp  = "suara_temp.mp3"
    tanggal_str = datetime.now().strftime('%Y%m%d_%H%M')
    video_hasil = f"Video_Emas_{tanggal_str}.mp4"

    print(f"\n{'='*60}")
    print(f"  AUTO VIDEO EMAS v7.2 — {NAMA_CHANNEL}")
    print(f"  Channel ID  : {CHANNEL_ID}")
    print(f"  Gaya Narasi : {NARASI_GAYA}")
    print(f"  Skema Warna : {CFG['skema_warna']}")
    print(f"  Waktu       : {datetime.now().strftime('%d %B %Y, %H:%M WIB')}")
    print(f"{'='*60}\n")

    debug_storage()

    try:
        # STEP 0 — Storage
        kelola_bank_gambar()
        kelola_bank_video()
        kelola_video_lama()

        # STEP 1 — Scraping
        info, data_harga = scrape_dan_kalkulasi_harga()
        if not info:
            print("FATAL: Scraping harga gagal.")
            return

        # STEP 2 — Narasi & Judul
        judul, narasi = buat_narasi_dan_judul(info, data_harga)
        print(f"\n{'='*60}")
        print(f"JUDUL: {judul}")
        print(f"{'='*60}\n")

        # STEP 3 — Suara
        try:
            durasi = buat_suara(narasi, audio_temp)
        except Exception as e:
            print(f"FATAL: Suara gagal: {e}")
            return

        # STEP 4 — Klip visual
        file_list = proses_semua_klip(durasi)
        if not file_list:
            print("FATAL: Tidak ada klip berhasil.")
            bersihkan_temp(file_list, audio_temp)
            return

        # STEP 5 — Render final
        sukses = render_video_final(file_list, audio_temp, video_hasil, durasi)
        bersihkan_temp(file_list, audio_temp)
        if not sukses:
            print("FATAL: Render final gagal.")
            return

        ukuran_mb = os.path.getsize(video_hasil) // 1024 // 1024
        print(f"\n✅ VIDEO: {video_hasil} ({ukuran_mb} MB)")

        # STEP 5b — Thumbnail
        thumbnail_file = f"thumbnail_{tanggal_str}.jpg"
        thumbnail_path = buat_thumbnail(info, judul, thumbnail_file)

        # STEP 6 — Upload
        deskripsi = (
            f"Update harga emas Antam {datetime.now().strftime('%d %B %Y')}.\n\n"
            f"✅ Harga 1 gram : Rp {info['harga_sekarang']:,}\n"
            f"📊 Status       : {info['status']}\n\n"
            f"#HargaEmas #EmasAntam #InvestasiEmas #LogamMulia\n\n"
            f"Subscribe & aktifkan 🔔 notifikasi!\n{NAMA_CHANNEL}"
        ).replace(",",".")

        from config import YOUTUBE_TAGS
        video_id = upload_ke_youtube(video_hasil, judul, deskripsi,
                                     YOUTUBE_TAGS, thumbnail_path)

        print(f"\n{'='*60}")
        print(f"  Video    : {video_hasil} ({ukuran_mb} MB)")
        print(f"  Thumbnail: {thumbnail_file}")
        print(f"  YouTube  : {'https://youtu.be/'+video_id if video_id else 'GAGAL'}")
        print(f"{'='*60}")

    except Exception as e:
        import traceback
        print(f"\nFATAL EXCEPTION: {type(e).__name__}: {e}")
        traceback.print_exc()
        bersihkan_temp(
            "concat_videos.txt" if os.path.exists("concat_videos.txt") else None,
            audio_temp if os.path.exists(audio_temp) else None
        )

if __name__ == "__main__":
    asyncio.run(main())

