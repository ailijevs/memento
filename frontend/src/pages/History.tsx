import { useMemo, useState } from 'react'
import ProfileDetail from '../components/ProfileDetail'
import BottomNav from '../components/BottomNav'
import { DiagonalDoubleArrowIcon } from '../components/icons'
import '../styles/events.css'
import type { Connection } from '../types/connection'

type HistoryProps = {
  onHome: () => void
  onFavorites: () => void
  onProfile: () => void
  onHistory: () => void
}

type EncounterGroup = {
  id: string
  eventName: string
  date: string
  connections: Connection[]
}

const encounterHistory: EncounterGroup[] = [
  {
    id: 'event-mentra',
    eventName: 'Memento App Live Demo',
    date: 'Today, 1:30 PM',
    connections: [
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
        conversationStarters: [],
      },
    ],
  },
  {
    id: 'event-alumni',
    eventName: 'Tech Alumni Networking',
    date: 'Today, 6:00 PM',
    connections: [
      {
        id: 2,
        name: 'Marcus Johnson',
        role: 'ML Engineer @ OpenAI',
        summary:
          'Fellow Boilermaker who also majored in ECE. Marcus plays basketball and is passionate about AI safety.',
        matchScore: 88,
        location: 'San Francisco, CA',
        sharedInterests: ['Purdue University', 'ECE', 'Basketball', 'AI'],
        avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Marcus',
        detectedPhoto: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Marcus2',
        professionalSummary:
          'Machine learning engineer specializing in large language models and AI alignment. Published 12+ papers on transformer architectures and reinforcement learning. Contributed to GPT-4 safety improvements.',
        experience: [
          'ML Engineer @ OpenAI (2022-Present) - Working on GPT model safety and alignment',
          'Research Scientist @ DeepMind (2019-2022) - Developed novel RL algorithms',
          'ML Intern @ Facebook AI (2018) - Computer vision research for content moderation',
        ],
        education:
          'MS Computer Science, Stanford University (2019)\nBS Electrical & Computer Engineering, Purdue University (2017)',
        skills: ['PyTorch', 'TensorFlow', 'Transformers', 'RLHF', 'Python', 'C++', 'Research'],
        linkedin: 'marcus-johnson',
        twitter: '@marcusml',
        conversationStarters: [],
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
        conversationStarters: [],
      },
    ],
  },
]

const HistoryPage = ({ onHome, onFavorites, onProfile, onHistory }: HistoryProps) => {
  const [selectedProfile, setSelectedProfile] = useState<Connection | null>(null)
  const [query, setQuery] = useState('')
  const [eventFilter, setEventFilter] = useState<string>('all')

  const eventOptions = useMemo(
    () => ['all', ...encounterHistory.map((g) => g.eventName)],
    []
  )

  const filtered = useMemo(() => {
    const base =
      eventFilter === 'all'
        ? encounterHistory
        : encounterHistory.filter((g) => g.eventName === eventFilter)

    if (!query.trim()) return base
    const q = query.toLowerCase()
    return base
      .map((group) => ({
        ...group,
        connections: group.connections.filter(
          (connection) =>
            connection.name.toLowerCase().includes(q) ||
            connection.role.toLowerCase().includes(q) ||
            connection.location.toLowerCase().includes(q)
        ),
      }))
      .filter((group) => group.connections.length > 0)
  }, [query, eventFilter])

  return (
    <div className="app-shell">
      <header className="hero">
        <p className="eyebrow">Encounter history</p>
        <h1>Past connections</h1>
        <p className="hero-subtitle">
          Review everyone you’ve seen, organized by event.
        </p>
        <div className="search-bar history-filters">
          <input
            type="search"
            placeholder="Search by name, role, or location"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <select
            value={eventFilter}
            onChange={(e) => setEventFilter(e.target.value)}
            aria-label="Filter by event"
          >
            {eventOptions.map((opt) => (
              <option key={opt} value={opt}>
                {opt === 'all' ? 'All events' : opt}
              </option>
            ))}
          </select>
        </div>
      </header>

      <div className="connections">
        {filtered.map((group) => (
          <section key={group.id} className="event-section">
            <div className="section-header">
              <h2>{group.eventName}</h2>
              <span className="pill">{group.date}</span>
            </div>

            {group.connections.map((connection) => (
              <article
                className="connection-card"
                key={`${group.id}-${connection.id}`}
                onClick={() => setSelectedProfile(connection)}
              >
                <div className="card-gradient">
                  <div className="card-body">
                    <div className="connection-cta" aria-hidden="true">
                      <DiagonalDoubleArrowIcon />
                    </div>
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
        ))}
      </div>

      {selectedProfile && (
        <ProfileDetail
          profile={selectedProfile}
          onClose={() => setSelectedProfile(null)}
        />
      )}

      <BottomNav
        onHome={onHome}
        onProfile={onProfile}
        onFavorites={onFavorites}
        onHistory={onHistory}
        active="history"
      />
    </div>
  )
}

export default HistoryPage
