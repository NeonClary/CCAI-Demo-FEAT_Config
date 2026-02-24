import React, { useState, useEffect, useCallback } from 'react';
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

  // Check for existing authentication on app start
  useEffect(() => {
    const token = localStorage.getItem('authToken');
    const userData = localStorage.getItem('user');
    
    if (token && userData) {
      try {
        const parsedUser = JSON.parse(userData);
        setAuthToken(token);
        setUser(parsedUser);
        setIsAuthenticated(true);
        setCurrentView('chat');
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
