# utils.py
import os, subprocess
from config import FFMPEG_LOG, VIDEO_WIDTH, VIDEO_HEIGHT

def log(msg):
    from datetime import datetime
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def rp(x):
    return f"Rp {x:,}".replace(",", ".")

def font_path():
    # Prioritas 1: font lokal di folder assets/ dalam repo
    base = os.path.dirname(os.path.abspath(__file__))
    local_names = [
        "DejaVuSans-Bold.ttf",
        "LiberationSans-Bold.ttf",
        "FreeSansBold.ttf",
        "Ubuntu-B.ttf",
    ]
    for name in local_names:
        local = os.path.join(base, "assets", name)
        if os.path.exists(local):
            return local

    # Prioritas 2: path sistem
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c

    # Prioritas 3: fc-list
    try:
        result = subprocess.run(
            ["fc-list", ":style=Bold", "--format=%{file}\n"],
            capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if line and os.path.exists(line):
                return line
    except Exception:
        pass

    return ""

def escape_ffmpeg_path(path):
    if not path:
        return ""
    return path.replace("\\", "/").replace(":", "\\:")

def get_font(fp, size=32):
    from PIL import ImageFont
    if fp and os.path.exists(fp):
        try:
            return ImageFont.truetype(fp, size)
        except Exception:
            pass
    # FIX: Pillow >= 10.1.0 mendukung parameter size di load_default
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        # Fallback lama (Pillow < 10.1.0): font 10px, tidak ideal
        return ImageFont.load_default()

def wrap_text(text, max_chars=30):
    words = text.split()
    lines = []
    line = ""
    for w in words:
        if len(line) + len(w) + 1 <= max_chars:
            line = (line + " " + w).strip()
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines

def draw_rounded_rect(draw, x1, y1, x2, y2, radius, fill=None, outline=None, width=1):
    if fill:
        draw.rounded_rectangle(
            [x1, y1, x2, y2], radius=radius, fill=fill, outline=outline, width=width
        )
    else:
        draw.rounded_rectangle(
            [x1, y1, x2, y2], radius=radius, outline=outline, width=width
        )

def draw_text_stroke(draw, x, y, text, font, fill, stroke=2, stroke_fill=(0, 0, 0), anchor=None):
    try:
        bbox = font.getbbox(text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    except Exception:
        tw, th = len(text) * 10, 20

    if anchor == "rt":
        x = x - tw
    elif anchor == "rb":
        x = x - tw
        y = y - th
    elif anchor == "mt":
        x = x - tw // 2
    elif anchor == "mb":
        x = x - tw // 2
        y = y - th
    elif anchor in ("lt", None):
        pass

    for dx in range(-stroke, stroke + 1):
        for dy in range(-stroke, stroke + 1):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, font=font, fill=stroke_fill)
    draw.text((x, y), text, font=font, fill=fill)

def crop_center_resize(img, w, h):
    from PIL import Image
    iw, ih = img.size
    ar_target = w / h
    ar_img = iw / ih
    if ar_img > ar_target:
        new_w = int(ih * ar_target)
        left = (iw - new_w) // 2
        img = img.crop((left, 0, left + new_w, ih))
    else:
        new_h = int(iw / ar_target)
        top = (ih - new_h) // 2
        img = img.crop((0, top, iw, top + new_h))
    return img.resize((w, h), Image.LANCZOS)

def ffmpeg_duration(path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except Exception:
        return 0.0

def ffmpeg_is_valid(path, min_size_kb=10):
    if not path or not os.path.exists(path):
        return False
    if os.path.getsize(path) < min_size_kb * 1024:
        return False
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_type",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        capture_output=True, text=True,
    )
    return result.returncode == 0

def log_ffmpeg_tail(n=20):
    if not os.path.exists(FFMPEG_LOG):
        log(" -> ffmpeg_log.txt tidak ditemukan")
        return
    with open(FFMPEG_LOG, encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    log(f" -> === FFMPEG LOG (last {n} lines) ===")
    for line in lines[-n:]:
        log(f"  {line.rstrip()}")
