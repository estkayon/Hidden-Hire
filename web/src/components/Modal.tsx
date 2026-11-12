import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import './Modal.css'

const CLOSE_MS = 220

type Props = {
  label: string
  onClose: () => void
  wide?: boolean
  children: ReactNode
}

export function Modal({ label, onClose, wide, children }: Props) {
  const [closing, setClosing] = useState(false)

  const close = useCallback(() => {
    setClosing(true)
    window.setTimeout(onClose, CLOSE_MS)
  }, [onClose])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close()
    }
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', onKey)
    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', onKey)
    }
  }, [close])

  return createPortal(
    <div className={`popup-overlay${closing ? ' is-closing' : ''}`} onClick={close}>
      <div
        className={`popup${wide ? ' is-wide' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label={label}
        onClick={(e) => e.stopPropagation()}
      >
        <button type="button" className="popup-close" aria-label="Close" onClick={close}>
          ×
        </button>
        <div className="popup-body">{children}</div>
      </div>
    </div>,
    document.body,
  )
}