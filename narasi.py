# narasi.py — Judul clickbait + narasi Gemini/fallback
import re, random, time
import requests
from datetime import datetime
from config   import (NAMA_CHANNEL, NARASI_GAYA, GEMINI_API_KEY,
                      CHANNEL_ID)
from utils    import log, rp

# ════════════════════════════════════════════════════════════
# VALIDASI JUDUL
# ════════════════════════════════════════════════════════════

BOCOR_KEYWORDS = [
    "tentu","berikut","ini dia","mari kita","baik,","oke,","siap,",
    "scriptwriter","naskah video","konten youtube","sebagai ai",
    "sebagai asisten","dengan pleasure","dengan senang"
]

def _validasi_judul(judul_raw, info, historis):
    if (any(k in judul_raw.lower() for k in BOCOR_KEYWORDS)
            or len(judul_raw.strip()) < 10):
        fix = buat_judul_clickbait_lokal(info, historis)
        log(f"  -> [FIX JUDUL bocor]: {fix}")
        return fix
    return judul_raw.strip()[:100]

# ════════════════════════════════════════════════════════════
# JUDUL CLICKBAIT LOKAL
# ════════════════════════════════════════════════════════════

def buat_judul_clickbait_lokal(info, historis):
    h   = f"Rp {info['harga_sekarang']:,}".replace(",", ".")
    st  = info["status"]
    sel = f"Rp {info['selisih']:,}".replace(",", ".")
    tgl = datetime.now().strftime("%d %b %Y")

    np = {"kemarin":"Kemarin","7_hari":"Seminggu","1_bulan":"Sebulan",
          "3_bulan":"3 Bulan","6_bulan":"6 Bulan","1_tahun":"Setahun"}

    # Cari historis signifikan >= 2%
    penting = None
    for lb in ["3_bulan","1_bulan","6_bulan","1_tahun","7_hari"]:
        d = historis.get(lb)
        if d and abs(d["persen"]) >= 2.0:
            penting = (lb, d)
            break

    if penting:
        lb, d  = penting
        pct    = abs(d["persen"])
        pl     = np.get(lb, lb)
        arah   = "naik" if d["naik"] else "turun"
        pools  = _pool_historis(h, pct, pl, tgl, arah)
        return random.choice(
            pools.get(NARASI_GAYA, pools["formal_analitis"])
        )[:100]

    pools = _pool_harian(h, st, sel, tgl)
    pool_status = pools.get(st, pools["Stabil"])
    pool_gaya   = pool_status.get(NARASI_GAYA,
                                   list(pool_status.values())[0])
    return random.choice(pool_gaya)[:100]


