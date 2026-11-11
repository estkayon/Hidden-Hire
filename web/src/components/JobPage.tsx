import { useEffect, useState } from 'react'
import { fetchJob, type Job, type JobDetail } from '../api'
import { countryName } from '../countries'
import {
  WORK_TYPE_LABEL,
  formatSalary,
  hostOf,
  placeLabel,
  safeEmail,
  safeUrl,
  timeAgo,
} from '../format'
import { Description } from './Description'

type Props = {
  jobId: string
  onToggleSave: (job: Job) => void
}

function parseAlsoSeen(entries: string[]): { source: string; url: string }[] {
  return entries.flatMap((entry) => {
    const [source, ...rest] = entry.split(': ')
    const url = safeUrl(rest.join(': '))
    return url ? [{ source, url }] : []
  })
}

export function JobPage({ jobId, onToggleSave }: Props) {
  const [job, setJob] = useState<JobDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    window.scrollTo({ top: 0 })
    setJob(null)
    setError(null)
    fetchJob(jobId, controller.signal)
      .then(setJob)
      .catch((err: Error) => {
        if (err.name !== 'AbortError') setError(err.message)
      })
    return () => controller.abort()
  }, [jobId])

  if (error) {
    return (
      <div className="job-page">
        <p className="notice">Could not load this job ({error}).</p>
      </div>
    )
  }

  if (!job) {
    return (
      <div className="job-page">
        <div className="job-loading" />
      </div>
    )
  }

  const applyUrl = safeUrl(job.apply_url)
  const email = safeEmail(job.apply_email)
  const alsoSeen = parseAlsoSeen(job.also_seen)
  const workType = WORK_TYPE_LABEL[job.work_type]
  const salary = formatSalary(job)
  const meta = [
    placeLabel(job),
    workType,
    job.posted_at ? `Posted ${timeAgo(job.posted_at)}` : null,
  ].filter(Boolean)

  const facts = [
    ['Company', job.company],
    ['Country', job.country ? countryName(job.country) : null],
    ['Work type', workType ?? null],
    ['Level', job.seniority],
    ['Salary', salary],
    ['Posted', job.posted_at ? new Date(job.posted_at).toLocaleDateString() : null],
    ['Deadline', job.deadline ? new Date(job.deadline).toLocaleDateString() : null],
    ['Source', job.source],
  ].filter((pair): pair is [string, string] => Boolean(pair[1]))

  function toggleSave() {
    if (!job) return
    onToggleSave(job)
    setJob({ ...job, saved: !job.saved })
  }

  return (
    <div className="job-page">
      <div className="job-layout">
        <article className="job-main">
          <header className="job-hero">
            <div className="company-avatar" aria-hidden="true">
              {job.company.trim().charAt(0).toUpperCase()}
            </div>
            <div className="job-hero-text">
              <p className="job-company">
                {job.company}
                {job.is_new && <span className="badge-new">New</span>}
              </p>
              <h1>{job.title}</h1>
              <p className="job-meta">{meta.join('  ·  ')}</p>
            </div>
          </header>

          <section className="job-section">
            <p className="eyebrow">Job description</p>
            <Description text={job.description} />
          </section>

          {job.tags.length > 0 && (
            <section className="job-section">
              <p className="eyebrow">Skills mentioned</p>
              <div className="chips">
                {job.tags.map((tag) => (
                  <span key={tag} className="chip chip-plain">
                    {tag}
                  </span>
                ))}
              </div>
            </section>
          )}
        </article>

        <aside className="job-side">
          <div className="apply-card">
            <p className="apply-title">Interested in this role?</p>
            {applyUrl && (
              <a className="btn-apply" href={applyUrl} target="_blank" rel="noopener noreferrer">
                Apply now
                <span aria-hidden="true">↗</span>
              </a>
            )}
            {applyUrl && <p className="apply-note">Opens {hostOf(applyUrl)} in a new tab</p>}
            {email && (
              <a className="btn-ghost" href={`mailto:${email}`}>
                Email {email}
              </a>
            )}
            {!applyUrl && !email && (
              <p className="apply-note">This posting has no application link or email.</p>
            )}
            <button type="button" className={`btn-ghost${job.saved ? ' is-on' : ''}`} onClick={toggleSave}>
              {job.saved ? '✓ Saved' : 'Save for later'}
            </button>
          </div>

          <div className="side-card">
            <p className="eyebrow">Overview</p>
            <dl className="facts">
              {facts.map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
          </div>

          {alsoSeen.length > 0 && (
            <div className="side-card">
              <p className="eyebrow">Also listed on</p>
              <ul className="also-list">
                {alsoSeen.map(({ source, url }) => (
                  <li key={url}>
                    <a href={url} target="_blank" rel="noopener noreferrer">
                      {source}
                      <span>{hostOf(url)} ↗</span>
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}