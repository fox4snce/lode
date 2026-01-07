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
    checkSetup().then(setInitialized)
  }, [])

  if (initialized === null) {
    return <div>Loading...</div>
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

