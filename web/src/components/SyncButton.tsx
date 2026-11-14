import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchSyncStatus, startSync, type SyncStatus } from '../api'
import './SyncButton.css'

const POLL_RUNNING_MS = 4000
const POLL_IDLE_MS = 60000

function ago(iso: string | null): string {
  if (!iso) return 'not yet'
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  return hours < 48 ? `${hours} h ago` : `${Math.round(hours / 24)} d ago`
}

function label(status: SyncStatus | null): string {
  if (!status) return 'Checking…'
  if (status.running) return status.fetched_locally ? 'Fetching jobs…' : 'Syncing jobs…'
  if (status.error) return 'Sync failed'
  return `Jobs updated ${ago(status.last_fetch_at)}`
}

/** Shows when jobs were last fetched and lets the user start a sync. Calls onSynced when one ends. */
export function SyncButton({ onSynced }: { onSynced: () => void }) {
  const [status, setStatus] = useState<SyncStatus | null>(null)
  const [tick, setTick] = useState(0)
  const wasRunning = useRef(false)

  const apply = useCallback(
    (next: SyncStatus) => {
      if (wasRunning.current && !next.running) onSynced()
      wasRunning.current = next.running
      setStatus(next)
    },
    [onSynced],
  )

  useEffect(() => {
    let timer = 0
    let active = true
    const poll = () => {
      fetchSyncStatus()
        .then((next) => active && apply(next))
        .catch(() => undefined)
        .finally(() => {
          if (active) timer = window.setTimeout(poll, wasRunning.current ? POLL_RUNNING_MS : POLL_IDLE_MS)
        })
    }
    poll()
    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [apply, tick])

  function refresh() {
    startSync()
      .then((next) => {
        apply({ ...next, running: true })
        setTick((t) => t + 1)
      })
      .catch(() => undefined)
  }

  const running = status?.running ?? false
  return (
    <div className={`sync${running ? ' is-running' : ''}${status?.error ? ' is-error' : ''}`}>
      <span className="sync-dot" aria-hidden="true" />
      <span className="sync-label" title={status?.error ?? undefined}>
        {label(status)}
      </span>
      <button type="button" className="sync-btn" onClick={refresh} disabled={running}>
        <span className="sync-icon" aria-hidden="true">
          ↻
        </span>
        Refresh
      </button>
    </div>
  )
}