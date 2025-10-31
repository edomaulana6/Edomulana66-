# Bot Pengunduh Media Telegram untuk Termux

Bot Telegram ini memungkinkan Anda untuk mengunduh video dan audio dari YouTube dan situs lain yang didukung oleh `yt-dlp`. Bot ini dirancang khusus untuk dijalankan dengan mudah di Termux.

## Fitur
- **Unduh dari URL**: Kirimkan link apa saja untuk mendapatkan pilihan unduhan (audio/video).
- **Pencarian Interaktif (Top 5)**: Gunakan `/search` untuk memulai pencarian. Bot akan menanyakan judul lagu yang Anda inginkan.
- **Unduh Lagu Interaktif**: Gunakan `/song` untuk memulai proses unduhan. Bot akan menanyakan judul lagu yang ingin diunduh.
- **Berjalan di Latar Belakang**: Dilengkapi dengan skrip untuk memulai dan menghentikan bot di latar belakang.

## Persiapan Awal di Termux
Pastikan Termux Anda sudah diperbarui.
```bash
pkg update && pkg upgrade
```

## Instalasi
1.  **Instal Git, Python, dan FFmpeg:**
    Bot ini memerlukan Python untuk berjalan dan FFmpeg untuk memproses file audio.
    ```bash
    pkg install git python ffmpeg
    ```

2.  **Dapatkan Kode Bot:**
    Gunakan `git clone` untuk menyalin semua file proyek ke Termux. Ganti `URL_REPOSITORI_ANDA` dengan URL Git yang sebenarnya.
    ```bash
    git clone URL_REPOSITORI_ANDA telegram-bot
    ```

3.  **Instal Library Python:**
    Pindah ke direktori bot yang baru saja dibuat, lalu instal dependensi dari file `requirements.txt`.
    ```bash
    cd telegram-bot
    pip install -r requirements.txt
    ```

## Konfigurasi (Cara Baru yang Lebih Mudah)
Anda tidak perlu lagi mengedit file secara manual. Cukup jalankan skrip setup interaktif.

1.  **Jalankan Skrip Setup:**
    Di direktori bot, jalankan perintah berikut:
    ```bash
    python setup.py
    ```

2.  **Masukkan Token Anda:**
    -   Skrip akan meminta Anda untuk memasukkan token bot.
    -   Dapatkan token Anda dari `@BotFather` di Telegram.
    -   Salin (copy) dan tempel (paste) token tersebut ke dalam terminal, lalu tekan Enter.

    Skrip akan secara otomatis membuat file `.env` yang benar untuk Anda. Proses selesai!

## Menjalankan Bot
Untuk kemudahan, telah disediakan skrip untuk menjalankan dan menghentikan bot.

1.  **Berikan Izin Eksekusi:**
    Sebelum menjalankan skrip untuk pertama kali, berikan izin eksekusi.
    ```bash
    chmod +x start.sh stop.sh
    ```

2.  **Mulai Bot:**
    Jalankan skrip `start.sh` untuk memulai bot di latar belakang.
    ```bash
    ./start.sh
    ```
    Anda akan melihat pesan bahwa bot telah dimulai.

3.  **Hentikan Bot:**
    Untuk menghentikan bot, jalankan skrip `stop.sh`.
    ```bash
    ./stop.sh
    ```

## Penting: Menjaga Termux Tetap Aktif
Termux dapat berhenti jika aplikasi ditutup oleh sistem Android. Untuk mencegah ini, jalankan `termux-wake-lock` di salah satu sesi Termux Anda. Ini akan menjaga Termux tetap berjalan di latar belakang.
