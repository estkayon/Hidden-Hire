import { useEffect, useState } from 'react'
import { cvDownloadUrl, fetchCvStatus, generateCv, type CvStatus } from '../api'
import { timeAgo } from '../format'
import { Modal } from './Modal'
import './ApplicationKit.css'

export function ApplicationKit({ jobId }: { jobId: string }) {
  const [status, setStatus] = useState<CvStatus | null>(null)
  const [busy, setBusy] = useState(false)
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

  async function generate() {
    setBusy(true)
    setError(null)
    try {
      setStatus(await generateCv(jobId))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

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
            <a className="kit-link" href={cvDownloadUrl(jobId, 'tex')} download>
              LaTeX source
            </a>
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
          <button type="button" className="kit-btn" disabled={busy || status === null} onClick={generate}>
            {busy ? 'Writing your CV…' : 'Generate CV'}
          </button>
          {busy && <p className="kit-hint">This takes about half a minute.</p>}
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