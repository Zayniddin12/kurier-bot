# Onlayn to'lov (Multicard) — restoran dasturchisi uchun

Mijoz to'lovini Tez-yetkaz qabul qiladi. Siz Multicard bilan ishlamaysiz — faqat bizning API (`/api/v1`, xuddi
[INTEGRATION.md](INTEGRATION.md) dagi kabi `Authorization: Bearer yl_live_…`). To'lov tushgach buyurtma **avtomatik "to'langan"**
bo'ladi va kuryer qidiruvi boshlanadi.

## Oqim (saytingizda)
1. Checkout sahifasi ochilganda `GET /payment-methods` ni chaqiring va mijozga ro'yxatni ko'rsating:
   ```json
   {"methods": [{"code": "card", "name": "Karta (Uzcard, Humo, Visa, Mastercard)", "type": "card"},
                {"code": "payme", "name": "Payme", "type": "app"}, {"code": "click", "name": "Click", "type": "app"},
                {"code": "uzum", "name": "Uzum Bank", "type": "app"}]}
   ```
   Ro'yxat bizning serverda boshqariladi (`MULTICARD_METHODS`) — yangi usul qo'shilsa, sizning kodingiz o'zgarmaydi.
   Ro'yxat bo'sh bo'lsa, onlayn to'lov hozircha yoqilmagan. Usul logotiplarini o'zingiz qo'ying (`code` bo'yicha).
2. Mijoz usulni tanlagach buyurtmani yuboring: `POST /orders` — `payment: {"method": "Multicard", "system": "payme"}`.
3. Javobdagi `payment.pay_url` ga mijozni yo'naltiring. `card` — Multicard to'lov sahifasi; `app` (Payme/Click/Uzum…) — to'g'ridan-to'g'ri
   shu ilovaga (universal link).
4. Mijoz to'laydi → pul **Tez-yetkaz hisobiga tushadi** → buyurtma avtomatik `pay_status: "paid"`, kuryer qidiruvi boshlanadi.
5. Sizning `webhook_url` ga `payment.paid` keladi; holatni `GET /orders/{external_id}/payment` bilan ham olish mumkin.
6. Mijoz usulni almashtirmoqchi bo'lsa (yoki to'lov o'tmasa): `POST /orders/{external_id}/pay` `{"method": "click"}` — eski havola bekor
   bo'ladi, yangisi qaytadi.

```json
POST /orders  →  201
{"id": 118452, "external_id": "ORD-1", "status": "new", "pay_status": "pending", "total": 97000, ...,
 "payment": {"payment_id": 7, "method": "payme", "status": "pending", "amount": 97000,
             "pay_url": "https://…", "short_link": null, "expires_at": "2026-11-03T15:00:00+00:00"}}
```

`pay_status: "pending"` bo'lgan buyurtmaga kuryer **berilmaydi**. Havola amal qilish muddati — 1 soat (karta sahifasi uchun).
Buyurtma `payment.method` hisobotlarda haqiqiy usulga o'zgaradi (Payme, Click, Uzum, Karta).

## Endpointlar
| | |
|---|---|
| `GET /payment-methods` | Mijozga ko'rsatiladigan usullar ro'yxati |
| `POST /orders/{external_id}/pay` | Havolani yaratadi/qaytaradi. Body: `{"method": "card\|payme\|click\|uzum…", "return_url", "return_error_url", "lang": "uz\|ru\|en"}`. **Idempotent**: shu usulda faol havola bo'lsa o'sha qaytadi |
| `GET /orders/{external_id}/payment` | `{pay_status, pay_method, payment: {method, status, pay_url, paid_at, card, receipt_url}}` |

`payment.status`: `pending` · `paid` · `cancelled` · `expired` · `refund_required`.
`POST /orders` da havola olinmasa buyurtma baribir yaratiladi: `payment: null` va `payment_error` bo'ladi — `/pay` ni qayta chaqiring.

## Webhook
Mavjud webhook (`X-Yolda-Signature`) ga yangi hodisa:
```json
{"event": "payment.paid", "external_id": "ORD-1", "pay_status": "paid", "amount": 97000, "paid_at": "…", "at": "…"}
```

## Bekor qilish va qaytarish
Buyurtma bekor bo'lsa: to'lanmagan havola bekor qilinadi (keyin to'lasa ham pul avtomatik mijozga qaytariladi);
**to'langan** to'lov `refund_required` bo'ladi — qaytarishni operator Multicard kabinetida bajaradi (avtomatik qaytarish keyingi bosqich).

---

## Sozlash (Tez-yetkaz serveri)
`.env` ga (`.env.example` ga qarang): `MULTICARD_BASE_URL`, `MULTICARD_APP_ID`, `MULTICARD_SECRET`, `MULTICARD_STORE_ID`,
`MULTICARD_MXIK`, `MULTICARD_PACKAGE_CODE`, `PUBLIC_API_URL`; ro'yxat: `MULTICARD_METHODS` (standart `card,payme,click,uzum`; yana: `anorbank, alif, oson, xazna, beepul, trastpay`). Hammasi to'ldirilmaguncha `/pay` `503 "To'lov tizimi sozlanmagan"` qaytaradi.
Multicard kabinetida callback manzili avtomatik: `{PUBLIC_API_URL}/api/v1/payments/multicard/callback` (invoys bilan birga yuboriladi).

## Xavfsizlik (callback)
- Imzo: `md5(store_id + invoice_id + amount + secret)`; noto'g'ri imzo → `403`. Ixtiyoriy `MULTICARD_CALLBACK_IPS`.
- Summa bazadagi buyurtma summasi bilan solishtiriladi; mos kelmasa yoki buyurtma bekor bo'lgan/allaqachon to'langan bo'lsa
  `{"success": false}` qaytadi → Multicard pulni mijozga qaytaradi.
- Takroriy callback (shu `uuid`) ikki marta hisoblanmaydi.

## Tasdiqlanmagan joylar (sandbox'da tekshirilsin)
Quyidagilar hujjatning ochiq qismida to'liq berilmagan, shuning uchun kodda taxminga asoslangan; **production'dan oldin sandbox'da sinang**:
1. Ilova to'lovlari (`POST /payment`: Payme/Click/Uzum…) uchun callback formati hujjatda alohida yozilmagan; kod invoys callback'idagi
   kabi (imzo + `invoice_id`) deb kutadi. Har usulda sandbox to'lov qilib tekshiring.
2. Fiskal chek (`ofd`) uchun IKPU (`mxik`) va `package_code` — hamma taomga bitta kod; buxgalter bilan aniqlashtiring.
3. Avtomatik qaytarish va callback yo'qolganda holatni so'rab tekshirish (`GET /invoice/{invoice_id}`) hali yozilmagan.
