import React, { useState, useMemo, useRef, useEffect } from 'react';
import {
  Search, ArrowLeft, ChevronDown, ChevronRight,
  MessageSquare, Upload, BookOpen, Brain,
  Users, Wrench, KeyRound, Layout
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
        content: `When you first visit the app, click **Get Started** on the homepage. You'll be taken to the signup page where you can create an account with your name, email, and password. Select your role (e.g. Project Manager, Site Supervisor) so the advisors can tailor their responses. After signing up, you'll be logged in automatically and taken to the chat interface.`
      },
      {
        id: 'onboarding',
        title: 'Completing Your Profile',
        content: `After your first login, a "Tell us about yourself" chat will appear. This onboarding conversation asks about your specialty, experience level, certifications, and current projects so the advisors can personalize their responses. You can also fill out your profile manually by clicking **Profile** in the sidebar menu. The more information you provide, the better tailored the advice will be.`
      },
      {
        id: 'navigation',
        title: 'Navigating the App',
        content: `The app has three main areas:\n\n- **Chat** — The main interface where you ask questions and receive advice from AI advisors.\n- **AI Notes & Planning** — A page that organizes key takeaways, action items, and plans from your conversations.\n- **Home** — The landing page with an overview of the app's features.\n\nUse the sidebar on the left to switch between chat sessions, start new conversations, or access AI Notes & Planning. The home button in the header takes you back to the landing page.`
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
        content: `Type your question in the input box at the bottom of the chat and press Enter or click the send button. You can ask about anything related to construction project management — scheduling, cost estimation, safety compliance, quality assurance, equipment logistics, or environmental permits.\n\nIf your question is too vague, the system may ask you to clarify with a follow-up question and clickable suggestion buttons.`
      },
      {
        id: 'panel-vs-aggregate',
        title: 'Response mode (Panel, Aggregate, Single)',
        content: `Use the **Response mode** dropdown in the header (to the right of the advisor selector) to choose how answers are produced:\n\n- **Panel** — Up to three relevant advisors each answer separately; responses appear as a carousel you can swipe through.\n- **Aggregate** — Multiple advisors contribute, then their insights are merged into one synthesized answer.\n- **Single advisor** — Open the submenu and pick one advisor; only that advisor answers.\n\nPanel mode shows diverse viewpoints. Aggregate is best for one consolidated answer. Single is best when you want a specific specialist only.`
      },
      {
        id: 'replying-to-advisors',
        title: 'Replying to a Specific Advisor',
        content: `If one advisor's response is particularly interesting, you can reply directly to them. Click the **reply** button on their message bubble. Your follow-up will be directed specifically to that advisor, who will continue the conversation with full context of what they said before.`
      },
      {
        id: 'chat-sessions',
        title: 'Managing Chat Sessions',
        content: `Each conversation is saved as a chat session. You can:\n\n- **Create a new chat** — Click the **+ New Chat** button in the sidebar.\n- **Switch between chats** — Click any previous session in the sidebar list.\n- **Search chats** — Use the search bar in the sidebar to find a specific conversation by title.\n- **Delete a chat** — Hover over a session and click the trash icon.\n\nYour chat history is preserved across sessions, so you can always come back to previous conversations.`
      },
    ]
  },
  {
    id: 'advisors',
    title: 'Your AI Advisors',
    icon: Users,
    subsections: [
      {
        id: 'advisor-overview',
        title: 'How Advisors Work',
        content: `The app includes a panel of AI advisors, each with a different construction specialty. When you ask a question, the system intelligently selects the three most relevant advisors to respond. Each advisor provides advice through their unique lens — so you get well-rounded guidance on every question.\n\nAdvisors are selected dynamically based on what you ask. A question about OSHA compliance will get different advisors than a question about cost estimation.`
      },
      {
        id: 'project-scheduler',
        title: 'Project Scheduler',
        content: `**Specialty:** Timeline & resource planning\n\nHelps with CPM scheduling, crew and equipment allocation, weather contingencies, look-ahead schedules, and schedule recovery. Best for questions about project timelines, phasing, and coordination.`
      },
      {
        id: 'safety-advisor',
        title: 'Safety Advisor',
        content: `**Specialty:** Jobsite safety & OSHA compliance\n\nHelps with OSHA 1926 requirements, work zone traffic control, heat illness prevention, PPE, incident investigation, and toolbox talks. Best for questions about safety programs and regulatory compliance.`
      },
      {
        id: 'cost-estimator',
        title: 'Cost Estimator',
        content: `**Specialty:** Budgeting & bid preparation\n\nHelps with takeoffs, unit costs, bid structures, material and fuel tracking, production rates, change orders, and margins. Best for questions about budgets, bids, and cost management.`
      },
      {
        id: 'quality-manager',
        title: 'Quality Manager',
        content: `**Specialty:** QC/QA & materials testing\n\nHelps with mix design, density testing, aggregate specs, DOT acceptance criteria, documentation, and non-conformance resolution. Best for questions about quality standards and test results.`
      },
      {
        id: 'operations-coordinator',
        title: 'Operations Coordinator',
        content: `**Specialty:** Equipment, crews & logistics\n\nHelps with fleet management, crew scheduling, plant coordination, haul dispatch, aggregate supply, and production optimization. Best for questions about equipment, logistics, and day-to-day operations.`
      },
      {
        id: 'environmental-specialist',
        title: 'Environmental Specialist',
        content: `**Specialty:** Permits, sustainability & regulatory compliance\n\nHelps with NPDES/SWPPP, emissions, erosion control, RAP/RAS, warm-mix asphalt, and community impact. Best for questions about environmental permits and sustainability practices.`
      },
    ]
  },
  {
    id: 'tools',
    title: 'Built-in Tools',
    icon: Wrench,
    subsections: [
      {
        id: 'contractor-scheduler',
        title: 'Contractor Scheduler',
        content: `The Contractor Scheduler is a specialized tool that checks contractor availability for specific construction tasks on specific dates. It considers preferred contractors, schedule conflicts, weather-sensitive work, and overtime/flex options.\n\nExamples:\n\n- "Schedule a cement pour for Thursday, April 30, 2026"\n- "I need roofing, windows, and cement across 3 days — use the same contractor when possible"\n- "Who's available for electrical work on Monday?"`
      },
      {
        id: 'weather-forecast',
        title: 'Weather Forecast',
        content: `The Weather Forecast tool retrieves a 10-day weather outlook for any location. It automatically warns about conditions that could affect weather-sensitive work like cement pouring, roofing, or painting.\n\nExamples:\n\n- "What's the weather forecast for Dallas, TX this week?"\n- "I need to pour cement Thursday in Raleigh, NC — will the weather cooperate?"\n\nWhen you ask about weather without specifying a location, the system will ask you to provide one.`
      },
      {
        id: 'tool-follow-ups',
        title: 'Follow-up Conversations',
        content: `After using a tool, you can continue the conversation naturally. The system remembers the context:\n\n- After a weather check: "What about next week?" or "Is Saturday better?"\n- After scheduling: "Can we move that to Tuesday instead?" or "What overtime options are there?"\n\nThe system will route follow-up questions to the same tool until you change the subject.`
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
        content: `Click the **paperclip icon** next to the chat input to open the upload area. You can drag and drop a file or click to browse. Supported file types:\n\n- **PDF** — Bid documents, safety plans, project schedules\n- **DOCX** — Scope summaries, change orders, reports\n- **TXT** — Plain text files\n\nMaximum file size is 10MB.`
      },
      {
        id: 'how-rag-works',
        title: 'How Document Context Works',
        content: `When you upload a document, it's processed and indexed so the advisors can reference it in their responses. The system uses a technique called **Retrieval-Augmented Generation (RAG)** — it finds the most relevant sections of your document for each question you ask.\n\nFor example, if you upload a bid document and ask "What are the biggest cost risks?", the Cost Estimator will analyze the actual document content and give specific, informed feedback.`
      },
      {
        id: 'document-tips',
        title: 'Tips for Best Results',
        content: `- Upload documents **before** asking questions about them.\n- Reference your document in your question: "Based on this bid tab, where are my biggest risk areas?"\n- Each chat session has its own document context. If you start a new chat, you'll need to re-upload.\n- The Safety Advisor is especially effective at reviewing uploaded JHAs and safety plans.\n- The Project Scheduler can analyze uploaded schedules and identify risks.`
      },
    ]
  },
  {
    id: 'canvas',
    title: 'AI Notes & Planning',
    icon: Layout,
    subsections: [
      {
        id: 'canvas-overview',
        title: 'What is AI Notes & Planning?',
        content: `AI Notes & Planning is a dynamic summary page that organizes insights from your chat conversations into structured sections. Think of it as a living document that captures the key takeaways, action items, and recommendations from all your advisor interactions.`
      },
      {
        id: 'canvas-sections',
        title: 'Sections',
        content: `Notes are organized into themed sections such as action items, project plans, safety notes, scheduling decisions, and cost considerations. Each section is expandable and shows the most relevant insights from your conversations.\n\nYou can refresh the page to pull in the latest insights from recent chats. Notes can also be printed or exported for your records.`
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
        content: `Toggle between light and dark themes using the **sun/moon icon** in the header. Your preference is saved and persists across sessions.`
      },
      {
        id: 'change-avatar',
        title: 'Changing Your Avatar',
        content: `Click your avatar icon in the sidebar header, or go to the sidebar menu and select **Change Avatar**. Choose from a variety of icons and color themes to personalize your profile.`
      },
      {
        id: 'account-settings',
        title: 'Account Settings',
        content: `Access **Account** from the sidebar menu to:\n\n- Update your first name, last name, or email\n- Change your password (requires current password)\n- Delete your account (irreversible — all data will be removed)`
      },
      {
        id: 'clear-data',
        title: 'Clearing Your Data',
        content: `The **Clear User Data** option in the sidebar menu lets you selectively clear:\n\n- **Profile** — Resets your onboarding answers and profile information\n- **Chat History** — Deletes all saved chat sessions\n- **AI Notes & Planning** — Clears all notes and planning content\n\nThis is useful if you want a fresh start without deleting your account.`
      },
      {
        id: 'sidebar',
        title: 'Sidebar Controls',
        content: `The sidebar can be collapsed to give more space to the chat area. Click the **chevron button** in the sidebar header to toggle between expanded and collapsed views. On mobile, the sidebar opens as an overlay — tap outside to close it.`
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
        content: `The more specific your question, the better the advice:\n\n- **Vague:** "Help me with scheduling"\n- **Better:** "I'm managing a highway resurfacing project with 3 crews — how should I sequence milling and paving to avoid weather delays this spring?"\n\nInclude context about your project type, phase, crew size, and constraints. The advisors use your profile information automatically, but adding details in your question helps them give more targeted responses.`
      },
      {
        id: 'using-multiple-advisors',
        title: 'Getting the Most from Multiple Advisors',
        content: `Use **Panel Mode** when you want diverse perspectives on a decision. For example, asking "Should I accelerate the schedule to avoid winter weather?" will get different angles from the Project Scheduler, Cost Estimator, and Safety Advisor.\n\nIf one advisor's response resonates, **reply directly** to continue that thread. You can always switch back to Panel mode for your next question.`
      },
      {
        id: 'document-workflow',
        title: 'Document Review Workflow',
        content: `For the best document review experience:\n\n1. Upload your document (bid tab, safety plan, schedule, etc.)\n2. Ask a specific question: "Review this bid and flag the highest-risk line items"\n3. Follow up on specific feedback: "Can you break down the aggregate cost assumptions?"\n4. Try asking different advisors — the Safety Advisor focuses on compliance gaps, while the Cost Estimator focuses on pricing risks.`
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

  // Clean up list formatting
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
      if (next.has(sectionId)) {
        next.delete(sectionId);
      } else {
        next.add(sectionId);
      }
      return next;
    });
  };

  const scrollToSubsection = (subsectionId) => {
    setActiveSubsection(subsectionId);
    const el = document.getElementById(`guide-${subsectionId}`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
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
      if (
        matchingSubs.length > 0 ||
        section.title.toLowerCase().includes(q)
      ) {
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
      const allIds = new Set(filteredSections.map(s => s.id));
      setExpandedSections(allIds);
    }
  }, [searchQuery, filteredSections]);

  return (
    <div className={`guide-page ${isDark ? 'dark' : ''}`}>
      {/* Header */}
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
        {/* Sidebar nav */}
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
                        onClick={() => {
                          if (!expandedSections.has(section.id)) toggleSection(section.id);
                          scrollToSubsection(sub.id);
                        }}
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

        {/* Main content */}
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
                  <button
                    className="guide-section-header"
                    onClick={() => toggleSection(section.id)}
                  >
                    <div className="guide-section-header-left">
                      <Icon size={20} />
                      <h2>{section.title}</h2>
                    </div>
                    {isExpanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
                  </button>
                  {isExpanded && (
                    <div className="guide-section-body">
                      {section.subsections.map(sub => (
                        <article
                          key={sub.id}
                          id={`guide-${sub.id}`}
                          className="guide-subsection"
                        >
                          <h3>{searchQuery ? highlightMatch(sub.title, searchQuery) : sub.title}</h3>
                          <div
                            className="guide-text"
                            dangerouslySetInnerHTML={{
                              __html: renderMarkdown(
                                searchQuery ? highlightMatch(sub.content, searchQuery) : sub.content
                              ),
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
