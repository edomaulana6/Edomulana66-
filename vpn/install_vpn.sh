#!/bin/bash

# --- Deteksi Lingkungan ---
IS_TERMUX=false
# Metode deteksi yang lebih andal untuk Termux
if [[ "$PREFIX" == *com.termux* ]]; then
    IS_TERMUX=true
fi

# --- Pemeriksaan Root yang Ditingkatkan ---
if [ "$(id -u)" -ne 0 ]; then
  if [ "$IS_TERMUX" = true ]; then
      # Periksa apakah tsu sudah terinstal
      if ! command -v tsu &> /dev/null; then
          echo "KESALAHAN: Perintah 'tsu' tidak ditemukan."
          echo "Harap instal dengan menjalankan: pkg install tsu"
          echo "Setelah itu, jalankan skrip ini lagi dengan 'tsu' terlebih dahulu."
      else
          echo "KESALAHAN: Skrip ini harus dijalankan sebagai root."
          echo "Silakan jalankan 'tsu' untuk menjadi root, lalu jalankan skrip ini lagi."
      fi
  else
      echo "KESALAHAN: Skrip ini harus dijalankan sebagai root. Coba jalankan dengan 'sudo'."
  fi
  exit 1
fi

# --- Variabel (dapat disesuaikan) ---
# Mencoba mendeteksi interface jaringan utama secara otomatis
SERVER_INTERFACE=$(ip route | grep default | awk '{print $5}' | head -n 1)
if [ -z "$SERVER_INTERFACE" ]; then
    echo "PERINGATAN: Tidak dapat mendeteksi interface jaringan utama."
    read -p "Masukkan nama interface jaringan utama Anda (misal: wlan0, eth0): " SERVER_INTERFACE
    if [ -z "$SERVER_INTERFACE" ]; then
        echo "KESALAHAN: Nama interface tidak boleh kosong."
        exit 1
    fi
fi
echo "INFO: Menggunakan interface jaringan: ${SERVER_INTERFACE}"

SERVER_PORT=51820
SERVER_PRIVATE_IP="10.0.0.1/24"
CLIENT_PRIVATE_IP="10.0.0.2/32"

# --- Instalasi ---
echo "INFO: Memperbarui daftar paket..."
if [ "$IS_TERMUX" = true ]; then
    pkg update
    echo "INFO: Menginstal paket untuk Termux (wireguard-tools, termux-exec, curl)..."
    pkg install -y wireguard-tools termux-exec curl
else
    apt-get update
    echo "INFO: Menginstal paket untuk Linux (wireguard, curl)..."
    apt-get install -y wireguard curl
fi

# --- Pembuatan Kunci ---
echo "INFO: Membuat kunci server dan klien..."
mkdir -p /etc/wireguard
chmod 700 /etc/wireguard

rm -f /etc/wireguard/server_private.key /etc/wireguard/server_public.key
rm -f /etc/wireguard/client_private.key /etc/wireguard/client_public.key

wg genkey | tee /etc/wireguard/server_private.key | wg pubkey > /etc/wireguard/server_public.key
wg genkey | tee /etc/wireguard/client_private.key | wg pubkey > /etc/wireguard/client_public.key

SERVER_PRIVATE_KEY=$(cat /etc/wireguard/server_private.key)
SERVER_PUBLIC_KEY=$(cat /etc/wireguard/server_public.key)
CLIENT_PRIVATE_KEY=$(cat /etc/wireguard/client_private.key)
CLIENT_PUBLIC_KEY=$(cat /etc/wireguard/client_public.key)

# --- Konfigurasi Server ---
echo "INFO: Membuat file konfigurasi server (/etc/wireguard/wg0.conf)..."
cat > /etc/wireguard/wg0.conf << EOL
[Interface]
Address = ${SERVER_PRIVATE_IP}
PrivateKey = ${SERVER_PRIVATE_KEY}
ListenPort = ${SERVER_PORT}
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o ${SERVER_INTERFACE} -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o ${SERVER_INTERFACE} -j MASQUERADE

[Peer]
# Klien 1
PublicKey = ${CLIENT_PUBLIC_KEY}
AllowedIPs = ${CLIENT_PRIVATE_IP}
EOL

# --- Konfigurasi Klien ---
SERVER_PUBLIC_IP=$(curl -s https://api.ipify.org)
if [ -z "${SERVER_PUBLIC_IP}" ]; then
    echo "PERINGATAN: Tidak dapat mendeteksi IP publik secara otomatis."
    echo "Harap edit 'client.conf' dan ganti '[SERVER_IP_PUBLIK]' secara manual."
    SERVER_PUBLIC_IP="[SERVER_IP_PUBLIK]"
fi

echo "INFO: Membuat file konfigurasi klien (client.conf)..."
cat > ./client.conf << EOL
[Interface]
PrivateKey = ${CLIENT_PRIVATE_KEY}
Address = ${CLIENT_PRIVATE_IP}
DNS = 1.1.1.1

[Peer]
PublicKey = ${SERVER_PUBLIC_KEY}
Endpoint = ${SERVER_PUBLIC_IP}:${SERVER_PORT}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
EOL

# --- Aktifkan IP Forwarding ---
echo "INFO: Mengaktifkan IP forwarding..."
if [ "$IS_TERMUX" = false ]; then
    sed -i '/net.ipv4.ip_forward=1/s/^#//' /etc/sysctl.conf
    sysctl -p
else
    # Di Termux, ini biasanya sudah aktif atau tidak dikontrol melalui sysctl.conf
    echo "INFO: Melewati konfigurasi sysctl untuk Termux."
fi

# --- Mulai Layanan WireGuard ---
echo "INFO: Memulai layanan WireGuard (wg-quick up wg0)..."
wg-quick up wg0

# Aktifkan saat boot untuk sistem Linux standar
if [ "$IS_TERMUX" = false ]; then
    echo "INFO: Mengaktifkan layanan agar berjalan saat boot..."
    systemctl enable wg-quick@wg0
fi

# --- Selesai ---
echo ""
echo "=========================================================="
echo "          🎉 Instalasi VPN WireGuard Selesai! 🎉"
echo "=========================================================="
echo ""
echo "-> Konfigurasi server telah disimpan di /etc/wireguard/wg0.conf"
echo "-> Konfigurasi klien telah disimpan di ./client.conf"
echo ""
echo "Langkah Selanjutnya:"
echo "1. Salin file 'client.conf' ke perangkat Anda."
echo "2. Instal aplikasi WireGuard dan impor file tersebut."
echo "3. Hubungkan VPN!"
echo ""
echo "Untuk memeriksa status VPN, gunakan perintah: wg show"
if [ "$IS_TERMUX" = true ]; then
    echo "PERINGATAN PENTING UNTUK TERMUX:"
    echo "Koneksi VPN akan berhenti jika Termux ditutup. Anda harus menjalankan 'wg-quick up wg0' setiap kali memulai ulang Termux."
fi
echo "=========================================================="
