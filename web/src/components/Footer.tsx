import { Logo } from './Logo'
import './Footer.css'

const REPO = 'https://github.com/estkayon/hidden-hire'

const APP_LINKS = [
  { label: 'Jobs', href: '#' },
  { label: 'Sources', href: '#/sources' },
  { label: 'Profile', href: '#/profile' },
  { label: 'CV editor', href: '#/cv' },
]

const PROJECT_LINKS = [
  { label: 'Source code', href: REPO },
  { label: 'Job data', href: 'https://github.com/estkayon/hidden-hire-data' },
  { label: 'Report an issue', href: `${REPO}/issues` },
  { label: 'MIT License', href: `${REPO}/blob/main/LICENSE` },
]

function LinkGroup({ title, links, external }: { title: string; links: typeof APP_LINKS; external?: boolean }) {
  return (
    <nav className="ftr-group" aria-label={title}>
      <p className="ftr-title">{title}</p>
      <ul>
        {links.map((link) => (
          <li key={link.label}>
            <a href={link.href} {...(external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}>
              {link.label}
              {external && (
                <span className="ftr-ext" aria-hidden="true">
                  ↗
                </span>
              )}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  )
}

export function Footer() {
  const year = new Date().getFullYear()
  return (
    <footer className="ftr">
      <div className="ftr-glass">
        <div className="ftr-top">
          <div className="ftr-brand">
            <div className="ftr-brand-row">
              <Logo size={44} />
              <p className="ftr-name">Hidden Hire</p>
            </div>
            <p className="ftr-tagline">
              Local-first job search for tech roles in Bangladesh. Underrated jobs, matched to your CV.
            </p>
            <span className="ftr-badge">
              <span className="ftr-badge-dot" aria-hidden="true" />
              Runs on 127.0.0.1 · Your data stays on this PC
            </span>
          </div>
          <LinkGroup title="App" links={APP_LINKS} />
          <LinkGroup title="Project" links={PROJECT_LINKS} external />
        </div>

        <div className="ftr-bottom">
          <p>
            © {year} Md. Estiak Rahman Ayon · <a href={`${REPO}/blob/main/LICENSE`} target="_blank" rel="noopener noreferrer">MIT License</a>
          </p>
          <button type="button" className="ftr-top-btn" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
            Back to top
            <span aria-hidden="true">↑</span>
          </button>
          <p className="ftr-end">Made in Bangladesh</p>
        </div>
        <p className="ftr-note">Apply only on the official posting. Hidden Hire never applies or sends emails for you.</p>
      </div>
    </footer>
  )
}