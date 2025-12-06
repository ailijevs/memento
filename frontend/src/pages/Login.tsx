import { useState } from 'react'
import '../styles/auth.css'

type LoginProps = {
  onSignIn: () => void
  onGoToRegister: () => void
}

const AppleIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    <path
      fill="currentColor"
      d="M17.56 13.34c.03 3.01 2.64 4.01 2.67 4.02-.02.07-.42 1.46-1.39 2.9-.84 1.25-1.71 2.5-3.08 2.53-1.34.02-1.77-.82-3.3-.82-1.53 0-2.01.8-3.28.84-1.31.05-2.31-1.35-3.17-2.6-1.73-2.51-3.05-7.08-1.27-10.17.88-1.54 2.46-2.51 4.17-2.54 1.3-.03 2.52.87 3.3.87.78 0 2.27-1.08 3.82-.92.65.03 2.47.26 3.64 2.03-.09.06-2.17 1.27-2.11 3.86zM14.52 5.9c.71-.86 1.18-2.05 1.05-3.25-1.02.04-2.25.68-2.98 1.54-.66.76-1.23 1.98-1.08 3.15 1.14.09 2.3-.58 3.01-1.44z"
    />
  </svg>
)

const GoogleIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    <path
      fill="#4285F4"
      d="M23.49 12.27c0-.82-.07-1.42-.23-2.05H12v3.72h6.51c-.13.93-.83 2.32-2.38 3.25l-.02.14 3.46 2.69.24.02c2.22-2.04 3.5-5.05 3.5-8.99z"
    />
    <path
      fill="#34A853"
      d="M12 24c3.18 0 5.85-1.05 7.8-2.88l-3.72-2.89c-.98.68-2.3 1.16-4.08 1.16-3.12 0-5.77-2.04-6.71-4.86l-.14.01-3.64 2.83-.05.13C2.98 21.53 7.15 24 12 24z"
    />
    <path
      fill="#FBBC05"
      d="M5.29 14.53c-.23-.68-.36-1.41-.36-2.16 0-.75.13-1.48.34-2.16l-.01-.14-3.69-2.87-.12.06C.52 8.89 0 10.4 0 12c0 1.59.52 3.11 1.43 4.55z"
    />
    <path
      fill="#EA4335"
      d="M12 4.73c2.21 0 3.71.95 4.56 1.74l3.33-3.25C17.82 1.48 15.18 0 12 0 7.15 0 2.98 2.47 1.43 7.45l3.7 2.87C5.23 6.77 8.88 4.73 12 4.73z"
    />
  </svg>
)

const LoginPage = ({ onSignIn, onGoToRegister }: LoginProps) => {
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
            <span className="social-icon">
              <AppleIcon />
            </span>
            <span>Sign in with Apple</span>
          </button>
          <button
            type="button"
            className="social-btn google"
            // TODO: connect Sign in with Google
            onClick={() => {}}
          >
            <span className="social-icon">
              <GoogleIcon />
            </span>
            <span>Sign in with Google</span>
          </button>
        </div>

        <p className="auth-footer">
          Don&apos;t have an account?{' '}
          <button type="button" className="link-button" onClick={onGoToRegister}>
            Sign up
          </button>
        </p>
      </div>
    </div>
  )
}

export default LoginPage
