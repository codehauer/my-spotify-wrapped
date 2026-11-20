import { useMemo } from 'react'
import { areaY, barX, barY, cell, defineChart, lineY } from '@tanstack/charts'
import { crosshair } from '@tanstack/charts/crosshair'
import { Chart } from '@tanstack/charts/react'
import { scaleBand } from '@tanstack/charts/scales/band'
import { scaleLinear } from '@tanstack/charts/scales/linear'
import { scaleOrdinal } from '@tanstack/charts/scales/ordinal'
import { scaleUtc } from '@tanstack/charts/scales/time'
import { tooltip } from '@tanstack/charts/tooltip'
import type { Bucket, HeatCell } from './types'
import { WEEKDAYS_SHORT, formatCompact, formatDuration, formatNumber, isoDate } from './format'

// Colors come from CSS custom properties (see styles.css), so charts follow
// light/dark mode without rebuilding their definitions.
const ACCENT = 'var(--wrapped-accent)'
const ACCENT_SOFT = 'var(--wrapped-accent-soft)'
const ACCENT_WASH = 'var(--wrapped-accent-wash)'

const monthTick = new Intl.DateTimeFormat('en-GB', { month: 'short', year: '2-digit', timeZone: 'UTC' })

const streamsAxis = {
  scale: scaleLinear,
  nice: true,
  grid: true,
  axis: { ticks: { format: (value: number) => formatCompact(value) } },
} as const

function rows(label: string, streams: number, minutes: number) {
  return {
    title: label,
    color: ACCENT,
    rows: [
      { label: 'Streams', value: formatNumber(streams) },
      { label: 'Listening time', value: formatDuration(minutes) },
    ],
  }
}

/** Streams per week as an area with a crosshair. */
export function WeeklyChart({ weeks }: { weeks: Bucket[] }) {
  const definition = useMemo(() => {
    const data = weeks.map((w) => ({ ...w, week: isoDate(String(w.key)) }))
    return defineChart({
      marks: [
        areaY(data, { x: 'week', y: 'streams', fill: ACCENT_WASH }),
        lineY(data, { x: 'week', y: 'streams', stroke: ACCENT, strokeWidth: 2 }),
        crosshair({ x: true, y: false }),
      ],
      scales: {
        x: { scale: scaleUtc, axis: { ticks: { format: (d: Date) => monthTick.format(d) } } },
        y: streamsAxis,
      },
      focus: 'nearest-x',
      maxFocusDistance: Number.POSITIVE_INFINITY,
      tooltip: {
        use: tooltip,
        content: (points) => {
          const d = points[0]?.datum
          return d ? rows(d.label, d.streams, d.minutes) : { rows: [] }
        },
      },
    })
  }, [weeks])
  return <Chart definition={definition} height={260} ariaLabel="Streams per week" className="chart" />
}

/** Vertical columns for ordered buckets (months, hours); the peak bucket is emphasized. */
export function ColumnChart({ buckets, ariaLabel, tick, height = 240 }: {
  buckets: Bucket[]
  ariaLabel: string
  tick?: (label: string, index: number) => string
  height?: number
}) {
  const definition = useMemo(() => {
    const peak = Math.max(...buckets.map((b) => b.streams))
    const labels = buckets.map((b) => b.label)
    return defineChart({
      marks: [
        barY(buckets, {
          x: 'label',
          y: 'streams',
          fill: (b) => (b.streams === peak ? ACCENT : ACCENT_SOFT),
          radius: [4, 4, 0, 0],
          maxThickness: 24,
        }),
      ],
      scales: {
        x: {
          scale: () => scaleBand<string>().domain(labels).padding(0.2),
          axis: { ticks: { format: (label: string) => (tick ? tick(label, labels.indexOf(label)) : label) } },
        },
        y: streamsAxis,
      },
      tooltip: {
        use: tooltip,
        content: (points) => {
          const b = points[0]?.datum
          return b ? rows(b.label, b.streams, b.minutes) : { rows: [] }
        },
      },
    })
  }, [buckets, tick])
  return <Chart definition={definition} height={height} ariaLabel={ariaLabel} className="chart" />
}

/** Horizontal bars per weekday. */
export function WeekdayChart({ weekdays }: { weekdays: Bucket[] }) {
  const definition = useMemo(() => {
    const peak = Math.max(...weekdays.map((b) => b.streams))
    return defineChart({
      marks: [
        barX(weekdays, {
          x: 'streams',
          y: 'label',
          fill: (b) => (b.streams === peak ? ACCENT : ACCENT_SOFT),
          radius: [0, 4, 4, 0],
          maxThickness: 24,
        }),
      ],
      scales: {
        x: streamsAxis,
        y: {
          scale: () => scaleBand<string>().domain(weekdays.map((d) => d.label)).padding(0.25),
          axis: { ticks: { format: (label: string) => label.slice(0, 3) } },
        },
      },
      tooltip: {
        use: tooltip,
        content: (points) => {
          const b = points[0]?.datum
          return b ? rows(b.label, b.streams, b.minutes) : { rows: [] }
        },
      },
    })
  }, [weekdays])
  return <Chart definition={definition} height={260} ariaLabel="Streams per weekday" className="chart" />
}

/** Six intensity levels, from the empty-cell tone to the full accent (one sequential hue). */
const HEAT_LEVELS = ['None', 'Very low', 'Low', 'Medium', 'High', 'Very high'] as const
const HEAT_COLORS = HEAT_LEVELS.map((_, i) =>
  i === 0 ? 'var(--wrapped-heat-empty)' : `color-mix(in oklab, ${ACCENT} ${[0, 22, 42, 62, 82, 100][i]}%, var(--wrapped-heat-empty))`,
)
export const heatLegend = HEAT_LEVELS.map((label, i) => ({ label, color: HEAT_COLORS[i] }))

/** Weekday × hour heatmap. */
export function ListeningHeatmap({ cells }: { cells: HeatCell[] }) {
  const definition = useMemo(() => {
    const max = Math.max(1, ...cells.map((c) => c.streams))
    const data = cells.map((c) => ({
      ...c,
      day: WEEKDAYS_SHORT[c.weekday],
      hourLabel: String(c.hour).padStart(2, '0'),
      level: HEAT_LEVELS[c.streams === 0 ? 0 : Math.min(5, 1 + Math.floor((c.streams / max) * 5))],
    }))
    return defineChart({
      marks: [
        cell(data, {
          x: 'hourLabel',
          y: 'day',
          color: 'level',
          key: (d) => `${d.weekday}-${d.hour}`,
          inset: 1,
          radius: 3,
        }),
      ],
      scales: {
        x: {
          scale: () => scaleBand<string>().domain(data.slice(0, 24).map((d) => d.hourLabel)).padding(0),
          axis: { ticks: { format: (h: string) => (Number(h) % 3 === 0 ? h : '') } },
        },
        y: { scale: () => scaleBand<string>().domain(WEEKDAYS_SHORT).padding(0) },
      },
      color: { scale: () => scaleOrdinal<string, string>().domain(HEAT_LEVELS).range(HEAT_COLORS) },
      tooltip: {
        use: tooltip,
        content: (points) => {
          const d = points[0]?.datum
          return d
            ? { title: `${d.day} ${d.hourLabel}:00–${d.hourLabel}:59`, rows: [{ label: 'Streams', value: formatNumber(d.streams) }] }
            : { rows: [] }
        },
      },
    })
  }, [cells])
  return <Chart definition={definition} height={250} ariaLabel="Streams by weekday and hour" className="chart" />
}