def _pool_historis(h, pct, pl, tgl, arah):
    if arah == "naik":
        return {
            "formal_analitis": [
                f"📊 Analisa: Emas Antam NAIK {pct:.1f}% dalam {pl} — Proyeksi {tgl}",
                f"Sinyal Bullish! Emas Antam +{pct:.1f}% Sejak {pl} — Harga {h}/gram",
                f"Data Kenaikan {pct:.1f}% dalam {pl}! Emas Antam {h}/gram — Beli?",
                f"Momentum NAIK {pct:.1f}%! Emas Antam {h}/gram — Analisa {tgl}",
                f"Tren Naik {pct:.1f}% dalam {pl} — Emas Antam {h}/gram Berapa Lagi?",
                f"📈 Emas Antam +{pct:.1f}% dari {pl} Lalu — Analisa Teknikal {tgl}",
                f"Investor Siap! Emas Antam +{pct:.1f}% dalam {pl} — Target {h}/gram",
                f"Fundamental Kuat! Emas Antam NAIK {pct:.1f}% Sejak {pl} — {tgl}",
            ],
            "santai_edukatif": [
                f"Eh Emas Naik {pct:.1f}% lho dalam {pl}! Masih Mau Beli? {h}/gram",
                f"Kamu Sudah Tau? Emas Antam Udah Naik {pct:.1f}% dari {pl} Lalu!",
                f"💡 Emas Naik {pct:.1f}% dalam {pl} — Apa Artinya Buat Kamu?",
                f"Emas Antam Naik {pct:.1f}%! {h}/gram — Yuk Pelajari Bareng!",
                f"Wow Naik {pct:.1f}% dalam {pl}! Emas Antam {h}/gram Worth It?",
                f"Baru Tau Emas Naik {pct:.1f}%? Antam {h}/gram — Simak Ini!",
                f"Naik {pct:.1f}% tapi Masih Bagus Beli? Emas Antam {h}/gram",
                f"💡 Belajar dari Kenaikan {pct:.1f}% Emas dalam {pl} — Yuk!",
            ],
            "berita_singkat": [
                f"BREAKING: Emas Antam +{pct:.1f}% dalam {pl}! Harga {h}/gram",
                f"UPDATE {tgl}: Emas Antam Naik {pct:.1f}% dari {pl} — {h}/gram",
                f"🔴 NAIK {pct:.1f}% dari {pl}! Emas Antam {h}/gram — Update Resmi",
                f"TERBARU: Kenaikan {pct:.1f}% Emas Antam {h}/gram — {tgl}",
                f"LIVE {tgl}: Emas Antam {h}/gram Naik {pct:.1f}% dari {pl}",
                f"INFO RESMI: Emas Antam +{pct:.1f}% Sejak {pl} — {h}/gram",
                f"WASPADA: Emas Antam Sudah Naik {pct:.1f}% dalam {pl}! {h}",
                f"TERKINI: Emas Antam {h}/gram — Naik {pct:.1f}% dari {pl}",
            ],
            "energik_motivatif": [
                f"🚀 EMAS MELEJIT {pct:.1f}%! {pl} Lalu Beli = UNTUNG BESAR!",
                f"NAIK {pct:.1f}% dalam {pl}!! BUKTI Emas Investasi TERBAIK! {h}",
                f"💥 PROFIT {pct:.1f}% dalam {pl}! Masih Ragu Beli Emas?!",
                f"EMAS ANTAM TERBANG {pct:.1f}%!! Jangan Menyesal! Harga {h}/gram",
                f"WOW {pct:.1f}% KEUNTUNGAN dalam {pl}!! Emas Antam {h}/gram!!",
                f"🔥 NAIK {pct:.1f}%!! Bukti Nyata Emas = Investasi TERBAIK!!",
                f"ALERT NAIK {pct:.1f}%! Emas Antam {h}/gram — Beli SEKARANG!",
                f"JANGAN LEWATKAN! Emas +{pct:.1f}% dalam {pl} — {h}/gram!!",
            ],
            "percakapan_akrab": [
                f"Bro, Emas Udah Naik {pct:.1f}% nih dari {pl} — Gimana?",
                f"Guys! Emas Naik {pct:.1f}% dalam {pl}! Worth It Beli? {h}",
                f"Jujur nih, Emas Antam {pct:.1f}% Naik dari {pl} — {h}/gram",
                f"Serius? Emas Naik {pct:.1f}% dalam {pl}! Yuk Bahas — {h}",
                f"Eh, Coba Liat Nih! Emas Naik {pct:.1f}% dari {pl} — Wow!",
                f"Kalian Tau Gak? Emas Udah +{pct:.1f}% dari {pl} — Keren!",
                f"Wah Serius Nih! Emas {h}/gram — Naik {pct:.1f}% dari {pl}",
                f"Ngobrol Bareng: Emas Naik {pct:.1f}% dalam {pl} — Gimana?",
            ],
        }
    else:
        return {
            "formal_analitis": [
                f"📊 Koreksi {pct:.1f}% dalam {pl} — Emas Antam {h}/gram Beli?",
                f"Teknikal Oversold! Emas -{pct:.1f}% dari {pl} — {h}/gram {tgl}",
                f"Data Koreksi {pct:.1f}% Sejak {pl} — Akumulasi Sekarang?",
                f"Support Level! Emas Antam Turun {pct:.1f}% dari {pl} — {h}",
                f"Analisa Koreksi {pct:.1f}%: Emas Antam {h}/gram — Entry Point?",
                f"📉 Emas -{pct:.1f}% dalam {pl} — Rekomendasi Analis {tgl}",
                f"Pullback {pct:.1f}%! Emas Antam {h}/gram — Beli atau Tunggu?",
                f"Reversal Signal? Emas Antam Turun {pct:.1f}% dari {pl} — {h}",
            ],
            "santai_edukatif": [
                f"Emas Turun {pct:.1f}% dari {pl} — Waktu Terbaik Beli Nih!",
                f"💡 Koreksi {pct:.1f}% = Kesempatan! Emas Antam {h}/gram",
                f"Mau Beli Emas Murah? Turun {pct:.1f}% dari {pl} — Ayo!",
                f"Tenang! Turun {pct:.1f}% itu Normal — Antam {h}/gram",
                f"Eh Emas Turun {pct:.1f}% nih! Justru Bagus Buat Nabung!",
                f"💡 Koreksi {pct:.1f}% = Sale Emas! Yuk Pelajari Strateginya",
                f"Emas Murah {pct:.1f}% dari {pl} — {h}/gram — Beli Dulu!",
                f"Penjelasan Koreksi {pct:.1f}%: Emas Antam {h}/gram Normal!",
            ],
            "berita_singkat": [
                f"UPDATE: Emas Antam -{pct:.1f}% dari {pl} — {h}/gram {tgl}",
                f"TERBARU {tgl}: Koreksi {pct:.1f}% — Emas Antam {h}/gram",
                f"🟢 TURUN {pct:.1f}% dari {pl}! Emas Antam {h}/gram Hari Ini",
                f"INFO: Emas -{pct:.1f}% dalam {pl} — {h}/gram — Beli Gak?",
                f"LIVE: Emas Antam Koreksi {pct:.1f}% dari {pl} — {h}/gram",
                f"TERKINI {tgl}: Emas {h}/gram Turun {pct:.1f}% dari {pl}",
                f"INFO RESMI: Koreksi Emas {pct:.1f}% — Harga {h}/gram {tgl}",
                f"DATA: Emas Antam -{pct:.1f}% Sejak {pl} — {h}/gram Now",
            ],
            "energik_motivatif": [
                f"💰 DISKON {pct:.1f}%!! EMAS ANTAM {h}/gram — BORONG NOW!",
                f"KESEMPATAN LANGKA! Emas -{pct:.1f}% dari {pl} — ACTION!",
                f"🎯 HARGA TERBAIK! Koreksi {pct:.1f}% dalam {pl} — BELI!",
                f"SALE EMAS {pct:.1f}%! Antam {h}/gram — Kapan Lagi Murah?!",
                f"ALERT MURAH! Emas Turun {pct:.1f}% — {h}/gram BELI NOW!!",
                f"🔥 DISKON EMAS {pct:.1f}%! Harga {h}/gram — Jangan Tunggu!",
                f"BORONG SEKARANG! Emas -{pct:.1f}% = {h}/gram — LAST CHANCE!",
                f"💸 PROFIT WAITING! Emas Koreksi {pct:.1f}% — {h}/gram BUY!",
            ],
            "percakapan_akrab": [
                f"Wah Emas Turun {pct:.1f}% nih dari {pl} — Udah Borong?",
                f"Guys, Waktu Beli Emas! Turun {pct:.1f}% — {h}/gram Nih",
                f"Serius Emas Turun {pct:.1f}%? Yuk Analisa Bareng — {h}",
                f"Bro, Emas {h}/gram — Turun {pct:.1f}% dari {pl}, Beli?",
                f"Kalian Udah Beli? Emas Turun {pct:.1f}% dari {pl} — {h}",
                f"Lagi Murah Nih! Emas -{pct:.1f}% dari {pl} — Gimana?",
                f"Eh Emas Turun {pct:.1f}%! {h}/gram — Mau Borong Bareng?",
                f"Diskusi Yuk! Emas -{pct:.1f}% dari {pl} — Worth It Beli?",
            ],
        }


