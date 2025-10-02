#!/bin/bash

# Nama file tempat ID proses disimpan
PID_FILE="bot.pid"
LOG_FILE="bot.log"

echo "Mencoba menghentikan bot..."

# Periksa apakah file PID ada
if [ ! -f $PID_FILE ]; then
    echo "Bot sepertinya tidak berjalan (file $PID_FILE tidak ditemukan)."
    exit 1
fi

# Baca PID dari file
PID=$(cat $PID_FILE)

# Periksa apakah proses dengan PID tersebut benar-benar ada
if ps -p $PID > /dev/null; then
    # Hentikan proses
    kill $PID
    echo "Proses bot dengan PID $PID telah dihentikan."
else
    echo "Proses dengan PID $PID tidak ditemukan, mungkin sudah berhenti."
fi

# Hapus file PID, log, dan persistensi
rm -f $PID_FILE
rm -f $LOG_FILE
rm -f bot_persistence

echo "Pembersihan selesai."