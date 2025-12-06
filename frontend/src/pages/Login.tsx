import { useState } from 'react'
import '../styles/login.css'

type LoginProps = {
  onSignIn: () => void
}

const LoginPage = ({ onSignIn }: LoginProps) => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    // TODO: wire up real authentication flow
    onSignIn()
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <h1 className="auth-title">Welcome to Memento!</h1>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="auth-field">
            <span className="auth-label">Email</span>
            <input
              type="email"
              name="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>

          <label className="auth-field">
            <span className="auth-label">Password</span>
            <input
              type="password"
              name="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>

          <button type="submit" className="primary-btn">
            Sign in
          </button>
        </form>

        <div className="auth-divider"></div>

        <div className="social-buttons">
          <button
            type="button"
            className="social-btn apple"
            // TODO: connect Sign in with Apple
            onClick={() => {}}
          >
            <span className="social-icon">A</span>
            <span>Sign in with Apple</span>
          </button>
          <button
            type="button"
            className="social-btn google"
            // TODO: connect Sign in with Google
            onClick={() => {}}
          >
            <span className="social-icon google-icon">G</span>
            <span>Sign in with Google</span>
          </button>
        </div>

        <p className="auth-footer">
          Don&apos;t have an account?{' '}
          <button type="button" className="link-button">
            Sign up
          </button>
        </p>
      </div>
    </div>
  )
}

export default LoginPage
