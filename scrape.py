# scrape.py
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
    try:
        resp = requests.get(
            "https://www.logammulia.com/id/harga-emas-hari-ini",
            headers=HEADERS, timeout=20,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                if not cells:
                    continue
                cell_texts = [c.get_text(strip=True)
                              for c in cells]
                if (len(cell_texts) >= 2 and
                        re.match(
                            r'^1\s*gr?$',
                            cell_texts[0],
                            re.IGNORECASE
                        )):
                    raw = re.sub(r'[^\d]', '',
                                 cell_texts[1])
                    if raw and len(raw) >= 6:
                        harga = int(raw)
                        if 2_000_000 <= harga <= 6_000_000:
                            log(f"  -> [logammulia] "
                                f"1 gr = {rp(harga)}")
                            return harga

        log("  -> [logammulia] Tabel tidak ketemu, "
            "coba regex...")
        return _scrape_logammulia_regex(resp.text)

    except Exception as e:
        log(f"  -> [logammulia] Error: {e}")
        return None


def _scrape_logammulia_regex(html):
    try:
        pattern = (
            r'(?<![0-9.])1\s*gr'
            r'(?!\s*\d)'
            r'.*?'
            r'(\d[\d.,]{5,})'
        )
        matches = re.findall(pattern, html,
                             re.IGNORECASE | re.DOTALL)
        for m in matches:
            raw   = re.sub(r'[^\d]', '', m)
            harga = int(raw)
            if 2_000_000 <= harga <= 6_000_000:
                log(f"  -> [logammulia regex] "
                    f"1 gr = {rp(harga)}")
                return harga
        log("  -> [logammulia regex] Tidak ada harga valid")
        return None
    except Exception as e:
        log(f"  -> [logammulia regex] Error: {e}")
        return None


# ════════════════════════════════════════════════════════════
# SCRAPE EMASANTAM.ID
# ════════════════════════════════════════════════════════════

def _scrape_emasantam():
    try:
        resp = requests.get(
            "https://emasantam.id/harga-emas-antam-harian/",
            headers=HEADERS, timeout=20,
        )
        resp.raise_for_status()
        soup    = BeautifulSoup(resp.text, "html.parser")
        teks    = soup.get_text()
        matches = re.findall(r'Rp[.\s]*(\d[\d.]+)', teks)
        for m in matches:
            raw   = re.sub(r'[^\d]', '', m)
            harga = int(raw)
            if 2_000_000 <= harga <= 6_000_000:
                log(f"  -> [emasantam] 1 gr = {rp(harga)}")
                return harga
        return None
    except Exception as e:
        log(f"  -> [emasantam] Error: {e}")
        return None


# ════════════════════════════════════════════════════════════
# SCRAPE GOODSTATS.ID
# ════════════════════════════════════════════════════════════

def _scrape_goodstats():
    try:
        resp = requests.get(
            "https://goodstats.id/data-trend/harga-emas/"
            "logammulia",
            headers=HEADERS, timeout=20,
        )
        resp.raise_for_status()
        soup  = BeautifulSoup(resp.text, "html.parser")
        teks  = soup.get_text()
        lines = teks.splitlines()
        for i, line in enumerate(lines):
            if re.match(r'^1\s*gr?$', line.strip(),
                        re.IGNORECASE):
                for j in range(i+1, min(i+5, len(lines))):
                    raw = re.sub(r'[^\d]', '',
                                 lines[j].strip())
                    if raw:
                        harga = int(raw)
                        if 2_000_000 <= harga <= 6_000_000:
                            log(f"  -> [goodstats] "
                                f"1 gr = {rp(harga)}")
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
            data = json.load(f)
        # FIX: pastikan selalu dict, bukan list/tipe lain
        if not isinstance(data, dict):
            log("  -> [history] Format salah, reset ke {}")
            return {}
        return data
    except Exception:
        return {}


def _save_history(history):
    try:
        with open(FILE_HISTORY, "w") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        log(f"  -> [history] Gagal simpan: {e}")


def _hitung_historis(history, harga_sekarang):
    hari_ini     = datetime.now().strftime("%Y-%m-%d")
    result       = {}
    peta         = {
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
                d            = datetime.strptime(tgl, "%Y-%m-%d")
                t            = datetime.strptime(hari_ini, "%Y-%m-%d")
                selisih_hari = (t - d).days
                if selisih_hari >= hari:
                    target = history[tgl]
                    break
            except Exception:
                continue

        if target is None:
            continue

        selisih = harga_sekarang - target
        persen  = (selisih / target * 100 if target else 0)
        result[key] = {
            "harga":   target,
            "selisih": selisih,
            "persen":  persen,
            "naik":    selisih > 0,
            "stabil":  abs(selisih) < 1000,
        }

    return result


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════

def ambil_harga_emas():
    log("[1/6] Scraping harga emas...")
    harga = None

    log("  -> Scraping: logammulia.com...")
    harga = _scrape_logammulia()

    if not harga:
        log("  -> Scraping: emasantam.id...")
        harga = _scrape_emasantam()

    if not harga:
        log("  -> Scraping: goodstats.id...")
        harga = _scrape_goodstats()

    if not harga:
        log("  -> ❌ Semua sumber gagal!")
        raise ValueError(
            "Tidak bisa mendapatkan harga emas "
            "dari semua sumber."
        )

    log(f"  -> ✅ Harga ditemukan: {rp(harga)}")

    # Load history — dijamin dict
    history      = _load_history()
    hari_ini     = datetime.now().strftime("%Y-%m-%d")
    kemarin_str  = None
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

    historis = _hitung_historis(history, harga)

    # Simpan history
    history[hari_ini] = harga
    if len(history) > 400:
        keys_old = sorted(history.keys())[:len(history)-400]
        for k in keys_old:
            del history[k]
    _save_history(history)

    now  = datetime.now()
    info = {
        "harga_sekarang": harga,
        "harga_kemarin":  harga_kemarin,
        "selisih":        abs(selisih),
        "persen":         persen,
        "status":         status,
        "tanggal":        now.strftime("%d %B %Y"),
        "waktu":          now.strftime("%H:%M WIB"),
        "historis":       historis,
    }

    log(f"  -> Harga   : {rp(harga)}")
    log(f"  -> Kemarin : {rp(harga_kemarin)}")
    log(f"  -> Status  : {status} ({persen:+.2f}%)")
    log(f"  -> Selisih : {rp(abs(selisih))}")

    return info
