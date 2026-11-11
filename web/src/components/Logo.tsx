import { useId } from 'react'

export function Logo({ size = 32 }: { size?: number }) {
  const gradientId = useId()

  return (
    <svg
      className="logo"
      width={size}
      height={size}
      viewBox="0 0 64 64"
      role="img"
      aria-label="Hidden Hire logo"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#2b5a6b" />
          <stop offset="1" stopColor="#204654" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="16" fill={`url(#${gradientId})`} />
      <rect x="16" y="15" width="7.5" height="34" rx="3.75" fill="#F7F9E1" />
      <rect x="40.5" y="15" width="7.5" height="34" rx="3.75" fill="#F7F9E1" />
      <rect x="22" y="30.25" width="20" height="3.5" fill="#F7F9E1" />
      <circle cx="32" cy="32" r="8.5" fill="#CAFFA6" stroke="#204654" strokeWidth="2" />
      <circle cx="32" cy="32" r="3.2" fill="#204654" />
      <circle cx="34.6" cy="29.4" r="1.3" fill="#A9E0F1" />
    </svg>
  )
}