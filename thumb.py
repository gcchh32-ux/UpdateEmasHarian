# thumb.py
import os, re, random
from datetime import datetime
from config import (CHANNEL_ID, NAMA_CHANNEL, SKEMA_AKTIF)
from utils  import (log, font_path, get_font, wrap_text,
                    draw_rounded_rect, draw_text_stroke,
                    crop_center_resize)

W, H = 1280, 720

def _list_gambar():
    import glob
    return sorted(
        glob.glob("gambar_bank/*.jpg")  +
        glob.glob("gambar_bank/*.jpeg") +
        glob.glob("gambar_bank/*.png")
    )

def buat_thumbnail(info, judul, output_path="thumbnail.jpg"):
    log("[+] Membuat thumbnail...")
    TEMPLATE_MAP = {
        1: _tmpl_ch1,
        2: _tmpl_ch2,
        3: _tmpl_ch3,
        4: _tmpl_ch4,
        5: _tmpl_ch5,
    }
    fn = TEMPLATE_MAP.get(CHANNEL_ID, _tmpl_ch1)
    return fn(info, judul, output_path)

# ════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════

def _sk(info):
    return SKEMA_AKTIF.get(
        info["status"], SKEMA_AKTIF.get("Stabil")
    )

def _fp():
    return font_path()

def _rp(x):
    return f"Rp {x:,}".replace(",", ".")

def _bersih(judul):
    return re.sub(
        r'[▲▼⬛🔥💥🚨🎯💰📊📈📉⚡😲🤔💡🛒🔴🟢⚠️📅💛*_`#]',
        '', judul
    ).strip()

def _foto_bg(brightness=0.85, blur=2):
    from PIL import Image, ImageFilter, ImageEnhance
    gb = _list_gambar()
    if not gb:
        return _solid_bg((30, 20, 5))
    try:
        img = Image.open(random.choice(gb)).convert("RGB")
        img = crop_center_resize(img, W, H)
        if blur > 0:
            img = img.filter(ImageFilter.GaussianBlur(blur))
        img = ImageEnhance.Brightness(img).enhance(brightness)
        img = ImageEnhance.Contrast(img).enhance(1.2)
        img = ImageEnhance.Color(img).enhance(1.3)
        return img
    except:
        return _solid_bg((30, 20, 5))

def _solid_bg(color=(20, 15, 5)):
    from PIL import Image
    return Image.new("RGB", (W, H), color)

def _overlay_warna(img, color, alpha):
    from PIL import Image
    ov  = Image.new("RGBA", (W, H),
                    (color[0], color[1], color[2], alpha))
    out = Image.alpha_composite(img.convert("RGBA"), ov)
    return out.convert("RGB")

def _overlay_gradient(img, color, dari="kiri",
                       alpha_maks=200, alpha_min=20):
    from PIL import Image, ImageDraw
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    r, g, b = color
    for i in range(W):
        if dari == "kiri":
            a = int(alpha_maks - (alpha_maks - alpha_min) * (i / W))
        elif dari == "kanan":
            a = int(alpha_min + (alpha_maks - alpha_min) * (i / W))
        elif dari == "bawah":
            a = int(alpha_min + (alpha_maks - alpha_min) * (i / H))
        elif dari == "atas":
            a = int(alpha_maks - (alpha_maks - alpha_min) * (i / H))
        else:
            a = int(alpha_maks - (alpha_maks - alpha_min) * (i / W))
        od.line([(i, 0), (i, H)], fill=(r, g, b, a))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")

def _overlay_gradient_vertikal(img, color, dari="bawah",
                                alpha_maks=220, alpha_min=0):
    from PIL import Image, ImageDraw
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    r, g, b = color
    for i in range(H):
        if dari == "bawah":
            a = int(alpha_min + (alpha_maks - alpha_min) * (i / H))
        else:
            a = int(alpha_maks - (alpha_maks - alpha_min) * (i / H))
        od.line([(0, i), (W, i)], fill=(r, g, b, a))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


# ════════════════════════════════════════════════════════════
# TEMPLATE 1 — Channel 1: Sobat Antam
# Warna muda: Kuning Hangat & Oranye Pastel
# Letak teks: KIRI BAWAH
# Gaya: Bold, besar, stroke tebal — keliatan dari jauh
# ════════════════════════════════════════════════════════════

