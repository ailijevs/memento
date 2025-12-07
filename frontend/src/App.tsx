import { useEffect, useState } from 'react'
import './App.css'
import ConnectionsPage from './pages/Connections'
import EventsPage from './pages/Events'
import LoginPage from './pages/Login'
import RegisterPage from './pages/Register'
import VerifyPage from './pages/Verify'
import AccountPage from './pages/Account'
import ResetPasswordPage from './pages/ResetPassword'
import type { Event } from './types/event'

const App = () => {
  const [view, setView] = useState<
    | 'login'
    | 'register'
    | 'verify'
    | 'events'
    | 'connections'
    | 'account'
    | 'resetPassword'
  >('login')
  const [postVerify, setPostVerify] = useState<'events' | 'resetPassword'>(
    'events'
  )

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

  const startPasswordReset = () => {
    setPostVerify('resetPassword')
    setView('verify')
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
        onGoToVerify={() => {
          setPostVerify('events')
          setView('verify')
        }}
      />
    )
  }

  if (view === 'verify') {
    return (
      <VerifyPage
        onVerified={() => {
          if (postVerify === 'resetPassword') {
            setView('resetPassword')
          } else {
            handleAuthenticated()
          }
        }}
      />
    )
  }

  if (view === 'events') {
    return (
      <EventsPage
        onSelectEvent={handleEventSelected}
        onHome={() => setView('events')}
        onProfile={() => setView('account')}
        activeNav="home"
      />
    )
  }

  if (view === 'account') {
    return (
      <AccountPage
        onHome={() => setView('events')}
        onStartPasswordReset={startPasswordReset}
      />
    )
  }

  if (view === 'resetPassword') {
    return (
      <ResetPasswordPage
        onResetComplete={() => {
          setView('account')
        }}
      />
    )
  }

  return (
    <ConnectionsPage
      onHome={() => setView('events')}
      onProfile={() => setView('account')}
      activeNav="home"
    />
  )
}

export default App
