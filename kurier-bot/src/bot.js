import { Bot, InlineKeyboard, Keyboard } from 'grammy';
import { config } from './config.js';
import { rec } from './store.js';
import * as yolda from './yolda.js';

export const bot = new Bot(config.botToken);

const esc = (s = '') => String(s ?? '').replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[c]);
const money = (n) => (n == null ? '—' : `${Number(n).toLocaleString('ru-RU')} so'm`);
const hasGeo = (p) => p && typeof p.lat === 'number' && typeof p.lng === 'number';
const errText = (e) => e?.detail || 'Xatolik yuz berdi, qayta urinib ko‘ring';

const BTN = {
  start: '▶️ Smenani boshlash',
  end: '⏹ Smenani tugatish',
  brk: '☕ Tanaffus / davom etish',
  cur: '📦 Joriy zakaz',
  bal: '💰 Balans',
};
const menu = () =>
  new Keyboard()
    .text(BTN.start).text(BTN.end).row()
    .text(BTN.cur).text(BTN.brk).row()
    .text(BTN.bal).requestLocation('📍 Lokatsiyani yuborish')
    .resized();

// ---------- Xabar matnlari ----------
const STATUS_LABEL = { assigned: '🏪 Restoranga yo‘lda', onway: '🛵 Mijozga yo‘lda' };

function offerText(of) {
  return (
    `🆕 <b>Yangi zakaz #${of.order_id}</b>\n\n` +
    `🏪 <b>${esc(of.restaurant.name)}</b>\n${esc(of.restaurant.address)}\n\n` +
    `🏠 ${esc([of.customer.district, of.customer.address].filter(Boolean).join(', ') || '—')}\n` +
    (of.distance_km != null ? `📏 ${of.distance_km} km\n` : '') +
    `\n💰 Zakaz summasi: ${money(of.total)} (${esc(of.pay_method)})\n` +
    (of.collect_cash ? `💵 <b>Mijozdan naqd oling: ${money(of.total)}</b>\n` : '') +
    `🛵 Sizga: <b>${money(of.earning)}</b>\n\n⏱ 30 soniya ichida qabul qiling`
  );
}

function orderText(o, { reveal = false } = {}) {
  const items = (o.items || []).map((i) => `• ${esc(i.name)} × ${i.qty}`).join('\n');
  let t =
    `<b>Zakaz #${o.id}</b>${o.external_id ? ` (${esc(o.external_id)})` : ''}\n` +
    `Holat: ${STATUS_LABEL[o.status] || o.status}\n\n` +
    `🏪 <b>${esc(o.restaurant.name)}</b>\n${esc(o.restaurant.address)}` +
    (o.restaurant.phone ? `\n📞 ${esc(o.restaurant.phone)}` : '') +
    '\n';
  if (items) t += `\n${items}\n`;
  t += `\n💰 Summa: ${money(o.total)} (${esc(o.pay_method)})`;
  if (o.collect_cash) t += `\n💵 <b>Mijozdan naqd oling: ${money(o.total)}</b>`;
  else if (o.pay_status === 'paid') t += ' — to‘langan';
  t += `\n🛵 Sizga: ${money(o.earning)}`;
  if (o.note) t += `\n💬 ${esc(o.note)}`;
  if (reveal) {
    // mijoz ma'lumotlari faqat ovqat olingandan keyin ochiladi
    t += `\n\n👤 <b>${esc(o.customer.name || 'Mijoz')}</b>\n📞 ${esc(o.customer.phone)}\n🏠 ${esc(o.customer.address || '')}`;
  } else {
    t += `\n\n🏠 Manzil: ${esc([o.customer.district, o.customer.address].filter(Boolean).join(', ') || '—')}`;
  }
  return t;
}

const offerKb = (of) => new InlineKeyboard().text('✅ Qabul qilish', `acc:${of.id}`).text('✖️ Rad etish', `dec:${of.id}`);
const stepKb = (o) =>
  o.status === 'assigned'
    ? new InlineKeyboard().text('🍽 Ovqatni oldim', `pk:${o.id}`)
    : new InlineKeyboard().text('🏁 Yetkazib berdim', `dl:${o.id}`);

