# scraper.py
import re
import json
import os
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from config import FILE_HISTORY
from utils import log, rp

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8",
}

# ════════════════════════════════════════════════════════════
# SCRAPE LOGAMMULIA.COM
# ════════════════════════════════════════════════════════════

def _scrape_logammulia():
    """
    Ambil harga emas 1 gram dari logammulia.com.
    Tabel urutan: 0.5gr, 1gr, 2gr, ...
    Kita cari baris yang berisi '1 gr' secara eksplisit.
    """
    try:
        resp = requests.get(
            "https://www.logammulia.com/id/harga-emas-hari-ini",
            headers=HEADERS, timeout=20,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Cari semua tabel di halaman
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                if not cells:
                    continue
                # Cari baris dengan teks "1 gr" persis
                cell_texts = [c.get_text(strip=True)
                              for c in cells]
                # Kolom 0 harus "1 gr" (bukan "0.5 gr", "10 gr", dll)
                if (len(cell_texts) >= 2 and
                        re.match(
                            r'^1\s*gr?$',
                            cell_texts[0],
                            re.IGNORECASE
                        )):
                    # Kolom 1 = harga dasar (tanpa pajak)
                    raw = re.sub(r'[^\d]', '', cell_texts[1])
                    if raw and len(raw) >= 6:
                        harga = int(raw)
                        log(f"  -> [logammulia] "
                            f"1 gr = Rp {harga:,}")
                        return harga

        # Fallback: cari dengan regex langsung di HTML
        log("  -> [logammulia] Tabel tidak ketemu, "
            "coba regex...")
        return _scrape_logammulia_regex(resp.text)

    except Exception as e:
        log(f"  -> [logammulia] Error: {e}")
        return None


def _scrape_logammulia_regex(html):
    """
    Fallback: cari pola '1 gr ... 3.xxx.xxx' di HTML mentah.
    Hindari menangkap 0.5 gr atau 10 gr.
    """
    try:
        # Pola: '1 gr' diikuti angka 7 digit (harga per gram)
        # Contoh: "1 gr</td><td>3,021,000</td>"
        pattern = (
            r'(?<![0-9.])'   # tidak didahului angka
            r'1\s*gr'        # tepat "1 gr"
            r'(?!\s*\d)'     # tidak diikuti angka (bukan "10 gr")
            r'.*?'           # isi tengah
            r'(\d[\d.,]{5,})'# angka minimal 6 digit
        )
        matches = re.findall(pattern, html,
                             re.IGNORECASE | re.DOTALL)
        for m in matches:
            raw   = re.sub(r'[^\d]', '', m)
            harga = int(raw)
            # Validasi: harga emas 1gr harusnya 2jt - 5jt
            if 2_000_000 <= harga <= 5_000_000:
                log(f"  -> [logammulia regex] "
                    f"1 gr = Rp {harga:,}")
                return harga
        log("  -> [logammulia regex] Tidak ada "
            "harga valid")
        return None
    except Exception as e:
        log(f"  -> [logammulia regex] Error: {e}")
        return None


# ════════════════════════════════════════════════════════════
# SCRAPE EMASANTAM.ID (sumber cadangan)
# ════════════════════════════════════════════════════════════

def _scrape_emasantam():
    """Sumber cadangan: emasantam.id"""
    try:
        resp = requests.get(
            "https://emasantam.id/harga-emas-antam-harian/",
            headers=HEADERS, timeout=20,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Cari angka harga 1 gram (format Rp. x.xxx.xxx)
        teks = soup.get_text()
        pattern = r'Rp[.\s]*(\d[\d.]+)'
        matches = re.findall(pattern, teks)
        for m in matches:
            raw   = re.sub(r'[^\d]', '', m)
            harga = int(raw)
            if 2_000_000 <= harga <= 5_000_000:
                log(f"  -> [emasantam] "
                    f"1 gr = Rp {harga:,}")
                return harga
        return None
    except Exception as e:
        log(f"  -> [emasantam] Error: {e}")
        return None


# ════════════════════════════════════════════════════════════
# SCRAPE GOODSTATS.ID (sumber cadangan ke-2)
# ════════════════════════════════════════════════════════════

def _scrape_goodstats():
    """Sumber cadangan ke-2: goodstats.id"""
    try:
        resp = requests.get(
            "https://goodstats.id/data-trend/harga-emas/"
            "logammulia",
            headers=HEADERS, timeout=20,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        teks = soup.get_text()

        # Cari baris "1 gr" lalu ambil harga
        lines = teks.splitlines()
        for i, line in enumerate(lines):
            line_s = line.strip()
            if re.match(r'^1\s*gr?$', line_s,
                        re.IGNORECASE):
                # Cari angka di baris berikutnya
                for j in range(i+1, min(i+5, len(lines))):
                    raw = re.sub(r'[^\d]', '',
                                 lines[j].strip())
                    if raw:
                        harga = int(raw)
                        if 2_000_000 <= harga <= 5_000_000:
                            log(f"  -> [goodstats] "
                                f"1 gr = Rp {harga:,}")
                            return harga
        return None
    except Exception as e:
        log(f"  -> [goodstats] Error: {e}")
        return None


# ════════════════════════════════════════════════════════════
# HISTORY HARGA
# ════════════════════════════════════════════════════════════

def _load_history():
    if not os.path.exists(FILE_HISTORY):
        return {}
    try:
        with open(FILE_HISTORY, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_history(history):
    try:
        with open(FILE_HISTORY, "w") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        log(f"  -> [history] Gagal simpan: {e}")


def _hitung_historis(history, harga_sekarang):
    """Hitung perubahan untuk berbagai periode."""
    hari_ini = datetime.now().strftime("%Y-%m-%d")
    result   = {}
    peta     = {
        "kemarin": 1,
        "7_hari":  7,
        "1_bulan": 30,
        "3_bulan": 90,
        "6_bulan": 180,
        "1_tahun": 365,
    }
    tanggal_list = sorted(history.keys(), reverse=True)

    for key, hari in peta.items():
        target = None
        for tgl in tanggal_list:
            try:
                d = datetime.strptime(tgl, "%Y-%m-%d")
                t = datetime.strptime(hari_ini, "%Y-%m-%d")
                selisih_hari = (t - d).days
                if selisih_hari >= hari:
                    target = history[tgl]
                    break
            except Exception:
                continue

        if target is None:
            continue

        selisih = harga_sekarang - target
        persen  = (selisih / target * 100
                   if target else 0)
        result[key] = {
            "harga":  target,
            "selisih": selisih,
            "persen":  persen,
            "naik":    selisih > 0,
            "stabil":  abs(selisih) < 1000,
        }

    return result


# ════════════════════════════════════════════════════════════
# MAIN — dipanggil dari video_maker.py
# ════════════════════════════════════════════════════════════

def ambil_harga_emas():
    log("[1/6] Scraping harga emas...")
    harga = None

    # Sumber 1: logammulia.com
    log("  -> Scraping: logammulia.com...")
    harga = _scrape_logammulia()

    # Sumber 2: emasantam.id
    if not harga:
        log("  -> Scraping: emasantam.id...")
        harga = _scrape_emasantam()

    # Sumber 3: goodstats.id
    if not harga:
        log("  -> Scraping: goodstats.id...")
        harga = _scrape_goodstats()

    # Tidak ada sumber yang berhasil
    if not harga:
        log("  -> ❌ Semua sumber gagal!")
        raise ValueError(
            "Tidak bisa mendapatkan harga emas "
            "dari semua sumber."
        )

    log(f"  -> ✅ logammulia.com: {rp(harga)}")

    # Hitung status vs kemarin
    history     = _load_history()
    hari_ini    = datetime.now().strftime("%Y-%m-%d")
    kemarin_str = None
    tanggal_list = sorted(history.keys(), reverse=True)
    for tgl in tanggal_list:
        if tgl != hari_ini:
            kemarin_str = tgl
            break

    harga_kemarin = (history[kemarin_str]
                     if kemarin_str else harga)
    selisih       = harga - harga_kemarin
    persen        = (selisih / harga_kemarin * 100
                     if harga_kemarin else 0)

    if selisih > 0:
        status = "Naik"
    elif selisih < 0:
        status = "Turun"
    else:
        status = "Stabil"

    # Hitung historis
    historis = _hitung_historis(history, harga)

    # Simpan ke history
    history[hari_ini] = harga
    # Batasi history 400 hari
    if len(history) > 400:
        keys_old = sorted(history.keys())[
            :len(history)-400
        ]
        for k in keys_old:
            del history[k]
    _save_history(history)

    now  = datetime.now()
    info = {
        "harga_sekarang": harga,
        "harga_kemarin":  harga_kemarin,
        "selisih":        selisih,
        "persen":         persen,
        "status":         status,
        "tanggal":        now.strftime("%d %B %Y"),
        "waktu":          now.strftime("%H:%M WIB"),
        "historis":       historis,
    }

    log(f"  -> Harga   : {rp(harga)}")
    log(f"  -> Status  : {status} ({persen:+.2f}%)")
    log(f"  -> Selisih : {rp(selisih)}")

    return info
