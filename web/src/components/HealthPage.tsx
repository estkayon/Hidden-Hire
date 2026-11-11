import { useEffect, useState } from 'react'
import { fetchHealth, type HealthReport, type SourceStatus } from '../api'
import { timeAgo } from '../format'

const STATUS_LABEL: Record<SourceStatus['status'], string> = {
  ok: 'Healthy',
  partial: 'Partial',
  empty: 'No jobs',
  failing: 'Failing',
}

const STATUS_ORDER: SourceStatus['status'][] = ['failing', 'partial', 'empty', 'ok']
const STALE_HOURS = 6

function SourceCard({ source, index }: { source: SourceStatus; index: number }) {
  return (
    <article className={`source-card is-${source.status}`} style={{ animationDelay: `${Math.min(index, 12) * 30}ms` }}>
      <header className="source-head">
        <h3>{source.source}</h3>
        <span className={`status-pill is-${source.status}`}>{STATUS_LABEL[source.status]}</span>
      </header>

      <div className="source-stats">
        <div>
          <span className="stat-value">{source.jobs_found.toLocaleString()}</span>
          <span className="stat-label">found</span>
        </div>
        <div>
          <span className="stat-value">{source.jobs_kept.toLocaleString()}</span>
          <span className="stat-label">kept</span>
        </div>
        <div>
          <span className="stat-value">{source.errors.length}</span>
          <span className="stat-label">errors</span>
        </div>
      </div>

      <p className="source-time">Last run {timeAgo(source.run_at)}</p>

      {source.errors.length > 0 && (
        <details className="source-errors">
          <summary>Show errors</summary>
          <ul>
            {source.errors.map((error, i) => (
              <li key={i}>{error}</li>
            ))}
          </ul>
        </details>
      )}
    </article>
  )
}

export function HealthPage() {
  const [report, setReport] = useState<HealthReport | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    window.scrollTo({ top: 0 })
    fetchHealth()
      .then(setReport)
      .catch((err: Error) => setError(err.message))
  }, [])

  if (error) {
    return (
      <div className="health-page">
        <p className="notice">Could not load source health ({error}).</p>
      </div>
    )
  }

  if (!report) {
    return (
      <div className="health-page">
        <div className="job-loading" />
      </div>
    )
  }

  const counts = STATUS_ORDER.map((status) => ({
    status,
    count: report.sources.filter((s) => s.status === status).length,
  }))
  const sorted = [...report.sources].sort(
    (a, b) => STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status) || a.source.localeCompare(b.source),
  )
  const hoursSinceRun = report.last_run_at
    ? (Date.now() - new Date(report.last_run_at).getTime()) / 3_600_000
    : null

  return (
    <div className="health-page">
      <header className="health-hero">
        <div>
          <p className="eyebrow">Source health</p>
          <h1>{report.sources.length} sources</h1>
          <p className="health-sub">
            {report.last_run_at ? `Last fetch ${timeAgo(report.last_run_at)}` : 'No fetch recorded yet. Run the sync first.'}
          </p>
        </div>
        <div className="health-counts">
          {counts.map(({ status, count }) => (
            <div key={status} className={`count-tile is-${status}`}>
              <span className="count-value">{count}</span>
              <span className="count-label">{STATUS_LABEL[status]}</span>
            </div>
          ))}
        </div>
      </header>

      {hoursSinceRun !== null && hoursSinceRun > STALE_HOURS && (
        <p className="notice">
          The last fetch was more than {STALE_HOURS} hours ago. Check that the GitHub Actions workflow is enabled,
          then run <code>python -m app.sync</code>.
        </p>
      )}

      <section className="source-grid">
        {sorted.map((source, i) => (
          <SourceCard key={source.source} source={source} index={i} />
        ))}
      </section>
    </div>
  )
}