def _tmpl_ch1(info, judul, output_path):
    from PIL import Image, ImageDraw
    fp = _fp()

    img  = _foto_bg(brightness=0.95, blur=1)
    # Gradient dari bawah ke atas — area teks bawah gelap
    img  = _overlay_gradient_vertikal(
        img, (20, 10, 0), dari="bawah",
        alpha_maks=210, alpha_min=10
    )
    # Sisi kiri sedikit redup
    img  = _overlay_gradient(
        img, (10, 5, 0), dari="kiri",
        alpha_maks=120, alpha_min=0
    )
    draw = ImageDraw.Draw(img)

    st   = info["status"]
    harga = f"{info['harga_sekarang']:,}".replace(",", ".")

    # ── Badge status (kiri atas, bulat) ──
    if st == "Naik":
        bg_badge = (255, 220, 100)   # kuning pastel
        tc_badge = (80, 50, 0)
        icon     = "▲ NAIK"
    elif st == "Turun":
        bg_badge = (255, 180, 120)   # oranye muda
        tc_badge = (80, 30, 0)
        icon     = "▼ TURUN"
    else:
        bg_badge = (220, 240, 180)   # hijau muda
        tc_badge = (40, 60, 10)
        icon     = "= STABIL"

    bw = len(icon) * 20 + 50
    draw_rounded_rect(draw, 30, 24, 30 + bw, 78, 24,
                      fill=bg_badge)
    draw.text((48, 32), icon,
              font=get_font(fp, 32), fill=tc_badge)

    # ── Nama channel kanan atas — kuning muda + stroke ──
    draw_text_stroke(draw, W - 30, 28,
                     NAMA_CHANNEL,
                     get_font(fp, 26),
                     (255, 235, 130),
                     stroke=3,
                     stroke_fill=(80, 40, 0),
                     anchor="rt")

    # ── Harga besar di bawah ──
    draw_text_stroke(draw, 34, H - 230, "Harga per gram",
                     get_font(fp, 30),
                     (255, 230, 160),
                     stroke=2, stroke_fill=(0, 0, 0))
    draw_text_stroke(draw, 30, H - 196,
                     f"Rp {harga}",
                     get_font(fp, 100),
                     (255, 240, 100),
                     stroke=6, stroke_fill=(80, 40, 0))

    # ── Selisih ──
    sel = _rp(info["selisih"])
    ar  = "▲ naik" if st == "Naik" else \
          ("▼ turun" if st == "Turun" else "= stabil")
    draw_text_stroke(draw, 34, H - 88,
                     f"{ar}  {sel}",
                     get_font(fp, 36),
                     (255, 210, 120),
                     stroke=3, stroke_fill=(0, 0, 0))

    # ── Tanggal pojok kanan bawah ──
    tgl = datetime.now().strftime("%d %B %Y")
    draw_text_stroke(draw, W - 30, H - 36,
                     tgl, get_font(fp, 26),
                     (255, 235, 180),
                     stroke=2, stroke_fill=(0, 0, 0),
                     anchor="rb")

    # ── Stripe oranye bawah ──
    draw.rectangle([0, H - 10, W, H], fill=(255, 160, 40))

    img.save(output_path, "JPEG", quality=96)
    log(f"  -> ✅ T1 saved: {output_path}")
    return output_path


# ════════════════════════════════════════════════════════════
# TEMPLATE 2 — Channel 2: Update Emas Harian
# Warna muda: Biru Muda & Biru Langit Pastel
# Letak teks: KANAN BAWAH
# Gaya: Modern clean, panel kanan semi-transparan
# ════════════════════════════════════════════════════════════

