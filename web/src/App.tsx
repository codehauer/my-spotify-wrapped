import { useMemo, useState, type ReactNode } from 'react'
import { Badge } from '@astryxdesign/core/Badge'
import { Card } from '@astryxdesign/core/Card'
import { Divider } from '@astryxdesign/core/Divider'
import { Grid } from '@astryxdesign/core/Grid'
import { Icon } from '@astryxdesign/core/Icon'
import { IconButton } from '@astryxdesign/core/IconButton'
import { HStack, Layout, LayoutContent, VStack } from '@astryxdesign/core/Layout'
import { ProgressBar } from '@astryxdesign/core/ProgressBar'
import { SegmentedControl, SegmentedControlItem } from '@astryxdesign/core/SegmentedControl'
import { Selector } from '@astryxdesign/core/Selector'
import { Table, pixel, proportional, type TableColumn } from '@astryxdesign/core/Table'
import { Heading, Text } from '@astryxdesign/core/Text'
import { TopNav, TopNavHeading, TopNavItem } from '@astryxdesign/core/TopNav'
import { AudioLines, Moon, Sun, SunMoon } from 'lucide-react'
import { ColumnChart, ListeningHeatmap, WeekdayChart, WeeklyChart, heatLegend } from './charts'
import { GenreDonut, GenreHoursChart, MoodHeatmap, TRINITY_AXES, TrinityRadar, genreColors, moodLegend } from './taste'
import { formatDate, formatDuration, formatNumber, formatWeekdayDate, plural } from './format'
import type { DayStat, RankedItem, Report, WrappedStatistics } from './types'

export type ColorMode = 'system' | 'light' | 'dark'

const SECTIONS = [
  { id: 'overview', label: 'Overview' },
  { id: 'favourites', label: 'Favourites' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'habits', label: 'Habits' },
  { id: 'taste', label: 'Taste' },
]

export function App({ report, mode, onModeChange }: {
  report: Report
  mode: ColorMode
  onModeChange: (mode: ColorMode) => void
}) {
  const [viewKey, setViewKey] = useState(report.default_view)
  const stats = report.views[viewKey] ?? report.views[report.default_view]
  const viewOptions = ['all', ...report.years.map(String)].map((key) => ({ value: key, label: report.views[key].label }))
  const nextMode: ColorMode = mode === 'system' ? 'dark' : mode === 'dark' ? 'light' : 'system'

  return (
    <Layout
      height="auto"
      header={
        <TopNav
          label="Report sections"
          heading={<TopNavHeading logo={<span className="brand-mark"><Icon icon={AudioLines} size="sm" /></span>} heading="My Spotify Wrapped" />}
          startContent={SECTIONS.map((s) => <TopNavItem key={s.id} label={s.label} href={`#${s.id}`} />)}
          endContent={
            <HStack gap={2} vAlign="center">
              {viewOptions.length <= 5 ? (
                <SegmentedControl label="Period" value={viewKey} onChange={setViewKey} size="sm">
                  {viewOptions.map((o) => <SegmentedControlItem key={o.value} value={o.value} label={o.label} />)}
                </SegmentedControl>
              ) : (
                <Selector label="Period" isLabelHidden size="sm" variant="secondary" options={viewOptions} value={viewKey} onChange={setViewKey} />
              )}
              <IconButton
                label={`Color mode: ${mode}. Switch to ${nextMode}`}
                tooltip={`Theme: ${mode}`}
                variant="ghost"
                size="sm"
                icon={<Icon icon={mode === 'system' ? SunMoon : mode === 'dark' ? Moon : Sun} />}
                onClick={() => onModeChange(nextMode)}
              />
            </HStack>
          }
        />
      }
      content={
        <LayoutContent padding={6}>
          <main className="page">
            <VStack gap={10}>
              <Hero stats={stats} report={report} />
              <Overview stats={stats} />
              <Favourites stats={stats} />
              <Timeline stats={stats} />
              <Habits stats={stats} />
              <Taste stats={stats} />
              <Footer report={report} />
            </VStack>
          </main>
        </LayoutContent>
      }
    />
  )
}

