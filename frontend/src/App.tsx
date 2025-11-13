import './App.css'

type Connection = {
  id: number
  name: string
  role: string
  summary: string
  matchScore: number
  location: string
  sharedInterests: string[]
}

const connections: Connection[] = [
  {
    id: 1,
    name: 'Marty Singh',
    role: 'Consultant',
    summary:
      'You both went to Purdue University and studied Computer Engineering. Marty currently lives in the Bay Area and also plays Soccer.',
    matchScore: 88,
    location: 'Bay Area, CA',
    sharedInterests: ['Purdue University', 'Computer Engineering', 'Soccer'],
  },
  {
    id: 2,
    name: 'Marty Singh',
    role: 'Consultant',
    summary:
      'You both went to Purdue University and studied Computer Engineering. Marty currently lives in the Bay Area and also plays Soccer.',
    matchScore: 88,
    location: 'Bay Area, CA',
    sharedInterests: ['Purdue University', 'Computer Engineering', 'Soccer'],
  },
  {
    id: 3,
    name: 'Marty Singh',
    role: 'Consultant',
    summary:
      'You both went to Purdue University and studied Computer Engineering. Marty currently lives in the Bay Area and also plays Soccer.',
    matchScore: 88,
    location: 'Bay Area, CA',
    sharedInterests: ['Purdue University', 'Computer Engineering', 'Soccer'],
  },
]

const App = () => {
  return (
    <div className="app-shell">
      <header className="hero">
        <p className="eyebrow">Live match from Mentra Glass</p>
        <h1>Memento</h1>
        <p className="hero-subtitle">
          Know someone before you say hello. Profiles update instantly as you
          scan the room.
        </p>
      </header>

      <section className="connections">
        {connections.map((connection) => (
          <article className="connection-card" key={connection.id}>
            <div className="card-gradient">
              <div className="card-body">
                <div className="avatar" aria-hidden="true">
                  <div className="avatar-blur" />
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
    </div>
  )
}

export default App
