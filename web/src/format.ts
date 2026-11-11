import type { Job } from './api'
import { countryName } from './countries'

export const WORK_TYPE_LABEL: Record<string, string> = {
  remote: 'Remote',
  hybrid: 'Hybrid',
  onsite: 'Onsite',
}

export function timeAgo(iso: string): string {
  const hours = Math.floor((Date.now() - new Date(iso).getTime()) / 3_600_000)
  if (hours < 1) return 'just now'
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

export function formatSalary(job: Job): string | null {
  if (!job.salary_currency || (job.salary_min === null && job.salary_max === null)) return null
  const amounts = [job.salary_min, job.salary_max]
    .filter((value): value is number => value !== null)
    .map((value) => value.toLocaleString())
  const range = [...new Set(amounts)].join(' – ')
  const period = job.salary_period ? ` / ${job.salary_period}` : ''
  return `${job.salary_currency} ${range}${period}`
}

export function placeLabel(job: Job): string {
  return (
    [job.city, job.country && countryName(job.country)].filter(Boolean).join(', ') ||
    job.location_raw ||
    'Location not stated'
  )
}

/** Only http(s) links from job data are rendered as links. */
export function safeUrl(value: string | null | undefined): string | null {
  if (!value) return null
  try {
    const url = new URL(value)
    return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : null
  } catch {
    return null
  }
}

export function safeEmail(value: string | null | undefined): string | null {
  return value && /^[\w.+-]+@[\w-]+(\.[\w-]+)+$/.test(value) ? value : null
}

export function hostOf(url: string): string {
  return new URL(url).hostname.replace(/^www\./, '')
}