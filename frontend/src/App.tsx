import React, { useState, useEffect } from 'react'
import WelcomeScreen from './screens/WelcomeScreen'
import ImportScreen from './screens/ImportScreen'
import MainShell from './screens/MainShell'
import AnalyticsScreen from './screens/AnalyticsScreen'
import FindToolsScreen from './screens/FindToolsScreen'
import ExportScreen from './screens/ExportScreen'
import SettingsScreen from './screens/SettingsScreen'
import ImportReportsScreen from './screens/ImportReportsScreen'
import AboutScreen from './screens/AboutScreen'
import { checkSetup, getState } from './api'

type Screen = 'main' | 'import' | 'analytics' | 'find-tools' | 'export' | 'settings' | 'import-reports' | 'about'

function App() {
  const [initialized, setInitialized] = useState<boolean | null>(null)
  const [currentScreen, setCurrentScreen] = useState<Screen>('main')

  useEffect(() => {
    console.log('=== App.tsx useEffect running ===')
    console.log('App mounted, checking setup...')
    console.log('checkSetup function:', typeof checkSetup)
    
    // Set a shorter timeout and default to false if it hangs
    const timeoutId = setTimeout(() => {
      console.warn('Setup check timed out after 3 seconds - defaulting to welcome screen')
      setInitialized(false)
    }, 3000)
    
    try {
      console.log('Calling checkSetup()...')
      const setupPromise = checkSetup()
      console.log('checkSetup() returned a promise:', !!setupPromise)
      
      setupPromise
        .then((result) => {
          clearTimeout(timeoutId)
          console.log('Setup check result:', result)
          setInitialized(result)
        })
        .catch((error) => {
          clearTimeout(timeoutId)
          console.error('Failed to check setup:', error)
          console.error('Error details:', error.message, error.stack)
          setInitialized(false) // Default to showing welcome screen on error
        })
    } catch (error) {
      clearTimeout(timeoutId)
      console.error('Exception calling checkSetup():', error)
      setInitialized(false)
    }
  }, [])

  if (initialized === null) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        fontSize: '16px',
        color: '#666'
      }}>
        Loading...
      </div>
    )
  }

  if (!initialized) {
    return <WelcomeScreen onInitialized={() => setInitialized(true)} />
  }

  // Route to different screens
  switch (currentScreen) {
    case 'import':
      return (
        <ImportScreen 
          onClose={() => setCurrentScreen('main')}
          onImportComplete={() => {
            setCurrentScreen('main')
          }}
        />
      )
    
    case 'analytics':
      return <AnalyticsScreen onClose={() => setCurrentScreen('main')} />
    
    case 'find-tools':
      return <FindToolsScreen onClose={() => setCurrentScreen('main')} />
    
    case 'export':
      return <ExportScreen onClose={() => setCurrentScreen('main')} />
    
    case 'settings':
      return <SettingsScreen onClose={() => setCurrentScreen('main')} />
    
    case 'import-reports':
      return <ImportReportsScreen onClose={() => setCurrentScreen('main')} />
    
    case 'about':
      return <AboutScreen onClose={() => setCurrentScreen('main')} />
    
    case 'main':
    default:
      return (
        <MainShell 
          onImport={() => setCurrentScreen('import')}
          onAnalytics={() => setCurrentScreen('analytics')}
          onFindTools={() => setCurrentScreen('find-tools')}
          onExport={() => setCurrentScreen('export')}
          onSettings={() => setCurrentScreen('settings')}
          onImportReports={() => setCurrentScreen('import-reports')}
          onAbout={() => setCurrentScreen('about')}
        />
      )
  }
}

export default App

