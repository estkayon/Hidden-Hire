import type { ScoreBreakdown } from '../api'
import { matchLevel } from './MatchPill'

const PARTS: { key: keyof ScoreBreakdown; label: string }[] = [
  { key: 'skills', label: 'Skills' },
  { key: 'semantic', label: 'Profile fit' },
  { key: 'role', label: 'Role' },
  { key: 'seniority', label: 'Level' },
  { key: 'location', label: 'Location' },
]

export function MatchCard({ match, breakdown }: { match: number; breakdown: ScoreBreakdown | null }) {
  const level = matchLevel(match)

  return (
    <div className="side-card match-card">
      <p className="eyebrow">Why this match</p>
      <div className="match-head">
        <div className={`match-ring is-${level}`} style={{ '--value': match } as React.CSSProperties}>
          <span>{match}%</span>
        </div>
        <p className="match-note">Estimate from your CV and profile. It is not a hiring probability.</p>
      </div>

      {breakdown && (
        <>
          <ul className="match-bars">
            {PARTS.map(({ key, label }) => {
              const value = Math.round((breakdown[key] as number) * 100)
              return (
                <li key={key}>
                  <span>{label}</span>
                  <div className="bar">
                    <div style={{ width: `${value}%` }} />
                  </div>
                  <span className="bar-value">{value}</span>
                </li>
              )
            })}
          </ul>

          {breakdown.matched_skills.length > 0 && (
            <div className="match-skills">
              <p>You have</p>
              <div className="chips">
                {breakdown.matched_skills.map((s) => (
                  <span key={s} className="chip chip-meadow">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
          {breakdown.missing_skills.length > 0 && (
            <div className="match-skills">
              <p>Mentioned, not in your profile</p>
              <div className="chips">
                {breakdown.missing_skills.map((s) => (
                  <span key={s} className="chip chip-plain">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}