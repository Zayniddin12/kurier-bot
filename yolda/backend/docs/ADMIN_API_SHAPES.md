# Admin API — javob shakllari

Baza: `/api/admin` (Bearer JWT). Xato: `{"detail": "o'zbekcha xabar"}` (401 token yo'q/yaroqsiz, 403 ruxsat yo'q, 404, 409, 422).
Vaqtlar — ISO 8601 (UTC, `...+00:00`); pul — butun so'm; `null` bo'lishi mumkin maydonlar `?` bilan belgilangan.
`restaurant_staff` roli uchun `restaurant_id` parametri e'tiborga olinmaydi — server o'z restoranini majburan qo'llaydi;
boshqa restoran resursi → 404. Kuryerlar, maosh, hisobotlar, restoran qo'shish/tahrirlash/kalit → faqat `platform_admin`/`operator` (aks holda 403).

## Umumiy bo'laklar
```
RestBrief   {id, name, color, district}
CourierBrief{id, number, name, phone, vehicle, plate, avatar_seed, is_female, rating}
OrderRow    {id, external_id, restaurant: RestBrief, created_at, status, status_text, status_color,
             subtotal, delivery_fee, total, distance_km?, pay_method, pay_status, pay_status_text, pay_status_color,
             customer_name, customer_phone, district, address, lat?, lng?, courier: CourierBrief?,
             delivery_minutes?, is_late, queued, customer_rating?}
   status: new|assigned|onway|delivered|cancelled ; status_color: red|blue|teal|grey|red
   pay_status: paid|pending|failed|cod|collected|refunded|void ; *_color: teal|amber|red|blue|grey|violet|grey
Eta         {stage:"pickup"|"delivering", eta_min, remaining_km, elapsed_min, total_min, late, over, progress(0..1),
             bar_percent(0..100), delay_min, arrive_at}
Issue       {id, order_id, courier_id, kind, text, delay_min, started_at, ended_at?, seconds, resolved_by?, auto_at?,
             buttons:[{key,label}], courier_name?, restaurant_name?, customer_phone?, restaurant_phone?}
   button keys: call_customer|call_restaurant|resolve|cancel|reassign
CourierRow  {id, number, first_name, last_name, full_name, phone(9 raqam), pinfl, vehicle, vehicle_name, plate, shift,
             rating, account_status:"active"|"blocked", work_status, work_label, work_color, line_state:"line"|"pause"|"offline",
             overall_status("blocked"|work_status), balance, over_limit, today_orders, today_amount,
             issue:{kind,text}?, current_text, current_order_id?, created_at, avatar_seed, is_female, lat?, lng?,
             idle_since?, online_since?, max_km?(null=cheklanmagan)}
RestaurantRow {id, name, cuisine, district, address, lat, lng, color, integration_type, pos_system, status:"open"|"paused"|"offline",
             pause_reason?, rating, prep_minutes, phone, hours, manager, connected_at, last_sync_at?, api_key_prefix?,
             webhook_url?, today, active, sync_ok}
MapEntry    {id, number, name, phone, vehicle, avatar_seed, is_female, rating, lat?, lng?, work_status, work_label, work_color,
             account_status, line_state, location_updated_at?, current_order_id?,
             order:{id,status,customer_name,customer_phone,address,district,restaurant_id,restaurant_name,pay_method}?,
             route:{stage, restaurant:{lat,lng}?, customer:{lat,lng}?}?, eta: Eta?, issue:{kind,text}?, late}
FeedItem    {id, created_at, html, color, restaurant_id?}     // html faqat <b> teg; color: brand|blue|amber|teal|grey|red|violet
LedgerItem  {id, type, type_label, color, amount, order_id?, note?, created_at}
```

## Auth
- `POST /auth/login` `{email, password}` → `{access_token, token_type:"bearer", user: User}`
- `GET /auth/me` → `User` = `{id, email, full_name, role, role_label, restaurant_id?}`

