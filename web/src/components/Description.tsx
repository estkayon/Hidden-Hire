type Block =
  | { kind: 'heading'; text: string }
  | { kind: 'paragraph'; text: string }
  | { kind: 'list'; items: string[] }

const BULLET = /^(?:[•\-*●▪➜►◦]|\d+[.)])\s+/

function looksLikeHeading(line: string): boolean {
  if (line.length > 70) return false
  const letters = line.replace(/[^A-Za-z]/g, '')
  return line.endsWith(':') || (letters.length > 3 && letters === letters.toUpperCase())
}

function toBlocks(text: string): Block[] {
  const blocks: Block[] = []
  for (const raw of text.split('\n')) {
    const line = raw.trim()
    if (!line) continue
    if (line.startsWith('## ')) {
      blocks.push({ kind: 'heading', text: line.slice(3) })
    } else if (BULLET.test(line)) {
      const item = line.replace(BULLET, '')
      const last = blocks[blocks.length - 1]
      if (last?.kind === 'list') last.items.push(item)
      else blocks.push({ kind: 'list', items: [item] })
    } else if (looksLikeHeading(line)) {
      blocks.push({ kind: 'heading', text: line.replace(/:$/, '') })
    } else {
      blocks.push({ kind: 'paragraph', text: line })
    }
  }
  return blocks
}

export function Description({ text }: { text: string }) {
  const blocks = toBlocks(text)
  if (blocks.length === 0) {
    return <p className="desc-empty">The posting has no description text.</p>
  }
  return (
    <div className="desc">
      {blocks.map((block, i) => {
        if (block.kind === 'heading') return <h3 key={i}>{block.text}</h3>
        if (block.kind === 'list') {
          return (
            <ul key={i}>
              {block.items.map((item, j) => (
                <li key={j}>{item}</li>
              ))}
            </ul>
          )
        }
        return <p key={i}>{block.text}</p>
      })}
    </div>
  )
}