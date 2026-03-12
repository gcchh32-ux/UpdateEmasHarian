# uploader.py — Upload video ke YouTube via YouTube Data API v3
import os, json, time
from datetime import datetime
from config import YOUTUBE_CATEGORY, NAMA_CHANNEL
from utils  import log

# ════════════════════════════════════════════════════════════
# LOAD CREDENTIALS
# ════════════════════════════════════════════════════════════

def _load_credentials():
    """Load OAuth2 credentials dari environment / file."""
    # Priority 1: GitHub Secrets via env
    token_json = os.environ.get("YOUTUBE_TOKEN_JSON", "")
    if token_json:
        try:
            return json.loads(token_json)
        except Exception as e:
            log(f"  -> Gagal parse YOUTUBE_TOKEN_JSON: {e}")

    # Priority 2: File lokal (dev mode)
    for fname in ["token.json", "credentials_token.json"]:
        if os.path.exists(fname):
            try:
                with open(fname, encoding="utf-8") as f:
                    log(f"  -> Load credentials dari file: {fname}")
                    return json.load(f)
            except Exception as e:
                log(f"  -> Gagal baca {fname}: {e}")
    return None

def _load_client_secret():
    """Load client_secret untuk refresh token."""
    secret_json = os.environ.get("YOUTUBE_CLIENT_SECRET_JSON", "")
    if secret_json:
        try:
            return json.loads(secret_json)
        except:
            pass
    if os.path.exists("client_secret.json"):
        try:
            with open("client_secret.json", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return None

# ════════════════════════════════════════════════════════════
# REFRESH ACCESS TOKEN
# ════════════════════════════════════════════════════════════

def _refresh_token(creds):
    """Refresh access token jika sudah expired."""
    import requests
    secret = _load_client_secret()
    if not secret:
        log("  -> ERROR: client_secret tidak tersedia untuk refresh!")
        return creds

    # Support format installed / web
    client_info = (secret.get("installed") or
                   secret.get("web") or {})
    client_id     = client_info.get("client_id", "")
    client_secret = client_info.get("client_secret", "")
    refresh_token = creds.get("refresh_token", "")

    if not all([client_id, client_secret, refresh_token]):
        log("  -> ERROR: Data refresh token tidak lengkap!")
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
            creds["expires_in"]   = data.get("expires_in", 3600)
            log("  -> ✅ Token berhasil di-refresh!")
        else:
            log(f"  -> Refresh gagal: {data}")
    except Exception as e:
        log(f"  -> Exception refresh token: {e}")
    return creds

# ════════════════════════════════════════════════════════════
# UPLOAD CORE
# ════════════════════════════════════════════════════════════

def _upload_video_core(video_path, judul, deskripsi,
                        tags, access_token):
    """Upload video ke YouTube (resumable upload)."""
    import requests
    UPLOAD_URL = (
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status"
    )
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type":  "application/json; charset=UTF-8",
        "X-Upload-Content-Type": "video/mp4",
    }
    metadata = {
        "snippet": {
            "title":       judul[:100],
            "description": deskripsi[:5000],
            "tags":        tags[:15],
            "categoryId":  YOUTUBE_CATEGORY,
            "defaultLanguage":          "id",
            "defaultAudioLanguage":     "id",
        },
        "status": {
            "privacyStatus":     "public",
            "selfDeclaredMadeForKids": False,
            "madeForKids":             False,
        },
    }

    # Initiate resumable session
    log("  -> Memulai sesi upload...")
    init_resp = requests.post(
        UPLOAD_URL,
        headers=headers,
        json=metadata,
        timeout=30,
    )
    if init_resp.status_code not in (200, 201):
        log(f"  -> ERROR init upload: "
            f"{init_resp.status_code} — {init_resp.text[:300]}")
        return None

    session_uri = init_resp.headers.get("Location")
    if not session_uri:
        log("  -> ERROR: Session URI tidak ditemukan!")
        return None
    log("  -> ✅ Session URI OK, mulai upload file...")

    # Upload file
    file_size = os.path.getsize(video_path)
    log(f"  -> Ukuran file: {file_size//1024//1024} MB")

    CHUNK_SIZE = 8 * 1024 * 1024   # 8 MB per chunk
    uploaded   = 0

    with open(video_path, "rb") as f:
        while uploaded < file_size:
            chunk  = f.read(CHUNK_SIZE)
            end    = uploaded + len(chunk) - 1
            c_hdrs = {
                "Content-Length": str(len(chunk)),
                "Content-Range":
                    f"bytes {uploaded}-{end}/{file_size}",
            }
            try:
                up_resp = requests.put(
                    session_uri,
                    headers=c_hdrs,
                    data=chunk,
                    timeout=120,
                )
            except Exception as e:
                log(f"  -> Chunk upload error: {e}")
                return None

            pct = int((uploaded + len(chunk)) / file_size * 100)
            print(f"  -> Upload: {pct}%", end="\r", flush=True)

            if up_resp.status_code in (200, 201):
                print()
                data     = up_resp.json()
                video_id = data.get("id", "")
                log(f"  -> ✅ Upload selesai! Video ID: {video_id}")
                log(f"  -> URL: https://youtu.be/{video_id}")
                return video_id

            elif up_resp.status_code == 308:
                # Resume Incomplete — lanjut chunk berikutnya
                rng = up_resp.headers.get("Range", "")
                if rng:
                    uploaded = int(rng.split("-")[-1]) + 1
                else:
                    uploaded += len(chunk)

            elif up_resp.status_code in (500, 502, 503, 504):
                log(f"  -> Server error {up_resp.status_code}, "
                    f"retry 10 detik...")
                time.sleep(10)

            else:
                log(f"  -> ERROR upload chunk: "
                    f"{up_resp.status_code} — {up_resp.text[:200]}")
                return None

    log("  -> ERROR: Upload loop selesai tanpa response OK!")
    return None


