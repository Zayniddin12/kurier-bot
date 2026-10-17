import { Bot, InlineKeyboard, Keyboard } from 'grammy';
import { config } from './config.js';
import { orders, couriers } from './store.js';
import { notifySite } from './webhook.js';

export const bot = new Bot(config.botToken);

const MAX_ACTIVE = 1; // kuryer bir vaqtda nechta zakaz olishi mumkin

const esc = (s = '') => String(s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[c]);
const money = (n) => (n == null ? '—' : `${Number(n).toLocaleString('ru-RU')} so'm`);
const hasGeo = (p) => p && typeof p.lat === 'number' && typeof p.lng === 'number';

const STATUS_LABEL = {
  new: '🆕 Yangi',
  accepted: '✅ Qabul qilindi',
  at_restaurant: '🏪 Restoranda',
  picked_up: '🍽 Ovqat olindi',
  arrived: '📍 Yetib keldi',
  delivered: '🏁 Yetkazildi',
  cancelled: '❌ Bekor qilindi',
};

// Har bir bosqichdan keyingi bosqichga o'tish tugmasi
const NEXT = {
  accepted: { to: 'at_restaurant', btn: '🏪 Restoranga bordim' },
  at_restaurant: { to: 'picked_up', btn: '🍽 Ovqatni oldim' },
  picked_up: { to: 'arrived', btn: '📍 Yetib keldim' },
  arrived: { to: 'delivered', btn: '🏁 Yetkazildi' },
};

const isActive = (o) => !['delivered', 'cancelled'].includes(o.status);
const activeOf = (cid) => orders.all().filter((o) => o.courier?.id === cid && isActive(o));

function orderText(o, { full = false } = {}) {
  const items = (o.items || []).map((i) => `• ${esc(i.name)} × ${i.qty ?? 1}`).join('\n');
  let t =
    `<b>Zakaz #${o.id}</b>${o.externalId ? ` (${esc(o.externalId)})` : ''}\n` +
    `Holat: ${STATUS_LABEL[o.status]}\n\n` +
    `🏪 <b>${esc(o.restaurant.name)}</b>\n${esc(o.restaurant.address || '')}\n`;
  if (items) t += `\n${items}\n`;
  t += `\n💰 Summa: ${money(o.total)}${o.payment ? ` (${esc(o.payment)})` : ''}`;
  if (o.deliveryFee != null) t += `\n🛵 Yetkazish: ${money(o.deliveryFee)}`;
  if (o.comment) t += `\n💬 ${esc(o.comment)}`;
  if (full) {
    // mijoz ma'lumotlari faqat ovqat olingandan keyin ochiladi
    t += `\n\n👤 <b>${esc(o.customer.name || 'Mijoz')}</b>\n📞 ${esc(o.customer.phone)}\n🏠 ${esc(o.customer.address || '')}`;
  } else {
    t += `\n\n🏠 Manzil: ${esc(o.customer.address || '—')}`;
  }
  return t;
}

const stepKeyboard = (o) => {
  const n = NEXT[o.status];
  return n ? new InlineKeyboard().text(n.btn, `st:${o.id}:${n.to}`) : undefined;
};

// ---- Yangi zakazni kuryerlarga yuborish (sayt API chaqiradi) ----
export async function dispatchOrder(o) {
  const kb = new InlineKeyboard().text('✅ Qabul qilish', `acc:${o.id}`);
  const text = orderText(o);
  o.broadcast = [];
  const targets = config.courierGroupId
    ? [config.courierGroupId]
    : couriers.all().filter((c) => c.active !== false).map((c) => c.id);
  for (const chatId of targets) {
    try {
      const m = await bot.api.sendMessage(chatId, text, { parse_mode: 'HTML', reply_markup: kb });
      o.broadcast.push({ chatId, messageId: m.message_id });
    } catch (e) {
      console.error('yuborib bo‘lmadi', chatId, e.description || e.message);
    }
  }
  orders.put(o);
}

async function closeBroadcast(o, byName) {
  for (const b of o.broadcast || []) {
    if (b.chatId === o.courier?.id) continue;
    const text = `${orderText(o)}\n\n🔒 ${esc(byName)} qabul qildi`;
    await bot.api.editMessageText(b.chatId, b.messageId, text, { parse_mode: 'HTML' }).catch(() => {});
  }
}

// ---- Ro'yxatdan o'tish ----
const allowed = (id) => config.courierIds.length === 0 || config.courierIds.includes(String(id));

bot.command('start', async (ctx) => {
  if (ctx.chat.type !== 'private') return;
  if (!allowed(ctx.from.id)) return ctx.reply('⛔ Sizga ruxsat berilmagan. Admin bilan bog‘laning.');
  const c = couriers.get(ctx.from.id);
  if (c?.phone) return ctx.reply('Siz ro‘yxatdan o‘tgansiz ✅ Zakazlar shu yerga keladi.', { reply_markup: menu() });
  await ctx.reply('Salom! Ro‘yxatdan o‘tish uchun telefon raqamingizni yuboring 👇', {
    reply_markup: new Keyboard().requestContact('📞 Raqamni yuborish').resized().oneTime(),
  });
});

const menu = () => new Keyboard().text('📦 Joriy zakaz').text('⏸ Ishni to‘xtatish / ▶️ Boshlash').resized();

