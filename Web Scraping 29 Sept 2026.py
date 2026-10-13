import time
import urllib.robotparser as urobot
from urllib.parse import urljoin, urlsplit

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://www.loker.id"
LISTING_BASE = f"{BASE_URL}/lokasi-pekerjaan/banten"
TOTAL_HALAMAN = 53          
JEDA_ANTAR_REQUEST = 1.5    
NAMA_FILE_OUTPUT = "loker_banten.csv"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
}

# Pola URL halaman
POLA_HALAMAN = "{base}/page/{n}"

# Label
LABEL_FIELDS = ["Lokasi", "Tipe Pekerjaan", "Level Pekerjaan", "Fungsi", "Pendidikan", "Gaji"]

# Nama kolom
NAMA_KOLOM = {"Fungsi": "kategori"}

# Teks penanda akhir sebuah bagian di halaman detail
HEADING_TANGGUNG_JAWAB = "Tanggung Jawab Pekerjaan"
HEADING_KUALIFIKASI = "Kualifikasi Pekerjaan"
PENANDA_AKHIR = ("Laporkan lowongan", "Loker Serupa")

# Session dengan retry otomatis (timeout/limit/server error) supaya tidak mudah gagal.
SESI = requests.Session()
SESI.headers.update(HEADERS)
SESI.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            respect_retry_after_header=True,
        )
    ),
)


def cek_robots():
    """Cek apakah scraping halaman ini diizinkan robots.txt."""
    try:
        resp = SESI.get(f"{BASE_URL}/robots.txt", timeout=15)
    except requests.RequestException as e:
        print(f"Peringatan: robots.txt tidak bisa dibaca ({e}). Lanjut dengan asumsi diizinkan.")
        return True

    if resp.status_code != 200:
        print(f"robots.txt tidak tersedia (HTTP {resp.status_code}). Lanjut dengan asumsi diizinkan.")
        return True

    rp = urobot.RobotFileParser()
    rp.parse(resp.text.splitlines())
    izin = rp.can_fetch("*", LISTING_BASE) and rp.can_fetch(
        "*", POLA_HALAMAN.format(base=LISTING_BASE, n=2)
    )
    print(f"Robots.txt mengizinkan scraping halaman ini: {izin}")
    return izin


def ambil_link_dari_halaman(nomor_halaman):
    """Ambil semua link detail lowongan (berakhiran .html) dari satu halaman listing."""
    if nomor_halaman == 1:
        url = LISTING_BASE
    else:
        url = POLA_HALAMAN.format(base=LISTING_BASE, n=nomor_halaman)

    try:
        resp = SESI.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  Gagal ambil halaman {nomor_halaman}: {e}")
        return []

    soup = BeautifulSoup(resp.content, "html.parser")


    # Ubah ke URL absolut dengan urljoin.
    link_list = []
    sudah_ada = set()
    for tag in soup.select('a[href*=".html"]'):
        bagian = urlsplit(urljoin(BASE_URL + "/", tag.get("href", "").strip()))
        if not bagian.path.endswith(".html"):
            continue
        # buang query dan fragment supaya link tidak terhitung ganda
        href = f"{bagian.scheme}://{bagian.netloc}{bagian.path}"
        if href.startswith(BASE_URL) and href not in sudah_ada:
            sudah_ada.add(href)
            link_list.append(href)

    return link_list


def ambil_nilai_setelah_label(baris, label, label_lainnya):
    try:
        idx_label = baris.index(label)
    except ValueError:
        return None

    hasil = []
    for i in range(idx_label + 1, len(baris)):
        teks = baris[i]
        if teks in label_lainnya or teks.startswith(
            (HEADING_TANGGUNG_JAWAB, HEADING_KUALIFIKASI) + PENANDA_AKHIR
        ):
            break
        if label == "Pendidikan" and len(teks) > 60:
            break
        hasil.append(teks)
        if label != "Pendidikan":
            break

    return " | ".join(hasil) if hasil else None


