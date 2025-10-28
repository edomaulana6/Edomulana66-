# Skrip Instalasi & Manajemen VPN WireGuard

Proyek ini menyediakan dua skrip Bash untuk mempermudah proses pembuatan dan pengelolaan server VPN WireGuard pribadi Anda di server berbasis Debian atau Ubuntu.

-   `install_vpn.sh`: Menginstal WireGuard, membuat semua konfigurasi awal, dan menghasilkan file konfigurasi untuk klien pertama.
-   `add_user.sh`: Menambahkan pengguna (klien) baru ke server VPN yang sudah ada.

## Persyaratan

-   Sebuah server yang menjalankan sistem operasi Debian atau Ubuntu.
-   Akses root atau pengguna dengan hak `sudo` di server tersebut.

---

## Panduan Penggunaan

### Langkah 1: Instalasi Awal Server VPN

Proses ini hanya perlu dilakukan sekali saat pertama kali menyiapkan server.

1.  **Salin Skrip ke Server Anda**
    Salin file `install_vpn.sh` dan `add_user.sh` ke direktori home di server Anda. Anda bisa melakukannya dengan `scp` atau dengan menyalin dan menempelkan isinya menggunakan editor teks seperti `nano`.

2.  **Berikan Izin Eksekusi**
    Buka terminal di server Anda dan berikan izin agar skrip dapat dijalankan:
    ```bash
    chmod +x install_vpn.sh add_user.sh
    ```

3.  **Jalankan Skrip Instalasi**
    Jalankan skrip instalasi dengan hak `sudo`. Skrip ini akan menginstal semua yang dibutuhkan, membuat kunci, dan mengkonfigurasi server.
    ```bash
    sudo ./install_vpn.sh
    ```
    Ikuti instruksi yang mungkin muncul. Setelah selesai, skrip akan membuat file bernama `client.conf` di direktori yang sama.

4.  **Ambil File Konfigurasi Klien**
    File `client.conf` adalah "tiket" Anda untuk terhubung ke VPN. Salin file ini dari server ke perangkat Anda (HP atau laptop). Anda bisa menggunakan `scp` atau menampilkan isinya dengan `cat client.conf` lalu menyalin teksnya secara manual.

### Langkah 2: Menghubungkan Klien (Perangkat Anda)

1.  **Instal Aplikasi WireGuard**
    Unduh dan instal aplikasi resmi WireGuard di perangkat Anda.
    -   [Android](https://play.google.com/store/apps/details?id=com.wireguard.android)
    -   [iOS (iPhone/iPad)](https://apps.apple.com/us/app/wireguard/id1441195209)
    -   [Windows](https://download.wireguard.com/windows-client/wireguard-installer.exe)
    -   [macOS](https://apps.apple.com/us/app/wireguard/id1451685025)

2.  **Impor Konfigurasi**
    Buka aplikasi WireGuard dan impor file `client.conf` yang sudah Anda salin. Biasanya ada tombol `+` atau "Import tunnel(s) from file". Anda juga bisa menggunakan fitur pindai kode QR jika aplikasi menawarkannya (skrip ini tidak membuat kode QR).

3.  **Aktifkan Koneksi**
    Setelah profil diimpor, cukup tekan tombol *connect* atau *activate* untuk terhubung ke server VPN Anda.

---

### Langkah 3: Menambah Pengguna atau Perangkat Baru

Jika Anda ingin menghubungkan perangkat lain (misalnya, laptop setelah HP Anda terhubung), jalankan skrip `add_user.sh`.

1.  **Jalankan Skrip `add_user.sh`**
    Di server Anda, jalankan perintah:
    ```bash
    sudo ./add_user.sh
    ```

2.  **Masukkan Nama Klien**
    Skrip akan meminta Anda memasukkan nama untuk klien baru. Gunakan nama yang deskriptif tanpa spasi, contoh: `laptop_kerja` atau `hp_samsung`.

3.  **Ambil File Konfigurasi Baru**
    Skrip akan membuat file baru, contohnya `laptop_kerja.conf`. Sama seperti sebelumnya, salin file ini ke perangkat baru Anda dan impor ke aplikasi WireGuard di sana.

    Ulangi langkah ini setiap kali Anda ingin menambahkan perangkat baru.

---

## Perintah Server yang Berguna

-   **Melihat Status WireGuard dan Klien yang Terhubung:**
    ```bash
    sudo wg show
    ```

-   **Memulai Ulang Layanan WireGuard:**
    ```bash
    sudo systemctl restart wg-quick@wg0
    ```

-   **Melihat Log Layanan:**
    ```bash
    sudo journalctl -u wg-quick@wg0
    ```
