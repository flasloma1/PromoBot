# app.py
import os, asyncio
from flask import Flask 
from main import run_bot   # импортируй свою функцию запуска бота

app = Flask(__name__)

@app.route("/")
def ping():
    return "👋 Бот работает!"

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(run_bot())   # запускаем бота в фоне
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
