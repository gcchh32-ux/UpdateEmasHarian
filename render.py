# render.py
import os, random, subprocess, sys, time, asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import (
    VIDEO_WIDTH, VIDEO_HEIGHT, FPS,
    NAMA_CHANNEL, FFMPEG_LOG,
    FOLDER_GAMBAR, FOLDER_VIDEO_BANK,
)
from utils import (
    log, font_path, escape_ffmpeg_path,
    ffmpeg_duration, ffmpeg_is_valid, log_ffmpeg_tail,
)
from store import list_gambar, list_video_bank

# ════════════════════════════════════════════════════════════
# BAGIAN 1 — GENERATE SUARA
# ════════════════════════════════════════════════════════════

def buat_suara(teks, output_audio):
    from config import VOICE, VOICE_RATE
    import re, asyncio, threading
    log("[3/6] Generate suara...")

    teks_bersih = re.sub(
        r'\[.*?\]|\(.*?\)|\*.*?\*|'
        r'[▲▼⬛📊📈📉💰🔥💥🚨🎯⚡😲🤔💡🛒🔴🟢⚠️📅💛]',
        '', teks
    ).strip()
    teks_bersih = re.sub(r'\n+', ' ', teks_bersih)
    teks_bersih = re.sub(r'\s+', ' ', teks_bersih).strip()
    log(f"  -> Panjang teks: {len(teks_bersih)} karakter")

    async def _generate():
        import edge_tts
        communicate = edge_tts.Communicate(
            text=teks_bersih,
            voice=VOICE,
            rate=VOICE_RATE,
        )
        await communicate.save(output_audio)

    MAX_ATTEMPT = 4
    for attempt in range(1, MAX_ATTEMPT + 1):
        log(f"  -> edge-tts attempt {attempt}/{MAX_ATTEMPT}...")
        error_container = []

        def _run_in_thread():
            try:
                asyncio.run(_generate())
            except Exception as e:
                error_container.append(e)

        t = threading.Thread(target=_run_in_thread)
        t.start()
        t.join(timeout=240)

        if t.is_alive():
            log(f"  -> Timeout attempt {attempt}, tunggu 15s lalu coba lagi...")
            if attempt < MAX_ATTEMPT:
                time.sleep(15)
            continue

        if error_container:
            log(f"  -> Error: {error_container[0]}, tunggu 10s lalu coba lagi...")
            if attempt < MAX_ATTEMPT:
                time.sleep(10)
            continue

        if not ffmpeg_is_valid(output_audio, min_size_kb=5):
            log(f"  -> Audio tidak valid attempt {attempt}, coba lagi...")
            if attempt < MAX_ATTEMPT:
                time.sleep(10)
            continue

        durasi = ffmpeg_duration(output_audio)
        size_kb = os.path.getsize(output_audio) // 1024
        log(f"  -> ✅ Audio OK: {durasi:.0f}s ({durasi/60:.1f} menit) — {size_kb} KB")
        if durasi < 30:
            raise ValueError(f"Audio terlalu pendek ({durasi:.1f}s)!")
        return durasi

    raise RuntimeError(f"edge-tts gagal setelah {MAX_ATTEMPT} percobaan!")



# ════════════════════════════════════════════════════════════
# BAGIAN 2 — KEN BURNS FILTER (6 variasi, tidak boleh sama)
# ════════════════════════════════════════════════════════════

_KB_MODES     = list(range(1, 7))
_last_kb_mode = None


def _get_ken_burns_filter(durasi=10.0, exclude=None):
    global _last_kb_mode
    try:
        dur = max(5.0, float(durasi))
    except Exception:
        dur = 10.0

    d_frames = int(FPS * dur)

    # Pilih mode random, hindari sama dengan sebelumnya
    pool = [m for m in _KB_MODES if m != exclude]
    mode = random.choice(pool)
    _last_kb_mode = mode

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
    return vf, name, mode


# ════════════════════════════════════════════════════════════
# BAGIAN 3 — RENDER KLIP GAMBAR
# ════════════════════════════════════════════════════════════

