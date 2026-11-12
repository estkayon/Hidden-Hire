import type { Eligibility, Job } from './api'
import { countryName } from './countries'

export type EligibilityTone = 'good' | 'maybe' | 'no'

const TONE: Record<Eligibility, EligibilityTone> = {
  bd: 'good',
  remote_worldwide: 'good',
  visa: 'good',
  remote_regions: 'maybe',
  remote_unknown: 'maybe',
  check_visa: 'maybe',
  remote_country: 'no',
  local_only: 'no',
}

const LABEL: Record<Eligibility, string> = {
  bd: 'In Bangladesh',
  remote_worldwide: 'Remote worldwide',
  visa: 'Visa sponsorship',
  remote_regions: 'Remote, some regions',
  remote_unknown: 'Remote, check location',
  check_visa: 'Check visa',
  remote_country: 'Remote, one country only',
  local_only: 'Local candidates only',
}

export function eligibilityInfo(job: Pick<Job, 'eligibility' | 'country'>): { label: string; tone: EligibilityTone } {
  const label =
    job.eligibility === 'remote_country' && job.country
      ? `Remote, ${countryName(job.country)} only`
      : LABEL[job.eligibility]
  return { label, tone: TONE[job.eligibility] }
}