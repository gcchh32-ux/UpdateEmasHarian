# renderer.py — Ken Burns + render klip + audio + render final
import os, glob, random, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import (VIDEO_WIDTH, VIDEO_HEIGHT, FPS,
                    NAMA_CHANNEL, FFMPEG_LOG,
                    FOLDER_GAMBAR, FOLDER_VIDEO_BANK)
from utils  import (log, font_path, escape_ffmpeg_path,
                    ffmpeg_duration, ffmpeg_is_valid, log_ffmpeg_tail)
from store import list_gambar, list_video_bank

# ════════════════════════════════════════════════════════════
# BAGIAN 1 — GENERATE SUARA (edge-tts)
# ════════════════════════════════════════════════════════════

def buat_suara(teks, output_audio):
    from config import VOICE, VOICE_RATE
    import re
    log(f"[3/6] Generate suara — voice:{VOICE} rate:{VOICE_RATE}...")

    teks_bersih = re.sub(
        r'\[.*?\]|\(.*?\)|\*.*?\*|[▲▼⬛📊📈📉💰🔥💥🚨🎯⚡😲🤔💡🛒🔴🟢⚠️📅💛]',
        '', teks
    ).strip()
    log(f"  -> Panjang teks: {len(teks_bersih)} karakter")

    cmd = [
        sys.executable, '-m', 'edge_tts',
        '--voice', VOICE,
        '--rate',  VOICE_RATE,
        '--text',  teks_bersih,
        '--write-media', output_audio,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log(f"  -> edge-tts stderr: {result.stderr[:300]}")
        raise RuntimeError(f"edge-tts gagal: {result.stderr[:200]}")

    if not ffmpeg_is_valid(output_audio, min_size_kb=5):
        raise FileNotFoundError("File audio tidak terbuat atau terlalu kecil!")

    durasi = ffmpeg_duration(output_audio)
    size_kb = os.path.getsize(output_audio) // 1024
    log(f"  -> ✅ Audio OK: {durasi:.0f}s "
        f"({durasi/60:.1f} menit) — {size_kb} KB")

    if durasi < 30:
        raise ValueError(
            f"Audio terlalu pendek ({durasi:.1f}s)! "
            f"Narasi mungkin terlalu singkat."
        )
    return durasi


# ════════════════════════════════════════════════════════════
# BAGIAN 2 — KEN BURNS FILTER
# ════════════════════════════════════════════════════════════

def _get_ken_burns_filter(durasi=10.0):
    try:
        dur = max(5.0, float(durasi))
    except:
        dur = 10.0
    d_frames = int(FPS * dur)
    mode     = random.randint(1, 6)

    if mode == 1:
        z    = "if(eq(on,1),1.0,min(zoom+0.0004,1.15))"
        x    = "iw/2-(iw/zoom/2)"
        y    = "ih/2-(ih/zoom/2)"
        name = "ZoomIn_Center"
    elif mode == 2:
        z    = "if(eq(on,1),1.15,max(zoom-0.0004,1.0))"
        x    = "iw/2-(iw/zoom/2)"
        y    = "ih/2-(ih/zoom/2)"
        name = "ZoomOut_Center"
    elif mode == 3:
        z    = "if(eq(on,1),1.02,min(zoom+0.0003,1.15))"
        x    = f"(iw-ow)*(on/{d_frames})*0.6"
        y    = "ih/2-(ih/zoom/2)"
        name = "PanLeft_Right"
    elif mode == 4:
        z    = "if(eq(on,1),1.02,min(zoom+0.0003,1.15))"
        x    = f"(iw-ow)*(1-on/{d_frames})*0.6"
        y    = "ih/2-(ih/zoom/2)"
        name = "PanRight_Left"
    elif mode == 5:
        z    = "if(eq(on,1),1.02,min(zoom+0.0003,1.15))"
        x    = "iw/2-(iw/zoom/2)"
        y    = f"(ih-oh)*(on/{d_frames})*0.6"
        name = "PanTop_Bottom"
    else:
        z    = "if(eq(on,1),1.02,min(zoom+0.0003,1.15))"
        x    = "iw/2-(iw/zoom/2)"
        y    = f"(ih-oh)*(1-on/{d_frames})*0.6"
        name = "PanBottom_Top"

    zoompan = (
        f"zoompan=z='{z}':x='{x}':y='{y}':"
        f"d={d_frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={FPS}"
    )
    vf = (
        f"scale={VIDEO_WIDTH*2}:{VIDEO_HEIGHT*2}:"
        f"force_original_aspect_ratio=increase,"
        f"crop={VIDEO_WIDTH*2}:{VIDEO_HEIGHT*2},"
        f"format=yuv420p,"
        f"{zoompan},"
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
        f"fps={FPS},"
        f"fade=t=in:st=0:d=0.5,"
        f"fade=t=out:st={dur-0.5:.1f}:d=0.5"
    )
    return vf, name


# ════════════════════════════════════════════════════════════
# BAGIAN 3 — RENDER KLIP GAMBAR (Ken Burns)
# ════════════════════════════════════════════════════════════

def _render_klip_gambar(args):
    i, img_path, fp, output_klip = args
    durasi_klip = random.choice([8, 10, 12])
    vf, mode    = _get_ken_burns_filter(durasi_klip)

    # Tambah watermark channel
    if fp:
        fe    = escape_ffmpeg_path(fp)
        x, y  = random.choice([
            ("30","30"), ("w-tw-30","30"),
            ("30","h-th-30"), ("w-tw-30","h-th-30")
        ])
        ch_esc = NAMA_CHANNEL.replace("'", "\\'")
        vf    += (f",drawtext=fontfile='{fe}':text='{ch_esc}':"
                  f"fontcolor=white@0.45:fontsize=26:x={x}:y={y}")

    cmd = [
        'ffmpeg', '-y',
        '-loop', '1', '-framerate', str(FPS), '-i', img_path,
        '-f', 'lavfi', '-i',
        'anullsrc=channel_layout=stereo:sample_rate=44100',
        '-vf', vf,
        '-map', '0:v', '-map', '1:a',
        '-c:v', 'libx264', '-preset', 'faster',
        '-pix_fmt', 'yuv420p', '-crf', '23',
        '-c:a', 'aac', '-ar', '44100', '-ac', '2',
        '-t', str(durasi_klip),
        output_klip,
    ]
    with open(FFMPEG_LOG, 'a', encoding='utf-8') as lf:
        lf.write(f"\n=== KLIP-IMG {i} [{mode}]: "
                 f"{os.path.basename(img_path)} ===\n")
        result = subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=lf
        )

    ok = (result.returncode == 0
          and ffmpeg_is_valid(output_klip, min_size_kb=10))
    if not ok:
        log(f"  -> [GAGAL] Klip-IMG {i}: {os.path.basename(img_path)}")
        return None
    return i, output_klip, durasi_klip


