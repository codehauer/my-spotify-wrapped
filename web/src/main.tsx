import { StrictMode, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { Theme } from '@astryxdesign/core/theme'
import { EmptyState } from '@astryxdesign/core/EmptyState'
import { neutralTheme } from '@astryxdesign/theme-neutral/built'
import '@fontsource-variable/figtree'
import './styles.css'
import { App, type ColorMode } from './App'
import { loadReport } from './data'
import type { Report } from './types'

const MODE_KEY = 'my-spotify-wrapped:mode'

function readMode(): ColorMode {
  try {
    const stored = localStorage.getItem(MODE_KEY)
    if (stored === 'light' || stored === 'dark' || stored === 'system') return stored
  } catch {
    // Storage can be unavailable (private mode, file:// restrictions).
  }
  return 'system'
}

function Root({ report, error }: { report?: Report; error?: string }) {
  const [mode, setMode] = useState<ColorMode>(readMode)
  const changeMode = (next: ColorMode) => {
    setMode(next)
    try {
      localStorage.setItem(MODE_KEY, next)
    } catch {
      // Ignore: the choice just won't be remembered.
    }
  }
  return (
    <Theme theme={neutralTheme} mode={mode}>
      {report ? (
        <App report={report} mode={mode} onModeChange={changeMode} />
      ) : (
        <div className="page">
          <EmptyState title="No statistics to show" description={error} headingLevel={1} />
        </div>
      )}
    </Theme>
  )
}

const root = createRoot(document.getElementById('root')!)
loadReport()
  .then((report) => root.render(<StrictMode><Root report={report} /></StrictMode>))
  .catch((error: unknown) => root.render(<Root error={error instanceof Error ? error.message : String(error)} />))
