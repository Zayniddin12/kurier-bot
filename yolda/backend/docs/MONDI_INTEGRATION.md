# Mondi sayti ↔ Yo'lda: ulanish qo'llanmasi

Bu hujjat Mondi veb-sayti dasturchisi uchun. Maqsad: mijoz saytdan buyurtma bergach, buyurtma Yo'lda'ga tushsin va
kuryer biriktirilsin. To'liq API ma'lumotnomasi: [INTEGRATION.md](INTEGRATION.md).

## 1. Umumiy sxema

```
Mijoz brauzeri ──▶ Mondi backend (sizning server) ──(Bearer yl_live_…)──▶ Yo'lda API
                                                                               │
                         Mondi backend ◀── holat (GET yoki webhook) ───────────┘
```

**Muhim qoidalar**
1. Yo'lda'ga so'rovni **faqat Mondi backend'i (server)** yuboradi. Brauzerdan (JavaScript) to'g'ridan-to'g'ri yubormang.
2. `yl_live_…` kalit maxfiy: faqat server `.env` da turadi. Frontend kodiga, GitHub'ga, chatga qo'ymang.
3. Brauzerdan yuborilmagani uchun **CORS kerak emas** (Yo'lda begona saytlarga CORS ruxsat bermaydi, bu ataylab).
4. Kalit yo'qolsa yoki oshkor bo'lsa, Yo'lda operatori panelda uni yangilaydi, eskisi darhol ishlamay qoladi.

## 2. Ulanish ma'lumotlari

| | |
|---|---|
| Baza URL | `https://yolda-api.2-31-28-150.sslip.io/api/v1` |
| Swagger (sinab ko'rish) | https://yolda-api.2-31-28-150.sslip.io/docs |
| Kalit | `yl_live_…` (Yo'lda operatori beradi; Mondi kafe restoraniga bog'langan) |
| Sarlavhalar | `Authorization: Bearer <kalit>` va `Content-Type: application/json` |
| Limit | 60 so'rov/daqiqa (oshsa `429`) |

Mondi backend `.env`:
```
YOLDA_BASE=https://yolda-api.2-31-28-150.sslip.io/api/v1
YOLDA_KEY=yl_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> Domen keyinroq o'zgarsa, faqat `YOLDA_BASE` o'zgaradi. URL'ni kodga qotirmang.

## 3. Qadam-baqadam

### Qadam 1. Ulanishni terminaldan tekshiring
```bash
curl -s https://yolda-api.2-31-28-150.sslip.io/api/v1/quote?lat=41.372\&lng=69.285 \
  -H "Authorization: Bearer $YOLDA_KEY"
```
Javob `{"distance_km":…, "delivery_fee":…, "eta_min":…}` bo'lsa, kalit to'g'ri. `401` bo'lsa, kalit xato.

### Qadam 2. Savat sahifasida yetkazish narxi (ixtiyoriy)
Mijoz manzilni tanlagach, Mondi backend'i `GET /quote?lat=..&lng=..` ni chaqiradi va `delivery_fee` ni savatga qo'shib ko'rsatadi.

### Qadam 3. Buyurtmani yuborish
Mijoz buyurtmani tasdiqlaganda (va to'lov bo'lsa, to'lov o'tgach) backend `POST /orders` yuboradi:

```bash
curl -X POST "$YOLDA_BASE/orders" \
  -H "Authorization: Bearer $YOLDA_KEY" -H "Content-Type: application/json" -d '{
  "external_id": "MND-20451",
  "customer": {"name": "Dilnoza A.", "phone": "+998901234567"},
  "address": {"text": "Yunusobod 4-kvartal, 12-uy", "district": "Yunusobod", "lat": 41.3650, "lng": 69.2890},
  "items": [{"name": "Kapuchino", "qty": 2, "price": 25000}],
  "payment": {"method": "Payme", "status": "paid"},
  "note": "Domofon ishlamaydi"
}'
```

| Maydon | Qoida |
|---|---|
| `external_id` | Mondi'dagi buyurtma raqami, takrorlanmasligi kerak |
| `address.lat/lng` | Yuboring: masofa va yetkazish haqi Yo'lda'da hisoblanadi. Yubormasangiz `delivery_fee` (so'm) majburiy |
| `payment.method` | `Payme`, `Click`, `Karta`, `Naqd` |
| `payment.status` | `paid` yoki `pending`. `Naqd` bo'lsa kuryer mijozdan pul oladi |
| narxlar | so'mda, butun son |

Javob `201`: `{"id":…, "external_id":"MND-20451", "status":"new", "delivery_fee":…, "total":…}`.
Yo'lda'dagi `id` va `status` ni Mondi bazasida buyurtma yoniga saqlang.

**Takroriy yuborish xavfsiz.** Shu `external_id` bilan buyurtma bor bo'lsa, yangisi yaratilmaydi, mavjudi `200` bilan qaytadi. Tarmoq xatosi bo'lsa, qayta urinavering.

**Qaysi kodda nima qilish kerak**
- `201` / `200`: muvaffaqiyat, buyurtma Yo'lda'da.
- `409`: restoran pauzada. Mijozga "hozir yetkazib berish vaqtincha yo'q" deb ayting.
- `422`: maydonlar noto'g'ri, `field` ga qarang.
- `401`: kalit noto'g'ri, Mondi `.env` ni tekshiring.
- `429` yoki `5xx` / tarmoq xatosi: 2–3 marta qayta urinib ko'ring (har safar `external_id` o'sha-o'sha).

### Qadam 4. Mijozga holatni ko'rsatish
Mondi buyurtma kuzatuv sahifasi uchun ikki yo'ldan birini tanlang.

**A) So'rash (oddiy):** backend har 15–30 soniyada `GET /orders/{external_id}` ni chaqiradi.

`status` qiymatlari:

| status | ma'nosi |
|---|---|
| `new` | Kuryer kutilmoqda |
| `assigned` | Kuryer restoranga yo'lda |
| `onway` | Mijozga yo'lda |
| `delivered` | Yetkazildi |
| `cancelled` | Bekor qilindi |

`courier` (ism, telefon) va `eta_min` kuryer biriktirilgach to'ladi.

**B) Webhook (tavsiya):** Mondi o'z URL'ini (masalan `https://mondi.uz/api/yolda/webhook`) Yo'lda operatoriga beradi. Holat o'zgarganda Yo'lda shu URL'ga `POST` yuboradi. Imzoni **tekshiring**:

```python
import hmac
ok = hmac.compare_digest(
    "sha256=" + hmac.new(WEBHOOK_SECRET.encode(), raw_body, "sha256").hexdigest(),
    request.headers["X-Yolda-Signature"])
```
`WEBHOOK_SECRET` webhook sozlanganda bir marta ko'rsatiladi. Javob 2xx bo'lmasa, 10 s, 60 s, 5 daqiqadan keyin qayta uriniladi.

### Qadam 5. Pending to'lov, bekor qilish, pauza
- `payment.status = "pending"` yuborgan bo'lsangiz, to'lov o'tgach `POST /orders/{external_id}/payment` ga `{"status":"paid"}` yuboring. Shundan keyin kuryer qidiriladi. `{"status":"failed"}` buyurtmani bekor qiladi.
- Bekor qilish: `POST /orders/{external_id}/cancel` `{"reason":"…"}`. Faqat kuryer olib ketmasidan oldin (`new`/`assigned`), keyin `409`.
- Oshxona yopilganda: `POST /restaurant/status` `{"status":"paused","reason":"Oshxona yopildi"}`; ochilganda `{"status":"open"}`.

## 4. Namuna kod (backend uchun)

**PHP**
```php
<?php
$payload = ["external_id" => "MND-20451",
  "customer" => ["name" => "Dilnoza A.", "phone" => "+998901234567"],
  "address" => ["text" => "Yunusobod 4-kvartal", "lat" => 41.365, "lng" => 69.289],
  "items" => [["name" => "Kapuchino", "qty" => 2, "price" => 25000]],
  "payment" => ["method" => "Payme", "status" => "paid"]];
$ch = curl_init(getenv("YOLDA_BASE") . "/orders");
curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 10,
  CURLOPT_HTTPHEADER => ["Authorization: Bearer " . getenv("YOLDA_KEY"), "Content-Type: application/json"],
  CURLOPT_POSTFIELDS => json_encode($payload)]);
$body = curl_exec($ch); $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
```

**Node.js**
```js
const res = await fetch(`${process.env.YOLDA_BASE}/orders`, {
  method: "POST",
  headers: { Authorization: `Bearer ${process.env.YOLDA_KEY}`, "Content-Type": "application/json" },
  body: JSON.stringify(payload),
  signal: AbortSignal.timeout(10_000),
});
const data = await res.json(); // res.status: 201 | 200 | 409 | 422 ...
```

**Python**
```python
r = requests.post(f"{YOLDA_BASE}/orders", timeout=10, json=payload,
                  headers={"Authorization": f"Bearer {YOLDA_KEY}"})
```

## 5. Ishga tushirishdan oldin tekshiruv ro'yxati
- [ ] `YOLDA_KEY` faqat backend `.env` da, frontend/git'da yo'q
- [ ] `external_id` har buyurtmada unikal va Mondi buyurtma raqamiga teng
- [ ] Koordinatalar yuboriladi (yoki `delivery_fee`)
- [ ] `409`, `422`, `401`, tarmoq xatolari mijozga tushunarli ko'rsatiladi / qayta uriniladi
- [ ] Test buyurtma yuborildi va Yo'lda panelida (https://panel.2-31-28-150.sslip.io) ko'rindi
- [ ] Webhook ishlatilsa, imzo tekshiriladi

## 6. Savol-javob
**CORS ruxsat kerakmi?** Yo'q. So'rov brauzerdan emas, serverdan ketadi.

**Kalitni brauzerga qo'ysam bo'ladimi?** Yo'q. Uni har kim ko'rib, Mondi nomidan buyurtma yubora oladi.

**Buyurtma `new` da qotib qoldi.** Smenada kuryer yo'q yoki hammasi band. Operator panelda kuryerlarni tekshiradi.

**Sinab ko'rish uchun?** Swagger'da (`/docs`) *Authorize* ga kalitni kiriting. Test buyurtmani keyin `cancel` qiling, shunda kuryerga tushmaydi.
