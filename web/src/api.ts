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
}

export const EMPTY_FILTERS: Filters = {
  q: '',
  country: '',
  workType: '',
  postedWithin: '',
  source: '',
  savedOnly: false,
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