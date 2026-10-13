library(readr)
library(dplyr)
library(stringr)
library(ggplot2)
library(forcats)

# 1. Import Data
df <- read.csv("D:/Project Data Challenge/loker_banten.csv",
               sep = ";",
               fileEncoding = "UTF-8-BOM",
               stringsAsFactors = FALSE)

glimpse(df)
cat("Jumlah baris:", nrow(df), "| Jumlah kolom:", ncol(df), "\n")

# 2. Data Cleaning
## Cek missing value per kolom
print(colSums(is.na(df)))

## Cek baris duplikat
cat("\nJumlah link duplikat:", sum(duplicated(df$link)), "\n")
cat("Jumlah baris duplikat total:", sum(duplicated(df)), "\n")

## Rapikan whitespace berlebih pada kolom teks
df <- df %>%
  mutate(across(c(judul, lokasi, tipe_pekerjaan, level_pekerjaan,
                  kategori, deskripsi, tanggung_jawab),
                str_squish))

## Parsing kolom gaji jadi numerik
parse_gaji <- function(teks) {
  if (str_detect(teks, "Dirahasiakan|Negosiasi")) return(c(NA_real_, NA_real_))
  satuan <- if (str_detect(teks, "Ribu")) 1e3 else 1e6
  angka <- as.numeric(str_extract_all(teks, "[0-9.]+")[[1]])
  if (length(angka) >= 2) return(c(angka[1] * satuan, angka[2] * satuan))
  if (length(angka) == 1) return(c(angka[1] * satuan, angka[1] * satuan))
  return(c(NA_real_, NA_real_))
}

hasil_gaji <- t(sapply(df$gaji, parse_gaji))
df$gaji_min <- hasil_gaji[, 1]
df$gaji_max <- hasil_gaji[, 2]
df$gaji_tengah <- rowMeans(hasil_gaji, na.rm = FALSE)

cat("\nProporsi gaji tidak diketahui (Dirahasiakan/Negosiasi):",
    round(mean(is.na(df$gaji_tengah)) * 100, 2), "%\n")

## Cek nilai gaji hasil parsing yang janggal (deteksi dini kesalahan)
cat("\nRingkasan gaji_tengah setelah parsing:\n")
print(summary(df$gaji_tengah))

cat("\nLowongan dengan gaji_tengah ekstrem rendah/tinggi :\n")
print(df %>%
        filter(!is.na(gaji_tengah)) %>%
        arrange(gaji_tengah) %>%
        select(judul, gaji, gaji_tengah) %>%
        slice(c(1:3, (n() - 2):n())))

# 3. Exploratory Data Analysis (EDA)
## Distribusi variabel kategorikal
cat("\nDistribusi lokasi"); print(table(df$lokasi))
cat("\nDistribusi tipe_pekerjaan"); print(table(df$tipe_pekerjaan))
cat("\nDistribusi level_pekerjaan"); print(table(df$level_pekerjaan))
cat("\nDistribusi pendidikan"); print(table(df$pendidikan))
cat("\nJumlah nilai unik kategori:", n_distinct(df$kategori))

## Visualisasi distribusi kategorikal
ggplot(df, aes(x = fct_infreq(lokasi))) +
  geom_bar(fill = "#1F4E79") +
  coord_flip() +
  labs(title = "Distribusi Lowongan per Lokasi", x = NULL, y = "Jumlah Lowongan") +
  theme_minimal()

ggplot(df, aes(x = fct_infreq(tipe_pekerjaan))) +
  geom_bar(fill = "#1F4E79") +
  labs(title = "Distribusi Lowongan per Tipe Pekerjaan", x = NULL, y = "Jumlah Lowongan") +
  theme_minimal()

ggplot(df, aes(x = fct_infreq(level_pekerjaan))) +
  geom_bar(fill = "#1F4E79") +
  coord_flip() +
  labs(title = "Distribusi Lowongan per Level Pekerjaan", x = NULL, y = "Jumlah Lowongan") +
  theme_minimal()

