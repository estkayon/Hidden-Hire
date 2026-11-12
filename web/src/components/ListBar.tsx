import type { Filters } from '../api'

const TABS: { value: Filters['relevance']; label: string }[] = [
  { value: '', label: 'All' },
  { value: 'relevant', label: 'Relevant' },
  { value: 'other', label: 'Others' },
]

type Props = {
  filters: Filters
  onChange: (patch: Partial<Filters>) => void
}

export function ListBar({ filters, onChange }: Props) {
  return (
    <div className="list-bar">
      <div className="tabs" role="tablist" aria-label="Relevance">
        {TABS.map((tab) => (
          <button
            key={tab.value}
            type="button"
            role="tab"
            aria-selected={filters.relevance === tab.value}
            className={filters.relevance === tab.value ? 'active' : ''}
            onClick={() => onChange({ relevance: tab.value })}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="list-controls">
        <label>
          Min match
          <select value={filters.minMatch} onChange={(e) => onChange({ minMatch: e.target.value })}>
            <option value="">Any</option>
            <option value="50">50%+</option>
            <option value="70">70%+</option>
            <option value="80">80%+</option>
          </select>
        </label>
        <label>
          Sort
          <select
            value={filters.sort}
            onChange={(e) => onChange({ sort: e.target.value as Filters['sort'] })}
          >
            <option value="">Newest</option>
            <option value="match">Best match</option>
          </select>
        </label>
      </div>
    </div>
  )
}