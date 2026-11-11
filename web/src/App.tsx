import { useEffect, useState } from 'react'
import {
  EMPTY_FILTERS,
  fetchFacets,
  fetchJobs,
  setSaved,
  toParams,
  type Facets,
  type Filters,
  type Job,
} from './api'
import { FilterBar } from './components/FilterBar'
import { JobCard } from './components/JobCard'
import { useDebouncedValue } from './hooks'
import './App.css'

export default function App() {
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS)
  const [facets, setFacets] = useState<Facets | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const debouncedQuery = useDebouncedValue(filters.q, 300)
  const searchKey = toParams({ ...filters, q: debouncedQuery }).toString()

  useEffect(() => {
    fetchFacets().then(setFacets).catch(() => setFacets(null))
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    fetchJobs(new URLSearchParams(searchKey), controller.signal)
      .then((data) => {
        setJobs(data.jobs)
        setTotal(data.total)
      })
      .catch((err: Error) => {
        if (err.name !== 'AbortError') setError(err.message)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [searchKey])

  async function loadMore() {
    setLoadingMore(true)
    try {
      const params = new URLSearchParams(searchKey)
      params.set('offset', String(jobs.length))
      const data = await fetchJobs(params)
      setJobs((prev) => [...prev, ...data.jobs])
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoadingMore(false)
    }
  }

  async function toggleSave(job: Job) {
    const next = !job.saved
    const removeFromList = filters.savedOnly && !next
    setJobs((prev) =>
      removeFromList
        ? prev.filter((j) => j.id !== job.id)
        : prev.map((j) => (j.id === job.id ? { ...j, saved: next } : j)),
    )
    if (removeFromList) setTotal((t) => t - 1)
    try {
      await setSaved(job.id, next)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <>
      <nav className="navbar">
        <div className="navbar-inner">
          <div className="brand">
            <span className="brand-mark" aria-hidden="true" />
            <span>Hidden Hire</span>
          </div>
          <FilterBar
            filters={filters}
            facets={facets}
            onChange={(patch) => setFilters((prev) => ({ ...prev, ...patch }))}
            onReset={() => setFilters(EMPTY_FILTERS)}
          />
        </div>
      </nav>

      <div className="shell">

      <section className="hero">
        <label className="hero-search">
          <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
            <circle cx="11" cy="11" r="7" />
            <path d="m20 20-3.5-3.5" />
          </svg>
          <input
            type="search"
            placeholder="Search jobs by title, company or skill"
            aria-label="Search jobs"
            value={filters.q}
            maxLength={100}
            onChange={(e) => setFilters((prev) => ({ ...prev, q: e.target.value }))}
          />
        </label>
        <p className="count">{loading ? 'Loading jobs…' : `${total.toLocaleString()} jobs`}</p>
      </section>

      <main className="content">
        {error && <p className="notice">Could not load jobs ({error}). Is the API running?</p>}

        {!error && !loading && jobs.length === 0 && (
          <p className="notice">No jobs match these filters.</p>
        )}

        <section className="grid" aria-busy={loading}>
          {loading
            ? Array.from({ length: 9 }, (_, i) => <div key={i} className="card skeleton" />)
            : jobs.map((job, i) => (
                <JobCard key={job.id} job={job} index={i} onToggleSave={toggleSave} />
              ))}
        </section>

        {!loading && jobs.length < total && (
          <div className="more">
            <button type="button" onClick={loadMore} disabled={loadingMore}>
              {loadingMore ? 'Loading…' : `Load more (${total - jobs.length} left)`}
            </button>
          </div>
        )}
      </main>
      </div>
    </>
  )
}