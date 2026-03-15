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

from narasi import buat_narasi_dan_judul
from store  import kelola_bank_gambar, kelola_bank_video, kelola_video_lama

from config import (
    GEMINI_API_KEY,
    PEXELS_API_KEY,
    NAMA_CHANNEL,
    YOUTUBE_CATEGORY,
    YOUTUBE_TAGS,
)

FFMPEG_LOG = "ffmpeg_log.txt"


# ════════════════════════════════════════════════════════════
# KEN BURNS - 10 variasi gerakan kamera
# ════════════════════════════════════════════════════════════
KEN_BURNS = [
    # 1. Zoom in perlahan dari tengah
    "zoompan=z='min(zoom+0.0015,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=300:s=1920x1080:fps=30",
    # 2. Zoom out dari 1.5 ke 1.0
    "zoompan=z='if(eq(on,1),1.5,max(1.001,zoom-0.0015))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=300:s=1920x1080:fps=30",
    # 3. Pan kiri ke kanan + zoom ringan
    "zoompan=z='1.3':x='if(eq(on,1),0,min(iw-iw/zoom,x+2))':y='ih/2-(ih/zoom/2)':d=300:s=1920x1080:fps=30",
    # 4. Pan kanan ke kiri
    "zoompan=z='1.3':x='if(eq(on,1),iw-iw/zoom,max(0,x-2))':y='ih/2-(ih/zoom/2)':d=300:s=1920x1080:fps=30",
    # 5. Pan atas ke bawah
    "zoompan=z='1.3':x='iw/2-(iw/zoom/2)':y='if(eq(on,1),0,min(ih-ih/zoom,y+1.5))':d=300:s=1920x1080:fps=30",
    # 6. Pan bawah ke atas
    "zoompan=z='1.3':x='iw/2-(iw/zoom/2)':y='if(eq(on,1),ih-ih/zoom,max(0,y-1.5))':d=300:s=1920x1080:fps=30",
    # 7. Zoom in + diagonal kiri atas
    "zoompan=z='min(zoom+0.001,1.4)':x='if(eq(on,1),0,min(iw-iw/zoom,x+1.5))':y='if(eq(on,1),0,min(ih-ih/zoom,y+0.8))':d=300:s=1920x1080:fps=30",
    # 8. Zoom in + diagonal kanan bawah
    "zoompan=z='min(zoom+0.001,1.4)':x='if(eq(on,1),iw-iw/zoom,max(0,x-1.5))':y='if(eq(on,1),ih-ih/zoom,max(0,y-0.8))':d=300:s=1920x1080:fps=30",
    # 9. Zoom in lembut + geser kanan
    "zoompan=z='min(zoom+0.0008,1.25)':x='if(eq(on,1),0,min(iw-iw/zoom,x+1))':y='ih/2-(ih/zoom/2)':d=300:s=1920x1080:fps=30",
    # 10. Zoom out + geser kiri
    "zoompan=z='if(eq(on,1),1.3,max(1.001,zoom-0.001))':x='if(eq(on,1),iw-iw/zoom,max(0,x-1))':y='ih/2-(ih/zoom/2)':d=300:s=1920x1080:fps=30",
]


# ════════════════════════════════════════════════════════════
# XFADE TRANSITIONS - 28 jenis transisi random
# ════════════════════════════════════════════════════════════
XFADE_TRANSITIONS = [
    "fade", "fadeblack", "fadewhite",
    "wipeleft", "wiperight", "wipeup", "wipedown",
    "slideleft", "slideright", "slideup", "slidedown",
    "smoothleft", "smoothright", "smoothup", "smoothdown",
    "circleopen", "circleclose",
    "radial", "pixelize",
    "diagtl", "diagtr", "diagbl", "diagbr",
    "hlslice", "hrslice", "vuslice", "vdslice",
    "dissolve",
]


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
    print("  -> PERINGATAN: Font tidak ditemukan, pakai font default FFmpeg.")
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
            raise ValueError(f"Audio terlalu pendek ({durasi:.1f}s).")
        size_kb = os.path.getsize(output_audio) // 1024
        print(f"  -> ✅ Audio OK: {durasi:.0f}s ({durasi/60:.1f} menit) — {size_kb} KB")
        return durasi
    except ValueError as e:
        raise ValueError(str(e))


