import logging
import re
import asyncio
import httpx
import os
from datetime import datetime, timezone
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Настройки логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Конфигурация из переменных окружения
CONFIG = {
    "api_id": int(os.getenv("TELEGRAM_API_ID")),
    "api_hash": os.getenv("TELEGRAM_API_HASH"),
    "string_session": os.getenv("TELEGRAM_SESSION"),
    "target_chat": os.getenv("TARGET_CHAT"),
    "bot_token": "8125104552:AAFubdRCSgpCizdb2A78-jsJhQJAVwUs6wA",  # НОВЫЙ ТОКЕН
    "bot_target_chat": os.getenv("BOT_TARGET_CHAT"),
    "codes_file": "promo_codes.txt"
}

def extract_promo(text: str) -> list[str]:
    """Извлекает промокоды из текста"""
    text = text.upper()
    matches = re.findall(r'[A-F0-9*]{12,}', text)
    return [match.replace('*', '0')[:12] for match in matches]

async def send_bot_message(text: str):
    """Отправляет сообщение через бота"""
    url = f"https://api.telegram.org/bot{CONFIG['bot_token']}/sendMessage"
    payload = {
        "chat_id": CONFIG["bot_target_chat"],
        "text": text,
        "parse_mode": "HTML"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                logger.info("✅ Уведомление отправлено")
            else:
                logger.error(f"❌ Ошибка: {response.text}")
        except Exception as e:
            logger.error(f"🚫 Сбой отправки: {e}")

async def main():
    """Основная функция"""
    # Инициализация клиента Telegram
    client = TelegramClient(
        StringSession(CONFIG["string_session"]),
        CONFIG["api_id"],
        CONFIG["api_hash"]
    )
    
    await client.start()
    logger.info("🔓 Клиент Telegram авторизован")

    # Поиск целевого чата
    target_chat = None
    async for dialog in client.iter_dialogs():
        if dialog.name == CONFIG["target_chat"]:
            target_chat = dialog.entity
            break

    if not target_chat:
        logger.error(f"❌ Чат '{CONFIG['target_chat']}' не найден")
        return

    # Загрузка истории промокодов
    seen_codes = set()
    if os.path.exists(CONFIG["codes_file"]):
        with open(CONFIG["codes_file"], "r") as f:
            seen_codes = {line.split(",")[0] for line in f}

    # Обработчик новых сообщений
    @client.on(events.NewMessage(chats=target_chat))
    async def message_handler(event):
        text = event.message.text
        if not text:
            return

        # Поиск промокодов
        codes = extract_promo(text)
        if not codes:
            return

        # Фильтрация новых кодов
        new_codes = [code for code in codes if code not in seen_codes]
        if not new_codes:
            logger.info("🔄 Новых промокодов нет")
            return

        # Обработка новых промокодов
        for code in new_codes:
            seen_codes.add(code)
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Запись в файл
            with open(CONFIG["codes_file"], "a") as f:
                f.write(f"{code},{timestamp}\n")
            
            logger.info(f"🎁 Новый промокод: {code}")
            
            # Отправка уведомления
            message = (
                f"🔥 Обнаружен новый промокод!\n\n"
                f"<b>Код:</b> <code>{code}</code>\n"
                f"<b>Чат:</b> {CONFIG['target_chat']}\n"
                f"<b>Время:</b> {timestamp.split('T')[1][:8]} UTC"
            )
            await send_bot_message(message)

    logger.info(f"👂 Ожидание сообщений в чате: {CONFIG['target_chat']}")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
