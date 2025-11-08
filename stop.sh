#!/bin/bash
PID_FILE="bot.pid"

echo "Mencoba menghentikan bot..."

if [ ! -f $PID_FILE ]; then
    echo "Bot sepertinya tidak berjalan (file $PID_FILE tidak ditemukan)."
else
    PID=$(cat $PID_FILE)
    if ps -p $PID > /dev/null; then
        kill $PID
        echo "Proses bot dengan PID $PID telah dihentikan."
    else
        echo "Proses dengan PID $PID tidak ditemukan."
    fi
    rm -f $PID_FILE
fi

echo "Melepaskan Termux wake lock..."
termux-wake-unlock
