# Server Proxy SOCKS5 di Termux (Tanpa Root)

Proyek ini memungkinkan Anda mengubah perangkat Android Anda menjadi server proxy SOCKS5 menggunakan Termux. Ini **tidak memerlukan akses root**. Anda dapat merutekan lalu lintas dari perangkat lain (seperti laptop) melalui koneksi internet ponsel Anda.

-   `start_proxy.sh`: Menginstal dependensi, mengkonfigurasi otentikasi, dan memulai server proxy.
-   `stop_proxy.sh`: Menghentikan server proxy yang sedang berjalan.

## Cara Menggunakan

### Langkah 1: Persiapan di Termux

1.  **Berikan Izin Eksekusi**
    Setelah menyalin file ke Termux, buka direktori `proxy` dan berikan izin agar skrip dapat dijalankan:
    ```bash
    cd proxy
    chmod +x start_proxy.sh stop_proxy.sh
    ```

2.  **Jalankan Skrip Start**
    Jalankan skrip untuk memulai server:
    ```bash
    ./start_proxy.sh
    ```
    -   Skrip akan menginstal `microsocks` jika belum ada.
    -   Anda akan diminta untuk membuat **username** dan **password**.
    -   Setelah dimulai, skrip akan menampilkan **Alamat IP** dan **Port** yang perlu Anda gunakan. Catat informasi ini.

3.  **Jaga Termux Tetap Aktif**
    Gunakan `termux-wake-lock` di sesi Termux lain untuk mencegah Android menghentikan aplikasi saat berjalan di latar belakang.

### Langkah 2: Konfigurasi di Perangkat Lain

Sekarang, pindah ke perangkat lain (misalnya, laptop) yang ingin Anda hubungkan ke proxy. Pastikan perangkat ini terhubung ke **jaringan WiFi yang sama** dengan ponsel Anda.

Gunakan Alamat IP, Port, Username, dan Password yang Anda dapatkan dari Langkah 1.

#### Contoh Konfigurasi: Browser Firefox (Direkomendasikan)

Firefox memungkinkan Anda mengatur proxy hanya untuk browser, tanpa mempengaruhi seluruh sistem operasi Anda.

1.  Buka Firefox, pergi ke **Settings** (Pengaturan).
2.  Di tab **General**, gulir ke bawah ke bagian **Network Settings** (Pengaturan Jaringan) dan klik **Settings...**.
3.  Pilih opsi **Manual proxy configuration** (Konfigurasi proxy manual).
4.  Di baris **SOCKS Host**, masukkan **Alamat IP** dari Termux.
5.  Di sebelah kanannya, masukkan **Port** (biasanya `1080`).
6.  Pilih opsi **SOCKS v5**.
7.  Centang kotak **Proxy DNS when using SOCKS v5** (ini penting untuk mencegah kebocoran DNS).
8.  Biarkan kolom lain (HTTP, SSL, FTP) kosong.
9.  Klik **OK** untuk menyimpan.

Saat Anda mencoba membuka situs web, Firefox akan memunculkan jendela pop-up yang meminta **Username** dan **Password** proxy. Masukkan kredensial yang Anda buat di Termux.

#### Contoh Konfigurasi: Sistem Operasi Windows 10/11

Pengaturan ini akan merutekan sebagian besar lalu lintas aplikasi Windows melalui proxy.

1.  Buka **Settings** -> **Network & Internet** -> **Proxy**.
2.  Di bawah **Manual proxy setup**, aktifkan **Use a proxy server**.
3.  Di kolom **Address**, masukkan **Alamat IP** dari Termux.
4.  Di kolom **Port**, masukkan **Port** (`1080`).
5.  Klik **Save**.
6.  Aplikasi yang mendukung proxy sistem (seperti browser) akan meminta username dan password saat Anda mencoba terhubung ke internet.

---

### Langkah 3: Menghentikan Server Proxy

Jika sudah selesai, kembali ke Termux dan jalankan:
```bash
./stop_proxy.sh
```
Ini akan menghentikan server proxy yang berjalan di latar belakang. Jangan lupa untuk menonaktifkan pengaturan proxy di perangkat lain Anda.
