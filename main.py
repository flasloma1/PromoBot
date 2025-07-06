import logging
import re
import asyncio
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
        self.codes_file = "promo_codes.txt"
        
        # ID пользователей для уведомлений (ваш и вашего друга)
        self.notify_user_ids = [817155267, 6344353030]
        
        # Проверка обязательных параметров
        if not all([self.api_id, self.api_hash, self.session, self.target_chat]):
            logger.error("❌ Ошибка конфигурации: Проверьте переменные окружения")
            sys.exit(1)

CONFIG = Config()

def extract_promo(text: str) -> list[str]:
    """Извлекает промокоды из текста"""
    text = text.upper()
    matches = re.findall(r'[A-F0-9*]{12,}', text)
    return [match.replace('*', '0')[:12] for match in matches]

async def send_user_notification(client, user_id: int, code: str):
    """Отправляет уведомление напрямую пользователю"""
    try:
        # Формируем сообщение
        message = (
            "🎉 ПРОМИК ЧЕХЛЕО ЖЕ ЕСТЬ Я ЕГО ВСЕ ЦЕЛОВАЛ, спасибо владу за такой промокод:\n\n"
            f"🔥 Код: `{code}`\n"
            f"💬 Чат: {CONFIG.target_chat}\n"
            f"🕒 Время: {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC"
        )
        
        # Отправляем сообщение
        await client.send_message(user_id, message)
        logger.info(f"📩 Уведомление отправлено пользователю {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки пользователю {user_id}: {str(e)}")

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
    logger.info(f"👤 Ваш ID: {(await client.get_me()).id}")

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
            
            logger.info(f"🎉 ПРОМИК ЧЕХЛЕО ЖЕ ЕСТЬ Я ЕГО ВСЕ ЦЕЛОВАЛ, спасибо владу за такой промокод: {code}")
            
            # Отправка уведомлений всем указанным пользователям
            for user_id in CONFIG.notify_user_ids:
                await send_user_notification(client, user_id, code)

    logger.info(f"👂 Ожидание сообщений в чате: {CONFIG.target_chat}")
    logger.info(f"👥 Уведомления будут отправляться: {CONFIG.notify_user_ids}")
    await client.run_until_disconnected()

# 👇 Добавляем эту функцию, чтобы app.py мог импортировать её
async def run_bot():
    await main()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⛔ Остановлено пользователем")
    except Exception as e:
        logger.exception(f"💥 Критическая ошибка: {str(e)}")
