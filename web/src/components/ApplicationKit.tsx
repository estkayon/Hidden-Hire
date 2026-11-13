import { useEffect, useState } from 'react'
import { cvDownloadUrl, deleteTailoredCv, fetchCvStatus, fetchMaster, generateCv, type CvStatus } from '../api'
import { timeAgo } from '../format'
import { Modal } from './Modal'
import './ApplicationKit.css'

type ProjectRange = { min: number; max: number }

export function ApplicationKit({ jobId }: { jobId: string }) {
  const [status, setStatus] = useState<CvStatus | null>(null)
  const [range, setRange] = useState<ProjectRange | null>(null)
  const [projects, setProjects] = useState(5)
  const [busy, setBusy] = useState<'generate' | 'delete' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [previewOpen, setPreviewOpen] = useState(false)

  useEffect(() => {
    setStatus(null)
    setError(null)
    setPreviewOpen(false)
    fetchCvStatus(jobId)
      .then(setStatus)
      .catch((err: Error) => setError(err.message))
  }, [jobId])

  useEffect(() => {
    fetchMaster()
      .then(({ exists, counts }) => {
        if (!exists) return
        const min = counts.pinned ?? 0
        const max = counts.projects ?? 0
        setRange({ min, max })
        setProjects(Math.min(max, Math.max(min, 5)))
      })
      .catch(() => setRange(null))
  }, [])

  async function generate() {
    setBusy('generate')
    setError(null)
    try {
      setStatus(await generateCv(jobId, projects))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(null)
    }
  }

  async function remove() {
    if (!window.confirm('Delete the tailored CV for this job? You can generate a new one after.')) return
    setBusy('delete')
    setError(null)
    try {
      setStatus(await deleteTailoredCv(jobId))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(null)
    }
  }

  const options = range ? Array.from({ length: range.max - range.min + 1 }, (_, i) => range.min + i) : []

  return (
    <div className="side-card kit-card">
      <p className="eyebrow">Application kit</p>

      {status?.exists ? (
        <>
          <p className="kit-text">
            Tailored CV ready{status.generated_at ? `, made ${timeAgo(status.generated_at)}` : ''}.
          </p>
          {status.keywords.length > 0 && (
            <div className="kit-keywords">
              <p>Tailored for</p>
              <div className="chips">
                {status.keywords.map((keyword) => (
                  <span key={keyword} className="chip chip-plain">
                    {keyword}
                  </span>
                ))}
              </div>
            </div>
          )}
          <div className="kit-actions">
            <button type="button" className="kit-btn" onClick={() => setPreviewOpen(true)}>
              Preview CV
            </button>
            <a className="kit-ghost" href={cvDownloadUrl(jobId, 'pdf')} download>
              Download PDF
            </a>
            <div className="kit-row">
              <a className="kit-link" href={cvDownloadUrl(jobId, 'tex')} download>
                LaTeX source
              </a>
              <button type="button" className="kit-delete" disabled={busy !== null} onClick={remove}>
                {busy === 'delete' ? 'Deleting…' : 'Delete CV'}
              </button>
            </div>
          </div>
          {status.flags.length > 0 && (
            <details className="kit-flags">
              <summary>
                {status.flags.length} fact-check {status.flags.length === 1 ? 'note' : 'notes'}
              </summary>
              <ul>
                {status.flags.map((flag, i) => (
                  <li key={i}>{flag}</li>
                ))}
              </ul>
            </details>
          )}
        </>
      ) : (
        <>
          <p className="kit-text">A CV tailored to this job, using only facts from your master CV.</p>
          {options.length > 1 && (
            <label className="kit-select">
              Projects in CV
              <select value={projects} disabled={busy !== null} onChange={(e) => setProjects(Number(e.target.value))}>
                {options.map((n) => (
                  <option key={n} value={n}>
                    {n}
                    {n === range?.min && range.min > 0 ? ' (pinned only)' : ''}
                  </option>
                ))}
              </select>
            </label>
          )}
          <button type="button" className="kit-btn" disabled={busy !== null || status === null} onClick={generate}>
            {busy === 'generate' ? 'Writing your CV…' : 'Generate CV'}
          </button>
          {busy === 'generate' && <p className="kit-hint">This takes about half a minute.</p>}
        </>
      )}

      {error && <p className="kit-error">{error}</p>}

      {previewOpen && (
        <Modal label="CV preview" className="is-document" onClose={() => setPreviewOpen(false)}>
          <iframe className="kit-preview" src={cvDownloadUrl(jobId, 'pdf', true)} title="Tailored CV preview" />
        </Modal>
      )}
    </div>
  )
}