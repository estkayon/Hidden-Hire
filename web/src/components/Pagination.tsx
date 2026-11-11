type Props = {
  page: number
  pageCount: number
  onChange: (page: number) => void
}

/** Page numbers with ellipses, e.g. 1 … 4 5 6 … 12 */
function pageItems(page: number, pageCount: number): (number | 'gap')[] {
  const pages = new Set([1, pageCount, page - 1, page, page + 1])
  const sorted = [...pages].filter((p) => p >= 1 && p <= pageCount).sort((a, b) => a - b)
  const items: (number | 'gap')[] = []
  sorted.forEach((p, i) => {
    if (i > 0 && p - sorted[i - 1] > 1) items.push('gap')
    items.push(p)
  })
  return items
}

export function Pagination({ page, pageCount, onChange }: Props) {
  if (pageCount <= 1) return null

  return (
    <nav className="pagination" aria-label="Pages">
      <button
        type="button"
        className="page-step"
        disabled={page === 1}
        onClick={() => onChange(page - 1)}
        aria-label="Previous page"
      >
        ‹
      </button>

      {pageItems(page, pageCount).map((item, i) =>
        item === 'gap' ? (
          <span key={`gap-${i}`} className="page-gap">
            …
          </span>
        ) : (
          <button
            key={item}
            type="button"
            className={`page-num${item === page ? ' active' : ''}`}
            aria-current={item === page ? 'page' : undefined}
            onClick={() => onChange(item)}
          >
            {item}
          </button>
        ),
      )}

      <button
        type="button"
        className="page-step"
        disabled={page === pageCount}
        onClick={() => onChange(page + 1)}
        aria-label="Next page"
      >
        ›
      </button>
    </nav>
  )
}