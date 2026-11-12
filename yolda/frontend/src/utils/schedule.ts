export const DAYS = ['Yakshanba', 'Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma', 'Shanba']
const hm = (m: number) => `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`

/** "09:00–22:00" → 7 ta 48 belgili "0/1" satr (jadval hali saqlanmagan restoranlar uchun) */
export function parseHours(h: string): string[] {
  const m = (h || '').match(/(\d{1,2}):(\d{2})\s*[–-]\s*(\d{1,2}):(\d{2})/)
  let day = '1'.repeat(48)
  if (m) {
    const a = (+m[1] * 60 + +m[2]) / 30, b = Math.ceil((+m[3] * 60 + +m[4] + (+m[4] % 30 === 29 ? 1 : 0)) / 30)
    day = Array.from({ length: 48 }, (_, i) => (a <= b ? i >= a && i < b : i >= a || i < b) ? '1' : '0').join('')
  }
  return Array(7).fill(day)
}

export function ranges(d: string): string[] {
  const out: string[] = []
  for (let i = 0; i < 48; i++) {
    if (d[i] !== '1') continue
    let j = i
    while (j + 1 < 48 && d[j + 1] === '1') j++
    out.push(`${hm(i * 30)} — ${hm((j + 1) * 30 - 1)}`)
    i = j
  }
  return out
}

/** Bir xil jadvalli ketma-ket kunlarni guruhlaydi: [{days:'Dushanba — Juma', text:'09:00 — 22:59'}] */
export function groups(sch: string[]) {
  const out: { days: string; text: string }[] = []
  let s = 0
  for (let i = 1; i <= 7; i++) {
    if (i === 7 || sch[i] !== sch[s]) {
      out.push({ days: i - 1 === s ? DAYS[s] : `${DAYS[s]} — ${DAYS[i - 1]}`, text: ranges(sch[s]).join(', ') || 'Dam olish' })
      s = i
    }
  }
  return out
}

/** Hozir ochiq bo'lsa tugash vaqti ("23:59"), aks holda null */
export function openUntil(sch: string[], now = new Date()): string | null {
  const day = sch[now.getDay()], slot = Math.floor((now.getHours() * 60 + now.getMinutes()) / 30)
  if (day[slot] !== '1') return null
  let j = slot
  while (j + 1 < 48 && day[j + 1] === '1') j++
  return hm((j + 1) * 30 - 1)
}