// --------------------------------------------------------------------------
// Building blocks
// --------------------------------------------------------------------------

function SectionHeader({ id, title, description }: { id: string; title: string; description?: string }) {
  return (
    <VStack gap={1}>
      <span id={id} className="anchor" />
      <Heading level={2}>{title}</Heading>
      {description && <Text type="supporting">{description}</Text>}
    </VStack>
  )
}

function ChartCard({ title, subtitle, children, actions }: {
  title: string
  subtitle?: string
  children: ReactNode
  actions?: ReactNode
}) {
  return (
    <Card>
      <VStack gap={4}>
        <HStack hAlign="between" vAlign="center" gap={3} wrap="wrap">
          <VStack gap={0.5}>
            <Heading level={4}>{title}</Heading>
            {subtitle && <Text type="supporting">{subtitle}</Text>}
          </VStack>
          {actions}
        </HStack>
        {children}
      </VStack>
    </Card>
  )
}

// --------------------------------------------------------------------------
// Sections
// --------------------------------------------------------------------------

function Hero({ stats, report }: { stats: WrappedStatistics; report: Report }) {
  const title = stats.year ? `Your ${stats.year} in music` : 'Your music, all time'
  return (
    <VStack gap={2}>
      <HStack gap={2} vAlign="center" wrap="wrap">
        <Badge variant="green" label={stats.label} />
        <Text type="supporting">
          {formatDate(stats.period_start)} – {formatDate(stats.period_end)} · times in {report.timezone}
        </Text>
      </HStack>
      <Text type="display-2" as="div">{title}</Text>
      <Text type="large" color="secondary">
        {plural(stats.overview.total_streams, 'stream')}, {formatDuration(stats.overview.total_minutes)} of listening and{' '}
        {plural(stats.overview.unique_artists, 'artist')}. Here is what stood out.
      </Text>
    </VStack>
  )
}

function StatTile({ label, value, caption }: { label: string; value: string; caption: string }) {
  return (
    <Card>
      <VStack gap={1}>
        <Text type="label" color="secondary">{label}</Text>
        <Text type="display-3" as="div" hasTabularNumbers>{value}</Text>
        <Text type="supporting">{caption}</Text>
      </VStack>
    </Card>
  )
}

function Overview({ stats }: { stats: WrappedStatistics }) {
  const o = stats.overview
  return (
    <VStack gap={4}>
      <SectionHeader id="overview" title="Overview" />
      <Grid columns={{ minWidth: 150, max: 6, repeat: 'fit' }} gap={4}>
        <StatTile label="Streams" value={formatNumber(o.total_streams)} caption={`${o.average_stream_minutes.toFixed(1)} min per stream`} />
        <StatTile label="Listening time" value={formatDuration(o.total_minutes)} caption={`${formatNumber(Math.round(o.total_minutes))} minutes`} />
        <StatTile label="Artists" value={formatNumber(o.unique_artists)} caption={`${o.streams_per_artist.toFixed(1)} streams each`} />
        <StatTile label="Tracks" value={formatNumber(o.unique_tracks)} caption={`${o.streams_per_track.toFixed(1)} streams each`} />
        <StatTile label="Active days" value={`${o.active_days} / ${o.days_in_period}`} caption={`${o.active_day_share}% of the period`} />
        <StatTile label="Longest streak" value={plural(o.longest_streak, 'day')} caption={`${formatDuration(o.average_minutes_per_active_day)} per active day`} />
      </Grid>
      <Grid columns={{ minWidth: 300, repeat: 'fit' }} gap={4}>
        {stats.highlights.map((h) => (
          <Card key={h.title}>
            <HStack gap={3} vAlign="start">
              <span className="highlight-icon" aria-hidden="true">{h.icon}</span>
              <VStack gap={1}>
                <Text type="label" color="secondary">{h.title}</Text>
                <Heading level={4}>{h.value}</Heading>
                <Text type="supporting">{h.detail}</Text>
              </VStack>
            </HStack>
          </Card>
        ))}
      </Grid>
    </VStack>
  )
}

