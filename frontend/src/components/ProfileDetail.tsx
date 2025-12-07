import { useEffect, useState } from 'react'
import './ProfileDetail.css'
import { generateConversationStarters } from '../services/openai'
import { HeartIcon } from './icons'
import type { Connection } from '../types/connection'

type ProfileProps = {
  profile: Connection
  onClose: () => void
}

const ProfileDetail = ({ profile, onClose }: ProfileProps) => {
  const [aiStarters, setAiStarters] = useState<string[]>([])
  const [loadingAI, setLoadingAI] = useState(true)

  useEffect(() => {
    // Prevent scrolling on body when modal is open
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = 'unset'
    }
  }, [])

  // Auto-generate conversation starters when profile opens
  useEffect(() => {
    const generateStarters = async () => {
      setLoadingAI(true)
      try {
        const starters = await generateConversationStarters(
          profile.name,
          profile.role,
          profile.sharedInterests
        )
        setAiStarters(starters)
      } catch (error) {
        console.error('Error generating AI starters:', error)
        setAiStarters(['Error: Could not generate conversation starters'])
      } finally {
        setLoadingAI(false)
      }
    }

    generateStarters()
  }, [profile.name, profile.role, profile.sharedInterests])

  return (
    <div className="profile-overlay" onClick={onClose}>
      <div className="profile-page" onClick={(e) => e.stopPropagation()}>
        <div className="profile-actions">
          <button className="favorite-btn" aria-label="Favorite profile">
            <HeartIcon />
          </button>
          <button className="close-btn" onClick={onClose}>
            &times;
          </button>
        </div>

        <div className="profile-content">
          <div className="profile-header">
            <div className="photos-container">
              <img
                src={profile.detectedPhoto}
                alt="Detection Photo"
                className="detection-photo"
              />
              <img
                src={profile.avatar}
                alt={profile.name}
                className="profile-avatar"
              />
            </div>
            <div className="profile-info">
              <h2>{profile.name}</h2>
              <div className="profile-role">{profile.role}</div>
              <div className="profile-location">{profile.location}</div>
            </div>
          </div>

          <div className="profile-section" style={{ '--section-index': 0 } as React.CSSProperties}>
            <h3>Match Details</h3>
            <p>
              <strong>Compatibility Score:</strong> {profile.matchScore}%
            </p>
            <div className="interests-grid">
              {profile.sharedInterests.map((interest, index) => (
                <div
                  key={interest}
                  className="interest-tag"
                  style={{ '--skill-index': index } as React.CSSProperties}
                >
                  {interest}
                </div>
              ))}
            </div>
          </div>

          <div className="profile-section" style={{ '--section-index': 1 } as React.CSSProperties}>
            <h3>Professional Summary</h3>
            <p>{profile.professionalSummary}</p>
          </div>

          {profile.experience.length > 0 && (
            <div className="profile-section" style={{ '--section-index': 2 } as React.CSSProperties}>
              <h3>Experience</h3>
              <div className="experience-list">
                {profile.experience.map((exp, index) => (
                  <div
                    key={index}
                    className="experience-item"
                    style={{ '--exp-index': index } as React.CSSProperties}
                  >
                    {exp}
                  </div>
                ))}
              </div>
            </div>
          )}

          {profile.education && (
            <div className="profile-section" style={{ '--section-index': 3 } as React.CSSProperties}>
              <h3>Education</h3>
              <p style={{ whiteSpace: 'pre-line' }}>{profile.education}</p>
            </div>
          )}

          {profile.skills.length > 0 && (
            <div className="profile-section" style={{ '--section-index': 4 } as React.CSSProperties}>
              <h3>Skills & Expertise</h3>
              <div className="skills-grid">
                {profile.skills.map((skill, index) => (
                  <div
                    key={skill}
                    className="skill-tag"
                    style={{ '--skill-index': index } as React.CSSProperties}
                  >
                    {skill}
                  </div>
                ))}
              </div>
            </div>
          )}

          {(profile.linkedin || profile.twitter || profile.instagram) && (
            <div className="profile-section" style={{ '--section-index': 5 } as React.CSSProperties}>
              <h3>Social Media</h3>
              <div className="social-links">
                {profile.linkedin && (
                  <div className="social-item">
                    <strong>LinkedIn:</strong> {profile.linkedin}
                  </div>
                )}
                {profile.twitter && (
                  <div className="social-item">
                    <strong>Twitter:</strong> {profile.twitter}
                  </div>
                )}
                {profile.instagram && (
                  <div className="social-item">
                    <strong>Instagram:</strong> {profile.instagram}
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="profile-section conversation-starters" style={{ '--section-index': 6 } as React.CSSProperties}>
            <h3>💡 Conversation Starters</h3>
            
            {loadingAI ? (
              <div className="ai-loading">
                <div className="loading-spinner"></div>
                <p>🤖 Generating personalized conversation starters with AI...</p>
              </div>
            ) : (
              <div className="starters-list ai-generated">
                <div className="ai-badge">AI Generated</div>
                {aiStarters.map((starter, index) => (
                  <div key={index} className="starter-item">
                    {starter}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default ProfileDetail
