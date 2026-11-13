import { useEffect, useRef, useState } from 'react'
import {
  draftFromNotes,
  draftFromUploadedCv,
  fetchMaster,
  mergeDraft,
  type MasterDraft,
  type MasterSummary,
} from '../api'
import './MasterBuilder.css'

const MAX_CHARS = 12_000
const MAX_FILE_BYTES = 100_000

const PLACEHOLDER = `Project name | Tech stack

* What you built
* How you built it
* Results or numbers

GitHub: https://github.com/...`

function summaryText(master: MasterSummary | null): string {
  if (!master) return ''
  if (!master.exists) return 'No master CV yet. Add your details here or open the CV editor.'
  const { projects = 0, experience = 0, certifications = 0 } = master.counts
  return `Your master CV has ${projects} projects, ${experience} experience entries and ${certifications} certifications.`
}

export function MasterBuilder({ hasCv }: { hasCv: boolean }) {
  const [master, setMaster] = useState<MasterSummary | null>(null)
  const [text, setText] = useState('')
  const [draft, setDraft] = useState<MasterDraft | null>(null)
  const [report, setReport] = useState<string[]>([])
  const [busy, setBusy] = useState<'draft' | 'import' | 'merge' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  useEffect(() => {
    fetchMaster()
      .then(setMaster)
      .catch(() => setMaster(null))
  }, [])

  async function run<T>(kind: 'draft' | 'import' | 'merge', action: () => Promise<T>): Promise<T | null> {
    setBusy(kind)
    setError(null)
    try {
      return await action()
    } catch (err) {
      setError((err as Error).message)
      return null
    } finally {
      setBusy(null)
    }
  }

  async function onFile(file: File) {
    if (!/\.(txt|md)$/i.test(file.name)) {
      setError('Please choose a .txt or .md file.')
      return
    }
    if (file.size > MAX_FILE_BYTES) {
      setError('The file is too large. Keep it under 100 KB.')
      return
    }
    setText((await file.text()).slice(0, MAX_CHARS))
    setError(null)
  }

  async function createDraft(fromCv: boolean) {
    setReport([])
    const result = await run(fromCv ? 'import' : 'draft', () =>
      fromCv ? draftFromUploadedCv() : draftFromNotes(text),
    )
    if (result) setDraft(result)
  }

  async function addToCv() {
    if (!draft) return
    const result = await run('merge', () => mergeDraft(draft.yaml))
    if (!result) return
    setReport(result.report)
    setDraft(null)
    setText('')
    fetchMaster().then(setMaster).catch(() => undefined)
  }

  return (
    <section className="profile-card mb-card">
      <h2 className="card-heading-title">Add to my CV</h2>
      <p className="card-help">
        Write a new project, job or certificate in plain text. It is turned into a CV entry you can check before saving.
      </p>
      {master && (
        <div className="mb-summary">
          <span>{summaryText(master)}</span>
          <button type="button" className="mb-edit" onClick={() => (window.location.hash = '/cv')}>
            Open CV editor
          </button>
        </div>
      )}

      {!draft ? (
        <>
          <textarea
            className="mb-input"
            value={text}
            maxLength={MAX_CHARS}
            placeholder={PLACEHOLDER}
            onChange={(e) => setText(e.target.value)}
          />
          <div className="mb-row">
            <span className="mb-count">
              {text.length.toLocaleString()} / {MAX_CHARS.toLocaleString()}
            </span>
            <input
              ref={fileInput}
              type="file"
              accept=".txt,.md,text/plain,text/markdown"
              hidden
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) onFile(file)
                e.target.value = ''
              }}
            />
            <button type="button" className="btn-secondary" onClick={() => fileInput.current?.click()}>
              Load .txt or .md
            </button>
          </div>
          <div className="mb-actions">
            <button
              type="button"
              className="btn-primary"
              disabled={busy !== null || text.trim().length < 20}
              onClick={() => createDraft(false)}
            >
              {busy === 'draft' ? 'Creating draft…' : 'Create draft'}
            </button>
            {hasCv && (
              <button type="button" className="btn-secondary" disabled={busy !== null} onClick={() => createDraft(true)}>
                {busy === 'import' ? 'Reading your CV…' : 'Import from uploaded CV'}
              </button>
            )}
          </div>
        </>
      ) : (
        <>
          <p className="mb-label">Check and edit the draft, then add it.</p>
          {draft.flags.length > 0 && (
            <div className="mb-flags">
              <p>Removed because they were not in your text</p>
              <ul>
                {draft.flags.map((flag, i) => (
                  <li key={i}>{flag}</li>
                ))}
              </ul>
            </div>
          )}
          <textarea
            className="mb-input mb-yaml"
            value={draft.yaml}
            spellCheck={false}
            onChange={(e) => setDraft({ ...draft, yaml: e.target.value })}
          />
          <div className="mb-actions">
            <button type="button" className="btn-primary" disabled={busy !== null} onClick={addToCv}>
              {busy === 'merge' ? 'Adding…' : 'Add to my CV'}
            </button>
            <button type="button" className="btn-secondary" disabled={busy !== null} onClick={() => setDraft(null)}>
              Discard
            </button>
          </div>
        </>
      )}

      {busy && busy !== 'merge' && <p className="mb-hint">This takes up to half a minute.</p>}
      {error && <p className="mb-error">{error}</p>}
      {report.length > 0 && (
        <div className="mb-report">
          <p>Saved to your master CV</p>
          <ul>
            {report.map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}