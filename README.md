# Bot Pengunduh Media Telegram untuk Termux

Bot Telegram ini memungkinkan Anda untuk mengunduh video dan audio dari YouTube dan situs lain yang didukung oleh `yt-dlp`. Bot ini dirancang khusus untuk dijalankan dengan mudah di Termux.

## Fitur
- **Unduh dari URL**: Kirimkan link apa saja untuk mendapatkan pilihan unduhan (audio/video).
- **Pencarian Interaktif (Top 5)**: Gunakan `/search` untuk memulai alur percakapan. Bot akan menanyakan nama artis dan judul lagu sebelum menampilkan 5 hasil teratas.
- **Unduh Lagu Interaktif**: Gunakan `/song` untuk memulai alur percakapan yang akan memandu Anda untuk mengunduh audio dari hasil pencarian teratas.
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
    Pindah ke direktori bot yang baru saja dibuat, lalu instal dependensi yang diperlukan.
    ```bash
    cd telegram-bot
    pip install python-telegram-bot "python-telegram-bot[ext]" --pre
    pip install git+https://github.com/yt-dlp/yt-dlp.git
    ```

## Konfigurasi
1.  **Dapatkan Token Bot:**
    - Buka Telegram dan cari `@BotFather`.
    - Buat bot baru dengan mengirimkan perintah `/newbot`.
    - Ikuti instruksinya, dan BotFather akan memberi Anda sebuah **token**. Token ini terlihat seperti `1234567890:ABCdEfgHiJKLmnOpqRsTUVwxyZ`.

2.  **Atur Token Anda:**
    Anda perlu mengatur token ini sebagai variabel lingkungan. Cara termudah adalah dengan menambahkannya ke skrip `start.sh`. Buka file `start.sh` dan edit baris berikut dengan token Anda:
    ```bash
    export TELEGRAM_TOKEN='GANTI_DENGAN_TOKEN_ANDA'
    ```

3.  **(Opsional) Atur Perintah Bot:**
    Untuk membuat bot lebih mudah digunakan, atur daftar perintah di `@BotFather`.
    - Kirim perintah `/mybots`, pilih bot Anda, lalu pilih "Edit Bot" -> "Edit Commands".
    - Salin dan tempel teks berikut:
    ```
    start - ✨ Memulai bot
    help - 🤔 Menampilkan bantuan
    search - 🔎 Memulai pencarian interaktif (5 teratas)
    song - 🎵 Memulai unduhan lagu interaktif
    cancel - ❌ Membatalkan operasi saat ini
    ```

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