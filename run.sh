#!/bin/bash
set -eu  # stop on first error & undefined variable

# Create venv if not exists
if [ ! -d "env" ]; then
    echo "📦 Environment yaratilmoqda..."
    python3 -m venv env

    echo "📚 Kerakli librarylar o'rnatilmoqda..."
    ./env/bin/pip install -r requiriements.txt
fi

# Run the bot
echo "🚀 Ishga tushmoqda..."
./env/bin/python session_generator.py