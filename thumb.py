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
    """Ambil foto dari bank, tampilkan cerah dengan blur minimal."""
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
    """Tempel warna overlay transparan di atas foto."""
    from PIL import Image
    ov  = Image.new("RGBA", (W, H),
                    (color[0], color[1], color[2], alpha))
    out = Image.alpha_composite(
        img.convert("RGBA"), ov
    )
    return out.convert("RGB")

def _overlay_gradient(img, color, dari="kiri",
                        alpha_maks=200, alpha_min=20):
    """Gradient overlay dari satu sisi agar teks mudah dibaca."""
    from PIL import Image, ImageDraw
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    r, g, b = color
    for i in range(W):
        if dari == "kiri":
            a = int(alpha_maks - (alpha_maks - alpha_min)
                    * (i / W))
        elif dari == "kanan":
            a = int(alpha_min + (alpha_maks - alpha_min)
                    * (i / W))
        elif dari == "bawah":
            a = int(alpha_min + (alpha_maks - alpha_min)
                    * (i / H))
        else:
            a = int(alpha_maks - (alpha_maks - alpha_min)
                    * (i / W))
        od.line([(i, 0), (i, H)], fill=(r, g, b, a))
    return Image.alpha_composite(
        img.convert("RGBA"), ov
    ).convert("RGB")

def _label_status(draw, fp, info, x, y):
    """Badge STATUS berwarna cerah."""
    st    = info["status"]
    sel   = _rp(info["selisih"])
    pct   = f"{info['persen']:.1f}%"
    if st == "Naik":
        bg_c  = (0, 200, 80)
        txt_c = (0, 60, 20)
        icon  = "▲"
        label = f"NAIK {pct}"
    elif st == "Turun":
        bg_c  = (220, 40, 40)
        txt_c = (255, 255, 255)
        icon  = "▼"
        label = f"TURUN {pct}"
    else:
        bg_c  = (255, 190, 0)
        txt_c = (60, 40, 0)
        icon  = "="
        label = "STABIL"
    bw = len(label) * 22 + 60
    draw_rounded_rect(draw, x, y, x+bw, y+54, 27,
                       fill=bg_c)
    draw.text((x+18, y+10),
              f"{icon}  {label}",
              font=get_font(fp, 30), fill=txt_c)

def _harga_box(draw, fp, info, x, y, warna_harga,
                warna_sub=(255, 255, 255)):
    """Kotak harga besar dengan shadow."""
    harga = f"{info['harga_sekarang']:,}".replace(",",".")
    draw_text_stroke(draw, x, y, "Rp",
                      get_font(fp, 44), warna_sub, stroke=3,
                      stroke_fill=(0, 0, 0))
    draw_text_stroke(draw, x, y+44, harga,
                      get_font(fp, 96), warna_harga,
                      stroke=5, stroke_fill=(0, 0, 0))
    draw_text_stroke(draw, x+4, y+148, "per gram · Antam",
                      get_font(fp, 30), warna_sub, stroke=2,
                      stroke_fill=(0, 0, 0))

def _judul_multiline(draw, fp, judul, x, y, w=22,
                      warna=(255, 255, 255), maks=3):
    baris = wrap_text(_bersih(judul), w)
    yy    = y
    for idx, b in enumerate(baris[:maks]):
        sz = 44 if idx == 0 else 34
        draw_text_stroke(draw, x, yy, b,
                          get_font(fp, sz), warna,
                          stroke=3,
                          stroke_fill=(0, 0, 0))
        yy += sz + 10

def _watermark(draw, fp, x=None, y=None,
                warna=(255, 255, 255, 180)):
    if x is None: x = 30
    if y is None: y = H - 50
    draw_text_stroke(draw, x, y, NAMA_CHANNEL,
                      get_font(fp, 26),
                      (255, 255, 255), stroke=2,
                      stroke_fill=(0, 0, 0))
    draw.text((x, y + 28),
              datetime.now().strftime("%d %B %Y"),
              font=get_font(fp, 20),
              fill=(220, 220, 220))

