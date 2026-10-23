# Yo'lda — restoran backend integratsiyasi

Mijoz restoran saytida buyurtma bergach, restoran **backendi** Yo'lda'ning `orders` API'siga bitta HTTP so'rov yuboradi:
mijoz ma'lumotlari, manzil, taomlar va to'lov. Kuryerni topish va yetkazishni Yo'lda o'zi boshqaradi.

- **Baza URL:** `https://<yolda-server>/api/v1`
- Barcha so'rov/javoblar JSON (UTF-8). Summalar — **so'mda, butun son**.

## 1. API kalit
Yo'lda sizga `yl_live_` bilan boshlanadigan kalit beradi (`yl_live_` + 32 belgi). Restoran aynan shu kalit orqali aniqlanadi —
so'rovda `restaurant_id` yuborilmaydi.

- Kalitni **faqat serveringizda** saqlang (masalan `.env` → `YOLDA_KEY`). Brauzer/mobil ilova kodiga qo'ymang.
- Yo'qotilsa yoki oshkor bo'lsa, Yo'lda'dan yangisini so'rang (eskisi darhol ishlamay qoladi).
- Limit: kalit uchun **60 so'rov/daqiqa** (oshsa `429`).

Har so'rovda:
```
Authorization: Bearer yl_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Content-Type: application/json
```

## 2. Buyurtma yuborish — `POST /orders`
Mijoz buyurtma berganda (to'lov holati ma'lum bo'lgach) chaqiring.

```bash
curl -X POST https://<yolda-server>/api/v1/orders \
  -H "Authorization: Bearer $YOLDA_KEY" -H "Content-Type: application/json" -d '{
  "external_id": "ORD-20451",
  "customer": {"name": "Dilnoza A.", "phone": "+998901234567"},
  "address": {"text": "Yunusobod 4-kvartal, 12-uy, 34-xonadon", "district": "Yunusobod", "lat": 41.3650, "lng": 69.2890},
  "items": [{"name": "Kapuchino", "qty": 2, "price": 25000}, {"name": "Cheesecake", "qty": 1, "price": 35000}],
  "payment": {"method": "Payme", "status": "paid"},
  "note": "Domofon ishlamaydi, qo'ng'iroq qiling"
}'
```

| maydon | majburiy | izoh |
|---|---|---|
| `external_id` | ha | sizdagi buyurtma raqami (sizning restoraningiz ichida unikal), ≤100 belgi |
| `customer.name` | ha | mijoz ismi |
| `customer.phone` | ha | mijoz telefoni (`+998…`) |
| `address.text` | ha | to'liq manzil (ko'cha, uy, xonadon) |
| `address.district` | yo'q | tuman |
| `address.lat`, `address.lng` | tavsiya | mijoz koordinatasi. Bo'lsa masofa va yetkazish haqi avtomatik hisoblanadi |
| `items[]` | ha (≥1) | `name`, `qty` (≥1), `price` (bitta birlik narxi, so'm) |
| `payment.method` | ha | `Payme` \| `Click` \| `Karta` \| `Naqd` |
| `payment.status` | yo'q | `paid` (standart) \| `pending`. `Naqd` da e'tiborga olinmaydi (kuryer mijozdan oladi) |
| `note` | yo'q | kuryerga izoh, ≤500 belgi |
| `delivery_fee` | koordinata bo'lmasa | yetkazish haqi (so'm). Koordinata yo'q bo'lsa **majburiy** |

`subtotal`, `total` va yetkazish haqini server hisoblaydi — o'zingiz jami summani yubormang.

**Javob `201`:**
```json
{"id": 118452, "external_id": "ORD-20451", "status": "new", "status_text": "Kuryer kutilmoqda",
 "delivery_fee": 12000, "total": 97000, "subtotal": 85000, "distance_km": 3.2, "pay_status": "paid"}
```

**Idempotentlik:** shu `external_id` bilan buyurtma allaqachon bo'lsa, yangisi yaratilmaydi — mavjudi `200` bilan qaytadi.
Tarmoq xatosi/timeout bo'lsa so'rovni xavfsiz qayta yuboravering.

> `payment.status = "pending"` bo'lsa kuryer berilmaydi, to'lovni 4-bo'limdagi so'rov bilan tasdiqlang.

