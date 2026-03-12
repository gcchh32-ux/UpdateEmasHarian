# utils.py — Helper functions bersama
import os, re, shutil, subprocess
from datetime import datetime

# ── Import config ──────────────────────────────────────────
from config import (NAMA_CHANNEL, VIDEO_WIDTH, VIDEO_HEIGHT,
                    FPS, FFMPEG_LOG)

# ════════════════════════════════════════════════════════════
# LOG
# ════════════════════════════════════════════════════════════

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# ════════════════════════════════════════════════════════════
# FONT
# ════════════════════════════════════════════════════════════

def font_path():
    lokal = os.path.abspath("font_temp.ttf")
    if os.path.exists(lokal):
        return lokal
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                shutil.copy(path, lokal)
                log(f"  -> Font disalin dari: {path}")
                return lokal
            except:
                continue
    log("  -> WARNING: Tidak ada font ditemukan, watermark dinonaktifkan.")
    return None

def get_font(fp, size):
    from PIL import ImageFont
    if fp:
        try:
            return ImageFont.truetype(fp, size)
        except:
            pass
    return ImageFont.load_default()

# ════════════════════════════════════════════════════════════
# TEXT HELPERS
# ════════════════════════════════════════════════════════════

def wrap_text(text, max_chars=26):
    """Bungkus teks ke beberapa baris berdasarkan max karakter."""
    text  = re.sub(r'[▲▼⬛🔥💥🚨🎯💰📊📈📉⚡😲🤔💡🛒🔴🟢⚠️📅💛]', '', text).strip()
    words = text.split()
    baris, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if len(test) <= max_chars:
            cur = test
        else:
            if cur:
                baris.append(cur)
            cur = w
    if cur:
        baris.append(cur)
    return baris[:3]

def bersihkan_teks_tts(teks):
    """Bersihkan teks untuk TTS — hapus simbol/markdown."""
    teks = re.sub(r'\[.*?\]|\(.*?\)|\*.*?\*', '', teks)
    teks = re.sub(r'[▲▼⬛📊📈📉💰🔥💥🚨🎯⚡😲🤔💡🛒🔴🟢⚠️📅💛]', '', teks)
    return teks.strip()

def rp(angka):
    """Format angka ke Rupiah: Rp 1.234.567"""
    return f"Rp {angka:,}".replace(",", ".")

# ════════════════════════════════════════════════════════════
# FFMPEG HELPERS
# ════════════════════════════════════════════════════════════

def escape_ffmpeg_path(path):
    """Escape path untuk dipakai di FFmpeg filter."""
    return path.replace('\\', '/').replace(':', '\\:')

def ffmpeg_duration(file_path):
    """Ambil durasi file audio/video via ffprobe."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error',
             '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1',
             file_path],
            capture_output=True, text=True, timeout=15
        )
        return float(result.stdout.strip())
    except:
        return 0.0

def ffmpeg_is_valid(file_path, min_size_kb=10):
    """Cek apakah file video/audio valid dan tidak kosong."""
    if not os.path.exists(file_path):
        return False
    if os.path.getsize(file_path) < min_size_kb * 1024:
        return False
    return True

def log_ffmpeg_tail(n=25):
    """Print N baris terakhir ffmpeg_log.txt untuk debug."""
    try:
        with open(FFMPEG_LOG, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        log(f"  -> {n} baris terakhir {FFMPEG_LOG}:")
        for line in lines[-n:]:
            print(f"     {line.rstrip()}", flush=True)
    except:
        log(f"  -> Tidak bisa baca {FFMPEG_LOG}")

# ════════════════════════════════════════════════════════════
# IMAGE HELPERS
# ════════════════════════════════════════════════════════════

def crop_center_resize(img, W, H):
    """Crop tengah gambar lalu resize ke W×H tanpa distorsi."""
    from PIL import Image
    ratio_src = img.width / img.height
    ratio_tgt = W / H
    if ratio_src > ratio_tgt:
        new_w = int(img.height * ratio_tgt)
        left  = (img.width - new_w) // 2
        img   = img.crop((left, 0, left + new_w, img.height))
    else:
        new_h = int(img.width / ratio_tgt)
        top   = (img.height - new_h) // 2
        img   = img.crop((0, top, img.width, top + new_h))
    return img.resize((W, H), Image.LANCZOS)

def draw_rounded_rect(draw, x1, y1, x2, y2, radius,
                       fill=None, outline=None, width=2):
    """Gambar rectangle sudut rounded, support fill & outline."""
    try:
        if fill:
            draw.rounded_rectangle([x1, y1, x2, y2],
                                    radius=radius, fill=fill)
        if outline:
            draw.rounded_rectangle([x1, y1, x2, y2],
                                    radius=radius,
                                    outline=outline, width=width)
    except:
        # Fallback Pillow lama
        if fill:
            draw.rectangle([x1, y1, x2, y2], fill=fill)
        if outline:
            draw.rectangle([x1, y1, x2, y2],
                            outline=outline, width=width)

def draw_text_stroke(draw, x, y, text, font, color,
                     stroke=2, stroke_col=(0, 0, 0)):
    """Gambar teks dengan stroke + shadow."""
    # Shadow
    draw.text((x + 3, y + 3), text, font=font, fill=(0, 0, 0))
    # Stroke
    if stroke > 0:
        for dx in range(-stroke, stroke + 1):
            for dy in range(-stroke, stroke + 1):
                if dx or dy:
                    draw.text((x + dx, y + dy), text,
                               font=font, fill=stroke_col)
    # Teks utama
    draw.text((x, y), text, font=font, fill=color)
