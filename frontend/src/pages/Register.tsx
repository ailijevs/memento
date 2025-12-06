import { useState } from 'react'
import '../styles/auth.css'

type RegisterProps = {
  onGoToLogin: () => void
}

const RegisterPage = ({ onGoToLogin }: RegisterProps) => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    // TODO: hook up registration flow
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <h1 className="auth-title">Welcome to Memento!</h1>

        <div className="auth-subtitle">Sign Up with us</div>

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
            Sign up
          </button>
        </form>

        <p className="auth-footer">
          Already have an account?{' '}
          <button type="button" className="link-button" onClick={onGoToLogin}>
            Sign in
          </button>
        </p>
      </div>
    </div>
  )
}

export default RegisterPage
