import { useState } from 'react'
import './App.css'
import ConnectionsPage from './pages/Connections'
import LoginPage from './pages/Login'
import RegisterPage from './pages/Register'

const App = () => {
  const [view, setView] = useState<'login' | 'register' | 'connections'>(
    'login'
  )

  if (view === 'login') {
    return (
      <LoginPage
        onSignIn={() => setView('connections')}
        onGoToRegister={() => setView('register')}
      />
    )
  }

  if (view === 'register') {
    return <RegisterPage onGoToLogin={() => setView('login')} />
  }

  return <ConnectionsPage />
}

export default App
