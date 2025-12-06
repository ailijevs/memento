import { useMemo, useState } from 'react'
import '../styles/events.css'
import type { Event } from '../types/event'

type EventsProps = {
  onSelectEvent: (event: Event) => void
}

const events: Event[] = [
  {
    id: 'today-1',
    name: 'Memento App Live Demo',
    location: 'Potter Engineering Center',
    startTime: '1:30 PM',
    endTime: '2:30 PM',
    description: 'CDR presentation of the Memento prototype with live demo.',
    isToday: true,
  },
  {
    id: 'today-2',
    name: 'Tech Alumni Networking',
    location: 'Seattle - Pioneer Square',
    startTime: '6:00 PM',
    endTime: '8:30 PM',
    description: 'Connect with product, design, and engineering alumni.',
    isToday: true,
  },
  {
    id: 'today-3',
    name: 'Purdue Industrial Roundtable',
    location: 'Memorial Mall',
    startTime: '3:30 PM',
    endTime: '5:30 PM',
    description:
      'Flagship Purdue career fair connecting students with industry leaders across engineering and tech.',
    isToday: true,
  },
  {
    id: 'upcoming-1',
    name: 'AI Safety Salon',
    location: 'SF - Hayes Valley',
    startTime: 'Tomorrow, 5:30 PM',
    endTime: '7:00 PM',
    description: 'Small-group discussion on frontier model safety.',
    isToday: false,
  },
  {
    id: 'upcoming-2',
    name: 'Design Systems Roundtable',
    location: 'NYC - Soho',
    startTime: 'Fri, 4:00 PM',
    endTime: '6:00 PM',
    description: 'Deep dive on scaling design systems across teams.',
    isToday: false,
  },
  {
    id: 'upcoming-3',
    name: 'Healthcare Innovation Summit',
    location: 'Boston - Seaport',
    startTime: 'Sat, 9:00 AM',
    endTime: '1:00 PM',
    description: 'Panels on AI diagnostics, regulatory paths, and funding.',
    isToday: false,
  },
]

const DiagonalArrow = () => (
  <svg
    className="arrow-icon"
    viewBox="0 0 24 24"
    aria-hidden="true"
    focusable="false"
  >
    <path
      d="M6 18 11.5 12.5M12.5 11.5 18 6M14 6h4v4M6 14v4h4"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

const EventsPage = ({ onSelectEvent }: EventsProps) => {
  const [query, setQuery] = useState('')

  const parseTimeToMinutes = (time: string) => {
    const match = time.match(/(\d{1,2}):(\d{2})\s*(AM|PM)/i)
    if (!match) return Number.MAX_SAFE_INTEGER
    const [, rawHour, rawMin, period] = match
    let hour = parseInt(rawHour, 10) % 12
    const minutes = parseInt(rawMin, 10)
    if (period.toUpperCase() === 'PM') {
      hour += 12
    }
    return hour * 60 + minutes
  }

  const filtered = useMemo(() => {
    if (!query.trim()) return events
    const q = query.toLowerCase()
    return events.filter(
      (event) =>
        event.name.toLowerCase().includes(q) ||
        event.location.toLowerCase().includes(q)
    )
  }, [query])

  const handleSelect = (event: Event) => {
    onSelectEvent(event)
  }

  const renderList = (list: Event[], title: string) => (
    <section className="event-section">
      <div className="section-header">
        <h2>{title}</h2>
        <span className="pill">{list.length} events</span>
      </div>
      <div className="event-list">
        {list.map((event) => (
          <article
            key={event.id}
            className="event-card"
            onClick={() => handleSelect(event)}
          >
            <div className="event-body">
              <div className="event-times">
                <span className="event-time">{event.startTime}</span>
                <span className="event-time to">{event.endTime}</span>
              </div>
              <div className="event-details">
                <h3>{event.name}</h3>
                <p className="event-location">{event.location}</p>
                {event.description && (
                  <p className="event-description">{event.description}</p>
                )}
              </div>
              <div className="event-cta" aria-hidden="true">
                <DiagonalArrow />
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  )

  const filteredToday = filtered.filter((event) => event.isToday)
  const filteredUpcoming = filtered.filter((event) => !event.isToday)

  const sortedToday = useMemo(
    () =>
      [...filteredToday].sort(
        (a, b) => parseTimeToMinutes(a.startTime) - parseTimeToMinutes(b.startTime)
      ),
    [filteredToday]
  )

  return (
    <div className="events-shell">
      <header className="events-hero">
        <p className="eyebrow">Live today</p>
        <h1>Choose your event</h1>
        <p className="hero-subtitle">
          Find the room you&apos;re in, then tap to see your connections.
        </p>
        <div className="search-bar">
          <input
            type="search"
            placeholder="Search events by name or location"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </header>

      {renderList(sortedToday, 'Happening today')}

      <section className="event-section">
        <div className="section-header">
          <h2>Coming up</h2>
        </div>
        <div className="event-grid">
          {filteredUpcoming.slice(0, 3).map((event) => (
            <article
              key={event.id}
              className="event-card compact"
              onClick={() => handleSelect(event)}
            >
              <div className="event-body">
                <div>
                  <div className="event-time to">{event.startTime}</div>
                  <h3>{event.name}</h3>
                  <p className="event-location">{event.location}</p>
                </div>
                <div className="event-cta" aria-hidden="true">
                  <DiagonalArrow />
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}

export default EventsPage
