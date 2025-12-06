import { useMemo, useRef, useState } from 'react'
import '../styles/auth.css'

type VerifyProps = {
  onVerified: () => void
}

const CODE_LENGTH = 6

const VerifyPage = ({ onVerified }: VerifyProps) => {
  const [code, setCode] = useState<string[]>(Array(CODE_LENGTH).fill(''))
  const inputsRef = useRef<Array<HTMLInputElement | null>>([])

  const codeValue = useMemo(() => code.join(''), [code])
  const isComplete = codeValue.length === CODE_LENGTH && code.every((c) => c !== '')

  const handleChange = (index: number, value: string) => {
    const sanitized = value.replace(/\D/g, '').slice(0, 1)
    const next = [...code]
    next[index] = sanitized
    setCode(next)

    if (sanitized && index < CODE_LENGTH - 1) {
      inputsRef.current[index + 1]?.focus()
    }
  }

  const handleKeyDown = (
    event: React.KeyboardEvent<HTMLInputElement>,
    index: number
  ) => {
    if (event.key === 'Backspace' && !code[index] && index > 0) {
      inputsRef.current[index - 1]?.focus()
    }
  }

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    // TODO: verify code with backend
    if (isComplete) {
      onVerified()
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <h1 className="auth-title">Verify your account</h1>
        <p className="auth-subtitle">
          We&apos;ve sent a six digit code to your email.
        </p>

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="code-grid">
            {code.map((digit, index) => (
              <input
                key={index}
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={1}
                className="code-input"
                value={digit}
                onChange={(e) => handleChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(e, index)}
                ref={(el) => {
                  inputsRef.current[index] = el
                }}
              />
            ))}
          </div>

          <button type="submit" className="primary-btn" disabled={!isComplete}>
            Submit
          </button>
        </form>
      </div>
    </div>
  )
}

export default VerifyPage
