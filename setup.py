import os

ENV_FILE = ".env"
TEMPLATE_FILE = ".env.template"

def main():
    """
    Fungsi utama untuk memandu pengguna melalui proses setup.
    """
    print("--- 🚀 Selamat Datang di Setup Bot Telegram 🚀 ---")
    print("Saya akan membantu Anda untuk mengatur token bot.")

    # 1. Periksa apakah file .env sudah ada
    if os.path.exists(ENV_FILE):
        overwrite = input(f"\n[!] File '{ENV_FILE}' sudah ada. Apakah Anda ingin menimpanya? (y/n): ").lower()
        if overwrite != 'y':
            print("\nSetup dibatalkan. File yang ada tidak diubah.")
            return

    # 2. Minta token dari pengguna
    print("\nSilakan dapatkan token bot Anda dari @BotFather di Telegram.")
    token = input("Masukkan token bot Anda di sini: ").strip()

    # Validasi sederhana untuk token
    if ':' not in token or len(token) < 20:
        print("\n[❌] KESALAHAN: Format token tampaknya tidak valid.")
        print("Pastikan Anda menyalin seluruh token yang diberikan oleh BotFather.")
        return

    # 3. Buat file .env
    try:
        with open(ENV_FILE, 'w') as f:
            f.write(f'TELEGRAM_TOKEN="{token}"\n')
        print(f"\n[✅] Berhasil! File '{ENV_FILE}' telah dibuat/diperbarui.")
        print("Sekarang Anda siap untuk menjalankan bot dengan './start.sh'.")
    except IOError as e:
        print(f"\n[❌] KESALAHAN: Tidak dapat menulis ke file '{ENV_FILE}'.")
        print(f"Detail error: {e}")

if __name__ == "__main__":
    main()