def _tmpl_ch2(info, judul, output_path):
    from PIL import Image, ImageDraw
    fp = _fp()

    img  = _foto_bg(brightness=1.0, blur=0)
    # Gradient dari kanan (panel teks kanan)
    img  = _overlay_gradient(
        img, (0, 30, 80), dari="kanan",
        alpha_maks=230, alpha_min=0
    )
    draw = ImageDraw.Draw(img)

    st    = info["status"]
    harga = f"{info['harga_sekarang']:,}".replace(",", ".")
    tgl   = datetime.now().strftime("%d %B %Y")

    # ── Stripe biru atas ──
    draw.rectangle([0, 0, W, 10], fill=(100, 200, 255))

    # ── Badge status kiri atas ──
    if st == "Naik":
        bg_badge = (160, 230, 255)   # biru muda
        tc_badge = (0, 50, 100)
        icon     = "▲ NAIK"
    elif st == "Turun":
        bg_badge = (180, 210, 255)   # biru lavender
        tc_badge = (20, 20, 100)
        icon     = "▼ TURUN"
    else:
        bg_badge = (200, 240, 255)   # biru terang
        tc_badge = (0, 60, 100)
        icon     = "= STABIL"

    bw = len(icon) * 20 + 50
    draw_rounded_rect(draw, 24, 20, 24 + bw, 74, 24,
                      fill=bg_badge)
    draw.text((40, 28), icon,
              font=get_font(fp, 32), fill=tc_badge)

    # ── Nama channel kiri bawah ──
    draw_text_stroke(draw, 30, H - 44,
                     NAMA_CHANNEL,
                     get_font(fp, 28),
                     (160, 230, 255),
                     stroke=3, stroke_fill=(0, 20, 60))

    # ── Label kanan ──
    draw_text_stroke(draw, W - 36, H - 230,
                     "Update Harga Emas",
                     get_font(fp, 28),
                     (180, 225, 255),
                     stroke=2, stroke_fill=(0, 0, 0),
                     anchor="rt")

    # ── Harga kanan bawah ──
    draw_text_stroke(draw, W - 30, H - 196,
                     f"Rp {harga}",
                     get_font(fp, 92),
                     (200, 240, 255),
                     stroke=6, stroke_fill=(0, 30, 80),
                     anchor="rt")
    draw_text_stroke(draw, W - 30, H - 96,
                     "per gram · Antam",
                     get_font(fp, 32),
                     (160, 215, 255),
                     stroke=2, stroke_fill=(0, 0, 0),
                     anchor="rt")

    # ── Tanggal ──
    draw_text_stroke(draw, W - 30, H - 50,
                     tgl, get_font(fp, 26),
                     (180, 230, 255),
                     stroke=2, stroke_fill=(0, 0, 0),
                     anchor="rt")

    # ── Stripe biru bawah ──
    draw.rectangle([0, H - 10, W, H], fill=(100, 200, 255))

    img.save(output_path, "JPEG", quality=96)
    log(f"  -> ✅ T2 saved: {output_path}")
    return output_path


# ════════════════════════════════════════════════════════════
# TEMPLATE 3 — Channel 3: Info Logam Mulia
# Warna muda: Hijau Mint & Hijau Pastel
# Letak teks: TENGAH BAWAH (center)
# Gaya: News bar bawah lebar, teks center
# ════════════════════════════════════════════════════════════

def _tmpl_ch3(info, judul, output_path):
    from PIL import Image, ImageDraw
    fp = _fp()

    img  = _foto_bg(brightness=1.0, blur=1)
    # Gradient bawah gelap untuk news bar
    img  = _overlay_gradient_vertikal(
        img, (0, 25, 15), dari="bawah",
        alpha_maks=230, alpha_min=0
    )
    draw = ImageDraw.Draw(img)

    st    = info["status"]
    harga = f"{info['harga_sekarang']:,}".replace(",", ".")
    tgl   = datetime.now().strftime("%d %B %Y")
    sel   = _rp(info["selisih"])

    # ── Bar hijau muda atas ──
    draw.rectangle([0, 0, W, 12], fill=(140, 255, 180))

    # ── Nama channel pojok kiri atas ──
    draw_text_stroke(draw, 30, 24,
                     NAMA_CHANNEL,
                     get_font(fp, 28),
                     (180, 255, 200),
                     stroke=3, stroke_fill=(0, 40, 20))

    # ── Tanggal pojok kanan atas ──
    draw_text_stroke(draw, W - 30, 24,
                     tgl, get_font(fp, 26),
                     (180, 255, 200),
                     stroke=2, stroke_fill=(0, 0, 0),
                     anchor="rt")

    # ── Harga BESAR CENTER ──
    draw_text_stroke(draw, W // 2, H - 200,
                     f"Rp {harga}",
                     get_font(fp, 110),
                     (200, 255, 210),
                     stroke=7, stroke_fill=(0, 50, 25),
                     anchor="mt")

    draw_text_stroke(draw, W // 2, H - 82,
                     "per gram · Antam",
                     get_font(fp, 34),
                     (160, 240, 180),
                     stroke=3, stroke_fill=(0, 0, 0),
                     anchor="mt")

    # ── Badge status center bawah ──
    if st == "Naik":
        bg_badge = (160, 255, 190)
        tc_badge = (0, 60, 20)
        icon     = f"▲ NAIK  {sel}"
    elif st == "Turun":
        bg_badge = (200, 255, 200)
        tc_badge = (0, 80, 30)
        icon     = f"▼ TURUN  {sel}"
    else:
        bg_badge = (220, 255, 220)
        tc_badge = (20, 80, 20)
        icon     = "= STABIL"

    bw  = len(icon) * 18 + 60
    bx  = W // 2 - bw // 2
    draw_rounded_rect(draw, bx, H - 44, bx + bw, H - 6,
                      18, fill=bg_badge)
    draw.text((bx + 20, H - 40), icon,
              font=get_font(fp, 28), fill=tc_badge)

    # ── Bar hijau muda bawah ──
    draw.rectangle([0, H - 6, W, H], fill=(140, 255, 180))

    img.save(output_path, "JPEG", quality=96)
    log(f"  -> ✅ T3 saved: {output_path}")
    return output_path


