import os

ENV_FILE = ".env"

def main():
    print("--- 🚀 Selamat Datang di Setup Bot Telegram 🚀 ---")
    if os.path.exists(ENV_FILE):
        overwrite = input(f"[!] File '{ENV_FILE}' sudah ada. Timpa? (y/n): ").lower()
        if overwrite != 'y':
            print("Setup dibatalkan.")
            return

    token = input("Masukkan token bot Anda dari @BotFather: ").strip()

    if ':' not in token or len(token) < 20:
        print("\n[❌] KESALAHAN: Format token tidak valid.")
        return

    try:
        with open(ENV_FILE, 'w') as f:
            f.write(f'TELEGRAM_TOKEN="{token}"\n')
        print(f"\n[✅] Berhasil! File '{ENV_FILE}' telah dibuat.")
        print("Jalankan './start.sh' untuk memulai bot.")
    except IOError as e:
        print(f"\n[❌] KESALAHAN: Gagal menulis file: {e}")

if __name__ == "__main__":
    main()
