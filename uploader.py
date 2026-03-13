# uploader.py
import os, json, time
from datetime import datetime
from config import YOUTUBE_CATEGORY, NAMA_CHANNEL
from utils  import log

# ════════════════════════════════════════════════════════════
# LOAD CREDENTIALS
# ════════════════════════════════════════════════════════════

def _load_credentials():
    token_json = os.environ.get("YOUTUBE_TOKEN_JSON", "")
    if token_json:
        try:
            return json.loads(token_json)
        except Exception as e:
            log(f"  -> Gagal parse YOUTUBE_TOKEN_JSON: {e}")

    for fname in ["token.json", "credentials_token.json"]:
        if os.path.exists(fname):
            try:
                with open(fname, encoding="utf-8") as f:
                    log(f"  -> Load credentials: {fname}")
                    return json.load(f)
            except Exception as e:
                log(f"  -> Gagal baca {fname}: {e}")
    return None

def _load_client_secret():
    secret_json = os.environ.get(
        "YOUTUBE_CLIENT_SECRET_JSON", ""
    )
    if secret_json:
        try:
            return json.loads(secret_json)
        except:
            pass
    if os.path.exists("client_secret.json"):
        try:
            with open("client_secret.json",
                      encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return None

# ════════════════════════════════════════════════════════════
# REFRESH TOKEN
# ════════════════════════════════════════════════════════════

def _refresh_token(creds):
    import requests
    secret = _load_client_secret()
    if not secret:
        log("  -> ERROR: client_secret tidak tersedia!")
        return creds

    client_info   = (secret.get("installed") or
                     secret.get("web") or {})
    client_id     = client_info.get("client_id", "")
    client_secret = client_info.get("client_secret", "")
    refresh_token = creds.get("refresh_token", "")

    if not all([client_id, client_secret, refresh_token]):
        log("  -> ERROR: Data refresh tidak lengkap!")
        return creds

    log("  -> Refreshing access token...")
    try:
        resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id":     client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type":    "refresh_token",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if "access_token" in data:
            creds["access_token"] = data["access_token"]
            creds["expires_in"]   = data.get(
                "expires_in", 3600
            )
            log("  -> ✅ Token berhasil di-refresh!")
        else:
            log(f"  -> Refresh gagal: {data}")
    except Exception as e:
        log(f"  -> Exception refresh: {e}")
    return creds

# ════════════════════════════════════════════════════════════
# UPLOAD CORE — Resumable Upload
# ════════════════════════════════════════════════════════════

def _upload_video_core(video_path, judul, deskripsi,
                        tags, access_token):
    import requests
    UPLOAD_URL = (
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status"
    )
    headers = {
        "Authorization":         f"Bearer {access_token}",
        "Content-Type":          "application/json; charset=UTF-8",
        "X-Upload-Content-Type": "video/mp4",
    }
    metadata = {
        "snippet": {
            "title":                 judul[:100],
            "description":           deskripsi[:5000],
            "tags":                  tags[:15],
            "categoryId":            YOUTUBE_CATEGORY,
            "defaultLanguage":       "id",
            "defaultAudioLanguage":  "id",
        },
        "status": {
            "privacyStatus":              "public",
            "selfDeclaredMadeForKids":    False,
            "madeForKids":                False,
        },
    }

    log("  -> Memulai sesi upload...")
    try:
        init_resp = requests.post(
            UPLOAD_URL, headers=headers,
            json=metadata, timeout=30,
        )
    except Exception as e:
        log(f"  -> ERROR init upload: {e}")
        return None

    if init_resp.status_code not in (200, 201):
        log(f"  -> ERROR init: "
            f"{init_resp.status_code} — "
            f"{init_resp.text[:300]}")
        return None

    session_uri = init_resp.headers.get("Location")
    if not session_uri:
        log("  -> ERROR: Session URI tidak ditemukan!")
        return None
    log("  -> ✅ Session URI OK, mulai upload...")

    file_size  = os.path.getsize(video_path)
    CHUNK_SIZE = 8 * 1024 * 1024
    uploaded   = 0
    log(f"  -> Ukuran: {file_size//1024//1024} MB")

    with open(video_path, "rb") as f:
        while uploaded < file_size:
            chunk = f.read(CHUNK_SIZE)
            end   = uploaded + len(chunk) - 1
            c_hdrs = {
                "Content-Length": str(len(chunk)),
                "Content-Range":
                    f"bytes {uploaded}-{end}/{file_size}",
            }
            try:
                up_resp = requests.put(
                    session_uri, headers=c_hdrs,
                    data=chunk, timeout=120,
                )
            except Exception as e:
                log(f"  -> Chunk error: {e}")
                return None

            pct = int(
                (uploaded + len(chunk)) / file_size * 100
            )
            print(f"  -> Upload: {pct}%",
                  end="\r", flush=True)

            if up_resp.status_code in (200, 201):
                print()
                data     = up_resp.json()
                video_id = data.get("id", "")
                log(f"  -> ✅ Upload selesai! "
                    f"ID: {video_id}")
                log(f"  -> URL: "
                    f"https://youtu.be/{video_id}")
                return video_id

            elif up_resp.status_code == 308:
                rng = up_resp.headers.get("Range","")
                if rng:
                    uploaded = int(
                        rng.split("-")[-1]
                    ) + 1
                else:
                    uploaded += len(chunk)

            elif up_resp.status_code in (500,502,503,504):
                log(f"  -> Server error "
                    f"{up_resp.status_code}, retry 10s...")
                time.sleep(10)

            else:
                log(f"  -> ERROR chunk: "
                    f"{up_resp.status_code} — "
                    f"{up_resp.text[:200]}")
                return None

    log("  -> ERROR: Upload loop selesai tanpa OK!")
    return None

# ════════════════════════════════════════════════════════════
# SET THUMBNAIL
# ════════════════════════════════════════════════════════════

def _set_thumbnail(video_id, thumbnail_path, access_token):
    import requests
    if not thumbnail_path or \
            not os.path.exists(thumbnail_path):
        log(f"  -> Thumbnail tidak ada: {thumbnail_path}")
        return False

    url = (
        "https://www.googleapis.com/upload/youtube/v3"
        f"/thumbnails/set?videoId={video_id}"
        "&uploadType=media"
    )
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type":  "image/jpeg",
    }
    try:
        with open(thumbnail_path, "rb") as f:
            resp = requests.post(
                url, headers=headers,
                data=f, timeout=60,
            )
        if resp.status_code in (200, 201):
            log("  -> ✅ Thumbnail berhasil di-set!")
            return True
        else:
            log(f"  -> Thumbnail gagal: "
                f"{resp.status_code} — "
                f"{resp.text[:200]}")
            return False
    except Exception as e:
        log(f"  -> Exception thumbnail: {e}")
        return False

