export const money = (n: number | null | undefined): string => {
  if (n == null) return '—'
  const s = Math.abs(Math.round(n)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
  return (n < 0 ? '−' : '') + s
}
export const moneyS = (n: number | null | undefined) => money(n) + " so'm"
export const short = (n: number): string => {
  const a = Math.abs(n)
  if (a >= 1_000_000) {
    const v = a / 1_000_000
    return (n < 0 ? '−' : '') + (a >= 10_000_000 ? Math.round(v).toString() : v.toFixed(1).replace('.', ',')) + ' mln'
  }
  return money(n)
}
const p2 = (n: number) => String(n).padStart(2, '0')
const d = (x: string | Date) => (x instanceof Date ? x : new Date(x))
export const hm = (x: string | Date | null | undefined) => (x ? `${p2(d(x).getHours())}:${p2(d(x).getMinutes())}` : '—')
export const dmy = (x: string | Date | null | undefined) => (x ? `${p2(d(x).getDate())}.${p2(d(x).getMonth() + 1)}.${d(x).getFullYear()}` : '—')
export const dm = (x: string | Date | null | undefined) => (x ? `${p2(d(x).getDate())}.${p2(d(x).getMonth() + 1)}` : '—')
export const dmyhm = (x: string | Date | null | undefined) => (x ? `${dmy(x)}, ${hm(x)}` : '—')
export const WEEKDAYS = ['Yak', 'Du', 'Se', 'Chor', 'Pay', 'Ju', 'Sha']
export const weekday = (x: string | Date) => WEEKDAYS[d(x).getDay()]
export const ago = (x: string | Date | null | undefined): string => {
  if (!x) return '—'
  const m = Math.floor((Date.now() - d(x).getTime()) / 60000)
  if (m < 1) return 'hozirgina'
  if (m < 60) return `${m} daq oldin`
  const h = Math.floor(m / 60), r = m % 60
  return r ? `${h} soat ${r} daq oldin` : `${h} soat oldin`
}
export const agoSec = (x: string | Date | null | undefined): string => {
  if (!x) return '—'
  const s = Math.floor((Date.now() - d(x).getTime()) / 1000)
  if (s < 60) return `${Math.max(s, 0)} soniya oldin`
  return ago(x)
}
export const initials = (name: string) => name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join('').toUpperCase()
export const iso = (x: Date) => `${x.getFullYear()}-${p2(x.getMonth() + 1)}-${p2(x.getDate())}`
export const dec = (n: number, f = 1) => n.toFixed(f).replace('.', ',')
export const phoneFmt = (p: string) => p.replace(/^\+998\s?/, '').replace(/^(\d{2})(\d{3})(\d{2})(\d{2})$/, '$1 $2 $3 $4')
