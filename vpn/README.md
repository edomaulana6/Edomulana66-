# Skrip Instalasi & Manajemen VPN WireGuard

Proyek ini menyediakan dua skrip Bash untuk mempermudah proses pembuatan dan pengelolaan server VPN WireGuard pribadi Anda. Skrip ini dirancang agar kompatibel dengan **server berbasis Debian/Ubuntu** dan **Termux di Android**.

-   `install_vpn.sh`: Menginstal semua dependensi, membuat konfigurasi awal, dan menghasilkan file konfigurasi untuk klien pertama.
-   `add_user.sh`: Menambahkan pengguna (klien) baru ke server VPN yang sudah ada.

## Persyaratan
-   **Untuk Server Linux:** Sebuah server yang menjalankan Debian atau Ubuntu dengan akses `sudo`.
-   **Untuk Termux:** Aplikasi Termux di Android dengan paket `tsu` terinstal untuk akses root (`pkg install tsu`).

---

## Panduan Instalasi Awal

Proses ini hanya perlu dilakukan sekali saat pertama kali menyiapkan server.

### Langkah 1: Persiapan

1.  **Salin Skrip**
    Salin file `install_vpn.sh` dan `add_user.sh` ke direktori home di server atau Termux Anda.

2.  **Berikan Izin Eksekusi**
    Buka terminal dan berikan izin agar skrip dapat dijalankan:
    ```bash
    chmod +x install_vpn.sh add_user.sh
    ```

### Langkah 2: Jalankan Skrip Instalasi

Pilih instruksi yang sesuai dengan platform Anda.

#### 🐧 Untuk Server Linux (Debian/Ubuntu)
Jalankan skrip instalasi dengan `sudo`:
```bash
sudo ./install_vpn.sh
```

#### 📱 Untuk Termux
1.  **Dapatkan Akses Root**
    Jalankan `tsu` untuk beralih ke mode superuser.
    ```bash
    tsu
    ```
    Anda akan melihat prompt berubah dari `$` menjadi `#`.

2.  **Jalankan Skrip Instalasi**
    Setelah berada di shell root (`#`), jalankan skripnya:
    ```bash
    ./install_vpn.sh
    ```

Setelah skrip selesai, sebuah file bernama `client.conf` akan dibuat di direktori yang sama.

### Langkah 3: Hubungkan Klien (Perangkat Anda)

1.  **Ambil File Konfigurasi Klien**
    Salin file `client.conf` dari server/Termux ke perangkat Anda (HP atau laptop).
    -   Di Termux, Anda bisa mengakses penyimpanan internal dari `/sdcard`. Contoh: `cp client.conf /sdcard/Download/`
    -   Di server, gunakan `scp` atau tampilkan isinya dengan `cat client.conf` lalu salin teksnya.

2.  **Instal Aplikasi WireGuard**
    Unduh aplikasi resmi WireGuard di perangkat yang ingin Anda hubungkan ke VPN.
    -   [Android](https://play.google.com/store/apps/details?id=com.wireguard.android)
    -   [iOS](https://apps.apple.com/us/app/wireguard/id1441195209)
    -   [Windows](https://download.wireguard.com/windows-client/wireguard-installer.exe)
    -   [macOS](https://apps.apple.com/us/app/wireguard/id1451685025)

3.  **Impor Konfigurasi & Hubungkan**
    Buka aplikasi WireGuard, impor file `client.conf`, dan aktifkan koneksi.

---

## Menambah Pengguna Baru

Jika Anda ingin menghubungkan perangkat lain, gunakan skrip `add_user.sh`.

1.  **Jalankan Skrip**
    -   **Di Linux:** `sudo ./add_user.sh`
    -   **Di Termux:** `tsu` (jika belum root), lalu `./add_user.sh`

2.  **Masukkan Nama Klien**
    Skrip akan meminta Anda memasukkan nama untuk klien baru (contoh: `laptop_kerja`).

3.  **Ambil File Konfigurasi Baru**
    Skrip akan membuat file baru (contoh: `laptop_kerja.conf`). Salin file ini ke perangkat baru Anda dan impor ke aplikasi WireGuard di sana.

---

## Catatan Penting untuk Termux

-   **Tidak Berjalan Saat Boot:** Koneksi VPN tidak akan dimulai secara otomatis saat perangkat dinyalakan ulang. Anda harus membuka Termux, beralih ke root (`tsu`), dan menjalankan `wg-quick up wg0` untuk mengaktifkan kembali server VPN.
-   **Jaga Termux Tetap Aktif:** Gunakan `termux-wake-lock` untuk mencegah Android menghentikan aplikasi Termux saat berjalan di latar belakang.
-   **Network Interface:** Skrip mencoba mendeteksi interface jaringan secara otomatis (biasanya `wlan0`), tetapi jika gagal, Anda mungkin perlu memasukkannya secara manual.
