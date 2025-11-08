#!/bin/bash
LOG_FILE="bot.log"
PID_FILE="bot.pid"
ENV_FILE=".env"

if [ ! -f "$ENV_FILE" ]; then
    echo "Kesalahan: File '$ENV_FILE' tidak ditemukan. Jalankan 'python3 setup.py' dulu."
    exit 1
fi

export $(grep -v '^#' $ENV_FILE | xargs)
if [ -z "$TELEGRAM_TOKEN" ]; then
    echo "Kesalahan: TELEGRAM_TOKEN belum diatur di '$ENV_FILE'."
    exit 1
fi

if [ -f $PID_FILE ]; then
    echo "Bot sudah berjalan. Hentikan dulu dengan ./stop.sh"
    exit 1
fi

echo "Memulai bot di latar belakang..."
echo "Mengaktifkan Termux wake lock..."
termux-wake-lock

nohup python3 bot.py > $LOG_FILE 2>&1 &
echo $! > $PID_FILE

echo "Bot telah dimulai. Log: $LOG_FILE. PID: $(cat $PID_FILE)"
