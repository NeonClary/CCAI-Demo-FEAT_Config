import React, { useState, useEffect, useCallback, useRef } from 'react';
import { ThemeProvider } from './contexts/ThemeContext';
import { AppConfigProvider } from './contexts/AppConfigContext';
import { VoiceStatusProvider } from './contexts/VoiceStatusContext';
import HomePage from './pages/HomePage';
import ChatPage from './pages/ChatPage';
import AuthPage from './pages/AuthPage';
import CanvasPage from './pages/CanvasPage';
import UserGuidePage from './pages/UserGuidePage';
import Tutorial, { TutorialButton } from './components/Tutorial';
import VoiceToast from './components/VoiceToast';
import './styles/components.css';

function App() {
  const [currentView, setCurrentView] = useState('home');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [authToken, setAuthToken] = useState(null);
  const activeTimerHandlesRef = useRef({});

  const parseDueAtMs = useCallback((dueAtRaw) => {
    if (!dueAtRaw || typeof dueAtRaw !== 'string') return NaN;
    const trimmed = dueAtRaw.trim();
    // Backend may send naive UTC timestamps; force UTC when no offset is present.
    const hasOffset = /([zZ]|[+-]\d{2}:\d{2})$/.test(trimmed);
    const normalized = hasOffset ? trimmed : `${trimmed}Z`;
    return new Date(normalized).getTime();
  }, []);

  const notifyTimerComplete = useCallback(() => {
    if (currentView === 'chat') {
      window.dispatchEvent(new CustomEvent('ccai-timer-complete'));
      return;
    }
    window.alert('⏰ Timer complete.');
  }, [currentView]);

  const registerTimer = useCallback((timerEvent) => {
    if (timerEvent?.persona_id !== 'timer_advisor') return;
    if (!timerEvent?.timer_due_at || !timerEvent?.timer_seconds) return;

    const timerKey = timerEvent.timer_id || `${timerEvent.timer_due_at}_${timerEvent.timer_seconds}`;
    const dueAtMs = parseDueAtMs(timerEvent.timer_due_at);
    if (!Number.isFinite(dueAtMs)) return;

    if (activeTimerHandlesRef.current[timerKey]) {
      clearTimeout(activeTimerHandlesRef.current[timerKey]);
      delete activeTimerHandlesRef.current[timerKey];
    }

    const remainingMs = dueAtMs - Date.now();
    if (remainingMs <= 0) {
      notifyTimerComplete();
      return;
    }

    const timeoutHandle = setTimeout(() => {
      notifyTimerComplete();
      delete activeTimerHandlesRef.current[timerKey];
    }, remainingMs);

    activeTimerHandlesRef.current[timerKey] = timeoutHandle;
  }, [notifyTimerComplete, parseDueAtMs]);

  // Check for existing authentication on app start
  useEffect(() => {
    const token = localStorage.getItem('authToken');
    const userData = localStorage.getItem('user');
    
    if (token && userData) {
      try {
        const parsedUser = JSON.parse(userData);
        const validateToken = async () => {
          try {
            const apiBaseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8001';
            const response = await fetch(`${apiBaseUrl}/api/users/me/profile`, {
              headers: { Authorization: `Bearer ${token}` },
            });

            if (!response.ok) {
              localStorage.removeItem('authToken');
              localStorage.removeItem('user');
              return;
            }

            setAuthToken(token);
            setUser(parsedUser);
            setIsAuthenticated(true);
            setCurrentView('chat');
          } catch (error) {
            // Keep the saved token on transient network failure.
            setAuthToken(token);
            setUser(parsedUser);
            setIsAuthenticated(true);
            setCurrentView('chat');
          }
        };

        validateToken();
      } catch (error) {
        // Clear invalid data
        localStorage.removeItem('authToken');
        localStorage.removeItem('user');
      }
    }
  }, []);

  const navigateToAuth = () => {
    setCurrentView('auth');
  };

  const navigateToCanvas = () => {
    setCurrentView('canvas');
  };

  const navigateToChat = () => {
    setCurrentView('chat');
  };

  const navigateToGuide = () => {
    setCurrentView('guide');
  };

  const [showTutorial, setShowTutorial] = useState(false);
  const [tutorialDismissed, setTutorialDismissed] = useState(
    () => localStorage.getItem('tutorialDismissed') === 'true'
  );
  const openTutorial = useCallback(() => setShowTutorial(true), []);
  const closeTutorial = useCallback(() => {
    setShowTutorial(false);
    setTutorialDismissed(true);
    localStorage.setItem('tutorialDismissed', 'true');
  }, []);

  

  const navigateToHome = () => {
    setCurrentView('home');
  };

  const handleAuthSuccess = (userData, token) => {
    setUser(userData);
    setAuthToken(token);
    setIsAuthenticated(true);
    setCurrentView('chat');
  };

  const handleSignOut = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('user');
    setUser(null);
    setAuthToken(null);
    setIsAuthenticated(false);
    setCurrentView('home');
  };

  useEffect(() => {
    return () => {
      Object.values(activeTimerHandlesRef.current).forEach((h) => clearTimeout(h));
      activeTimerHandlesRef.current = {};
    };
  }, []);

  return (
    <AppConfigProvider>
      <ThemeProvider>
        <div className="App">
          {currentView === 'home' && (
            <HomePage
              onNavigateToChat={isAuthenticated ? navigateToChat : navigateToAuth}
              isAuthenticated={isAuthenticated}
            />
          )}
          {currentView === 'auth' && (
            <AuthPage onAuthSuccess={handleAuthSuccess} />
          )}
          {currentView === 'canvas' && isAuthenticated && (
            <CanvasPage 
              user={user}
              authToken={authToken}
              onNavigateToChat={navigateToChat}
              onSignOut={handleSignOut}
            />
          )}
          {currentView === 'guide' && isAuthenticated && (
            <UserGuidePage onNavigateToChat={navigateToChat} />
          )}
          {currentView === 'chat' && isAuthenticated && (
            <VoiceStatusProvider authToken={authToken}>
              <ChatPage 
                user={user}
                authToken={authToken}
                onNavigateToHome={navigateToHome}
                onNavigateToCanvas={navigateToCanvas}
                onNavigateToGuide={navigateToGuide}
                onSignOut={handleSignOut}
                onOpenTutorial={openTutorial}
                onRegisterTimer={registerTimer}
              />
              <VoiceToast />
            </VoiceStatusProvider>
          )}

          {/* Tutorial — rendered at app level so it persists across views */}
          {isAuthenticated && (
            <>
              <Tutorial active={showTutorial} onClose={closeTutorial} />
              {!showTutorial && !tutorialDismissed && (
                <TutorialButton onClick={openTutorial} />
              )}
            </>
          )}
        </div>
      </ThemeProvider>
    </AppConfigProvider>
  );
}

export default App;