def _pool_harian(h, st, sel, tgl):
    return {
        "Naik": {
            "formal_analitis": [
                f"Emas Antam {h}/gram Naik {sel} — Analisa & Proyeksi {tgl}",
                f"Kenaikan {sel} pada Emas Antam {h}/gram — Rekomendasi Analis",
                f"📈 Emas Antam Terkerek {sel} Jadi {h}/gram — Sinyal Beli?",
                f"Momentum Naik! Emas Antam +{sel} Jadi {h}/gram Hari Ini",
                f"Emas Antam {h}/gram Naik {sel} — Fundamental Masih Kuat?",
                f"🔴 Emas Antam Menguat {sel} ke {h}/gram — Update Resmi {tgl}",
                f"Harga Emas Antam Naik {sel} — Tren Berlanjut? {h}/gram",
                f"Update: Emas Antam +{sel} ke {h}/gram — Rekomendasi {tgl}",
            ],
            "santai_edukatif": [
                f"Emas Naik Lagi {sel}! Jadi {h}/gram — Masih Oke Buat Invest?",
                f"Harga Emas Antam Naik {sel} — Yuk Pahami Kenapa! {h}/gram",
                f"💡 Kenapa Emas Naik {sel}? Penjelasan Mudahnya! {h}/gram",
                f"Emas Antam {h}/gram Naik {sel} — 5 Hal yang Perlu Kamu Tau",
                f"Naik {sel}! Emas Antam {h}/gram — Tips Investor Pemula",
                f"Update Emas: Naik {sel} ke {h}/gram — Santai, Ini Normal!",
                f"Eh Emas Naik {sel} lho! Jadi {h}/gram — Mau Tau Kenapa?",
                f"Emas Antam {h}/gram — Naik {sel}, Waktu Tepat Nabung?",
            ],
            "berita_singkat": [
                f"BREAKING: Emas Antam Naik {sel} Jadi {h}/gram — {tgl}",
                f"UPDATE {tgl}: Naik {sel} ke {h}/gram — Cek Sekarang!",
                f"🔴 NAIK {sel}! Emas Antam {h}/gram — Update Resmi Hari Ini",
                f"TERBARU: Emas Antam {h}/gram Naik {sel} dari Kemarin",
                f"INFO {tgl}: Emas Antam Naik {sel} — Harga Lengkap di Sini",
                f"LIVE: Emas Antam {h}/gram Naik {sel} Hari Ini!",
                f"WASPADA: Emas Antam Naik {sel} ke {h}/gram — {tgl}",
                f"TERKINI: Emas Antam {h}/gram Naik {sel} — Jual atau Tahan?",
            ],
            "energik_motivatif": [
                f"🚨 EMAS NAIK {sel}!! Antam {h}/gram — Masih Mau Diam Aja?!",
                f"NAIK {sel}! Emas Antam {h}/gram — INI TANDA NAIK TERUS?!",
                f"💥 EMAS ANTAM MELEJIT {sel}! {h}/gram — Kapan Lagi Beli?!",
                f"ALERT! Emas Naik {sel}! {h}/gram — Jangan Sampai Nyesel!",
                f"🔥 EMAS NAIK {sel} HARI INI! {h}/gram — ACTION SEKARANG!",
                f"WOW! Emas Antam Naik {sel} ke {h}/gram — Ini Buktinya!",
                f"NAIK TERUS! Emas Antam +{sel} Jadi {h}/gram — Beli Gak?!",
                f"EMAS ANTAM {h}/gram NAIK {sel}!! Mau Untung? Tonton Ini!",
            ],
            "percakapan_akrab": [
                f"Guys Emas Naik Lagi {sel}! Antam {h}/gram — Kalian Gimana?",
                f"Bro Emas Naik {sel} nih! Jadi {h}/gram — Worth It Beli?",
                f"Serius Emas Naik {sel}? Antam {h}/gram — Yuk Bahas!",
                f"Wah Emas Antam Naik {sel}! {h}/gram — Mau Beli atau Tunggu?",
                f"Eh Tau Gak? Emas Naik {sel} Hari Ini! Antam {h}/gram nih",
                f"Nabung Emas Gak? Antam Naik {sel} jadi {h}/gram hari ini!",
                f"Emas Antam {h}/gram — Naik {sel}, Gimana Strategi Kamu?",
                f"Sip! Emas Naik {sel} ke {h}/gram — Share ke Temenmu Juga!",
            ],
        },
        "Turun": {
            "formal_analitis": [
                f"Koreksi Emas Antam {sel} ke {h}/gram — Analisa Support Level",
                f"Teknikal: Emas Antam Turun {sel} ke {h}/gram — Beli atau Wait?",
                f"📉 Emas Antam Terkoreksi {sel} ke {h}/gram — Rekomendasi {tgl}",
                f"Data Koreksi: Emas Antam {h}/gram Turun {sel} — Fundamentals?",
                f"Emas Antam Melemah {sel} ke {h}/gram — Analisa {tgl}",
                f"Update: Emas Antam -{sel} Jadi {h}/gram — Momentum Akumulasi?",
                f"🟢 Emas Antam Koreksi {sel} — {h}/gram Titik Masuk Terbaik?",
                f"Harga Emas Antam {h}/gram Turun {sel} — Oversold atau Lanjut?",
            ],
            "santai_edukatif": [
                f"Emas Turun {sel} jadi {h}/gram — Tenang, Ini Waktu Nabung!",
                f"💡 Emas Antam Turun {sel}! {h}/gram — Manfaatin Momen Ini",
                f"Emas Antam {h}/gram Turun {sel} — 3 Alasan Ini Justru Bagus",
                f"Turun {sel}? Emas Antam {h}/gram Tetap Investasi Terbaik!",
                f"Eh Emas Turun {sel} lho! {h}/gram — Ini Artinya Apa buat Kamu?",
                f"Emas Antam Turun {sel} ke {h}/gram — Tips Beli Harga Murah",
                f"Santai! Turun {sel} Itu Normal — Emas Antam {h}/gram Hari Ini",
                f"Mau Beli Emas Murah? {h}/gram Turun {sel} — Yuk Simak!",
            ],
            "berita_singkat": [
                f"UPDATE: Emas Antam Turun {sel} ke {h}/gram — {tgl}",
                f"TERBARU: Emas Antam {h}/gram Koreksi {sel} Hari Ini",
                f"🟢 TURUN {sel}! Emas Antam {h}/gram — Update Resmi {tgl}",
                f"INFO {tgl}: Emas Antam Melemah {sel} ke {h}/gram",
                f"LIVE: Harga Emas Antam {h}/gram Koreksi {sel} — Cek Di Sini",
                f"TERKINI: Emas Antam -{sel} Jadi {h}/gram — Saatnya Beli?",
                f"UPDATE EMAS {tgl}: Turun {sel} ke {h}/gram — Data Lengkap",
                f"INFO HARGA: Emas Antam {h}/gram Turun {sel} dari Kemarin",
            ],
            "energik_motivatif": [
                f"🎯 EMAS TURUN {sel}!! {h}/gram — INI WAKTU BELI TERBAIK!",
                f"DISKON {sel}! Emas Antam {h}/gram — BORONG SEBELUM NAIK!",
                f"💰 HARGA MURAH! Emas Turun {sel} ke {h}/gram — BURUAN!",
                f"KESEMPATAN EMAS! Turun {sel} ke {h}/gram — Jangan Ragu!",
                f"🔥 SALE EMAS! Antam -{sel} = {h}/gram — Kapan Lagi?!",
                f"EMAS MURAH {sel}! {h}/gram — BELI SEBELUM TERLAMBAT!",
                f"WOW TURUN {sel}!! Emas Antam {h}/gram — Sinyal Kuat Beli!",
                f"ALERT MURAH! Emas -{sel} ke {h}/gram — ACTION NOW!",
            ],
            "percakapan_akrab": [
                f"Bro Emas Turun {sel}! {h}/gram — Udah Beli Belum Nih?",
                f"Guys! Emas Antam {h}/gram Turun {sel} — Mau Borong Gak?",
                f"Eh Emas Murah {sel}! Antam {h}/gram — Yuk Nabung Bareng!",
                f"Serius Emas Turun {sel}? {h}/gram — Kalian Beli Gak Nih?",
                f"Wah Emas Antam {h}/gram Turun {sel} — Worth It Banget Beli!",
                f"Emas Turun {sel} nih! Antam {h}/gram — Gimana Pendapatmu?",
                f"Nabung Emas Yuk! Antam Turun {sel} jadi {h}/gram Hari Ini",
                f"Beli Emas Sekarang! Turun {sel} ke {h}/gram — Mumpung Murah!",
            ],
        },
        "Stabil": {
            "formal_analitis": [
                f"Analisa: Emas Antam Konsolidasi di {h}/gram — Arah Selanjutnya?",
                f"Sideways! Emas Antam {h}/gram — Sinyal Teknikal & Proyeksi {tgl}",
                f"📊 Emas Antam Stagnan {h}/gram — Kapan Break Out? Analisa {tgl}",
                f"Consolidation Phase: Emas Antam {h}/gram — Beli atau Tunggu?",
                f"Emas Antam {h}/gram Flat — Analisa Fundamental & Teknikal {tgl}",
                f"Update Harga Emas Antam {h}/gram — Stabil, Menuju Tren Mana?",
                f"Harga Emas Antam {h}/gram Konsolidasi — Rekomendasi Investor",
                f"⬛ Emas Antam {h}/gram — Koreksi Dulu atau Mau Naik? Analisa",
            ],
            "santai_edukatif": [
                f"Emas Antam {h}/gram Hari Ini — Stabil, tapi Tunggu Dulu Nih!",
                f"💡 Emas Antam Stagnan di {h}/gram — Apa yang Harus Dilakukan?",
                f"Harga Emas {h}/gram Gak Bergerak — Ini Penjelasan Lengkapnya!",
                f"Emas Antam {h}/gram Masih Flat — 4 Strategi Investasi Tepat",
                f"Tenang Emas Antam {h}/gram Stabil — Yuk Belajar Cara Invest!",
                f"Emas Antam Stagnan {h}/gram — Waktu Terbaik Belajar Investasi",
                f"Eh Emas {h}/gram Stabil Nih! Buat Kamu yang Mau Mulai Invest",
                f"Emas Antam {h}/gram Flat — 3 Hal yang Perlu Kamu Persiapkan",
            ],
            "berita_singkat": [
                f"UPDATE {tgl}: Emas Antam Stabil di {h}/gram — Harga Lengkap",
                f"TERBARU: Emas Antam {h}/gram — Stagnan, Ini Data Resminya!",
                f"⬛ STABIL! Emas Antam {h}/gram — Update Resmi {tgl}",
                f"INFO HARGA {tgl}: Emas Antam {h}/gram Tidak Berubah Hari Ini",
                f"LIVE: Emas Antam {h}/gram Konsolidasi — Update Terkini {tgl}",
                f"TERKINI: Harga Emas Antam {h}/gram — Flat, Ini Penyebabnya!",
                f"INFO: Emas Antam {h}/gram Stabil — Daftar Harga Lengkap {tgl}",
                f"UPDATE EMAS {tgl}: Antam {h}/gram Stagnan — Naik atau Turun?",
            ],
            "energik_motivatif": [
                f"😲 EMAS ANTAM DIAM di {h}/gram — INI PERTANDA MENARIK!!",
                f"🤔 Kenapa Emas {h}/gram Gak Bergerak?! Ini Jawabannya!!",
                f"⚡ STAGNAN = KESEMPATAN! Emas Antam {h}/gram — Beli Sekarang!",
                f"WASPADA! Emas Antam {h}/gram Tenang — BADAI AKAN DATANG?!",
                f"🎯 EMAS ANTAM {h}/gram STAGNAN — STRATEGI PROFIT TERBAIK!",
                f"SINYAL KUAT! Emas {h}/gram Konsolidasi — MAU NAIK BESAR?!",
                f"EMAS ANTAM {h}/gram FLAT — TAPI INI JUSTRU WAKTU BELI!",
                f"⚠️ ALERT! Emas {h}/gram Tidak Bergerak — Ini Berbahaya?!",
            ],
            "percakapan_akrab": [
                f"Guys Emas Antam {h}/gram Hari Ini — Stabil, Gimana Menurutmu?",
                f"Bro, Emas Antam {h}/gram Gak Kemana-mana — Beli atau Tunggu?",
                f"Eh Emas Antam Masih {h}/gram Nih — Kalian Gimana Strateginya?",
                f"Emas Antam {h}/gram Stagnan — Yuk Diskusi di Kolom Komentar!",
                f"Serius Emas {h}/gram Flat? — Curhat Dong, Kalian Beli Gak?",
                f"Wah Emas Antam {h}/gram Masih Sama — Enak nih Buat Nabung!",
                f"Emas {h}/gram Tenang Banget — Kalian Bakal Beli Gak?",
                f"Emas Antam {h}/gram — Stagnan Bro, tapi Worth It Tetap Nabung!",
            ],
        },
    }

