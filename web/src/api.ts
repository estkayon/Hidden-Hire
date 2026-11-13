export type Job = {
  id: string
  title: string
  company: string
  location_raw: string
  country: string | null
  city: string | null
  work_type: string
  remote_scope: string
  source: string
  seniority: string | null
  also_seen: string[]
  posted_at: string | null
  deadline: string | null
  salary_min: number | null
  salary_max: number | null
  salary_currency: string | null
  salary_period: string | null
  is_new: boolean
  country_tier: number
  saved: boolean
  applied_at: string | null
  match: number | null
  eligibility: Eligibility
}

export type Eligibility =
  | 'bd'
  | 'remote_worldwide'
  | 'remote_regions'
  | 'remote_unknown'
  | 'remote_country'
  | 'visa'
  | 'local_only'
  | 'check_visa'

export type Dimension = { score: number; reason: string }

export type RecruiterView = {
  skills: Dimension
  experience: Dimension
  eligibility: Dimension
  domain: Dimension
  education: Dimension
  strengths: string[]
  gaps: string[]
  blockers: string[]
  summary: string
  total: number
  requirements?: { text: string; importance: 'must' | 'nice'; status: 'met' | 'partly' | 'missing'; evidence: string }[]
  verdict?: 'apply' | 'stretch' | 'skip'
  verdict_reason?: string
  keywords?: { percent: number | null; matched: string[]; missing: string[] }
}

export type JobList = {
  total: number
  jobs: Job[]
}

export type JobDetail = Job & {
  description: string
  source_url: string | null
  apply_url: string | null
  apply_email: string | null
  tags: string[]
  recruiter_view: RecruiterView | null
  recruiter_outdated: boolean
}

export type PasteInput = {
  title: string
  company: string
  location: string
  url: string
  text: string
}

export type Facet = { value: string; count: number }
export type Facets = { countries: Facet[]; sources: Facet[] }

export type Filters = {
  q: string
  country: string
  workType: string
  postedWithin: string
  source: string
  savedOnly: boolean
  appliedOnly: boolean
  relevance: '' | 'relevant' | 'other'
  minMatch: string
  sort: '' | 'match'
}

export const EMPTY_FILTERS: Filters = {
  q: '',
  country: '',
  workType: '',
  postedWithin: '',
  source: '',
  savedOnly: false,
  appliedOnly: false,
  relevance: '',
  minMatch: '',
  sort: '',
}
export const PAGE_SIZE = 30

export function toParams(filters: Filters): URLSearchParams {
  const params = new URLSearchParams({ limit: String(PAGE_SIZE) })
  if (filters.q.trim()) params.set('q', filters.q.trim())
  if (filters.country) params.set('country', filters.country)
  if (filters.workType) params.set('work_type', filters.workType)
  if (filters.postedWithin) params.set('posted_within_hours', filters.postedWithin)
  if (filters.source) params.set('source', filters.source)
  if (filters.savedOnly) params.set('saved', 'true')
  if (filters.appliedOnly) params.set('applied', 'true')
  if (filters.relevance) params.set('relevance', filters.relevance)
  if (filters.minMatch) params.set('min_match', filters.minMatch)
  if (filters.sort) params.set('sort', filters.sort)
  return params
}

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal })
  if (!response.ok) {
    throw new Error(`API error ${response.status}`)
  }
  return response.json()
}

export function fetchJobs(params: URLSearchParams, signal?: AbortSignal): Promise<JobList> {
  return getJson(`/api/jobs?${params}`, signal)
}

export type SourceStatus = {
  source: string
  run_at: string
  jobs_found: number
  jobs_kept: number
  errors: string[]
  status: 'ok' | 'partial' | 'empty' | 'failing'
}

export type HealthReport = {
  last_run_at: string | null
  sources: SourceStatus[]
}

export type PersonalInfo = {
  full_name: string
  email: string
  phone: string
  location: string
  github: string
  linkedin: string
  portfolio: string
}

export type Profile = {
  personal: PersonalInfo
  skills: string[]
  target_roles: string[]
  years_experience: number | null
  cv_file: string | null
  cv_uploaded_at: string | null
}

export type ProfileState = {
  has_cv: boolean
  profile: Profile | null
  detected_skills: string[]
}

export type ProfileUpdate = Pick<Profile, 'personal' | 'skills' | 'target_roles' | 'years_experience'>

async function errorMessage(response: Response): Promise<string> {
  try {
    const data = await response.json()
    if (typeof data.detail === 'string') return data.detail
    if (Array.isArray(data.detail)) {
      const fields = data.detail.map((d: { loc?: string[] }) => d.loc?.[d.loc.length - 1]).filter(Boolean)
      return `Please check: ${fields.join(', ')}`
    }
  } catch {
    // fall through to the generic message
  }
  return `API error ${response.status}`
}

