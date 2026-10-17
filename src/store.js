import fs from 'node:fs';
import path from 'node:path';

const FILE = path.resolve('data/db.json');
let db = { orders: {}, couriers: {}, seq: 0 };

try {
  db = JSON.parse(fs.readFileSync(FILE, 'utf8'));
} catch {}

let timer;
function save() {
  clearTimeout(timer);
  timer = setTimeout(() => {
    fs.mkdirSync(path.dirname(FILE), { recursive: true });
    fs.writeFileSync(FILE, JSON.stringify(db));
  }, 100);
}

export const orders = {
  get: (id) => db.orders[id],
  all: () => Object.values(db.orders),
  nextId: () => ++db.seq,
  put(o) {
    db.orders[o.id] = o;
    save();
    return o;
  },
};

export const couriers = {
  get: (id) => db.couriers[id],
  all: () => Object.values(db.couriers),
  put(c) {
    db.couriers[c.id] = c;
    save();
    return c;
  },
};