# ── Step 4: Render klip dengan Ken Burns + Watermark fix ─────

def render_satu_klip(args):
    i, img, font_sistem, output_klip = args

    # 1. Scale + pad ke 1920x1080 dengan background hitam
    scale_pad = (
        "scale=1920:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black"
    )

    # 2. Ken Burns random
    kb = random.choice(KEN_BURNS)

    # 3. FIX KRITIS: force format=yuv420p setelah zoompan
    #    agar drawtext tidak gagal diam-diam
    filter_vf = f"{scale_pad},{kb},format=yuv420p"

    # 4. Watermark — selalu tampil dengan background box
    if font_sistem:
        font_esc = escape_ffmpeg_path(font_sistem)
        x, y = random.choice([
            ("30",        "30"),
            ("w-tw-30",   "30"),
            ("30",        "h-th-40"),
            ("w-tw-30",   "h-th-40"),
        ])
        filter_vf += (
            f",drawtext=fontfile='{font_esc}'"
            f":text='{NAMA_CHANNEL}'"
            f":fontcolor=white"
            f":fontsize=32"
            f":x={x}:y={y}"
            f":box=1"
            f":boxcolor=black@0.45"
            f":boxborderw=8"
        )
    else:
        # Fallback: drawtext tanpa fontfile, pakai font default FFmpeg
        x, y = random.choice([
            ("30",        "30"),
            ("w-tw-30",   "30"),
            ("30",        "h-th-40"),
            ("w-tw-30",   "h-th-40"),
        ])
        filter_vf += (
            f",drawtext=text='{NAMA_CHANNEL}'"
            f":fontcolor=white"
            f":fontsize=32"
            f":x={x}:y={y}"
            f":box=1"
            f":boxcolor=black@0.45"
            f":boxborderw=8"
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
        log.write(f"\n=== Klip {i}: {os.path.basename(img)} ===\n")
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

    gambar_list = []
    folder_cari = ["gambar_bank", "gambar_static", "gambar_pexels", "."]
    for folder in folder_cari:
        for ext in ("*.jpg", "*.jpeg", "*.png"):
            gambar_list.extend(glob.glob(os.path.join(folder, ext)))

    gambar_list = list(set(os.path.abspath(g) for g in gambar_list))

    if not gambar_list:
        print("ERROR: Tidak ada gambar ditemukan!")
        return None

    random.shuffle(gambar_list)

    jumlah_klip = int(durasi_total_detik / 10) + 2
    print(f"  -> Bank: {len(gambar_list)} gambar, 0 video")
    print(f"  -> Target klip: {jumlah_klip}")

    # Spread merata pakai modulo
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

    list_txt = os.path.abspath("concat_videos.txt")
    with open(list_txt, "w", encoding="utf-8") as f:
        for i in sorted(klip_berhasil.keys()):
            path_aman = klip_berhasil[i].replace("\\", "/")
            f.write(f"file '{path_aman}'\n")

    return list_txt


# ── Step 5: Render final dengan xfade transition ──────────────

def render_video_final(file_list, audio, output, durasi):
    print("[5/6] Merender video final dengan xfade transition...")

    klip_paths = []
    with open(file_list, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("file '") and line.endswith("'"):
                path = line[6:-1]
                if os.path.exists(path):
                    klip_paths.append(path)

    if not klip_paths:
        print("  -> ERROR: Tidak ada klip valid!")
        return False

    if len(klip_paths) == 1:
        return _render_simple_concat(file_list, audio, output, durasi)

    DURASI_KLIP  = 10.0
    DURASI_TRANS = 0.8

    input_args = []
    for path in klip_paths:
        input_args.extend(["-i", path])
    input_args.extend(["-i", audio])
    audio_idx = len(klip_paths)

    filter_parts  = []
    trans_dipakai = []

    for i in range(len(klip_paths) - 1):
        trans  = random.choice(XFADE_TRANSITIONS)
        trans_dipakai.append(trans)
        offset = round((i + 1) * (DURASI_KLIP - DURASI_TRANS), 2)

        in_a = "[0:v]"  if i == 0                      else f"[vx{i-1}]"
        in_b = f"[{i+1}:v]"
        out  = "[vout]" if i == len(klip_paths) - 2    else f"[vx{i}]"

        filter_parts.append(
            f"{in_a}{in_b}xfade=transition={trans}"
            f":duration={DURASI_TRANS}:offset={offset}{out}"
        )

    fade_out_st = round(durasi - 1.5, 2)
    filter_parts.append(
        f"[vout]fade=t=in:st=0:d=0.8,"
        f"fade=t=out:st={fade_out_st}:d=1.0[vfinal]"
    )

    filter_complex = ";".join(filter_parts)
    unik_trans     = list(set(trans_dipakai))
    print(
        f"  -> {len(klip_paths)} klip, {len(trans_dipakai)} transisi: "
        f"{', '.join(unik_trans[:5])}{'...' if len(unik_trans) > 5 else ''}"
    )

    cmd = [
        "ffmpeg", "-y",
        *input_args,
        "-filter_complex", filter_complex,
        "-map", "[vfinal]",
        "-map", f"{audio_idx}:a",
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-t", str(durasi),
        output,
    ]

    with open(FFMPEG_LOG, "a", encoding="utf-8") as log:
        log.write("\n=== RENDER FINAL XFADE ===\n")
        log.write(f"Klip: {len(klip_paths)}, Transisi: {trans_dipakai}\n\n")
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=log)

    if result.returncode != 0:
        print("  -> xfade gagal, fallback ke simple concat...")
        return _render_simple_concat(file_list, audio, output, durasi)

    print("  -> ✅ Render final dengan xfade OK!")
    return True


def _render_simple_concat(file_list, audio, output, durasi):
    print("  -> Mode fallback: simple concat...")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", file_list,
        "-i", audio,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-t", str(durasi),
        output,
    ]
    with open(FFMPEG_LOG, "a", encoding="utf-8") as log:
        log.write("\n=== RENDER FALLBACK SIMPLE CONCAT ===\n")
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=log)
    return result.returncode == 0


