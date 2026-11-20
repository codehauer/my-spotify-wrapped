// Display formatting, kept in line with src/spotify_wrapped/formatting.py.

const number = new Intl.NumberFormat('en-US')
const compact = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 })

export const formatNumber = (value: number) => number.format(value)
export const formatCompact = (value: number) => compact.format(value)

/** Minutes → "3 min 30 s", "12 h 5 min", "1 d 4 h". */
export function formatDuration(minutes: number): string {
  if (minutes < 1) return `${Math.round(minutes * 60)} s`
  if (minutes < 10) {
    const whole = Math.floor(minutes)
    const seconds = Math.round((minutes - whole) * 60)
    return seconds ? `${whole} min ${seconds} s` : `${whole} min`
  }
  const total = Math.round(minutes)
  const days = Math.floor(total / 1440)
  const hours = Math.floor((total % 1440) / 60)
  const mins = total % 60
  if (days) return hours ? `${days} d ${hours} h` : `${days} d`
  if (hours) return mins ? `${hours} h ${mins} min` : `${hours} h`
  return `${mins} min`
}

/** ISO date (UTC-free calendar date) → Date at UTC midnight, for time scales. */
export const isoDate = (iso: string) => new Date(`${iso.slice(0, 10)}T00:00:00Z`)

const longDate = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })
const weekdayDate = new Intl.DateTimeFormat('en-GB', {
  weekday: 'short', day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC',
})
export const formatDate = (iso: string) => longDate.format(isoDate(iso))
export const formatWeekdayDate = (iso: string) => weekdayDate.format(isoDate(iso))

export const plural = (count: number, word: string) => `${formatNumber(count)} ${word}${count === 1 ? '' : 's'}`

export const WEEKDAYS_SHORT = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