# ════════════════════════════════════════════════════════════
# SET THUMBNAIL
# ════════════════════════════════════════════════════════════

def _set_thumbnail(video_id, thumbnail_path, access_token):
    """Upload custom thumbnail ke video."""
    import requests
    if not thumbnail_path or not os.path.exists(thumbnail_path):
        log(f"  -> Thumbnail tidak ditemukan: {thumbnail_path}")
        return False

    url = (
        f"https://www.googleapis.com/upload/youtube/v3/thumbnails"
        f"/set?videoId={video_id}&uploadType=media"
    )
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type":  "image/jpeg",
    }
    try:
        with open(thumbnail_path, "rb") as f:
            resp = requests.post(
                url, headers=headers, data=f, timeout=60
            )
        if resp.status_code in (200, 201):
            log(f"  -> ✅ Thumbnail berhasil di-set!")
            return True
        else:
            log(f"  -> Thumbnail gagal: "
                f"{resp.status_code} — {resp.text[:200]}")
            return False
    except Exception as e:
        log(f"  -> Exception set thumbnail: {e}")
        return False


# ════════════════════════════════════════════════════════════
# SIMPAN HISTORY UPLOAD
# ════════════════════════════════════════════════════════════

def _simpan_upload_history(video_id, judul, video_path,
                            thumbnail_path):
    history_file = "upload_history.json"
    try:
        hist = []
        if os.path.exists(history_file):
            with open(history_file, encoding="utf-8") as f:
                hist = json.load(f)
    except:
        hist = []

    hist.insert(0, {
        "tanggal":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "video_id":   video_id,
        "url":        f"https://youtu.be/{video_id}",
        "judul":      judul,
        "file_video": os.path.basename(video_path),
        "thumbnail":  os.path.basename(thumbnail_path)
                      if thumbnail_path else "",
        "channel":    NAMA_CHANNEL,
    })
    hist = hist[:90]   # simpan 90 entry terakhir

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(hist, f, indent=2, ensure_ascii=False)
    log(f"  -> History upload disimpan ({len(hist)} entry)")


# ════════════════════════════════════════════════════════════
# MAIN UPLOAD FUNCTION
# ════════════════════════════════════════════════════════════

def upload_ke_youtube(video_path, judul, deskripsi,
                       tags, thumbnail_path=None):
    log(f"[6/6] Upload ke YouTube — {NAMA_CHANNEL}...")

    # Validasi file video
    if not os.path.exists(video_path):
        log(f"  -> ERROR: File video tidak ditemukan: {video_path}")
        return None
    size_mb = os.path.getsize(video_path) // 1024 // 1024
    if size_mb < 2:
        log(f"  -> ERROR: File video terlalu kecil ({size_mb} MB)!")
        return None

    # Load credentials
    creds = _load_credentials()
    if not creds:
        log("  -> ERROR: Credentials tidak ditemukan!")
        log("  -> Pastikan YOUTUBE_TOKEN_JSON di GitHub Secrets!")
        return None

    # Refresh token jika perlu
    creds        = _refresh_token(creds)
    access_token = creds.get("access_token", "")
    if not access_token:
        log("  -> ERROR: Access token kosong setelah refresh!")
        return None

    log(f"  -> Video : {video_path} ({size_mb} MB)")
    log(f"  -> Judul : {judul[:60]}...")

    # Retry upload maks 3x
    video_id = None
    for attempt in range(1, 4):
        log(f"  -> Upload attempt {attempt}/3...")
        video_id = _upload_video_core(
            video_path, judul, deskripsi, tags, access_token
        )
        if video_id:
            break
        if attempt < 3:
            wait = attempt * 15
            log(f"  -> Gagal, retry {wait} detik...")
            time.sleep(wait)
            # Refresh token lagi sebelum retry
            creds        = _refresh_token(creds)
            access_token = creds.get("access_token", "")

    if not video_id:
        log("  -> ❌ Upload GAGAL setelah 3 attempt!")
        return None

    # Set thumbnail
    if thumbnail_path:
        time.sleep(3)   # Tunggu video diproses dulu
        _set_thumbnail(video_id, thumbnail_path, access_token)

    # Simpan history
    _simpan_upload_history(video_id, judul, video_path,
                            thumbnail_path)

    log(f"  -> ✅ UPLOAD SUKSES: https://youtu.be/{video_id}")
    return video_id
