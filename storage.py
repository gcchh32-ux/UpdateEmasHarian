# storage.py — Kelola bank gambar & video dari Pexels
import os, glob, time, random
import requests
from config  import (PEXELS_API_KEY, KATA_KUNCI_GAMBAR, KATA_KUNCI_VIDEO,
                     FOLDER_GAMBAR, FOLDER_VIDEO_BANK,
                     JUMLAH_GAMBAR_MIN, JUMLAH_DL_GAMBAR,
                     JUMLAH_VIDEO_MIN, JUMLAH_DL_VIDEO,
                     SIMPAN_VIDEO_MAKS, GEMINI_API_KEY,
                     CHANNEL_ID, NAMA_CHANNEL, NARASI_GAYA, CFG)
from utils   import log

# ════════════════════════════════════════════════════════════
# LIST HELPERS
# ════════════════════════════════════════════════════════════

def list_gambar():
    return sorted(
        glob.glob(f"{FOLDER_GAMBAR}/*.jpg") +
        glob.glob(f"{FOLDER_GAMBAR}/*.jpeg") +
        glob.glob(f"{FOLDER_GAMBAR}/*.png")
    )

def list_video_bank():
    return sorted(glob.glob(f"{FOLDER_VIDEO_BANK}/*.mp4"))

# ════════════════════════════════════════════════════════════
# BANK GAMBAR
# ════════════════════════════════════════════════════════════

def kelola_bank_gambar():
    os.makedirs(FOLDER_GAMBAR, exist_ok=True)
    ada = list_gambar()
    log(f"[STORAGE] Bank gambar: {len(ada)} file")
    if len(ada) < JUMLAH_GAMBAR_MIN:
        kurang = JUMLAH_DL_GAMBAR - len(ada)
        log(f"[STORAGE] Download {kurang} gambar dari Pexels...")
        _download_gambar(kurang)
        ada = list_gambar()
        log(f"[STORAGE] Bank gambar sekarang: {len(ada)}")
    return ada

