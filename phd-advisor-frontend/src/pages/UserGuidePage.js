import React, { useState, useMemo, useRef, useEffect } from 'react';
import {
  Search, ArrowLeft, ChevronDown, ChevronRight,
  MessageSquare, Upload, BookOpen, Brain,
  Users, KeyRound, Layout
} from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import '../styles/UserGuide.css';

const GUIDE_SECTIONS = [
  {
    id: 'getting-started',
    title: 'Getting Started',
    icon: BookOpen,
    subsections: [
      {
        id: 'creating-account',
        title: 'Creating Your Account',
        content: `Click **Get Started** on the homepage and create an account with your name, email, and password. After signup, you will be logged in automatically and taken to the advisory workspace.`
      },
      {
        id: 'onboarding',
        title: 'Configuring Your Profile',
        content: `A short onboarding chat collects role level, focus area, goals, and preferences so persona responses can be tailored to your context. You can edit this information anytime from **Profile** in the sidebar menu.`
      },
      {
        id: 'navigation',
        title: 'Navigating the App',
        content: `The app has three core areas:\n\n- **Chat** — ask questions and receive multi-persona guidance\n- **Canvas** — view structured insights and action items\n- **Home** — review this white-label template overview\n\nUse the sidebar to switch chats, start new sessions, and open Canvas.`
      },
    ]
  },
  {
    id: 'chat-interface',
    title: 'Chat Interface',
    icon: MessageSquare,
    subsections: [
      {
        id: 'asking-questions',
        title: 'Asking Questions',
        content: `Type your question in the input box and press Enter or click send. Ask strategic, operational, implementation, or governance questions based on your use case.\n\nIf a prompt is too broad, the orchestrator may ask clarifying follow-up questions.`
      },
      {
        id: 'panel-vs-aggregate',
        title: 'Response mode (Panel, Aggregate, Single)',
        content: `Use the **Response mode** dropdown in the header (to the right of the advisor selector) to choose how answers are produced:\n\n- **Panel** — Up to three relevant advisors each answer separately; responses appear as a carousel you can swipe through.\n- **Aggregate** — Multiple advisors contribute, then their insights are merged into one synthesized answer.\n- **Single advisor** — Open the submenu and pick one advisor; only that advisor answers.\n\nPanel mode shows diverse viewpoints. Aggregate is best for one consolidated answer. Single is best when you want a specific specialist only.`
      },
      {
        id: 'replying-to-advisors',
        title: 'Replying to a Specific Persona',
        content: `If one persona gives a useful direction, click **reply** on that message to continue with that persona specifically.`
      },
      {
        id: 'chat-sessions',
        title: 'Managing Chat Sessions',
        content: `Each conversation is saved as a chat session:\n\n- **New chat** — click **+ New Chat**\n- **Switch chats** — select any prior session in the sidebar\n- **Search chats** — use the sidebar search field\n- **Delete chat** — remove sessions you no longer need`
      },
    ]
  },
  {
    id: 'personas',
    title: 'Persona Panel',
    icon: Users,
    subsections: [
      {
        id: 'persona-overview',
        title: 'How Personas Work',
        content: `This white-label demo includes six configurable personas (**Expert Persona 1** through **Expert Persona 6**). Each persona has a different style, so one question produces multiple complementary viewpoints.`
      },
      {
        id: 'customization',
        title: 'Customizing Personas',
        content: `You can customize persona names, prompts, colors, and suggested questions in ` + "`config.yaml`" + `. This is the fastest way to adapt the app for industries such as construction, HR, education, nonprofit support, or internal enterprise operations.`
      },
      {
        id: 'persona-value',
        title: 'Why Multi-Persona Design',
        content: `Multi-persona responses make trade-offs visible. One persona can emphasize strategy, another implementation, another risk, and another communication readiness.`
      },
    ]
  },
  {
    id: 'documents',
    title: 'Uploading Documents',
    icon: Upload,
    subsections: [
      {
        id: 'upload-docs',
        title: 'How to Upload',
        content: `Click the **paperclip icon** next to the chat input. Supported file types:\n\n- **PDF**\n- **DOCX**\n- **TXT**\n\nMaximum file size is 10MB.`
      },
      {
        id: 'how-rag-works',
        title: 'How Document Context Works',
        content: `Uploaded files are indexed so personas can reference relevant sections during response generation. This uses **Retrieval-Augmented Generation (RAG)** to ground answers in your own organizational knowledge.`
      },
      {
        id: 'document-tips',
        title: 'Tips for Best Results',
        content: `- Upload files **before** asking questions about them\n- Mention document context directly in your prompt\n- Keep one topic per chat when possible for cleaner context\n- Use follow-up questions to refine recommendations`
      },
    ]
  },
  {
    id: 'canvas',
    title: 'Advisor Canvas',
    icon: Layout,
    subsections: [
      {
        id: 'canvas-overview',
        title: 'What is the Canvas?',
        content: `Canvas is a dynamic summary that organizes insights from your chats into structured sections. It is designed as a decision-support artifact, not just a transcript.`
      },
      {
        id: 'canvas-sections',
        title: 'Canvas Sections',
        content: `Sections are aligned to reusable business themes such as strategy, implementation, operations, governance, metrics, and opportunities.\n\nYou can refresh Canvas to pull in new insights and print/export for stakeholder review.`
      },
    ]
  },
  {
    id: 'settings',
    title: 'Settings & Account',
    icon: KeyRound,
    subsections: [
      {
        id: 'dark-mode',
        title: 'Dark Mode',
        content: `Use the sun/moon icon to toggle between light and dark themes. Your preference is saved across sessions.`
      },
      {
        id: 'change-avatar',
        title: 'Changing Your Avatar',
        content: `Choose **Change Avatar** from the sidebar menu to personalize your profile icon and color theme.`
      },
      {
        id: 'account-settings',
        title: 'Account Settings',
        content: `Open **Account** from the sidebar menu to update name, email, or password, or to delete your account.`
      },
      {
        id: 'clear-data',
        title: 'Clearing Your Data',
        content: `Use **Clear User Data** to selectively remove profile data, chat history, or Canvas content without deleting your account.`
      },
    ]
  },
  {
    id: 'tips',
    title: 'Tips & Best Practices',
    icon: Brain,
    subsections: [
      {
        id: 'better-questions',
        title: 'Asking Better Questions',
        content: `Include context and desired outcomes for higher quality responses.\n\n- **Vague:** "Help with AI"\n- **Better:** "We are a 200-person company and need a 90-day AI adoption roadmap for support and operations."`
      },
      {
        id: 'using-multiple-advisors',
        title: 'Getting the Most from Multiple Personas',
        content: `Start in **Panel Mode** to compare viewpoints, then switch to **Aggregate** for a concise synthesis. Reply directly to a persona when you want to deepen one thread.`
      },
      {
        id: 'document-workflow',
        title: 'Document Review Workflow',
        content: `1. Upload a relevant internal document\n2. Ask a focused question tied to a business outcome\n3. Request follow-up detail on trade-offs or implementation\n4. Convert insights into action owners and timelines`
      },
    ]
  },
];

