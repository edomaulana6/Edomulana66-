#!/bin/bash
PID_FILE="bot.pid"

if [ ! -f ".env" ]; then
    echo "Error: .env file not found. Please run 'python3 setup.py' first."
    exit 1
fi

if [ -f $PID_FILE ]; then
    echo "Bot is already running. Stop it first with ./stop.sh"
    exit 1
fi

echo "Checking for yt-dlp updates..."
pip install -U yt-dlp

echo "Starting bot in the background..."
termux-wake-lock
nohup python3 bot.py > bot.log 2>&1 &
echo $! > $PID_FILE
echo "Bot started with PID $(cat $PID_FILE). Logs are in bot.log."
