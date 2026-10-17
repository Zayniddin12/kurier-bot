import { config } from './config.js';

// Status o'zgarganda saytga xabar beradi (xato bo'lsa zakazni to'xtatmaydi)
export async function notifySite(order) {
  if (!config.webhookUrl) return;
  try {
    await fetch(config.webhookUrl, {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'x-webhook-secret': config.webhookSecret },
      body: JSON.stringify({
        orderId: order.id,
        externalId: order.externalId,
        status: order.status,
        courier: order.courier && { id: order.courier.id, name: order.courier.name, phone: order.courier.phone },
        at: new Date().toISOString(),
      }),
      signal: AbortSignal.timeout(5000),
    });
  } catch (e) {
    console.error('webhook xato:', e.message);
  }
}