# ════════════════════════════════════════════════════════════
# BAGIAN 4 — RENDER KLIP VIDEO BANK
# ════════════════════════════════════════════════════════════

def _render_klip_video(args):
    i, vid_path, fp, output_klip = args
    durasi_klip = random.choice([8, 10, 12])

    # Durasi sumber
    try:
        dur_src = ffmpeg_duration(vid_path)
    except:
        dur_src = 30.0
    if dur_src < 3:
        log(f"  -> Skip video terlalu pendek: {os.path.basename(vid_path)}")
        return None

    # Titik mulai random
    max_start = max(0, dur_src - durasi_klip - 1)
    start     = round(random.uniform(0, max_start), 1) if max_start > 0 else 0.0

    vf = (
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
        f"force_original_aspect_ratio=decrease,"
        f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
        f"format=yuv420p,"
        f"fps={FPS},"
        f"fade=t=in:st=0:d=0.5,"
        f"fade=t=out:st={durasi_klip-0.5:.1f}:d=0.5"
    )

    if fp:
        fe    = escape_ffmpeg_path(fp)
        x, y  = random.choice([
            ("30","30"), ("w-tw-30","30"),
            ("30","h-th-30"), ("w-tw-30","h-th-30")
        ])
        ch_esc = NAMA_CHANNEL.replace("'", "\\'")
        vf    += (f",drawtext=fontfile='{fe}':text='{ch_esc}':"
                  f"fontcolor=white@0.45:fontsize=26:x={x}:y={y}")

    cmd = [
        'ffmpeg', '-y',
        '-ss', str(start),
        '-i', vid_path,
        '-t', str(durasi_klip),
        '-vf', vf,
        '-c:v', 'libx264', '-preset', 'faster',
        '-pix_fmt', 'yuv420p', '-crf', '23',
        '-c:a', 'aac', '-ar', '44100', '-ac', '2',
        output_klip,
    ]
    with open(FFMPEG_LOG, 'a', encoding='utf-8') as lf:
        lf.write(f"\n=== KLIP-VID {i}: "
                 f"{os.path.basename(vid_path)} (ss={start}) ===\n")
        result = subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=lf
        )

    ok = (result.returncode == 0
          and ffmpeg_is_valid(output_klip, min_size_kb=10))
    if not ok:
        log(f"  -> [GAGAL] Klip-VID {i}: {os.path.basename(vid_path)}")
        return None
    return i, output_klip, durasi_klip