type Metric = 'streams' | 'minutes'

interface RankingRow extends Record<string, unknown> {
  id: string
  item: RankedItem
}

function RankingCard({ title, byStreams, byTime }: { title: string; byStreams: RankedItem[]; byTime?: RankedItem[] }) {
  const [metric, setMetric] = useState<Metric>('streams')
  const items = metric === 'minutes' && byTime ? byTime : byStreams
  const max = Math.max(...items.map((i) => (metric === 'streams' ? i.streams : i.minutes)), 1)
  const columns = useMemo<TableColumn<RankingRow>[]>(() => [
    {
      key: 'rank', header: '#', width: pixel(44),
      renderCell: ({ item }) => <Text weight="semibold" color={item.rank <= 3 ? 'accent' : 'secondary'} hasTabularNumbers>{item.rank}</Text>,
    },
    {
      key: 'name', header: 'Name', width: proportional(3, { minWidth: 160 }),
      renderCell: ({ item }) => (
        <VStack gap={0.5}>
          <Text weight="semibold" maxLines={1}>{item.name}</Text>
          {item.artist && <Text type="supporting" maxLines={1}>{item.artist}</Text>}
        </VStack>
      ),
    },
    {
      key: 'value', header: metric === 'streams' ? 'Streams' : 'Time', width: proportional(2, { minWidth: 120 }),
      renderCell: ({ item }) => {
        const value = metric === 'streams' ? item.streams : item.minutes
        const text = metric === 'streams' ? formatNumber(item.streams) : formatDuration(item.minutes)
        return (
          <VStack gap={1}>
            <div className="ranking-bar">
              <ProgressBar value={value} max={max} label={`${item.name}: ${text}`} isLabelHidden />
            </div>
            <Text type="supporting" hasTabularNumbers>
              {text} · {item.share}%
            </Text>
          </VStack>
        )
      },
    },
  ], [metric, max])

  return (
    <ChartCard
      title={title}
      actions={byTime && (
        <SegmentedControl label={`Rank ${title.toLowerCase()} by`} value={metric} onChange={(v) => setMetric(v as Metric)} size="sm">
          <SegmentedControlItem value="streams" label="Streams" />
          <SegmentedControlItem value="minutes" label="Time" />
        </SegmentedControl>
      )}
    >
      <Table<RankingRow>
        data={items.map((item) => ({ id: `${item.rank}-${item.name}`, item }))}
        columns={columns}
        idKey="id"
        density="compact"
        hasHover
      />
    </ChartCard>
  )
}

function Favourites({ stats }: { stats: WrappedStatistics }) {
  return (
    <VStack gap={4}>
      <SectionHeader
        id="favourites"
        title="Favourites"
        description={`Your top ${stats.top_artists.length} artists account for ${stats.overview.top_artists_share}% of all streams.`}
      />
      <Grid columns={{ minWidth: 420, repeat: 'fit' }} gap={4}>
        <RankingCard title="Top artists" byStreams={stats.top_artists} byTime={stats.top_artists_by_time} />
        <RankingCard title="Top tracks" byStreams={stats.top_tracks} byTime={stats.top_tracks_by_time} />
        {stats.top_albums.length > 0 && <RankingCard title="Top albums" byStreams={stats.top_albums} />}
        <RankingCard title="Least streamed artists" byStreams={stats.least_streamed_artists} />
      </Grid>
    </VStack>
  )
}

interface DayRow extends Record<string, unknown> {
  id: string
  day: DayStat
}

