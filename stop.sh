#!/bin/bash
PID_FILE="bot.pid"

echo "Attempting to stop the bot..."
if [ -f $PID_FILE ]; then
    PID=$(cat $PID_FILE)
    if ps -p $PID > /dev/null; then
        kill $PID
        echo "Bot process with PID $PID has been terminated."
    else
        echo "Bot process with PID $PID not found."
    fi
    rm $PID_FILE
else
    echo "Bot does not seem to be running (PID file not found)."
fi
termux-wake-unlock
echo "Cleanup complete."
