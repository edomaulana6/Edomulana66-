import os

def main():
    print("--- 🤖 Asisten Konfigurasi & Perbaikan Token 🤖 ---")
    print("Skrip ini akan membuat atau menimpa file .env dengan token yang benar.")

    token = input("\nSilakan masukkan Token Bot Telegram Anda yang VALID:\n> ")
    if not token or len(token.split(':')) != 2:
        print("\n[❌] Error: Token tidak valid.")
        return

    with open('.env', 'w') as f:
        f.write(f"TELEGRAM_TOKEN={token}\n")

    print("\n[✅] Sukses! File .env telah dibuat.")
    print("Mulai bot dengan: ./start.sh")

if __name__ == "__main__":
    main()
