# Yo'lda — restoran integratsiyasi (`/api/v1`)

Restoran o'z saytida savat va to'lovni o'zi boshqaradi. Buyurtma tayyor bo'lgach **bitta HTTP so'rov** yuboradi — qolganini
Yo'lda hal qiladi (kuryerni avtomatik topadi, yo'lda holatni yangilab turadi).

- **Baza URL:** `https://<yolda-server>/api/v1` (lokal: `http://localhost:8000/api/v1`)
- **Hujjat (Swagger):** `https://<yolda-server>/docs`
- Barcha so'rov/javoblar JSON, UTF-8. Summalar — **so'mda, butun son** (tiyinsiz).

## 1. API kalitni qayerdan olish
Operator panelida **Restoranlar → restoran kartasi → Integratsiya → "Kalitni yangilash"** (yoki yangi restoran ulanganda
natija oynasida). Kalit `yl_live_` + 32 belgi. **U faqat bir marta to'liq ko'rsatiladi** — xavfsiz joyda (server `.env`) saqlang.
Restoran o'zida tayyor `yl_live_` + 32 belgili kalit bo'lsa, operator uni *Restoran ulash* oynasidagi "API kaliti" maydoniga kiritadi — platforma yangi kalit yaratmaydi (kalit boshqa restoranga ulangan bo'lsa `409`). Yo'qotsangiz — kalitni yangilang (eskisi darhol ishlamay qoladi). Kalitni brauzer (frontend) kodiga qo'ymang: so'rovlarni faqat serveringizdan yuboring.

Har so'rovga:
```
Authorization: Bearer yl_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Content-Type: application/json
```
Restoran kalit orqali aniqlanadi — `restaurant_id` yuborilmaydi. **Limit:** kalit uchun 60 so'rov/daqiqa (oshsa `429`).

## 2. Buyurtma yaratish — `POST /orders`
```bash
curl -X POST https://<server>/api/v1/orders \
  -H "Authorization: Bearer $YOLDA_KEY" -H "Content-Type: application/json" -d '{
  "external_id": "MND-20451",
  "customer": {"name": "Dilnoza A.", "phone": "+998901234567"},
  "address": {"text": "Yunusobod 4-kvartal, 12-uy, 34-xonadon", "district": "Yunusobod", "lat": 41.3650, "lng": 69.2890},
  "items": [{"name": "Kapuchino", "qty": 2, "price": 25000}, {"name": "Cheesecake", "qty": 1, "price": 35000}],
  "payment": {"method": "Payme", "status": "paid"},
  "note": "Domofon ishlamaydi, qo'ng'iroq qiling"
}'
```
| maydon | izoh |
|---|---|
| `external_id` | sizdagi buyurtma raqami (restoran ichida unikal) |
| `payment.method` | `Payme` \| `Click` \| `Karta` \| `Naqd` |
| `payment.status` | `paid` \| `pending` (`Naqd` uchun e'tiborga olinmaydi — kuryer mijozdan oladi). `pending` bo'lsa kuryer berilmaydi, to'lovni 5-bo'limdagi so'rov bilan tasdiqlang |
| `address.lat/lng` | ixtiyoriy, **tavsiya etiladi**: bo'lsa masofa va yetkazish haqi serverda hisoblanadi. Bo'lmasa `delivery_fee` (so'm) **majburiy**, xaritada mijoz nuqtasi ko'rinmaydi |
| `delivery_fee` | faqat koordinata yo'q bo'lsa |

`subtotal`, `total` va yetkazish haqini server hisoblaydi.

**Javob** `201`:
```json
{"id": 118452, "external_id": "MND-20451", "status": "new", "status_text": "Kuryer kutilmoqda",
 "delivery_fee": 12000, "total": 97000, "subtotal": 85000, "distance_km": 3.2, "pay_status": "paid"}
```
**Idempotentlik:** shu `external_id` bilan buyurtma allaqachon bor bo'lsa — yangisi yaratilmaydi, mavjudi `200` bilan qaytadi.
Tarmoq xatosida so'rovni xavfsiz qayta yuborishingiz mumkin.

## 3. Holatni olish — `GET /orders/{external_id}`
Mondi sayti kuzatuv sahifasi uchun; 15–30 soniyada bir so'rash kifoya.
```json
{"id": 118452, "external_id": "MND-20451", "status": "assigned", "status_text": "Kuryer restoranga yo'lda",
 "pay_status": "paid", "delivery_fee": 12000, "total": 97000,
 "courier": {"name": "Sardor Karimov", "phone": "901234567"}, "eta_min": 18, "cancel_reason": null,
 "times": {"created_at": "...", "assigned_at": "...", "picked_at": null, "delivered_at": null, "cancelled_at": null}}
```
`status`: `new` (Kuryer kutilmoqda) → `assigned` (Kuryer restoranga yo'lda) → `onway` (Mijozga yo'lda) → `delivered` (Yetkazildi); `cancelled` (Bekor qilindi).
`courier` va `eta_min` kuryer biriktirilgandan keyin to'ladi (aks holda `null`).

## 4. Narx so'rash (ixtiyoriy) — `GET /quote?lat=..&lng=..`
Savat sahifasida yetkazish narxini ko'rsatish uchun → `{"distance_km": 3.2, "delivery_fee": 12000, "eta_min": 31}`.

## 5. To'lovni tasdiqlash — `POST /orders/{external_id}/payment`
Dastlab `"status": "pending"` yuborgan bo'lsangiz: `{"status": "paid"}` (taqsimlash boshlanadi) yoki `{"status": "failed"}` (buyurtma avtomatik bekor qilinadi).

## 6. Bekor qilish — `POST /orders/{external_id}/cancel`
`{"reason": "Mijoz bekor qildi"}` — faqat kuryer olib ketmasdan oldin (`new`/`assigned`), aks holda `409`.

## 7. Restoran holati (ixtiyoriy) — `POST /restaurant/status`
`{"status": "paused", "reason": "Oshxona yopildi"}` yoki `{"status": "open"}`. Pauzada yangi buyurtmalar `409` qaytaradi.

## 8. Webhook (ixtiyoriy)
Panelda restoranga `webhook_url` kiritilsa, buyurtma holati o'zgarganda sizning URL'ingizga `POST` yuboriladi:
```json
{"event": "order.status_changed", "external_id": "MND-20451", "status": "onway", "status_text": "Mijozga yo'lda",
 "courier": {"name": "Sardor Karimov", "phone": "901234567"}, "at": "2026-10-17T10:15:00+00:00"}
```
Header: `X-Yolda-Signature: sha256=<HMAC-SHA256(webhook_secret, xom_body)>`. **Imzoni tekshiring** — `webhook_secret` panelda
webhook sozlanganda bir marta ko'rsatiladi. Javob 2xx bo'lmasa 3 marta qayta uriniladi (10 s, 60 s, 5 daqiqadan keyin).

Tekshirish (Python): `hmac.compare_digest("sha256=" + hmac.new(secret, raw_body, "sha256").hexdigest(), header)`.

## 9. Xato kodlari
Format har doim: `{"detail": "o'zbekcha xabar"}` (422 da qo'shimcha `field`).

| kod | ma'nosi |
|---|---|
| 200 | muvaffaqiyat (yoki idempotent takror) |
| 201 | buyurtma yaratildi |
| 401 | kalit yo'q yoki noto'g'ri |
| 404 | buyurtma topilmadi |
| 409 | restoran pauzada / buyurtmani bekor qilib bo'lmaydi / to'lov holati mos emas |
| 422 | so'rov maydonlari noto'g'ri (masalan koordinata ham, `delivery_fee` ham yo'q) |
| 429 | limit: 60 so'rov/daqiqa |

## 10. Kod namunalari — buyurtma yuborish

**PHP**
```php
<?php
$payload = ["external_id" => "MND-20451",
  "customer" => ["name" => "Dilnoza A.", "phone" => "+998901234567"],
  "address" => ["text" => "Yunusobod 4-kvartal, 12-uy", "district" => "Yunusobod", "lat" => 41.3650, "lng" => 69.2890],
  "items" => [["name" => "Kapuchino", "qty" => 2, "price" => 25000]],
  "payment" => ["method" => "Payme", "status" => "paid"]];
$ch = curl_init("https://YOLDA_SERVER/api/v1/orders");
curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 10,
  CURLOPT_HTTPHEADER => ["Authorization: Bearer " . getenv("YOLDA_KEY"), "Content-Type: application/json"],
  CURLOPT_POSTFIELDS => json_encode($payload, JSON_UNESCAPED_UNICODE)]);
$res = curl_exec($ch);
$code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
echo $code, " ", $res;   // 201 {"id":118452,...}
```

**Node.js (18+)**
```js
const res = await fetch("https://YOLDA_SERVER/api/v1/orders", {
  method: "POST",
  headers: { Authorization: `Bearer ${process.env.YOLDA_KEY}`, "Content-Type": "application/json" },
  body: JSON.stringify({
    external_id: "MND-20451",
    customer: { name: "Dilnoza A.", phone: "+998901234567" },
    address: { text: "Yunusobod 4-kvartal, 12-uy", district: "Yunusobod", lat: 41.365, lng: 69.289 },
    items: [{ name: "Kapuchino", qty: 2, price: 25000 }],
    payment: { method: "Payme", status: "paid" },
  }),
});
console.log(res.status, await res.json()); // 201 { id: 118452, ... }
```

**Python (requests)**
```python
import os, requests
r = requests.post("https://YOLDA_SERVER/api/v1/orders", timeout=10,
    headers={"Authorization": f"Bearer {os.environ['YOLDA_KEY']}"},
    json={"external_id": "MND-20451",
          "customer": {"name": "Dilnoza A.", "phone": "+998901234567"},
          "address": {"text": "Yunusobod 4-kvartal, 12-uy", "district": "Yunusobod", "lat": 41.365, "lng": 69.289},
          "items": [{"name": "Kapuchino", "qty": 2, "price": 25000}],
          "payment": {"method": "Payme", "status": "paid"}})
print(r.status_code, r.json())   # 201 {'id': 118452, ...}
```

## 11. Tekshirish
Backend papkasidan: `python scripts/mondi_test_order.py` — test buyurtma yuboradi (kalit `backend/.mondi_key` yoki `YOLDA_API_KEY` dan olinadi).
