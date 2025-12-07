import { useState } from 'react'
import '../styles/account.css'

type ResetPasswordProps = {
  onResetComplete: () => void
}

const ResetPasswordPage = ({ onResetComplete }: ResetPasswordProps) => {
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    // TODO: call API to update password
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }
    setError('')
    onResetComplete()
  }

  return (
    <div className="account-shell">
      <header className="account-header">
        <h1>Reset Password</h1>
        <p className="hero-subtitle">Enter and confirm your new password.</p>
      </header>
      <section className="card">
        <form className="reset-form" onSubmit={handleSubmit}>
          <label className="auth-field">
            <span className="auth-label">New password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          <label className="auth-field">
            <span className="auth-label">Confirm password</span>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </label>
          {error && <p className="error-text">{error}</p>}
          <button type="submit" className="primary-btn">
            Save password
          </button>
        </form>
      </section>
    </div>
  )
}

export default ResetPasswordPage
