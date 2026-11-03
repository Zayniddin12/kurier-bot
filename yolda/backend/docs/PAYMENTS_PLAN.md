# To'lov tizimi (Multicard / Rahmat) — reja

> Holat: **1–4 bosqich bajarildi** (variant A, pul Tez-yetkaz kassasiga tushadi). Restoran uchun qo'llanma: [PAYMENTS.md](PAYMENTS.md).
> Qolgan: panelda to'lov tabi, avtomatik refund, callback yo'qolsa holatni so'rab tekshirish (worker), sandbox sinovi.

## 1. Maqsad
Har bir restoran uchun to'lov Tez-yetkaz orqali o'tsin:

1. Restoran dasturchisi bizning **bitta API**'ni chaqiradi ("to'lov yarat") → mijoz uchun to'lov havolasi oladi.
2. Mijoz Multicard (Rahmat) orqali to'laydi (karta, Payme, Click va h.k. — Multicard qaysilarini qo'llashiga qarab).
3. To'lov **bizning serverga** kelganda (Multicard callback) buyurtma **avtomatik "to'landi"** bo'ladi va kuryer qidiruvi boshlanadi.
4. Restoranga webhook ketadi (mavjud `X-Yolda-Signature` mexanizmi orqali).

Restoran dasturchisi Multicard bilan to'g'ridan-to'g'ri ishlamaydi — faqat bizning API bilan.

## 2. Hozirgi holat (kodda bor narsa)
- `POST /api/v1/orders` — `payment: {method, status}`; `status = pending` bo'lsa kuryer berilmaydi.
- `POST /api/v1/orders/{external_id}/payment` — restoran to'lovni **qo'lda** tasdiqlaydi (`osvc.set_payment`).
- `orders.pay_method`, `orders.pay_status` (`paid | pending | cod`) maydonlari mavjud.
- Operator panelda "To'lov kutilmoqda" holati bor.
- Restoranga webhook (`services/webhooks.py`, HMAC imzo) mavjud.

Ya'ni asosiy oqim tayyor; **yetishmayotgani** — haqiqiy to'lov provayderi bilan ulanish va avtomatik tasdiqlash.

## 3. Muhim: hal qilinishi kerak bo'lgan savollar (Multicard hujjatidan)
`rhmt.uz/uz/pos/integration/` — faqat marketing sahifasi, **API hujjati yo'q**. Multicard hujjati (`docs.multicard.uz`)
dan faqat umumiy ma'lumot ochiq: sandbox `https://dev-mesh.multicard.uz/`, production `https://mesh.multicard.uz/`,
javoblar `{success, data | error{code,details}}`. Quyidagilar **hujjatdan aniqlanishi shart** (taxmin qilmaymiz):