function Timeline({ stats }: { stats: WrappedStatistics }) {
  const busiest = stats.weekly.reduce((a, b) => (b.streams > a.streams ? b : a), stats.weekly[0])
  const monthTick = useMemo(() => {
    const every = Math.max(1, Math.ceil(stats.monthly.length / 8))
    return (label: string, index: number) => (index % every === 0 ? label.replace(/ (\d\d)(\d\d)$/, " '$2") : '')
  }, [stats.monthly.length])
  const dayColumns: TableColumn<DayRow>[] = [
    { key: 'date', header: 'Day', width: proportional(2, { minWidth: 130 }), renderCell: ({ day }) => <Text weight="semibold">{formatWeekdayDate(day.date)}</Text> },
    { key: 'streams', header: 'Streams', width: pixel(80), renderCell: ({ day }) => <Text hasTabularNumbers>{formatNumber(day.streams)}</Text> },
    { key: 'time', header: 'Time', width: pixel(96), renderCell: ({ day }) => <Text hasTabularNumbers>{formatDuration(day.minutes)}</Text> },
    { key: 'artist', header: 'Mostly', width: proportional(2, { minWidth: 120 }), renderCell: ({ day }) => <Text type="supporting" maxLines={1}>{day.top_artist}</Text> },
  ]
  return (
    <VStack gap={4}>
      <SectionHeader id="timeline" title="Timeline" description="How your listening developed over time." />
      <ChartCard title="Streams per week" subtitle={busiest ? `Busiest: ${busiest.label} with ${plural(busiest.streams, 'stream')}` : undefined}>
        <WeeklyChart weeks={stats.weekly} />
      </ChartCard>
      <Grid columns={{ minWidth: 420, repeat: 'fit' }} gap={4}>
        <ChartCard title="Streams per month">
          <ColumnChart buckets={stats.monthly} ariaLabel="Streams per month" tick={monthTick} height={300} />
        </ChartCard>
        <ChartCard title="Your biggest days">
          <Table<DayRow>
            data={stats.top_days.map((day) => ({ id: day.date, day }))}
            columns={dayColumns}
            idKey="id"
            density="compact"
            hasHover
          />
        </ChartCard>
      </Grid>
    </VStack>
  )
}

function Habits({ stats }: { stats: WrappedStatistics }) {
  const o = stats.overview
  const hourTick = (label: string, index: number) => (index % 3 === 0 ? label.slice(0, 2) : '')
  return (
    <VStack gap={4}>
      <SectionHeader id="habits" title="Habits" description="When the music plays." />
      <Grid columns={{ minWidth: 420, repeat: 'fit' }} gap={4}>
        <ChartCard title="Hour of day" subtitle={`Peak at ${String(o.peak_hour).padStart(2, '0')}:00`}>
          <ColumnChart buckets={stats.hours} ariaLabel="Streams per hour of day" tick={hourTick} height={260} />
        </ChartCard>
        <ChartCard title="Day of week" subtitle={`${stats.weekdays[o.peak_weekday].label} is your day`}>
          <WeekdayChart weekdays={stats.weekdays} />
        </ChartCard>
      </Grid>
      <ChartCard title="Weekday × hour" subtitle="Each cell is one hour of the week">
        <ListeningHeatmap cells={stats.heatmap} />
        <HStack gap={3} vAlign="center" wrap="wrap">
          <Text type="supporting">Fewer streams</Text>
          {heatLegend.map((l) => (
            <span key={l.label} className="heat-swatch" style={{ background: l.color }} title={l.label} />
          ))}
          <Text type="supporting">More streams</Text>
        </HStack>
      </ChartCard>
    </VStack>
  )
}

function Legend({ items }: { items: { label: string; color: string; value?: string; strong?: boolean }[] }) {
  return (
    <ul className="legend">
      {items.map((i) => (
        <li key={i.label}>
          <span className="legend-swatch" style={{ background: i.color }} aria-hidden="true" />
          <Text weight={i.strong ? 'semibold' : undefined}>{i.label}</Text>
          {i.value && <Text type="supporting" hasTabularNumbers>{i.value}</Text>}
        </li>
      ))}
    </ul>
  )
}

