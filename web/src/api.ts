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
}

export type JobList = {
  total: number
  jobs: Job[]
}

export async function fetchJobs(params = new URLSearchParams()): Promise<JobList> {
  const response = await fetch(`/api/jobs?${params}`)
  if (!response.ok) {
    throw new Error(`API error ${response.status}`)
  }
  return response.json()
}