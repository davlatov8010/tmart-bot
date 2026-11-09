# T-MART — Telegram bot va Mini App

Mijoz botda **«🛒 Do'konni ochish»** tugmasini bosadi → ramyonlarni tanlaydi → ism, telefon, manzilni yozadi → buyurtma sizning Telegram chatingizga keladi. To'lov — yetkazib berishda (naqd yoki Click/Payme orqali qo'lda).

## Fayllar

| Fayl | Nima uchun |
|---|---|
| `docs/products.json` | **Mahsulotlar ro'yxati va narxlar** — shu faylni tahrirlaysiz |
| `docs/img/` | Mahsulot rasmlari (o'zingiz qo'shasiz) |
| `docs/index.html`, `style.css`, `app.js` | Mini App (do'kon sahifasi) |
| `bot.py`, `orders.py` | Bot |
| `.env` | Maxfiy sozlamalar (token) — **hech kimga bermang** |
| `orders.jsonl` | Barcha buyurtmalar tarixi (bot o'zi yaratadi) |

---

## 1-qadam. Bot yaratish (BotFather)

1. Telegram'da **@BotFather** ga yozing → `/newbot` → bot nomi (masalan `T-MART`) va username (masalan `tmart_ramen_bot`).
2. BotFather sizga **token** beradi (`123456789:AA...` ko'rinishida).
3. ⚠️ Tokenni hech kimga yubormang va chatlarga yozmang — u faqat `.env` fayliga yoziladi (3-qadam).

## 2-qadam. Mini App'ni GitHub Pages'ga joylash (bepul HTTPS)

1. [github.com](https://github.com) da ro'yxatdan o'ting.
2. Yangi repository yarating, masalan `tmart-bot` (**Public**).
3. **Add file → Upload files** orqali shu papkadagi hamma narsani yuklang (`.env` faylidan **tashqari**!).
4. Repository → **Settings → Pages** → *Source*: **Deploy from a branch**, *Branch*: `main`, papka: **`/docs`** → **Save**.
5. 1–2 daqiqadan so'ng manzil chiqadi: `https://USERNAME.github.io/tmart-bot/` — bu sizning **WEBAPP_URL**.

## 3-qadam. Botni kompyuterda ishga tushirish

1. [python.org](https://www.python.org/downloads/) dan Python 3.10+ o'rnating (o'rnatishda **"Add Python to PATH"** belgisini qo'ying).
2. Shu papkada terminal (PowerShell) oching va kutubxonalarni o'rnating:
   ```bash
   pip install -r requirements.txt
   ```
3. `.env.example` faylidan nusxa oling, nomini **`.env`** qiling va to'ldiring:
   ```
   BOT_TOKEN=BotFather bergan token
   WEBAPP_URL=https://USERNAME.github.io/tmart-bot/
   ADMIN_CHAT_ID=
   ```
4. Botni ishga tushiring:
   ```bash
   python bot.py
   ```
5. Telegram'da botingizga `/myid` yozing → chiqqan raqamni `.env` dagi `ADMIN_CHAT_ID=` ga yozing → botni to'xtating (**Ctrl+C**) va qayta ishga tushiring.
   - Buyurtmalar guruhga kelsin desangiz: botni guruhga qo'shing, guruhda `/myid` yozing (raqam `-100...` bilan boshlanadi).

Tayyor! `/start` bosing → **🛒 Do'konni ochish** → buyurtma bering → buyurtma sizga keladi.

> Bot faqat kompyuter yoqiq va `python bot.py` ishlab turganda javob beradi. Doimiy ishlashi uchun keyinchalik arzon VPS yoki PythonAnywhere kabi xizmatga qo'yish mumkin.

## Mahsulotlarni tahrirlash

`docs/products.json` faylini oching (GitHub'da to'g'ridan-to'g'ri ✏️ tugmasi bilan ham bo'ladi). Har bir mahsulot:

```json
{
  "id": "shin-ramyun",          // takrorlanmas qisqa nom (lotincha, bo'sh joysiz)
  "name": "Shin Ramyun",         // ko'rinadigan nom
  "category": "korea",           // "korea" yoki "china"
  "price": 16000,                // narx, so'mda (bo'sh joysiz)
  "image": "img/shin.jpg",       // rasm; bo'sh qoldirsangiz 🍜 belgisi chiqadi
  "description": "120 g, achchiq",
  "spicy": 2,                    // achchiqlik 0–3 (🌶 soni)
  "available": true              // tugasa false qiling
}
```

- **Rasm qo'shish:** rasmni `docs/img/` papkasiga yuklang (kvadrat, ~600×600, `.jpg`), so'ng `"image": "img/fayl-nomi.jpg"` deb yozing.
- **Sozlamalar** (`settings`): `delivery_fee` — yetkazib berish narxi, `free_delivery_from` — shu summadan oshsa bepul, `min_order` — eng kam buyurtma, `pickup_address` — olib ketish manzili.
- Fayl o'zgargach GitHub'ga saqlang. Bot narxlarni har buyurtmada shu fayldan o'qiydi, shuning uchun **kompyuterdagi nusxani ham yangilang** (yoki ikkala joyda bir xil qiling).
- Vergul va qo'shtirnoqlarga e'tibor bering — xato bo'lsa katalog ochilmaydi. Tekshirish uchun: [jsonlint.com](https://jsonlint.com).

## Muhim eslatmalar

- Buyurtma faqat **pastki «🛒 Do'konni ochish» tugmasi** orqali ochilgan Mini App'dan keladi (Telegram qoidasi). Boshqa joydan ochilsa, sahifa shu haqda ogohlantiradi.
- Narxlar botda qayta hisoblanadi — mijoz narxni o'zgartirib yubora olmaydi.

## Test (dasturchi uchun)

```bash
pip install pytest
python -m pytest tests
```

Mini App'ni brauzerda ko'rish: `python -m http.server 8765 --directory docs` → `http://localhost:8765` (Telegram'siz «test rejimi»da ishlaydi).
"# tmart-bot" 