## Distribusi dan visualisasi gaji
cat("\nStatistik deskriptif gaji_tengah (yang tidak dirahasiakan)")
print(summary(df$gaji_tengah))

ggplot(df %>% filter(!is.na(gaji_tengah)), aes(x = gaji_tengah)) +
  geom_histogram(bins = 30, fill = "#1F4E79") +
  labs(title = "Distribusi Gaji Lowongan (yang Dicantumkan)",
       x = "Gaji (Rupiah)", y = "Frekuensi") +
  theme_minimal()

## Hubungan awal antar variabel
ggplot(df %>% filter(!is.na(gaji_tengah)),
       aes(x = level_pekerjaan, y = gaji_tengah)) +
  geom_boxplot(fill = "#1F4E79", alpha = 0.6) +
  coord_flip() +
  labs(title = "Sebaran Gaji per Level Pekerjaan", x = NULL, y = "Gaji (Rupiah)") +
  theme_minimal()

# 4. Feature Engineering
ambil_bidang <- function(url) {
  bagian <- str_remove(url, "https://www.loker.id/")
  str_split(bagian, "/")[[1]][1]
}

df$bidang_industri <- sapply(df$link, ambil_bidang)
df$bidang_industri <- factor(df$bidang_industri)

cat("\nJumlah bidang industri unik setelah derivasi:", nlevels(df$bidang_industri), "\n")
print(sort(table(df$bidang_industri), decreasing = TRUE))

ggplot(df, aes(x = fct_infreq(bidang_industri))) +
  geom_bar(fill = "#1F4E79") +
  coord_flip() +
  labs(title = "Distribusi Lowongan per Bidang Industri (Hasil Derivasi)",
       x = NULL, y = "Jumlah Lowongan") +
  theme_minimal()

## Sederhanakan pendidikan jadi satu nilai ordinal
rank_pendidikan <- c(
  "SMA / SMK / STM"  = 1,
  "Diploma/D1/D2/D3" = 2,
  "Sarjana / S1"     = 3,
  "Master / S2"      = 4
)

ambil_pendidikan_tertinggi <- function(x) {
  bagian <- str_trim(str_split(x, "\\|")[[1]])
  skor <- rank_pendidikan[bagian]
  skor <- skor[!is.na(skor)]
  if (length(skor) == 0) return(NA_character_)
  names(skor)[which.max(skor)]
}

df$pendidikan_tertinggi <- sapply(df$pendidikan, ambil_pendidikan_tertinggi)
df$pendidikan_tertinggi <- factor(df$pendidikan_tertinggi,
                                  levels = names(rank_pendidikan),
                                  ordered = TRUE)

cat("\nDistribusi pendidikan tertinggi (hasil derivasi):\n")
print(table(df$pendidikan_tertinggi))

## Tetapkan skala/tipe tiap variabel
urutan_level_kerja <- c("Junior / Entry Level", "Staff / Officer",
                        "Supervisor / Coordinator", "Manager / Assistant Manager",
                        "CEO / GM / Director / Senior Manager")

df$level_pekerjaan <- factor(df$level_pekerjaan,
                             levels = urutan_level_kerja,
                             ordered = TRUE)

df$lokasi         <- factor(df$lokasi)
df$tipe_pekerjaan <- factor(df$tipe_pekerjaan)

## Susun data frame fitur final
df_fitur <- df %>%
  transmute(
    link,                     
    judul,
    lokasi,
    tipe_pekerjaan,
    level_pekerjaan,
    bidang_industri,
    pendidikan_tertinggi,
    gaji_tengah
  )

# 5. Data siap analisis
str(df_fitur)
cat("\nJumlah baris:", nrow(df_fitur), "\n")
cat("Missing value tersisa :\n")
print(colSums(is.na(df_fitur)))