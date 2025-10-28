#!/bin/bash

# Port default untuk proxy
PORT=1080
# File untuk menyimpan PID dari proses proxy
PID_FILE="microsocks.pid"

# --- Instalasi ---
echo "INFO: Memeriksa apakah 'microsocks' sudah terinstal..."
if ! command -v microsocks &> /dev/null; then
    echo "INFO: 'microsocks' tidak ditemukan. Menginstal..."
    pkg update
    pkg install -y microsocks
    echo "INFO: Instalasi 'microsocks' selesai."
else
    echo "INFO: 'microsocks' sudah terinstal."
fi

# --- Konfigurasi ---
echo ""
echo "--- Pengaturan Otentikasi Proxy ---"
read -p "Masukkan username untuk proxy: " PROXY_USER
if [ -z "$PROXY_USER" ]; then
    echo "KESALAHAN: Username tidak boleh kosong."
    exit 1
fi

read -sp "Masukkan password untuk proxy: " PROXY_PASS
if [ -z "$PROXY_PASS" ]; then
    echo ""
    echo "KESALAHAN: Password tidak boleh kosong."
    exit 1
fi
echo ""
echo "------------------------------------"
echo ""

# --- Memulai Server ---
echo "INFO: Memulai server proxy SOCKS5 di latar belakang..."
# Opsi -i 0.0.0.0 agar bisa diakses dari perangkat lain di jaringan yang sama
# Opsi -p untuk port
# Opsi -u untuk username, -P untuk password
microsocks -i 0.0.0.0 -p $PORT -u "$PROXY_USER" -P "$PROXY_PASS" &

# Simpan PID dari proses yang baru saja dimulai
MICROSOCKS_PID=$!
echo $MICROSOCKS_PID > $PID_FILE

# --- Menampilkan Informasi Koneksi ---
echo "=========================================================="
echo "      ✅ Server Proxy SOCKS5 Berhasil Dimulai! ✅"
echo "=========================================================="
echo ""
echo "Gunakan informasi berikut untuk mengkonfigurasi perangkat lain:"
echo ""
# Mencari dan menampilkan semua alamat IP lokal perangkat
echo "  Alamat IP Server:"
ifconfig | grep "inet " | grep -v "127.0.0.1" | awk '{print $2}'
echo ""
echo "  Port:           ${PORT}"
echo "  Username:       ${PROXY_USER}"
echo "  Password:       (yang baru saja Anda masukkan)"
echo ""
echo "CATATAN: Pastikan perangkat lain Anda terhubung ke jaringan WiFi yang sama."
echo ""
echo "Untuk menghentikan server proxy, jalankan skrip 'stop_proxy.sh'"
echo "=========================================================="