# ── Generate Thumbnail dari frame video ──────────────────────

def buat_thumbnail(video_path, output_thumb="thumbnail.jpg"):
    print("  -> Generate thumbnail...")

    # Ambil frame di detik ke-3 (biasanya frame paling bagus)
    cmd_frame = [
        "ffmpeg", "-y",
        "-ss", "3",
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        output_thumb,
    ]
    with open(FFMPEG_LOG, "a", encoding="utf-8") as log:
        result = subprocess.run(cmd_frame, stdout=subprocess.DEVNULL, stderr=log)

    if result.returncode != 0 or not os.path.exists(output_thumb):
        print("  -> [GAGAL] Generate thumbnail dari video.")
        return None

    print(
        f"  -> ✅ Thumbnail OK: {output_thumb} "
        f"({os.path.getsize(output_thumb) // 1024} KB)"
    )
    return output_thumb


# ── Step 6: Upload ke YouTube + Thumbnail ────────────────────

def upload_ke_youtube(video_path, judul, deskripsi, tags, thumbnail_path=None):
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
                "privacyStatus":           "public",
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

        # ── Upload video ──────────────────────────────────────
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(
                    f"  -> Upload video: {int(status.progress() * 100)}%",
                    end="\r",
                )

        video_id = response.get("id")
        print(f"\n  -> ✅ Upload video sukses! https://youtu.be/{video_id}")

        # ── Upload thumbnail ──────────────────────────────────
        if thumbnail_path and os.path.exists(thumbnail_path):
            size_kb = os.path.getsize(thumbnail_path) // 1024
            print(f"  -> Upload thumbnail: {thumbnail_path} ({size_kb} KB)...")
            try:
                thumb_media = MediaFileUpload(
                    thumbnail_path,
                    mimetype="image/jpeg",
                    resumable=False,
                )
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=thumb_media,
                ).execute()
                print("  -> ✅ Thumbnail berhasil di-upload!")
            except Exception as e:
                print(f"  -> ⚠️ Thumbnail gagal upload: {e}")
                print("     (Video tetap OK, thumbnail pakai auto-generated YouTube)")
        else:
            print("  -> ⚠️ Thumbnail tidak tersedia, pakai auto-generated YouTube.")

        # ── Simpan riwayat ────────────────────────────────────
        with open("upload_history.json", "a", encoding="utf-8") as f:
            json.dump(
                {
                    "tanggal":   datetime.now().isoformat(),
                    "video_id":  video_id,
                    "judul":     judul,
                    "thumbnail": thumbnail_path or "auto",
                },
                f, ensure_ascii=False,
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

    audio_temp  = "suara.mp3"
    tanggal_str = datetime.now().strftime("%Y%m%d")
    video_hasil = f"Video_Emas_{tanggal_str}.mp4"

    print(f"\n{'='*60}")
    print(f" AUTO VIDEO EMAS - Info Logam Mulia")
    print(f" {datetime.now().strftime('%d %B %Y, %H:%M WIB')}")
    print(f"{'='*60}\n")

    # 0. Kelola bank gambar
    kelola_bank_gambar()
    kelola_video_lama()

    # 1. Scrape harga emas
    info = scrape_dan_kalkulasi_harga()
    if not info:
        print("Scraping gagal. Menghentikan proses.")
        return

    # 2. Buat narasi
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

    # 4. Render klip dengan Ken Burns
    file_list = proses_gambar(durasi)
    if not file_list:
        return

    # 5. Render video final dengan xfade
    sukses = render_video_final(file_list, audio_temp, video_hasil, durasi)
    bersihkan_temp(file_list, audio_temp)

    if sukses and os.path.exists(video_hasil):
        ukuran_mb = os.path.getsize(video_hasil) // 1024 // 1024
        print(f"\n✅ VIDEO SELESAI: {video_hasil} ({ukuran_mb} MB)")

        if ukuran_mb < 5:
            print(f"⚠️ Ukuran video terlalu kecil. Buka '{FFMPEG_LOG}' untuk debug.")
            return

        # Generate thumbnail dari frame video
        thumbnail = buat_thumbnail(video_hasil, "thumbnail.jpg")

        # 6. Upload YouTube + Thumbnail
        deskripsi = (
            f"Update harga emas Antam hari ini "
            f"{datetime.now().strftime('%d %B %Y')}.\n\n"
            f"Harga 1 gram : Rp {info['harga_sekarang']:,}\n"
            f"Status       : {info['status'].title()}\n\n"
            f"Informasi diambil langsung dari situs resmi Logam Mulia.\n\n"
            f"#HargaEmas #EmasAntam #InvestasiEmas #LogamMulia #EmasHariIni\n\n"
            f"Jangan lupa SUBSCRIBE dan aktifkan notifikasi!"
        ).replace(",", ".")

        upload_ke_youtube(video_hasil, judul, deskripsi, YOUTUBE_TAGS, thumbnail)

        # Bersihkan thumbnail setelah upload
        if thumbnail and os.path.exists(thumbnail):
            os.remove(thumbnail)
            print("  -> Thumbnail temp dihapus.")

    else:
        print(f"\n❌ GAGAL membuat video. Buka '{FFMPEG_LOG}' untuk detail.")


if __name__ == "__main__":
    asyncio.run(main())
    print("\n" + "=" * 60)
