# scrape.py
import os, json, re, time
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from config import FILE_HISTORY
from utils  import log

SUMBER_SCRAPING = [
    {
        "nama": "logammulia.com",
        "url":  "https://www.logammulia.com/id/harga-emas-hari-ini",
        "fn":   "_scrape_logammulia",
    },
    {
        "nama": "harga-emas.org",
        "url":  "https://harga-emas.org/",
        "fn":   "_scrape_hargaemas_org",
    },
    {
        "nama": "investing.com",
        "url":  "https://id.investing.com/commodities/gold",
        "fn":   "_scrape_investing",
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
}

# ════════════════════════════════════════════════════════════
# SCRAPER PER SUMBER
# ════════════════════════════════════════════════════════════

def _scrape_logammulia(url):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    for tag in soup.find_all(
            string=re.compile(r"1\s*[Gg]ram")):
        row = tag.find_parent("tr")
        if not row:
            continue
        cells = row.find_all("td")
        for cell in cells:
            txt   = cell.get_text(strip=True)
            clean = re.sub(r"[^\d]", "", txt)
            if clean and 900000 <= int(clean) <= 5000000:
                return int(clean)
    tds = soup.find_all("td")
    for td in tds:
        txt   = td.get_text(strip=True)
        clean = re.sub(r"[^\d]", "", txt)
        if clean and 900000 <= int(clean) <= 5000000:
            return int(clean)
    return None

def _scrape_hargaemas_org(url):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    for tag in soup.find_all(
            string=re.compile(r"Antam|antam|ANTAM")):
        parent = tag.find_parent(
            ["tr","div","span","p","td"])
        if not parent:
            continue
        txt  = parent.get_text(strip=True)
        nums = re.findall(r"\d{3}[\d\.]+", txt)
        for n in nums:
            clean = re.sub(r"\.", "", n)
            try:
                if 900000 <= int(clean) <= 5000000:
                    return int(clean)
            except:
                continue
    patterns = [
        r"Rp\s*([\d\.]+)",
        r"([\d]{3}\.[\d]{3}\.[\d]{3})",
        r"([\d]{1,3}(?:\.[\d]{3})+)",
    ]
    text = soup.get_text()
    for pat in patterns:
        matches = re.findall(pat, text)
        for m in matches:
            clean = re.sub(r"\.", "", m)
            try:
                val = int(clean)
                if 900000 <= val <= 5000000:
                    return val
            except:
                continue
    return None

def _scrape_investing(url):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    text = soup.get_text()
    nums = re.findall(
        r"(?:Rp|IDR)?\s*([\d]{3}[\d\.]+)", text
    )
    for n in nums:
        clean = re.sub(r"\.", "", n)
        try:
            val = int(clean)
            if 900000 <= val <= 5000000:
                return val
        except:
            continue
    return None

# ════════════════════════════════════════════════════════════
# SCRAPE UTAMA — coba semua sumber
# ════════════════════════════════════════════════════════════

def _scrape_harga():
    fn_map = {
        "_scrape_logammulia":    _scrape_logammulia,
        "_scrape_hargaemas_org": _scrape_hargaemas_org,
        "_scrape_investing":     _scrape_investing,
    }
    for sumber in SUMBER_SCRAPING:
        try:
            log(f"  -> Scraping: {sumber['nama']}...")
            fn    = fn_map[sumber["fn"]]
            harga = fn(sumber["url"])
            if harga:
                log(f"  -> ✅ {sumber['nama']}: "
                    f"Rp {harga:,}".replace(",","."))
                return harga
            else:
                log(f"  -> {sumber['nama']}: "
                    f"tidak dapat harga")
        except Exception as e:
            log(f"  -> {sumber['nama']} error: {e}")
        time.sleep(1)
    return None

# ════════════════════════════════════════════════════════════
# HISTORY HARGA
# ════════════════════════════════════════════════════════════

def _load_history():
    if not os.path.exists(FILE_HISTORY):
        return []
    try:
        with open(FILE_HISTORY, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            log("  -> WARNING: history bukan list, reset!")
            return []
        return data
    except Exception as e:
        log(f"  -> WARNING load history: {e}")
        return []

def _simpan_history(history):
    if not isinstance(history, list):
        history = []
    history = history[:400]
    with open(FILE_HISTORY, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2,
                  ensure_ascii=False)

def _hitung_perubahan(harga_kini, history, hari):
    if not isinstance(history, list):
        return None
    target = None
    for h in history:
        try:
            tgl   = datetime.strptime(
                h["tanggal"], "%Y-%m-%d"
            )
            delta = (datetime.now() - tgl).days
            if delta >= hari:
                target = h["harga"]
                break
        except:
            continue
    if not target:
        return None
    selisih = harga_kini - target
    persen  = (selisih / target) * 100
    return {
        "harga_lalu": target,
        "selisih":    selisih,
        "persen":     round(persen, 2),
        "naik":       selisih > 0,
        "stabil":     abs(persen) < 0.1,
    }

# ════════════════════════════════════════════════════════════
# KALKULASI LENGKAP
# ════════════════════════════════════════════════════════════

def scrape_dan_kalkulasi_harga():
    log("[1/6] Scraping harga emas...")
    history = _load_history()

    if not isinstance(history, list):
        log("  -> WARNING: history bukan list, reset!")
        history = []

    harga = _scrape_harga()

    if not harga:
        if history and len(history) > 0:
            harga = history[0]["harga"]
            log(f"  -> Fallback ke history: "
                f"Rp {harga:,}".replace(",","."))
        else:
            harga = 1_650_000
            log(f"  -> Fallback default: "
                f"Rp {harga:,}".replace(",","."))

    if history and len(history) > 0:
        try:
            harga_kemarin = int(history[0]["harga"])
        except (KeyError, ValueError, TypeError):
            harga_kemarin = harga
    else:
        harga_kemarin = harga

    selisih     = harga - harga_kemarin
    persen_hari = round(
        (selisih / harga_kemarin * 100)
        if harga_kemarin else 0, 2
    )

    if abs(persen_hari) < 0.05:
        status = "Stabil"
    elif selisih > 0:
        status = "Naik"
    else:
        status = "Turun"

    historis = {}
    periode  = {
        "kemarin": 1,  "7_hari":  7,
        "1_bulan": 30, "3_bulan": 90,
        "6_bulan": 180,"1_tahun": 365,
    }
    for key, hari in periode.items():
        try:
            historis[key] = _hitung_perubahan(
                harga, history, hari
            )
        except Exception as e:
            log(f"  -> WARNING historis [{key}]: {e}")
            historis[key] = None

    entry = {
        "tanggal": datetime.now().strftime("%Y-%m-%d"),
        "waktu":   datetime.now().strftime("%H:%M:%S"),
        "harga":   harga,
    }
    history.insert(0, entry)
    _simpan_history(history)

    info = {
        "harga_sekarang": harga,
        "harga_kemarin":  harga_kemarin,
        "selisih":        abs(selisih),
        "persen":         abs(persen_hari),
        "status":         status,
        "historis":       historis,
        "tanggal":        datetime.now().strftime(
                              "%d %B %Y"
                          ),
        "waktu":          datetime.now().strftime(
                              "%H:%M WIB"
                          ),
    }

    log(f"  -> Harga   : Rp "
        f"{harga:,}".replace(",","."))
    log(f"  -> Status  : {status} "
        f"({persen_hari:+.2f}%)")
    log(f"  -> Selisih : Rp "
        f"{abs(selisih):,}".replace(",","."))
    return info
