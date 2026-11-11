import type { Job } from '../api'
import { countryName } from '../countries'

const WORK_TYPE_LABEL: Record<string, string> = {
  remote: 'Remote',
  hybrid: 'Hybrid',
  onsite: 'Onsite',
}

function timeAgo(iso: string): string {
  const hours = Math.floor((Date.now() - new Date(iso).getTime()) / 3_600_000)
  if (hours < 1) return 'just now'
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

function formatSalary(job: Job): string | null {
  if (!job.salary_currency || (job.salary_min === null && job.salary_max === null)) return null
  const amounts = [job.salary_min, job.salary_max]
    .filter((value): value is number => value !== null)
    .map((value) => value.toLocaleString())
  const range = [...new Set(amounts)].join(' – ')
  const period = job.salary_period ? ` / ${job.salary_period}` : ''
  return `${job.salary_currency} ${range}${period}`
}

type Props = {
  job: Job
  index: number
  onToggleSave: (job: Job) => void
}

export function JobCard({ job, index, onToggleSave }: Props) {
  const place =
    [job.city, job.country && countryName(job.country)].filter(Boolean).join(', ') ||
    job.location_raw ||
    'Location not stated'
  const salary = formatSalary(job)
  const sources = job.also_seen.length ? `${job.source} +${job.also_seen.length}` : job.source
  const workType = WORK_TYPE_LABEL[job.work_type]

  return (
    <article className="card" style={{ animationDelay: `${Math.min(index, 10) * 40}ms` }}>
      <header className="card-head">
        <div className="card-heading">
          {job.is_new && <span className="badge-new">New</span>}
          <h2 className="card-title">{job.title}</h2>
          <p className="card-company">{job.company}</p>
        </div>
        <button
          type="button"
          className={`save${job.saved ? ' is-saved' : ''}`}
          aria-pressed={job.saved}
          aria-label={job.saved ? 'Remove from saved' : 'Save job'}
          onClick={() => onToggleSave(job)}
        >
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <path d="M6 3.5h12a1 1 0 0 1 1 1V21l-7-4.2L5 21V4.5a1 1 0 0 1 1-1z" />
          </svg>
        </button>
      </header>

      <div className="chips">
        {workType && <span className="chip chip-sky">{workType}</span>}
        {job.seniority && <span className="chip chip-meadow">{job.seniority}</span>}
        {salary && <span className="chip chip-plain">{salary}</span>}
      </div>

      <footer className="card-foot">
        <span className="card-place">{place}</span>
        <span className="card-meta">
          {job.posted_at ? timeAgo(job.posted_at) : 'Date not stated'} · {sources}
        </span>
      </footer>
    </article>
  )
}