# ════════════════════════════════════════════════════════════
# TEMPLATE 4 — Channel 4: Harga Emas Live
# Warna muda: Ungu Muda & Lavender Pastel
# Letak teks: KIRI ATAS
# Gaya: Live broadcast style, badge LIVE merah muda
# ════════════════════════════════════════════════════════════

def _tmpl_ch4(info, judul, output_path):
    from PIL import Image, ImageDraw
    fp = _fp()

    img  = _foto_bg(brightness=0.9, blur=2)
    # Gradient kiri ungu muda
    img  = _overlay_gradient(
        img, (40, 0, 80), dari="kiri",
        alpha_maks=210, alpha_min=10
    )
    draw = ImageDraw.Draw(img)

    st    = info["status"]
    harga = f"{info['harga_sekarang']:,}".replace(",", ".")
    tgl   = datetime.now().strftime("%d %B %Y")
    sel   = _rp(info["selisih"])

    # ── Badge LIVE kiri atas ──
    draw_rounded_rect(draw, 28, 22, 168, 74, 20,
                      fill=(255, 180, 220))   # pink muda
    draw.text((44, 28), "● LIVE",
              font=get_font(fp, 32),
              fill=(120, 0, 60))

    # ── Nama channel kanan atas ──
    draw_text_stroke(draw, W - 30, 28,
                     NAMA_CHANNEL,
                     get_font(fp, 26),
                     (220, 190, 255),
                     stroke=3, stroke_fill=(40, 0, 80),
                     anchor="rt")

    # ── Harga besar kiri ──
    draw_text_stroke(draw, 30, 96,
                     "Harga Emas",
                     get_font(fp, 32),
                     (210, 190, 255),
                     stroke=2, stroke_fill=(0, 0, 0))
    draw_text_stroke(draw, 28, 130,
                     f"Rp {harga}",
                     get_font(fp, 96),
                     (230, 210, 255),
                     stroke=6, stroke_fill=(50, 0, 100))
    draw_text_stroke(draw, 30, 238,
                     "per gram · Antam",
                     get_font(fp, 30),
                     (200, 180, 255),
                     stroke=2, stroke_fill=(0, 0, 0))

    # ── Badge status kiri ──
    if st == "Naik":
        bg_badge = (220, 200, 255)
        tc_badge = (60, 0, 120)
        icon     = f"▲ NAIK  {sel}"
    elif st == "Turun":
        bg_badge = (200, 180, 255)
        tc_badge = (50, 0, 100)
        icon     = f"▼ TURUN  {sel}"
    else:
        bg_badge = (230, 215, 255)
        tc_badge = (60, 20, 100)
        icon     = "= STABIL"

    bw = len(icon) * 18 + 50
    draw_rounded_rect(draw, 28, 286, 28 + bw, 338, 20,
                      fill=bg_badge)
    draw.text((46, 292), icon,
              font=get_font(fp, 30), fill=tc_badge)

    # ── Tanggal bawah kiri ──
    draw_text_stroke(draw, 30, H - 44,
                     tgl, get_font(fp, 26),
                     (210, 190, 255),
                     stroke=2, stroke_fill=(0, 0, 0))

    # ── Border ungu muda ──
    draw.rectangle([0, 0, W, 6], fill=(180, 140, 255))
    draw.rectangle([0, H - 6, W, H], fill=(180, 140, 255))

    img.save(output_path, "JPEG", quality=96)
    log(f"  -> ✅ T4 saved: {output_path}")
    return output_path


