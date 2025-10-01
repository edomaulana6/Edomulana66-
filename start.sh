#!/bin/bash

# --- KONFIGURASI ---
# Ganti 'GANTI_DENGAN_TOKEN_ANDA' dengan token bot Telegram Anda yang sebenarnya.
export TELEGRAM_TOKEN='GANTI_DENGAN_TOKEN_ANDA'

# Nama file untuk menyimpan log dan ID proses
LOG_FILE="bot.log"
PID_FILE="bot.pid"

# Periksa apakah bot sudah berjalan
if [ -f $PID_FILE ]; then
    echo "Bot sudah berjalan dengan PID $(cat $PID_FILE). Hentikan dulu dengan ./stop.sh"
    exit 1
fi

# Periksa apakah token sudah diatur
if [ "$TELEGRAM_TOKEN" == "GANTI_DENGAN_TOKEN_ANDA" ]; then
    echo "Kesalahan: Token bot belum diatur. Silakan edit file start.sh dan masukkan token Anda."
    exit 1
fi

echo "Memulai bot di latar belakang..."

# Jalankan bot menggunakan nohup dan simpan output ke log
# & menjalankan proses di latar belakang
nohup python bot.py > $LOG_FILE 2>&1 &

# Simpan ID Proses (PID) dari proses yang baru saja dimulai
echo $! > $PID_FILE

echo "Bot telah dimulai. Log disimpan di $LOG_FILE. PID: $(cat $PID_FILE)"
echo "Untuk menghentikan bot, jalankan ./stop.sh"