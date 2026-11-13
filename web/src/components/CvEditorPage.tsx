import { useEffect, useState, type ReactNode } from 'react'
import { fetchMasterCv, saveMasterCv, type CvData, type CvLink } from '../api'
import { ChipInput } from './ChipInput'
import './CvEditor.css'

type ListKey = Exclude<keyof CvData, 'header' | 'summary'>
type Item<K extends ListKey> = CvData[K][number]

const TRACKS = [
  { value: 'software', label: 'Software / backend' },
  { value: 'frontend', label: 'Frontend' },
  { value: 'ml', label: 'ML / AI / data' },
]

const EMPTY_CV: CvData = {
  header: { name: '', location: '', phone: '', email: '', links: [] },
  summary: '',
  skills: [],
  experience: [],
  projects: [],
  research: [],
  education: [],
  certifications: [],
  volunteering: [],
  references: [],
}

const NEW_ITEM: { [K in ListKey]: () => Item<K> } = {
  skills: () => ({ name: '', items: [] }),
  experience: () => ({ title: '', dates: '', organization: '', location: '', stack: [], bullets: [''] }),
  projects: () => ({ name: '', pinned: false, tracks: [], links: [], stack: [], bullets: [''] }),
  research: () => ({ title: '', links: [], subtitle: '', tools: '', bullets: [''] }),
  education: () => ({ degree: '', dates: '', institution: '', grade: '', location: '' }),
  certifications: () => ({ name: '', issuer: '', url: '' }),
  volunteering: () => ({ name: '', date: '', url: '', bullets: [] }),
  references: () => ({ name: '', lines: [], phone: '', email: '' }),
}

const isUrl = (value: string) => /^https?:\/\/\S+$/.test(value.trim())
const blank = (value: string) => !value.trim()

function move<T>(list: T[], index: number, step: number): T[] {
  const next = [...list]
  const [item] = next.splice(index, 1)
  next.splice(index + step, 0, item)
  return next
}

function cleanLinks(links: CvLink[]): CvLink[] {
  return links
    .filter((l) => l.url.trim())
    .map((l) => ({ label: l.label.trim() || 'Link', url: l.url.trim() }))
}

function cleanList(values: string[]): string[] {
  return values.map((v) => v.trim()).filter(Boolean)
}

/** Drop empty bullets, lines and links before saving. */
function cleanCv(cv: CvData): CvData {
  return {
    ...cv,
    header: { ...cv.header, links: cleanLinks(cv.header.links) },
    skills: cv.skills.map((g) => ({ ...g, items: cleanList(g.items) })),
    experience: cv.experience.map((e) => ({ ...e, stack: cleanList(e.stack), bullets: cleanList(e.bullets) })),
    projects: cv.projects.map((p) => ({
      ...p,
      links: cleanLinks(p.links),
      stack: cleanList(p.stack),
      bullets: cleanList(p.bullets),
    })),
    research: cv.research.map((r) => ({ ...r, links: cleanLinks(r.links), bullets: cleanList(r.bullets) })),
    volunteering: cv.volunteering.map((v) => ({ ...v, bullets: cleanList(v.bullets) })),
    references: cv.references.map((r) => ({ ...r, lines: cleanList(r.lines) })),
  }
}