def _historis_panel(draw, fp, info, x, y, warna_judul,
                     warna_val=(255, 255, 255)):
    """Panel historis dengan background gelap transparan."""
    from PIL import Image, ImageDraw as ID
    historis = info.get("historis", {})
    lbl_map  = [
        ("kemarin","Kemarin"),
        ("7_hari","7 Hari"),
        ("1_bulan","1 Bulan"),
        ("3_bulan","3 Bulan"),
        ("6_bulan","6 Bulan"),
        ("1_tahun","1 Tahun"),
    ]
    draw_text_stroke(draw, x, y, "PERUBAHAN HARGA",
                      get_font(fp, 24), warna_judul,
                      stroke=2, stroke_fill=(0,0,0))
    yi = y + 36
    for lb, nama in lbl_map:
        d = historis.get(lb)
        if not d:
            continue
        wc  = (80, 255, 120)  if d["naik"]        else \
              (255, 100, 100) if not d["stabil"]   else \
              (255, 220, 80)
        ar  = "▲" if d["naik"] else \
              ("▼" if not d["stabil"] else "→")
        draw_text_stroke(draw, x, yi, nama+":",
                          get_font(fp, 22),
                          (230, 230, 230), stroke=1,
                          stroke_fill=(0,0,0))
        draw_text_stroke(draw, x+150, yi,
                          f"{ar} {abs(d['persen']):.1f}%",
                          get_font(fp, 24), wc,
                          stroke=2, stroke_fill=(0,0,0))
        yi += 40
        if yi > H - 60:
            break


# ════════════════════════════════════════════════════════════
# TEMPLATE 1 — Merah-Emas Cerah | Channel 1: Sobat Antam
# Foto full + gradient kiri gelap + harga kuning besar
# ════════════════════════════════════════════════════════════

def _tmpl_ch1(info, judul, output_path):
    from PIL import Image, ImageDraw
    fp  = _fp()
    sk  = _sk(info)

    # Foto cerah blur ringan
    img = _foto_bg(brightness=0.9, blur=1)
    # Gradient kiri hitam agar teks terbaca
    img = _overlay_gradient(img, (0,0,0),
                             dari="kiri",
                             alpha_maks=210, alpha_min=10)
    draw = ImageDraw.Draw(img)

    # Aksen bar merah kiri
    for i in range(18):
        draw.line([(i,0),(i,H)],
                  fill=(220, 30, 30))

    # Badge status
    _label_status(draw, fp, info, 26, 24)

    # Harga
    _harga_box(draw, fp, info, 26, 90,
               warna_harga=(255, 215, 0),
               warna_sub=(255, 240, 200))

    # Judul
    _judul_multiline(draw, fp, judul, 26, 300,
                     w=24, warna=(255, 255, 255))

    # Historis kanan
    _historis_panel(draw, fp, info,
                    x=W//2+80, y=24,
                    warna_judul=(255, 215, 0))

    # Garis bawah emas
    draw.rectangle([0, H-8, W, H],
                   fill=(255, 180, 0))

    _watermark(draw, fp)
    img.save(output_path, "JPEG", quality=96)
    log(f"  -> ✅ T1 saved: {output_path}")
    return output_path


# ════════════════════════════════════════════════════════════
# TEMPLATE 2 — Biru Terang | Channel 2: Update Emas Harian
# Split 50/50: foto kanan, panel biru kiri
# ════════════════════════════════════════════════════════════

