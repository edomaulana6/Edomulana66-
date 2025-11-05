# Bot Downloader Media Telegram

Bot Telegram serbaguna yang dirancang untuk berjalan di Termux, mampu mengunduh media dari berbagai URL, meningkatkan kualitas foto, dan mengonversi resolusi video.

## Fitur

-   **Unduhan Langsung**: Unduh media dengan menyediakan argumen langsung ke perintah (misalnya, `/download <url>`).
-   **Pencarian Cepat**: Cari video menggunakan `/search <query>`.
-   **Fitur Interaktif**: Gunakan `/enhance_photo` dan `/convert_video` untuk alur kerja interaktif berbasis tombol.
-   **Indikator Memuat**: Umpan balik visual dengan stiker animasi selama proses unduhan.
-   **Instalasi Mudah**: Skrip penyiapan interaktif untuk konfigurasi token yang mudah.
-   **Notifikasi Status**: Menerima siaran saat bot online atau offline.
-   **Mode 24/7 di Termux**: Terintegrasi dengan `termux-wake-lock` untuk mencegah bot dimatikan oleh sistem Android.

## Prasyarat

-   **Python**: `pkg install python`
-   **FFmpeg**: `pkg install ffmpeg`
-   **Git**: `pkg install git`
-   **Termux API (untuk mode 24/7)**: `pkg install termux-api`

## Menjalankan di Termux (Mode 24/7)

Bot ini dirancang untuk berjalan terus-menerus di Termux. Skrip `start.sh` secara otomatis menggunakan `termux-wake-lock` untuk mencegah Android mematikan bot untuk menghemat baterai. Demikian pula, `stop.sh` akan melepaskan kunci tersebut.

Pastikan aplikasi Termux:API sudah terinstal dari F-Droid dan Anda telah menjalankan `pkg install termux-api` agar fitur ini berfungsi.

## Penyiapan Cepat

1.  **Klon Repositori**: `git clone <URL_REPO> && cd <NAMA_REPO>`
2.  **Instal Dependensi**: `pip install -r requirements.txt`
3.  **Jalankan Penyiapan**: `python setup.py` (dan masukkan token bot Anda)

## Menjalankan Bot

-   **Mulai**: `bash start.sh`
-   **Hentikan**: `bash stop.sh`

## Daftar Perintah

-   `/start`: Memulai interaksi dengan bot.
-   `/help`: Menampilkan daftar lengkap perintah.
-   `/search`: Memulai alur interaktif untuk mencari video/musik.
-   `/song`: Memulai alur interaktif untuk mengunduh sebuah lagu.
-   `/download`: Memulai alur interaktif untuk mengunduh dari URL.
-   `/enhance_photo`: Memulai alur interaktif untuk meningkatkan kualitas foto.
-   `/convert_video`: Memulai alur interaktif untuk mengubah resolusi video.
-   `/cancel`: Membatalkan operasi yang sedang berjalan.
