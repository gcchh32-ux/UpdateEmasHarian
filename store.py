# store.py — Kelola bank gambar & video dari Pexels
import os, glob, time, random
import requests
from config import (
    PEXELS_API_KEY,
    KATA_KUNCI_GAMBAR,
    KATA_KUNCI_VIDEO,
    FOLDER_GAMBAR,
    FOLDER_VIDEO_BANK,
    JUMLAH_GAMBAR_MIN,
    JUMLAH_DL_GAMBAR,
    JUMLAH_VIDEO_MIN,
    JUMLAH_DL_VIDEO,
    SIMPAN_VIDEO_MAKS,
    GEMINI_API_KEY,
    CHANNEL_ID,
    NAMA_CHANNEL,
    NARASI_GAYA,
    CFG,
)
from utils import log

# ════════════════════════════════════════════════════════════
# BLACKLIST — keyword gambar tidak relevan
# ════════════════════════════════════════════════════════════

BLACKLIST = [
    "bitcoin", "crypto", "cryptocurrency", "ethereum",
    "blockchain", "coin", "dollar", "forex", "stock",
    "chart", "graph", "silver", "diamond", "jewelry",
    "necklace", "ring", "bracelet", "earring", "watch",
    "money", "cash", "banknote", "wallet", "credit",
    "market", "trading", "exchange", "currency", "piggy",
    "bank building", "office", "business", "laptop",
    "phone", "computer", "person", "people", "hand",
    "finger", "face", "man", "woman", "child",
]

def _is_relevan(alt_text, url=""):
    """True jika gambar/video relevan (tidak ada blacklist keyword)."""
    teks = (alt_text + " " + url).lower()
    return not any(bk in teks for bk in BLACKLIST)


# ════════════════════════════════════════════════════════════
# LIST HELPERS
# ════════════════════════════════════════════════════════════

