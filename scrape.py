# scraper.py — Scraping harga emas + history
import os, re, json
import requests
from bs4      import BeautifulSoup
from datetime import datetime, timedelta
from config   import FILE_HISTORY
from utils    import log, rp

# ════════════════════════════════════════════════════════════
# HISTORY
# ════════════════════════════════════════════════════════════

def muat_history():
    if os.path.exists(FILE_HISTORY):
        try:
            with open(FILE_HISTORY, encoding="utf-8") as f:
                d = json.load(f)
            # Migrasi format lama
            if "records" not in d and "harga_1_gram" in d:
                return {"records": [{
                    "tanggal": d.get("tanggal", "2000-01-01"),
                    "harga":   d["harga_1_gram"]
                }]}
            return d
        except Exception as e:
            log(f"  -> Gagal muat history: {e}")
    return {"records": []}

def simpan_history(harga):
    hist    = muat_history()
    records = hist.get("records", [])
    today   = datetime.now().strftime("%Y-%m-%d")
    records = [r for r in records if r["tanggal"] != today]
    records.insert(0, {"tanggal": today, "harga": harga})
    records = records[:365]
    with open(FILE_HISTORY, "w", encoding="utf-8") as f:
        json.dump({"records": records}, f, indent=2, ensure_ascii=False)
    return records

def cari_harga_n_hari_lalu(records, n):
    target = (datetime.now().date() - timedelta(days=n)).strftime("%Y-%m-%d")
    for r in records:
        if r["tanggal"] <= target:
            return r
    return None

def analisa_historis(harga_skrg, records):
    hasil = {}
    periods = {
        "kemarin": 1, "7_hari": 7,  "1_bulan": 30,
        "3_bulan": 90,"6_bulan": 180,"1_tahun": 365
    }
    for label, n in periods.items():
        rec = cari_harga_n_hari_lalu(records, n)
        if rec:
            s = harga_skrg - rec["harga"]
            p = round((s / rec["harga"]) * 100, 2)
            hasil[label] = {
                "tanggal":   rec["tanggal"],
                "harga_ref": rec["harga"],
                "selisih":   s,
                "persen":    p,
                "naik":      s > 0,
                "stabil":    s == 0,
            }
    return hasil

# ════════════════════════════════════════════════════════════
# SCRAPING UTAMA
# ════════════════════════════════════════════════════════════

def scrape_dan_kalkulasi_harga():
    log("[1/6] Scraping harga emas Antam dari logammulia.com...")
    try:
        resp = requests.get(
            "https://www.logammulia.com/id/harga-emas-hari-ini",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15
        )
        log(f"  -> HTTP status: {resp.status_code}")
        soup = BeautifulSoup(resp.text, "html.parser")
        raw  = soup.get_text(separator=" | ", strip=True)
        log(f"  -> Raw text: {len(raw)} chars")

        # Parse harga 1 gram
        harga = 0
        for row in soup.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if (len(cells) >= 2 and
                    cells[0].text.strip().lower() in ("1 gr", "1 gram")):
                a = re.sub(r"[^\d]", "", cells[1].text)
                if a:
                    harga = int(a)
                    break

        # Fallback parse
        if harga == 0:
            log("  -> Coba fallback parse angka besar...")
            matches = re.findall(r"\d{1,2}[.,]\d{3}[.,]\d{3}", raw)
            for m in matches:
                angka = int(re.sub(r"[^\d]", "", m))
                if 500000 < angka < 10000000:
                    harga = angka
                    log(f"  -> Fallback harga: {rp(harga)}")
                    break

        if harga == 0:
            log("  -> FATAL: Tidak bisa parse harga sama sekali!")
            return None, None

        log(f"  -> Harga 1 gram: {rp(harga)}")

        # Analisa historis
        hist     = muat_history()
        records  = hist.get("records", [])
        historis = analisa_historis(harga, records)

        # Status vs kemarin
        kmrn = historis.get("kemarin")
        if kmrn:
            s       = kmrn["selisih"]
            status  = "Naik" if s > 0 else ("Turun" if s < 0 else "Stabil")
            selisih = abs(s)
        else:
            status, selisih = "Stabil", 0

        records_baru = simpan_history(harga)
        log(f"  -> Status: {status} {rp(selisih)} | "
            f"History: {len(records_baru)} hari")

        # Log historis detail
        arah_map = {True: "↑", False: "↓"}
        for lb, d in historis.items():
            if d:
                arah = "↑" if d["naik"] else ("↓" if not d["stabil"] else "→")
                log(f"  -> {lb:10s}: {arah} {abs(d['persen']):.1f}% "
                    f"dari {rp(d['harga_ref'])}")

        info = {
            "harga_sekarang": harga,
            "status":         status,
            "selisih":        selisih,
            "historis":       historis,
            "total_record":   len(records_baru),
        }
        konteks = "; ".join([
            f"{lb}: {'naik' if d['naik'] else ('turun' if not d['stabil'] else 'stabil')} "
            f"{abs(d['persen']):.1f}% dari {rp(d['harga_ref'])}"
            for lb, d in historis.items() if d
        ])
        teks_data = (f"Tanggal: {datetime.now().strftime('%d %B %Y')}. "
                     f"Historis: {konteks}. Data: {raw[:2500]}...")
        return info, teks_data

    except Exception as e:
        log(f"  -> EXCEPTION scraping: {type(e).__name__}: {e}")
        return None, None
