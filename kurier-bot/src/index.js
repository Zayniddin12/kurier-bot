import { bot, syncAll } from './bot.js';
import { config } from './config.js';

// Yolda backend holatini kuzatib, Telegramga xabar yuboradi
let failing = false;
async function loop() {
  try {
    await syncAll();
    if (failing) console.log('Yolda bilan aloqa tiklandi');
    failing = false;
  } catch (e) {
    if (!failing) console.error('Yolda bilan aloqa yo‘q:', e.detail || e.message);
    failing = true;
  }
  setTimeout(loop, failing ? 5000 : config.pollMs);
}

bot.start({ onStart: (me) => console.log(`Bot: @${me.username} → ${config.yoldaUrl}`) });
loop();

for (const sig of ['SIGINT', 'SIGTERM']) process.on(sig, () => bot.stop().finally(() => process.exit(0)));