def list_gambar():
    return sorted(
        glob.glob(f"{FOLDER_GAMBAR}/*.jpg")  +
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
        log(f"[STORAGE] Kurang {kurang} gambar, download dari Pexels...")
        _download_gambar(kurang)
        ada = list_gambar()
        log(f"[STORAGE] Bank gambar sekarang: {len(ada)}")
    return ada


def _download_gambar(jumlah):
    if not PEXELS_API_KEY:
        log("  -> ERROR: PEXELS_API_KEY kosong!")
        return

    headers     = {"Authorization": PEXELS_API_KEY}
    per_keyword = max(6, jumlah // max(len(KATA_KUNCI_GAMBAR), 1))
    total       = 0
    ts          = int(time.time())

    for kw in KATA_KUNCI_GAMBAR:
        try:
            resp = requests.get(
                "https://api.pexels.com/v1/search",
                params={
                    "query":       kw,
                    "per_page":    per_keyword,
                    "orientation": "landscape",
                    "size":        "large",
                },
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            fotos = resp.json().get("photos", [])
            dl    = 0

            for i, foto in enumerate(fotos):

                # ── Filter resolusi rendah ──
                if (foto.get("width",  0) < 1200 or
                        foto.get("height", 0) < 800):
                    log(f"  -> Skip resolusi rendah: "
                        f"{foto.get('width')}x{foto.get('height')}")
                    continue

                # ── Filter tidak relevan ──
                alt = foto.get("alt", "")
                src = foto.get("src", {}).get("large2x", "")
                if not _is_relevan(alt, src):
                    log(f"  -> Skip tidak relevan: {alt[:60]}")
                    continue

                fn = (f"{FOLDER_GAMBAR}/px_{ts}_"
                      f"{kw.replace(' ','_')}_{i}.jpg")
                if os.path.exists(fn):
                    continue

                try:
                    data = requests.get(src, timeout=30).content
                    if len(data) < 50000:   # Skip file terlalu kecil
                        continue
                    with open(fn, "wb") as f:
                        f.write(data)
                    total += 1
                    dl    += 1
                    log(f"  -> ✅ Gambar [{kw}] {i+1}: "
                        f"{len(data)//1024} KB — {alt[:40]}")
                except Exception as e:
                    log(f"  -> Gagal download gambar: {e}")

            log(f"  -> Keyword '{kw}': {dl} foto didownload")

        except Exception as e:
            log(f"  -> Gagal fetch Pexels '{kw}': {e}")

        # Jangan spam API
        time.sleep(0.5)

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
        log(f"[STORAGE] Kurang {kurang} video, download dari Pexels...")
        _download_video(kurang)
        ada = list_video_bank()
        log(f"[STORAGE] Bank video sekarang: {len(ada)}")
    return ada


def _download_video(jumlah):
    if not PEXELS_API_KEY:
        log("  -> ERROR: PEXELS_API_KEY kosong!")
        return

    headers     = {"Authorization": PEXELS_API_KEY}
    per_keyword = max(3, jumlah // max(len(KATA_KUNCI_VIDEO), 1))
    total       = 0
    ts          = int(time.time())

    for kw in KATA_KUNCI_VIDEO:
        try:
            resp = requests.get(
                "https://api.pexels.com/videos/search",
                params={
                    "query":       kw,
                    "per_page":    per_keyword,
                    "orientation": "landscape",
                },
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            videos = resp.json().get("videos", [])
            dl     = 0

            for i, vid in enumerate(videos):

                # ── Filter tidak relevan ──
                alt = vid.get("url", "") + " " + str(vid.get("tags", ""))
                if not _is_relevan(alt):
                    log(f"  -> Skip video tidak relevan: {kw} [{i}]")
                    continue

                # ── Pilih resolusi terbaik >= 720p ──
                files = vid.get("video_files", [])
                best  = None
                for vf in sorted(files,
                                  key=lambda x: x.get("height", 0),
                                  reverse=True):
                    if (vf.get("height", 0) >= 720 and
                            vf.get("file_type") == "video/mp4"):
                        best = vf
                        break
                # Fallback resolusi apapun
                if not best:
                    for vf in files:
                        if vf.get("file_type") == "video/mp4":
                            best = vf
                            break
                if not best:
                    continue

                fn = (f"{FOLDER_VIDEO_BANK}/px_{ts}_"
                      f"{kw.replace(' ','_')}_{i}.mp4")
                if os.path.exists(fn):
                    continue

                try:
                    data    = requests.get(
                        best["link"], timeout=90
                    ).content
                    size_kb = len(data) // 1024
                    if size_kb < 100:   # Skip video terlalu kecil
                        log(f"  -> Skip video terlalu kecil: "
                            f"{size_kb} KB")
                        continue
                    with open(fn, "wb") as f:
                        f.write(data)
                    total += 1
                    dl    += 1
                    log(f"  -> ✅ Video [{kw}] {i+1}: "
                        f"{size_kb} KB "
                        f"({best.get('height')}p)")
                except Exception as e:
                    log(f"  -> Gagal download video: {e}")

            log(f"  -> Keyword '{kw}': {dl} video didownload")

            if total >= jumlah:
                break

        except Exception as e:
            log(f"  -> Gagal fetch Pexels video '{kw}': {e}")

        time.sleep(0.5)

    log(f"  -> Total video baru: {total}")


# ════════════════════════════════════════════════════════════
# RESET BANK — hapus semua, download ulang fresh
# ════════════════════════════════════════════════════════════

def reset_bank_gambar():
    """Hapus semua gambar lama, download ulang dari awal."""
    if os.path.exists(FOLDER_GAMBAR):
        files = list_gambar()
        for f in files:
            try:
                os.remove(f)
            except:
                pass
        log(f"[STORAGE] Reset: {len(files)} gambar lama dihapus")
    os.makedirs(FOLDER_GAMBAR, exist_ok=True)
    _download_gambar(JUMLAH_DL_GAMBAR)

def reset_bank_video():
    """Hapus semua video lama, download ulang dari awal."""
    if os.path.exists(FOLDER_VIDEO_BANK):
        files = list_video_bank()
        for f in files:
            try:
                os.remove(f)
            except:
                pass
        log(f"[STORAGE] Reset: {len(files)} video lama dihapus")
    os.makedirs(FOLDER_VIDEO_BANK, exist_ok=True)
    _download_video(JUMLAH_DL_VIDEO)


# ════════════════════════════════════════════════════════════
# KELOLA VIDEO HASIL LAMA
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
    log(f"  Bank gambar    : {len(list_gambar())} file"
        f" (min: {JUMLAH_GAMBAR_MIN})")
    log(f"  Bank video     : {len(list_video_bank())} file"
        f" (min: {JUMLAH_VIDEO_MIN})")
    log(f"  Video hasil    : "
        f"{len(glob.glob('Video_Emas_*.mp4'))} file")
    log(f"  Thumbnail      : "
        f"{len(glob.glob('thumbnail_*.jpg'))} file")
    log(f"  Upload history : "
        f"{'Ada' if os.path.exists('upload_history.json') else 'Belum ada'}")
    log(f"  GEMINI_API_KEY : "
        f"{'✅ Set' if GEMINI_API_KEY else '❌ KOSONG!'}")
    log(f"  PEXELS_API_KEY : "
        f"{'✅ Set' if PEXELS_API_KEY else '❌ KOSONG!'}")
    log(f"  CHANNEL_ID     : {CHANNEL_ID} ({NAMA_CHANNEL})")
    log(f"  NARASI_GAYA    : {NARASI_GAYA}")
    log(f"  SKEMA_WARNA    : {CFG['skema_warna']}")
    log(f"  KEYWORD GAMBAR : {KATA_KUNCI_GAMBAR}")
    log(f"  KEYWORD VIDEO  : {KATA_KUNCI_VIDEO}")
    log("=====================")
