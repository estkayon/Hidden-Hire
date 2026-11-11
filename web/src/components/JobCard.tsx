import type { Job } from '../api'
import { WORK_TYPE_LABEL, formatSalary, placeLabel, timeAgo } from '../format'

type Props = {
  job: Job
  index: number
  onOpen: (jobId: string) => void
  onToggleSave: (job: Job) => void
}

export function JobCard({ job, index, onOpen, onToggleSave }: Props) {
  const salary = formatSalary(job)
  const workType = WORK_TYPE_LABEL[job.work_type]

  return (
    <article className="card" style={{ animationDelay: `${Math.min(index, 10) * 40}ms` }}>
      <header className="card-head">
        <div className="card-heading">
          {job.is_new && <span className="badge-new">New</span>}
          <h2 className="card-title">{job.title}</h2>
          <p className="card-company">{job.company}</p>
        </div>

        <div className="card-actions">
          <button
            type="button"
            className={`save${job.saved ? ' is-saved' : ''}`}
            aria-pressed={job.saved}
            aria-label={job.saved ? 'Remove from saved' : 'Save job'}
            onClick={() => onToggleSave(job)}
          >
            <svg viewBox="0 0 24 24" width="17" height="17" aria-hidden="true">
              <path d="M6 3.5h12a1 1 0 0 1 1 1V21l-7-4.2L5 21V4.5a1 1 0 0 1 1-1z" />
            </svg>
          </button>
          <button type="button" className="card-apply" onClick={() => onOpen(job.id)}>
            Apply
          </button>
        </div>
      </header>

      {(workType || job.seniority || salary) && (
        <div className="chips">
          {workType && <span className="chip chip-sky">{workType}</span>}
          {job.seniority && <span className="chip chip-meadow">{job.seniority}</span>}
          {salary && <span className="chip chip-plain">{salary}</span>}
        </div>
      )}

      <footer className="card-foot">
        <span className="card-place">{placeLabel(job)}</span>
        <span className="card-time">{job.posted_at ? timeAgo(job.posted_at) : 'Date not stated'}</span>
      </footer>
    </article>
  )
}