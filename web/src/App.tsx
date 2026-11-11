import { useCallback, useEffect, useRef, useState } from 'react'
import {
  EMPTY_FILTERS,
  PAGE_SIZE,
  fetchFacets,
  fetchJobs,
  fetchProfile,
  setSaved,
  toParams,
  type Facets,
  type Filters,
  type Job,
} from './api'
import { FilterBar } from './components/FilterBar'
import { Footer } from './components/Footer'
import { HealthPage } from './components/HealthPage'
import { JobCard } from './components/JobCard'
import { JobPage } from './components/JobPage'
import { Logo } from './components/Logo'
import { Pagination } from './components/Pagination'
import { PasteJobModal } from './components/PasteJobModal'
import { ProfilePage } from './components/ProfilePage'
import { useDebouncedValue } from './hooks'
import './App.css'

type Route =
  | { view: 'list' }
  | { view: 'job'; jobId: string }
  | { view: 'sources' }
  | { view: 'profile' }

function routeFromHash(): Route {
  const hash = window.location.hash
  const job = hash.match(/^#\/job\/(.+)$/)
  if (job) return { view: 'job', jobId: decodeURIComponent(job[1]) }
  if (hash === '#/sources') return { view: 'sources' }
  if (hash === '#/profile') return { view: 'profile' }
  return { view: 'list' }
}

export default function App() {
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS)
  const [facets, setFacets] = useState<Facets | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [route, setRoute] = useState<Route>(routeFromHash)
  const [pasteOpen, setPasteOpen] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)
  const [hasCv, setHasCv] = useState<boolean | null>(null)
  const listScroll = useRef(0)
  const contentRef = useRef<HTMLElement>(null)

  const debouncedQuery = useDebouncedValue(filters.q, 300)
  const searchKey = toParams({ ...filters, q: debouncedQuery }).toString()
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const onList = route.view === 'list'

  useEffect(() => {
    fetchFacets().then(setFacets).catch(() => setFacets(null))
  }, [reloadKey])

  useEffect(() => {
    fetchProfile()
      .then((state) => setHasCv(state.has_cv))
      .catch(() => setHasCv(null))
  }, [])

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
    const onHashChange = () => setRoute(routeFromHash())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  useEffect(() => {
    if (onList) {
      requestAnimationFrame(() => window.scrollTo({ top: listScroll.current }))
    }
  }, [onList])

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

  function navigate(hash: string) {
    if (onList) listScroll.current = window.scrollY
    window.location.hash = hash
  }

  const openJob = (jobId: string) => navigate(`/job/${encodeURIComponent(jobId)}`)
  const backToList = () => navigate('')
  const closePaste = useCallback(() => setPasteOpen(false), [])

  return (
    <>
      <nav className="navbar">
        <div className="navbar-inner">
          <button type="button" className="brand" onClick={backToList}>
            <Logo size={34} />
            <span>Hidden Hire</span>
          </button>
          {onList ? (
            <FilterBar filters={filters} facets={facets} onChange={updateFilters} />
          ) : (
            <div className="nav-spacer" />
          )}
          {/* <button
            type="button"
            className={`nav-link${route.view === 'profile' ? ' active' : ''}`}
            onClick={() => navigate('/profile')}
          >
            Profile
          </button> */}
          <button
            type="button"
            className={`nav-link${route.view === 'sources' ? ' active' : ''}`}
            onClick={() => navigate('/sources')}
          >
            Sources
          </button>
          <button type="button" className="nav-action" onClick={() => setPasteOpen(true)}>
            + Paste job
          </button>
          <button
            type="button"
            className={`nav-avatar${route.view === 'profile' ? ' active' : ''}`}
            aria-label="Profile"
            title="Profile"
            onClick={() => navigate('/profile')}
          >
            <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
              <circle cx="12" cy="8.5" r="3.6" />
              <path d="M4.8 19.5c1.3-3.3 4-5 7.2-5s5.9 1.7 7.2 5" />
            </svg>
            {hasCv === false && <span className="avatar-dot" aria-hidden="true" />}
          </button>
        </div>
      </nav>

      {!onList && (
        <div className="subnav">
          <button type="button" className="back-btn" onClick={backToList}>
            <span aria-hidden="true">←</span>
            All jobs
          </button>
        </div>
      )}

      {route.view === 'job' && <JobPage jobId={route.jobId} onToggleSave={toggleSave} />}
      {route.view === 'sources' && <HealthPage />}
      {route.view === 'profile' && <ProfilePage onStateChange={(state) => setHasCv(state.has_cv)} />}

      {onList && (
        <div className="list-tools">
          <button
            type="button"
            className="clear-btn"
            onClick={() => updateFilters(EMPTY_FILTERS)}
            disabled={!Object.values(filters).some(Boolean)}
          >
            Clear filters
          </button>
        </div>
      )}

      <div className="shell" hidden={!onList}>
        {hasCv === false && (
          <section className="unlock-banner">
            <div>
              <p className="unlock-title">Upload your CV to unlock match scores</p>
              <p className="unlock-sub">See how well each job fits you, and get tailored CVs and emails. Your CV stays on this computer.</p>
            </div>
            <button type="button" className="btn-apply" onClick={() => navigate('/profile')}>
              Upload CV
            </button>
          </section>
        )}

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