import os

def main():
    print("--- 🤖 Bot Setup Assistant 🤖 ---")
    if os.path.exists('.env'):
        print("\n[⚠️] File .env sudah ada.")
        if input("Timpa file? (yes/no): ").lower() not in ['yes', 'y']:
            print("\nSetup dibatalkan.")
            return

    token = input("\nSilakan masukkan Token Bot Telegram Anda:\n> ")
    if not token or len(token.split(':')) != 2:
        print("\n[❌] Error: Token tidak valid.")
        return

    with open('.env', 'w') as f:
        f.write(f"TELEGRAM_TOKEN={token}\n")

    print("\n[✅] Sukses! File .env telah dibuat.")
    print("Mulai bot dengan: ./start.sh")

if __name__ == "__main__":
    main()
