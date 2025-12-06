import { useState } from 'react'
import './App.css'
import ConnectionsPage from './pages/Connections'
import LoginPage from './pages/Login'
import RegisterPage from './pages/Register'
import VerifyPage from './pages/Verify'

const App = () => {
  const [view, setView] = useState<
    'login' | 'register' | 'verify' | 'connections'
  >('login')

  if (view === 'login') {
    return (
      <LoginPage
        onSignIn={() => setView('connections')}
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
    return <VerifyPage onVerified={() => setView('connections')} />
  }

  return <ConnectionsPage />
}

export default App
