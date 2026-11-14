import { useEffect, useRef, useState, type DragEvent } from 'react'
import {
  deleteCv,
  fetchProfile,
  updateProfile,
  uploadCv,
  type PersonalInfo,
  type Profile,
  type ProfileState,
} from '../api'
import { ChipInput } from './ChipInput'
import { MasterBuilder } from './MasterBuilder'

type Draft = {
  personal: PersonalInfo
  skills: string[]
  target_roles: string[]
  years_experience: string
}

type Message = { kind: 'ok' | 'error'; text: string } | null

const PERSONAL_FIELDS: { key: keyof PersonalInfo; label: string; type: string; placeholder?: string }[] = [
  { key: 'full_name', label: 'Full name', type: 'text' },
  { key: 'email', label: 'Email', type: 'email' },
  { key: 'phone', label: 'Phone', type: 'tel' },
  { key: 'location', label: 'Location', type: 'text', placeholder: 'e.g. Dhaka, Bangladesh' },
  { key: 'github', label: 'GitHub', type: 'url', placeholder: 'https://github.com/…' },
  { key: 'linkedin', label: 'LinkedIn', type: 'url', placeholder: 'https://linkedin.com/in/…' },
  { key: 'portfolio', label: 'Portfolio', type: 'url', placeholder: 'https://…' },
]

function toDraft(profile: Profile): Draft {
  return {
    personal: { ...profile.personal },
    skills: [...profile.skills],
    target_roles: [...profile.target_roles],
    years_experience: profile.years_experience === null ? '' : String(profile.years_experience),
  }
}

function UploadZone({ busy, onFile, compact }: { busy: boolean; onFile: (file: File) => void; compact?: boolean }) {
  const input = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  function onDrop(e: DragEvent) {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) onFile(file)
  }

  return (
    <div
      className={`upload-zone${dragging ? ' is-dragging' : ''}${compact ? ' is-compact' : ''}`}
      onDragOver={(e) => {
        e.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
    >
      <input
        ref={input}
        type="file"
        accept="application/pdf,.pdf"
        hidden
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) onFile(file)
          e.target.value = ''
        }}
      />
      {!compact && (
        <div className="upload-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="28" height="28">
            <path d="M12 16V4m0 0-4 4m4-4 4 4M5 15v3a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-3" />
          </svg>
        </div>
      )}
      {!compact && <p className="upload-title">Drop your CV here</p>}
      {!compact && <p className="upload-sub">PDF only, up to 5 MB. It stays on this computer.</p>}
      <button type="button" className="btn-primary" disabled={busy} onClick={() => input.current?.click()}>
        {busy ? 'Reading your CV…' : compact ? 'Replace CV' : 'Choose PDF'}
      </button>
    </div>
  )
}

