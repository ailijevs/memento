import { useState } from 'react'
import './App.css'
import ConnectionsPage from './pages/Connections'
import LoginPage from './pages/Login'

const App = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  if (!isAuthenticated) {
    return <LoginPage onSignIn={() => setIsAuthenticated(true)} />
  }

  return <ConnectionsPage />
}

export default App
