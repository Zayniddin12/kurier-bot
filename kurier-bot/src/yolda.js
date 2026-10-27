import { config } from './config.js';

export class YoldaError extends Error {
  constructor(status, detail) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

async function call(path, { method = 'GET', body, headers = {} } = {}) {
  let res;
  try {
    res = await fetch(config.yoldaUrl + path, {
      method,
      headers: { 'content-type': 'application/json', ...headers },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(8000),
    });
  } catch (e) {
    throw new YoldaError(0, 'Server bilan aloqa yo‘q, birozdan keyin urinib ko‘ring');
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new YoldaError(res.status, data?.detail || `Xato ${res.status}`);
  return data;
}

const bot = (path, opts = {}) => call(`/api/bot${path}`, { ...opts, headers: { 'x-bot-key': config.botApiKey } });

// ---- bot servisi endpointlari ----
export const link = (telegram_id, phone) => bot('/link', { method: 'POST', body: { telegram_id, phone } });
export const states = () => bot('/state').then((r) => r.couriers);
export const stateOf = (telegram_id) => bot(`/state?telegram_id=${telegram_id}`).then((r) => r.couriers[0] || null);
export const orderInfo = (id) => bot(`/orders/${id}`);

// ---- kuryer nomidan (qisqa muddatli token) ----
const tokens = new Map(); // telegram_id -> { value, exp }

async function tokenFor(tg) {
  const t = tokens.get(tg);
  if (t && t.exp > Date.now() + 30_000) return t.value;
  const r = await bot('/token', { method: 'POST', body: { telegram_id: tg } });
  tokens.set(tg, { value: r.access_token, exp: Date.now() + 9 * 60_000 });
  return r.access_token;
}

export async function asCourier(tg, path, method = 'POST', body) {
  const go = async () => call(`/api/courier${path}`, { method, body, headers: { authorization: `Bearer ${await tokenFor(tg)}` } });
  try {
    return await go();
  } catch (e) {
    if (e.status !== 401) throw e;
    tokens.delete(tg); // token muddati tugagan bo'lishi mumkin — bir marta yangilab qaytaramiz
    return go();
  }
}

export const isLinked = async (tg) => {
  try {
    await tokenFor(tg);
    return true;
  } catch (e) {
    if (e.status === 404) return false;
    throw e;
  }
};