def _tmpl_ch2(info, judul, output_path):
    from PIL import Image, ImageDraw
    fp   = _fp()
    sk   = _sk(info)

    # Base foto cerah
    foto = _foto_bg(brightness=1.0, blur=0)
    img  = Image.new("RGB", (W, H), (10, 30, 80))

    # Foto di sisi kanan (60%)
    foto_w = int(W * 0.6)
    foto_r = foto.crop((0, 0, foto_w, H))
    img.paste(foto_r, (W - foto_w, 0))

    # Gradient biru dari kiri menutupi foto
    ov = Image.new("RGBA", (W, H), (0,0,0,0))
    od = ImageDraw.Draw(ov)
    for x in range(W):
        a = max(0, min(255, int(255 - (x/(W*0.55))*255)))
        od.line([(x,0),(x,H)], fill=(10,40,120,a))
    img = Image.alpha_composite(
        img.convert("RGBA"), ov
    ).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Garis terang atas
    draw.rectangle([0, 0, W, 8], fill=(0, 180, 255))

    # Badge status
    _label_status(draw, fp, info, 30, 20)

    # Label channel
    draw_text_stroke(draw, 30, 82, NAMA_CHANNEL.upper(),
                      get_font(fp, 22),
                      (0, 200, 255), stroke=1,
                      stroke_fill=(0,20,60))

    # Harga
    _harga_box(draw, fp, info, 30, 112,
               warna_harga=(0, 230, 255),
               warna_sub=(200, 240, 255))

    # Judul
    _judul_multiline(draw, fp, judul, 30, 310,
                     w=22, warna=(255, 255, 255))

    # Garis bawah biru
    draw.rectangle([0, H-8, W, H], fill=(0,150,255))

    _watermark(draw, fp)
    img.save(output_path, "JPEG", quality=96)
    log(f"  -> ✅ T2 saved: {output_path}")
    return output_path


# ════════════════════════════════════════════════════════════
# TEMPLATE 3 — Hijau Segar | Channel 3: Info Logam Mulia
# Foto blur + overlay hijau gelap + historis kanan
# ════════════════════════════════════════════════════════════

def _tmpl_ch3(info, judul, output_path):
    from PIL import Image, ImageDraw
    fp  = _fp()

    img  = _foto_bg(brightness=0.85, blur=3)
    img  = _overlay_warna(img, (0, 40, 20), 160)
    img  = _overlay_gradient(img, (0, 20, 10),
                              dari="kiri",
                              alpha_maks=180, alpha_min=0)
    draw = ImageDraw.Draw(img)

    # Bar hijau atas & bawah
    draw.rectangle([0, 0,  W, 10], fill=(0, 220, 100))
    draw.rectangle([0, H-10, W, H], fill=(0, 220, 100))

    # Badge status
    _label_status(draw, fp, info, 30, 20)

    # Harga
    _harga_box(draw, fp, info, 30, 90,
               warna_harga=(100, 255, 160),
               warna_sub=(200, 255, 220))

    # Judul
    _judul_multiline(draw, fp, judul, 30, 300,
                     w=24, warna=(240, 255, 240))

    # Historis kanan
    _historis_panel(draw, fp, info,
                    x=W//2+90, y=20,
                    warna_judul=(100, 255, 160))

    _watermark(draw, fp)
    img.save(output_path, "JPEG", quality=96)
    log(f"  -> ✅ T3 saved: {output_path}")
    return output_path


# ════════════════════════════════════════════════════════════
# TEMPLATE 4 — Neon Ungu | Channel 4: Harga Emas Live
# Foto vivid + efek neon + badge LIVE merah
# ════════════════════════════════════════════════════════════

