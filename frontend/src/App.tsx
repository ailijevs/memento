import { useEffect, useState } from 'react'
import './App.css'
import ConnectionsPage from './pages/Connections'
import EventsPage from './pages/Events'
import LoginPage from './pages/Login'
import RegisterPage from './pages/Register'
import VerifyPage from './pages/Verify'
import type { Event } from './types/event'

const App = () => {
  const [view, setView] = useState<
    'login' | 'register' | 'verify' | 'events' | 'connections'
  >('login')

  useEffect(() => {
    const storedAuth = localStorage.getItem('memento_authed')
    if (storedAuth === 'true') {
      setView('events')
    }
  }, [])

  const handleAuthenticated = () => {
    localStorage.setItem('memento_authed', 'true')
    setView('events')
  }

  const handleEventSelected = (event: Event) => {
    localStorage.setItem('memento_last_event', event.id)
    setView('connections')
  }

  if (view === 'login') {
    return (
      <LoginPage
        onSignIn={handleAuthenticated}
        onGoToRegister={() => setView('register')}
      />
    )
  }

  if (view === 'register') {
    return (
      <RegisterPage
        onGoToLogin={() => setView('login')}
        onGoToVerify={() => setView('verify')}
      />
    )
  }

  if (view === 'verify') {
    return <VerifyPage onVerified={handleAuthenticated} />
  }

  if (view === 'events') {
    return <EventsPage onSelectEvent={handleEventSelected} />
  }

  return <ConnectionsPage />
}

export default App