def _download_gambar(jumlah):
    if not PEXELS_API_KEY:
        log("  -> ERROR: PEXELS_API_KEY kosong!")
        return
    headers     = {"Authorization": PEXELS_API_KEY}
    per_keyword = max(6, jumlah // len(KATA_KUNCI_GAMBAR))
    total       = 0
    ts          = int(time.time())

    for kw in KATA_KUNCI_GAMBAR:
        try:
            resp = requests.get(
                f"https://api.pexels.com/v1/search"
                f"?query={kw}&per_page={per_keyword}"
                f"&orientation=landscape&size=large",
                headers=headers, timeout=15
            )
            resp.raise_for_status()
            fotos = resp.json().get("photos", [])
            dl    = 0
            for i, foto in enumerate(fotos):
                # Skip resolusi rendah
                if foto.get("width", 0) < 1200 or foto.get("height", 0) < 800:
                    continue
                fn = (f"{FOLDER_GAMBAR}/px_{ts}_"
                      f"{kw.replace(' ','_')}_{i}.jpg")
                if os.path.exists(fn):
                    continue
                try:
                    data = requests.get(
                        foto["src"]["large2x"], timeout=30
                    ).content
                    with open(fn, "wb") as f:
                        f.write(data)
                    total += 1
                    dl    += 1
                except:
                    pass
            log(f"  -> Gambar '{kw}': {dl} foto didownload")
        except Exception as e:
            log(f"  -> Gagal download gambar '{kw}': {e}")

    log(f"  -> Total gambar baru: {total}")

# ════════════════════════════════════════════════════════════
# BANK VIDEO
# ════════════════════════════════════════════════════════════

def kelola_bank_video():
    os.makedirs(FOLDER_VIDEO_BANK, exist_ok=True)
    ada = list_video_bank()
    log(f"[STORAGE] Bank video: {len(ada)} file")
    if len(ada) < JUMLAH_VIDEO_MIN:
        kurang = JUMLAH_DL_VIDEO - len(ada)
        log(f"[STORAGE] Download {kurang} video dari Pexels...")
        _download_video(kurang)
        ada = list_video_bank()
        log(f"[STORAGE] Bank video sekarang: {len(ada)}")
    return ada

def _download_video(jumlah):
    if not PEXELS_API_KEY:
        log("  -> ERROR: PEXELS_API_KEY kosong!")
        return
    headers     = {"Authorization": PEXELS_API_KEY}
    per_keyword = max(3, jumlah // len(KATA_KUNCI_VIDEO))
    total       = 0
    ts          = int(time.time())

    for kw in KATA_KUNCI_VIDEO:
        try:
            resp = requests.get(
                f"https://api.pexels.com/videos/search"
                f"?query={kw}&per_page={per_keyword}"
                f"&orientation=landscape",
                headers=headers, timeout=15
            )
            resp.raise_for_status()
            videos = resp.json().get("videos", [])
            dl     = 0
            for i, vid in enumerate(videos):
                files = vid.get("video_files", [])
                # Pilih resolusi terbaik >= 720p
                best  = None
                for vf in sorted(files,
                                  key=lambda x: x.get("height", 0),
                                  reverse=True):
                    if (vf.get("height", 0) >= 720 and
                            vf.get("file_type") == "video/mp4"):
                        best = vf
                        break
                if not best and files:
                    best = files[0]
                if not best:
                    continue
                fn = (f"{FOLDER_VIDEO_BANK}/px_{ts}_"
                      f"{kw.replace(' ','_')}_{i}.mp4")
                if os.path.exists(fn):
                    continue
                try:
                    data = requests.get(best["link"], timeout=90).content
                    with open(fn, "wb") as f:
                        f.write(data)
                    size_kb = len(data) // 1024
                    total  += 1
                    dl     += 1
                    log(f"  -> Video '{kw}' [{i+1}] OK ({size_kb} KB)")
                except Exception as e:
                    log(f"  -> Gagal download video: {e}")
            log(f"  -> Video '{kw}': {dl} file")
            if total >= jumlah:
                break
        except Exception as e:
            log(f"  -> Gagal video '{kw}': {e}")

    log(f"  -> Total video baru: {total}")

# ════════════════════════════════════════════════════════════
# KELOLA VIDEO LAMA
# ════════════════════════════════════════════════════════════

def kelola_video_lama():
    videos = sorted(glob.glob("Video_Emas_*.mp4"))
    hapus  = videos[:max(0, len(videos) - SIMPAN_VIDEO_MAKS)]
    for v in hapus:
        try:
            os.remove(v)
            log(f"[STORAGE] Hapus video lama: {v}")
        except:
            pass

# ════════════════════════════════════════════════════════════
# DEBUG
# ════════════════════════════════════════════════════════════

def debug_storage():
    log("=== DEBUG STORAGE ===")
    log(f"  Bank gambar    : {len(list_gambar())} file")
    log(f"  Bank video     : {len(list_video_bank())} file")
    log(f"  Video hasil    : {len(glob.glob('Video_Emas_*.mp4'))} file")
    log(f"  Thumbnail      : {len(glob.glob('thumbnail_*.jpg'))} file")
    log(f"  Upload history : "
        f"{'Ada' if os.path.exists('upload_history.json') else 'Belum ada'}")
    log(f"  GEMINI_API_KEY : {'✅ Set' if GEMINI_API_KEY else '❌ KOSONG!'}")
    log(f"  PEXELS_API_KEY : {'✅ Set' if PEXELS_API_KEY else '❌ KOSONG!'}")
    log(f"  CHANNEL_ID     : {CHANNEL_ID} ({NAMA_CHANNEL})")
    log(f"  NARASI_GAYA    : {NARASI_GAYA}")
    log(f"  SKEMA_WARNA    : {CFG['skema_warna']}")
    log("=====================")
