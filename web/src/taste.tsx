import { useMemo } from 'react'
import { barY, cell, defineChart } from '@tanstack/charts'
import { angleGrid, pie, polar, radialArc, radialArea, radialDot, radialGrid, radialLine } from '@tanstack/charts/polar'
import { Chart } from '@tanstack/charts/react'
import { scaleBand } from '@tanstack/charts/scales/band'
import { scaleLinear } from '@tanstack/charts/scales/linear'
import { scaleOrdinal } from '@tanstack/charts/scales/ordinal'
import { scalePoint } from '@tanstack/charts/scales/point'
import { tooltip } from '@tanstack/charts/tooltip'
import { curveLinearClosed } from 'd3-shape'
import { WEEKDAYS_SHORT, formatDuration } from './format'
import type { GenreHour, GenreShare, MoodCell, Trinity, TrinityAxis } from './types'

// Categorical slots in a fixed, CVD-validated order (see styles.css). Color follows
// the genre's slot in the pie; "Other" is always the neutral gray.
const SLOTS = 7
export const OTHER = 'Other'

export function genreColors(genres: GenreShare[]): Map<string, string> {
  const colors = new Map<string, string>()
  let slot = 0
  for (const g of genres) {
    colors.set(g.genre, g.genre === OTHER ? 'var(--wrapped-other)' : `var(--wrapped-cat-${(slot++ % SLOTS) + 1})`)
  }
  return colors
}

const pct = (value: number) => `${value.toFixed(1)}%`
const hourLabel = (h: number) => String(h).padStart(2, '0')

/** Donut of the genre shares; the legend is rendered next to it in HTML. */
export function GenreDonut({ genres }: { genres: GenreShare[] }) {
  const definition = useMemo(() => {
    const colors = genreColors(genres)
    const slices = pie(genres, { value: 'minutes', gapAngle: 0.012 })
    return defineChart({
      marks: [
        polar({
          inset: 6,
          radiusRatio: 0.96,
          marks: [
            radialArc(slices, {
              innerRadius: ({ radius }) => radius * 0.58,
              cornerRadius: 3,
              color: 'genre',
              key: 'genre',
            }),
          ],
          scales: { angle: null, radius: null },
        }),
      ],
      scales: { x: null, y: null },
      color: { scale: () => scaleOrdinal<string, string>().domain([...colors.keys()]).range([...colors.values()]) },
      tooltip: {
        use: tooltip,
        content: (points) => {
          const d = points[0]?.datum
          return d
            ? {
                title: d.genre,
                color: colors.get(d.genre),
                rows: [
                  { label: 'Share of listening time', value: pct(d.share) },
                  { label: 'Listening time', value: formatDuration(d.minutes) },
                  { label: 'Streams', value: d.streams.toLocaleString('en-GB') },
                ],
              }
            : { rows: [] }
        },
      },
    })
  }, [genres])
  return <Chart definition={definition} height={260} ariaLabel="Share of listening time per genre" className="chart" />
}

export const TRINITY_AXES: { key: TrinityAxis; label: string; icon: string }[] = [
  { key: 'atzig', label: 'Atzig', icon: '🍻' },
  { key: 'fotzig', label: 'Fotzig', icon: '💅' },
  { key: 'mausig', label: 'Mausig', icon: '🐭' },
]

/** Radar chart of the atzig/fotzig/mausig trinity (each 0–100). */
export function TrinityRadar({ trinity }: { trinity: Trinity }) {
  const definition = useMemo(() => {
    const labels = TRINITY_AXES.map((a) => `${a.icon} ${a.label}`)
    const profile = TRINITY_AXES.map((a, i) => ({ axis: labels[i], key: a.key, value: trinity[a.key] }))
    return defineChart({
      marks: [
        polar({
          radiusRatio: 0.72,
          scales: {
            angle: { scale: scalePoint<string>().domain(labels), wrap: true },
            radius: { scale: scaleLinear().domain([0, 100]) },
          },
          guides: [
            radialGrid({ values: [25, 50, 75, 100], shape: 'polygon', stroke: 'var(--wrapped-grid)' }),
            angleGrid({ labels: true, stroke: 'var(--wrapped-grid)', labelFill: 'var(--color-text-primary)', labelFontSize: 13 }),
          ],
          marks: [
            radialArea(profile, { angle: 'axis', radius: 'value', curve: curveLinearClosed, fill: 'var(--wrapped-accent)', fillOpacity: 0.22 }),
            radialLine(profile, { angle: 'axis', radius: 'value', curve: curveLinearClosed, stroke: 'var(--wrapped-accent)', strokeWidth: 2 }),
            radialDot(profile, { angle: 'axis', radius: 'value', r: 5, fill: 'var(--wrapped-accent)', stroke: 'var(--color-background-card)', strokeWidth: 2, key: 'key' }),
          ],
        }),
      ],
      scales: { x: null, y: null },
      tooltip: {
        use: tooltip,
        content: (points) => {
          const d = points[0]?.datum
          return d ? { title: d.axis, rows: [{ label: 'Score', value: `${Math.round(d.value)} / 100` }] } : { rows: [] }
        },
      },
    })
  }, [trinity])
  return <Chart definition={definition} height={300} ariaLabel="Atzig, fotzig and mausig scores" className="chart" />
}

