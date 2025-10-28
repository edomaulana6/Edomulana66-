#!/bin/bash

PID_FILE="microsocks.pid"

if [ -f "$PID_FILE" ]; then
    PID_TO_KILL=$(cat $PID_FILE)
    if [ -n "$PID_TO_KILL" ]; then
        echo "INFO: Menghentikan proses proxy SOCKS5 dengan PID: $PID_TO_KILL..."
        # Gunakan kill untuk menghentikan proses
        kill $PID_TO_KILL
        # Hapus file PID setelah proses dihentikan
        rm $PID_FILE
        echo "INFO: Server proxy telah dihentikan."
    else
        echo "PERINGATAN: File PID ada tetapi kosong. Tidak ada yang bisa dihentikan."
    fi
else
    echo "PERINGATAN: File PID tidak ditemukan. Sepertinya server proxy tidak sedang berjalan (atau file PID dihapus secara manual)."
fi
