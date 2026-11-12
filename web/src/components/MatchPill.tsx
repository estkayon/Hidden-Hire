export function matchLevel(match: number): 'high' | 'mid' | 'low' {
  if (match >= 75) return 'high'
  if (match >= 60) return 'mid'
  return 'low'
}

export function MatchPill({ match }: { match: number | null }) {
  if (match === null) return null
  return <span className={`match-pill is-${matchLevel(match)}`}>{match}% match</span>
}