function validate(cv: CvData): string[] {
  const errors: string[] = []
  const need = (ok: boolean, message: string) => {
    if (!ok) errors.push(message)
  }
  const linksOk = (links: CvLink[], where: string) =>
    links.forEach((l) => need(blank(l.url) || isUrl(l.url), `${where}: a link must start with https://`))

  need(!blank(cv.header.name), 'Header: add your name')
  linksOk(cv.header.links, 'Header')
  cv.skills.forEach((g, i) => {
    need(!blank(g.name), `Skill group ${i + 1}: add a name`)
    need(cleanList(g.items).length > 0, `Skill group ${g.name || i + 1}: add at least one skill`)
  })
  cv.experience.forEach((e, i) => {
    const where = e.title || `Experience ${i + 1}`
    need(!blank(e.title) && !blank(e.organization) && !blank(e.dates), `${where}: add title, organization and dates`)
    need(cleanList(e.bullets).length > 0, `${where}: add at least one bullet`)
  })
  cv.projects.forEach((p, i) => {
    const where = p.name || `Project ${i + 1}`
    need(!blank(p.name), `Project ${i + 1}: add a name`)
    need(cleanList(p.bullets).length > 0, `${where}: add at least one bullet`)
    linksOk(p.links, where)
  })
  cv.research.forEach((r, i) => {
    const where = r.title || `Research ${i + 1}`
    need(!blank(r.title), `Research ${i + 1}: add a title`)
    need(cleanList(r.bullets).length > 0, `${where}: add at least one bullet`)
    linksOk(r.links, where)
  })
  cv.education.forEach((e, i) =>
    need(!blank(e.degree) && !blank(e.institution) && !blank(e.dates), `Education ${i + 1}: add degree, institution and dates`),
  )
  cv.certifications.forEach((c, i) => {
    need(!blank(c.name), `Certification ${i + 1}: add a name`)
    need(blank(c.url) || isUrl(c.url), `${c.name || `Certification ${i + 1}`}: the link must start with https://`)
  })
  cv.volunteering.forEach((v, i) => {
    need(!blank(v.name), `Volunteering ${i + 1}: add a name`)
    need(blank(v.url) || isUrl(v.url), `${v.name || `Volunteering ${i + 1}`}: the link must start with https://`)
  })
  cv.references.forEach((r, i) => need(!blank(r.name), `Reference ${i + 1}: add a name`))
  return errors
}

type FieldProps = {
  label: string
  value: string
  onChange: (value: string) => void
  required?: boolean
  url?: boolean
  wide?: boolean
  placeholder?: string
}

function Field({ label, value, onChange, required, url, wide, placeholder }: FieldProps) {
  const invalid = (required && blank(value)) || (url && !blank(value) && !isUrl(value))
  return (
    <label className={`cv-field${wide ? ' is-wide' : ''}${invalid ? ' is-invalid' : ''}`}>
      <span>
        {label}
        {required && <em> *</em>}
      </span>
      <input value={value} placeholder={placeholder} maxLength={400} onChange={(e) => onChange(e.target.value)} />
    </label>
  )
}

function Bullets({ values, onChange }: { values: string[]; onChange: (values: string[]) => void }) {
  return (
    <div className="cv-block is-wide">
      <span className="cv-sub">Bullet points</span>
      {values.map((bullet, i) => (
        <div key={i} className="cv-bullet">
          <span className="cv-dot" aria-hidden="true">
            •
          </span>
          <textarea
            rows={2}
            value={bullet}
            maxLength={400}
            onChange={(e) => onChange(values.map((b, j) => (j === i ? e.target.value : b)))}
          />
          <div className="cv-mini">
            <button type="button" aria-label="Move up" disabled={i === 0} onClick={() => onChange(move(values, i, -1))}>
              ↑
            </button>
            <button
              type="button"
              aria-label="Move down"
              disabled={i === values.length - 1}
              onClick={() => onChange(move(values, i, 1))}
            >
              ↓
            </button>
            <button type="button" aria-label="Remove bullet" onClick={() => onChange(values.filter((_, j) => j !== i))}>
              ×
            </button>
          </div>
        </div>
      ))}
      <button type="button" className="cv-add-small" onClick={() => onChange([...values, ''])}>
        + Add bullet
      </button>
    </div>
  )
}

function Links({ values, onChange }: { values: CvLink[]; onChange: (values: CvLink[]) => void }) {
  const update = (i: number, patch: Partial<CvLink>) => onChange(values.map((l, j) => (j === i ? { ...l, ...patch } : l)))
  return (
    <div className="cv-block is-wide">
      <span className="cv-sub">Links</span>
      {values.map((link, i) => (
        <div key={i} className="cv-link">
          <input
            className="cv-link-label"
            value={link.label}
            placeholder="GitHub"
            maxLength={40}
            onChange={(e) => update(i, { label: e.target.value })}
          />
          <input
            className={!blank(link.url) && !isUrl(link.url) ? 'is-invalid' : ''}
            value={link.url}
            placeholder="https://"
            maxLength={400}
            onChange={(e) => update(i, { url: e.target.value })}
          />
          <button type="button" className="cv-x" aria-label="Remove link" onClick={() => onChange(values.filter((_, j) => j !== i))}>
            ×
          </button>
        </div>
      ))}
      <button type="button" className="cv-add-small" onClick={() => onChange([...values, { label: '', url: '' }])}>
        + Add link
      </button>
    </div>
  )
}