// ---------- Xavfsiz yuborish ----------
const html = { parse_mode: 'HTML' };
const send = (chat, text, extra = {}) =>
  bot.api.sendMessage(chat, text, { ...html, ...extra }).catch((e) => {
    console.error('yuborib bo‘lmadi', chat, e.description || e.message);
    return null;
  });
const edit = (chat, id, text, extra = {}) => (id ? bot.api.editMessageText(chat, id, text, { ...html, ...extra }).catch(() => {}) : null);
const clearKb = (chat, id) => (id ? bot.api.editMessageReplyMarkup(chat, id, { reply_markup: undefined }).catch(() => {}) : null);

async function sendPlace(chat, p, label, text) {
  if (hasGeo(p)) await bot.api.sendLocation(chat, p.lat, p.lng).catch(() => {});
  else await send(chat, `📍 ${label}: ${esc(text || '—')}`);
}

async function sendCustomer(chat, o) {
  await send(chat, `📞 Mijoz: <b>${esc(o.customer.name || '')}</b>\n<code>${esc(o.customer.phone)}</code>`);
  await sendPlace(chat, o.customer, 'Manzil', o.customer.address);
}

// ---------- Yolda holatini Telegramga moslash ----------
const locks = new Map();
const locked = (tg, fn) => {
  const next = (locks.get(tg) || Promise.resolve()).then(fn, fn);
  locks.set(tg, next.catch(() => {}));
  return next;
};

async function closeOffer(tg, r, accepted) {
  await edit(tg, r.offerMsg, accepted ? `✅ Zakaz #${r.offerOrderId} qabul qilindi` : `⌛ Zakaz #${r.offerOrderId} taklifi tugadi`);
  r.offerId = r.offerOrderId = r.offerMsg = null;
}

async function closeOrder(tg, r, s) {
  const info = await yolda.orderInfo(r.orderId); // xato bo'lsa keyingi siklda qayta uriniladi
  await clearKb(tg, r.cardMsg);
  if (info.status === 'cancelled') {
    await send(tg, `❌ Zakaz #${info.id} bekor qilindi${info.cancel_reason ? `: ${esc(info.cancel_reason)}` : ''}.`);
  } else if (info.courier_id !== s.courier_id) {
    await send(tg, `🔁 Zakaz #${info.id} sizdan boshqa kuryerga o‘tkazildi.`);
  }
  r.orderId = r.orderStatus = r.cardMsg = null;
}

async function reconcile(s, at) {
  const tg = s.telegram_id;
  const r = { ...rec.get(tg) };
  if (r.syncedAt && r.syncedAt > at) return; // bundan yangiroq holat allaqachon qo'llangan
  r.syncedAt = at;

  const { offer, order } = s;
  if (offer) {
    if (r.offerId !== offer.id) {
      if (r.offerId) await closeOffer(tg, r, false);
      const m = await send(tg, offerText(offer), { reply_markup: offerKb(offer) });
      Object.assign(r, { offerId: offer.id, offerOrderId: offer.order_id, offerMsg: m?.message_id });
    }
  } else if (r.offerId) {
    await closeOffer(tg, r, order?.id === r.offerOrderId);
  }
  rec.set(tg, r);

  if (order) {
    if (r.orderId !== order.id) {
      if (r.orderId) await closeOrder(tg, r, s);
      const m = await send(tg, `✅ Zakaz #${order.id} sizga biriktirildi.\n\n${orderText(order, { reveal: order.status === 'onway' })}`, {
        reply_markup: stepKb(order),
      });
      Object.assign(r, { orderId: order.id, orderStatus: order.status, cardMsg: m?.message_id });
      rec.set(tg, r);
      if (order.status === 'assigned') await sendPlace(tg, order.restaurant, 'Restoran manzili', order.restaurant.address);
      else await sendCustomer(tg, order);
    } else if (r.orderStatus !== order.status) {
      await edit(tg, r.cardMsg, orderText(order, { reveal: order.status === 'onway' }), { reply_markup: stepKb(order) });
      r.orderStatus = order.status;
      rec.set(tg, r);
      if (order.status === 'onway') await sendCustomer(tg, order);
    }
  } else if (r.orderId) {
    await closeOrder(tg, r, s);
    rec.set(tg, r);
  }
}

