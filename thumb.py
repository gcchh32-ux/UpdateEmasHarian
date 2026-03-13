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
        1: _tmpl_bold_left,
        2: _tmpl_center_split,
        3: _tmpl_dark_minimal,
        4: _tmpl_neon_energy,
        5: _tmpl_warm_card,
    }
    fn = TEMPLATE_MAP.get(CHANNEL_ID, _tmpl_bold_left)
    return fn(info, judul, output_path)

# ════════════════════════════════════════════════════════════
# SHARED HELPERS
# ════════════════════════════════════════════════════════════

def _sk(info):
    return SKEMA_AKTIF.get(
        info["status"], SKEMA_AKTIF.get("Stabil")
    )

def _fp():
    return font_path()

def _rp(x):
    return f"Rp {x:,}".replace(",", ".")

def _judul_bersih(judul):
    return re.sub(
        r'[▲▼⬛🔥💥🚨🎯💰📊📈📉⚡😲🤔💡🛒🔴🟢⚠️📅💛]',
        '', judul
    ).strip()

def _buat_bg_blur(kanan_saja=False, brightness=0.25):
    from PIL import (Image, ImageFilter,
                     ImageEnhance, ImageDraw)
    gb = _list_gambar()
    if gb:
        try:
            bg = Image.open(
                random.choice(gb)
            ).convert("RGB")
            bg = crop_center_resize(bg, W, H)
            bg = bg.filter(ImageFilter.GaussianBlur(10))
            bg = ImageEnhance.Brightness(bg).enhance(
                brightness
            )
            if kanan_saja:
                solid = Image.new("RGB", (W, H), (8, 5, 0))
                mask  = Image.new("L",   (W, H), 0)
                md    = ImageDraw.Draw(mask)
                for x in range(W):
                    a = max(
                        0, int((x - W//2) / (W//2) * 255)
                    )
                    md.line([(x,0),(x,H)], fill=a)
                solid.paste(bg, (0,0), mask)
                return solid
            return bg
        except:
            pass
    return _gradient_fallback()

def _gradient_fallback():
    from PIL import Image, ImageDraw
    img  = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        r = int(30 + (5 - 30) * t)
        g = int(10 + (0 - 10) * t)
        b = 0
        draw.line([(0,y),(W,y)], fill=(r,g,b))
    return img

def _overlay_gelap(img, alpha=220, kiri=True):
    from PIL import Image, ImageDraw
    ov = Image.new("RGBA", (W,H), (0,0,0,0))
    od = ImageDraw.Draw(ov)
    for x in range(W):
        a = int(alpha*(1 - x/W*0.55)) if kiri \
            else int(alpha*0.7)
        od.line([(x,0),(x,H)], fill=(0,0,0,a))
    return Image.alpha_composite(
        img.convert("RGBA"), ov
    ).convert("RGB")

def _badge(draw, x, y, sk):
    fp = _fp()
    bw, bh = 240, 62
    draw_rounded_rect(draw, x, y, x+bw, y+bh, 16,
                       fill=sk["badge"])
    draw_rounded_rect(draw, x, y, x+bw, y+bh, 16,
                       outline=sk["aksen"], width=3)
    draw.text((x+16, y+14), sk["icon"],
              font=get_font(fp,30), fill=(255,255,255))

def _pill_selisih(draw, info, x, y, fp):
    st  = info["status"]
    sel = info["selisih"]
    if sel <= 0:
        return
    sc   = (80,255,120) if st=="Naik" else (255,100,100)
    arah = "▲"          if st=="Naik" else "▼"
    draw_rounded_rect(draw, x, y, x+300, y+50, 24,
                       fill=(sc[0]//5,sc[1]//5,sc[2]//5))
    draw_rounded_rect(draw, x, y, x+300, y+50, 24,
                       outline=sc, width=2)
    draw.text((x+18, y+8), f"{arah} {_rp(sel)}",
              font=get_font(fp,30), fill=sc)

def _judul_draw(draw, judul, fp, sk, x, y, w=24):
    baris = wrap_text(_judul_bersih(judul), w)
    yy    = y
    for idx, b in enumerate(baris[:3]):
        sz  = 42 if idx==0 else 34
        col = sk["hl_teks"] if idx==0 else sk["sub"]
        draw_text_stroke(draw, x, yy, b,
                          get_font(fp,sz), col, stroke=2)
        yy += sz + 8

def _footer(draw, fp, sk, x=28):
    draw.text((x, H-52), NAMA_CHANNEL,
              font=get_font(fp,26), fill=sk["aksen"])
    draw.text((x, H-24),
              datetime.now().strftime("%d %B %Y"),
              font=get_font(fp,20), fill=(160,160,160))

def _historis_list(draw, info, fp, sk, px, py, pw):
    historis = info.get("historis", {})
    lbl_map  = [
        ("kemarin","Kemarin"), ("7_hari","7 Hari"),
        ("1_bulan","1 Bulan"), ("3_bulan","3 Bulan"),
        ("6_bulan","6 Bulan"), ("1_tahun","1 Tahun"),
    ]
    draw.text((px,py), "Perubahan Harga",
              font=get_font(fp,28), fill=sk["aksen"])
    draw.line([(px,py+36),(px+pw,py+36)],
              fill=sk["aksen"], width=2)
    yi = py + 48
    for lb, nama in lbl_map:
        d = historis.get(lb)
        if not d:
            continue
        warna = (80,255,120)  if d["naik"]        else \
                (255,100,100) if not d["stabil"]   else \
                (180,180,180)
        ar    = "▲" if d["naik"] else \
                ("▼" if not d["stabil"] else "→")
        draw.text((px,yi), nama+":",
                  font=get_font(fp,24), fill=(200,200,200))
        draw.text((px+pw-130,yi),
                  f"{ar} {abs(d['persen']):.1f}%",
                  font=get_font(fp,26), fill=warna)
        yi += 44
        if yi > H-60:
            break

# ════════════════════════════════════════════════════════════
# TEMPLATE 1 — Bold Left (Channel 1)
# ════════════════════════════════════════════════════════════

def _tmpl_bold_left(info, judul, output_path):
    from PIL import Image, ImageDraw
    sk  = _sk(info)
    fp  = _fp()
    img = _buat_bg_blur(kanan_saja=True, brightness=0.3)
    img = _overlay_gelap(img, alpha=230, kiri=True)

    panel = Image.new("RGBA", (W,H), (0,0,0,0))
    pd    = ImageDraw.Draw(panel)
    pd.rectangle([0,0,W//2+80,H], fill=(10,5,0,220))
    img   = Image.alpha_composite(
        img.convert("RGBA"), panel
    ).convert("RGB")
    draw  = ImageDraw.Draw(img)

    for x in range(20):
        draw.line([(x,0),(x,H)], fill=sk["aksen"])

    _badge(draw, 28, 28, sk)
    draw.text((28,108), "Rp",
              font=get_font(fp,44), fill=sk["sub"])
    draw_text_stroke(
        draw, 28, 144,
        f"{info['harga_sekarang']:,}".replace(",","."),
        get_font(fp,102), sk["teks"], stroke=4
    )
    draw.text((30,258), "/ gram  ·  Antam",
              font=get_font(fp,26), fill=sk["sub"])
    _pill_selisih(draw, info, 28, 302, fp)
    _judul_draw(draw, judul, fp, sk, 28, 376, w=26)
    _footer(draw, fp, sk)
    _historis_list(draw, info, fp, sk,
                   px=W//2+100, py=30, pw=W//2-130)
    draw.rectangle([0,0,W-1,H-1],
                   outline=sk["aksen"], width=5)
    img.save(output_path, "JPEG", quality=95)
    log(f"  -> ✅ T1: {output_path}")
    return output_path

# ════════════════════════════════════════════════════════════
# TEMPLATE 2 — Center Split (Channel 2)
# ════════════════════════════════════════════════════════════

def _tmpl_center_split(info, judul, output_path):
    from PIL import Image, ImageDraw
    sk  = _sk(info)
    fp  = _fp()
    img = _buat_bg_blur(kanan_saja=False, brightness=0.18)
    r,g,b = sk.get("bg_grad_atas",(0,20,60))
    tint  = Image.new("RGBA",(W,H),(r,g,b,195))
    img   = Image.alpha_composite(
        img.convert("RGBA"), tint
    ).convert("RGB")
    draw  = ImageDraw.Draw(img)

    draw.polygon(
        [(W//2-55,0),(W//2+55,0),
         (W//2-10,H),(W//2-120,H)],
        fill=sk["aksen"]
    )
    draw.text((30,24), NAMA_CHANNEL.upper(),
              font=get_font(fp,22), fill=sk["aksen"])
    draw.line([(30,54),(W//2-80,54)],
              fill=sk["aksen"], width=2)
    _badge(draw, 30, 68, sk)
    draw.text((30,144), "Harga Emas Antam",
              font=get_font(fp,26), fill=(180,210,240))
    draw_text_stroke(draw, 30, 178,
                      _rp(info["harga_sekarang"]),
                      get_font(fp,80), sk["teks"], stroke=3)
    draw.text((30,270), "/ gram  ·  Antam",
              font=get_font(fp,24), fill=sk["sub"])
    _pill_selisih(draw, info, 30, 308, fp)

    baris = wrap_text(_judul_bersih(judul), 28)
    yy = 374
    for idx, b in enumerate(baris[:2]):
        col = (255,255,255) if idx==0 else (180,210,240)
        draw_text_stroke(draw, 30, yy, b,
                          get_font(fp,36 if idx==0 else 30),
                          col, 1)
        yy += 44

    cx = W//2+80
    draw.text((cx,24), "Perubahan Harga",
              font=get_font(fp,26), fill=(200,220,255))
    draw.line([(cx,58),(W-30,58)],
              fill=sk["aksen"], width=2)
    historis = info.get("historis",{})
    lbl_map  = [
        ("kemarin","1H"),("7_hari","7H"),
        ("1_bulan","1B"),("3_bulan","3B"),
        ("6_bulan","6B"),("1_tahun","1T"),
    ]
    pcts    = [abs(historis[lb]["persen"])
               for lb,_ in lbl_map if historis.get(lb)]
    max_pct = max(pcts) if pcts else 1.0
    by      = 68
    for lb, nama in lbl_map:
        d = historis.get(lb)
        if not d: continue
        warna = (80,220,120)  if d["naik"]      else \
                (255,100,100) if not d["stabil"] else \
                (150,150,200)
        bw_   = int(abs(d["persen"])/max_pct
                    *(W-cx-60)*0.75)+16
        ar    = "▲" if d["naik"] else \
                ("▼" if not d["stabil"] else "→")
        draw.text((cx,by+4), nama+":",
                  font=get_font(fp,22), fill=(180,205,240))
        draw_rounded_rect(draw, cx+64, by+2,
                           cx+64+bw_, by+32, 8, fill=warna)
        draw.text((cx+64+bw_+6,by+4),
                  f"{ar}{abs(d['persen']):.1f}%",
                  font=get_font(fp,20), fill=warna)
        by += 46
        if by > H-80: break

    draw.text((cx,H-34),
              datetime.now().strftime("%d %B %Y"),
              font=get_font(fp,22), fill=(140,165,210))
    draw.rectangle([0,0,W-1,H-1],
                   outline=sk["aksen"], width=4)
    img.save(output_path,"JPEG",quality=95)
    log(f"  -> ✅ T2: {output_path}")
    return output_path

# ════════════════════════════════════════════════════════════
# TEMPLATE 3 — Dark Minimal (Channel 3)
# ════════════════════════════════════════════════════════════

def _tmpl_dark_minimal(info, judul, output_path):
    from PIL import (Image, ImageDraw,
                     ImageFilter, ImageEnhance)
    sk  = _sk(info)
    fp  = _fp()
    img = Image.new("RGB",(W,H),(8,12,10))
    draw= ImageDraw.Draw(img)

    for x in range(0,W,80):
        draw.line([(x,0),(x,H)], fill=(20,35,25))
    for y in range(0,H,80):
        draw.line([(0,y),(W,y)], fill=(20,35,25))

    gb = _list_gambar()
    if gb:
        try:
            bg = Image.open(
                random.choice(gb)
            ).convert("RGB")
            bg = bg.resize((500,280), Image.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(6))
            bg = ImageEnhance.Brightness(bg).enhance(0.3)
            mask = Image.new("L",(500,280),0)
            md   = ImageDraw.Draw(mask)
            for x in range(500):
                md.line([(x,0),(x,280)],
                         fill=min(255,int(x*0.5)))
            img.paste(bg,(W-500,H-280),mask)
            draw = ImageDraw.Draw(img)
        except:
            pass

    draw.rectangle([0,0,W,6],   fill=sk["aksen"])
    draw.rectangle([0,H-6,W,H], fill=sk["aksen"])
    draw.text((40,18), NAMA_CHANNEL.upper(),
              font=get_font(fp,22), fill=sk["aksen"])
    draw.text((W-220,18),
              datetime.now().strftime("%d %b %Y"),
              font=get_font(fp,22), fill=(100,145,115))

    _badge(draw, 40, 60, sk)
    draw.text((40,132), "HARGA EMAS ANTAM",
              font=get_font(fp,26), fill=(120,185,135))
    draw_text_stroke(draw, 40, 164,
                      _rp(info["harga_sekarang"]),
                      get_font(fp,90), sk["teks"], stroke=3)
    draw.line([(40,268),(W//2+80,268)],
              fill=sk["aksen"], width=3)

    sel  = info["selisih"]
    st   = info["status"]
    sc   = (80,255,120)  if st=="Naik"  else \
           (255,100,100) if st=="Turun" else (160,160,160)
    ar   = "▲" if st=="Naik" else \
           ("▼" if st=="Turun" else "→")
    if sel > 0:
        draw.text((40,282),
                  f"{ar} {_rp(sel)} dari kemarin",
                  font=get_font(fp,30), fill=sc)

    _judul_draw(draw, judul, fp, sk, 40, 348, w=32)

    cx = W//2+110
    draw.text((cx,60), "PERUBAHAN HARGA",
              font=get_font(fp,22), fill=(100,165,115))
    draw.line([(cx,88),(W-40,88)],
              fill=(60,100,70), width=1)
    historis = info.get("historis",{})
    lbl_map  = [
        ("kemarin","1 Hari"),  ("7_hari","7 Hari"),
        ("1_bulan","1 Bulan"), ("3_bulan","3 Bulan"),
        ("6_bulan","6 Bulan"), ("1_tahun","1 Tahun"),
    ]
    yh = 96
    for lb, nama in lbl_map:
        d = historis.get(lb)
        if not d: continue
        warna = (80,230,110)  if d["naik"]      else \
                (255,110,100) if not d["stabil"] else \
                (140,140,185)
        ar_h  = "▲" if d["naik"] else \
                ("▼" if not d["stabil"] else "→")
        draw.text((cx,yh), nama,
                  font=get_font(fp,24), fill=(140,170,150))
        draw.text((cx+160,yh),
                  f"{ar_h} {abs(d['persen']):.1f}%",
                  font=get_font(fp,24), fill=warna)
        yh += 42
        if yh > H-80: break

    img.save(output_path,"JPEG",quality=95)
    log(f"  -> ✅ T3: {output_path}")
    return output_path

# ════════════════════════════════════════════════════════════
# TEMPLATE 4 — Neon Energy (Channel 4)
# ════════════════════════════════════════════════════════════

def _tmpl_neon_energy(info, judul, output_path):
    from PIL import (Image, ImageDraw,
                     ImageFilter, ImageEnhance)
    sk  = _sk(info)
    fp  = _fp()
    img = Image.new("RGB",(W,H),(5,0,15))

    gb = _list_gambar()
    if gb:
        try:
            bg = Image.open(
                random.choice(gb)
            ).convert("RGB")
            bg = crop_center_resize(bg,W,H)
            bg = bg.filter(ImageFilter.GaussianBlur(14))
            bg = ImageEnhance.Brightness(bg).enhance(0.14)
            img.paste(bg,(0,0))
        except:
            pass

    glow = Image.new("RGBA",(W,H),(0,0,0,0))
    gd   = ImageDraw.Draw(glow)
    rr,gg,bb = sk["aksen"]
    for rs in range(320,0,-20):
        a = int(55*(1-rs/320))
        gd.ellipse(
            [(280-rs,H//2-rs),(280+rs,H//2+rs)],
            fill=(rr,gg,bb,a)
        )
    img  = Image.alpha_composite(
        img.convert("RGBA"), glow
    ).convert("RGB")
    draw = ImageDraw.Draw(img)

    for i in range(4):
        draw.line([(0,2+i),(W,2+i)],
                  fill=(rr,gg,bb,255-i*50))
        draw.line([(0,H-2-i),(W,H-2-i)],
                  fill=(rr,gg,bb,255-i*50))

    _badge(draw, 28, 26, sk)
    draw_rounded_rect(draw,W-115,26,W-28,72,10,
                       fill=(200,0,0))
    draw.text((W-104,32),"LIVE",
              font=get_font(fp,28), fill=(255,255,255))
    draw.ellipse([(W-120,36),(W-102,54)],
                  fill=(255,60,60))

    harga_str = _rp(info["harga_sekarang"])
    for off in [(0,3),(0,-3),(3,0),(-3,0),(2,2),(-2,2)]:
        draw.text((28+off[0],112+off[1]), harga_str,
                  font=get_font(fp,88),
                  fill=(rr,gg,bb,70))
    draw_text_stroke(draw,28,112,harga_str,
                      get_font(fp,88),sk["teks"],stroke=3)
    draw.text((30,210),"/ gram  ·  Antam Logam Mulia",
              font=get_font(fp,26), fill=sk["sub"])
    _pill_selisih(draw, info, 28, 250, fp)
    _judul_draw(draw, judul, fp, sk, 28, 318, w=26)

    historis = info.get("historis",{})
    lbl_map  = [
        ("kemarin","1H"),("7_hari","7H"),
        ("1_bulan","1B"),("3_bulan","3B"),
        ("6_bulan","6B"),("1_tahun","1T"),
    ]
    cx_c = W//2+60
    for lb, nama in lbl_map:
        d = historis.get(lb)
        if not d: continue
        if cx_c+90 > W-8: break
        warna = (80,255,120)  if d["naik"]      else \
                (255,100,100) if not d["stabil"] else \
                (160,160,200)
