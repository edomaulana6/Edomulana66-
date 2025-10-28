#!/bin/bash

# Pastikan skrip dijalankan sebagai root
if [ "$(id -u)" -ne 0 ]; then
  echo "Skrip ini harus dijalankan sebagai root. Coba jalankan dengan 'sudo'." >&2
  exit 1
fi

# Pastikan file konfigurasi server ada
if [ ! -f /etc/wireguard/wg0.conf ]; then
    echo "Kesalahan: File konfigurasi server /etc/wireguard/wg0.conf tidak ditemukan."
    echo "Pastikan Anda telah menjalankan skrip instalasi terlebih dahulu."
    exit 1
fi

# Minta nama untuk klien baru
read -p "Masukkan nama untuk klien VPN baru (contoh: hp_budi, laptop_kantor): " CLIENT_NAME

# Validasi input nama klien
if [ -z "$CLIENT_NAME" ]; then
    echo "Kesalahan: Nama klien tidak boleh kosong."
    exit 1
fi
# Hapus spasi dan karakter spesial untuk nama file yang aman
SAFE_CLIENT_NAME=$(echo "$CLIENT_NAME" | tr -dc 'a-zA-Z0-9_-')

# --- Logika Penentuan IP ---
# Temukan IP terakhir yang digunakan di wg0.conf
LAST_IP=$(grep 'AllowedIPs' /etc/wireguard/wg0.conf | tail -n 1 | awk -F '[ ./]' '{print $6}')
# Jika tidak ada IP sebelumnya, mulai dari 2
if [ -z "$LAST_IP" ]; then
    # Jika server (10.0.0.1) adalah satu-satunya entri, IP klien pertama adalah 2
    LAST_IP=1
fi

# IP baru adalah IP terakhir + 1
NEW_IP_OCTET=$((LAST_IP + 1))
CLIENT_PRIVATE_IP="10.0.0.${NEW_IP_OCTET}/32"

echo "INFO: IP internal berikutnya yang tersedia adalah 10.0.0.${NEW_IP_OCTET}"

# --- Pembuatan Kunci Klien ---
echo "INFO: Membuat kunci privat dan publik untuk klien '${SAFE_CLIENT_NAME}'..."
CLIENT_PRIVATE_KEY=$(wg genkey)
CLIENT_PUBLIC_KEY=$(echo "${CLIENT_PRIVATE_KEY}" | wg pubkey)

# --- Pembuatan Konfigurasi Klien ---
SERVER_PUBLIC_KEY=$(cat /etc/wireguard/server_public.key)
SERVER_PUBLIC_IP=$(curl -s https://api.ipify.org)
SERVER_PORT=$(grep 'ListenPort' /etc/wireguard/wg0.conf | awk '{print $3}')

if [ -z "${SERVER_PUBLIC_IP}" ]; then
    echo "PERINGATAN: Tidak dapat mendeteksi IP publik server secara otomatis."
    SERVER_PUBLIC_IP="[SERVER_IP_PUBLIK]"
fi

# Buat file konfigurasi di direktori saat ini
CLIENT_CONFIG_FILE="${SAFE_CLIENT_NAME}.conf"
echo "INFO: Membuat file konfigurasi klien (${CLIENT_CONFIG_FILE})..."
cat > ./${CLIENT_CONFIG_FILE} << EOL
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

# --- Tambahkan Klien ke Server ---
echo "INFO: Menambahkan klien baru ke konfigurasi server..."
cat >> /etc/wireguard/wg0.conf << EOL

[Peer]
# Klien: ${CLIENT_NAME}
PublicKey = ${CLIENT_PUBLIC_KEY}
AllowedIPs = ${CLIENT_PRIVATE_IP}
EOL

# --- Terapkan Perubahan ---
echo "INFO: Menerapkan konfigurasi baru ke WireGuard..."
wg syncconf wg0 <(wg-quick strip wg0)

# --- Selesai ---
echo ""
echo "=========================================================="
echo "          ✅ Klien VPN Baru Berhasil Ditambahkan! ✅"
echo "=========================================================="
echo ""
echo "-> Nama Klien: ${CLIENT_NAME}"
echo "-> Konfigurasi klien telah disimpan di ./${CLIENT_CONFIG_FILE}"
echo ""
echo "Langkah Selanjutnya:"
echo "1. Salin file '${CLIENT_CONFIG_FILE}' ke perangkat baru."
echo "2. Impor file tersebut ke aplikasi WireGuard di perangkat itu."
echo "3. Hubungkan VPN!"
echo ""
echo "Status VPN saat ini:"
wg show
echo "=========================================================="
