import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Home, MessageCircle, Reply, X, Sparkles, Users, Settings2, FileText , LogOut, Menu} from 'lucide-react';
import EnhancedChatInput from '../components/EnhancedChatInput';
import MessageBubble from '../components/MessageBubble';
import AdvisorCarousel from '../components/AdvisorCarousel';
import ThinkingIndicator from '../components/ThinkingIndicator';
import SuggestionsPanel from '../components/SuggestionsPanel';
import ThemeToggle from '../components/ThemeToggle';
import ProviderDropdown from '../components/ProviderDropdown';
import ExportButton from '../components/ExportButton';
import Sidebar from '../components/Sidebar';
import { useAppConfig } from '../contexts/AppConfigContext';
import { useTheme } from '../contexts/ThemeContext';
import '../styles/ChatPage.css';
import '../styles/EnhancedChatInput.css';
import AdvisorStatusDropdown from '../components/AdvisorStatusDropdown';
import AgentStatusDropdown from '../components/AgentStatusDropdown';
import OnboardingChat from '../components/OnboardingChat';
import ProfileWalkthrough from '../components/ProfileWalkthrough';
import ClearDataModal from '../components/ClearDataModal';
import AccountModal from '../components/AccountModal';

const ChatPage = ({ user, authToken, onNavigateToHome, onNavigateToCanvas, onNavigateToGuide, onSignOut, onOpenTutorial }) => {
  const { config, advisors, agents, allPersonas, getAdvisorColors, getAgentColors, getAllPersonaColors, orchestratorAvatar } = useAppConfig();
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [thinkingAdvisors, setThinkingAdvisors] = useState([]);
  const [collectedInfo, setCollectedInfo] = useState({});
  const [replyingTo, setReplyingTo] = useState(null);
  const [currentProvider, setCurrentProvider] = useState('gemini');
  const [isProviderSwitching, setIsProviderSwitching] = useState(false);
  const [uploadedDocuments, setUploadedDocuments] = useState([]);
  const messagesEndRef = useRef(null);
  const { isDark } = useTheme();

  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [currentSessionTitle, setCurrentSessionTitle] = useState('');
  const [isSavingSession, setIsSavingSession] = useState(false);
  const [isLoadingSession, setIsLoadingSession] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  // Phase 1.1: User avatar
  const [userAvatarId, setUserAvatarId] = useState(() => localStorage.getItem('userAvatarId') || (user?.avatarId ?? null));
  const avatarOptions = config?.app?.user_avatars || [];

  const handleAvatarChange = async (id) => {
    setUserAvatarId(id);
    localStorage.setItem('userAvatarId', id);
    try {
      await fetch(`${process.env.REACT_APP_API_URL}/auth/me`, {
        method: 'PATCH',
        headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ avatarId: id })
      });
    } catch (e) { console.error('Failed to save avatar:', e); }
  };

  // Phase 1.2: Active advisors
  const allAdvisorIds = Object.keys(advisors);
  const [activeAdvisors, setActiveAdvisors] = useState(() => {
    const stored = localStorage.getItem('activeAdvisors');
    if (!stored) return null;
    try {
      const parsed = JSON.parse(stored);
      return Array.isArray(parsed) ? parsed : null;
    } catch { return null; }
  });

  // Prune stale IDs whenever the advisor list changes
  useEffect(() => {
    if (!activeAdvisors) return;
    const valid = activeAdvisors.filter(id => allAdvisorIds.includes(id));
    if (valid.length === 0 || valid.length === allAdvisorIds.length) {
      localStorage.removeItem('activeAdvisors');
      setActiveAdvisors(null);
    } else if (valid.length !== activeAdvisors.length) {
      localStorage.setItem('activeAdvisors', JSON.stringify(valid));
      setActiveAdvisors(valid);
    }
  }, [allAdvisorIds.join(',')]);

  const handleToggleAdvisor = (id) => {
    setActiveAdvisors(prev => {
      const current = prev || allAdvisorIds;
      let next;
      if (current.includes(id)) {
        if (current.length <= 1) return current;
        next = current.filter(a => a !== id);
      } else {
        next = [...current, id];
      }
      localStorage.setItem('activeAdvisors', JSON.stringify(next));
      return next;
    });
  };

  // Phase 1.3: Synthesized mode
  const [synthesizedMode, setSynthesizedMode] = useState(() => localStorage.getItem('synthesizedMode') === 'true');
  const handleToggleSynthesized = () => {
    setSynthesizedMode(prev => {
      localStorage.setItem('synthesizedMode', String(!prev));
      return !prev;
    });
  };

  // Phase 3.2/3.3: Onboarding and profile walkthrough
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [showProfileForm, setShowProfileForm] = useState(false);
  const [showClearData, setShowClearData] = useState(false);
  const [showAccount, setShowAccount] = useState(false);
  const [userProfile, setUserProfile] = useState(null);

  const loadProfile = async () => {
    try {
      const resp = await fetch(`${process.env.REACT_APP_API_URL}/api/users/me/profile`, {
        headers: { 'Authorization': `Bearer ${authToken}` },
      });
      if (resp.ok) setUserProfile(await resp.json());
    } catch (e) { /* ignore */ }
  };

  useEffect(() => { loadProfile(); }, [authToken]);

  // Phase 4.2: Reference search
  const [refSearchPopover, setRefSearchPopover] = useState(null);
  const [refSearchQuery, setRefSearchQuery] = useState('');
  const [refSearchLoading, setRefSearchLoading] = useState(false);

  const handleSearchReferences = async (message) => {
    setRefSearchPopover(message.id);
    setRefSearchLoading(true);
    try {
      const resp = await fetch(`${process.env.REACT_APP_API_URL}/api/search-references`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ statement: message.content?.substring(0, 500) || '' })
      });
      if (resp.ok) {
        const data = await resp.json();
        setRefSearchQuery(data.search_query || message.content?.substring(0, 100));
      } else {
        setRefSearchQuery(message.content?.substring(0, 100) || '');
      }
    } catch {
      setRefSearchQuery(message.content?.substring(0, 100) || '');
    } finally {
      setRefSearchLoading(false);
    }
  };

  

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleMobileMenuToggle = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, thinkingAdvisors]);

  useEffect(() => {
    fetchCurrentProvider();
  }, []);

  const fetchCurrentProvider = async () => {
    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL}/current-provider`);
      if (response.ok) {
        const data = await response.json();
        setCurrentProvider(data.current_provider);
        console.log('Loaded provider:', data.current_provider, 'Available:', data.available_providers);
      }
    } catch (error) {
      console.error('Error fetching current provider:', error);
    }
  };

  

  const handleProviderSwitch = async (newProvider) => {
    if (newProvider === currentProvider || isProviderSwitching) return;

    setIsProviderSwitching(true);
    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL}/switch-provider`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          provider: newProvider
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setCurrentProvider(newProvider);
        
        const switchMessage = {
          id: generateMessageId(),
          type: 'system',
          content: `✨ Switched to ${newProvider.charAt(0).toUpperCase() + newProvider.slice(1)} provider. Your advisors are now ready with the new AI model.`,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, switchMessage]);
      } else {
        const error = await response.json();
        console.error('Failed to switch provider:', error);
        const errorMessage = {
          id: generateMessageId(),
          type: 'error',
          content: `Failed to switch to ${newProvider}: ${error.detail || 'Unknown error'}`,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error('Error switching provider:', error);
      const errorMessage = {
        id: generateMessageId(),
        type: 'error',
        content: `Error switching to ${newProvider}. Please try again.`,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsProviderSwitching(false);
    }
  };

  const generateMessageId = () => {
    return Date.now().toString() + Math.random().toString(36).substr(2, 9);
  };

  const createNewSession = async (firstMessage = null) => {
    try {
      const title = firstMessage 
        ? `${firstMessage.substring(0, 30)}...` 
        : `Chat ${new Date().toLocaleDateString()}`;

      const response = await fetch(`${process.env.REACT_APP_API_URL}/api/chat-sessions`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ title })
      });

      if (response.ok) {
        const newSession = await response.json();
        
        // Update state immediately
        setCurrentSessionId(newSession.id);
        setCurrentSessionTitle(newSession.title);
        
        console.log('MongoDB session created:', newSession.id);
        return newSession.id;
      } else {
        console.error('Failed to create new session');
        return null;
      }
    } catch (error) {
      console.error('Error creating new session:', error);
      return null;
    }
  };


