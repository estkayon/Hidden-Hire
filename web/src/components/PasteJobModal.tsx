import { useEffect, useState, type FormEvent } from 'react'
import { pasteJob, type JobDetail, type PasteInput } from '../api'

type Props = {
  onClose: () => void
  onSaved: (job: JobDetail) => void
}

const EMPTY: PasteInput = { title: '', company: '', location: '', url: '', text: '' }

export function PasteJobModal({ onClose, onSaved }: Props) {
  const [form, setForm] = useState<PasteInput>(EMPTY)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  function update(field: keyof PasteInput, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      onSaved(await pasteJob(form))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <div className="overlay" onClick={onClose} />
      <form className="modal" onSubmit={submit} aria-label="Paste a job">
        <header className="modal-head">
          <h2>Paste a job</h2>
          <p className="muted">From a Facebook post, email or message. It is saved like any other job.</p>
        </header>

        <div className="form-row">
          <label>
            Job title
            <input required maxLength={200} value={form.title} onChange={(e) => update('title', e.target.value)} />
          </label>
          <label>
            Company
            <input required maxLength={200} value={form.company} onChange={(e) => update('company', e.target.value)} />
          </label>
        </div>

        <div className="form-row">
          <label>
            Location
            <input maxLength={200} placeholder="e.g. Remote, Dhaka" value={form.location} onChange={(e) => update('location', e.target.value)} />
          </label>
          <label>
            Apply link
            <input type="url" maxLength={2000} placeholder="https://" value={form.url} onChange={(e) => update('url', e.target.value)} />
          </label>
        </div>

        <label>
          Job text
          <textarea
            required
            minLength={20}
            maxLength={20000}
            rows={10}
            placeholder="Paste the full job post here"
            value={form.text}
            onChange={(e) => update('text', e.target.value)}
          />
        </label>

        {error && <p className="form-error">{error}</p>}

        <footer className="modal-foot">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? 'Saving…' : 'Save job'}
          </button>
        </footer>
      </form>
    </>
  )
}