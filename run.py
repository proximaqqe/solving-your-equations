"""
Запуск бота с выводом ошибок.
"""
import sys
import os

# Переходим в папку скрипта
os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("Python:", sys.executable)
print("Version:", sys.version)
print()

try:
    print("Loading modules...")
    from dotenv import load_dotenv
    from telegram import Update
    from telegram.ext import Application
    print("OK: telegram, dotenv")
except ImportError as e:
    print("ERROR: Missing module:", e)
    print()
    print("Run: pip install -r requirements.txt")
    input("Press Enter to exit...")
    sys.exit(1)

try:
    from math_solver import solve_math
    print("OK: math_solver")
except ImportError as e:
    print("ERROR:", e)
    input("Press Enter to exit...")
    sys.exit(1)

load_dotenv(".env")
if not os.getenv("TELEGRAM_BOT_TOKEN"):
    load_dotenv(".env.example")

token = os.getenv("TELEGRAM_BOT_TOKEN")
if not token:
    print("ERROR: TELEGRAM_BOT_TOKEN not found in .env")
    input("Press Enter to exit...")
    sys.exit(1)

token = token.strip().strip('"').strip("'")
print("Token: OK")
print()
print("Starting bot...")
print()

try:
    from bot import main
    main()
except Exception as e:
    print("ERROR:", e)
    import traceback
    traceback.print_exc()
    input("Press Enter to exit...")
    sys.exit(1)
