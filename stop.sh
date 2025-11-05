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

# Hapus hanya file PID. Biarkan file log untuk tujuan debugging.
rm -f $PID_FILE

echo "Pembersihan selesai. File log tetap ada di $LOG_FILE."

# Selalu coba lepaskan wake lock untuk memastikan kebersihan
echo "Melepaskan Termux wake lock..."
termux-wake-unlock