# ════════════════════════════════════════════════════════════
# TEMPLATE 5 — Channel 5: Cek Harga Emas
# Warna muda: Kuning Muda & Krem Pastel
# Letak teks: TENGAH ATAS + TENGAH BAWAH (split)
# Gaya: Friendly, card putih transparan di tengah
# ════════════════════════════════════════════════════════════

def _tmpl_ch5(info, judul, output_path):
    from PIL import Image, ImageDraw
    fp = _fp()

    img  = _foto_bg(brightness=0.88, blur=2)
    # Overlay kuning muda ringan
    img  = _overlay_warna(img, (60, 40, 0), 100)
    draw = ImageDraw.Draw(img)

    st    = info["status"]
    harga = f"{info['harga_sekarang']:,}".replace(",", ".")
    tgl   = datetime.now().strftime("%d %B %Y")
    sel   = _rp(info["selisih"])

    # ── Card putih transparan tengah ──
    card = Image.new("RGBA", (W - 100, 300),
                     (255, 250, 220, 190))
    img  = Image.alpha_composite(
        img.convert("RGBA"), card
    )
    # Paste card di tengah vertikal
    card_full = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    card_full.paste(card, (50, H // 2 - 150))
    img = Image.alpha_composite(
        img.convert("RGBA"), card_full
    ).convert("RGB")
    draw = ImageDraw.Draw(img)

    # ── Nama channel tengah atas ──
    draw_text_stroke(draw, W // 2, 24,
                     NAMA_CHANNEL,
                     get_font(fp, 30),
                     (255, 240, 140),
                     stroke=3, stroke_fill=(80, 50, 0),
                     anchor="mt")

    # ── Harga di dalam card (tengah) ──
    draw_text_stroke(draw, W // 2, H // 2 - 130,
                     "Harga Emas Antam Hari Ini",
                     get_font(fp, 28),
                     (100, 60, 0),
                     stroke=1, stroke_fill=(200, 180, 100),
                     anchor="mt")
    draw_text_stroke(draw, W // 2, H // 2 - 96,
                     f"Rp {harga}",
                     get_font(fp, 100),
                     (80, 50, 0),
                     stroke=4, stroke_fill=(255, 220, 80),
                     anchor="mt")
    draw_text_stroke(draw, W // 2, H // 2 + 16,
                     "per gram · Antam",
                     get_font(fp, 30),
                     (120, 80, 10),
                     stroke=2, stroke_fill=(255, 230, 140),
                     anchor="mt")

    # ── Badge status di dalam card ──
    if st == "Naik":
        bg_badge = (200, 255, 180)
        tc_badge = (0, 80, 10)
        icon     = f"▲ NAIK  {sel}"
    elif st == "Turun":
        bg_badge = (255, 220, 160)
        tc_badge = (100, 40, 0)
        icon     = f"▼ TURUN  {sel}"
    else:
        bg_badge = (255, 245, 180)
        tc_badge = (80, 60, 0)
        icon     = "= STABIL"

    bw  = len(icon) * 18 + 60
    bx  = W // 2 - bw // 2
    draw_rounded_rect(draw, bx, H // 2 + 58,
                      bx + bw, H // 2 + 108, 20,
                      fill=bg_badge)
    draw.text((bx + 20, H // 2 + 64), icon,
              font=get_font(fp, 30), fill=tc_badge)

    # ── Tanggal tengah bawah ──
    draw_text_stroke(draw, W // 2, H - 38,
                     tgl, get_font(fp, 28),
                     (255, 235, 130),
                     stroke=3, stroke_fill=(80, 50, 0),
                     anchor="mt")

    # ── Strip kuning atas & bawah ──
    draw.rectangle([0, 0, W, 8], fill=(255, 210, 60))
    draw.rectangle([0, H - 8, W, H], fill=(255, 210, 60))

    img.save(output_path, "JPEG", quality=96)
    log(f"  -> ✅ T5 saved: {output_path}")
    return output_path
