// TypeScript mirror of the dataclasses in src/spotify_wrapped/statistics.py.
// The Python statistics module does all the processing; this app only displays it.

export interface RankedItem {
  rank: number
  name: string
  streams: number
  minutes: number
  /** Percent of all streams (or of all minutes for time based rankings). */
  share: number
  artist: string | null
}

export interface DayStat {
  date: string
  streams: number
  minutes: number
  top_artist: string | null
}

export interface Bucket {
  key: number | string
  label: string
  streams: number
  minutes: number
}

export interface HeatCell {
  weekday: number
  hour: number
  streams: number
}

export interface Highlight {
  icon: string
  title: string
  value: string
  detail: string
}

export interface Stream {
  track: string
  artist: string
  minutes: number
  played_at: string
}

export interface Overview {
  total_streams: number
  total_minutes: number
  unique_artists: number
  unique_tracks: number
  unique_albums: number | null
  active_days: number
  days_in_period: number
  active_day_share: number
  average_stream_minutes: number
  average_minutes_per_active_day: number
  streams_per_artist: number
  streams_per_track: number
  top_artists_share: number
  one_off_artists: number
  longest_streak: number
  longest_streak_start: string | null
  longest_streak_end: string | null
  longest_stream: Stream | null
  first_stream: string
  last_stream: string
  peak_hour: number
  peak_weekday: number
}

export interface WrappedStatistics {
  key: string
  label: string
  year: number | null
  period_start: string
  period_end: string
  overview: Overview
  highlights: Highlight[]
  top_artists: RankedItem[]
  top_artists_by_time: RankedItem[]
  least_streamed_artists: RankedItem[]
  top_tracks: RankedItem[]
  top_tracks_by_time: RankedItem[]
  top_albums: RankedItem[]
  top_days: DayStat[]
  daily: DayStat[]
  weekly: Bucket[]
  monthly: Bucket[]
  weekdays: Bucket[]
  hours: Bucket[]
  heatmap: HeatCell[]
}

export interface Report {
  schema_version: number
  generated_at: string
  timezone: string
  top_n: number
  years: number[]
  default_view: string
  views: Record<string, WrappedStatistics>
}