## 3. Buyurtma holatini olish — `GET /orders/{external_id}`
Kuzatuv sahifasi uchun (15–30 soniyada bir so'rash yetarli).
```json
{"id": 118452, "external_id": "ORD-20451", "status": "assigned", "status_text": "Kuryer restoranga yo'lda",
 "pay_status": "paid", "delivery_fee": 12000, "total": 97000, "subtotal": 85000, "distance_km": 3.2,
 "courier": {"name": "Sardor Karimov", "phone": "901234567"}, "eta_min": 18, "cancel_reason": null,
 "times": {"created_at": "...", "assigned_at": "...", "picked_at": null, "delivered_at": null, "cancelled_at": null}}
```
`status`: `new` (kuryer kutilmoqda) → `assigned` (kuryer restoranga yo'lda) → `onway` (mijozga yo'lda) → `delivered` (yetkazildi); `cancelled` (bekor qilindi).
`courier` va `eta_min` kuryer biriktirilguncha `null`.

## 4. To'lovni tasdiqlash — `POST /orders/{external_id}/payment`
Buyurtmani `"status": "pending"` bilan yuborgan bo'lsangiz:
- `{"status": "paid"}` — to'lov o'tdi, kuryer qidirish boshlanadi;
- `{"status": "failed"}` — to'lov o'tmadi, buyurtma avtomatik bekor qilinadi.

## 5. Bekor qilish — `POST /orders/{external_id}/cancel`
```json
{"reason": "Mijoz bekor qildi"}
```
Faqat kuryer buyurtmani olib ketmasdan oldin mumkin; aks holda `409`.

## 6. Yetkazish narxi (ixtiyoriy) — `GET /quote?lat=..&lng=..`
Savatda yetkazish narxini ko'rsatish uchun: `{"distance_km": 3.2, "delivery_fee": 12000, "eta_min": 31}`.

## 7. Restoran holati (ixtiyoriy) — `POST /restaurant/status`
`{"status": "paused", "reason": "Oshxona yopildi"}` yoki `{"status": "open"}`.
Pauza paytida yangi buyurtmalar `409` qaytaradi.

## 8. Webhook (ixtiyoriy)
Webhook URL'ingizni Yo'lda'ga bersangiz, buyurtma holati o'zgarganda u yerga `POST` keladi:
```json
{"event": "order.status_changed", "external_id": "ORD-20451", "status": "onway", "status_text": "Mijozga yo'lda",
 "courier": {"name": "Sardor Karimov", "phone": "901234567"}, "at": "2026-10-17T10:15:00+00:00"}
```
Header: `X-Yolda-Signature: sha256=<HMAC-SHA256(webhook_secret, xom_body)>`. **Imzoni tekshiring** (`webhook_secret` sizga
alohida beriladi). 2xx qaytmasa 3 marta qayta uriniladi (10 s, 60 s, 5 daqiqadan keyin).

Python: `hmac.compare_digest("sha256=" + hmac.new(secret, raw_body, "sha256").hexdigest(), header)`

## 9. Xato kodlari
Format: `{"detail": "xabar"}` (422 da qo'shimcha `field`).

| kod | ma'nosi |
|---|---|
| 200 | muvaffaqiyat (yoki idempotent takror) |
| 201 | buyurtma yaratildi |
| 401 | kalit yuborilmagan yoki noto'g'ri |
| 404 | buyurtma topilmadi |
| 409 | restoran pauzada / buyurtmani bekor qilib bo'lmaydi / to'lov holati mos emas |
| 422 | maydonlar noto'g'ri (masalan koordinata ham, `delivery_fee` ham yo'q) |
| 429 | limit oshdi (60 so'rov/daqiqa) |

Tavsiya: `5xx` yoki timeout bo'lsa, shu `external_id` bilan 2–3 marta qayta urining (idempotent).

## 10. Kod namunalari

**Node.js (18+)**
```js
const res = await fetch("https://YOLDA_SERVER/api/v1/orders", {
  method: "POST",
  headers: { Authorization: `Bearer ${process.env.YOLDA_KEY}`, "Content-Type": "application/json" },
  body: JSON.stringify({
    external_id: "ORD-20451",
    customer: { name: "Dilnoza A.", phone: "+998901234567" },
    address: { text: "Yunusobod 4-kvartal, 12-uy", district: "Yunusobod", lat: 41.365, lng: 69.289 },
    items: [{ name: "Kapuchino", qty: 2, price: 25000 }],
    payment: { method: "Payme", status: "paid" },
  }),
});
console.log(res.status, await res.json()); // 201 { id: 118452, ... }
```

**PHP**
```php
<?php
$payload = ["external_id" => "ORD-20451",
  "customer" => ["name" => "Dilnoza A.", "phone" => "+998901234567"],
  "address" => ["text" => "Yunusobod 4-kvartal, 12-uy", "district" => "Yunusobod", "lat" => 41.3650, "lng" => 69.2890],
  "items" => [["name" => "Kapuchino", "qty" => 2, "price" => 25000]],
  "payment" => ["method" => "Payme", "status" => "paid"]];
$ch = curl_init("https://YOLDA_SERVER/api/v1/orders");
curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 10,
  CURLOPT_HTTPHEADER => ["Authorization: Bearer " . getenv("YOLDA_KEY"), "Content-Type: application/json"],
  CURLOPT_POSTFIELDS => json_encode($payload, JSON_UNESCAPED_UNICODE)]);
$res = curl_exec($ch);
echo curl_getinfo($ch, CURLINFO_HTTP_CODE), " ", $res;   // 201 {"id":118452,...}
```

**Python (requests)**
```python
import os, requests
r = requests.post("https://YOLDA_SERVER/api/v1/orders", timeout=10,
    headers={"Authorization": f"Bearer {os.environ['YOLDA_KEY']}"},
    json={"external_id": "ORD-20451",
          "customer": {"name": "Dilnoza A.", "phone": "+998901234567"},
          "address": {"text": "Yunusobod 4-kvartal, 12-uy", "district": "Yunusobod", "lat": 41.365, "lng": 69.289},
          "items": [{"name": "Kapuchino", "qty": 2, "price": 25000}],
          "payment": {"method": "Payme", "status": "paid"}})
print(r.status_code, r.json())   # 201 {'id': 118452, ...}
```

## 11. Integratsiya tartibi (qisqacha)
1. Yo'lda'dan API kalit (`yl_live_…`) va server URL oling.
2. Mijoz buyurtma berib, to'lov holati aniq bo'lgach — backend `POST /orders` yuboradi.
3. `201`/`200` kelsa — buyurtma Yo'lda'da; holatni `GET /orders/{external_id}` yoki webhook orqali kuzating.
4. Xato bo'lsa 9-bo'limga qarang; `5xx`/timeout'da qayta yuboring.
