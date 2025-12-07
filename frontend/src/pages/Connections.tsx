import { useState } from 'react'
import ProfileDetail from '../components/ProfileDetail'
import BottomNav from '../components/BottomNav'
import type { Connection } from '../types/connection'
import { BackIcon, DiagonalDoubleArrowIcon, HeartIcon } from '../components/icons'

type ConnectionsProps = {
  onHome: () => void
  onProfile: () => void
  onFavorites?: () => void
  onHistory?: () => void
  onBack?: () => void
  activeNav?: 'home' | 'favorites' | 'history' | 'profile'
}

const connections: Connection[] = [
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
    skills: [
      'Product Strategy',
      'User Research',
      'A/B Testing',
      'SQL',
      'Figma',
      'Agile',
      'Leadership',
    ],
    linkedin: 'sarah-chen',
    twitter: '@sarahchen',
    conversationStarters: [
      'Hey Sarah! I saw you worked on Google Maps - what\'s the most surprising thing you learned about how people navigate?',
      'You hiked the Pacific Northwest recently, right? Any hidden trails you\'d recommend?',
      'I noticed you went from APM to PM to Senior PM - what was the biggest mindset shift at each level?',
    ],
  },
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
    skills: [
      'PyTorch',
      'TensorFlow',
      'Transformers',
      'RLHF',
      'Python',
      'C++',
      'Research',
    ],
    linkedin: 'marcus-johnson',
    twitter: '@marcusml',
    conversationStarters: [
      'Marcus! ECE at Purdue too - did you have Professor Bouman? How did that shape your path to AI?',
      'What\'s it like working on GPT safety at OpenAI? Any ethical dilemmas that keep you up at night?',
      'I heard there are great pickup basketball games in SF - do you play at Mission Dolores or somewhere else?',
    ],
  },
  {
    id: 3,
    name: 'Emily Rodriguez',
    role: 'Venture Capitalist @ a16z',
    summary:
      'Connected through Purdue alumni network. Emily invests in enterprise SaaS and also enjoys rock climbing.',
    matchScore: 85,
    location: 'Menlo Park, CA',
    sharedInterests: ['Purdue Alumni', 'Startups', 'Rock Climbing'],
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Emily',
    detectedPhoto: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Emily2',
    professionalSummary:
      'Early-stage investor focused on enterprise infrastructure and developer tools. Led investments in 15+ companies with 3 unicorn exits. Former founder of a B2B SaaS startup acquired by Salesforce.',
    experience: [
      'General Partner @ Andreessen Horowitz (2020-Present) - Leading enterprise investments',
      'Principal @ Sequoia Capital (2017-2020) - Focused on seed and Series A deals',
      'Founder & CEO @ CloudSync (2014-2017) - B2B collaboration platform (acquired by Salesforce)',
    ],
    education: 'MBA, Harvard Business School (2014)\nBS Management, Purdue University (2010)',
    skills: [
      'Venture Capital',
      'Due Diligence',
      'Pitch Analysis',
      'Portfolio Management',
      'Networking',
      'SaaS',
    ],
    linkedin: 'emily-rodriguez',
    instagram: '@emily.climbs',
    conversationStarters: [
      'Emily, congrats on the Salesforce exit! What\'s the #1 thing you look for in founders now that you\'re on the other side?',
      'I see you invest in developer tools - what\'s the most underrated dev tool category right now?',
      'Do you climb at Touchstone in the Bay? I\'ve been trying to break into V6s outdoors - any advice?',
    ],
  },
  {
    id: 4,
    name: 'David Park',
    role: 'Startup Founder @ HealthTech Co',
    summary:
      'Both interested in healthcare innovation. David is building an AI diagnostics platform and loves tennis.',
    matchScore: 79,
    location: 'Boston, MA',
    sharedInterests: ['Healthcare Tech', 'AI', 'Tennis'],
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=David',
    detectedPhoto: 'https://api.dicebear.com/7.x/avataaars/svg?seed=David2',
    professionalSummary:
      'Serial entrepreneur building AI-powered healthcare solutions. Currently working on FDA-approved diagnostic tools for early cancer detection. Previously exited two startups in medical devices.',
    experience: [
      'Founder & CEO @ MedAI Diagnostics (2021-Present) - AI-powered pathology analysis',
      'Co-founder @ CardioSense (2017-2021) - Wearable heart monitoring (acquired by Philips)',
      'Engineering Lead @ Johnson & Johnson (2014-2017) - Medical device innovation',
    ],
    education:
      'PhD Biomedical Engineering, MIT (2014)\nBS Bioengineering, UC Berkeley (2009)',
    skills: [
      'Medical Devices',
      'Machine Learning',
      'FDA Regulatory',
      'Fundraising',
      'Team Building',
      'Python',
    ],
    linkedin: 'david-park-md',
    twitter: '@davidparkmd',
    conversationStarters: [
      'David, two successful exits in healthtech - what\'s different about the FDA approval process now versus 5 years ago?',
      'How do you balance innovation speed with the rigorous testing requirements for medical AI?',
      'Tennis in Boston must be tough in winter - do you play at Longwood or have a favorite indoor spot?',
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
    education:
      'MFA Interaction Design, School of Visual Arts (2015)\nBA Psychology, NYU (2013)',
    skills: [
      'Figma',
      'Design Systems',
      'Prototyping',
      'User Research',
      'Accessibility',
      'Facilitation',
    ],
    linkedin: 'priya-patel',
    instagram: '@priya.designs',
    conversationStarters: [
      'Priya! Figma\'s design system is legendary - how do you balance consistency with giving teams creative freedom?',
      'You teach design workshops - what\'s the most common misconception junior designers have about UX?',
      'I\'m curious - do you find any parallels between yoga and design thinking? Like flow states or something?',
    ],
  },
]

const ConnectionsPage = ({
  onHome,
  onProfile,
  activeNav = 'home',
  onFavorites,
  onHistory,
  onBack,
}: ConnectionsProps) => {
  const [selectedProfile, setSelectedProfile] = useState<Connection | null>(
    null
  )

  return (
    <div className="app-shell">
      <header className="hero with-back">
        {onBack && (
          <button className="back-btn" onClick={onBack} aria-label="Back">
            <BackIcon />
          </button>
        )}
        <p className="eyebrow">Live match from Mentra Glass</p>
        <h1>Memento</h1>
        <p className="hero-subtitle">
          Know someone before you say hello. Profiles update instantly as you
          scan the room.
        </p>
      </header>

      <section className="connections">
        {connections.map((connection) => (
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
                aria-label="Favorite connection"
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
                        <li key={`${connection.id}-${interest}`}>
                          {interest}
                        </li>
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

      <BottomNav
        onHome={onHome}
        onProfile={onProfile}
        onFavorites={onFavorites}
        onHistory={onHistory}
        active={activeNav}
      />
    </div>
  )
}

export default ConnectionsPage