# ════════════════════════════════════════════════════════════
# SIMPAN HISTORY
# ════════════════════════════════════════════════════════════

def _simpan_history(video_id, judul,
                     video_path, thumbnail_path):
    history_file = "upload_history.json"
    try:
        hist = []
        if os.path.exists(history_file):
            with open(history_file,
                      encoding="utf-8") as f:
                hist = json.load(f)
    except:
        hist = []

    hist.insert(0, {
        "tanggal":    datetime.now().strftime(
                          "%Y-%m-%d %H:%M:%S"
                      ),
        "video_id":   video_id,
        "url":        f"https://youtu.be/{video_id}",
        "judul":      judul,
        "file_video": os.path.basename(video_path),
        "thumbnail":  os.path.basename(thumbnail_path)
                      if thumbnail_path else "",
        "channel":    NAMA_CHANNEL,
    })
    hist = hist[:90]

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(hist, f, indent=2, ensure_ascii=False)
    log(f"  -> History disimpan ({len(hist)} entry)")

# ════════════════════════════════════════════════════════════
# BUAT DESKRIPSI
# ════════════════════════════════════════════════════════════

def _buat_deskripsi(info, narasi):
    harga   = f"Rp {info['harga_sekarang']:,}".replace(",",".")
    kemarin = f"Rp {info['harga_kemarin']:,}".replace(",",".")
    selisih = f"Rp {info['selisih']:,}".replace(",",".")
    status  = info["status"]
    tgl     = info["tanggal"]
    waktu   = info["waktu"]

    hist_txt = ""
    lbl_map  = [
        ("kemarin","Kemarin"),
        ("7_hari","7 Hari"),
        ("1_bulan","1 Bulan"),
        ("3_bulan","3 Bulan"),
        ("6_bulan","6 Bulan"),
        ("1_tahun","1 Tahun"),
    ]
    for key, label in lbl_map:
        d = info["historis"].get(key)
        if d:
            ar = "Naik" if d["naik"] else \
                 ("Turun" if not d["stabil"] else "Stabil")
            hist_txt += (
                f"• {label}: {ar} "
                f"{abs(d['persen']):.2f}% "
                f"(Rp {abs(d['selisih']):,})\n"
            ).replace(",",".")

    deskripsi = f"""Update harga emas Antam hari ini, {tgl}.

💰 HARGA EMAS ANTAM HARI INI
• Harga/gram : {harga}
• Kemarin    : {kemarin}
• Perubahan  : {status} {selisih}
• Update     : {waktu}

📊 HISTORIS PERUBAHAN HARGA:
{hist_txt}
📌 TENTANG CHANNEL INI
Channel {NAMA_CHANNEL} hadir setiap hari dengan update harga emas Antam terkini. Dapatkan informasi harga emas batangan, analisis tren, dan tips investasi emas yang bermanfaat.

⚠️ DISCLAIMER
Informasi dalam video ini hanya bersifat edukatif. Selalu lakukan riset mandiri sebelum mengambil keputusan investasi. Harga emas dapat berubah sewaktu-waktu.

🔔 Jangan lupa SUBSCRIBE dan aktifkan notifikasi agar tidak ketinggalan update harga emas setiap hari!

#HargaEmas #EmasAntam #InvestasiEmas #LogamMulia #HargaEmasHariIni #EmasBatangan #{NAMA_CHANNEL.replace(' ','')}"""

    return deskripsi

