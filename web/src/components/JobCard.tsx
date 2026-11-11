import type { Job } from '../api'

const WORK_TYPE_LABEL: Record<string, string> = {
  remote: 'Remote',
  hybrid: 'Hybrid',
  onsite: 'Onsite',
  unknown: 'Work type not stated',
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

export function JobCard({ job }: { job: Job }) {
  const place = [job.city, job.country].filter(Boolean).join(', ') || job.location_raw || 'Location not stated'
  const salary = formatSalary(job)
  const sources = job.also_seen.length ? `${job.source} +${job.also_seen.length}` : job.source

  return (
    <article className="card">
      <header className="card-head">
        <h2 className="card-title">{job.title}</h2>
        {job.is_new && <span className="badge-new">New</span>}
      </header>
      <p className="card-company">{job.company}</p>
      <ul className="card-meta">
        <li>{place}</li>
        <li>{WORK_TYPE_LABEL[job.work_type] ?? job.work_type}</li>
        {job.posted_at && (
          <li>
            {new Date(job.posted_at).toLocaleDateString()} · {timeAgo(job.posted_at)}
          </li>
        )}
        <li>{sources}</li>
        {salary && <li>{salary}</li>}
      </ul>
    </article>
  )
}