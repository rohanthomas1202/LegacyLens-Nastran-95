import { useState, useRef, useEffect } from 'react'
import { apiPost } from '../api'

export default function Autocomplete({ value, onChange, placeholder, className }) {
  const [suggestions, setSuggestions] = useState([])
  const [showDropdown, setShowDropdown] = useState(false)
  const [highlighted, setHighlighted] = useState(-1)
  const timerRef = useRef(null)
  const wrapperRef = useRef(null)

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const fetchSuggestions = (prefix) => {
    clearTimeout(timerRef.current)
    if (!prefix || prefix.length < 2) {
      setSuggestions([])
      setShowDropdown(false)
      return
    }
    timerRef.current = setTimeout(async () => {
      try {
        const data = await apiPost('/api/autocomplete', { prefix, limit: 10 })
        setSuggestions(data.suggestions || [])
        setShowDropdown((data.suggestions || []).length > 0)
        setHighlighted(-1)
      } catch {
        setSuggestions([])
      }
    }, 150)
  }

  const handleInputChange = (e) => {
    const val = e.target.value
    onChange(val)
    fetchSuggestions(val)
  }

  const selectSuggestion = (name) => {
    onChange(name)
    setShowDropdown(false)
    setSuggestions([])
  }

  const handleKeyDown = (e) => {
    if (!showDropdown) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlighted((h) => Math.min(h + 1, suggestions.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlighted((h) => Math.max(h - 1, 0))
    } else if (e.key === 'Enter' && highlighted >= 0) {
      e.preventDefault()
      selectSuggestion(suggestions[highlighted].name)
    } else if (e.key === 'Escape') {
      setShowDropdown(false)
    }
  }

  return (
    <div className="autocomplete-wrapper" ref={wrapperRef}>
      <input
        type="text"
        value={value}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onFocus={() => suggestions.length > 0 && setShowDropdown(true)}
        placeholder={placeholder}
        className={className}
      />
      {showDropdown && (
        <div className="autocomplete-dropdown">
          {suggestions.map((s, i) => (
            <div
              key={s.name}
              className={`autocomplete-item ${i === highlighted ? 'highlighted' : ''}`}
              onClick={() => selectSuggestion(s.name)}
            >
              <span className="ac-name">{s.name}</span>
              <span className="ac-type">{s.chunk_type}</span>
              <span className="ac-file">{s.file_path}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
