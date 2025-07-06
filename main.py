import logging
import re
import asyncio
import httpx
import os
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# ---------------- НАСТРОЙКИ ---------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

CONFIG = {
    "api_id": int(os.getenv("TELEGRAM_API_ID")),
    "api_hash": os.getenv("TELEGRAM_API_HASH"),
    "string_session": os.getenv("TELEGRAM_SESSION"),
    "target_chat_title": os.getenv("TARGET_CHAT"),  # Например "Кальянная Алика (чат)"
    "bot_token": "7792811749:AAEPG63BBnmdbAwApMVuCpC82ZW3XfKx_O0",  # ← токен бота
    "bot_target_chat_id": "@call_flagmen",  # ← username чата или ID (если это группа)
}
# ------------------------------------------- #

def extract_promo(text: str) -> list[str]:
    text = text.upper()
    matches = re.findall(r'[A-F0-9*]{12,}', text)
    results = []
    for match in matches:
        code = match.replace('*', '0')
        if len(code) >= 12:
            results.append(code[:12])
    return results

async def send_via_bot(token: str, chat_id: str, text: str):
    async with httpx.AsyncClient() as client:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        try:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                logger.info(f"📩 Уведомление отправлено в {chat_id}")
            else:
                logger.error(f"❌ Ошибка отправки: {response.text}")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки через бота: {e}")

async def main():
    client = TelegramClient(StringSession(CONFIG["session_str"]), CONFIG["api_id"], CONFIG["api_hash"])
    await client.start()
    logger.info("✅ Telegram клиент запущен")

    dialogs = await client.get_dialogs()
    target_entity = None
    for dialog in dialogs:
        if dialog.name == CONFIG["target_chat_title"]:
            target_entity = dialog.entity
            break

    if not target_entity:
        logger.error(f"Чат с названием '{CONFIG['target_chat_title']}' не найден")
        return

    seen_codes = set()
    try:
        with open(CONFIG["codes_file"], "r", encoding="utf-8") as f:
            for line in f:
                seen_codes.add(line.split(",")[0].strip())
    except FileNotFoundError:
        pass

    @client.on(events.NewMessage(chats=target_entity))
    async def handler(event: events.NewMessage.Event):
        text = event.message.message
        matches = extract_promo(text)
        if not matches:
            return

        unique_codes = [c for c in matches if c not in seen_codes]

        if not unique_codes:
            logger.info("♻️ Повторные промокоды, новых нет")
            return

        for code in unique_codes:
            seen_codes.add(code)
            timestamp = datetime.utcnow().isoformat()
            with open(CONFIG["codes_file"], "a", encoding="utf-8") as f:
                f.write(f"{code},{timestamp}\n")
            logger.info(f"🎉 Новый промокод: {code}")

            message = (
                f"🎉 ПРОМИК ЧЕХЛЕО ЖЕ ЕСТЬ Я ЕГО ВСЕ ЦЕЛОВАЛ,\n"
                f"спасибо владу за такой промокод: {code}"
            )
            await send_via_bot(CONFIG["bot_token"], CONFIG["bot_target_chat_id"], message)

    logger.info(f"👂 Ожидаю сообщения в чате: {CONFIG['target_chat_title']}")
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("⛔ Остановлено пользователем")