function Taste({ stats }: { stats: WrappedStatistics }) {
  const t = stats.taste
  if (!t) {
    return (
      <VStack gap={4}>
        <SectionHeader id="taste" title="Taste" />
        <Card>
          <Text type="supporting">
            Your Spotify export contains no genres. Create the report with <code>--genres</code> to look up the genres of your
            most played artists on MusicBrainz (only artist names are sent, results are cached), or with{' '}
            <code>--genres my_genres.json</code> to provide them yourself.
          </Text>
        </Card>
      </VStack>
    )
  }
  const colors = genreColors(t.genres)
  const tr = t.trinity
  const dominant = TRINITY_AXES.find((a) => a.key === tr.dominant)
  const moments = t.happiest_hour !== null && t.gloomiest_hour !== null
    ? `Happiest at ${String(t.happiest_hour).padStart(2, '0')}:00, gloomiest at ${String(t.gloomiest_hour).padStart(2, '0')}:00`
    : undefined
  return (
    <VStack gap={4}>
      <SectionHeader
        id="taste"
        title="Taste"
        description={`Genres, mood and your holy trinity. ${t.coverage}% of your listening time has a known genre.`}
      />
      <Grid columns={{ minWidth: 420, repeat: 'fit' }} gap={4}>
        <ChartCard title="Genres" subtitle="Share of your listening time">
          <div className="donut-layout">
            <GenreDonut genres={t.genres} />
            <Legend items={t.genres.map((g, i) => ({ label: g.genre, color: colors.get(g.genre) ?? '', value: `${g.share.toFixed(1)}%`, strong: i === 0 }))} />
          </div>
        </ChartCard>
        <ChartCard title="Holy trinity" subtitle={`${dominant?.icon ?? ''} Mostly ${dominant?.label.toLowerCase() ?? tr.dominant}`}>
          <TrinityRadar trinity={tr} />
          <HStack gap={4} hAlign="center" wrap="wrap">
            {TRINITY_AXES.map((a) => (
              <Text key={a.key} weight={a.key === tr.dominant ? 'semibold' : undefined} hasTabularNumbers>
                {a.icon} {a.label} {Math.round(tr[a.key])}
              </Text>
            ))}
          </HStack>
          <Text type="supporting">{tr.tagline}</Text>
        </ChartCard>
      </Grid>
      <ChartCard title="Mood by weekday and hour" subtitle={moments}>
        <MoodHeatmap cells={t.mood_heatmap} average={t.average_happiness} />
        <HStack gap={3} vAlign="center" wrap="wrap">
          <Text type="supporting">Sadder</Text>
          {moodLegend.map((l) => <span key={l.label} className="heat-swatch" style={{ background: l.color }} title={l.label} />)}
          <Text type="supporting">Happier than your average of {Math.round(t.average_happiness)}/100</Text>
        </HStack>
      </ChartCard>
      <ChartCard title="Genres by hour of day" subtitle="Share of each hour's listening time">
        <GenreHoursChart genres={t.genres} cells={t.genre_hours} />
        <Legend items={t.genres.map((g) => ({ label: g.genre, color: colors.get(g.genre) ?? '' }))} />
      </ChartCard>
      <Text type="supporting">
        Genres come from the artists' tags. Mood (happiness) and the atzig/fotzig/mausig profile are estimated from those
        genres and from when you listen, not from the individual songs.
      </Text>
    </VStack>
  )
}

function Footer({ report }: { report: Report }) {
  return (
    <VStack gap={3}>
      <Divider />
      <Text type="supporting">
        Generated {new Date(report.generated_at).toLocaleString()} by My Spotify Wrapped from your personal Spotify data export.
        Everything was computed on your own computer; this file contains no tracking and needs no internet connection.
      </Text>
    </VStack>
  )
}