async function sendJson<T>(url: string, method: string, body?: unknown): Promise<T> {
  const response = await fetch(url, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.json()
}

export function requestRecruiterView(jobId: string): Promise<JobDetail> {
  return sendJson(`/api/jobs/${encodeURIComponent(jobId)}/recruiter-view`, 'POST')
}

export type CvStatus = {
  exists: boolean
  generated_at: string | null
  flags: string[]
  keywords: string[]
}
export function fetchCvStatus(jobId: string): Promise<CvStatus> {
  return getJson(`/api/jobs/${encodeURIComponent(jobId)}/cv`)
}

export function generateCv(jobId: string, projects: number): Promise<CvStatus> {
  return sendJson(`/api/jobs/${encodeURIComponent(jobId)}/cv?projects=${projects}`, 'POST')
}

export function deleteTailoredCv(jobId: string): Promise<CvStatus> {
  return sendJson(`/api/jobs/${encodeURIComponent(jobId)}/cv`, 'DELETE')
}

export function cvDownloadUrl(jobId: string, kind: 'pdf' | 'tex', inline = false): string {
  return `/api/jobs/${encodeURIComponent(jobId)}/cv.${kind}${inline ? '?inline=true' : ''}`
}

export async function setApplied(jobId: string, applied: boolean): Promise<string | null> {
  const data = await sendJson<{ applied_at: string | null }>(
    `/api/applied/${encodeURIComponent(jobId)}`,
    applied ? 'POST' : 'DELETE',
  )
  return data.applied_at
}

export type MasterSummary = { exists: boolean; counts: Record<string, number> }

export function fetchMaster(): Promise<MasterSummary> {
  return getJson('/api/master')
}

export function draftFromNotes(text: string): Promise<MasterDraft> {
  return sendJson('/api/master/draft', 'POST', { text })
}

export function draftFromUploadedCv(): Promise<MasterDraft> {
  return sendJson('/api/master/draft-from-cv', 'POST')
}

export function mergeDraft(draft: CvDraft): Promise<{ report: string[] }> {
  return sendJson('/api/master/merge', 'POST', { draft })
}
export type CvLink = { label: string; url: string }

export type CvData = {
  header: { name: string; location: string; phone: string; email: string; links: CvLink[] }
  summary: string
  skills: { name: string; items: string[] }[]
  experience: {
    title: string
    dates: string
    organization: string
    location: string
    stack: string[]
    bullets: string[]
  }[]
  projects: {
    name: string
    pinned: boolean
    tracks: string[]
    links: CvLink[]
    stack: string[]
    bullets: string[]
  }[]
  research: { title: string; links: CvLink[]; subtitle: string; tools: string; bullets: string[] }[]
  education: { degree: string; dates: string; institution: string; grade: string; location: string }[]
  certifications: { name: string; issuer: string; url: string }[]
  volunteering: { name: string; date: string; url: string; bullets: string[] }[]
  other_sections: { title: string; items: { text: string; url: string }[] }[]
  references: { name: string; lines: string[]; phone: string; email: string }[]
  section_order: string[]
}

export type CvDraft = Omit<CvData, 'header'> & { header: CvData['header'] | null }
export type MasterDraft = { draft: CvDraft; flags: string[] }

export function fetchMasterCv(): Promise<CvData> {
  return getJson('/api/master/cv')
}

export function saveMasterCv(cv: CvData): Promise<CvData> {
  return sendJson('/api/master/cv', 'PUT', cv)
}

export function fetchProfile(): Promise<ProfileState> {
  return getJson('/api/profile')
}

export async function uploadCv(file: File): Promise<ProfileState> {
  const form = new FormData()
  form.append('file', file)
  const response = await fetch('/api/profile/cv', { method: 'POST', body: form })
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.json()
}

export function updateProfile(body: ProfileUpdate): Promise<ProfileState> {
  return sendJson('/api/profile', 'PUT', body)
}

export function deleteCv(): Promise<ProfileState> {
  return sendJson('/api/profile/cv', 'DELETE')
}

export function fetchHealth(): Promise<HealthReport> {
  return getJson('/api/health')
}

export function fetchFacets(): Promise<Facets> {
  return getJson('/api/jobs/facets')
}

export function fetchJob(jobId: string, signal?: AbortSignal): Promise<JobDetail> {
  return getJson(`/api/jobs/${encodeURIComponent(jobId)}`, signal)
}

export async function pasteJob(input: PasteInput): Promise<JobDetail> {
  const response = await fetch('/api/jobs/paste', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...input, url: input.url.trim() || null }),
  })
  if (response.status === 422) {
    throw new Error('Check the fields: job text needs at least 20 characters and the URL must start with http.')
  }
  if (!response.ok) {
    throw new Error(`API error ${response.status}`)
  }
  return response.json()
}

export async function setSaved(jobId: string, saved: boolean): Promise<void> {
  const response = await fetch(`/api/saved/${encodeURIComponent(jobId)}`, {
    method: saved ? 'POST' : 'DELETE',
  })
  if (!response.ok) {
    throw new Error(`API error ${response.status}`)
  }
}