import { useCallback, useEffect, useRef, useState } from 'react'
import {
  EMPTY_FILTERS,
  PAGE_SIZE,
  fetchFacets,
  fetchJobs,
  setSaved,
  toParams,
  type Facets,
  type Filters,
  type Job,
} from './api'
import { FilterBar } from './components/FilterBar'
import { Footer } from './components/Footer'
import { JobCard } from './components/JobCard'
import { JobPage } from './components/JobPage'
import { Logo } from './components/Logo'
import { Pagination } from './components/Pagination'
import { PasteJobModal } from './components/PasteJobModal'
import { useDebouncedValue } from './hooks'
import './App.css'

function jobIdFromHash(): string | null {
  const match = window.location.hash.match(/^#\/job\/(.+)$/)
  return match ? decodeURIComponent(match[1]) : null
}

export default function App() {
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS)
  const [facets, setFacets] = useState<Facets | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [openJobId, setOpenJobId] = useState<string | null>(jobIdFromHash)
  const [pasteOpen, setPasteOpen] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)
  const listScroll = useRef(0)
  const contentRef = useRef<HTMLElement>(null)

  const debouncedQuery = useDebouncedValue(filters.q, 300)
  const searchKey = toParams({ ...filters, q: debouncedQuery }).toString()
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE))

  useEffect(() => {
    fetchFacets().then(setFacets).catch(() => setFacets(null))
  }, [reloadKey])

  useEffect(() => {
    const controller = new AbortController()
    const params = new URLSearchParams(searchKey)
    params.set('offset', String((page - 1) * PAGE_SIZE))
    setLoading(true)
    setError(null)
    fetchJobs(params, controller.signal)
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
  }, [searchKey, page, reloadKey])

  useEffect(() => {
    const onHashChange = () => setOpenJobId(jobIdFromHash())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  useEffect(() => {
    if (openJobId === null) {
      requestAnimationFrame(() => window.scrollTo({ top: listScroll.current }))
    }
  }, [openJobId])

  function updateFilters(patch: Partial<Filters>) {
    setFilters((prev) => ({ ...prev, ...patch }))
    setPage(1)
  }

  function changePage(next: number) {
    setPage(next)
    contentRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
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

  function openJob(jobId: string) {
    if (openJobId === null) listScroll.current = window.scrollY
    window.location.hash = `/job/${encodeURIComponent(jobId)}`
  }

  function backToList() {
    window.location.hash = ''
  }

  const closePaste = useCallback(() => setPasteOpen(false), [])

  return (
    <>
      <nav className="navbar">
        <div className="navbar-inner">
          <button type="button" className="brand" onClick={backToList}>
            <Logo size={34} />
            <span>Hidden Hire</span>
          </button>
          {openJobId === null ? (
            <FilterBar
              filters={filters}
              facets={facets}
              onChange={updateFilters}
              onReset={() => updateFilters(EMPTY_FILTERS)}
            />
          ) : (
            <>
              <button type="button" className="nav-back" onClick={backToList}>
                ← All jobs
              </button>
              <div className="nav-spacer" />
            </>
          )}
          <button type="button" className="nav-action" onClick={() => setPasteOpen(true)}>
            + Paste job
          </button>
        </div>
      </nav>

      {openJobId !== null && <JobPage jobId={openJobId} onToggleSave={toggleSave} />}

      <div className="shell" hidden={openJobId !== null}>
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
              onChange={(e) => updateFilters({ q: e.target.value })}
            />
          </label>
          <p className="count">
            {loading
              ? 'Loading jobs…'
              : `${total.toLocaleString()} jobs · page ${page} of ${pageCount}`}
          </p>
        </section>

        <main className="content" ref={contentRef}>
          {error && <p className="notice">Something went wrong ({error}). Is the API running?</p>}

          {!error && !loading && jobs.length === 0 && (
            <p className="notice">No jobs match these filters.</p>
          )}

          <section className="grid" aria-busy={loading}>
            {loading
              ? Array.from({ length: 6 }, (_, i) => <div key={i} className="card skeleton" />)
              : jobs.map((job, i) => (
                  <JobCard
                    key={job.id}
                    job={job}
                    index={i}
                    onOpen={openJob}
                    onToggleSave={toggleSave}
                  />
                ))}
          </section>

          {!loading && <Pagination page={page} pageCount={pageCount} onChange={changePage} />}
        </main>
      </div>

      <Footer />

      {pasteOpen && (
        <PasteJobModal
          onClose={closePaste}
          onSaved={(job) => {
            setPasteOpen(false)
            setReloadKey((k) => k + 1)
            openJob(job.id)
          }}
        />
      )}
    </>
  )
}