# ════════════════════════════════════════════════════════════
# NARASI FALLBACK LOKAL (5 GAYA)
# ════════════════════════════════════════════════════════════

def _buat_narasi_fallback(info, harga_skrg, status_harga, selisih_harga):
    tgl  = datetime.now().strftime("%d %B %Y")
    hari = {"Monday":"Senin","Tuesday":"Selasa","Wednesday":"Rabu",
            "Thursday":"Kamis","Friday":"Jumat",
            "Saturday":"Sabtu","Sunday":"Minggu"
            }.get(datetime.now().strftime("%A"), "")
    h    = info["harga_sekarang"]
    tabel_ukuran = {
        "setengah gram": h//2,    "satu gram": h,
        "dua gram":      h*2,     "tiga gram": h*3,
        "lima gram":     h*5,     "sepuluh gram": h*10,
        "dua puluh lima gram": h*25, "lima puluh gram": h*50,
        "seratus gram":  h*100,   "dua ratus lima puluh gram": h*250,
        "lima ratus gram": h*500, "seribu gram": h*1000,
    }
    daftar = " ".join(
        f"Untuk {s}, harganya {rp(v)}."
        for s, v in tabel_ukuran.items()
    )
    ks = {
        "Naik":  f"mengalami kenaikan sebesar {selisih_harga} Rupiah dari kemarin",
        "Turun": f"mengalami penurunan sebesar {selisih_harga} Rupiah dari kemarin",
        "Stabil":"terpantau stabil tidak berubah dari hari sebelumnya",
    }.get(status_harga, "terpantau stabil")

    kh = ""
    for lb, d in info.get("historis", {}).items():
        if d and abs(d["persen"]) >= 1.0:
            arah = "naik" if d["naik"] else "turun"
            nama = {"kemarin":"kemarin","7_hari":"seminggu lalu",
                    "1_bulan":"sebulan lalu","3_bulan":"tiga bulan lalu",
                    "6_bulan":"enam bulan lalu","1_tahun":"setahun lalu"
                    }.get(lb, lb)
            kh = (f" Dibandingkan {nama}, harga emas telah {arah} "
                  f"{abs(d['persen']):.1f}% dari {rp(d['harga_ref'])} "
                  f"menjadi {rp(h)}.")
            break

    templates = {
        "formal_analitis": f"""Halo sobat {NAMA_CHANNEL}, selamat datang kembali di channel kami. Pada hari {hari} tanggal {tgl} ini, kami hadir dengan update komprehensif pergerakan harga emas Antam Logam Mulia.

Berdasarkan data resmi dari situs Logam Mulia, harga emas Antam satu gram hari ini adalah {rp(h)}. Harga ini {ks}.{kh} Data ini dapat dijadikan acuan dalam mengambil keputusan investasi.

Berikut daftar lengkap harga emas Antam semua ukuran hari ini. {daftar}

Dari perspektif fundamental, kebijakan moneter Federal Reserve Amerika Serikat tetap menjadi variabel paling dominan. Indeks dolar berkorelasi negatif dengan emas. Situasi geopolitik global mendorong permintaan emas sebagai safe haven. Data inflasi global di atas target bank sentral memberikan dukungan positif bagi harga emas sebagai instrumen lindung nilai.

Kami rekomendasikan systematic investment plan sebagai metode paling efektif membangun portofolio emas jangka panjang. Beli melalui gerai resmi Antam dan simpan dengan aman menggunakan Safe Deposit Box.

Demikian analisa dari {NAMA_CHANNEL}. Subscribe dan aktifkan notifikasi untuk update harga dan analisa emas terbaru setiap hari. Terima kasih dan salam investasi cerdas!""",

        "santai_edukatif": f"""Halo sobat {NAMA_CHANNEL}! Selamat datang lagi, hari ini hari {hari} tanggal {tgl} dan kita bahas bareng update harga emas Antam paling fresh!

Harga emas Antam satu gram hari ini ada di angka {rp(h)}. Harga ini {ks}.{kh} Info ini dari website resmi Logam Mulia, jadi bisa dipercaya.

Oke sekarang kita lihat harga lengkap semua ukuran. {daftar}

Yuk pahami kenapa harga emas bisa naik turun. Pertama, emas sangat dipengaruhi kebijakan bank sentral Amerika soal suku bunga. Kedua, kondisi geopolitik global selalu bikin orang lari ke emas sebagai tempat berlindung. Ketiga, nilai tukar Rupiah terhadap Dolar sangat menentukan harga emas dalam Rupiah.

Buat yang mau mulai investasi emas, mulai dari yang kecil, beli rutin setiap bulan, dan jangan panik kalau harga turun. Simpan emas dengan aman dan pastikan beli di tempat terpercaya.

Oke itu tadi update dari {NAMA_CHANNEL}! Kalau ada pertanyaan, langsung tulis di kolom komentar. Jangan lupa subscribe dan nyalakan lonceng notifikasinya. Sampai jumpa besok!""",

        "berita_singkat": f"""Halo sobat {NAMA_CHANNEL}, berikut update harga emas Antam Logam Mulia hari {hari} tanggal {tgl}.

Harga emas Antam resmi hari ini untuk ukuran satu gram adalah {rp(h)}. Harga ini {ks}.{kh}

Daftar harga lengkap emas Antam semua ukuran hari ini. {daftar}

Kondisi pasar emas global hari ini dipengaruhi arah kebijakan Federal Reserve, pergerakan indeks dolar, serta sentimen risiko global terkait geopolitik. Data inflasi dari negara-negara ekonomi utama juga menjadi pertimbangan investor.

Tips hari ini: beli rutin setiap bulan, manfaatkan harga turun sebagai momentum akumulasi, dan selalu beli melalui gerai resmi Antam.

Itulah update dari {NAMA_CHANNEL}. Subscribe dan aktifkan notifikasi untuk update harga emas setiap hari. Terima kasih!""",

        "energik_motivatif": f"""Halo halo halo sobat {NAMA_CHANNEL}!! Selamat datang kembali di channel paling update soal harga emas Antam!! Hari ini hari {hari} tanggal {tgl}!!

Langsung gas ya!! Harga emas Antam satu gram hari ini adalah {rp(h)}!! Harga ini {ks}!!{kh} Ini data RESMI langsung dari Logam Mulia!!

Catat baik-baik harga lengkap semua ukuran!! {daftar}

Guys ada hal penting yang harus kamu ketahui!! Federal Reserve Amerika Serikat sedang dalam sorotan tajam!! Ketidakpastian geopolitik global masih tinggi dan ini MENGUNTUNGKAN yang sudah pegang emas!! Emas adalah satu-satunya aset yang terbukti bertahan di kondisi krisis apapun!!

Buat yang belum punya emas, mulai dari satu gram pun tidak masalah!! Yang penting MULAI SEKARANG!! Beli rutin setiap bulan, tidak perlu banyak yang penting KONSISTEN!!

Kalau video ini bermanfaat, LIKE sekarang, SUBSCRIBE sekarang, dan SHARE!! Aktifkan notifikasi biar selalu yang pertama dapat update!! SALAM KAYA RAYA!!""",

        "percakapan_akrab": f"""Hei hei hei, apa kabar semua? Selamat datang kembali di {NAMA_CHANNEL}! Hari ini hari {hari} tanggal {tgl}, yuk langsung kita bahas bareng harga emas Antam hari ini!

Jadi gini guys, harga emas Antam buat ukuran satu gram hari ini ada di angka {rp(h)}. Harga ini {ks}.{kh} Infonya dari website resmi Logam Mulia ya, jadi bisa dipercaya!

Buat yang mau tau harga lengkap semua ukuran, ini dia! {daftar}

Nah aku mau kasih tau juga kenapa emas itu selalu menarik buat dibahas. Pertama, emas itu gak ada matinya sebagai investasi. Kedua, kondisi global yang gak pasti justru bikin emas makin bersinar. Ketiga, emas itu gampang dicairin kalau butuh dana darurat. Keempat, mulai belinya bisa dari ukuran kecil.

Buat kalian yang udah lama invest emas, good job! Buat yang baru mau mulai, jangan takut, mulai aja dulu dari yang kecil. Beli tiap bulan rutin!

Kalau ada yang mau diskusi, yuk tulis di kolom komentar! Jangan lupa subscribe ya biar kita bisa ketemu terus tiap hari! Bye bye dan sampai jumpa besok!""",
    }
    return templates.get(NARASI_GAYA,
                          templates["formal_analitis"]).strip()

