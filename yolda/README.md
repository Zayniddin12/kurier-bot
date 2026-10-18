# Yo'lda — yetkazib berish platformasi

Admin panel (Vue 3) + backend (FastAPI) + restoranlar uchun integratsiya API + Telegram kuryer boti (`../kurier-bot`).

```
yolda/
  backend/    FastAPI, SQLAlchemy 2 (async), Alembic, PostgreSQL 16
  frontend/   Vue 3 + Vite + TypeScript
  docker-compose.yml   postgres + backend + bot + frontend
../kurier-bot/   Telegram bot (Node.js, grammY) — backend'ning mijozi
```

## Qanday ishlaydi

```
Restoran sayti ──(Bearer yl_live_…)──▶ POST /api/v1/orders ──▶ Yo'lda backend ──▶ dispatcher
                                                                   │ ▲                │
                                          admin panel (WebSocket) ◀┘ │                ▼
                                                                     │       kuryerga taklif (30 s)
Telegram bot ──(X-Bot-Key: /api/bot/state, har 2 s)──────────────────┘                │
     │  ▲                                                                              │
     ▼  └──── kuryer tugmalari: qabul / ovqatni oldim / yetkazdim  ──▶ /api/courier/* ─┘
  kuryer
```

- **Restoran ulash**: panel → *Restoranlar → Restoran ulash*. Kalitni platforma yaratadi (bir marta ko'rsatiladi) **yoki** restoranning o'zida bor
  `yl_live_…` kalitini maydonga kiritasiz — shu kalit bilan restoran darhol buyurtma yubora oladi. Har bir restoran o'z domenida/serverida bo'lishi mumkin:
  u faqat `https://<yolda-server>/api/v1` ga murojaat qiladi ([INTEGRATION.md](backend/docs/INTEGRATION.md)).
- **Ulangan istalgan restorandan** kelgan buyurtma bir xil yo'l bilan dispatcher orqali Telegramdagi kuryerga boradi (zakazda restoran nomi ko'rinadi).
- **Kuryer**: panel → *Kuryerlar → qo'shish* (telefon + JShShIR). Kuryer botga `/start` yozib, telefon va JShShIR bilan o'z Telegramini ulaydi,
  keyin *Smenani boshlash* + jonli lokatsiya yuboradi. Panelda kuryer kartasida "Telegram bot: Ulangan" ko'rinadi (kerak bo'lsa *Uzish*).

## Ishga tushirish (production, Docker)

```bash
cp .env.example .env        # SECRET_KEY, BOT_API_KEY, BOT_TOKEN, ADMIN_EMAIL, ADMIN_PASSWORD ni to'ldiring
docker compose up -d --build
```
- Panel: http://localhost:8080 · API hujjati: http://localhost:8000/docs
- Birinchi ishga tushishda migratsiyalar qo'llanadi va `ADMIN_EMAIL`/`ADMIN_PASSWORD` bilan administrator yaratiladi (demo ma'lumot **yo'q**).
- Internetga chiqarishda backend (`/api/v1`) va panel oldiga HTTPS reverse-proxy (nginx/Caddy) qo'ying; `CORS_ORIGINS` ga panel domenini yozing.
- Bot — alohida konteyner, faqat chiqish (outbound) ulanish kerak: Telegram va `backend`. Webhook/ochiq port shart emas.

### Demo rejim (faqat sinov)
`SEED_DEMO=true DEMO_SIMULATION=true docker compose up --build` — demo ma'lumot va "jonli" simulyatsiya. Demo loginlar:

| email | parol | rol |
|---|---|---|
| admin@yolda.uz | admin123 | platform_admin |
| operator@yolda.uz | operator123 | operator (Nigora Saidova) |
| mondi@yolda.uz | mondi123 | restaurant_staff (faqat Mondi kafe) |

Mondi test API kaliti: `docker compose logs backend | grep "API kaliti"`

## Lokal ishlab chiqish

```bash
# Postgres (yoki o'zingizniki)
docker compose up -d postgres

cd backend
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env                       # DATABASE_URL, DEMO_SIMULATION ...
.venv/bin/alembic upgrade head             # migratsiya
.venv/bin/python -m app.seed               # demo ma'lumot (qayta yaratish: --reset)
.venv/bin/uvicorn app.main:app --reload --port 8000

cd ../frontend && npm install && npm run dev    # http://localhost:5173
```

### Testlar
```bash
cd backend
createdb -h localhost -U yolda yolda_test                       # bir marta (yoki: docker compose exec postgres createdb -U yolda yolda_test)
.venv/bin/pytest -q                                              # TEST_DATABASE_URL bilan boshqa bazani ko'rsatish mumkin
```
Testlar: pul formulalari, ETA, taqsimlash shartlari (transport/naqd limit/pending), taklif → qabul → yetkazish ledger, navbat,
transport nosozligi, maosh, idempotentlik, webhook imzosi, restaurant_staff izolyatsiyasi.

## Mondi kafe integratsiyasi
- Dasturchi uchun hujjat: [`backend/docs/INTEGRATION.md`](backend/docs/INTEGRATION.md) (curl, PHP, Node.js, Python).
- Test buyurtma: `python backend/scripts/mondi_test_order.py` (kalit seed'dan: `backend/.mondi_key`). Buyurtma panelda 1 soniya ichida paydo bo'ladi.
- Admin API javob shakllari: [`backend/docs/ADMIN_API_SHAPES.md`](backend/docs/ADMIN_API_SHAPES.md).

## Sozlamalar (`backend/.env`)
`DATABASE_URL`, `SECRET_KEY`, `BOT_API_KEY`, `CORS_ORIGINS`, `DEMO_SIMULATION`, `RUN_WORKERS` (dispatcher/webhook loop'larni o'chirish — faqat testlar uchun).
Biznes konstantalari (SLA 45, CASH_LIMIT 400 000, COMMISSION 0.15, BONUS_PER_10 20 000, LATE_FINE 5 000) — `backend/app/config.py`.

## Telegram bot (`../kurier-bot`)
```bash
cd ../kurier-bot && cp .env.example .env     # BOT_TOKEN, BOT_API_KEY (backend bilan bir xil), YOLDA_URL
npm install && npm start
```
Bot o'z bazasiga ega emas: zakaz holati faqat yolda bazasida. Bot `/api/bot/*` (kalit: `X-Bot-Key`) orqali kuryer holatini o'qiydi va kuryer
nomidan qisqa muddatli (10 daq) token bilan mavjud `/api/courier/*` endpointlarini chaqiradi — taqsimlash va hisob-kitob mantiqi bitta joyda.
