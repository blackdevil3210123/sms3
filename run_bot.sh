#!/usr/bin/env bash
# 24x7 Auto-restart wrapper for SMS Blast Bot
cd /app || cd /workspace || cd .

LOG_FILE="/app/bot.log"

while true; do
    echo "========================================" >> "$LOG_FILE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting SMS Blast Bot..." >> "$LOG_FILE"
    echo "========================================" >> "$LOG_FILE"
    
    python3 /app/main.py >> "$LOG_FILE" 2>&1
    EXIT_CODE=$?
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Bot exited with code $EXIT_CODE. Restarting in 5s..." >> "$LOG_FILE"
    sleep 5
done