// Load an existing chat session
const loadChatSession = async (sessionId) => {
  if (!sessionId || isLoadingSession) return;
  setIsLoadingSession(true);
  try {
    // Use the new switch-chat endpoint that syncs context
    const response = await fetch(`${process.env.REACT_APP_API_URL}/switch-chat`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        chat_session_id: sessionId
      })
    });

    if (response.ok) {
      const result = await response.json();
      if (result.status === 'success') {
        setCurrentSessionId(sessionId);
        setCurrentSessionTitle(''); // Will be set from MongoDB data
        
        // Load the messages from the synced context
        const formattedMessages = result.context.messages.map(msg => ({
          ...msg,
          timestamp: new Date(msg.timestamp),
          persona_id: msg.persona_id || msg.advisor || msg.advisorId
        }));
        
        setMessages(formattedMessages);
        setReplyingTo(null);
        setThinkingAdvisors([]);
        
        // Also get the session title from MongoDB
        const sessionResponse = await fetch(`${process.env.REACT_APP_API_URL}/api/chat-sessions/${sessionId}`, {
          headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json'
          }
        });
        if (sessionResponse.ok) {
          const sessionData = await sessionResponse.json();
          setCurrentSessionTitle(sessionData.title);
        }
      }
    }
  } catch (error) {
    console.error('Error loading session:', error);
  } finally {
    setIsLoadingSession(false);
  }
};

