#!/bin/bash

# Pastikan skrip dijalankan sebagai root
if [ "$(id -u)" -ne 0 ]; then
  echo "Skrip ini harus dijalankan sebagai root. Coba jalankan dengan 'sudo'." >&2
  exit 1
fi

# --- Variabel (dapat disesuaikan) ---
# Ganti dengan nama network interface utama Anda jika berbeda (misal: eth0, ens3)
# Gunakan `ip a` atau `ifconfig` untuk memeriksa
SERVER_INTERFACE="eth0"
# Ganti dengan port yang Anda inginkan
SERVER_PORT=51820
# Alamat IP internal untuk server VPN
SERVER_PRIVATE_IP="10.0.0.1/24"
# Alamat IP internal untuk klien pertama
CLIENT_PRIVATE_IP="10.0.0.2/32"

# --- Instalasi ---
echo "INFO: Memperbarui daftar paket..."
apt-get update

echo "INFO: Menginstal WireGuard dan paket pendukung..."
apt-get install -y wireguard resolvconf

# --- Pembuatan Kunci ---
echo "INFO: Membuat kunci server dan klien..."
# Buat direktori konfigurasi
mkdir -p /etc/wireguard
# Atur izin yang aman
chmod 700 /etc/wireguard

# Hapus kunci lama jika ada untuk menghindari konflik
rm -f /etc/wireguard/server_private.key /etc/wireguard/server_public.key
rm -f /etc/wireguard/client_private.key /etc/wireguard/client_public.key

# Buat kunci baru
wg genkey | tee /etc/wireguard/server_private.key | wg pubkey > /etc/wireguard/server_public.key
wg genkey | tee /etc/wireguard/client_private.key | wg pubkey > /etc/wireguard/client_public.key

# Simpan nilai kunci ke dalam variabel
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
# Dapatkan alamat IP publik server
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
DNS = 1.1.1.1 # DNS resolver dari Cloudflare

[Peer]
PublicKey = ${SERVER_PUBLIC_KEY}
Endpoint = ${SERVER_PUBLIC_IP}:${SERVER_PORT}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
EOL

# --- Aktifkan IP Forwarding ---
echo "INFO: Mengaktifkan IP forwarding..."
sed -i '/net.ipv4.ip_forward=1/s/^#//' /etc/sysctl.conf
sysctl -p

# --- Mulai Layanan WireGuard ---
echo "INFO: Memulai dan mengaktifkan layanan WireGuard (wg-quick@wg0)..."
systemctl enable wg-quick@wg0
systemctl start wg-quick@wg0

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
echo "1. Salin file 'client.conf' ke perangkat Anda (HP/PC)."
echo "2. Instal aplikasi WireGuard di perangkat Anda."
echo "3. Impor file 'client.conf' ke dalam aplikasi."
echo "4. Hubungkan VPN!"
echo ""
echo "Untuk memeriksa status VPN di server, gunakan perintah: wg show"
echo "=========================================================="
