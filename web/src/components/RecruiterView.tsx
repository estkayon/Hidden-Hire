import { useCallback, useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import type { RecruiterView as View } from '../api'
import { MatchRing, band } from './MatchRing'
import './RecruiterView.css'

type DimensionKey = 'skills' | 'experience' | 'eligibility' | 'domain' | 'education'

const DIMENSIONS: { key: DimensionKey; label: string; weight: string }[] = [
  { key: 'skills', label: 'Skills and tools', weight: '35%' },
  { key: 'experience', label: 'Experience and level', weight: '25%' },
  { key: 'eligibility', label: 'Eligibility', weight: '20%' },
  { key: 'domain', label: 'Domain and projects', weight: '15%' },
  { key: 'education', label: 'Education', weight: '5%' },
]

const CLOSE_MS = 220

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

function Details({ view }: { view: View }) {
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
  const [closing, setClosing] = useState(false)

  const close = useCallback(() => {
    setClosing(true)
    window.setTimeout(onClose, CLOSE_MS)
  }, [onClose])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close()
    }
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', onKey)
    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', onKey)
    }
  }, [close])

  return createPortal(
    <div className={`rv-overlay${closing ? ' is-closing' : ''}`} onClick={close}>
      <div
        className="rv-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Recruiter view"
        onClick={(e) => e.stopPropagation()}
      >
        <button type="button" className="rv-close" aria-label="Close" onClick={close}>
          ×
        </button>
        <Details view={view} />
      </div>
    </div>,
    document.body,
  )
}

type CardProps = {
  view: View | null
  judging: boolean
  error: string | null
  onRequest: () => void
  onOpen: () => void
}

export function RecruiterCard({ view, judging, error, onRequest, onOpen }: CardProps) {
  return (
    <div className="side-card rv-card">
      <p className="eyebrow">Recruiter view</p>
      {view ? (
        <div className="rv-card-result">
          <MatchRing match={view.total} />
          <button type="button" className="rv-btn" onClick={onOpen}>
            View details
          </button>
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