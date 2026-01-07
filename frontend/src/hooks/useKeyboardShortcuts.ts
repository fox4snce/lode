import { useEffect } from 'react'

interface Shortcuts {
  [key: string]: (e: KeyboardEvent) => void
}

export function useKeyboardShortcuts(shortcuts: Shortcuts, deps: any[] = []) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const key = e.key.toLowerCase()
      const ctrl = e.ctrlKey || e.metaKey
      const shift = e.shiftKey
      const alt = e.altKey

      // Build shortcut key
      let shortcut = ''
      if (ctrl) shortcut += 'ctrl+'
      if (shift) shortcut += 'shift+'
      if (alt) shortcut += 'alt+'
      shortcut += key

      // Check for exact match
      if (shortcuts[shortcut]) {
        e.preventDefault()
        shortcuts[shortcut](e)
        return
      }

      // Check for key-only match (no modifiers)
      if (!ctrl && !shift && !alt && shortcuts[key]) {
        e.preventDefault()
        shortcuts[key](e)
        return
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, deps)
}

