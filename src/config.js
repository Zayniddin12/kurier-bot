import 'dotenv/config';

const need = (k) => {
  const v = process.env[k];
  if (!v) throw new Error(`.env da ${k} yo'q`);
  return v;
};

export const config = {
  botToken: need('BOT_TOKEN'),
  apiKey: need('API_KEY'), // sayt shu kalit bilan zakaz yuboradi
  port: Number(process.env.PORT || 3000),
  // ixtiyoriy: zakazlar tushadigan guruh (kuryerlar a'zo). Bo'sh bo'lsa — ro'yxatdagi har bir kuryerga DM
  courierGroupId: process.env.COURIER_GROUP_ID || '',
  // ixtiyoriy: ruxsat berilgan kuryer Telegram ID lari (vergul bilan). Bo'sh bo'lsa — hamma ro'yxatdan o'tadi
  courierIds: (process.env.COURIER_IDS || '').split(',').map((s) => s.trim()).filter(Boolean),
  // ixtiyoriy: status o'zgarganda saytga POST qilinadi
  webhookUrl: process.env.WEBHOOK_URL || '',
  webhookSecret: process.env.WEBHOOK_SECRET || '',
};
