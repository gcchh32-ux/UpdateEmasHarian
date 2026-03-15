# store.py
import os, glob, time, random, shutil
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

FOLDER_GAMBAR_STATIC = "gambar_static"


def _is_relevan(alt_text, url=""):
    teks = (alt_text + " " + url).lower()
    return not any(bk in teks for bk in BLACKLIST)


def list_gambar():
    return sorted(
        glob.glob(f"{FOLDER_GAMBAR}/*.jpg")
        + glob.glob(f"{FOLDER_GAMBAR}/*.jpeg")
        + glob.glob(f"{FOLDER_GAMBAR}/*.png")
    )


def list_gambar_static():
    return sorted(
        glob.glob(f"{FOLDER_GAMBAR_STATIC}/*.jpg")
        + glob.glob(f"{FOLDER_GAMBAR_STATIC}/*.jpeg")
        + glob.glob(f"{FOLDER_GAMBAR_STATIC}/*.png")
    )


def list_video_bank():
    return sorted(glob.glob(f"{FOLDER_VIDEO_BANK}/*.mp4"))


def _duplikasi_sampai_cukup(target):
    """Duplikasi gambar yang sudah ada sampai mencapai target jumlah."""
    base_list = list_gambar()
    if not base_list:
        return
    idx = 0
    while len(list_gambar()) < target:
        src = base_list[idx % len(base_list)]
        ext = os.path.splitext(src)[1]
        dst = f"{FOLDER_GAMBAR}/dup_{int(time.time())}_{idx}{ext}"
        if not os.path.exists(dst):
            shutil.copy(src, dst)
        idx += 1
        time.sleep(0.01)  # hindari nama file sama persis
    log(f"[STORAGE] Duplikasi selesai: {len(list_gambar())} gambar")


# ════════════════════════════════════════════════════════════
# BANK GAMBAR
# ════════════════════════════════════════════════════════════

def kelola_bank_gambar():
    os.makedirs(FOLDER_GAMBAR, exist_ok=True)
    os.makedirs(FOLDER_GAMBAR_STATIC, exist_ok=True)

    # Hapus semua gambar lama hasil download/salin sebelumnya
    for f in list_gambar():
        try:
            os.remove(f)
        except Exception:
            pass

    # ── PRIORITAS 1: Salin dari gambar_static (repo GitHub) ──
    gambar_static = list_gambar_static()
    if gambar_static:
        random.shuffle(gambar_static)
        # Ambil semua jika < JUMLAH_DL_GAMBAR, atau sejumlah target
        dipilih = gambar_static[:max(JUMLAH_DL_GAMBAR, len(gambar_static))]
        for src in dipilih:
            dst = f"{FOLDER_GAMBAR}/{os.path.basename(src)}"
            try:
                shutil.copy(src, dst)
            except Exception as e:
                log(f"  -> [Static] Gagal salin {src}: {e}")
        log(f"[STORAGE] ✅ Salin {len(list_gambar())} gambar dari {FOLDER_GAMBAR_STATIC}/")
    else:
        # ── PRIORITAS 2: Download dari Pexels ──
        log(f"[STORAGE] {FOLDER_GAMBAR_STATIC}/ kosong, download {JUMLAH_DL_GAMBAR} dari Pexels...")
        _download_gambar_pexels(JUMLAH_DL_GAMBAR)

    ada = list_gambar()

    # ── PRIORITAS 3: Tambah dari Pixabay jika masih kurang ──
    if len(ada) < JUMLAH_GAMBAR_MIN:
        kurang = JUMLAH_DL_GAMBAR - len(ada)
        log(f"[STORAGE] Kurang ({len(ada)}/{JUMLAH_GAMBAR_MIN}), coba Pixabay ({kurang} lagi)...")
        _download_gambar_pixabay(kurang)
        ada = list_gambar()

    # ── PRIORITAS 4: Masih kurang → download Pexels lagi ──
    if len(ada) < JUMLAH_GAMBAR_MIN:
        kurang = JUMLAH_DL_GAMBAR - len(ada)
        log(f"[STORAGE] Masih kurang ({len(ada)}), coba Pexels lagi ({kurang} lagi)...")
        _download_gambar_pexels(kurang)
        ada = list_gambar()

    # ── PRIORITAS 5: Darurat → duplikasi gambar yang ada ──
    if len(ada) < JUMLAH_GAMBAR_MIN and len(ada) > 0:
        log(f"[STORAGE] Darurat: duplikasi gambar yang ada ({len(ada)}) sampai {JUMLAH_GAMBAR_MIN}...")
        _duplikasi_sampai_cukup(JUMLAH_GAMBAR_MIN)
        ada = list_gambar()

    # ── PRIORITAS 6: Benar-benar kosong → download ulang semua ──
    if len(ada) == 0:
        log("[STORAGE] ⚠️ Tidak ada gambar sama sekali! Download ulang semua keyword...")
        _download_gambar_pexels(JUMLAH_DL_GAMBAR)
        _download_gambar_pixabay(JUMLAH_DL_GAMBAR)
        ada = list_gambar()

    log(f"[STORAGE] Bank gambar siap: {len(ada)} gambar")
    return ada


def _download_gambar_pexels(jumlah):
    if not PEXELS_API_KEY:
        log("  -> PEXELS_API_KEY kosong, skip!")
        return

    headers = {"Authorization": PEXELS_API_KEY}

    # Putar keyword sampai cukup memenuhi jumlah
    kw_semua = KATA_KUNCI_GAMBAR.copy()
    random.shuffle(kw_semua)
    kw_pool = []
    while len(kw_pool) < jumlah:
        kw_pool.extend(kw_semua)
    kw_pool = kw_pool[:jumlah * 2]  # cadangan 2x

    ts    = int(time.time())
    total = 0

    for kw in kw_pool:
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
            for foto in fotos:
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
                    break  # 1 gambar per keyword
                except Exception as e:
                    log(f"  -> [Pexels] Gagal download: {e}")

            if not dapat:
                log(f"  -> [Pexels] '{kw}': tidak ada foto relevan")

        except Exception as e:
            log(f"  -> [Pexels] Error '{kw}': {e}")

        time.sleep(0.5)

    log(f"  -> [Pexels] Total: {total} gambar baru")


def _download_gambar_pixabay(jumlah):
    if not PIXABAY_API_KEY:
        log("  -> PIXABAY_API_KEY kosong, skip!")
        return

    kw_pool = []
    while len(kw_pool) < jumlah:
        kw_pool.extend(PIXABAY_KEYWORDS)
    kw_pool = kw_pool[:jumlah * 2]
    random.shuffle(kw_pool)

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

            for hit in hits:
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
    log(f"  Gambar static: {len(list_gambar_static())} "
        f"file di {FOLDER_GAMBAR_STATIC}/")
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
