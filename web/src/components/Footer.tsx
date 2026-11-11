import { Logo } from './Logo'

export function Footer() {
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <Logo size={48} />
          <div>
            <p className="footer-name">Hidden Hire</p>
            <p className="footer-tagline">Underrated tech jobs, found for you. Runs privately on your machine.</p>
          </div>
        </div>
        <button
          type="button"
          className="to-top"
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
        >
          Back to top
          <span aria-hidden="true">↑</span>
        </button>
      </div>
      <p className="footer-note">Always apply on the official posting. Hidden Hire never applies or sends emails for you.</p>
    </footer>
  )
}