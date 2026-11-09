"""Lokal testlar: python -m pytest tests"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import SendMessage
from aiogram.types import Chat, Message, Update

from bot import create_dispatcher
from orders import OrderError, format_admin, load_catalog, parse_order

CATALOG = load_catalog()


def payload(**kw):
    data = {
        "v": 1,
        "items": [["shin-ramyun", 2], ["luosifen", 1]],
        "name": "Aziz",
        "phone": "+998 90 123 45 67",
        "delivery": "delivery",
        "address": "Toshkent, Chilonzor 5, 12-uy",
        "comment": "",
    }
    data.update(kw)
    return json.dumps(data)


def test_valid_order_totals():
    o = parse_order(payload(), CATALOG)
    assert o.subtotal == 2 * 16000 + 32000
    assert o.delivery_fee == 15000
    assert o.total == 64000 + 15000


def test_free_delivery_and_pickup():
    big = parse_order(payload(items=[["luosifen", 7]]), CATALOG)
    assert big.delivery_fee == 0
    pick = parse_order(payload(delivery="pickup", address=""), CATALOG)
    assert pick.delivery_fee == 0 and pick.address == ""


def test_duplicates_are_merged():
    o = parse_order(payload(items=[["shin-ramyun", 1], ["shin-ramyun", 2]]), CATALOG)
    assert len(o.lines) == 1 and o.lines[0].qty == 3


@pytest.mark.parametrize("kw", [
    {"items": []},
    {"items": [["no-such", 1]]},
    {"items": [["tomato-egg-noodles", 1]]},  # available: false
    {"items": [["shin-ramyun", 0]]},
    {"items": [["shin-ramyun", 100]]},
    {"items": [["shin-ramyun", 1]]},  # min_order dan kam
    {"name": "A"},
    {"phone": "123"},
    {"delivery": "drone"},
    {"address": ""},
])
def test_invalid_orders(kw):
    with pytest.raises(OrderError):
        parse_order(payload(**kw), CATALOG)


def test_garbage_input():
    for raw in ["", "not json", "[]", '{"items": "x"}']:
        with pytest.raises(OrderError):
            parse_order(raw, CATALOG)


def test_admin_text_escapes_html():
    o = parse_order(payload(name="<b>Hacker</b>", comment="<script>"), CATALOG)
    text = format_admin(o, 1, 42, "Ali <x>", "ali")
    assert "<b>Hacker</b>" not in text and "&lt;b&gt;Hacker" in text
    assert "&lt;script&gt;" in text


# ---- Botni Telegram'siz test qilish: so'rovlarni ushlab qoluvchi sessiya ----
class FakeSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.sent = []

    async def make_request(self, bot, method, timeout=None):
        self.sent.append(method)
        if isinstance(method, SendMessage):
            return Message(message_id=len(self.sent), date=datetime.now(),
                           chat=Chat(id=method.chat_id, type="private"), text=method.text)
        return True

    async def stream_content(self, *a, **kw):
        yield b""

    async def close(self):
        pass


def make_update(update_id, user_id, **message_fields):
    return Update.model_validate({
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "date": int(datetime.now().timestamp()),
            "chat": {"id": user_id, "type": "private"},
            "from": {"id": user_id, "is_bot": False, "first_name": "Aziz", "username": "aziz"},
            **message_fields,
        },
    })


def test_bot_flow(tmp_path):
    async def run():
        session = FakeSession()
        bot = Bot("123456:TEST", session=session)
        dp = create_dispatcher("https://example.github.io/tmart/", admin_chat_id=999, orders_path=tmp_path / "o.jsonl")

        await dp.feed_update(bot, make_update(1, 555, text="/start"))
        start = session.sent[-1]
        assert start.chat_id == 555 and "T-MART" in start.text
        assert start.reply_markup.keyboard[0][0].web_app.url == "https://example.github.io/tmart/"

        await dp.feed_update(bot, make_update(2, 555, text="/myid"))
        assert "555" in session.sent[-1].text

        session.sent.clear()
        await dp.feed_update(bot, make_update(3, 555, web_app_data={"data": payload(), "button_text": "x"}))
        admin, customer = session.sent
        assert admin.chat_id == 999 and "Yangi buyurtma #1" in admin.text and "79 000" in admin.text
        assert customer.chat_id == 555 and "qabul qilindi" in customer.text
        assert json.loads((tmp_path / "o.jsonl").read_text("utf-8"))["total"] == 79000

        session.sent.clear()
        await dp.feed_update(bot, make_update(4, 555, web_app_data={"data": payload(items=[]), "button_text": "x"}))
        assert len(session.sent) == 1 and "❌" in session.sent[0].text

    asyncio.run(run())
