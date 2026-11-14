import { useEffect, useRef, useState } from 'react'
import {
  deleteMasterCv,
  draftFromNotes,
  extractFileText,
  draftFromUploadedCv,
  fetchMaster,
  mergeDraft,
  type CvData,
  type MasterDraft,
  type MasterSummary,
} from '../api'
import {
  CvListSections,
  EMPTY_CV,
  HeaderSection,
  LIST_SECTIONS,
  SummarySection,
  cleanCv,
  validate,
  type ListKey,
  type SetCv,
} from './CvEditorPage'
import './MasterBuilder.css'

const MAX_CHARS = 12_000
const MAX_FILE_BYTES = 5 * 1024 * 1024
const FILE_TYPES = /\.(pdf|docx|txt|md)$/i

const PLACEHOLDER = `Project name | Tech stack

* What you built
* How you built it
* Results or numbers

GitHub: https://github.com/...`

type Review = { cv: CvData; flags: string[]; sections: ListKey[]; withHeader: boolean }

function summaryText(master: MasterSummary | null): string {
  if (!master) return ''
  if (!master.exists) return 'No master CV yet. Add your details here or open the CV editor.'
  const { projects = 0, experience = 0, certifications = 0 } = master.counts
  return `Your master CV has ${projects} projects, ${experience} experience entries and ${certifications} certifications.`
}

export function MasterBuilder({ hasCv }: { hasCv: boolean }) {
  const [master, setMaster] = useState<MasterSummary | null>(null)
  const [text, setText] = useState('')
  const [review, setReview] = useState<Review | null>(null)
  const [report, setReport] = useState<string[]>([])
  const [busy, setBusy] = useState<'draft' | 'import' | 'merge' | 'delete' | 'load' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  useEffect(() => {
    fetchMaster()
      .then(setMaster)
      .catch(() => setMaster(null))
  }, [])

  async function run<T>(
    kind: 'draft' | 'import' | 'merge' | 'delete' | 'load',
    action: () => Promise<T>,
  ): Promise<T | null> {
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
    if (!FILE_TYPES.test(file.name)) {
      setError('Please choose a PDF, Word (.docx), .txt or .md file.')
      return
    }
    if (file.size > MAX_FILE_BYTES) {
      setError('The file is too large. Keep it under 5 MB.')
      return
    }
    const loaded = await run('load', () => extractFileText(file))
    if (loaded !== null) setText(loaded.slice(0, MAX_CHARS))
  }

  function startReview({ draft, flags }: MasterDraft) {
    const cv: CvData = { ...EMPTY_CV, ...draft, header: draft.header ?? EMPTY_CV.header }
    const sections = LIST_SECTIONS.filter((key) => cv[key].length > 0)
    const withHeader = !master?.exists
    if (sections.length === 0 && !withHeader) {
      setError('Nothing new was found in the text to add.')
      return
    }
    setReview({ cv, flags, sections, withHeader })
  }

  async function createDraft(fromCv: boolean) {
    setReport([])
    const result = await run(fromCv ? 'import' : 'draft', () =>
      fromCv ? draftFromUploadedCv() : draftFromNotes(text),
    )
    if (result) startReview(result)
  }

  async function addToCv() {
    if (!review) return
    const clean = cleanCv(review.cv)
    const result = await run('merge', () => mergeDraft({ ...clean, header: review.withHeader ? clean.header : null }))
    if (!result) return
    setReport(result.report)
    setReview(null)
    setText('')
    fetchMaster().then(setMaster).catch(() => undefined)
  }

  async function removeMaster() {
    if (!window.confirm('Delete your master CV from this computer? Your uploaded CV and tailored CVs are kept.')) {
      return
    }
    setReport([])
    await run('delete', async () => {
      await deleteMasterCv()
      return true
    })
    fetchMaster().then(setMaster).catch(() => undefined)
  }

  const setDraft: SetCv = (key, value) => setReview((r) => (r ? { ...r, cv: { ...r.cv, [key]: value } } : r))
  const errors = review ? validate(review.cv, review.withHeader) : []

  return (
    <section className="profile-card mb-card">
      <h2 className="card-heading-title">Add to my CV</h2>
      <p className="card-help">
        Write a new project, job or certificate in plain text. It is turned into a CV entry you can check before saving.
      </p>
      {master && (
        <div className="mb-summary">
          <span>{summaryText(master)}</span>
          <div className="mb-summary-actions">
            {master.exists && (
              <button type="button" className="btn-danger" disabled={busy !== null} onClick={removeMaster}>
                {busy === 'delete' ? 'Deleting…' : 'Delete master CV'}
              </button>
            )}
            <button type="button" className="mb-edit" onClick={() => (window.location.hash = '/cv')}>
              Open CV editor
            </button>
          </div>
        </div>
      )}

      {!review ? (
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
              accept=".pdf,.docx,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown"
              hidden
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) onFile(file)
                e.target.value = ''
              }}
            />
            <button
              type="button"
              className="btn-secondary"
              disabled={busy !== null}
              onClick={() => fileInput.current?.click()}
            >
              {busy === 'load' ? 'Reading file…' : 'Load PDF, Word or text file'}
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
          {review.flags.length > 0 && (
            <div className="mb-flags">
              <p>Removed because they were not in your text</p>
              <ul>
                {review.flags.map((flag, i) => (
                  <li key={i}>{flag}</li>
                ))}
              </ul>
            </div>
          )}
          <div className="mb-form">
            {review.withHeader && <HeaderSection cv={review.cv} set={setDraft} />}
            {review.withHeader && <SummarySection cv={review.cv} set={setDraft} />}
            <CvListSections cv={review.cv} set={setDraft} sections={review.sections} openFirst />
          </div>
          {errors.length > 0 && (
            <div className="mb-flags">
              <p>Fix before adding</p>
              <ul>
                {errors.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </div>
          )}
          <div className="mb-actions">
            <button type="button" className="btn-primary" disabled={busy !== null || errors.length > 0} onClick={addToCv}>
              {busy === 'merge' ? 'Adding…' : 'Add to my CV'}
            </button>
            <button type="button" className="btn-secondary" disabled={busy !== null} onClick={() => setReview(null)}>
              Discard
            </button>
          </div>
        </>
      )}

      {busy && !['merge', 'load', 'delete'].includes(busy) && <p className="mb-hint">This takes up to half a minute.</p>}
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