# ════════════════════════════════════════════════════════════
# BAGIAN 5 — PROSES SEMUA KLIP (PARALEL)
# ════════════════════════════════════════════════════════════

def proses_semua_klip(durasi_total_detik):
    log(f"[4/6] Menyiapkan klip visual "
        f"(target: {durasi_total_detik:.0f}s)...")
    os.makedirs("temp_clips", exist_ok=True)

    gambar_list = list_gambar()
    video_list  = list_video_bank()
    log(f"  -> Bank: {len(gambar_list)} gambar, "
        f"{len(video_list)} video")

    if not gambar_list and not video_list:
        log("  -> FATAL: Bank gambar & video kosong!")
        log(f"  -> Pastikan PEXELS_API_KEY valid dan "
            f"folder {FOLDER_GAMBAR}/ atau {FOLDER_VIDEO_BANK}/ ada.")
        return None

    jumlah_klip = int(durasi_total_detik / 10) + 4
    log(f"  -> Target klip: {jumlah_klip}")

    # Proporsi 60% video, 40% gambar
    if video_list and gambar_list:
        n_video  = int(jumlah_klip * 0.6)
        n_gambar = jumlah_klip - n_video
    elif video_list:
        n_video, n_gambar = jumlah_klip, 0
    else:
        n_video, n_gambar = 0, jumlah_klip

    fp      = font_path()
    tasks   = []
    counter = 0

    def repeat_list(lst, n):
        result = []
        while len(result) < n:
            result.extend(lst)
        return result[:n]

    if n_video > 0 and video_list:
        vids = repeat_list(
            random.sample(video_list, min(len(video_list), n_video)),
            n_video
        )
        random.shuffle(vids)
        for vid in vids:
            out = os.path.abspath(f"temp_clips/klip_{counter:04d}.mp4")
            tasks.append(('video', counter, vid, fp, out))
            counter += 1

    if n_gambar > 0 and gambar_list:
        imgs = repeat_list(
            random.sample(gambar_list, min(len(gambar_list), n_gambar)),
            n_gambar
        )
        random.shuffle(imgs)
        for img in imgs:
            out = os.path.abspath(f"temp_clips/klip_{counter:04d}.mp4")
            tasks.append(('gambar', counter, img, fp, out))
            counter += 1

    # Acak urutan agar video & gambar bercampur
    random.shuffle(tasks)

    max_workers = min(3, os.cpu_count() or 2)
    log(f"  -> Render {len(tasks)} klip "
        f"({max_workers} thread paralel)...")

    klip_berhasil = {}

    def run_task(task):
        tipe = task[0]
        if tipe == 'video':
            _, i, path, fp_, out = task
            return _render_klip_video((i, path, fp_, out))
        else:
            _, i, path, fp_, out = task
            return _render_klip_gambar((i, path, fp_, out))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(run_task, t): t[1] for t in tasks
        }
        for future in as_completed(futures):
            hasil = future.result()
            if hasil:
                idx, path, dur = hasil
                klip_berhasil[idx] = (path, dur)
                print(
                    f"  -> {len(klip_berhasil)}/{len(tasks)} klip selesai",
                    end='\r', flush=True
                )
    print()
    log(f"  -> {len(klip_berhasil)}/{len(tasks)} klip berhasil")

    if not klip_berhasil:
        log(f"  -> FATAL: Semua klip gagal! Cek {FFMPEG_LOG}")
        log_ffmpeg_tail(30)
        return None

    # Tulis concat list
    list_txt = os.path.abspath("concat_videos.txt")
    with open(list_txt, 'w', encoding='utf-8') as f:
        for idx in sorted(klip_berhasil.keys()):
            path_aman = klip_berhasil[idx][0].replace('\\', '/')
            f.write(f"file '{path_aman}'\n")

    total_dur = sum(d for _, d in klip_berhasil.values())
    log(f"  -> Total durasi klip: {total_dur:.0f}s "
        f"(audio: {durasi_total_detik:.0f}s)")
    return list_txt


