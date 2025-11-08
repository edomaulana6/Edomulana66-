import os

def main():
    """
    Guides the user through creating a .env file for the bot.
    """
    print("--- 🤖 Bot Setup Assistant 🤖 ---")
    print("This script will help you set up the .env file for the bot.")

    if os.path.exists('.env'):
        print("\n[⚠️] An '.env' file already exists.")
        overwrite = input("Do you want to overwrite it? (yes/no): ").lower()
        if overwrite not in ['yes', 'y']:
            print("\nSetup cancelled. Your existing .env file has been preserved.")
            return

    token = input("\nPlease paste your Telegram Bot Token here:\n> ")

    if not token or len(token.split(':')) != 2:
        print("\n[❌] Error: That doesn't look like a valid Telegram token.")
        print("Setup failed. Please run the script again with a valid token.")
        return

    with open('.env', 'w') as f:
        f.write(f"TELEGRAM_TOKEN={token}\n")

    print("\n[✅] Success! Your '.env' file has been created.")
    print("You can now start the bot using: ./start.sh")

if __name__ == "__main__":
    main()