# ════════════════════════════════════════════════════════════
# NARASI & JUDUL VIA GEMINI
# ════════════════════════════════════════════════════════════

def buat_narasi_dan_judul(info, data_harga):
    log("[2/6] Membuat narasi dan judul...")
    status_harga  = info["status"]
    selisih_harga = f"{info['selisih']:,}".replace(",", ".")
    harga_skrg    = f"{info['harga_sekarang']:,}".replace(",", ".")
    historis      = info.get("historis", {})

    judul = buat_judul_clickbait_lokal(info, historis)
    log(f"  -> Judul lokal: {judul}")

    ringkasan_h = []
    for label, d in historis.items():
        if d:
            arah = "naik" if d["naik"] else ("turun" if not d["stabil"] else "stabil")
            nama = {"kemarin":"kemarin","7_hari":"seminggu lalu",
                    "1_bulan":"sebulan lalu","3_bulan":"3 bulan lalu",
                    "6_bulan":"6 bulan lalu","1_tahun":"setahun lalu"
                    }.get(label, label)
            ringkasan_h.append(
                f"{nama}: {arah} {abs(d['persen']):.1f}% "
                f"dari Rp {d['harga_ref']:,}".replace(",", ".")
            )
    konteks = " | ".join(ringkasan_h) or "Data historis belum tersedia."

    GAYA_DESC = {
        "formal_analitis":  "profesional dan analitis seperti analis keuangan senior",
        "santai_edukatif":  "santai tapi informatif, bahasa sehari-hari, edukatif",
        "berita_singkat":   "singkat padat jelas seperti reporter berita profesional",
        "energik_motivatif":"sangat energik dan semangat, banyak tanda seru",
        "percakapan_akrab": "akrab seperti ngobrol teman dekat, casual, pakai kata guys/bro",
    }
    gaya_desc = GAYA_DESC.get(NARASI_GAYA, GAYA_DESC["formal_analitis"])

    prompt = f"""Kamu adalah scriptwriter YouTube profesional.
Gaya narasi WAJIB: {gaya_desc}
Channel: {NAMA_CHANNEL}

BARIS PERTAMA HARUS PERSIS: "Halo sobat {NAMA_CHANNEL}," — tidak boleh ada teks apapun sebelumnya.

DATA HARI INI:
- Harga 1 gram: Rp {harga_skrg}
- Status: {status_harga} Rp {selisih_harga} vs kemarin
- Historis: {konteks}
- Data Antam: {data_harga[:2000]}

STRUKTUR (900-1000 KATA, konsisten gaya {NARASI_GAYA}):
1. Pembuka (100 kata): Sapa penonton, umumkan harga, status hari ini
2. Daftar harga (200 kata): Semua ukuran 0.5g hingga 1000g lengkap
3. Analisa & konteks global (300 kata): Historis + faktor ekonomi global
4. Edukasi & penutup (300 kata): Tips investasi + ajakan subscribe {NAMA_CHANNEL}

ATURAN KERAS:
- MULAI LANGSUNG "Halo sobat {NAMA_CHANNEL}," tanpa kata pengantar apapun
- Semua angka ditulis dengan HURUF
- Paragraf narasi murni, TANPA bullet/nomor/markdown
- Konsisten gaya {NARASI_GAYA} dari awal sampai akhir"""

    MODEL_CHAIN = [
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash",
        "gemini-2.5-flash-lite",
    ]

    for model_name in MODEL_CHAIN:
        for attempt in range(3):
            try:
                url_api = (
                    f"https://generativelanguage.googleapis.com/v1beta"
                    f"/models/{model_name}:generateContent"
                    f"?key={GEMINI_API_KEY}"
                )
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "maxOutputTokens": 8192,
                        "temperature": 0.9,
                    },
                }
                log(f"  -> {model_name} attempt {attempt+1}...")
                resp = requests.post(url_api, json=payload, timeout=90)

                if resp.status_code == 429:
                    t = int(resp.headers.get("Retry-After",
                                              (2**attempt) * 10))
                    log(f"  -> Rate limit. Tunggu {t}s...")
                    time.sleep(t)
                    continue
                if resp.status_code != 200:
                    log(f"  -> HTTP {resp.status_code}: {resp.text[:200]}")
                    break

                script_raw = (resp.json()["candidates"][0]
                              ["content"]["parts"][0]["text"].strip())

                # Bersihkan baris bocor
                baris, baru, skip = script_raw.split("\n"), [], True
                for idx, b in enumerate(baris):
                    bl = b.lower().strip()
                    if skip:
                        if bl.startswith("halo sobat"):
                            skip = False
                            baru.append(b)
                        elif idx > 4:
                            skip = False
                            baru.append(b)
                    elif not (bl.startswith("[judul]") or
                              bl.startswith("[script]")):
                        baru.append(b)
                script = "\n".join(baru).strip() or script_raw
                log(f"  -> ✅ Gemini OK ({len(script.split())} kata) "
                    f"via {model_name}")
                judul = _validasi_judul(judul, info, historis)
                return judul, script

            except Exception as e:
                if "429" not in str(e):
                    log(f"  -> Exception {model_name}: {e}")
                    break
                time.sleep((2**attempt) * 10)
        log(f"  -> {model_name} semua attempt gagal.")

    if not GEMINI_API_KEY:
        log("  -> GEMINI_API_KEY kosong! Set di GitHub Secrets.")

    log("  -> [FALLBACK] Pakai narasi template lokal...")
    narasi = _buat_narasi_fallback(info, harga_skrg,
                                    status_harga, selisih_harga)
    judul  = _validasi_judul(judul, info, historis)
    return judul, narasi