## Overview — `GET /overview?period=today|yesterday|week|month|range&from=YYYY-MM-DD&to=YYYY-MM-DD&restaurant_id`
```
{ period:{key, from, to, days, compare_label},
  kpis:{ orders:{value,prev,delta_pct?,good?}, active:{value, searching},
         delivered:{value,prev,delta_pct?,good?}, cancelled:{value,prev,delta_pct?,good?, rate, norm:5},
         avg_delivery:{value,prev,delta_pct?,good?, late_count, sla:45}, revenue:{value,prev,delta_pct?,good?} },
  chart:{mode:"hours"|"days", labels:[str], current:[int|null], previous:[int]},
  flow:{searching, pickup, delivering, issues, risk, total},
  couriers:{total, online, on_route, offline},
  restaurants:[{id,name,color,count}]  // top-7, restoran filtri qo'llanmaydi (faqat majburiy staff filtri)
  top_couriers:[{id,number,name,avatar_seed,is_female,delivered,amount,earned,avg_minutes,late,rating}] }
```
`compare_label`: "kechagiga nisbatan" | "oldingi kunga nisbatan" | "oldingi davrga nisbatan". `good` — delta yaxshi (teal) ekanligi.

## Orders
- `GET /orders?period&from&to&restaurant_id&status=all|active|delivered|cancelled&pay=Payme|Naqd|Click|Karta&q&page=1&per_page=20`
  → `{items:[OrderRow], total, page, per_page, summary:{orders,revenue,avg_check,success_pct,avg_delivery,delivered,cancelled}, chart:{mode, labels, delivered:[int], other:[int]}}`
  (`q`: raqam, tashqi raqam, mijoz, manzil, kuryer ismi, telefon). period default `today`.
- `GET /orders/{id}` →
```
{ ...OrderRow, note?, 
  restaurant:{id,name,color,district,cuisine,address,lat,lng,phone},
  courier:{...CourierBrief, lat?, lng?, work_status}?,
  items:[{name,qty,price}],
  eta: Eta?, issue: Issue?, issues:[Issue] (tarix, eskisi birinchi),
  payment:{method,status,status_text,status_color,subtotal,delivery_fee,total,courier_fee,commission,courier_collects,company_due},
  timeline:[{key,label,at?,state:"done"|"current"|"todo"|"cancelled"}],
  search:{pending_payment, offer_courier:{id,name}?, declined_count, wait_minutes}?  // faqat status=new
  times:{created_at,assigned_at?,picked_at?,delivered_at?,cancelled_at?}, cancel_reason?, prep_minutes?, reassigned_count,
  handoff:{lat,lng,name}?, ago_min }
```
- `POST /orders/{id}/cancel` `{reason}` → `{order: OrderDetail, refunded: bool}`
- `POST /orders/{id}/issue/resolve` → `{order: OrderDetail}`; `POST /orders/{id}/issue/reassign` → `{order: OrderDetail}`
- `POST /orders/{id}/notify-customer` → `{ok:true}` (stub)

