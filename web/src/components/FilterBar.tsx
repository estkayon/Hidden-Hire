import type { Facets, Filters } from '../api'
import { countryName } from '../countries'

const WORK_TYPES = [
  { value: '', label: 'All' },
  { value: 'remote', label: 'Remote' },
  { value: 'hybrid', label: 'Hybrid' },
  { value: 'onsite', label: 'Onsite' },
]

const POSTED_WITHIN = [
  { value: '', label: 'Last 7 days' },
  { value: '24', label: 'Last 24 hours' },
  { value: '48', label: 'Last 48 hours' },
  { value: '240', label: 'Last 10 days' },
]

type Props = {
  filters: Filters
  facets: Facets | null
  onChange: (patch: Partial<Filters>) => void
  onReset: () => void
}

export function FilterBar({ filters, facets, onChange, onReset }: Props) {
  const isFiltered = Object.values(filters).some(Boolean)

  return (
    <div className="filter-bar">
      <div className="segmented" role="group" aria-label="Work type">
        {WORK_TYPES.map((option) => (
          <button
            key={option.value}
            type="button"
            className={filters.workType === option.value ? 'active' : ''}
            onClick={() => onChange({ workType: option.value })}
          >
            {option.label}
          </button>
        ))}
      </div>

      <select value={filters.country} onChange={(e) => onChange({ country: e.target.value })}>
        <option value="">All countries</option>
        {[...(facets?.countries ?? [])]
          .sort((a, b) => countryName(a.value).localeCompare(countryName(b.value)))
          .map((c) => (
          <option key={c.value} value={c.value}>
            {countryName(c.value)} ({c.count})
          </option>
        ))}
      </select>

      <select value={filters.postedWithin} onChange={(e) => onChange({ postedWithin: e.target.value })}>
        {POSTED_WITHIN.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>

      <select value={filters.source} onChange={(e) => onChange({ source: e.target.value })}>
        <option value="">All sources</option>
        {facets?.sources.map((s) => (
          <option key={s.value} value={s.value}>
            {s.value} ({s.count})
          </option>
        ))}
      </select>

      <button
        type="button"
        className={`saved-toggle${filters.savedOnly ? ' active' : ''}`}
        aria-pressed={filters.savedOnly}
        onClick={() => onChange({ savedOnly: !filters.savedOnly })}
      >
        Saved
      </button>

      <button type="button" className="reset" onClick={onReset} disabled={!isFiltered}>
        Clear
      </button>
    </div>
  )
}