def ambil_detail_lowongan(link):
    time.sleep(JEDA_ANTAR_REQUEST)

    try:
        resp = SESI.get(link, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"    Gagal ambil detail {link}: {e}")
        return None

    try:
        soup = BeautifulSoup(resp.content, "html.parser")

        # Buang isi <script>/<style> supaya tidak ikut masuk ke teks halaman
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        h1 = soup.find("h1")
        judul = h1.get_text(strip=True) if h1 else None

        teks_lengkap = soup.get_text(separator="\n")
        baris = [b.strip() for b in teks_lengkap.split("\n") if b.strip() != ""]

        data = {"link": link, "judul": judul}

        for label in LABEL_FIELDS:
            label_lainnya = [l for l in LABEL_FIELDS if l != label]
            kolom = NAMA_KOLOM.get(label, label.lower().replace(" ", "_"))
            data[kolom] = ambil_nilai_setelah_label(baris, label, label_lainnya)

        # Bukan halaman lowongan kalau tidak ada satu pun field yang ditemukan
        if not any(data[NAMA_KOLOM.get(l, l.lower().replace(" ", "_"))] for l in LABEL_FIELDS):
            print(f"    Dilewati (bukan halaman lowongan): {link}")
            return None

        # Posisi heading bagian (None kalau tidak ada di halaman ini)
        idx_tj = next((i for i, b in enumerate(baris) if b.startswith(HEADING_TANGGUNG_JAWAB)), None)
        idx_kual = next((i for i, b in enumerate(baris) if b.startswith(HEADING_KUALIFIKASI)), None)

        # Posisi awal deskripsi
        idx_label_terakhir = max(
            (baris.index(l) for l in LABEL_FIELDS if l in baris),
            default=None,
        )
        idx_mulai = (idx_label_terakhir + 2) if idx_label_terakhir is not None else 0

        # Batas akhir isi halaman
        titik_cari = max(i for i in (idx_kual, idx_tj, idx_mulai) if i is not None)
        idx_akhir = next(
            (i for i, b in enumerate(baris) if i > titik_cari and b.startswith(PENANDA_AKHIR)),
            len(baris),
        )

        # Deskripsi
        batas_deskripsi = next((i for i in (idx_tj, idx_kual) if i is not None), idx_akhir)
        deskripsi = " ".join(baris[idx_mulai:batas_deskripsi]).strip()
        data["deskripsi"] = deskripsi if deskripsi else None

        # Tanggung jawab
        if idx_tj is not None:
            batas_tj = idx_kual if (idx_kual is not None and idx_kual > idx_tj) else idx_akhir
            tanggung_jawab = "; ".join(baris[idx_tj + 1:batas_tj])
        else:
            tanggung_jawab = None
        data["tanggung_jawab"] = tanggung_jawab if tanggung_jawab else None

        return data

    except Exception as e:  # satu halaman bermasalah tidak boleh menghentikan seluruh proses
        print(f"    Gagal memproses detail {link}: {e}")
        return None


def simpan_csv(data_lowongan):
    """Simpan data ke CSV. Kalau file sedang terbuka (mis. di Excel), pakai nama cadangan."""
    df = pd.DataFrame(data_lowongan)
    try:
        df.to_csv(NAMA_FILE_OUTPUT, index=False, encoding="utf-8-sig")
        nama_akhir = NAMA_FILE_OUTPUT
    except PermissionError:
        nama_akhir = time.strftime("loker_banten_%Y%m%d_%H%M%S.csv")
        df.to_csv(nama_akhir, index=False, encoding="utf-8-sig")
        print(f"  {NAMA_FILE_OUTPUT} sedang terbuka/terkunci, disimpan sebagai {nama_akhir}")
    return nama_akhir


def main():
    if not cek_robots():
        print("Scraping tidak diizinkan menurut robots.txt. Berhenti.")
        return

    print("TAHAP 1: Mengumpulkan link lowongan dari semua halaman listing")
    semua_link = []
    try:
        for halaman in range(1, TOTAL_HALAMAN + 1):
            link_halaman = ambil_link_dari_halaman(halaman)
            semua_link.extend(link_halaman)
            print(f"Halaman {halaman}/{TOTAL_HALAMAN} - {len(link_halaman)} lowongan ditemukan")
            time.sleep(JEDA_ANTAR_REQUEST)
    except KeyboardInterrupt:
        print("\nDihentikan manual. Lanjut memproses link yang sudah terkumpul.")

    semua_link = list(dict.fromkeys(semua_link))  # buang duplikat, jaga urutan
    print(f"\nTotal link lowongan unik: {len(semua_link)}\n")

    print("TAHAP 2: Mengambil detail tiap lowongan")
    data_lowongan = []
    try:
        for i, link in enumerate(semua_link, start=1):
            detail = ambil_detail_lowongan(link)
            if detail:
                data_lowongan.append(detail)
            if i % 25 == 0 or i == len(semua_link):
                print(f"  Progres: {i}/{len(semua_link)} lowongan diproses")
    except KeyboardInterrupt:
        print("\nDihentikan manual. Data yang sudah terkumpul tetap disimpan.")

    print(f"\nBerhasil mengambil {len(data_lowongan)} dari {len(semua_link)} lowongan")

    if not data_lowongan:
        print("Tidak ada data yang berhasil diambil, CSV tidak dibuat.")
        return

    nama_akhir = simpan_csv(data_lowongan)
    print(f"\nSelesai! Data tersimpan di {nama_akhir}")


if __name__ == "__main__":
    main()