function highlightMatch(text, query) {
  if (!query) return text;
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(`(${escaped})`, 'gi');
  return text.replace(regex, '**$1**');
}

function renderMarkdown(text) {
  let html = text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n- /g, '</p><ul><li>')
    .replace(/\n(\d+)\. /g, '</p><ol><li>')
    .replace(/<\/li>\n/g, '</li>')
    .replace(/<li>(.*?)(?=<li>|<\/ul>|<\/ol>|$)/gs, '<li>$1</li>');

  html = '<p>' + html + '</p>';
  html = html.replace(/<\/p><ul>/g, '</p><ul>');
  html = html.replace(/<\/li><\/p>/g, '</li></ul><p>');
  html = html.replace(/<p><\/p>/g, '');
  html = html.replace(/<ul><li>/g, '<ul><li>');
  html = html.replace(/<\/li>(?!<li|<\/ul)/g, '</li></ul>');
  return html;
}

export default function UserGuidePage({ onNavigateToChat }) {
  const { isDark } = useTheme();
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedSections, setExpandedSections] = useState(new Set(['getting-started']));
  const [activeSubsection, setActiveSubsection] = useState(null);
  const contentRef = useRef(null);

  const toggleSection = (sectionId) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(sectionId)) next.delete(sectionId);
      else next.add(sectionId);
      return next;
    });
  };

  const scrollToSubsection = (subsectionId) => {
    setActiveSubsection(subsectionId);
    const el = document.getElementById(`guide-${subsectionId}`);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const filteredSections = useMemo(() => {
    if (!searchQuery.trim()) return GUIDE_SECTIONS;
    const q = searchQuery.toLowerCase();
    return GUIDE_SECTIONS.map(section => {
      const matchingSubs = section.subsections.filter(
        sub =>
          sub.title.toLowerCase().includes(q) ||
          sub.content.toLowerCase().includes(q)
      );
      if (matchingSubs.length > 0 || section.title.toLowerCase().includes(q)) {
        return { ...section, subsections: matchingSubs.length > 0 ? matchingSubs : section.subsections };
      }
      return null;
    }).filter(Boolean);
  }, [searchQuery]);

  const matchCount = useMemo(() => {
    if (!searchQuery.trim()) return 0;
    return filteredSections.reduce((sum, s) => sum + s.subsections.length, 0);
  }, [filteredSections, searchQuery]);

  useEffect(() => {
    if (searchQuery.trim() && filteredSections.length > 0) {
      setExpandedSections(new Set(filteredSections.map(s => s.id)));
    }
  }, [searchQuery, filteredSections]);

  return (
    <div className={`guide-page ${isDark ? 'dark' : ''}`}>
      <header className="guide-header">
        <div className="guide-header-left">
          <button className="guide-back-btn" onClick={onNavigateToChat} title="Back to Chat">
            <ArrowLeft size={20} />
          </button>
          <div className="guide-header-brand">
            <BookOpen size={22} className="guide-brand-icon" />
            <h1 className="guide-title">User Guide</h1>
          </div>
        </div>
        <div className="guide-search-wrapper">
          <Search size={16} className="guide-search-icon" />
          <input
            type="text"
            className="guide-search-input"
            placeholder="Search the guide..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            autoFocus
          />
          {searchQuery && (
            <span className="guide-search-count">
              {matchCount} result{matchCount !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </header>

      <div className="guide-layout">
        <nav className="guide-nav">
          {GUIDE_SECTIONS.map(section => {
            const Icon = section.icon;
            const isMatch = filteredSections.some(s => s.id === section.id);
            return (
              <div key={section.id} className={`guide-nav-group ${!isMatch && searchQuery ? 'dimmed' : ''}`}>
                <button
                  className="guide-nav-section"
                  onClick={() => {
                    toggleSection(section.id);
                    const el = document.getElementById(`guide-section-${section.id}`);
                    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                  }}
                >
                  <Icon size={16} />
                  <span>{section.title}</span>
                </button>
                {expandedSections.has(section.id) && (
                  <div className="guide-nav-subs">
                    {section.subsections.map(sub => (
                      <button
                        key={sub.id}
                        className={`guide-nav-sub ${activeSubsection === sub.id ? 'active' : ''}`}
                        onClick={() => scrollToSubsection(sub.id)}
                      >
                        {sub.title}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        <main className="guide-content" ref={contentRef}>
          {filteredSections.length === 0 ? (
            <div className="guide-no-results">
              <Search size={40} />
              <p>No results for "{searchQuery}"</p>
              <button onClick={() => setSearchQuery('')}>Clear search</button>
            </div>
          ) : (
            filteredSections.map(section => {
              const Icon = section.icon;
              const isExpanded = expandedSections.has(section.id);
              return (
                <section key={section.id} id={`guide-section-${section.id}`} className="guide-section">
                  <button className="guide-section-header" onClick={() => toggleSection(section.id)}>
                    <div className="guide-section-header-left">
                      <Icon size={20} />
                      <h2>{section.title}</h2>
                    </div>
                    {isExpanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
                  </button>
                  {isExpanded && (
                    <div className="guide-section-body">
                      {section.subsections.map(sub => (
                        <article key={sub.id} id={`guide-${sub.id}`} className="guide-subsection">
                          <h3>{searchQuery ? highlightMatch(sub.title, searchQuery) : sub.title}</h3>
                          <div
                            className="guide-text"
                            dangerouslySetInnerHTML={{
                              __html: renderMarkdown(searchQuery ? highlightMatch(sub.content, searchQuery) : sub.content),
                            }}
                          />
                        </article>
                      ))}
                    </div>
                  )}
                </section>
              );
            })
          )}
        </main>
      </div>
    </div>
  );
}
