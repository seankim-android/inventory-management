// Date-only strings ("YYYY-MM-DD") parse as UTC midnight, which shows as the
// previous day west of UTC, so build them as local dates instead.
export function parseDate(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  return match ? new Date(+match[1], +match[2] - 1, +match[3]) : new Date(value)
}