bot.on('message:contact', async (ctx) => {
  if (!allowed(ctx.from.id)) return;
  if (ctx.message.contact.user_id !== ctx.from.id) return ctx.reply('Iltimos, o‘zingizning raqamingizni yuboring.');
  couriers.put({
    id: ctx.from.id,
    name: [ctx.from.first_name, ctx.from.last_name].filter(Boolean).join(' '),
    phone: ctx.message.contact.phone_number,
    active: true,
  });
  await ctx.reply('✅ Ro‘yxatdan o‘tdingiz! Yangi zakazlar shu yerga keladi.', { reply_markup: menu() });
});

bot.hears('⏸ Ishni to‘xtatish / ▶️ Boshlash', async (ctx) => {
  const c = couriers.get(ctx.from.id);
  if (!c) return ctx.reply('Avval /start bosing.');
  c.active = c.active === false;
  couriers.put(c);
  await ctx.reply(c.active ? '▶️ Ish boshlandi, zakazlar keladi.' : '⏸ To‘xtatildi, zakaz kelmaydi.');
});

bot.hears('📦 Joriy zakaz', async (ctx) => {
  const list = activeOf(ctx.from.id);
  if (!list.length) return ctx.reply('Hozir faol zakaz yo‘q.');
  for (const o of list) {
    await ctx.reply(orderText(o, { full: ['picked_up', 'arrived'].includes(o.status) }), {
      parse_mode: 'HTML',
      reply_markup: stepKeyboard(o),
    });
  }
});

// ---- 1) Qabul qilish → restoran lokatsiyasi ----
bot.callbackQuery(/^acc:(\d+)$/, async (ctx) => {
  const o = orders.get(ctx.match[1]);
  const c = couriers.get(ctx.from.id);
  if (!o) return ctx.answerCallbackQuery({ text: 'Zakaz topilmadi', show_alert: true });
  if (!c?.phone) return ctx.answerCallbackQuery({ text: 'Avval botga /start yozib ro‘yxatdan o‘ting', show_alert: true });
  if (o.status !== 'new') return ctx.answerCallbackQuery({ text: 'Bu zakazni boshqa kuryer oldi yoki bekor qilingan', show_alert: true });
  if (activeOf(c.id).length >= MAX_ACTIVE)
    return ctx.answerCallbackQuery({ text: 'Avval joriy zakazni yakunlang', show_alert: true });

  // Node bitta thread — yuqoridagi tekshiruv va quyidagi o'zgartirish orasida await yo'q, shuning uchun poyga bo'lmaydi
  o.status = 'accepted';
  o.courier = { id: c.id, name: c.name, phone: c.phone };
  orders.put(o);
  await ctx.answerCallbackQuery({ text: 'Zakaz sizniki ✅' });

  await closeBroadcast(o, c.name);
  await ctx.editMessageText(`${orderText(o)}\n\n🔒 ${esc(c.name)} qabul qildi`, { parse_mode: 'HTML' }).catch(() => {});

  // Kuryerga shaxsiy chatda davom ettiramiz
  await bot.api.sendMessage(c.id, `✅ Zakaz #${o.id} sizga biriktirildi.\n\n${orderText(o)}`, {
    parse_mode: 'HTML',
    reply_markup: stepKeyboard(o),
  });
  if (hasGeo(o.restaurant)) {
    await bot.api.sendLocation(c.id, o.restaurant.lat, o.restaurant.lng);
  } else {
    await bot.api.sendMessage(c.id, `📍 Restoran manzili: ${esc(o.restaurant.address || '—')}`, { parse_mode: 'HTML' });
  }
  notifySite(o);
});

// ---- 2..4) Keyingi bosqichlar ----
bot.callbackQuery(/^st:(\d+):(\w+)$/, async (ctx) => {
  const [, id, to] = ctx.match;
  const o = orders.get(id);
  if (!o || o.courier?.id !== ctx.from.id) return ctx.answerCallbackQuery({ text: 'Bu sizning zakazingiz emas', show_alert: true });
  if (NEXT[o.status]?.to !== to) return ctx.answerCallbackQuery({ text: 'Bu bosqich allaqachon bajarilgan' });

  o.status = to;
  orders.put(o);
  await ctx.answerCallbackQuery();

  // Ovqat olindi → mijoz raqami va lokatsiyasi
  const full = ['picked_up', 'arrived'].includes(to);
  await ctx.editMessageText(orderText(o, { full }), { parse_mode: 'HTML', reply_markup: stepKeyboard(o) }).catch(() => {});

  if (to === 'picked_up') {
    await ctx.reply(`📞 Mijoz: <b>${esc(o.customer.name || '')}</b>\n<code>${esc(o.customer.phone)}</code>`, { parse_mode: 'HTML' });
    if (hasGeo(o.customer)) await ctx.api.sendLocation(ctx.from.id, o.customer.lat, o.customer.lng);
    else await ctx.reply(`📍 Manzil: ${esc(o.customer.address || '—')}`);
  }
  if (to === 'delivered') await ctx.reply(`🎉 Zakaz #${o.id} yetkazildi. Rahmat!`);
  notifySite(o);
});

// Saytdan bekor qilish
export async function cancelOrder(o) {
  o.status = 'cancelled';
  orders.put(o);
  for (const b of o.broadcast || []) {
    await bot.api.editMessageText(b.chatId, b.messageId, orderText(o), { parse_mode: 'HTML' }).catch(() => {});
  }
  if (o.courier) await bot.api.sendMessage(o.courier.id, `❌ Zakaz #${o.id} bekor qilindi.`).catch(() => {});
  notifySite(o);
}

bot.catch((e) => console.error('bot xato:', e.error?.message || e.message));