# ════════════════════════════════════════════════════════════
# MAIN UPLOAD
# ════════════════════════════════════════════════════════════

def upload_ke_youtube(video_path, judul, narasi,
                       tags, info, thumbnail_path=None):
    log(f"[6/6] Upload ke YouTube — {NAMA_CHANNEL}...")

    if not os.path.exists(video_path):
        log(f"  -> ERROR: File tidak ada: {video_path}")
        return None

    size_mb = os.path.getsize(video_path) // 1024 // 1024
    if size_mb < 2:
        log(f"  -> ERROR: File terlalu kecil ({size_mb}MB)!")
        return None

    creds = _load_credentials()
    if not creds:
        log("  -> ERROR: Credentials tidak ditemukan!")
        log("  -> Pastikan YOUTUBE_TOKEN_JSON di Secrets!")
        return None

    creds        = _refresh_token(creds)
    access_token = creds.get("access_token", "")
    if not access_token:
        log("  -> ERROR: Access token kosong!")
        return None

    deskripsi = _buat_deskripsi(info, narasi)

    log(f"  -> Video : {video_path} ({size_mb} MB)")
    log(f"  -> Judul : {judul[:60]}...")

    video_id = None
    for attempt in range(1, 4):
        log(f"  -> Upload attempt {attempt}/3...")
        video_id = _upload_video_core(
            video_path, judul, deskripsi,
            tags, access_token,
        )
        if video_id:
            break
        if attempt < 3:
            wait = attempt * 15
            log(f"  -> Gagal, retry {wait}s...")
            time.sleep(wait)
            creds        = _refresh_token(creds)
            access_token = creds.get("access_token", "")

    if not video_id:
        log("  -> ❌ Upload GAGAL setelah 3 attempt!")
        return None

    if thumbnail_path:
        time.sleep(3)
        _set_thumbnail(video_id, thumbnail_path,
                        access_token)

    _simpan_history(video_id, judul,
                     video_path, thumbnail_path)

    log(f"  -> ✅ SUKSES: https://youtu.be/{video_id}")
    return video_id
