# 🏢 Analisis Segmentasi Pasar Lowongan Kerja Banten (loker.id)

Repository ini berisi proyek *end-to-end* yang mencakup pengumpulan data (*web scraping*) dan analisis segmentasi pasar lowongan kerja di wilayah Banten. Data dikumpulkan secara langsung dari situs Loker.id berdasarkan lowongan yang tayang pada periode September 2026. Analisis data dilakukan dengan pendekatan *clustering* menggunakan algoritma Partitioning Around Medoids (PAM) dan Jarak Gower untuk menangani dataset bertipe campuran.

## 🎯 Tujuan Penelitian
Melakukan segmentasi pasar lowongan kerja untuk menemukan profil klaster pekerjaan di Banten berdasarkan enam variabel utama: Lokasi, Tipe pekerjaan, Level pekerjaan, Bidang industri, Pendidikan tertinggi, dan Gaji.

## 🛠️ Teknologi & Library yang Digunakan

**1. Pengumpulan Data (Web Scraping)**
*   **Bahasa:** Python
*   **Library:** `requests` (mengambil halaman HTML), `BeautifulSoup` (membaca isi HTML), `pandas` (menyusun tabel dan ekspor CSV), serta `urllib.robotparser` (mematuhi aturan robots.txt).

**2. Pra-pemrosesan & Analisis Data (Clustering)**
*   **Bahasa:** R
*   **Library:** `readr`, `dplyr`, `stringr`, `forcats`, `ggplot2` (untuk prapemrosesan dan EDA), serta `cluster` dan `factoextra` (untuk tahap klasterisasi).

## 📊 Metodologi Analisis

1.  **Pengumpulan Data:** Menggunakan teknik sensus pada seluruh lowongan kerja aktif (1.108 lowongan dari 53 halaman listing) yang tayang publik pada 29 September 2026. Skrip dilengkapi sistem *retry* otomatis dan jeda 1,5 detik untuk mematuhi etika *scraping*.
2.  **Pra-pemrosesan Data (Data Preparation):** Meliputi pembersihan duplikat, penghapusan spasi berlebih, perhitungan nilai tengah rentang gaji, penyederhanaan urutan level jenjang kerja, hingga derivasi variabel (seperti ekstraksi "Bidang Industri" langsung dari URL lowongan).
3.  **Perhitungan Jarak Gower:** Digunakan secara khusus karena data memiliki tipe variabel campuran, yaitu kombinasi dari data nominal, ordinal, dan numerik rasio secara bersamaan.
4.  **Klasterisasi PAM (K-Medoids):** Menggunakan rata-rata *Silhouette width* untuk menentukan jumlah klaster ($k$) yang paling optimal. Algoritma PAM dipilih karena langsung bekerja pada matriks jarak dan menggunakan data lowongan asli (medoid) sebagai pusat klasternya, sehingga kebal terhadap pencilan.
5.  **Evaluasi & Profiling:** Memvalidasi klaster dengan plot Silhouette dan melakukan visualisasi menggunakan Metric MDS (PCoA).
