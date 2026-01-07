import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

console.log('main.tsx: Starting React app...')
console.log('main.tsx: Root element exists:', !!document.getElementById('root'))

try {
  const rootElement = document.getElementById('root')
  if (!rootElement) {
    throw new Error('Root element not found!')
  }
  
  const root = ReactDOM.createRoot(rootElement)
  console.log('main.tsx: React root created')
  
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  )
  console.log('main.tsx: App rendered')
} catch (error) {
  console.error('FATAL ERROR in main.tsx:', error)
  document.body.innerHTML = `<div style="padding: 20px; color: red;">
    <h1>Fatal Error</h1>
    <pre>${error}</pre>
  </div>`
}