export function ProfilePage({ onStateChange }: { onStateChange: (state: ProfileState) => void }) {
  const [state, setState] = useState<ProfileState | null>(null)
  const [draft, setDraft] = useState<Draft | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<Message>(null)

  function apply(next: ProfileState) {
    setState(next)
    setDraft(next.profile ? toDraft(next.profile) : null)
    onStateChange(next)
  }

  useEffect(() => {
    window.scrollTo({ top: 0 })
    fetchProfile()
      .then(apply)
      .catch((err: Error) => setMessage({ kind: 'error', text: err.message }))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function run(action: () => Promise<ProfileState>, success: string) {
    setBusy(true)
    setMessage(null)
    try {
      apply(await action())
      setMessage({ kind: 'ok', text: success })
    } catch (err) {
      setMessage({ kind: 'error', text: (err as Error).message })
    } finally {
      setBusy(false)
    }
  }

  function onFile(file: File) {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setMessage({ kind: 'error', text: 'Please choose a PDF file.' })
      return
    }
    run(() => uploadCv(file), 'CV uploaded. Check the details below and save.')
  }

  function save() {
    if (!draft) return
    const years = draft.years_experience.trim()
    run(
      () =>
        updateProfile({
          personal: draft.personal,
          skills: draft.skills,
          target_roles: draft.target_roles,
          years_experience: years === '' ? null : Number(years),
        }),
      'Profile saved.',
    )
  }

  function remove() {
    if (window.confirm('Delete your uploaded CV and profile from this computer? Your master CV is kept.')) {
      run(deleteCv, 'Your CV and profile were deleted.')
    }
  }

  if (!state) {
    return (
      <div className="profile-page">
        {message ? <p className="notice">{message.text}</p> : <div className="job-loading" />}
      </div>
    )
  }

  const suggestions = draft
    ? state.detected_skills.filter((s) => !draft.skills.some((d) => d.toLowerCase() === s.toLowerCase()))
    : []

  return (
    <div className="profile-page">
      <header className="profile-hero">
        <p className="eyebrow">Your profile</p>
        <h1>{state.has_cv ? draft?.personal.full_name || 'Your profile' : 'Start with your CV'}</h1>
        <p className="profile-sub">
          Match scores, tailored CVs and emails use only what is in your CV and this profile.
        </p>
      </header>

      {message && <p className={`toast is-${message.kind}`}>{message.text}</p>}

      {!state.has_cv || !draft ? (
        <>
          <UploadZone busy={busy} onFile={onFile} />
          <MasterBuilder hasCv={false} />
        </>
      ) : (
        <>
          <section className="cv-row">
            <div className="cv-file">
              <span className="cv-badge">PDF</span>
              <div>
                <p className="cv-name">{state.profile?.cv_file}</p>
                {state.profile?.cv_uploaded_at && (
                  <p className="cv-date">Uploaded {new Date(state.profile.cv_uploaded_at).toLocaleString()}</p>
                )}
              </div>
            </div>
            <div className="cv-actions">
              <UploadZone busy={busy} onFile={onFile} compact />
              <button type="button" className="btn-danger" disabled={busy} onClick={remove}>
                Delete my data
              </button>
            </div>
          </section>

          <div className="profile-grid">
            <section className="profile-card">
              <h2 className="card-heading-title">Personal info</h2>
              <div className="field-grid">
                {PERSONAL_FIELDS.map(({ key, label, type, placeholder }) => (
                  <label key={key} className={key === 'full_name' || key === 'location' ? 'span-2' : ''}>
                    {label}
                    <input
                      type={type}
                      value={draft.personal[key]}
                      placeholder={placeholder}
                      maxLength={300}
                      onChange={(e) =>
                        setDraft({ ...draft, personal: { ...draft.personal, [key]: e.target.value } })
                      }
                    />
                  </label>
                ))}
              </div>

              <h3 className="card-subheading">Preferences</h3>
              <label className="field-label">
                Target roles
                <ChipInput
                  values={draft.target_roles}
                  onChange={(target_roles) => setDraft({ ...draft, target_roles })}
                  placeholder="e.g. MLOps Engineer"
                />
              </label>
              <label className="field-label">
                Years of experience
                <input
                  type="number"
                  min={0}
                  max={60}
                  step={0.5}
                  value={draft.years_experience}
                  onChange={(e) => setDraft({ ...draft, years_experience: e.target.value })}
                />
              </label>
            </section>

            <div className="profile-stack">
              <section className="profile-card">
                <h2 className="card-heading-title">Skills</h2>
                <p className="card-help">Keep only skills you can talk about in an interview.</p>
                <ChipInput
                  values={draft.skills}
                  onChange={(skills) => setDraft({ ...draft, skills })}
                  placeholder="Add a skill and press Enter"
                />
                {suggestions.length > 0 && (
                  <div className="suggestions">
                    <p className="card-help">Found in your CV</p>
                    <div className="chips">
                      {suggestions.map((skill) => (
                        <button
                          key={skill}
                          type="button"
                          className="chip chip-suggest"
                          onClick={() => setDraft({ ...draft, skills: [...draft.skills, skill] })}
                        >
                          + {skill}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </section>
            </div>
          </div>

          <MasterBuilder hasCv />

          <div className="save-bar">
            <p>Changes are saved only on this computer.</p>
            <button type="button" className="btn-primary" disabled={busy} onClick={save}>
              {busy ? 'Saving…' : 'Save profile'}
            </button>
          </div>
        </>
      )}
    </div>
  )
}