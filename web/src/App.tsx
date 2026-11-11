import { useEffect, useState } from 'react'
import { fetchJobs, type JobList } from './api'
import { JobCard } from './components/JobCard'
import './App.css'

export default function App() {
  const [data, setData] = useState<JobList | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchJobs()
      .then(setData)
      .catch((err: Error) => setError(err.message))
  }, [])

  return (
    <main className="page">
      <header className="page-head">
        <h1>Hidden Hire</h1>
        {data && (
          <p className="muted">
            Showing {data.jobs.length} of {data.total} jobs from the last 7 days
          </p>
        )}
      </header>

      {error && <p className="error">Could not load jobs ({error}). Is the API running?</p>}
      {!data && !error && <p className="muted">Loading…</p>}

      <section className="grid">
        {data?.jobs.map((job) => <JobCard key={job.id} job={job} />)}
      </section>
    </main>
  )
}