// Save a message to the current session
const saveMessageToSession = async (message) => {
  if (!currentSessionId || !authToken) return;

  try {
    await fetch(`${process.env.REACT_APP_API_URL}/api/chat-sessions/${currentSessionId}/messages`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        session_id: currentSessionId,
        message: {
          ...message,
          timestamp: message.timestamp.toISOString()
        }
      })
    });
  } catch (error) {
    console.error('Error saving message to session:', error);
  }
};

// Update session title based on first message
const updateSessionTitle = async (sessionId, newTitle) => {
  if (!sessionId || !authToken) return;

  try {
    await fetch(`${process.env.REACT_APP_API_URL}/api/chat-sessions/${sessionId}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ title: newTitle })
    });
    setCurrentSessionTitle(newTitle);
  } catch (error) {
    console.error('Error updating session title:', error);
  }
};

// Handle selecting a session from sidebar
const handleSelectSession = async (sessionId) => {
  if (sessionId === currentSessionId) return;
  await loadChatSession(sessionId);
};

// Handle creating new chat from sidebar
const handleNewChat = async (sessionId = null) => {
  if (sessionId) {
    // Loading existing session
    await loadChatSession(sessionId);
    return; // Return early for existing session loading
  } else {
    // Creating completely new chat with fresh context
    try {
      // Step 1: Reset memory session
      const response = await fetch(`${process.env.REACT_APP_API_URL}/new-chat`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          title: `Chat ${new Date().toLocaleDateString()}`
        })
      });

      if (response.ok) {
        const result = await response.json();
        if (result.status === 'success') {
          // Step 2: Immediately create MongoDB session
          const newSessionId = await createNewSession(`Chat ${new Date().toLocaleDateString()}`);
          
          if (newSessionId) {
            // Reset all state to fresh with the new session
            setMessages([]);
            setCurrentSessionId(newSessionId); // Set the new session ID immediately
            setCurrentSessionTitle(`Chat ${new Date().toLocaleDateString()}`);
            setReplyingTo(null);
            setThinkingAdvisors([]);
            setUploadedDocuments([]);
            
            console.log('New chat created with MongoDB session:', newSessionId);
            
            // Wait a bit to ensure state has updated
            await new Promise(resolve => setTimeout(resolve, 100));
            return newSessionId; // Return the session ID for the sidebar
          } else {
            throw new Error('Failed to create MongoDB session');
          }
        } else {
          throw new Error('Failed to create memory session');
        }
      } else {
        throw new Error(`HTTP error: ${response.status}`);
      }
    } catch (error) {
      console.error('Error creating new chat:', error);
      
      // Fallback to local reset
      setMessages([]);
      setCurrentSessionId(null);
      setCurrentSessionTitle('');
      setReplyingTo(null);
      setThinkingAdvisors([]);
      setUploadedDocuments([]);
      
      // Re-throw the error so the sidebar knows something went wrong
      throw error;
    }
  }
};

  

  const handleFileUploaded = async (file, uploadResult) => {
    // FIXED: Use the upload result data for better messaging
    const documentMessage = {
      id: generateMessageId(),
      type: 'document_upload',
      content: `Document uploaded: ${uploadResult.filename || file.name} (${uploadResult.chunks_created || 0} sections processed)`,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, documentMessage]);
    setUploadedDocuments(prev => [...prev, file]);
    
    // FIXED: Log document access info
    console.log('File uploaded to session:', {
      filename: uploadResult.filename,
      session_id: uploadResult.session_id,
      chat_session_id: uploadResult.chat_session_id,
      current_session_id: currentSessionId
    });
    
    // Save document upload message to database if we have a current session
    if (currentSessionId) {
      await saveMessageToSession(documentMessage);
    }
  };


  const handleSendMessage = async (inputMessage) => {
    if (!inputMessage.trim()) return;

    const userMessage = {
      id: generateMessageId(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);

    let sessionId = currentSessionId;
    if (!sessionId) {
      sessionId = await createNewSession(inputMessage);
      if (!sessionId) {
        console.error('Failed to create session');
        return;
      }
    }

    // Fire-and-forget: save user message to DB without blocking
    saveMessageToSession(userMessage).catch(err =>
      console.error('Failed to persist user message:', err)
    );

    if (messages.length === 0 && currentSessionTitle.includes('Chat ')) {
      const newTitle = inputMessage.length > 30
        ? `${inputMessage.substring(0, 30)}...`
        : inputMessage;
      updateSessionTitle(sessionId, newTitle).catch(() => {});
    }

    setIsLoading(true);
    setThinkingAdvisors(['system']);

    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL}/chat-stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          user_input: inputMessage,
          response_length: 'medium',
          chat_session_id: currentSessionId,
          active_advisors: activeAdvisors || undefined,
          synthesized: synthesizedMode,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      const dbSavePromises = [];

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE events (delimited by double newline)
        let boundary;
        while ((boundary = buffer.indexOf('\n\n')) !== -1) {
          const raw = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);

          let eventType = 'message';
          let eventData = '';
          for (const line of raw.split('\n')) {
            if (line.startsWith('event: ')) eventType = line.slice(7).trim();
            else if (line.startsWith('data: ')) eventData = line.slice(6);
          }
          if (!eventData) continue;

          let parsed;
          try { parsed = JSON.parse(eventData); } catch { continue; }

          if (eventType === 'advisor') {
            const msg = {
              id: generateMessageId(),
              type: 'advisor',
              persona_id: parsed.persona_id,
              content: parsed.content,
              timestamp: new Date(),
              advisorName: parsed.persona_name || parsed.persona_id,
              used_documents: parsed.used_documents || false,
              document_chunks_used: parsed.document_chunks_used || 0,
            };
            setMessages(prev => [...prev, msg]);
            setThinkingAdvisors(prev => prev.filter(id => id !== parsed.persona_id && id !== 'system'));
            dbSavePromises.push(saveMessageToSession(msg));
          } else if (eventType === 'progress') {
            // Synthesized mode: an advisor finished but we only show
            // the final merged answer. Update thinking indicator.
            setThinkingAdvisors(prev => {
              const next = prev.filter(id => id !== parsed.persona_id && id !== 'system');
              if (!next.includes('synthesizing')) next.push('synthesizing');
              return next;
            });
          } else if (eventType === 'synthesized') {
            setThinkingAdvisors([]);
            const msg = {
              id: generateMessageId(),
              type: 'advisor',
              persona_id: parsed.persona_id || 'orchestrator',
              content: parsed.content,
              timestamp: new Date(),
              advisorName: parsed.persona_name || 'Synthesized Answer',
              used_documents: parsed.used_documents || false,
              document_chunks_used: parsed.document_chunks_used || 0,
            };
            setMessages(prev => [...prev, msg]);
            dbSavePromises.push(saveMessageToSession(msg));
          } else if (eventType === 'clarification') {
            const cMsg = {
              id: generateMessageId(),
              type: 'clarification',
              content: parsed.message,
              suggestions: parsed.suggestions || [],
              timestamp: new Date(),
            };
            setMessages(prev => [...prev, cMsg]);
            dbSavePromises.push(saveMessageToSession(cMsg));
          } else if (eventType === 'error') {
            setMessages(prev => [...prev, {
              id: generateMessageId(),
              type: 'error',
              content: parsed.detail || 'An error occurred.',
              timestamp: new Date(),
            }]);
          }
          // eventType === 'done' → stream finished, loop will exit naturally
        }
      }

      // Wait for all DB saves to finish (parallel, non-blocking during stream)
      await Promise.allSettled(dbSavePromises);

    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, {
        id: generateMessageId(),
        type: 'error',
        content: `Failed to send message: ${error.message}`,
        timestamp: new Date()
      }]);
    } finally {
      setIsLoading(false);
      setThinkingAdvisors([]);
    }
  };

  const handleReplyToAdvisor = async (inputMessage, replyContext) => {
  // Ensure we have a session before proceeding
  let sessionId = currentSessionId;
  if (!sessionId) {
    sessionId = await createNewSession(inputMessage);
    if (!sessionId) {
      console.error('Failed to create session for reply');
      return;
    }
  }

  const replyMessage = {
    id: generateMessageId(),
    type: 'user',
    content: inputMessage,
    replyTo: {
      advisorId: replyContext.persona_id,
      advisorName: replyContext.advisorName,
      messageId: replyContext.messageId
    },
    timestamp: new Date()
  };

  setMessages(prev => [...prev, replyMessage]);
  
  // Save reply message to database with explicit session ID
  await saveMessageToSession(replyMessage, sessionId);
  
  setIsLoading(true);
  setThinkingAdvisors([replyContext.persona_id]);

  try {
    const response = await fetch(`${process.env.REACT_APP_API_URL}/reply-to-advisor`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_input: inputMessage,
        advisor_id: replyContext.advisorId,
        original_message_id: replyContext.messageId,
        chat_session_id: sessionId // Use confirmed session ID
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }

    const data = await response.json();

    if (data.type === 'advisor_reply') {
      const replyResponseMessage = {
        id: generateMessageId(),
        type: 'advisor',
        persona_id: data.persona_id,
        advisorName: data.persona,
        content: data.response,
        isReply: true,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, replyResponseMessage]);
      
      // Save advisor reply to database
      await saveMessageToSession(replyResponseMessage, sessionId);
    }

  } catch (error) {
    console.error('Error replying to advisor:', error);
    const errorMessage = {
      id: generateMessageId(),
      type: 'error',
      content: 'Sorry, I encountered an error with your reply. Please try again.',
      timestamp: new Date()
    };
    setMessages(prev => [...prev, errorMessage]);
    
    // Save error message to database
    await saveMessageToSession(errorMessage, sessionId);
  }

  setIsLoading(false);
  setThinkingAdvisors([]);
};

  const handleCopyMessage = (messageId, content) => {
    // Optional: Show a toast notification or add to message history
    console.log(`Copied message ${messageId}: ${content.substring(0, 50)}...`);
  };

  const handleExpandMessage = async (messageId, advisorId) => {
    const advisor = allPersonas[advisorId];
    if (!advisor) return;

    const originalMessage = messages.find(msg => msg.id === messageId);
    if (!originalMessage) return;

    const expandPrompt = `Please expand on your previous response: "${originalMessage.content.substring(0, 100)}..." Provide more detail and depth.`;
    
    const expandMessage = {
      id: generateMessageId(),
      type: 'user',
      content: expandPrompt,
      timestamp: new Date(),
      isExpandRequest: true,
      expandsMessageId: messageId
    };
    setMessages(prev => [...prev, expandMessage]);
    
    // Save expand request to database
    await saveMessageToSession(expandMessage);
    
    setIsLoading(true);
    setThinkingAdvisors([advisorId]);

    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL}/chat/${advisorId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_input: expandPrompt,
          response_length: 'long'
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const data = await response.json();

      if (data.persona && data.response) {
        const expandedMessage = {
          id: generateMessageId(),
          type: 'advisor',
          persona_id: advisorId,
          advisorName: advisor.name,
          content: data.response,
          isExpansion: true,
          expandsMessageId: messageId,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, expandedMessage]);
        
        // Save expanded response to database
        await saveMessageToSession(expandedMessage);
      } else {
        const errorMessage = {
          id: generateMessageId(),
          type: 'error',
          content: 'Sorry, I received an unexpected response format. Please try again.',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, errorMessage]);
        
        // Save error message to database
        await saveMessageToSession(errorMessage);
      }

    } catch (error) {
      console.error('Error expanding message:', error);
      const errorMessage = {
        id: generateMessageId(),
        type: 'error',
        content: 'Sorry, I encountered an error while expanding the message. Please try again.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
      
      // Save error message to database
      await saveMessageToSession(errorMessage);
    }

    setIsLoading(false);
    setThinkingAdvisors([]);
  };

  const handleReplyToMessage = (message) => {
    const advisor = allPersonas[message.persona_id];
    setReplyingTo({
      advisorId: message.persona_id,
      messageId: message.id,
      advisorName: advisor?.name || message.advisorName || 'Advisor',
      persona_id: message.persona_id
    });
  };

  const handleMessageClick = (message) => {
    if (message.type === 'advisor') {
      const advisor = allPersonas[message.persona_id];
      setReplyingTo({
        advisorId: message.persona_id,
        messageId: message.id,
        advisorName: advisor?.name || message.advisorName || 'Advisor',
        persona_id: message.persona_id
      });
    }
  };

  const handleInputSubmit = async (inputMessage) => {
  if (replyingTo) {
    // This is a reply to a specific message
    await handleReplyToAdvisor(inputMessage, replyingTo);
  } else {
    // This is a regular message
    await handleSendMessage(inputMessage);
  }
};

  const cancelReply = () => {
    setReplyingTo(null);
  };

  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  const handleSidebarToggle = (isCollapsed) => {
    setIsSidebarCollapsed(isCollapsed);
  };

  const hasMessages = messages.length > 0;
  const hasConversationMessages = messages.filter(m => m.type !== 'system' && m.type !== 'document_upload').length > 0;

  // Group consecutive non-reply advisor messages for carousel display
  const groupedMessages = useMemo(() => {
    const groups = [];
    let i = 0;
    while (i < messages.length) {
      const msg = messages[i];
      if (msg.type === 'advisor' && !msg.isReply && !msg.isExpansion) {
        const batch = [];
        while (
          i < messages.length &&
          messages[i].type === 'advisor' &&
          !messages[i].isReply &&
          !messages[i].isExpansion
        ) {
          batch.push(messages[i]);
          i++;
        }
        groups.push({ kind: 'advisor-group', id: batch[0].id, messages: batch });
      } else {
        groups.push({ kind: 'single', id: msg.id, message: msg });
        i++;
      }
    }
    return groups;
  }, [messages]);

  const chatPlaceholder = config?.chat_page?.placeholder || "Ask your advisors anything...";

  return (
    <div className="chat-page-with-sidebar">
      {/* Sidebar Component */}
      <Sidebar 
        user={user}
        currentSessionId={currentSessionId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        onSignOut={onSignOut}
        authToken={authToken}
        onSidebarToggle={handleSidebarToggle}
        isMobileOpen={isMobileMenuOpen}
        onMobileToggle={setIsMobileMenuOpen}
        onNavigateToCanvas={onNavigateToCanvas}
        userAvatarId={userAvatarId}
        onAvatarChange={handleAvatarChange}
        onOpenProfile={() => setShowProfileForm(true)}
        onOpenAccount={() => setShowAccount(true)}
        onOpenClearData={() => setShowClearData(true)}
        onOpenUserGuide={onNavigateToGuide}
        onOpenTutorial={onOpenTutorial}
      />
      
      <div className={`main-chat-area ${isSidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        <div className="modern-chat-page">
          {/* Floating Header */}
          <div className="floating-header">
            <div className="header-left">
              <button 
                className="mobile-menu-button"
                onClick={handleMobileMenuToggle}
              >
                <Menu size={20} />
              </button>
              <button onClick={onNavigateToHome} className="modern-home-btn">
                <Home size={20} />
              </button>
              <div className="header-brand">
                <div className="brand-icon">
                  <Users size={24} />
                </div>
                <div className="brand-text">
                  <h1>{config?.app?.title || 'Advisory'}</h1>
                  <p>{config?.app?.subtitle || 'AI-Powered Guidance'}</p>
                </div>
              </div>
            </div>
            
            <div className="header-right">
              <AdvisorStatusDropdown 
                advisors={advisors}
                thinkingAdvisors={thinkingAdvisors}
                getAdvisorColors={getAdvisorColors}
                isDark={isDark}
                activeAdvisors={activeAdvisors || allAdvisorIds}
                onToggleAdvisor={handleToggleAdvisor}
              />
              <AgentStatusDropdown
                agents={agents}
                thinkingAdvisors={thinkingAdvisors}
                getAgentColors={getAgentColors}
                isDark={isDark}
              />
              
              <div className="header-controls">
                {/* Optional: Add header sign out button */}
                <button 
                  className="header-signout-btn"
                  onClick={onSignOut}
                  title="Sign Out"
                >
                  <LogOut size={16} />
                </button>
                
                {/* Export Button */}
                <ExportButton 
                  hasMessages={hasConversationMessages} 
                  currentSessionId={currentSessionId}
                  authToken={authToken}
                />
                
                {/* Provider Dropdown */}
                <ProviderDropdown 
                  currentProvider={currentProvider}
                  onProviderChange={handleProviderSwitch}
                  isLoading={isProviderSwitching}
                />
                
                {/* Theme Toggle */}
                <ThemeToggle />
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div className="chat-content">
            {!hasMessages ? (
              <div className="welcome-state">
                <SuggestionsPanel onSuggestionClick={handleSendMessage} />
                <footer className="welcome-copyright-footer">
                  <p className="footer-text">
                    Copyright{' '}
                    <a href="https://neon.ai" target="_blank" rel="noopener noreferrer" className="footer-neon-link">
                      <img src="/neon-logo.png" alt="" className="footer-neon-logo" />
                      Neon.ai
                    </a>
                    , portions copyright University of Colorado Boulder. All rights reserved.{' '}
                    <a href="https://www.neon.ai/contact" target="_blank" rel="noopener noreferrer" className="footer-patents-link">
                      Patents and licensing.
                    </a>
                  </p>
                </footer>
              </div>
            ) : (
              <div className="messages-container">
                {/* Add loading session indicator */}
                {isLoadingSession && (
                  <div className="loading-session">
                    <div className="loading-spinner"></div>
                    <span>Loading chat session...</span>
                  </div>
                )}
                
                <div className="messages-list">
                  <div className="messages-scroll">
                    {groupedMessages.map((item) => (
                      <div key={item.id}>
                        {item.kind === 'advisor-group' && (
                          <AdvisorCarousel
                            messages={item.messages}
                            onReply={handleReplyToMessage}
                            onExpand={handleExpandMessage}
                            onClick={handleMessageClick}
                            onSearchReferences={handleSearchReferences}
                            userAvatarId={userAvatarId}
                            userAvatarOptions={avatarOptions}
                          />
                        )}

                        {item.kind === 'single' && item.message.type === 'user' && (
                          <div className="user-message-container">
                            <div className="user-message">
                              {item.message.replyTo && (
                                <div className="reply-indicator">
                                  <Reply size={12} />
                                  <span>Reply to {item.message.replyTo.advisorName}</span>
                                </div>
                              )}
                              <p>{item.message.content}</p>
                            </div>
                          </div>
                        )}

                        {item.kind === 'single' && item.message.type === 'advisor' && (
                          <div style={{ position: 'relative' }}>
                            <MessageBubble
                              message={item.message}
                              onReply={handleReplyToMessage}
                              onExpand={handleExpandMessage}
                              onClick={handleMessageClick}
                              onSearchReferences={handleSearchReferences}
                              showReplyButton={true}
                              userAvatarId={userAvatarId}
                              userAvatarOptions={avatarOptions}
                            />
                            {refSearchPopover === item.message.id && (
                              <ReferenceSearchPopover
                                query={refSearchQuery}
                                loading={refSearchLoading}
                                onClose={() => setRefSearchPopover(null)}
                              />
                            )}
                          </div>
                        )}

                        {item.kind === 'single' && item.message.type === 'error' && (
                          <div className="error-message-container">
                            <div className="error-message">
                              <p>{item.message.content}</p>
                            </div>
                          </div>
                        )}

                        {item.kind === 'single' && item.message.type === 'system' && (
                          <div className="system-message-container">
                            <div className="system-message">
                              <p>{item.message.content}</p>
                            </div>
                          </div>
                        )}

                        {item.kind === 'single' && item.message.type === 'document_upload' && (
                          <div className="system-message-container">
                            <div className="system-message document-upload">
                              <FileText size={16} />
                              <p>{item.message.content}</p>
                            </div>
                          </div>
                        )}

                        {item.kind === 'single' && item.message.type === 'clarification' && (
                          <div className="clarification-message-container">
                            <div className="clarification-message">
                              <div className="clarification-header">
                                {orchestratorAvatar ? (
                                  <img 
                                    src={orchestratorAvatar} 
                                    alt="Orchestrator" 
                                    style={{ width: 20, height: 20, borderRadius: '50%', objectFit: 'cover' }} 
                                  />
                                ) : (
                                  <MessageCircle size={16} />
                                )}
                                <span>I need a bit more information</span>
                              </div>
                              <p>{item.message.content}</p>
                              
                              {item.message.suggestions && item.message.suggestions.length > 0 && (
                                <div className="clarification-suggestions">
                                  <p className="suggestions-label">Here are some ways you could be more specific:</p>
                                  <div className="suggestions-list">
                                    {item.message.suggestions.map((suggestion, index) => (
                                      <button
                                        key={index}
                                        className="suggestion-button"
                                        onClick={() => handleSendMessage(suggestion)}
                                      >
                                        {suggestion}
                                      </button>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}

                    {thinkingAdvisors.includes('system') && (
                      <div className="orchestrator-thinking">
                        <div className="thinking-bubble" style={orchestratorAvatar ? { overflow: 'hidden', padding: 0 } : {}}>
                          {orchestratorAvatar ? (
                            <img 
                              src={orchestratorAvatar} 
                              alt="Orchestrator" 
                              style={{ width: '100%', height: '100%', borderRadius: 'inherit', objectFit: 'cover' }} 
                            />
                          ) : (
                            <MessageCircle size={20} />
                          )}
                        </div>
                        <div className="thinking-content">
                          <span className="thinking-label">Orchestrator is thinking...</span>
                          <div className="thinking-animation">
                            <div className="dot"></div>
                            <div className="dot"></div>
                            <div className="dot"></div>
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {thinkingAdvisors.filter(id => id !== 'system' && id !== 'synthesizing').map(advisorId => (
                      <ThinkingIndicator key={advisorId} advisorId={advisorId} />
                    ))}

                    {thinkingAdvisors.includes('synthesizing') && (
                      <div className="orchestrator-thinking">
                        <div className="thinking-bubble" style={orchestratorAvatar ? { overflow: 'hidden', padding: 0 } : {}}>
                          {orchestratorAvatar ? (
                            <img src={orchestratorAvatar} alt="Synthesizing" style={{ width: '100%', height: '100%', borderRadius: 'inherit', objectFit: 'cover' }} />
                          ) : (
                            <MessageCircle size={20} />
                          )}
                        </div>
                        <div className="thinking-content">
                          <span className="thinking-label">Synthesizing answers...</span>
                          <div className="thinking-animation">
                            <div className="dot"></div>
                            <div className="dot"></div>
                            <div className="dot"></div>
                          </div>
                        </div>
                      </div>
                    )}

                    <div ref={messagesEndRef} />
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className={`floating-input-area ${isSidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
            {replyingTo && (
              <div className="reply-banner">
                <div className="reply-info">
                  <Reply size={16} />
                  <span>Replying to <strong>{replyingTo.advisorName}</strong></span>
                </div>
                <button onClick={cancelReply} className="cancel-reply">
                  <X size={16} />
                </button>
              </div>
            )}
            
            <EnhancedChatInput 
              onSendMessage={handleInputSubmit}
              onFileUploaded={handleFileUploaded}
              uploadedDocuments={uploadedDocuments}
              isLoading={isLoading}
              currentChatSessionId={currentSessionId}
              authToken={authToken}
              placeholder={
                replyingTo 
                  ? `Reply to ${replyingTo.advisorName}...`
                  : chatPlaceholder
              }
              showProfileButtons={!userProfile || userProfile.completion_pct < 100}
              onOpenOnboarding={() => setShowOnboarding(true)}
              onOpenProfileForm={() => setShowProfileForm(true)}
              synthesizedMode={synthesizedMode}
              onToggleSynthesized={handleToggleSynthesized}
              ensureSessionId={async () => {
                if (currentSessionId) return currentSessionId;
                return await createNewSession('Document upload');
              }}
            />
          </div>
        </div>
      </div>

      {showOnboarding && (
        <OnboardingChat
          authToken={authToken}
          userName={user?.firstName}
          onClose={() => { setShowOnboarding(false); loadProfile(); }}
        />
      )}

      {showProfileForm && (
        <ProfileWalkthrough
          authToken={authToken}
          existingProfile={userProfile}
          onClose={() => { setShowProfileForm(false); loadProfile(); }}
        />
      )}

      {showClearData && (
        <ClearDataModal
          authToken={authToken}
          onClose={() => setShowClearData(false)}
          onDataCleared={({ profile: clearedProfile, chats: clearedChats }) => {
            if (clearedProfile) {
              setUserProfile(null);
              loadProfile();
            }
            if (clearedChats) {
              setMessages([]);
              setCurrentSessionId(null);
              setCurrentSessionTitle('');
              handleNewChat();
            }
          }}
        />
      )}

      {showAccount && (
        <AccountModal
          user={user}
          authToken={authToken}
          onClose={() => setShowAccount(false)}
          onAccountUpdated={(updated) => {
            if (user) {
              user.firstName = updated.firstName;
              user.lastName = updated.lastName;
              user.email = updated.email;
            }
          }}
          onAccountDeleted={() => {
            setShowAccount(false);
            onSignOut();
          }}
        />
      )}

    </div>
  );
};

const ReferenceSearchPopover = ({ query, loading, onClose }) => {
  const handleCopy = () => {
    navigator.clipboard.writeText(query).catch(() => {});
  };
  const handlePerplexity = () => {
    window.open(`https://www.perplexity.ai/?q=${encodeURIComponent(query)}`, '_blank');
  };

  return (
    <div style={{
      position: 'absolute', bottom: '100%', right: 0, marginBottom: 8,
      background: 'var(--bg-primary)', border: '1px solid var(--border-primary)',
      borderRadius: 12, padding: 16, minWidth: 280, maxWidth: 360,
      boxShadow: '0 8px 32px rgba(0,0,0,0.15)', zIndex: 100,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <span style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>Search for References</span>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}>
          <X size={14} />
        </button>
      </div>
      {loading ? (
        <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>Generating search query...</div>
      ) : (
        <>
          <div style={{
            background: 'var(--bg-secondary)', borderRadius: 8, padding: '8px 10px',
            fontSize: 12, color: 'var(--text-primary)', marginBottom: 10, lineHeight: 1.4,
          }}>
            {query}
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <button onClick={handlePerplexity} style={{
              padding: '6px 12px', borderRadius: 8, fontSize: 11, fontWeight: 600,
              background: 'var(--accent-primary)', color: '#fff', border: 'none', cursor: 'pointer',
            }}>Open in Perplexity</button>
            <button onClick={handleCopy} style={{
              padding: '6px 12px', borderRadius: 8, fontSize: 11, fontWeight: 600,
              background: 'var(--bg-secondary)', color: 'var(--text-primary)',
              border: '1px solid var(--border-primary)', cursor: 'pointer',
            }}>Copy Prompt</button>
          </div>
        </>
      )}
    </div>
  );
};

export default ChatPage;
