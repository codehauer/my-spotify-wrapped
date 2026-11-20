import type { Report } from './types'

/**
 * The report is embedded into the page by `spotify-wrapped web`.
 * During development (`npm run dev`) it is fetched from public/stats.json instead,
 * which `npm run demo-data` creates.
 */
export async function loadReport(): Promise<Report> {
  const embedded = document.getElementById('wrapped-data')?.textContent
  if (embedded) {
    const parsed: unknown = JSON.parse(embedded)
    if (parsed && typeof parsed === 'object') return parsed as Report
  }
  const response = await fetch(`${import.meta.env.BASE_URL}stats.json`)
  if (!response.ok) {
    throw new Error('No statistics found. Create the report with `spotify-wrapped web --data <your export>`.')
  }
  return (await response.json()) as Report
}