def _render_klip_gambar(args):
    i, img_path, fp, output_klip, exclude_mode = args

    durasi_klip       = random.choice([8, 10, 12])
    vf, mode, kb_mode = _get_ken_burns_filter(
        durasi_klip, exclude=exclude_mode
    )

    if fp:
        fe     = escape_ffmpeg_path(fp)
        x, y   = random.choice([
            ("30", "30"), ("w-tw-30", "30"),
            ("30", "h-th-30"), ("w-tw-30", "h-th-30"),
        ])
        ch_esc = NAMA_CHANNEL.replace("'", "\\'")
        vf    += (
            f",drawtext=fontfile='{fe}'"
            f":text='{ch_esc}'"
            f":fontcolor=white@0.45:fontsize=26"
            f":x={x}:y={y}"
        )

    cmd = [
        'ffmpeg', '-y',
        '-loop', '1',
        '-framerate', str(FPS),
        '-i', img_path,
        '-f', 'lavfi',
        '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
        '-vf', vf,
        '-map', '0:v', '-map', '1:a',
        '-c:v', 'libx264',
        '-preset', 'faster',
        '-pix_fmt', 'yuv420p',
        '-crf', '23',
        '-c:a', 'aac',
        '-ar', '44100',
        '-ac', '2',
        '-t', str(durasi_klip),
        output_klip,
    ]

    with open(FFMPEG_LOG, 'a', encoding='utf-8') as lf:
        lf.write(
            f"\n=== KLIP-IMG {i} [{mode}]: "
            f"{os.path.basename(img_path)} ===\n"
        )
        result = subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=lf
        )

    ok = (result.returncode == 0
          and ffmpeg_is_valid(output_klip, min_size_kb=10))
    if not ok:
        log(f"  -> [GAGAL] Klip-IMG {i}: "
            f"{os.path.basename(img_path)}")
        return None

    return i, output_klip, durasi_klip, kb_mode


# ════════════════════════════════════════════════════════════
# BAGIAN 4 — RENDER KLIP VIDEO BANK
# ════════════════════════════════════════════════════════════

def _render_klip_video(args):
    i, vid_path, fp, output_klip = args

    durasi_klip = random.choice([8, 10, 12])
    try:
        dur_src = ffmpeg_duration(vid_path)
    except Exception:
        dur_src = 30.0

    if dur_src < 3:
        log(f"  -> Skip video pendek: "
            f"{os.path.basename(vid_path)}")
        return None

    max_start = max(0, dur_src - durasi_klip - 1)
    start     = (round(random.uniform(0, max_start), 1)
                 if max_start > 0 else 0.0)

    vf = (
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
        f"force_original_aspect_ratio=decrease,"
        f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
        f"(ow-iw)/2:(oh-ih)/2,"
        f"format=yuv420p,"
        f"fps={FPS},"
        f"fade=t=in:st=0:d=0.5,"
        f"fade=t=out:st={durasi_klip-0.5:.1f}:d=0.5"
    )

    if fp:
        fe     = escape_ffmpeg_path(fp)
        x, y   = random.choice([
            ("30", "30"), ("w-tw-30", "30"),
            ("30", "h-th-30"), ("w-tw-30", "h-th-30"),
        ])
        ch_esc = NAMA_CHANNEL.replace("'", "\\'")
        vf    += (
            f",drawtext=fontfile='{fe}'"
            f":text='{ch_esc}'"
            f":fontcolor=white@0.45:fontsize=26"
            f":x={x}:y={y}"
        )

    cmd = [
        'ffmpeg', '-y',
        '-ss', str(start),
        '-i', vid_path,
        '-t', str(durasi_klip),
        '-vf', vf,
        '-c:v', 'libx264',
        '-preset', 'faster',
        '-pix_fmt', 'yuv420p',
        '-crf', '23',
        '-c:a', 'aac',
        '-ar', '44100',
        '-ac', '2',
        output_klip,
    ]

    with open(FFMPEG_LOG, 'a', encoding='utf-8') as lf:
        lf.write(
            f"\n=== KLIP-VID {i}: "
            f"{os.path.basename(vid_path)} "
            f"(ss={start}) ===\n"
        )
        result = subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=lf
        )

    ok = (result.returncode == 0
          and ffmpeg_is_valid(output_klip, min_size_kb=10))
    if not ok:
        log(f"  -> [GAGAL] Klip-VID {i}: "
            f"{os.path.basename(vid_path)}")
        return None

    return i, output_klip, durasi_klip


# ════════════════════════════════════════════════════════════
# BAGIAN 5 — PROSES SEMUA KLIP PARALEL
# ════════════════════════════════════════════════════════════

