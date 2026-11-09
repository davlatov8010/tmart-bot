"""Buyurtmalarni tekshirish, hisoblash va xabar matnini tayyorlash.

Narxlar Mini App'dan emas, docs/products.json faylidan olinadi —
shuning uchun mijoz narxni o'zgartirib yubora olmaydi.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from html import escape
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PRODUCTS_PATH = BASE_DIR / "docs" / "products.json"
ORDERS_PATH = BASE_DIR / "orders.jsonl"

CATEGORY_LABELS = {"korea": "🇰🇷 Koreya", "china": "🇨🇳 Xitoy"}
MAX_QTY = 99


class OrderError(ValueError):
    """Mijozga ko'rsatiladigan xato matni."""


@dataclass
class OrderLine:
    product: dict
    qty: int

    @property
    def total(self) -> int:
        return self.product["price"] * self.qty


@dataclass
class Order:
    lines: list[OrderLine]
    name: str
    phone: str
    delivery: str  # "delivery" yoki "pickup"
    address: str
    comment: str
    subtotal: int
    delivery_fee: int
    currency: str = "so'm"
    pickup_address: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def total(self) -> int:
        return self.subtotal + self.delivery_fee


def load_catalog(path: Path = PRODUCTS_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def money(amount: int, currency: str = "so'm") -> str:
    return f"{amount:,}".replace(",", " ") + f" {currency}"


def _text(data: dict, key: str, max_len: int) -> str:
    value = data.get(key, "")
    if not isinstance(value, str):
        raise OrderError("Buyurtma ma'lumotlari noto'g'ri.")
    value = value.strip()
    if len(value) > max_len:
        raise OrderError("Matn juda uzun.")
    return value


def parse_order(raw: str, catalog: dict) -> Order:
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        raise OrderError("Buyurtma ma'lumotlari noto'g'ri.") from None
    if not isinstance(data, dict):
        raise OrderError("Buyurtma ma'lumotlari noto'g'ri.")

    settings = catalog.get("settings", {})
    products = {p["id"]: p for p in catalog.get("products", [])}

    raw_items = data.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise OrderError("Savatcha bo'sh.")

    quantities: dict[str, int] = {}
    for item in raw_items:
        if not (isinstance(item, list) and len(item) == 2):
            raise OrderError("Buyurtma ma'lumotlari noto'g'ri.")
        pid, qty = item
        if not isinstance(pid, str) or not isinstance(qty, int) or isinstance(qty, bool):
            raise OrderError("Buyurtma ma'lumotlari noto'g'ri.")
        product = products.get(pid)
        if product is None:
            raise OrderError("Savatchadagi mahsulot endi sotuvda yo'q. Savatchani yangilang.")
        if not product.get("available", True):
            raise OrderError(f"«{product['name']}» hozir mavjud emas.")
        if qty < 1:
            raise OrderError("Mahsulot soni noto'g'ri.")
        quantities[pid] = quantities.get(pid, 0) + qty
        if quantities[pid] > MAX_QTY:
            raise OrderError(f"Bitta mahsulotdan ko'pi bilan {MAX_QTY} dona buyurtma qilish mumkin.")

    lines = [OrderLine(products[pid], qty) for pid, qty in quantities.items()]

    name = _text(data, "name", 64)
    if len(name) < 2:
        raise OrderError("Ismingizni kiriting.")

    phone = _text(data, "phone", 32)
    digits = re.sub(r"\D", "", phone)
    if not 9 <= len(digits) <= 15:
        raise OrderError("Telefon raqami noto'g'ri.")

    delivery = data.get("delivery")
    if delivery not in ("delivery", "pickup"):
        raise OrderError("Yetkazib berish turini tanlang.")

    address = _text(data, "address", 300)
    if delivery == "delivery" and len(address) < 5:
        raise OrderError("Yetkazib berish manzilini kiriting.")
    if delivery == "pickup":
        address = ""

    comment = _text(data, "comment", 300)

    subtotal = sum(line.total for line in lines)
    min_order = int(settings.get("min_order", 0))
    currency = settings.get("currency", "so'm")
    if subtotal < min_order:
        raise OrderError(f"Eng kam buyurtma summasi — {money(min_order, currency)}.")

    fee = 0
    if delivery == "delivery":
        free_from = settings.get("free_delivery_from")
        if not (free_from and subtotal >= int(free_from)):
            fee = int(settings.get("delivery_fee", 0))

    return Order(
        lines=lines,
        name=name,
        phone=phone,
        delivery=delivery,
        address=address,
        comment=comment,
        subtotal=subtotal,
        delivery_fee=fee,
        currency=currency,
        pickup_address=settings.get("pickup_address", ""),
    )


def _lines_text(order: Order) -> str:
    rows = []
    for i, line in enumerate(order.lines, 1):
        p = line.product
        rows.append(
            f"{i}. {escape(p['name'])} — {line.qty} × {money(p['price'], order.currency)}"
            f" = <b>{money(line.total, order.currency)}</b>"
        )
    return "\n".join(rows)


def _totals_text(order: Order) -> str:
    rows = [f"Mahsulotlar: {money(order.subtotal, order.currency)}"]
    if order.delivery == "delivery":
        fee = money(order.delivery_fee, order.currency) if order.delivery_fee else "bepul"
        rows.append(f"Yetkazib berish: {fee}")
    rows.append(f"<b>Jami: {money(order.total, order.currency)}</b>")
    return "\n".join(rows)


def format_admin(order: Order, number: int, user_id: int, full_name: str, username: str | None) -> str:
    user = f'<a href="tg://user?id={user_id}">{escape(full_name)}</a>'
    if username:
        user += f" (@{escape(username)})"
    if order.delivery == "delivery":
        delivery = f"🚚 Yetkazib berish\n📍 {escape(order.address)}"
    else:
        delivery = "🏪 O'zi olib ketadi"
    parts = [
        f"🛒 <b>Yangi buyurtma #{number}</b>",
        f"🕒 {order.created_at:%d.%m.%Y %H:%M}",
        "",
        f"👤 {escape(order.name)}",
        f"📞 {escape(order.phone)}",
        f"💬 Telegram: {user}",
        delivery,
    ]
    if order.comment:
        parts.append(f"📝 {escape(order.comment)}")
    parts += ["", _lines_text(order), "", _totals_text(order)]
    return "\n".join(parts)


def format_customer(order: Order, number: int) -> str:
    if order.delivery == "delivery":
        delivery = f"🚚 Manzil: {escape(order.address)}"
    else:
        delivery = "🏪 O'zingiz olib ketasiz"
        if order.pickup_address:
            delivery += f": {escape(order.pickup_address)}"
    return "\n".join([
        f"✅ <b>Buyurtmangiz qabul qilindi! (#{number})</b>",
        "",
        _lines_text(order),
        "",
        _totals_text(order),
        delivery,
        "",
        "Tez orada operatorimiz siz bilan bog'lanadi. Rahmat! 🍜",
    ])


def save_order(order: Order, user_id: int, path: Path = ORDERS_PATH) -> int:
    """Buyurtmani orders.jsonl fayliga yozadi va uning raqamini qaytaradi."""
    path = Path(path)
    number = 1
    if path.exists():
        with path.open(encoding="utf-8") as f:
            number = sum(1 for line in f if line.strip()) + 1
    record = {
        "number": number,
        "created_at": order.created_at.isoformat(timespec="seconds"),
        "user_id": user_id,
        "name": order.name,
        "phone": order.phone,
        "delivery": order.delivery,
        "address": order.address,
        "comment": order.comment,
        "items": [[l.product["id"], l.product["name"], l.qty, l.product["price"]] for l in order.lines],
        "delivery_fee": order.delivery_fee,
        "total": order.total,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return number
