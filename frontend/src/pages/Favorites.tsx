import { useMemo, useState } from 'react'
import ProfileDetail from '../components/ProfileDetail'
import BottomNav from '../components/BottomNav'
import { DiagonalDoubleArrowIcon, HeartIcon } from '../components/icons'
import type { Connection } from '../types/connection'

type FavoritesProps = {
  onHome: () => void
  onProfile: () => void
  onFavorites: () => void
}

// Mock favorites list for now (could be driven by real likes)
const favoriteConnections: Connection[] = [
  {
    id: 1,
    name: 'Sarah Chen',
    role: 'Senior Product Manager @ Google',
    summary:
      'You both studied CS at Purdue and worked in product management. Sarah loves hiking and recently moved to Seattle.',
    matchScore: 92,
    location: 'Seattle, WA',
    sharedInterests: ['Purdue University', 'Product Management', 'Hiking'],
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Sarah',
    detectedPhoto: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Sarah2',
    professionalSummary:
      'Product leader with 8+ years of experience building consumer-facing products at scale. Passionate about user-centered design and data-driven decision making. Led multiple 0-to-1 product launches reaching millions of users.',
    experience: [
      'Senior Product Manager @ Google (2021-Present) - Leading Maps discovery features',
      'Product Manager @ Uber (2018-2021) - Built rider safety features used by 50M+ users',
      'APM @ Microsoft (2016-2018) - Worked on Office 365 collaboration tools',
    ],
    education: 'BS Computer Science, Purdue University (2016)',
    skills: ['Product Strategy', 'User Research', 'A/B Testing', 'SQL', 'Figma', 'Agile', 'Leadership'],
    linkedin: 'sarah-chen',
    twitter: '@sarahchen',
    conversationStarters: [
      "Hey Sarah! I saw you worked on Google Maps - what's the most surprising thing you learned about how people navigate?",
      'You hiked the Pacific Northwest recently, right? Any hidden trails you would recommend?',
      'I noticed you went from APM to PM to Senior PM - what was the biggest mindset shift at each level?',
    ],
  },
  {
    id: 5,
    name: 'Priya Patel',
    role: 'UX Design Lead @ Figma',
    summary:
      'Both passionate about design and user experience. Priya teaches yoga and organizes design workshops.',
    matchScore: 91,
    location: 'New York, NY',
    sharedInterests: ['UX Design', 'Teaching', 'Yoga'],
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Priya',
    detectedPhoto: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Priya2',
    professionalSummary:
      'Design leader with expertise in building design systems and collaborative tools. Advocate for accessibility and inclusive design practices. Regular speaker at design conferences worldwide.',
    experience: [
      'Design Lead @ Figma (2020-Present) - Leading design systems team',
      'Senior Product Designer @ Airbnb (2017-2020) - Built host dashboard and booking flow',
      'Product Designer @ Dropbox (2015-2017) - Worked on Paper and file sharing features',
    ],
    education: 'MFA Interaction Design, School of Visual Arts (2015)\nBA Psychology, NYU (2013)',
    skills: ['Figma', 'Design Systems', 'Prototyping', 'User Research', 'Accessibility', 'Facilitation'],
    linkedin: 'priya-patel',
    instagram: '@priya.designs',
    conversationStarters: [
      "Priya! Figma's design system is legendary - how do you balance consistency with giving teams creative freedom?",
      "You teach design workshops - what's the most common misconception junior designers have about UX?",
      "Do you find any parallels between yoga and design thinking? Like flow states or something?",
    ],
  },
]

const FavoritesPage = ({ onHome, onProfile, onFavorites }: FavoritesProps) => {
  const [selectedProfile, setSelectedProfile] = useState<Connection | null>(null)
  const [query, setQuery] = useState('')

  const filtered = useMemo(() => {
    if (!query.trim()) return favoriteConnections
    const q = query.toLowerCase()
    return favoriteConnections.filter(
      (connection) =>
        connection.name.toLowerCase().includes(q) ||
        connection.role.toLowerCase().includes(q) ||
        connection.location.toLowerCase().includes(q)
    )
  }, [query])

  return (
    <div className="app-shell">
      <header className="hero">
        <p className="eyebrow">Favorites</p>
        <h1>Saved profiles</h1>
        <p className="hero-subtitle">Quickly jump back to people you liked.</p>
        <div className="search-bar">
          <input
            type="search"
            placeholder="Search favorites by name, role, or location"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </header>

      <section className="connections">
        {filtered.map((connection) => (
          <article
            className="connection-card"
            key={connection.id}
            onClick={() => setSelectedProfile(connection)}
          >
            <div className="card-gradient">
              <div className="card-body">
                <div className="connection-cta" aria-hidden="true">
                  <DiagonalDoubleArrowIcon />
                </div>
                <button
                  type="button"
                  className="favorite-btn"
                  aria-label="Unlike connection"
                  onClick={(e) => e.stopPropagation()}
                >
                  <HeartIcon />
                </button>
                <div className="avatar" aria-hidden="true">
                  <img
                    src={connection.avatar}
                    alt={connection.name}
                    className="avatar-img"
                  />
                </div>

                <div className="profile-details">
                  <div>
                    <h2>{connection.name}</h2>
                    <p className="role">{connection.role}</p>
                  </div>
                  <p className="summary">{connection.summary}</p>
                  <div className="meta">
                    <span>{connection.location}</span>
                    <ul>
                      {connection.sharedInterests.map((interest) => (
                        <li key={`${connection.id}-${interest}`}>{interest}</li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="match-pill">
                  <span>{connection.matchScore}%</span>
                </div>
              </div>
            </div>
          </article>
        ))}
      </section>

      {selectedProfile && (
        <ProfileDetail
          profile={selectedProfile}
          onClose={() => setSelectedProfile(null)}
        />
      )}

      <BottomNav onHome={onHome} onProfile={onProfile} onFavorites={onFavorites} active="favorites" />
    </div>
  )
}

export default FavoritesPage
