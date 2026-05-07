import React from 'react';
import { Home, Menu, Users } from 'lucide-react';
import ThemeToggle from './ThemeToggle';
import { useAppConfig } from '../contexts/AppConfigContext';

/**
 * Shared floating header used on every page so the app feels like one surface.
 *
 * Props:
 *   currentPage: 'home' | 'chat' | 'canvas'
 *   onNavigateToHome, onNavigateToChat, onNavigateToCanvas: navigation callbacks
 *     (onNavigateToCanvas may receive 'insights' | 'workspace' to deep-link a view)
 *   onMobileMenu?: () => void  — when present, shows the mobile menu button
 *   children?: ReactNode        — extra controls slotted between the tabs and the theme toggle
 */
const AppHeader = ({
  currentPage = 'home',
  onNavigateToHome,
  onNavigateToChat,
  onNavigateToCanvas,
  onMobileMenu,
  children,
}) => {
  const { config, resolveIcon } = useAppConfig();
  const BrandIcon = resolveIcon ? resolveIcon('Users') : Users;

  const goToCanvas = (view) => {
    if (onNavigateToCanvas) onNavigateToCanvas(view);
  };

  const isOnHome = currentPage === 'home';
  const isOnChat = currentPage === 'chat';
  const isOnCanvas = currentPage === 'canvas';

  return (
    <header className="floating-header app-header">
      <div className="header-left">
        {onMobileMenu && (
          <button className="mobile-menu-button" onClick={onMobileMenu}>
            <Menu size={20} />
          </button>
        )}
        <button
          className="modern-home-btn"
          onClick={onNavigateToHome}
          title="Home"
          disabled={isOnHome}
          aria-disabled={isOnHome}
        >
          <Home size={20} />
        </button>
        <div className="header-brand">
          <div className="brand-icon">
            <BrandIcon size={24} />
          </div>
          <div className="brand-text">
            <h1>{config?.app?.title || 'Advisory'}</h1>
            <p>{config?.app?.subtitle || 'AI-Powered Guidance'}</p>
          </div>
        </div>
      </div>

      <div className="canvas-tabs chat-view-tabs">
        <button className={`tab ${isOnChat ? 'active' : ''}`} onClick={onNavigateToChat}>Chat</button>
        <button className={`tab ${isOnCanvas ? 'active' : ''}`} onClick={() => goToCanvas('insights')}>Insights</button>
        <button className={`tab ${isOnCanvas ? 'active' : ''}`} onClick={() => goToCanvas('workspace')}>Workspace</button>
      </div>

      <div className="header-right">
        {children}
        <ThemeToggle />
      </div>
    </header>
  );
};

export default AppHeader;