export const syncOne = (tg) => {
  const at = Date.now();
  return locked(tg, async () => {
    const s = await yolda.stateOf(tg);
    if (s) await reconcile(s, at);
  });
};

export async function syncAll() {
  const at = Date.now();
  const list = await yolda.states();
  await Promise.all(
    list.map((s) =>
      locked(s.telegram_id, () => reconcile(s, at)).catch((e) => console.error('sync xato', s.telegram_id, e.detail || e.message)),
    ),
  );
}

// ---------- Ro'yxatdan o'tish: telefon (Telegram kontakti) ----------
bot.command('start', async (ctx) => {
  if (ctx.chat.type !== 'private') return;
  try {
    if (await yolda.isLinked(ctx.from.id)) return ctx.reply('Siz ro‘yxatdan o‘tgansiz ✅ Zakazlar shu yerga keladi.', { reply_markup: menu() });
  } catch (e) {
    if (e.status !== 404) return ctx.reply(`⚠️ ${errText(e)}`);
  }
  await ctx.reply('Salom! Ro‘yxatdan o‘tish uchun telefon raqamingizni yuboring 👇\n\nRaqam admin panelda kiritilgan raqam bilan bir xil bo‘lishi kerak.', {
    reply_markup: new Keyboard().requestContact('📞 Raqamni yuborish').resized().oneTime(),
  });
});

bot.on('message:contact', async (ctx) => {
  if (ctx.chat.type !== 'private') return;
  if (ctx.message.contact.user_id !== ctx.from.id) return ctx.reply('Iltimos, o‘zingizning raqamingizni yuboring.');
  try {
    const r = await yolda.link(ctx.from.id, ctx.message.contact.phone_number);
    await ctx.reply(`✅ Ro‘yxatdan o‘tdingiz, ${r.courier.name}!\n\nSmenani boshlang va lokatsiya yuboring — zakazlar shu yerga keladi.`, { reply_markup: menu() });
  } catch (e) {
    await ctx.reply(`❌ ${errText(e)}\n\nQayta urinish uchun /start bosing.`, { reply_markup: { remove_keyboard: true } });
  }
});

// ---------- Menyu ----------
bot.hears(BTN.start, async (ctx) => {
  try {
    await yolda.asCourier(ctx.from.id, '/shift/start');
    const s = await yolda.stateOf(ctx.from.id);
    await ctx.reply(
      '▶️ Smena boshlandi.\n\n' +
        (s?.has_location
          ? 'Zakazlar to‘g‘ri kuryerga yetishi uchun lokatsiyangizni yangilab turing: 📎 → Lokatsiya → <b>Jonli lokatsiya</b>.'
          : '📍 Zakaz olish uchun lokatsiyangizni yuboring: 📎 → Lokatsiya → <b>Jonli lokatsiya</b> (yoki pastdagi tugma).'),
      { ...html, reply_markup: menu() },
    );
  } catch (e) {
    await ctx.reply(`⚠️ ${errText(e)}`);
  }
});

bot.hears(BTN.end, async (ctx) => {
  try {
    await yolda.asCourier(ctx.from.id, '/shift/end');
    await ctx.reply('⏹ Smena tugadi. Zakazlar kelmaydi.');
  } catch (e) {
    await ctx.reply(`⚠️ ${errText(e)}`);
  }
});

