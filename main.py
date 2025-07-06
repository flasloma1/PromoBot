import logging
import re
import asyncio
import httpx
import os
import sys
from datetime import datetime, timezone
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Настройки логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Конфигурация
class Config:
    def __init__(self):
        self.api_id = int(os.getenv("TELEGRAM_API_ID", 0))
        self.api_hash = os.getenv("TELEGRAM_API_HASH", "")
        self.session = os.getenv("TELEGRAM_SESSION", "")
        self.target_chat = os.getenv("TARGET_CHAT", "")
        self.bot_token = "8125104552:AAFubdRCSgpCizdb2A78-jsJhQJAVwUs6wA"
        self.bot_chat_id = os.getenv("BOT_CHAT_ID", "")
        self.codes_file = "promo_codes.txt"
        
        # Проверка обязательных параметров
        if not all([self.api_id, self.api_hash, self.session, self.target_chat, self.bot_chat_id]):
            logger.error("❌ Ошибка конфигурации: Проверьте переменные окружения")
            sys.exit(1)

CONFIG = Config()

def extract_promo(text: str) -> list[str]:
    """Извлекает промокоды из текста"""
    text = text.upper()
    matches = re.findall(r'[A-F0-9*]{12,}', text)
    return [match.replace('*', '0')[:12] for match in matches]

async def send_bot_message(text: str):
    """Отправляет сообщение через бота"""
    url = f"https://api.telegram.org/bot{CONFIG.bot_token}/sendMessage"
    
    # Параметры запроса
    payload = {
        "chat_id": CONFIG.bot_chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            logger.info("✅ Уведомление отправлено")
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Ошибка HTTP {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"🚫 Ошибка отправки: {str(e)}")

async def main():
    """Основная функция"""
    logger.info("🚀 Запуск мониторинга промокодов")
    
    # Инициализация клиента Telegram
    client = TelegramClient(
        StringSession(CONFIG.session),
        CONFIG.api_id,
        CONFIG.api_hash
    )
    
    await client.start()
    logger.info("🔓 Клиент Telegram авторизован")

    # Поиск целевого чата
    target_entity = None
    async for dialog in client.iter_dialogs():
        if dialog.name == CONFIG.target_chat:
            target_entity = dialog.entity
            logger.info(f"🎯 Найден целевой чат: {dialog.name} (ID: {dialog.id})")
            break

    if not target_entity:
        logger.error(f"❌ Чат '{CONFIG.target_chat}' не найден")
        await client.disconnect()
        return

    # Загрузка истории промокодов
    seen_codes = set()
    if os.path.exists(CONFIG.codes_file):
        try:
            with open(CONFIG.codes_file, "r") as f:
                seen_codes = {line.split(",")[0].strip() for line in f}
            logger.info(f"📚 Загружено {len(seen_codes)} промокодов из истории")
        except Exception as e:
            logger.error(f"⚠️ Ошибка чтения файла промокодов: {str(e)}")

    # Обработчик новых сообщений
    @client.on(events.NewMessage(chats=target_entity))
    async def message_handler(event):
        text = event.message.text or ""
        
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
            try:
                with open(CONFIG.codes_file, "a") as f:
                    f.write(f"{code},{timestamp}\n")
            except Exception as e:
                logger.error(f"⚠️ Ошибка записи промокода: {str(e)}")
            
            logger.info(f"🎁 Новый промокод: {code}")
            
            # Отправка уведомления
            message = f"🔥 Обнаружен новый промокод: <code>{code}</code>"
            await send_bot_message(message)

    logger.info(f"👂 Ожидание сообщений в чате: {CONFIG.target_chat}")
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⛔ Остановлено пользователем")
    except Exception as e:
        logger.exception(f"💥 Критическая ошибка: {str(e)}")