function Chips({ label, values, onChange, commaAdds }: { label: string; values: string[]; onChange: (v: string[]) => void; commaAdds?: boolean }) {
  return (
    <div className="cv-block is-wide">
      <span className="cv-sub">{label}</span>
      <ChipInput values={values} onChange={onChange} placeholder="Type and press Enter" commaAdds={commaAdds} />
    </div>
  )
}

type ListProps<K extends ListKey> = {
  title: string
  hint?: string
  addLabel: string
  items: Item<K>[]
  makeItem: () => Item<K>
  heading: (item: Item<K>, index: number) => string
  onChange: (items: Item<K>[]) => void
  render: (item: Item<K>, update: (patch: Partial<Item<K>>) => void) => ReactNode
}

function ItemList<K extends ListKey>({ title, hint, addLabel, items, makeItem, heading, onChange, render }: ListProps<K>) {
  const [open, setOpen] = useState<number | null>(null)
  const update = (i: number, patch: Partial<Item<K>>) =>
    onChange(items.map((item, j) => (j === i ? ({ ...item, ...patch } as Item<K>) : item)))

  return (
    <section className="profile-card cv-section">
      <header className="cv-section-head">
        <h2 className="card-heading-title">
          {title} <span className="cv-count">{items.length}</span>
        </h2>
        {hint && <p className="card-help">{hint}</p>}
      </header>
      {items.map((item, i) => (
        <div key={i} className={`cv-item${open === i ? ' is-open' : ''}`}>
          <div className="cv-item-head">
            <button type="button" className="cv-item-title" onClick={() => setOpen(open === i ? null : i)}>
              <span className="cv-caret" aria-hidden="true">
                ▸
              </span>
              {heading(item, i) || 'Untitled'}
            </button>
            <div className="cv-mini">
              <button type="button" aria-label="Move up" disabled={i === 0} onClick={() => { setOpen(null); onChange(move(items, i, -1)) }}>
                ↑
              </button>
              <button
                type="button"
                aria-label="Move down"
                disabled={i === items.length - 1}
                onClick={() => { setOpen(null); onChange(move(items, i, 1)) }}
              >
                ↓
              </button>
              <button
                type="button"
                aria-label="Delete"
                onClick={() => {
                  if (window.confirm(`Delete "${heading(item, i) || 'this item'}"?`)) {
                    setOpen(null)
                    onChange(items.filter((_, j) => j !== i))
                  }
                }}
              >
                ×
              </button>
            </div>
          </div>
          {open === i && <div className="cv-grid">{render(item, (patch) => update(i, patch))}</div>}
        </div>
      ))}
      <button
        type="button"
        className="cv-add"
        onClick={() => {
          onChange([...items, makeItem()])
          setOpen(items.length)
        }}
      >
        + {addLabel}
      </button>
    </section>
  )
}

