import type { RecruiterView as View } from '../api'
import { MatchRing, band } from './MatchRing'
import { Modal } from './Modal'
import './RecruiterView.css'

type DimensionKey = 'skills' | 'experience' | 'eligibility' | 'domain' | 'education'
type Requirement = NonNullable<View['requirements']>[number]

const DIMENSIONS: { key: DimensionKey; label: string; weight: string }[] = [
  { key: 'skills', label: 'Skills and tools', weight: '35%' },
  { key: 'experience', label: 'Experience and level', weight: '25%' },
  { key: 'eligibility', label: 'Eligibility', weight: '20%' },
  { key: 'domain', label: 'Domain and projects', weight: '15%' },
  { key: 'education', label: 'Education', weight: '5%' },
]

const VERDICT = {
  apply: { label: 'Apply', tone: 'good' },
  stretch: { label: 'Stretch', tone: 'maybe' },
  skip: { label: 'Skip', tone: 'no' },
} as const

const STATUS = {
  met: { icon: '✓', label: 'Met' },
  partly: { icon: '◐', label: 'Partly' },
  missing: { icon: '✕', label: 'Missing' },
} as const

function List({ title, items, tone }: { title: string; items: string[]; tone: 'good' | 'gap' | 'block' }) {
  if (items.length === 0) return null
  return (
    <div className={`rv-list is-${tone}`}>
      <p className="rv-list-title">{title}</p>
      <ul>
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  )
}

function Requirements({ title, items }: { title: string; items: Requirement[] }) {
  if (items.length === 0) return null
  return (
    <div className="rv-reqs">
      <p className="rv-list-title">{title}</p>
      <ul>
        {items.map((r, i) => (
          <li key={i} className={`is-${r.status}`}>
            <span className="rv-req-icon" aria-label={STATUS[r.status].label}>
              {STATUS[r.status].icon}
            </span>
            <div>
              <p className="rv-req-text">{r.text}</p>
              {r.evidence && <p className="rv-req-evidence">{r.evidence}</p>}
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

function Details({ view }: { view: View }) {
  const requirements = view.requirements ?? []
  const keywords = view.keywords
  const verdict = view.verdict ? VERDICT[view.verdict] : null

  return (
    <>
      <header className="rv-head">
        <div>
          <p className="eyebrow">Recruiter view</p>
          {view.summary && <p className="rv-summary">{view.summary}</p>}
          <p className="rv-note">AI judgment based on your CV. It is not a hiring probability.</p>
        </div>
        <MatchRing match={view.total} />
      </header>

      {verdict && (
        <div className={`rv-verdict is-${verdict.tone}`}>
          <span className="rv-verdict-pill">{verdict.label}</span>
          {view.verdict_reason && <p>{view.verdict_reason}</p>}
        </div>
      )}

      <Requirements title="Must have" items={requirements.filter((r) => r.importance === 'must')} />
      <Requirements title="Nice to have" items={requirements.filter((r) => r.importance === 'nice')} />

      {keywords && keywords.percent !== null && (
        <div className="rv-keywords">
          <div className="rv-dim-top">
            <span className="rv-dim-label">ATS keyword coverage</span>
            <span className="rv-dim-score">{keywords.percent}%</span>
          </div>
          <div className={`rv-bar is-${band(keywords.percent)}`}>
            <div style={{ width: `${keywords.percent}%` }} />
          </div>
          <div className="chips rv-kw-chips">
            {keywords.matched.map((k) => (
              <span key={k} className="chip rv-kw is-have">
                {k}
              </span>
            ))}
            {keywords.missing.map((k) => (
              <span key={k} className="chip rv-kw is-missing">
                {k}
              </span>
            ))}
          </div>
        </div>
      )}

      <ul className="rv-dims">
        {DIMENSIONS.map(({ key, label, weight }) => {
          const { score, reason } = view[key]
          return (
            <li key={key}>
              <div className="rv-dim-top">
                <span className="rv-dim-label">
                  {label} <span className="rv-weight">{weight}</span>
                </span>
                <span className="rv-dim-score">{score}</span>
              </div>
              <div className={`rv-bar is-${band(score)}`}>
                <div style={{ width: `${score}%` }} />
              </div>
              <p className="rv-reason">{reason}</p>
            </li>
          )
        })}
      </ul>

      <div className="rv-lists">
        <List title="Strengths" items={view.strengths} tone="good" />
        <List title="Gaps" items={view.gaps} tone="gap" />
        <List title="Blockers" items={view.blockers} tone="block" />
      </div>
    </>
  )
}

export function RecruiterModal({ view, onClose }: { view: View; onClose: () => void }) {
  return (
    <Modal label="Recruiter view" onClose={onClose}>
      <Details view={view} />
    </Modal>
  )
}

type CardProps = {
  view: View | null
  outdated: boolean
  judging: boolean
  error: string | null
  onRequest: () => void
  onOpen: () => void
}

export function RecruiterCard({ view, outdated, judging, error, onRequest, onOpen }: CardProps) {
  const verdict = view?.verdict ? VERDICT[view.verdict] : null
  return (
    <div className="side-card rv-card">
      <p className="eyebrow">Recruiter view</p>
      {view ? (
        <div className="rv-card-result">
          <MatchRing match={view.total} />
          {verdict && <span className={`rv-verdict-pill is-${verdict.tone}`}>{verdict.label}</span>}
          <button type="button" className="rv-btn" onClick={onOpen}>
            View details
          </button>
          {outdated && (
            <div className="rv-outdated">
              <p>Your CV changed since this review.</p>
              <button type="button" disabled={judging} onClick={onRequest}>
                {judging ? 'Reviewing…' : 'Refresh'}
              </button>
            </div>
          )}
        </div>
      ) : (
        <>
          <p className="rv-card-text">A recruiter-style review of this job against your CV.</p>
          <button type="button" className="rv-btn" disabled={judging} onClick={onRequest}>
            {judging ? 'Reviewing…' : 'Get recruiter view'}
          </button>
        </>
      )}
      {error && <p className="rv-error">{error}</p>}
    </div>
  )
}