| # | Savol | Nega muhim |
|---|---|---|
| 1 | Autentifikatsiya (token olish, kalitlar) | Server-to-server chaqiruv |
| 2 | Hisob-faktura/to'lov yaratish endpointi va maydonlari (summa, `invoice_id`, qaytish URL, muddat) | "To'lov yarat" API |
| 3 | Mijoz to'lov havolasi/QR qaytadimi | Restoran saytida ko'rsatish |
| 4 | **Callback** formati va **imzo tekshirish** usuli | Soxta to'lovdan himoya (eng muhim) |
| 5 | To'lov statuslari (kutilmoqda/to'landi/bekor/xato) | Holat xaritasi |
| 6 | Qaytarish (refund) / bekor qilish | Buyurtma bekor bo'lganda |
| 7 | Pul kimga tushadi: bizning merchant hisobga, keyin restoranlarga taqsimlash, yoki split/har restoranga alohida merchant | **Biznes-modelni belgilaydi** (7-bo'lim) |
| 8 | Komissiya, to'lov muddati | Moliya hisobi |
| 9 | Ta'sischi/shartnoma, merchant ID, test kartalar | Production'ga chiqish |

Birinchi qadam: Multicard'dan (`@rhmt_support_bot`, 1865) to'liq API hujjati va sandbox kalitlarini olish.

## 4. Taklif qilinadigan arxitektura

```
Restoran backend ──(1) POST /api/v1/orders/{ext}/pay ──► Tez-yetkaz
                                                          │ (2) invoice yaratish
                                                          ▼
                                                      Multicard
                                                          │
Mijoz ◄───────── to'lov havolasi/QR ──────────────────────┘
Mijoz ──(3) to'laydi ──► Multicard ──(4) callback ──► Tez-yetkaz /api/v1/payments/multicard/callback
                                                          │ imzo tekshiriladi, pay_status=paid
                                                          ▼ kuryer qidiruvi boshlanadi
Restoran backend ◄──(5) webhook (order.paid) ─────────────┘
```

### 4.1 Yangi restoran API
- `POST /api/v1/orders/{external_id}/pay` — to'lov yaratadi. Javob: `{payment_id, pay_url, qr?, expires_at}`. Idempotent
  (qayta chaqirilsa shu faol to'lov qaytadi).
- `GET /api/v1/orders/{external_id}/payment` — to'lov holati (`pending|paid|failed|expired|refunded`).
- `POST /api/v1/orders/{external_id}/refund` — (2-bosqich) qaytarish.
- Mavjud `POST /orders` ga `payment.method = "Multicard"` va `payment.status = "pending"` qo'shiladi: buyurtma yaratilgach
  javobda to'g'ridan-to'g'ri `pay_url` ham qaytishi mumkin (restoran uchun bitta so'rov — eng oson).
- Mavjud qo'lda tasdiqlash (`/payment`) qoladi (Naqd, boshqa tizimlar uchun).

### 4.2 Provayder abstraksiyasi
`app/services/payments/` — umumiy interfeys (`create_invoice`, `parse_callback`, `get_status`, `refund`) + `multicard.py`.
Keyin Payme/Click qo'shish kerak bo'lsa, faqat yangi adapter yoziladi ("biz integratsiya qilgan to'lov tizimlari" — ko'plik).

### 4.3 Callback (eng xavfli joy)
- Alohida ochiq endpoint, **imzo majburiy tekshiriladi**; imzosiz/noto'g'ri so'rov `4xx`.
- Summa va `invoice_id` bazadagi buyurtma bilan **solishtiriladi** (callbackdagi summaga ishonmaymiz).
- **Idempotent**: bir xil callback ikki marta kelsa, ikkinchisi hech narsa o'zgartirmaydi.
- Ishonchlilik uchun callbackdan tashqari **fon ishchi (worker)** kutilayotgan to'lovlarni Multicard'dan so'rab tekshiradi
  (callback yo'qolsa ham buyurtma "osilib" qolmaydi).
- `paid` bo'lganda: `osvc.set_payment(paid)` → kuryer qidiruvi → restoranga webhook.

### 4.4 Ma'lumotlar bazasi (yangi migratsiya `0006`)
Jadval `payments`: `id`, `order_id`, `restaurant_id`, `provider`, `provider_invoice_id`, `amount`, `status`, `pay_url`,
`raw_callback (JSON)`, `expires_at`, `paid_at`, `created_at`, `refunded_amount`. Unikal: `(provider, provider_invoice_id)`.
Restoran bo'yicha: Multicard merchant ma'lumotlari (agar har restoran alohida merchant bo'lsa — 7-bo'lim).

### 4.5 Panel (frontend)
- Operator buyurtma tafsilotida "To'lov" tabi: to'lov holati, havola, vaqtlar, qo'lda tasdiqlash/qaytarish.
- Moliya bo'limida: restoranlar bo'yicha qabul qilingan to'lovlar va hisob-kitob (mavjud `ledger` bilan bog'lanadi).

### 4.6 Xavfsizlik
- Multicard kalitlari faqat serverda (`.env`), kodda/gitda emas.
- Callback URL'ni oldindan taxmin qilib bo'lmaydigan qilish + imzo.
- Barcha to'lov o'zgarishlari audit jurnalida (kim/qachon/qaysi manba).
- Rate-limit mavjud (60/daq) — `pay` endpointiga ham qo'llanadi.

## 5. Bosqichlar
1. **Hujjat va kalitlar**: Multicard'dan API hujjati, sandbox, shartnoma (3-bo'lim savollari).
2. **Ichki asos**: `payments` jadvali, provayder interfeysi, Multicard adapteri (sandbox).
3. **Restoran API**: `pay`, `payment` holati; `POST /orders` bilan birlashtirish.
4. **Callback + ishchi**: imzo, idempotentlik, avtomatik `paid`, webhook.
5. **Panel**: operator/moliya ko'rinishi.
6. **Testlar**: callback imzosi, ikki marta callback, summa mos kelmasligi, muddat tugashi, sandbox end-to-end.
7. **Hujjat**: `INTEGRATION.md` ga yangi bo'lim (restoran dasturchisi uchun) + production'ga chiqish.
8. (Keyin) refund, qo'shimcha provayderlar.

## 6. Osonroq muqobillar
- **A (tavsiya):** yuqoridagi — Multicard orqali bitta API, **avtomatik** tasdiqlash. Eng to'g'ri, lekin hujjat/shartnoma kerak.
- **B (eng tez):** Multicard'ni faqat **to'lov sahifasi** sifatida ishlatish, ya'ni mavjud `/orders/{id}/payment` ni
  Multicard callback chaqiradigan qilish. Ya'ni 4.1 dagi `pay` endpointisiz, restoran Multicard havolasini o'zi oladi.
  Kamchilik: restoran Multicard bilan ishlaydi, nazorat bizda kam.
- **C:** Multicard'ning tayyor "POS/hisob-faktura" mahsulotini restoran o'zi ulaydi, biz faqat natijani qabul qilamiz.
  Eng sodda, lekin "bitta API orqali" talabiga mos kelmaydi.

Tavsiya: **A**, lekin 1-bosqichdan (hujjat) oldin boshlamaymiz.

## 7. Biznes-model savoli (kod boshlashdan oldin hal qilinsin)
Pul qaerga tushadi?
1. **Bitta merchant (Tez-yetkaz)** — hamma pul bizga tushadi, restoranlarga biz keyin o'tkazamiz. Eng oson texnik, lekin
   hisob-kitob (`ledger`) va pul tarqatish bizning mas'uliyat; litsenziya/soliq masalasi bor.
2. **Har restoran alohida merchant** — pul to'g'ridan-to'g'ri restoranga, biz faqat yetkazish haqini ushlaymiz. Texnik
   murakkabroq (har restoran uchun kalit/ID saqlash), lekin soliq jihatdan toza.
3. **Split to'lov** (Multicard qo'llasa) — bir to'lov avtomatik bo'linadi.

Bu javob `payments` jadvali va moliya bo'limiga ta'sir qiladi.

## 8. Sizdan kerak
- [ ] Rejani tasdiqlash (A / B / C).
- [ ] Multicard shartnoma, merchant ID, API hujjati va sandbox kalitlari.
- [ ] Pul modeli (7-bo'lim): 1, 2 yoki 3.
- [ ] Qaysi usullar kerak: faqat Multicard yoki Payme/Click ham.
- [ ] Production callback uchun domen (hozir `yolda-api.2-31-28-150.sslip.io`).
