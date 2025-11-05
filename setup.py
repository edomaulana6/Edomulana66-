import os
import sys

ENV_FILE = ".env"

def main():
    print("--- 🚀 Setup Bot Telegram Anti-Gagal 🚀 ---")

    # 1. Minta Token
    token = input("➡️  Masukkan token bot Anda dari @BotFather: ").strip()

    if ':' not in token or len(token) < 20:
        print("\n[❌] KESALAHAN FATAL: Format token tidak valid. Pastikan Anda menyalin token lengkap.")
        sys.exit(1)

    # 2. Tulis ke File
    try:
        with open(ENV_FILE, 'w') as f:
            f.write(f'TELEGRAM_TOKEN="{token}"\n')
        print(f"\n[📝] File '{ENV_FILE}' berhasil ditulis...")
    except IOError as e:
        print(f"\n[❌] KESALAHAN FATAL: Gagal menulis file: {e}")
        print("Pastikan Anda memiliki izin tulis (write permission) di direktori ini.")
        sys.exit(1)

    # 3. Verifikasi File
    print("[🔍] Memverifikasi file yang baru saja ditulis...")
    try:
        with open(ENV_FILE, 'r') as f:
            content = f.read().strip()

        expected_content = f'TELEGRAM_TOKEN="{token}"'

        if content == expected_content:
            print("\n" + "="*40)
            print("✅✅✅ SETUP BERHASIL! ✅✅✅")
            print("="*40)
            print(f"Token Anda telah disimpan dengan benar di '{ENV_FILE}'.")
            print("\nSekarang, Anda bisa menjalankan bot dengan perintah:")
            print("./start.sh")
            print("="*40)
        else:
            print("\n" + "="*40)
            print("❌❌❌ SETUP GAGAL! ❌❌❌")
            print("="*40)
            print("Gagal memverifikasi konten file. File mungkin rusak.")
            print("Konten yang diharapkan:", expected_content)
            print("Konten yang terbaca:", content)
            print("\nSilakan coba jalankan setup ini lagi.")
            print("="*40)
            sys.exit(1)

    except FileNotFoundError:
        print("\n[❌] KESALAHAN FATAL: File .env tidak ditemukan setelah ditulis. Ini sangat aneh.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[❌] KESALAHAN FATAL: Terjadi error yang tidak diketahui saat verifikasi: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