export function CvEditorPage() {
  const [cv, setCv] = useState<CvData | null>(null)
  const [original, setOriginal] = useState('')
  const [loadError, setLoadError] = useState<string | null>(null)
  const [message, setMessage] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    window.scrollTo({ top: 0 })
    fetchMasterCv()
      .then((data) => {
        setCv(data)
        setOriginal(JSON.stringify(data))
      })
      .catch((err: Error) => {
        if (err.message === 'No master CV yet.') {
          setCv(EMPTY_CV)
          setOriginal(JSON.stringify(EMPTY_CV))
        } else {
          setLoadError(err.message)
        }
      })
  }, [])

  if (loadError) {
    return (
      <div className="cv-page">
        <p className="notice">Could not load your CV ({loadError}).</p>
      </div>
    )
  }
  if (!cv) {
    return (
      <div className="cv-page">
        <div className="job-loading" />
      </div>
    )
  }

  const set = <K extends keyof CvData>(key: K, value: CvData[K]) => setCv({ ...cv, [key]: value })
  const errors = validate(cv)
  const dirty = JSON.stringify(cv) !== original

  async function save() {
    if (!cv) return
    setSaving(true)
    setMessage(null)
    try {
      const saved = await saveMasterCv(cleanCv(cv))
      setCv(saved)
      setOriginal(JSON.stringify(saved))
      setMessage({ kind: 'ok', text: 'CV saved. The previous version is kept as a backup.' })
    } catch (err) {
      setMessage({ kind: 'error', text: (err as Error).message })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="cv-page">
      <header className="profile-hero">
        <button type="button" className="cv-back" onClick={() => (window.location.hash = '/profile')}>
          ← Back to profile
        </button>
        <p className="eyebrow">Master CV</p>
        <h1>{cv.header.name || 'Your CV'}</h1>
        <p className="profile-sub">Every tailored CV is built only from what you keep here.</p>
      </header>

      {message && <p className={`toast is-${message.kind}`}>{message.text}</p>}

      <section className="profile-card cv-section">
        <h2 className="card-heading-title">Header</h2>
        <div className="cv-grid">
          <Field label="Full name" required wide value={cv.header.name} onChange={(name) => set('header', { ...cv.header, name })} />
          <Field label="Location" value={cv.header.location} onChange={(location) => set('header', { ...cv.header, location })} />
          <Field label="Phone" value={cv.header.phone} onChange={(phone) => set('header', { ...cv.header, phone })} />
          <Field label="Email" wide value={cv.header.email} onChange={(email) => set('header', { ...cv.header, email })} />
          <Links values={cv.header.links} onChange={(links) => set('header', { ...cv.header, links })} />
        </div>
      </section>

      <section className="profile-card cv-section">
        <h2 className="card-heading-title">Professional summary</h2>
        <textarea className="cv-summary" rows={5} maxLength={1200} value={cv.summary} onChange={(e) => set('summary', e.target.value)} />
      </section>

      <ItemList<'skills'>
        title="Skills"
        addLabel="Add skill group"
        items={cv.skills}
        makeItem={NEW_ITEM.skills}
        heading={(g) => g.name}
        onChange={(skills) => set('skills', skills)}
        render={(g, update) => (
          <>
            <Field label="Group name" required wide value={g.name} onChange={(name) => update({ name })} placeholder="e.g. Backend Development" />
            <Chips label="Skills" values={g.items} onChange={(items) => update({ items })} commaAdds={false} />
          </>
        )}
      />

      <ItemList<'experience'>
        title="Experience"
        addLabel="Add experience"
        items={cv.experience}
        makeItem={NEW_ITEM.experience}
        heading={(e) => [e.title, e.organization].filter(Boolean).join(' · ')}
        onChange={(experience) => set('experience', experience)}
        render={(e, update) => (
          <>
            <Field label="Job title" required value={e.title} onChange={(title) => update({ title })} />
            <Field label="Organization" required value={e.organization} onChange={(organization) => update({ organization })} />
            <Field label="Dates" required value={e.dates} onChange={(dates) => update({ dates })} placeholder="Feb 2026 – Apr 2026" />
            <Field label="Location" value={e.location} onChange={(location) => update({ location })} />
            <Chips label="Tools used (not printed, used to check tailored CVs)" values={e.stack} onChange={(stack) => update({ stack })} />
            <Bullets values={e.bullets} onChange={(bullets) => update({ bullets })} />
          </>
        )}
      />

      <ItemList<'projects'>
        title="Projects"
        hint="Pinned projects appear first in every tailored CV. Two more are chosen by job type."
        addLabel="Add project"
        items={cv.projects}
        makeItem={NEW_ITEM.projects}
        heading={(p) => `${p.pinned ? '📌 ' : ''}${p.name}`}
        onChange={(projects) => set('projects', projects)}
        render={(p, update) => (
          <>
            <Field label="Project name" required wide value={p.name} onChange={(name) => update({ name })} />
            <div className="cv-block is-wide cv-options">
              <label className="cv-check">
                <input type="checkbox" checked={p.pinned} onChange={(e) => update({ pinned: e.target.checked })} />
                Pinned (always shown)
              </label>
              {!p.pinned && (
                <div className="cv-tracks">
                  <span className="cv-sub">Use for jobs in</span>
                  {TRACKS.map((t) => (
                    <label key={t.value} className="cv-check">
                      <input
                        type="checkbox"
                        checked={p.tracks.includes(t.value)}
                        onChange={(e) =>
                          update({ tracks: e.target.checked ? [...p.tracks, t.value] : p.tracks.filter((x) => x !== t.value) })
                        }
                      />
                      {t.label}
                    </label>
                  ))}
                </div>
              )}
            </div>
            <Links values={p.links} onChange={(links) => update({ links })} />
            <Chips label="Tools used (not printed, used to check tailored CVs)" values={p.stack} onChange={(stack) => update({ stack })} />
            <Bullets values={p.bullets} onChange={(bullets) => update({ bullets })} />
          </>
        )}
      />

      <ItemList<'research'>
        title="Research"
        addLabel="Add research"
        items={cv.research}
        makeItem={NEW_ITEM.research}
        heading={(r) => r.title}
        onChange={(research) => set('research', research)}
        render={(r, update) => (
          <>
            <Field label="Title" required wide value={r.title} onChange={(title) => update({ title })} />
            <Field label="Subtitle" wide value={r.subtitle} onChange={(subtitle) => update({ subtitle })} placeholder="Undergraduate Thesis – University" />
            <Links values={r.links} onChange={(links) => update({ links })} />
            <Bullets values={r.bullets} onChange={(bullets) => update({ bullets })} />
          </>
        )}
      />

      <ItemList<'education'>
        title="Education"
        addLabel="Add education"
        items={cv.education}
        makeItem={NEW_ITEM.education}
        heading={(e) => e.degree}
        onChange={(education) => set('education', education)}
        render={(e, update) => (
          <>
            <Field label="Degree" required wide value={e.degree} onChange={(degree) => update({ degree })} />
            <Field label="Institution" required wide value={e.institution} onChange={(institution) => update({ institution })} />
            <Field label="Dates" required value={e.dates} onChange={(dates) => update({ dates })} />
            <Field label="Grade" value={e.grade} onChange={(grade) => update({ grade })} placeholder="CGPA: 3.54 / 4.00" />
            <Field label="Location" wide value={e.location} onChange={(location) => update({ location })} />
          </>
        )}
      />

      <ItemList<'certifications'>
        title="Certifications"
        addLabel="Add certification"
        items={cv.certifications}
        makeItem={NEW_ITEM.certifications}
        heading={(c) => c.name}
        onChange={(certifications) => set('certifications', certifications)}
        render={(c, update) => (
          <>
            <Field label="Name" required wide value={c.name} onChange={(name) => update({ name })} />
            <Field label="Issuer" value={c.issuer} onChange={(issuer) => update({ issuer })} />
            <Field label="Link" url value={c.url} onChange={(url) => update({ url })} placeholder="https://" />
          </>
        )}
      />

      <ItemList<'volunteering'>
        title="Volunteering"
        addLabel="Add volunteering"
        items={cv.volunteering}
        makeItem={NEW_ITEM.volunteering}
        heading={(v) => v.name}
        onChange={(volunteering) => set('volunteering', volunteering)}
        render={(v, update) => (
          <>
            <Field label="Name" required wide value={v.name} onChange={(name) => update({ name })} />
            <Field label="Date" value={v.date} onChange={(date) => update({ date })} placeholder="Apr 2025" />
            <Field label="Link" url value={v.url} onChange={(url) => update({ url })} placeholder="https://" />
            <Bullets values={v.bullets} onChange={(bullets) => update({ bullets })} />
          </>
        )}
      />

      <ItemList<'references'>
        title="References"
        addLabel="Add reference"
        items={cv.references}
        makeItem={NEW_ITEM.references}
        heading={(r) => r.name}
        onChange={(references) => set('references', references)}
        render={(r, update) => (
          <>
            <Field label="Name" required wide value={r.name} onChange={(name) => update({ name })} />
            <label className="cv-field is-wide">
              <span>Title, organization and address (one per line)</span>
              <textarea rows={4} value={r.lines.join('\n')} onChange={(e) => update({ lines: e.target.value.split('\n') })} />
            </label>
            <Field label="Phone" value={r.phone} onChange={(phone) => update({ phone })} />
            <Field label="Email" value={r.email} onChange={(email) => update({ email })} />
          </>
        )}
      />

      <div className="save-bar">
        <div className="cv-status">
          {errors.length > 0 ? (
            <details>
              <summary>
                {errors.length} {errors.length === 1 ? 'thing' : 'things'} to fix before saving
              </summary>
              <ul>
                {errors.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </details>
          ) : (
            <p>{dirty ? 'You have unsaved changes.' : 'All changes saved.'}</p>
          )}
        </div>
        <button type="button" className="btn-primary" disabled={saving || !dirty || errors.length > 0} onClick={save}>
          {saving ? 'Saving…' : 'Save CV'}
        </button>
      </div>
    </div>
  )
}