def proses_semua_klip(durasi_total_detik):
    log(f"[4/6] Menyiapkan klip visual "
        f"(target:{durasi_total_detik:.0f}s)...")
    os.makedirs("temp_clips", exist_ok=True)

    gambar_list = list_gambar()
    video_list  = list_video_bank()

    log(f"  -> Bank: {len(gambar_list)} gambar, "
        f"{len(video_list)} video")

    if not gambar_list and not video_list:
        log("  -> FATAL: Bank gambar & video kosong!")
        return None

    jumlah_klip = int(durasi_total_detik / 10) + 4
    log(f"  -> Target klip: {jumlah_klip}")

    if video_list and gambar_list:
        n_video  = int(jumlah_klip * 0.2)
        n_gambar = jumlah_klip - n_video
    elif video_list:
        n_video, n_gambar = jumlah_klip, 0
    else:
        n_video, n_gambar = 0, jumlah_klip

    fp      = font_path()
    tasks   = []
    counter = 0

    # ── Video bank ────────────────────────────────────────
    if n_video > 0 and video_list:
        def repeat_list(lst, n):
            result = []
            while len(result) < n:
                result.extend(lst)
            return result[:n]

        vids = repeat_list(
            random.sample(
                video_list,
                min(len(video_list), n_video)
            ),
            n_video,
        )
        random.shuffle(vids)
        for vid in vids:
            out = os.path.abspath(
                f"temp_clips/klip_{counter:04d}.mp4"
            )
            tasks.append(('video', counter, vid, fp, out))
            counter += 1

    # ── Gambar — pakai TEPAT 2 gambar, alternasi ─────────
    if n_gambar > 0 and gambar_list:
        # Gunakan semua gambar yang tersedia, acak urutannya
        pool_img = gambar_list.copy()
        random.shuffle(pool_img)
        # Extend pool kalau gambar kurang dari jumlah klip yang dibutuhkan
        while len(pool_img) < n_gambar:
            extra = gambar_list.copy()
            random.shuffle(extra)
            pool_img.extend(extra)
        last_kb = None
        for j in range(n_gambar):
            img = pool_img[j % len(pool_img)]
            out = os.path.abspath(
                f"temp_clips/klip_{counter:04d}.mp4"
            )
            tasks.append(
                ('gambar', counter, img, fp, out, last_kb)
            )
            last_kb = (last_kb % 6 + 1) if last_kb else 1
            counter += 1


    random.shuffle(tasks)

    max_workers = min(3, os.cpu_count() or 2)
    log(f"  -> Render {len(tasks)} klip "
        f"({max_workers} thread)...")

    klip_berhasil = {}

    def run_task(task):
        tipe = task[0]
        if tipe == 'video':
            _, i, path, fp_, out = task
            return _render_klip_video((i, path, fp_, out))
        else:
            # gambar: bisa 5 atau 6 elemen
            if len(task) == 6:
                _, i, path, fp_, out, excl = task
            else:
                _, i, path, fp_, out = task
                excl = None
            return _render_klip_gambar((i, path, fp_, out, excl))

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {
            ex.submit(run_task, t): t[1] for t in tasks
        }
        for future in as_completed(futures):
            hasil = future.result()
            if hasil:
                if len(hasil) == 4:
                    idx, path, dur, _ = hasil
                else:
                    idx, path, dur = hasil
                klip_berhasil[idx] = (path, dur)
            print(
                f"  -> {len(klip_berhasil)}"
                f"/{len(tasks)} klip selesai",
                end='\r', flush=True,
            )

    print()
    log(f"  -> {len(klip_berhasil)}/{len(tasks)} "
        f"klip berhasil")

    if not klip_berhasil:
        log(f"  -> FATAL: Semua klip gagal! Cek {FFMPEG_LOG}")
        log_ffmpeg_tail(30)
        return None

    list_txt = os.path.abspath("concat_videos.txt")
    with open(list_txt, 'w', encoding='utf-8') as f:
        for idx in sorted(klip_berhasil.keys()):
            path_aman = (klip_berhasil[idx][0]
                         .replace('\\', '/'))
            f.write(f"file '{path_aman}'\n")

    total_dur = sum(d for _, d in klip_berhasil.values())
    log(f"  -> Total durasi klip: {total_dur:.0f}s "
        f"(audio:{durasi_total_detik:.0f}s)")
    return list_txt


# ════════════════════════════════════════════════════════════
# BAGIAN 6 — RENDER VIDEO FINAL
# ════════════════════════════════════════════════════════════

def render_video_final(file_list, audio, output, durasi):
    log(f"[5/6] Render video final → {output}...")

    with open(file_list, 'r', encoding='utf-8') as f:
        entries = [l.strip() for l in f if l.strip()]
    log(f"  -> Concat list: {len(entries)} entri")

    valid = 0
    for line in entries:
        path = (line.replace("file '", "")
                    .replace("'", "").strip())
        if ffmpeg_is_valid(path, min_size_kb=10):
            valid += 1
        else:
            log(f"  -> WARNING invalid: {path}")
    log(f"  -> File valid: {valid}/{len(entries)}")

    if valid == 0:
        log("  -> FATAL: Tidak ada klip valid!")
        return False

    cmd = [
        'ffmpeg', '-y',
        '-f', 'concat', '-safe', '0', '-i', file_list,
        '-i', audio,
        '-map', '0:v',
        '-map', '1:a',
        '-vf', (
            f'format=yuv420p,fps={FPS},'
            f'scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}'
        ),
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '22',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-ar', '44100',
        '-ac', '2',
        '-t', str(int(durasi) + 3),
        '-avoid_negative_ts', 'make_zero',
        '-fflags', '+genpts',
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
    log(f"  -> ✅ Video OK: {ukuran_mb} MB")

    if ukuran_mb < 5:
        log(f"  -> WARNING: Ukuran sangat kecil "
            f"({ukuran_mb} MB)!")

    return True
