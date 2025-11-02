# Bot Downloader Media Telegram

Bot Telegram serbaguna yang dirancang untuk berjalan di Termux, mampu mengunduh media dari berbagai URL, meningkatkan kualitas foto, dan mengonversi resolusi video.

## Fitur

-   **Pengunduhan Media Canggih**: Unduh audio atau video dari URL (YouTube, dll.) menggunakan perintah `/download`.
-   **Pencarian Interaktif**: Cari video menggunakan `/search` atau langsung unduh lagu teratas dengan `/song`.
-   **Peningkat Foto**: Tingkatkan kualitas gambar menggunakan perintah `/enhance_photo` untuk mempertajam atau menyesuaikan kontras.
-   **Konverter Video**: Ubah resolusi video ke ukuran yang lebih kecil (720p, 480p, 360p) dengan perintah `/convert_video`.
-   **Indikator Memuat**: Umpan balik visual dengan stiker animasi selama proses unduhan.
-   **Instalasi Mudah**: Skrip penyiapan interaktif untuk konfigurasi token yang mudah.

## Prasyarat

Sebelum Anda mulai, pastikan Anda telah menginstal yang berikut di lingkungan Termux Anda:

-   **Python**: `pkg install python`
-   **FFmpeg**: `pkg install ffmpeg` (diperlukan untuk konversi audio dan video)
-   **Git**: `pkg install git`

## Penyiapan Cepat

1.  **Klon Repositori**:
    ```bash
    git clone https://github.com/user/repo.git
    cd repo
    ```

2.  **Instal Dependensi**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Jalankan Skrip Penyiapan Interaktif**:
    Skrip ini akan meminta Anda untuk memasukkan token bot Telegram Anda dan secara otomatis membuat file `.env` yang diperlukan.
    ```bash
    python setup.py
    ```

## Cara Menjalankan Bot

-   **Memulai Bot**:
    Gunakan skrip `start.sh` untuk menjalankan bot di latar belakang.
    ```bash
    bash start.sh
    ```

-   **Menghentikan Bot**:
    Gunakan skrip `stop.sh` untuk menghentikan proses bot dengan aman.
    ```bash
    bash stop.sh
    ```

## Daftar Perintah

-   `/start`: Memulai interaksi dengan bot.
-   `/help`: Menampilkan pesan bantuan dengan daftar semua perintah yang tersedia.
-   `/search <query>`: Mencari video/musik berdasarkan kueri yang diberikan.
-   `/song <query>`: Langsung mengunduh lagu teratas yang cocok dengan kueri Anda.
-   `/download <url>`: Mengunduh media dari URL yang diberikan.
-   `/enhance_photo`: Memulai alur interaktif untuk meningkatkan kualitas foto.
-   `/convert_video`: Memulai alur interaktif untuk mengubah resolusi video.
-   `/cancel`: Membatalkan operasi interaktif yang sedang berjalan (misalnya, `/enhance_photo`).
