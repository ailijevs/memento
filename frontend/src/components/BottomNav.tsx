import '../styles/nav.css'

type BottomNavProps = {
  onHome: () => void
}

const HomeIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    <path
      d="M5 10.5 12 4l7 6.5V20a1 1 0 0 1-1 1h-4.5v-5.5h-3V21H6a1 1 0 0 1-1-1z"
      stroke="currentColor"
      strokeWidth="2"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

const HeartIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    <path
      d="M12 20s-6.5-4.35-8.5-8A4.75 4.75 0 0 1 12 6.5 4.75 4.75 0 0 1 20.5 12c-2 3.65-8.5 8-8.5 8Z"
      stroke="currentColor"
      strokeWidth="2"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

const HistoryIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    <path
      d="M4 4v5h5M12 8v5l3 2M4.9 19.1A9 9 0 1 0 6.2 6.2"
      stroke="currentColor"
      strokeWidth="2"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

const ProfileIcon = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    <path
      d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4Z"
      stroke="currentColor"
      strokeWidth="2"
      fill="none"
    />
    <path
      d="M6 20a6 6 0 0 1 12 0"
      stroke="currentColor"
      strokeWidth="2"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

const BottomNav = ({ onHome }: BottomNavProps) => {
  return (
    <nav className="bottom-nav" aria-label="Primary">
      <button type="button" className="nav-item" onClick={onHome}>
        <HomeIcon />
      </button>
      <button type="button" className="nav-item nav-disabled" aria-disabled="true">
        <HeartIcon />
      </button>
      <button type="button" className="nav-item nav-disabled" aria-disabled="true">
        <HistoryIcon />
      </button>
      <button type="button" className="nav-item nav-disabled" aria-disabled="true">
        <ProfileIcon />
      </button>
    </nav>
  )
}

export default BottomNav
