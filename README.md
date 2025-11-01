# Bot Pengunduh Media Telegram untuk Termux

Bot Telegram ini memungkinkan Anda untuk mengunduh video, audio, dan gambar dari berbagai sumber. Bot ini dirancang khusus untuk dijalankan dengan mudah di Termux.

## Fitur
- **/search**: Mencari 5 video YouTube teratas (durasi di bawah 10 menit) berdasarkan judul.
- **/song**: Mencari dan mengunduh lagu teratas dari YouTube sebagai file MP3.
- **/download**: Memulai proses unduhan dari URL (mendukung video dari yt-dlp dan gambar langsung).

## Instalasi & Setup

1.  **Persiapan di Termux:**
    ```bash
    pkg update && pkg upgrade
    pkg install git python ffmpeg
    ```

2.  **Dapatkan Kode Bot:**
    ```bash
    git clone URL_REPOSITORI_ANDA telegram-bot
    cd telegram-bot
    ```

3.  **Instal Dependensi Python:**
    Skrip ini akan menginstal `yt-dlp` versi terbaru langsung dari GitHub.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Konfigurasi Token Bot (Cara Mudah):**
    Jalankan skrip setup dan masukkan token bot Anda saat diminta.
    ```bash
    python setup.py
    ```

5.  **(Opsional) Atur Perintah Bot di @BotFather:**
    ```
    start - ✨ Memulai bot
    help - 🤔 Menampilkan bantuan
    search - 🔎 Cari video
    song - 🎵 Unduh lagu
    download - 🔗 Unduh dari URL
    cancel - ❌ Batalkan operasi
    ```

## Menjalankan Bot

1.  **Berikan Izin Eksekusi:**
    ```bash
    chmod +x start.sh stop.sh
    ```

2.  **Mulai & Hentikan Bot:**
    ```bash
    ./start.sh
    ./stop.sh
    ```

**Penting:** Gunakan `termux-wake-lock` untuk menjaga Termux tetap aktif di latar belakang.