## Couriers (faqat admin/operator)
- `GET /couriers?q&phone&pinfl&vehicle=Skuter|Avto|Velo|Piyoda&status=all|line|pause|offline|blocked&sort=work|name|phone|pinfl|vehicle|balance|today|status|created&dir=asc|desc`
  → `{items:[CourierRow], stats:{total,line,pause,inactive}, debt_total}`  (`debt_total` manfiy yig'indi yoki 0; `inactive` = bloklangan)
- `GET /couriers/{id}` →
```
{ courier: CourierRow,
  today:{earned, cash, delivered, km, shift_minutes?},
  ledger:[LedgerItem] (oxirgi 8),
  order: OrderDetail?, issue: Issue?, eta: Eta?, queue:[OrderRow],
  offer:{id, order_id}? , limit:400000, max_km? }
```
- `POST /couriers` `{first_name,last_name,phone(9 raqam),pinfl(14),vehicle,shift}` → `CourierRow` (201). Xato: 422 matnlari spetsifikatsiyadagidek.
- `PATCH /couriers/{id}` `{first_name?,last_name?,phone?,vehicle?,plate?,shift?}` → CourierRow
- `POST /couriers/{id}/block|unblock` → CourierRow (blok: 409 "Kuryerda faol buyurtma bor — avval yakunlansin")
- `POST /couriers/{id}/ledger` `{type:"topup"|"fix"|"payout"|"penalty", amount>0, note?}` → `{courier: CourierRow, entry: LedgerItem}`

## Reports (faqat admin/operator)
- `GET /reports/courier-income?days=1|7|30` → `{from,to,days, items:[{courier:CourierBrief, delivered, amount, cash, earned, commission}], totals:{delivered,amount,cash,earned,commission}}`
- `GET /reports/salary` → `{items:[{courier:CourierBrief, settled_at?, deliveries, earned, bonus, fine, late, balance, payable}], total_payable, rules:{commission,bonus_per_10,late_fine,sla,cash_limit}}`
- `POST /couriers/{id}/settle` → `{paid, courier: CourierRow}`; `POST /couriers/settle-all` → `{paid_total, count}`

## Restaurants
- `GET /restaurants?q&status=open|paused|all` → `{items:[RestaurantRow], counts:{all,open,paused}}`
- `GET /restaurants/{id}` → `{restaurant: RestaurantRow, week:{labels,values}, top_items:[{name,qty}], active_orders:[OrderRow],
   integration:{type, pos_system, ok, status_text, last_sync_at?, api_key_prefix?, webhook_url?}}`
- `POST /restaurants` `{name,cuisine,district,address,lat,lng,integration_type,pos_system?,phone?,webhook_url?}` → `{restaurant: RestaurantRow, api_key, webhook_secret?}` (201; kalit FAQAT shu yerda)
- `PATCH /restaurants/{id}` (`name,cuisine,district,address,phone,hours,manager,prep_minutes,webhook_url,...`) → `{restaurant, webhook_secret?}` (secret faqat yangi yaratilganda)
- `POST /restaurants/{id}/pause` `{reason}` / `resume` → `RestaurantRow`
- `POST /restaurants/{id}/rotate-key` → `{api_key, api_key_prefix}`

## Analytics — `GET /analytics?days=7|14|30&restaurant_id`
```
{ range:{from,to,days},
  daily:{labels, delivered:[int], cancelled:[int]},
  revenue_mln:{labels, values:[float 1 kasr]},
  hourly_avg_delivery:{labels:[24], values:[int daq]},
  restaurants:[{id,name,color,count,revenue}],
  couriers:[{id,number,name,avatar_seed,is_female,delivered,avg_minutes,rating,...}],   // top 8
  payments:[{method:"Payme"|"Naqd"|"Click"|"Karta", count, percent}],
  cancel_reasons:[{reason,count}] }
```

## Alerts
- `GET /alerts?restaurant_id` → `{items:[Alert], count}`
```
Alert {key, kind:"issue"|"late"|"nocourier"|"payfail"|"cash"|"restpaused"|"complaint",
       severity:"red"|"amber"|"grey"|"violet", title, text, dismissible, order_id?, courier_id?, restaurant_id?, created_at,
       customer_phone?, restaurant_phone?, issue_kind?, actions:[{key,label}] }
 action keys: call_customer|call_restaurant|resolve|cancel|reassign|view_courier|notify_customer|details|write_customer|topup|resume_restaurant|write_restaurant
```
- `POST /alerts/{key}/dismiss` → `{ok:true}` (faqat dismissible)

## Map / Feed
- `GET /map/state?restaurant_id` → `{couriers:[MapEntry], restaurants:[RestaurantRow]}` (bloklanmagan hamma kuryer; front oflaynlarni yashiradi)
- `GET /feed?limit=60` → `{items:[FeedItem]}` (yangisi birinchi)

## WebSocket — `ws://host/ws?token=JWT`
`{type, data}`; turlar: `order.created`/`order.updated` (data = OrderRow), `courier.updated` (data = MapEntry),
`issue.opened` `{id,order_id,courier_id,kind,text}`, `issue.closed` `{id,order_id,courier_id}`, `feed` (FeedItem),
`restaurant.updated` (RestaurantRow), `alerts.changed` `{}`. Token yaroqsiz bo'lsa close code 4401.