def _tmpl_ch4(info, judul, output_path):
    from PIL import Image, ImageDraw, ImageFilter
    fp  = _fp()

    # Foto vivid
    img  = _foto_bg(brightness=0.8, blur=2)
    img  = _overlay_warna(img, (30, 0, 60), 140)
    img  = _overlay_gradient(img, (20, 0, 50),
                              dari="kiri",
                              alpha_maks=200, alpha_min=10)
    draw = ImageDraw.Draw(img)

    # Neon border
    for i in range(5):
        col = (180, 0, 255) if i % 2 == 0 else (255, 80, 255)
        draw.rectangle([i, i, W-1-i, H-1-i],
                        outline=col, width=1)

    # Badge LIVE
    draw_rounded_rect(draw, W-130, 20, W-20, 72,
                       12, fill=(200, 0, 0))
    draw.text((W-116, 28), "● LIVE",
              font=get_font(fp, 30),
              fill=(255, 255, 255))

    # Badge status
    _label_status(draw, fp, info, 28, 20)

    # Harga dengan glow
    harga = f"{info['harga_sekarang']:,}".replace(",",".")
    for off in [(0,4),(0,-4),(4,0),(-4,0)]:
        draw.text((28+off[0], 96+off[1]),
                  "Rp " + harga,
                  font=get_font(fp, 88),
                  fill=(200, 0, 255, 60))
    draw_text_stroke(draw, 28, 52, "Rp",
                      get_font(fp, 40),
                      (220, 180, 255), stroke=2,
                      stroke_fill=(0,0,0))
    draw_text_stroke(draw, 28, 96, harga,
                      get_font(fp, 88),
                      (255, 220, 255), stroke=4,
                      stroke_fill=(80, 0, 120))
    draw_text_stroke(draw, 30, 196, "per gram · Antam",
                      get_font(fp, 28),
                      (220, 180, 255), stroke=2,
                      stroke_fill=(0,0,0))

    # Badge selisih
    sel  = info["selisih"]
    st   = info["status"]
    if sel > 0:
        sc   = (80,255,120) if st=="Naik" else (255,80,80)
        ar   = "▲" if st=="Naik" else "▼"
        draw_rounded_rect(draw, 28, 240, 340, 290,
                           20, fill=(0,0,0,180))
        draw_text_stroke(draw, 46, 246,
                          f"{ar} {_rp(sel)}",
                          get_font(fp, 30), sc,
                          stroke=2, stroke_fill=(0,0,0))

    # Judul
    _judul_multiline(draw, fp, judul, 28, 316,
                     w=24, warna=(255, 230, 255))

    # Historis kanan
    _historis_panel(draw, fp, info,
                    x=W//2+70, y=20,
                    warna_judul=(220, 100, 255))

    _watermark(draw, fp)
    img.save(output_path, "JPEG", quality=96)
    log(f"  -> ✅ T4 saved: {output_path}")
    return output_path


# ════════════════════════════════════════════════════════════
# TEMPLATE 5 — Oranye Hangat | Channel 5: Cek Harga Emas
# Foto full cerah + card oranye + teks putih besar
# ════════════════════════════════════════════════════════════

def _tmpl_ch5(info, judul, output_path):
    from PIL import Image, ImageDraw
    fp  = _fp()

    # Foto sangat cerah
    img  = _foto_bg(brightness=1.0, blur=0)
    img  = _overlay_gradient(img, (80, 30, 0),
                              dari="kiri",
                              alpha_maks=220, alpha_min=20)
    draw = ImageDraw.Draw(img)

    # Card oranye semi-transparan kiri
    card = Image.new("RGBA", (W//2+60, H),
                     (200, 80, 0, 180))
    img  = Image.alpha_composite(
        img.convert("RGBA"), card
    ).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Stripe atas & bawah
    draw.rectangle([0, 0, W, 12], fill=(255, 140, 0))
    draw.rectangle([0, H-12, W, H], fill=(255, 140, 0))

    # Badge status
    _label_status(draw, fp, info, 28, 18)

    # Label
    draw_text_stroke(draw, 28, 80,
                      NAMA_CHANNEL.upper(),
                      get_font(fp, 22),
                      (255, 220, 100), stroke=2,
                      stroke_fill=(80,30,0))

    # Harga
    _harga_box(draw, fp, info, 28, 106,
               warna_harga=(255, 240, 100),
               warna_sub=(255, 220, 180))

    # Garis pemisah
    draw.line([(28, 310), (W//2+40, 310)],
              fill=(255, 200, 80), width=3)

    # Judul
    _judul_multiline(draw, fp, judul, 28, 322,
                     w=22, warna=(255, 255, 255))

    # Historis kanan (area foto)
    _historis_panel(draw, fp, info,
                    x=W//2+80, y=20,
                    warna_judul=(255, 200, 80))

    # Tanggal pojok kanan bawah
    tgl = datetime.now().strftime("%d %B %Y")
    draw_text_stroke(draw, W-260, H-48, tgl,
                      get_font(fp, 24),
                      (255, 220, 100), stroke=2,
                      stroke_fill=(0,0,0))

    _watermark(draw, fp, x=28)
    img.save(output_path, "JPEG", quality=96)
    log(f"  -> ✅ T5 saved: {output_path}")
    return output_path
