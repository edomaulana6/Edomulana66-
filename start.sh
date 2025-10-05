#!/bin/bash

# Nama file untuk menyimpan log dan ID proses
LOG_FILE="bot.log"
PID_FILE="bot.pid"
ENV_FILE=".env"

# --- Validasi Awal ---

# 1. Periksa apakah file .env ada
if [ ! -f "$ENV_FILE" ]; then
    echo "Kesalahan: File konfigurasi '$ENV_FILE' tidak ditemukan."
    echo "Silakan salin '.env.template' menjadi '.env' dan isi token Anda."
    exit 1
fi

# 2. Muat variabel dari .env dan periksa token
export $(grep -v '^#' $ENV_FILE | xargs)
if [ -z "$TELEGRAM_TOKEN" ] || [ "$TELEGRAM_TOKEN" == "GANTI_DENGAN_TOKEN_ANDA" ]; then
    echo "Kesalahan: TELEGRAM_TOKEN belum diatur di dalam file '$ENV_FILE'."
    exit 1
fi

# 3. Periksa apakah bot sudah berjalan
if [ -f $PID_FILE ]; then
    echo "Bot sudah berjalan dengan PID $(cat $PID_FILE). Hentikan dulu dengan ./stop.sh"
    exit 1
fi

echo "Memulai bot di latar belakang..."

# Jalankan bot menggunakan nohup, arahkan output ke log
nohup python bot.py > $LOG_FILE 2>&1 &

# Simpan ID Proses (PID) dari proses yang baru saja dimulai
echo $! > $PID_FILE

echo "Bot telah dimulai. Log disimpan di $LOG_FILE. PID: $(cat $PID_FILE)"
echo "Untuk menghentikan bot, jalankan ./stop.sh"