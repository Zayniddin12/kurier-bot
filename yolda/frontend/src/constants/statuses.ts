export type Tone = 'teal' | 'blue' | 'amber' | 'red' | 'grey' | 'violet'
export const ORDER_STATUS: Record<string, { label: string; tone: Tone }> = {
  new: { label: 'Kuryer kutilmoqda', tone: 'red' },
  assigned: { label: "Kuryer restoranga yo'lda", tone: 'blue' },
  onway: { label: "Mijozga yo'lda", tone: 'teal' },
  delivered: { label: 'Yetkazildi', tone: 'grey' },
  cancelled: { label: 'Bekor qilindi', tone: 'red' },
}
export const WORK_STATUS: Record<string, { label: string; tone: Tone; color: string }> = {
  delivering: { label: 'Yetkazmoqda', tone: 'teal', color: 'var(--teal)' },
  pickup: { label: "Restoranga yo'lda", tone: 'blue', color: 'var(--blue)' },
  idle: { label: "Bo'sh", tone: 'amber', color: 'var(--amber)' },
  break: { label: 'Tanaffusda', tone: 'grey', color: 'var(--grey)' },
  offline: { label: 'Smenada emas', tone: 'grey', color: 'var(--faint)' },
}
export const workLine = (w: string, blocked = false) =>
  blocked ? { label: 'Nofaol', tone: 'red' as Tone } : w === 'offline' ? { label: 'Oflayn', tone: 'grey' as Tone } : w === 'break' ? { label: 'Pauzada', tone: 'amber' as Tone } : { label: 'Liniyada', tone: 'teal' as Tone }
export const PAY_STATUS: Record<string, { label: string; tone: Tone }> = {
  paid: { label: "To'langan", tone: 'teal' },
  pending: { label: 'Tasdiqlanmoqda', tone: 'amber' },
  failed: { label: "To'lov o'tmadi", tone: 'red' },
  cod: { label: 'Kuryer oladi', tone: 'blue' },
  collected: { label: 'Kuryer oldi', tone: 'grey' },
  refunded: { label: 'Qaytarildi', tone: 'violet' },
  void: { label: "To'lanmagan", tone: 'grey' },
}
export const LEDGER: Record<string, { label: string; color: string }> = {
  earn: { label: 'Yetkazish haqi', color: 'var(--teal)' },
  cash: { label: 'Naqd pul mijozdan olindi', color: 'var(--red)' },
  topup: { label: 'Naqd pul topshirildi', color: 'var(--blue)' },
  payout: { label: "Maosh to'lab berildi", color: 'var(--amber)' },
  fix: { label: 'Bonus / tuzatish', color: 'var(--violet)' },
  penalty: { label: 'Kechikish jarimasi', color: 'var(--red)' },
}
export const ISSUES: Record<string, { text: string; delay: number }> = {
  noanswer: { text: 'Mijoz telefonni ko\'tarmayapti', delay: 6 },
  address: { text: 'Mijoz manzili topilmadi', delay: 8 },
  restdelay: { text: 'Restoran buyurtmani kechiktirmoqda', delay: 10 },
  vehicle: { text: 'Transport nosozligi', delay: 12 },
  wrong: { text: 'Buyurtma tarkibida xatolik', delay: 5 },
}
export const VEHICLES: Record<string, { label: string; max: string }> = {
  Skuter: { label: 'Skuter', max: '12 km gacha' },
  Avto: { label: 'Avtomobil', max: 'cheklanmagan' },
  Velo: { label: 'Velosiped', max: '5 km gacha' },
  Piyoda: { label: 'Piyoda', max: '2.5 km gacha' },
}
export const REST_STATUS: Record<string, { label: string; tone: Tone }> = {
  open: { label: 'Qabul qilmoqda', tone: 'teal' },
  paused: { label: 'Pauzada', tone: 'amber' },
  offline: { label: 'Oflayn', tone: 'grey' },
}
export const PAY_METHODS = ['Payme', 'Naqd', 'Click', 'Karta']
export const PAY_COLORS: Record<string, string> = { Payme: '#33CCCC', Naqd: 'var(--teal)', Click: 'var(--blue)', Karta: 'var(--violet)' }
export const CUISINES = ['Milliy taomlar', 'Fast-fud', 'Kafe', 'Pitsa', 'Sushi', 'Grill', "Sog'lom ovqat"]
export const DISTRICTS = ['Yunusobod', 'Olmazor', 'Shayxontohur', 'Chilonzor', 'Yakkasaroy', 'Mirobod', "Mirzo Ulug'bek", 'Yashnobod', 'Sergeli', 'Uchtepa']
export const SLA = 45
export const CASH_LIMIT = 400000
