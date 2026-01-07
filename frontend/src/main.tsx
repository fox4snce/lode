console.log('=== main.tsx MODULE LOADING ===')
console.log('Timestamp:', new Date().toISOString())

import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

console.log('=== main.tsx: Imports successful ===')
console.log('main.tsx: Starting React app...')
console.log('main.tsx: Root element exists:', !!document.getElementById('root'))

// Remove loading message
const testMsg = document.getElementById('test-message')
if (testMsg) {
  testMsg.textContent = 'React Loading...'
  testMsg.style.background = '#4dabf7'
}

try {
  const rootElement = document.getElementById('root')
  if (!rootElement) {
    throw new Error('Root element not found!')
  }
  
  // Clear any placeholder content
  rootElement.innerHTML = ''
  
  const root = ReactDOM.createRoot(rootElement)
  console.log('main.tsx: React root created')
  
  if (testMsg) {
    testMsg.textContent = 'React Mounting...'
    testMsg.style.background = '#ffd43b'
  }
  
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  )
  console.log('main.tsx: App rendered')
  
  if (testMsg) {
    setTimeout(() => {
      testMsg.style.display = 'none'
    }, 2000)
  }
} catch (error) {
  console.error('FATAL ERROR in main.tsx:', error)
  console.error('Error stack:', error.stack)
  
  if (testMsg) {
    testMsg.textContent = 'ERROR - Check Console'
    testMsg.style.background = '#ff6b6b'
  }
  
  const rootElement = document.getElementById('root')
  if (rootElement) {
    rootElement.innerHTML = `<div style="padding: 40px; color: red; background: white; border: 2px solid red; border-radius: 8px; margin: 20px;">
      <h1>Fatal Error Loading React</h1>
      <pre style="background: #f0f0f0; padding: 20px; border-radius: 4px; overflow: auto;">${error.toString()}\n\n${error.stack || 'No stack trace'}</pre>
      <p>Check the browser console (F12) for more details.</p>
    </div>`
  }
}