/** Diverging mood levels around the listener's own average: sad (blue) – neutral – happy (orange). */
const MOOD_LEVELS = ['Much sadder', 'Sadder', 'A bit sadder', 'Average', 'A bit happier', 'Happier', 'Much happier'] as const
const MOOD_COLORS = [
  'var(--wrapped-sad)',
  'color-mix(in oklab, var(--wrapped-sad) 62%, var(--wrapped-neutral))',
  'color-mix(in oklab, var(--wrapped-sad) 28%, var(--wrapped-neutral))',
  'var(--wrapped-neutral)',
  'color-mix(in oklab, var(--wrapped-happy) 28%, var(--wrapped-neutral))',
  'color-mix(in oklab, var(--wrapped-happy) 62%, var(--wrapped-neutral))',
  'var(--wrapped-happy)',
]
const NO_DATA = 'Too few streams'
export const moodLegend = MOOD_LEVELS.map((label, i) => ({ label, color: MOOD_COLORS[i] }))

function moodLevel(happiness: number | null, average: number, spread: number): string {
  if (happiness === null) return NO_DATA
  const delta = Math.max(-1, Math.min(1, (happiness - average) / spread))
  return MOOD_LEVELS[Math.round(delta * 3) + 3]
}

/** Weekday × hour heatmap of the happiness of what was played. */
export function MoodHeatmap({ cells, average }: { cells: MoodCell[]; average: number }) {
  const definition = useMemo(() => {
    const values = cells.flatMap((c) => (c.happiness === null ? [] : [Math.abs(c.happiness - average)]))
    const spread = Math.max(1, ...values)
    const data = cells.map((c) => ({
      ...c,
      day: WEEKDAYS_SHORT[c.weekday],
      hourLabel: hourLabel(c.hour),
      level: moodLevel(c.happiness, average, spread),
    }))
    return defineChart({
      marks: [cell(data, { x: 'hourLabel', y: 'day', color: 'level', key: (d) => `${d.weekday}-${d.hour}`, inset: 1, radius: 3 })],
      scales: {
        x: {
          scale: () => scaleBand<string>().domain(data.slice(0, 24).map((d) => d.hourLabel)).padding(0),
          axis: { ticks: { format: (h: string) => (Number(h) % 3 === 0 ? h : '') } },
        },
        y: { scale: () => scaleBand<string>().domain(WEEKDAYS_SHORT).padding(0) },
      },
      color: {
        scale: () => scaleOrdinal<string, string>().domain([...MOOD_LEVELS, NO_DATA]).range([...MOOD_COLORS, 'var(--wrapped-heat-empty)']),
      },
      tooltip: {
        use: tooltip,
        content: (points) => {
          const d = points[0]?.datum
          if (!d) return { rows: [] }
          return {
            title: `${d.day} ${d.hourLabel}:00–${d.hourLabel}:59`,
            rows: d.happiness === null
              ? [{ label: 'Streams', value: String(d.streams) }, { label: 'Mood', value: NO_DATA }]
              : [
                  { label: 'Happiness', value: `${Math.round(d.happiness)} / 100` },
                  { label: 'Compared to you', value: d.level },
                  { label: 'Streams', value: String(d.streams) },
                ],
          }
        },
      },
    })
  }, [cells, average])
  return <Chart definition={definition} height={250} ariaLabel="Mood of your music by weekday and hour" className="chart" />
}

/** 100 % stacked columns: which genres play at which hour of the day. */
export function GenreHoursChart({ genres, cells }: { genres: GenreShare[]; cells: GenreHour[] }) {
  const definition = useMemo(() => {
    const colors = genreColors(genres)
    const order = genres.map((g) => g.genre)
    const data = cells.map((c) => ({ ...c, hourLabel: hourLabel(c.hour), rank: order.indexOf(c.genre) }))
    data.sort((a, b) => a.hour - b.hour || a.rank - b.rank)
    return defineChart({
      marks: [
        barY(data, {
          x: 'hourLabel',
          y: 'share',
          z: 'genre',
          color: 'genre',
          key: (d) => `${d.hour}-${d.genre}`,
          inset: 1,
          maxThickness: 28,
        }),
      ],
      scales: {
        x: {
          scale: () => scaleBand<string>().domain(data.filter((d) => d.rank === 0).map((d) => d.hourLabel)).padding(0.15),
          axis: { ticks: { format: (h: string) => (Number(h) % 3 === 0 ? h : '') } },
        },
        y: {
          scale: () => scaleLinear().domain([0, 100]),
          grid: true,
          axis: { ticks: { format: (v: number) => `${v}%` } },
        },
      },
      color: { scale: () => scaleOrdinal<string, string>().domain(order).range(order.map((g) => colors.get(g) ?? 'var(--wrapped-other)')) },
      focus: 'nearest-x',
      tooltip: {
        use: tooltip,
        content: (points) => {
          const hour = points[0]?.datum?.hour
          if (hour === undefined) return { rows: [] }
          const rows = data.filter((d) => d.hour === hour && d.share > 0).sort((a, b) => b.share - a.share)
          return {
            title: `${hourLabel(hour)}:00–${hourLabel(hour)}:59`,
            rows: rows.map((d) => ({ label: d.genre, value: pct(d.share), color: colors.get(d.genre) })),
          }
        },
      },
    })
  }, [genres, cells])
  return <Chart definition={definition} height={320} ariaLabel="Genre mix per hour of day" className="chart" />
}
