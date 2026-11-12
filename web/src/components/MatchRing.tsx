import { useId } from 'react'

const RADIUS = 44
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

function band(match: number): 'great' | 'good' | 'fair' | 'weak' {
  if (match >= 85) return 'great'
  if (match >= 70) return 'good'
  if (match >= 55) return 'fair'
  return 'weak'
}

export function MatchRing({ match }: { match: number }) {
  const gradientId = useId()

  return (
    <div className={`match-ring is-${band(match)}`} role="img" aria-label={`${match}% match`}>
      <svg viewBox="0 0 104 104" aria-hidden="true">
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" className="ring-stop-a" />
            <stop offset="1" className="ring-stop-b" />
          </linearGradient>
        </defs>
        <circle cx="52" cy="52" r={RADIUS} className="ring-track" />
        <circle
          cx="52"
          cy="52"
          r={RADIUS}
          className="ring-value"
          stroke={`url(#${gradientId})`}
          strokeDasharray={`${(CIRCUMFERENCE * match) / 100} ${CIRCUMFERENCE}`}
        />
      </svg>
      <div className="ring-label">
        <strong>{match}%</strong>
        <span>Match</span>
      </div>
    </div>
  )
}