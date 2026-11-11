import { useState } from 'react'

type Props = {
  values: string[]
  onChange: (values: string[]) => void
  placeholder: string
}

export function ChipInput({ values, onChange, placeholder }: Props) {
  const [text, setText] = useState('')

  function add() {
    const value = text.trim()
    if (value && !values.some((v) => v.toLowerCase() === value.toLowerCase())) {
      onChange([...values, value])
    }
    setText('')
  }

  return (
    <div className="chip-input">
      {values.map((value) => (
        <span key={value} className="chip chip-edit">
          {value}
          <button
            type="button"
            aria-label={`Remove ${value}`}
            onClick={() => onChange(values.filter((v) => v !== value))}
          >
            ×
          </button>
        </span>
      ))}
      <input
        value={text}
        maxLength={60}
        placeholder={placeholder}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ',') {
            e.preventDefault()
            add()
          }
        }}
        onBlur={add}
      />
    </div>
  )
}