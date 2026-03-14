# store.py
import os, glob, time, random
import requests
from config import (
    PEXELS_API_KEY,
    PIXABAY_API_KEY,
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

BLACKLIST = [
    "bitcoin", "crypto", "cryptocurrency", "ethereum",
    "blockchain", "coin", "dollar", "forex", "stock",
    "chart", "graph", "silver",
    "money", "cash", "banknote", "wallet", "credit",
    "market", "trading", "exchange", "currency",
    "office", "laptop", "phone", "computer",
    "person", "people", "hand", "face",
    "man", "woman", "child", "piggy",
]

PIXABAY_KEYWORDS = [
    "gold bar", "gold bullion", "gold ingot",
    "gold bar stack", "gold bar close up",
    "pure gold bar", "gold bullion bar",
    "gold ingot shiny", "gold bar investment",
    "stacked gold bars",
]


def _is_relevan(alt_text, url=""):
    teks = (alt_text + " " + url).lower()
    return not any(bk in teks for bk in BLACKLIST)


def list_gambar():
    return sorted(
        glob.glob(f"{FOLDER_GAMBAR}/*.jpg")
        + glob.glob(f"{FOLDER_GAMBAR}/*.jpeg")
        + glob.glob(f"{FOLDER_GAMBAR}/*.png")
    )


def list_video_bank():
    return sorted(glob.glob(f"{FOLDER_VIDEO_BANK}/*.mp4"))


# ════════════════════════════════════════════════════════════
# BANK GAMBAR
# ════════════════════════════════════════════════════════════

def kelola_bank_gambar():
    os.makedirs(FOLDER_GAMBAR, exist_ok=True)

    for f in list_gambar():
        try:
            os.remove(f)
        except Exception:
            pass

    log("[STORAGE] Download 2 gambar baru (keyword berbeda)...")
    _download_gambar_pexels(2)

    ada = list_gambar()

    if len(ada) < 2:
        log(f"[STORAGE] Pexels kurang ({len(ada)}), coba Pixabay...")
        _download_gambar_pixabay(2 - len(ada))
        ada = list_gambar()

    # Kalau masih cuma 1, duplikasi agar render tidak gagal
    if len(ada) == 1:
        import shutil
        dst = ada[0].replace(".jpg", "_dup.jpg").replace(".jpeg", "_dup.jpeg").replace(".png", "_dup.png")
        shutil.copy(ada[0], dst)
        ada = list_gambar()
        log(f"[STORAGE] Hanya 1 gambar tersedia, diduplikasi.")

    log(f"[STORAGE] Bank gambar siap: {len(ada)} gambar")
    return ada


def _download_gambar_pexels(jumlah):
    if not PEXELS_API_KEY:
        log("  -> PEXELS_API_KEY kosong, skip!")
        return

    headers = {"Authorization": PEXELS_API_KEY}

    # Acak SEMUA keyword — coba satu per satu sampai dapat 'jumlah' gambar
    # Ini fix utama: tidak berhenti di 2 keyword saja
    kw_semua = KATA_KUNCI_GAMBAR.copy()
    random.shuffle(kw_semua)

    ts    = int(time.time())
    total = 0

    for kw in kw_semua:
        if total >= jumlah:
            break

        try:
            resp = requests.get(
                "https://api.pexels.com/v1/search",
                params={
                    "query":       kw,
                    "per_page":    15,
                    "orientation": "landscape",
                    "size":        "large",
                },
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            fotos = resp.json().get("photos", [])

            dapat = False
            for i, foto in enumerate(fotos):
                if (foto.get("width",  0) < 1200 or
                        foto.get("height", 0) < 800):
                    continue
                alt = foto.get("alt", "")
                src = foto.get("src", {}).get("large2x", "")
                if not _is_relevan(alt, src):
                    log(f"  -> [Pexels] Skip: {alt[:50]}")
                    continue

                fn = (f"{FOLDER_GAMBAR}/px_{ts}_{total+1}_"
                      f"{kw.replace(' ', '_')[:20]}.jpg")
                if os.path.exists(fn):
                    continue

                try:
                    data = requests.get(src, timeout=30).content
                    if len(data) < 50000:
                        continue
                    with open(fn, "wb") as f:
                        f.write(data)
                    total += 1
                    dapat = True
                    log(f"  -> ✅ [Pexels] [{kw}] "
                        f"{len(data)//1024}KB")
                    break  # 1 gambar per keyword, lanjut keyword berikutnya
                except Exception as e:
                    log(f"  -> [Pexels] Gagal download: {e}")

            if not dapat:
                log(f"  -> [Pexels] '{kw}': tidak ada foto relevan, coba keyword lain...")

        except Exception as e:
            log(f"  -> [Pexels] Error '{kw}': {e}")

        time.sleep(0.5)

    log(f"  -> [Pexels] Total: {total} gambar baru")


def _download_gambar_pixabay(jumlah):
    if not PIXABAY_API_KEY:
        log("  -> PIXABAY_API_KEY kosong, skip!")
        return

    kw_pool  = random.sample(
        PIXABAY_KEYWORDS,
        min(jumlah, len(PIXABAY_KEYWORDS))
    )
    ts    = int(time.time()) + 9999
    total = 0

    for kw in kw_pool:
        if total >= jumlah:
            break
        try:
            resp = requests.get(
                "https://pixabay.com/api/",
                params={
                    "key":         PIXABAY_API_KEY,
                    "q":           kw,
                    "image_type":  "photo",
                    "orientation": "horizontal",
                    "min_width":   1280,
                    "min_height":  720,
                    "per_page":    10,
                    "safesearch":  "true",
                    "order":       "popular",
                },
                timeout=15,
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", [])

            for i, hit in enumerate(hits):
                tags = hit.get("tags", "")
                url  = hit.get("largeImageURL", "")
                if not url:
                    continue
                if not _is_relevan(tags, url):
                    log(f"  -> [Pixabay] Skip: {tags[:40]}")
                    continue

                fn = (f"{FOLDER_GAMBAR}/pbx_{ts}_{total+1}_"
                      f"{kw.replace(' ', '_')[:20]}.jpg")
                if os.path.exists(fn):
                    continue

                try:
                    data = requests.get(url, timeout=30).content
                    if len(data) < 50000:
                        continue
                    with open(fn, "wb") as f:
                        f.write(data)
                    total += 1
                    log(f"  -> ✅ [Pixabay] [{kw}] "
                        f"{len(data)//1024}KB — {tags[:35]}")
                    break
                except Exception as e:
                    log(f"  -> [Pixabay] Gagal: {e}")

        except Exception as e:
            log(f"  -> [Pixabay] Error '{kw}': {e}")
        time.sleep(0.3)

    log(f"  -> [Pixabay] Total: {total} gambar baru")


# ════════════════════════════════════════════════════════════
# BANK VIDEO
# ════════════════════════════════════════════════════════════

def kelola_bank_video():
    os.makedirs(FOLDER_VIDEO_BANK, exist_ok=True)
    ada = list_video_bank()
    log(f"[STORAGE] Bank video: {len(ada)} file")
    if len(ada) < JUMLAH_VIDEO_MIN:
        kurang = JUMLAH_DL_VIDEO - len(ada)
        log(f"[STORAGE] Kurang {kurang} video, download...")
        _download_video(kurang)
        ada = list_video_bank()
    log(f"[STORAGE] Bank video sekarang: {len(ada)}")
    return ada


def _download_video(jumlah):
    if not PEXELS_API_KEY:
        log("  -> PEXELS_API_KEY kosong, skip!")
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

            dl = 0
            for i, vid in enumerate(videos):
                alt = (vid.get("url", "")
                       + str(vid.get("tags", "")))
                if not _is_relevan(alt):
                    log(f"  -> [Video] Skip [{i}]")
                    continue

                files = vid.get("video_files", [])
                best  = None
                for vf in sorted(
                    files,
                    key=lambda x: x.get("height", 0),
                    reverse=True,
                ):
                    if (vf.get("height", 0) >= 720 and
                            vf.get("file_type") == "video/mp4"):
                        best = vf
                        break
                if not best:
                    for vf in files:
                        if vf.get("file_type") == "video/mp4":
                            best = vf
                            break
                if not best:
                    continue

                fn = (f"{FOLDER_VIDEO_BANK}/px_{ts}_"
                      f"{kw.replace(' ', '_')}_{i}.mp4")
                if os.path.exists(fn):
                    continue

                try:
                    data    = requests.get(
                        best["link"], timeout=90
                    ).content
                    size_kb = len(data) // 1024
                    if size_kb < 100:
                        continue
                    with open(fn, "wb") as f:
                        f.write(data)
                    total += 1
                    dl    += 1
                    log(f"  -> ✅ [Video] [{kw}] "
                        f"{i+1}: {size_kb}KB "
                        f"({best.get('height')}p)")
                except Exception as e:
                    log(f"  -> [Video] Gagal: {e}")

            log(f"  -> [Video] '{kw}': {dl} video")
            if total >= jumlah:
                break

        except Exception as e:
            log(f"  -> [Video] Error '{kw}': {e}")
        time.sleep(0.5)

    log(f"  -> [Video] Total: {total} video baru")


# ════════════════════════════════════════════════════════════
# RESET & UTILITY
# ════════════════════════════════════════════════════════════

def reset_bank_gambar():
    if os.path.exists(FOLDER_GAMBAR):
        files = list_gambar()
        for f in files:
            try:
                os.remove(f)
            except Exception:
                pass
        log(f"[STORAGE] Reset: {len(files)} gambar dihapus")
    os.makedirs(FOLDER_GAMBAR, exist_ok=True)
    _download_gambar_pexels(JUMLAH_DL_GAMBAR)
    _download_gambar_pixabay(JUMLAH_DL_GAMBAR)


def reset_bank_video():
    if os.path.exists(FOLDER_VIDEO_BANK):
        files = list_video_bank()
        for f in files:
            try:
                os.remove(f)
            except Exception:
                pass
        log(f"[STORAGE] Reset: {len(files)} video dihapus")
    os.makedirs(FOLDER_VIDEO_BANK, exist_ok=True)
    _download_video(JUMLAH_DL_VIDEO)


def kelola_video_lama():
    videos = sorted(glob.glob("Video_Emas_*.mp4"))
    hapus  = videos[:max(0, len(videos) - SIMPAN_VIDEO_MAKS)]
    for v in hapus:
        try:
            os.remove(v)
            log(f"[STORAGE] Hapus video lama: {v}")
        except Exception:
            pass


def debug_storage():
    log("=== DEBUG STORAGE ===")
    log(f"  Bank gambar  : {len(list_gambar())} "
        f"file (min:{JUMLAH_GAMBAR_MIN})")
    log(f"  Bank video   : {len(list_video_bank())} "
        f"file (min:{JUMLAH_VIDEO_MIN})")
    log(f"  Video hasil  : "
        f"{len(glob.glob('Video_Emas_*.mp4'))} file")
    log(f"  GEMINI_API_KEY : "
        f"{'✅' if GEMINI_API_KEY else '❌ KOSONG!'}")
    log(f"  PEXELS_API_KEY : "
        f"{'✅' if PEXELS_API_KEY else '❌ KOSONG!'}")
    log(f"  PIXABAY_API_KEY: "
        f"{'✅' if PIXABAY_API_KEY else '⚠️ Kosong'}")
    log(f"  CHANNEL_ID   : {CHANNEL_ID} — {NAMA_CHANNEL}")
    log(f"  SAPAAN       : {CFG['sapaan']}")
    log(f"  KEYWORD GAMBAR: {KATA_KUNCI_GAMBAR}")
    log(f"  KEYWORD VIDEO : {KATA_KUNCI_VIDEO}")
    log("=====================")
