"""T-MART Telegram boti.

Ishga tushirish:  python bot.py
Sozlamalar .env faylida (namuna: .env.example).
"""
from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, WebAppInfo
from dotenv import load_dotenv

from orders import ORDERS_PATH, OrderError, format_admin, format_customer, load_catalog, parse_order, save_order

log = logging.getLogger("tmart")


def shop_keyboard(webapp_url: str) -> ReplyKeyboardMarkup:
    # Muhim: buyurtma (sendData) faqat shu pastki klaviatura tugmasi orqali
    # ochilgan Mini App'dan botga keladi.
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🛒 Do'konni ochish", web_app=WebAppInfo(url=webapp_url))]],
        resize_keyboard=True,
        is_persistent=True,
    )


def create_dispatcher(webapp_url: str, admin_chat_id: int | None, orders_path=ORDERS_PATH) -> Dispatcher:
    dp = Dispatcher()
    keyboard = shop_keyboard(webapp_url)

    @dp.message(CommandStart())
    async def on_start(message: Message) -> None:
        name = message.from_user.first_name if message.from_user else "do'stim"
        await message.answer(
            f"Assalomu alaykum, {name}! 👋\n\n"
            "<b>T-MART</b> — Koreya va Xitoy ramyonlari do'koniga xush kelibsiz! 🍜🇰🇷🇨🇳\n\n"
            "Pastdagi <b>«🛒 Do'konni ochish»</b> tugmasini bosing, ramyonlarni tanlang "
            "va bir necha soniyada buyurtma bering.",
            reply_markup=keyboard,
        )

    @dp.message(Command("myid"))
    async def on_myid(message: Message) -> None:
        await message.answer(
            f"Bu chat ID: <code>{message.chat.id}</code>\n"
            "Buyurtmalar shu chatga kelishi uchun uni .env faylidagi ADMIN_CHAT_ID ga yozing."
        )

    @dp.message(F.web_app_data)
    async def on_order(message: Message) -> None:
        try:
            order = parse_order(message.web_app_data.data, load_catalog())
        except OrderError as e:
            await message.answer(f"❌ {e}\nIltimos, do'konni qayta ochib urinib ko'ring.", reply_markup=keyboard)
            return

        user = message.from_user
        number = save_order(order, user.id, orders_path)
        log.info("Yangi buyurtma #%s, jami %s", number, order.total)

        if admin_chat_id:
            try:
                await message.bot.send_message(
                    admin_chat_id, format_admin(order, number, user.id, user.full_name, user.username)
                )
            except Exception:
                log.exception("Buyurtmani admin chatga yuborib bo'lmadi (ADMIN_CHAT_ID=%s)", admin_chat_id)
        else:
            log.warning("ADMIN_CHAT_ID yozilmagan — buyurtma #%s faqat orders.jsonl ga saqlandi", number)

        await message.answer(format_customer(order, number), reply_markup=keyboard)

    return dp


async def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    token = os.getenv("BOT_TOKEN", "").strip()
    webapp_url = os.getenv("WEBAPP_URL", "").strip()
    admin_raw = os.getenv("ADMIN_CHAT_ID", "").strip()

    if not token:
        raise SystemExit("BOT_TOKEN topilmadi. .env faylini to'ldiring (README.md ga qarang).")
    if not webapp_url.startswith("https://"):
        raise SystemExit("WEBAPP_URL https:// bilan boshlanishi kerak (README.md ga qarang).")
    admin_chat_id = int(admin_raw) if admin_raw else None
    if admin_chat_id is None:
        log.warning("ADMIN_CHAT_ID yozilmagan. Botga /myid yuboring va chiqqan raqamni .env ga yozing.")

    bot = Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = create_dispatcher(webapp_url, admin_chat_id)
    log.info("Bot ishga tushdi. To'xtatish uchun Ctrl+C bosing.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
