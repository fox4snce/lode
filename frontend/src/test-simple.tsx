// Minimal test to see if React can mount at all
console.log('=== TEST FILE LOADING ===')

import React from 'react'
import ReactDOM from 'react-dom/client'

console.log('React:', typeof React)
console.log('ReactDOM:', typeof ReactDOM)

const rootElement = document.getElementById('root')
if (!rootElement) {
  console.error('NO ROOT ELEMENT!')
} else {
  console.log('Root element found:', rootElement)
  rootElement.innerHTML = '<div style="padding: 40px; background: #4dabf7; color: white; font-size: 24px;">TEST: If you see this, React mounted!</div>'
  
  try {
    const root = ReactDOM.createRoot(rootElement)
    root.render(React.createElement('div', {
      style: { padding: '40px', background: '#51cf66', color: 'white', fontSize: '24px' }
    }, 'SUCCESS: React is working!'))
    console.log('React rendered successfully!')
  } catch (error) {
    console.error('React render failed:', error)
    rootElement.innerHTML = `<div style="padding: 40px; background: #ff6b6b; color: white;">
      <h1>React Failed</h1>
      <pre>${error.toString()}</pre>
    </div>`
  }
}

