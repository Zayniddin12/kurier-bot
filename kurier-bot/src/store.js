import fs from 'node:fs';
import path from 'node:path';
import { config } from './config.js';

// Faqat Telegram xabar ID lari: zakazning o'zi yolda bazasida turadi
const FILE = path.resolve(config.stateFile);
let db = {};

try {
  db = JSON.parse(fs.readFileSync(FILE, 'utf8'));
} catch {}

let timer;
function save() {
  clearTimeout(timer);
  timer = setTimeout(() => {
    fs.mkdirSync(path.dirname(FILE), { recursive: true });
    fs.writeFileSync(`${FILE}.tmp`, JSON.stringify(db));
    fs.renameSync(`${FILE}.tmp`, FILE);
  }, 100);
}

export const rec = {
  get: (tg) => db[tg] || {},
  set(tg, r) {
    db[tg] = r;
    save();
  },
};
