#!/usr/bin/env bash
echo "🚀 Starting SMS Blast Bot..."
echo "🤖 Bot: @Blackdeviltoolowner_bot"
echo "👤 Owner: @Blackdeviltoolowner_bot"

cd /app || cd /workspace || cd .

if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found!"
    exit 1
fi

if ! pip3 show aiogram &> /dev/null; then
    echo "📦 Installing requirements..."
    pip3 install -r requirements.txt
fi

python3 launcher.py