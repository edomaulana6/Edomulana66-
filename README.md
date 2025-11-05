# Bot Downloader Media Telegram

Bot Telegram serbaguna yang dirancang untuk berjalan di Termux, mampu mengunduh media dari berbagai URL, meningkatkan kualitas foto, dan mengonversi resolusi video.

## Fitur

-   **Unduhan Langsung**: Unduh media dengan menyediakan argumen langsung ke perintah (misalnya, `/download <url>`).
-   **Pencarian Cepat**: Cari video menggunakan `/search <query>`.
-   **Fitur Interaktif**: Gunakan `/enhance_photo` dan `/convert_video` untuk alur kerja interaktif berbasis tombol.
-   **Indikator Memuat**: Umpan balik visual dengan stiker animasi selama proses unduhan.
-   **Instalasi Mudah**: Skrip penyiapan interaktif untuk konfigurasi token yang mudah.
-   **Notifikasi Status**: Menerima siaran saat bot online atau offline.

## Prasyarat

-   **Python**: `pkg install python`
-   **FFmpeg**: `pkg install ffmpeg`
-   **Git**: `pkg install git`

## Penyiapan Cepat

1.  **Klon Repositori**: `git clone <URL_REPO> && cd <NAMA_REPO>`
2.  **Instal Dependensi**: `pip install -r requirements.txt`
3.  **Jalankan Penyiapan**: `python setup.py` (dan masukkan token bot Anda)

## Menjalankan Bot

-   **Mulai**: `bash start.sh`
-   **Hentikan**: `bash stop.sh`

## Daftar Perintah

-   `/start`: Memulai interaksi dengan bot.
-   `/help`: Menampilkan pesan bantuan ini.
-   `/search <query>`: Mencari video/musik berdasarkan kueri yang diberikan.
-   `/song`: Memulai alur interaktif untuk mengunduh sebuah lagu.
-   `/download <url>`: Mengunduh media dari URL yang diberikan.
-   `/enhance_photo`: Memulai alur interaktif untuk meningkatkan kualitas foto.
-   `/convert_video`: Memulai alur interaktif untuk mengubah resolusi video.
-   `/cancel`: Membatalkan operasi interaktif yang sedang berjalan.
