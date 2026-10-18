import 'dotenv/config';

const need = (k) => {
  const v = process.env[k];
  if (!v) throw new Error(`.env da ${k} yo'q`);
  return v;
};

export const config = {
  botToken: need('BOT_TOKEN'),
  yoldaUrl: (process.env.YOLDA_URL || 'http://localhost:8000').replace(/\/$/, ''),
  botApiKey: need('BOT_API_KEY'), // yolda backend dagi BOT_API_KEY bilan bir xil
  pollMs: Number(process.env.POLL_MS || 2000),
  // bot yuborgan xabarlarning ID lari shu faylda saqlanadi (zakazning o'zi yolda bazasida)
  stateFile: process.env.STATE_FILE || 'data/state.json',
};
