import type { Job } from '../api'
import { eligibilityInfo } from '../eligibility'
import { WORK_TYPE_LABEL, formatSalary, placeLabel, timeAgo } from '../format'
import './JobCard.css'
import { MatchRing } from './MatchRing'

type Props = {
  job: Job
  index: number
  onOpen: (jobId: string) => void
  onToggleSave: (job: Job) => void
}

function Icon({
  name,
}: {
  name: 'onsite' | 'remote' | 'hybrid' | 'level' | 'salary' | 'clock' | 'pin' | 'good' | 'maybe' | 'no'
}) {
  const paths = {
    onsite: 'M4 21V5l7-2v18M11 21h9V9l-9-2M7 8h1M7 12h1M7 16h1M14 12h3M14 16h3',
    remote: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3z',
    hybrid: 'M3 11l9-7 9 7M5 10v10h5v-6h4v6h5V10',
    level: 'M12 21v-7M12 14c-4 0-6-2.5-6-6 3.5 0 6 2 6 6zm0 0c0-4 2.5-6 6-6 0 3.5-2 6-6 6zM17 3l.7 1.5L19 5l-1.3.6L17 7l-.7-1.4L15 5l1.3-.5z',
    salary: 'M3 7h18v10H3zM12 10a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM6 10v4M18 10v4',
    clock: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 7v5l3 2',
    pin: 'M12 21s7-6.2 7-12a7 7 0 1 0-14 0c0 5.8 7 12 7 12zM12 11.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z',
    good: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM8 12.5l2.7 2.7L16 9.8',
    maybe: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 7.5v5.5M12 16.5v.01',
    no: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM9 9l6 6M15 9l-6 6',
  }
  return (
    <svg className="jc-icon" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
      <path d={paths[name]} />
    </svg>
  )
}

export function JobCard({ job, index, onOpen, onToggleSave }: Props) {
  const salary = formatSalary(job)
  const workType = WORK_TYPE_LABEL[job.work_type]
  const workIcon = job.work_type === 'remote' ? 'remote' : job.work_type === 'hybrid' ? 'hybrid' : 'onsite'
  const elig = eligibilityInfo(job)

  return (
    <article className="card job-card" style={{ animationDelay: `${Math.min(index, 10) * 40}ms` }}>
      <header className="jc-top">
        <div className="jc-company">
          <span className="jc-avatar" aria-hidden="true">
            {job.company.trim().charAt(0).toUpperCase()}
          </span>
          <span className="jc-company-name">{job.company}</span>
          {job.is_new && <span className="jc-new">New</span>}
        </div>

        <div className="jc-top-right">
          <span className="jc-time">
            <Icon name="clock" />
            {job.posted_at ? timeAgo(job.posted_at) : 'Date not stated'}
          </span>
          <button
            type="button"
            className={`jc-save${job.saved ? ' is-saved' : ''}`}
            aria-pressed={job.saved}
            aria-label={job.saved ? 'Remove from saved' : 'Save job'}
            onClick={() => onToggleSave(job)}
          >
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
              <path d="M6 3.5h12a1 1 0 0 1 1 1V21l-7-4.2L5 21V4.5a1 1 0 0 1 1-1z" />
            </svg>
          </button>
        </div>
      </header>

      <div className="jc-body">
        <div className="jc-main">
          <h2 className="jc-title">{job.title}</h2>
          <div className="jc-chips">
            <span className={`jc-chip is-elig is-${elig.tone}`}>
              <Icon name={elig.tone} />
              {elig.label}
            </span>
            {workType && (
              <span className="jc-chip is-work">
                <Icon name={workIcon} />
                {workType}
              </span>
            )}
            {job.seniority && (
              <span className="jc-chip is-level">
                <Icon name="level" />
                {job.seniority}
              </span>
            )}
            {salary && (
              <span className="jc-chip is-salary">
                <Icon name="salary" />
                {salary}
              </span>
            )}
          </div>
        </div>
        {job.match !== null && <MatchRing match={job.match} />}
      </div>

      <footer className="jc-foot">
        <span className="jc-place">
          <Icon name="pin" />
          <span>{placeLabel(job)}</span>
        </span>
        <button type="button" className="jc-apply" onClick={() => onOpen(job.id)}>
          Apply
          <span aria-hidden="true">↗</span>
        </button>
      </footer>
    </article>
  )
}