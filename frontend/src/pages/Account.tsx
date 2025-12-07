import { useState } from 'react'
import BottomNav from '../components/BottomNav'
import '../styles/account.css'
import { PencilIcon } from '../components/icons'
import type { Profile } from '../types/profile'

type AccountProps = {
  onHome: () => void
  onStartPasswordReset: () => void
}

const AccountPage = ({ onHome, onStartPasswordReset }: AccountProps) => {
  const [tab, setTab] = useState<'profile' | 'settings'>('profile')
  const isRegisteredWithEmail = true // TODO: drive from real auth source
  const [profile, setProfile] = useState<Profile>({
    name: 'Alex Morgan',
    role: 'Product Manager',
    school: 'Purdue University',
    major: 'Computer Engineering',
    linkedin: 'linkedin.com/in/alex-morgan',
  })
  const [editingKey, setEditingKey] = useState<keyof Profile | null>(null)
  const [draftValue, setDraftValue] = useState('')
  const [privacy, setPrivacy] = useState({
    showNearby: true,
    allowRequests: true,
    shareInterests: true,
    showSocial: true,
  })

  const handleEditField = (field: string) => {
    const key = field as keyof Profile
    setEditingKey(key)
    setDraftValue(profile[key] || '')
  }

  const handleSubmitField = () => {
    if (!editingKey) return
    const trimmed = draftValue.trim()
    if (!trimmed) return
    setProfile((prev) => ({ ...prev, [editingKey]: trimmed }))
    setEditingKey(null)
    setDraftValue('')
    // TODO: persist updated profile info
  }

  const handleCancelEdit = () => {
    setEditingKey(null)
    setDraftValue('')
  }

  const handlePasswordReset = () => {
    const confirmed = window.confirm(
      'Reset your password? We will send you a verification code.'
    )
    if (confirmed) {
      onStartPasswordReset()
    }
  }

  return (
    <div className="account-shell">
      <header className="account-header">
        <h1>Account</h1>
        <div className="tab-list" role="tablist" aria-label="Account sections">
          <button
            type="button"
            className={`tab-btn ${tab === 'profile' ? 'active' : ''}`}
            onClick={() => setTab('profile')}
            role="tab"
            aria-selected={tab === 'profile'}
          >
            Profile Info
          </button>
          <button
            type="button"
            className={`tab-btn ${tab === 'settings' ? 'active' : ''}`}
            onClick={() => setTab('settings')}
            role="tab"
            aria-selected={tab === 'settings'}
          >
            Account Settings
          </button>
        </div>
      </header>

      {tab === 'profile' && (
        <section className="card">
          <h2>Profile Info</h2>
          <ul className="info-list">
            {(
              [
                { key: 'name', label: 'Name' },
                { key: 'role', label: 'Role' },
                { key: 'school', label: 'School' },
                { key: 'major', label: 'Major' },
                { key: 'linkedin', label: 'LinkedIn' },
              ] as Array<{ key: keyof Profile; label: string }>
            ).map((field) => (
              <li key={field.key}>
                <div>
                  <p className="label">{field.label}</p>
                  {editingKey === field.key ? (
                    <div className="inline-edit">
                      <input
                        className="inline-input"
                        value={draftValue}
                        onChange={(e) => setDraftValue(e.target.value)}
                      />
                      <div className="inline-actions">
                        <button
                          type="button"
                          className="secondary-btn inline-cancel"
                          onClick={handleCancelEdit}
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          className="primary-btn inline-btn"
                          onClick={handleSubmitField}
                        >
                          Change
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p className="value">{profile[field.key]}</p>
                  )}
                </div>
                {editingKey !== field.key && (
                  <button
                    type="button"
                    className="icon-btn"
                    onClick={() => handleEditField(field.key)}
                  >
                    <PencilIcon />
                  </button>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {tab === 'settings' && (
        <section className="card">
          <h2>Account Settings</h2>
          <div className="settings-group">
            <p className="label">Login</p>
            {isRegisteredWithEmail ? (
              <div className="settings-actions">
                <button type="button" className="primary-btn outline" onClick={() => handleEditField('email')}>
                  Update email
                </button>
                <button type="button" className="primary-btn outline" onClick={handlePasswordReset}>
                  Reset password
                </button>
              </div>
            ) : (
              <p className="value">Managed by external provider</p>
            )}
          </div>

          <div className="settings-group">
            <p className="label">Privacy</p>
            <ul className="privacy-list">
              <li>
                <span>Show profile to nearby attendees</span>
                <button
                  type="button"
                  className={`toggle-btn ${privacy.showNearby ? 'active' : ''}`}
                  aria-label="Toggle visibility"
                  aria-pressed={privacy.showNearby}
                  onClick={() =>
                    setPrivacy((prev) => ({ ...prev, showNearby: !prev.showNearby }))
                  }
                />
              </li>
              <li>
                <span>Allow connection requests</span>
                <button
                  type="button"
                  className={`toggle-btn ${privacy.allowRequests ? 'active' : ''}`}
                  aria-label="Toggle connection requests"
                  aria-pressed={privacy.allowRequests}
                  onClick={() =>
                    setPrivacy((prev) => ({ ...prev, allowRequests: !prev.allowRequests }))
                  }
                />
              </li>
              <li>
                <span>Share mutual interests</span>
                <button
                  type="button"
                  className={`toggle-btn ${privacy.shareInterests ? 'active' : ''}`}
                  aria-label="Toggle mutual interests"
                  aria-pressed={privacy.shareInterests}
                  onClick={() =>
                    setPrivacy((prev) => ({ ...prev, shareInterests: !prev.shareInterests }))
                  }
                />
              </li>
              <li>
                <span>Show social links</span>
                <button
                  type="button"
                  className={`toggle-btn ${privacy.showSocial ? 'active' : ''}`}
                  aria-label="Toggle social links"
                  aria-pressed={privacy.showSocial}
                  onClick={() =>
                    setPrivacy((prev) => ({ ...prev, showSocial: !prev.showSocial }))
                  }
                />
              </li>
            </ul>
            {/* TODO: wire toggles to real settings */}
          </div>
        </section>
      )}

      <BottomNav onHome={onHome} active="profile" />
    </div>
  )
}

export default AccountPage
