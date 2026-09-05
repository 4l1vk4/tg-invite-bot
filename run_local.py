#!/usr/bin/env python3
"""
Локальный запуск Mini App и Telegram Бота на Mac
Запуск: python run_local.py
"""

import sys
import os
import time
import subprocess
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8000
DIRECTORY = os.path.abspath(os.path.dirname(__file__))

class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def log_message(self, format, *args):
        # Логируем только ошибки или нужные запросы
        pass

def start_http_server():
    server = HTTPServer(("0.0.0.0", PORT), QuietHandler)
    server.serve_forever()

def main():
    print("=" * 65)
    print("🌴 TG INVITE BOT — LOCAL LAUNCHER (MAC OS)")
    print("=" * 65)

    # 1. Проверяем наличие .env
    env_file = os.path.join(DIRECTORY, ".env")
    if not os.path.exists(env_file):
        example_file = os.path.join(DIRECTORY, ".env.example")
        if os.path.exists(example_file):
            with open(example_file, "r") as src, open(env_file, "w") as dst:
                dst.write(src.read())
            print("📝 Создан файл .env из .env.example.")
            print("   👉 Обязательно укажи свой BOT_TOKEN в файле .env!")
        else:
            with open(env_file, "w") as dst:
                dst.write("BOT_TOKEN=\nWEBAPP_URL=http://localhost:8000/webapp/\nADMIN_CHAT_ID=\n")
            print("📝 Создан файл .env.")

    # 2. Запускаем локальный веб-сервер в фоне
    server_thread = threading.Thread(target=start_http_server, daemon=True)
    server_thread.start()

    print(f"\n🌐 Локальный веб-сервер запущен:")
    print(f"   👉 Тест в браузере на Mac: http://localhost:{PORT}/webapp/")
    print("\n💡 Как тестировать Telegram Mini App прямо с телефона/Mac:")
    print("   Вариант 1 (Быстрый туннель без установки):")
    print(f"      Открой новый терминал и выполни: npx localtunnel --port {PORT}")
    print("      Скопируй полученную HTTPS ссылку в .env (WEBAPP_URL=https://...)")
    print("   Вариант 2 (Бесплатный хостинг за 1 минуту):")
    print("      Залей папку webapp на GitHub Pages / Vercel / Netlify")
    print("=" * 65)

    # 3. Запускаем бота
    print("\n🤖 Запуск bot.py...\n")
    try:
        subprocess.run([sys.executable, "bot.py"], check=True)
    except KeyboardInterrupt:
        print("\n👋 Остановка локального сервера и бота.")

if __name__ == "__main__":
    main()
