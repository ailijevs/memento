import '../styles/nav.css'
import { HeartIcon, HistoryIcon, HomeIcon, ProfileIcon } from './icons'

type BottomNavProps = {
  onHome: () => void
  onFavorites?: () => void
  onProfile?: () => void
  active?: 'home' | 'favorites' | 'history' | 'profile'
}

const BottomNav = ({ onHome, onFavorites, onProfile, active }: BottomNavProps) => {
  return (
    <nav className="bottom-nav" aria-label="Primary">
      <button
        type="button"
        className={`nav-item ${active === 'home' ? 'active' : ''}`}
        onClick={onHome}
      >
        <HomeIcon />
      </button>
      <button
        type="button"
        className={`nav-item ${onFavorites ? '' : 'nav-disabled'} ${
          active === 'favorites' ? 'active' : ''
        }`}
        aria-disabled={!onFavorites}
        onClick={onFavorites}
      >
        <HeartIcon />
      </button>
      <button type="button" className="nav-item nav-disabled" aria-disabled="true">
        <HistoryIcon />
      </button>
      <button
        type="button"
        className={`nav-item ${onProfile ? '' : 'nav-disabled'} ${
          active === 'profile' ? 'active' : ''
        }`}
        aria-disabled={!onProfile}
        onClick={onProfile}
      >
        <ProfileIcon />
      </button>
    </nav>
  )
}

export default BottomNav