# ════════════════════════════════════════════════════════════
# BAGIAN 6 — RENDER VIDEO FINAL
# ════════════════════════════════════════════════════════════

def render_video_final(file_list, audio, output, durasi):
    log(f"[5/6] Render video final → {output}...")

    # Baca & validasi concat list
    with open(file_list, 'r', encoding='utf-8') as f:
        entries = [l.strip() for l in f if l.strip()]
    log(f"  -> Concat list: {len(entries)} entri")

    valid = 0
    for line in entries:
        path = line.replace("file '", "").replace("'", "").strip()
        if ffmpeg_is_valid(path, min_size_kb=10):
            valid += 1
        else:
            log(f"  -> WARNING missing/invalid: {path}")
    log(f"  -> File valid: {valid}/{len(entries)}")

    if valid == 0:
        log("  -> FATAL: Tidak ada klip valid!")
        return False

    cmd = [
        'ffmpeg', '-y',
        '-f', 'concat', '-safe', '0', '-i', file_list,
        '-i', audio,
        '-map', '0:v', '-map', '1:a',
        # Normalize format & fps — FIX BLANK HITAM
        '-vf', f'format=yuv420p,fps={FPS},'
               f'scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '22',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k', '-ar', '44100', '-ac', '2',
        '-t', str(int(durasi) + 3),
        '-avoid_negative_ts', 'make_zero',   # Fix timestamp
        '-fflags', '+genpts',                 # Fix blank frames
        '-movflags', '+faststart',
        output,
    ]

    log("  -> Menjalankan FFmpeg render final...")
    with open(FFMPEG_LOG, 'a', encoding='utf-8') as lf:
        lf.write("\n=== RENDER FINAL ===\n")
        lf.write(' '.join(cmd) + '\n')
        result = subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=lf
        )

    log(f"  -> FFmpeg return code: {result.returncode}")

    if result.returncode != 0:
        log(f"  -> ERROR render final! Cek {FFMPEG_LOG}")
        log_ffmpeg_tail(25)
        return False

    if not os.path.exists(output):
        log("  -> ERROR: Output tidak terbuat!")
        return False

    ukuran    = os.path.getsize(output)
    ukuran_mb = ukuran // 1024 // 1024
    log(f"  -> ✅ Video OK: {ukuran_mb} MB "
        f"({ukuran:,} bytes)".replace(",", "."))

    if ukuran_mb < 5:
        log(f"  -> WARNING: Ukuran video sangat kecil "
            f"({ukuran_mb} MB)! Mungkin ada masalah.")
    return True
