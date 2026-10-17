import crypto from 'node:crypto';
import express from 'express';
import { config } from './config.js';
import { orders } from './store.js';
import { bot, dispatchOrder, cancelOrder } from './bot.js';

const app = express();
app.use(express.json({ limit: '100kb' }));

const safeEq = (a = '', b = '') => {
  const x = Buffer.from(String(a));
  const y = Buffer.from(String(b));
  return x.length === y.length && crypto.timingSafeEqual(x, y);
};

app.use('/api', (req, res, next) => {
  if (!safeEq(req.get('x-api-key'), config.apiKey)) return res.status(401).json({ error: 'unauthorized' });
  next();
});

const num = (v) => (v === undefined || v === null || v === '' ? undefined : Number(v));
const geo = (p = {}) => ({ ...p, lat: num(p.lat), lng: num(p.lng) });

// Sayt yangi zakaz yuboradi
app.post('/api/orders', async (req, res) => {
  const b = req.body || {};
  if (!b.restaurant?.name || !b.customer?.phone)
    return res.status(400).json({ error: 'restaurant.name va customer.phone majburiy' });

  // Sayt qayta yuborsa dublikat bo'lmasligi uchun
  if (b.externalId) {
    const dup = orders.all().find((o) => o.externalId === String(b.externalId));
    if (dup) return res.json({ id: dup.id, status: dup.status, duplicate: true });
  }

  const order = {
    id: String(orders.nextId()),
    externalId: b.externalId ? String(b.externalId) : undefined,
    status: 'new',
    restaurant: geo(b.restaurant),
    customer: geo(b.customer),
    items: Array.isArray(b.items) ? b.items : [],
    total: num(b.total),
    deliveryFee: num(b.deliveryFee),
    payment: b.payment,
    comment: b.comment,
    createdAt: Date.now(),
  };
  orders.put(order);
  await dispatchOrder(order);
  res.status(201).json({ id: order.id, status: order.status });
});

app.get('/api/orders/:id', (req, res) => {
  const o = orders.get(req.params.id);
  if (!o) return res.status(404).json({ error: 'not found' });
  res.json({ id: o.id, externalId: o.externalId, status: o.status, courier: o.courier });
});

app.post('/api/orders/:id/cancel', async (req, res) => {
  const o = orders.get(req.params.id);
  if (!o) return res.status(404).json({ error: 'not found' });
  if (['delivered', 'cancelled'].includes(o.status)) return res.status(409).json({ error: `already ${o.status}` });
  await cancelOrder(o);
  res.json({ id: o.id, status: o.status });
});

app.listen(config.port, () => console.log(`API: http://localhost:${config.port}`));
bot.start({ onStart: (me) => console.log(`Bot: @${me.username}`) });