bot.hears(BTN.brk, async (ctx) => {
  try {
    const s = await yolda.stateOf(ctx.from.id);
    if (s?.work_status === 'break') {
      await yolda.asCourier(ctx.from.id, '/break/end');
      await ctx.reply('▶️ Tanaffus tugadi, zakazlar kelaveradi.');
    } else {
      await yolda.asCourier(ctx.from.id, '/break/start');
      await ctx.reply('☕ 15 daqiqalik tanaffus. Shu vaqtda zakaz kelmaydi.');
    }
  } catch (e) {
    await ctx.reply(`⚠️ ${errText(e)}`);
  }
});

bot.hears(BTN.cur, async (ctx) => {
  try {
    const s = await yolda.stateOf(ctx.from.id);
    if (!s?.order) return ctx.reply('Hozir faol zakaz yo‘q.');
    await ctx.reply(orderText(s.order, { reveal: s.order.status === 'onway' }), { ...html, reply_markup: stepKb(s.order) });
  } catch (e) {
    await ctx.reply(`⚠️ ${errText(e)}`);
  }
});

bot.hears(BTN.bal, async (ctx) => {
  try {
    const s = await yolda.stateOf(ctx.from.id);
    if (!s) return ctx.reply('Avval /start bosing.');
    await ctx.reply(
      `💰 Balans: <b>${money(s.balance)}</b>\n` +
        (s.balance < 0 ? 'Minus — mijozlardan olingan naqd pul sizda, kassaga topshiring.' : 'Plus — sizga to‘lanadigan summa.'),
      html,
    );
  } catch (e) {
    await ctx.reply(`⚠️ ${errText(e)}`);
  }
});

// ---------- Lokatsiya (oddiy va jonli) ----------
const lastLoc = new Map();
async function onLocation(ctx, loc, force) {
  const tg = ctx.from.id;
  if (!force && Date.now() - (lastLoc.get(tg) || 0) < 4000) return; // jonli lokatsiya tez-tez keladi
  lastLoc.set(tg, Date.now());
  try {
    await yolda.asCourier(tg, '/location', 'POST', { lat: loc.latitude, lng: loc.longitude });
    if (force) await ctx.reply('📍 Lokatsiya qabul qilindi.');
  } catch (e) {
    if (force) await ctx.reply(`⚠️ ${errText(e)}`);
  }
}
bot.on('message:location', (ctx) => onLocation(ctx, ctx.message.location, true));
bot.on('edited_message:location', (ctx) => onLocation(ctx, ctx.editedMessage.location, false));

// ---------- Tugmalar ----------
async function act(ctx, fn, ok) {
  const tg = ctx.from.id;
  try {
    const r = await fn();
    await ctx.answerCallbackQuery(ok ? { text: ok } : undefined);
    return r;
  } catch (e) {
    await ctx.answerCallbackQuery({ text: errText(e), show_alert: true }).catch(() => {});
  } finally {
    await syncOne(tg).catch((e) => console.error('sync xato', tg, e.detail || e.message));
  }
}

bot.callbackQuery(/^acc:(\d+)$/, (ctx) => act(ctx, () => yolda.asCourier(ctx.from.id, `/offers/${ctx.match[1]}/accept`), 'Zakaz sizniki ✅'));
bot.callbackQuery(/^dec:(\d+)$/, (ctx) => act(ctx, () => yolda.asCourier(ctx.from.id, `/offers/${ctx.match[1]}/decline`), 'Rad etildi'));
bot.callbackQuery(/^pk:(\d+)$/, (ctx) => act(ctx, () => yolda.asCourier(ctx.from.id, `/orders/${ctx.match[1]}/picked-up`)));
bot.callbackQuery(/^dl:(\d+)$/, async (ctx) => {
  const r = await act(ctx, () => yolda.asCourier(ctx.from.id, `/orders/${ctx.match[1]}/delivered`), 'Yetkazildi 🏁');
  if (r) await ctx.reply(`🎉 Zakaz #${ctx.match[1]} yetkazildi. Rahmat!\n💰 Balans: ${money(r.balance)}`);
});

bot.catch((e) => console.error('bot xato:', e.error?.message || e.message));
