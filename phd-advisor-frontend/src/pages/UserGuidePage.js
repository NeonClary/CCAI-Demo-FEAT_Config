import React, { useState, useMemo, useRef, useEffect } from 'react';
import {
  Search, ArrowLeft, ChevronDown, ChevronRight,
  MessageSquare, Upload, BookOpen, Brain,
  Users, GraduationCap, KeyRound, Layout
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
        content: `When you first visit the app, click **Get Started** on the homepage. You'll be taken to the signup page where you can create an account with your name, email, and password. After signing up, you'll be logged in automatically and taken to the chat interface.`
      },
      {
        id: 'onboarding',
        title: 'Completing Your Profile',
        content: `After your first login, a "Tell us about yourself" chat will appear. This onboarding conversation asks about your major, year, goals, and preferences so the advisors can personalize their responses. You can also fill out your profile manually by clicking **Profile** in the sidebar menu. The more information you provide, the better tailored the advice will be.`
      },
      {
        id: 'navigation',
        title: 'Navigating the App',
        content: `The app has three main areas:\n\n- **Chat** — The main interface where you ask questions and receive advice from AI advisors.\n- **Canvas** — A research insights page that organizes key takeaways from your conversations.\n- **Home** — The landing page with an overview of the app's features.\n\nUse the sidebar on the left to switch between chat sessions, start new conversations, or access the Canvas. The home button in the header takes you back to the landing page.`
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
        content: `Type your question in the input box at the bottom of the chat and press Enter or click the send button. You can ask about anything related to college life — academics, career planning, study tips, campus resources, well-being, or writing help.\n\nIf your question is too vague, the system may ask you to clarify with a follow-up question and clickable suggestion buttons.`
      },
      {
        id: 'panel-vs-single',
        title: 'Panel Mode vs. Single Answer',
        content: `You can toggle between two response modes using the button next to the chat input:\n\n- **Panel Mode** (three columns icon) — Three advisors respond independently, each from their own specialty. Their responses appear as a carousel you can swipe through.\n- **Single Answer** (document icon) — All advisors' insights are merged into one synthesized response that combines the best of each perspective.\n\nPanel mode is great for seeing diverse viewpoints. Single mode is faster to read when you just want one consolidated answer.`
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
        content: `The app includes a panel of AI advisors, each with a different specialty. When you ask a question, the system intelligently selects the three most relevant advisors to respond. Each advisor provides advice through their unique lens — so you get well-rounded guidance on every question.\n\nAdvisors are selected dynamically based on what you ask. A question about choosing a major will get different advisors than a question about managing stress.`
      },
      {
        id: 'academic-planner',
        title: 'Academic Planner',
        content: `**Specialty:** Course & degree planning\n\nHelps with choosing majors and minors, building four-year plans, understanding prerequisites, and navigating registration. Best for questions about degree requirements, credit planning, and course sequencing.`
      },
      {
        id: 'career-coach',
        title: 'Career Coach',
        content: `**Specialty:** Internships & professional development\n\nHelps with resumes, cover letters, internship searches, interview prep, and career exploration. Best for questions about building professional skills and planning your career path.`
      },
      {
        id: 'study-strategist',
        title: 'Study Strategist',
        content: `**Specialty:** Learning techniques & academic performance\n\nHelps with study methods, time management, test preparation, and building effective academic habits. Advice is grounded in cognitive science research on how people learn best.`
      },
      {
        id: 'campus-guide',
        title: 'Campus Guide',
        content: `**Specialty:** University life & resources\n\nHelps with campus resources, student organizations, housing, financial aid, and navigating university services. Best for questions about making the most of your college experience.`
      },
      {
        id: 'wellness-advisor',
        title: 'Wellness Advisor',
        content: `**Specialty:** Student well-being & balance\n\nHelps with stress management, mental health, work-life balance, and self-care. Takes a compassionate, whole-person approach and can point you to campus counseling and support resources.`
      },
      {
        id: 'writing-tutor',
        title: 'Writing Tutor',
        content: `**Specialty:** Academic writing & communication\n\nHelps with essay structure, research papers, citations, grammar, and editing. Can review uploaded documents and provide specific feedback on your writing.`
      },
    ]
  },
  {
    id: 'course-advisor',
    title: 'Course Advisor Agent',
    icon: GraduationCap,
    subsections: [
      {
        id: 'course-advisor-overview',
        title: 'How the Course Advisor Works',
        content: `The Course Advisor is a specialized agent that has access to CU Boulder's live course database. Unlike the general advisors, it can look up real course sections, professor ratings, schedules, and enrollment data.\n\nWhen you ask about specific courses (e.g., "Find CSCI 1300 sections"), the system automatically routes your question to the Course Advisor for a data-driven response.`
      },
      {
        id: 'course-search',
        title: 'Searching for Courses',
        content: `You can search for courses using natural language. Examples:\n\n- "Find CSCI 1300 sections for Spring 2026"\n- "What ENES 1010 sections have professors rated 4 or higher?"\n- "Show me afternoon MATH 2400 sections with no 8am classes"\n\nThe advisor will return specific section numbers, instructor names, professor ratings, schedules, and locations.`
      },
      {
        id: 'available-semesters',
        title: 'Available Semesters',
        content: `The course database currently includes data for:\n\n- **Fall 2025**\n- **Spring 2026**\n- **Summer 2026**\n\nIf you don't specify a semester, the system defaults to the current one. You can ask about any available semester, and the data is refreshed monthly.`
      },
      {
        id: 'follow-up-queries',
        title: 'Follow-up Questions',
        content: `After an initial course search, you can ask follow-up questions without repeating all your criteria. The system remembers your previous search and applies modifications:\n\n- "What about Fall semester?" — Keeps all your previous filters but switches to Fall.\n- "Any sections with better professors?" — Adds a higher rating filter.\n- "Show me morning options instead" — Changes the time preference.\n\nThe system will automatically carry forward your course code, preferences, and other filters.`
      },
      {
        id: 'professor-ratings',
        title: 'Professor Ratings',
        content: `Course search results include professor quality data:\n\n- **Rating** — Overall quality rating (out of 5)\n- **Difficulty** — Course difficulty rating (out of 5)\n- **Would Take Again** — Percentage of students who would retake\n\nYou can filter by minimum professor rating (e.g., "professors rated 4+"). When no exact matches are found, the advisor will suggest alternatives with relaxed criteria.`
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
        content: `Click the **paperclip icon** next to the chat input to open the upload area. You can drag and drop a file or click to browse. Supported file types:\n\n- **PDF** — Research papers, syllabi, transcripts\n- **DOCX** — Word documents, essays, resumes\n- **TXT** — Plain text files\n\nMaximum file size is 10MB.`
      },
      {
        id: 'how-rag-works',
        title: 'How Document Context Works',
        content: `When you upload a document, it's processed and indexed so the advisors can reference it in their responses. The system uses a technique called **Retrieval-Augmented Generation (RAG)** — it finds the most relevant sections of your document for each question you ask.\n\nFor example, if you upload a resume and ask "How can I improve my resume?", the Career Coach will analyze your actual resume content and give specific, personalized feedback.`
      },
      {
        id: 'document-tips',
        title: 'Tips for Best Results',
        content: `- Upload documents **before** asking questions about them.\n- Reference your document in your question: "Based on my resume, what should I improve?"\n- Each chat session has its own document context. If you start a new chat, you'll need to re-upload.\n- The Writing Tutor is especially good at reviewing uploaded essays and papers.\n- The Academic Planner can analyze uploaded syllabi and degree audits.`
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
        content: `The Canvas is a dynamic summary page that organizes insights from your chat conversations into structured sections. Think of it as a living document that captures the key takeaways, action items, and recommendations from all your advisor interactions.`
      },
      {
        id: 'canvas-sections',
        title: 'Canvas Sections',
        content: `The Canvas organizes information into themed sections such as academic plans, career goals, study strategies, and wellness notes. Each section is expandable and shows the most relevant insights from your conversations.\n\nYou can refresh the Canvas to pull in the latest insights from recent chats. The Canvas can also be printed or exported for your records.`
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
        content: `The **Clear User Data** option in the sidebar menu lets you selectively clear:\n\n- **Profile** — Resets your onboarding answers and profile information\n- **Chat History** — Deletes all saved chat sessions\n- **Canvas** — Clears all Canvas content\n\nThis is useful if you want a fresh start without deleting your account.`
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
        content: `The more specific your question, the better the advice:\n\n- **Vague:** "Help me with classes"\n- **Better:** "I'm a sophomore CS major — how should I plan my Fall course load if I want to take CSCI 2270 and CSCI 2400?"\n\nInclude context about your year, major, goals, and constraints. The advisors use your profile information automatically, but adding details in your question helps them give more targeted responses.`
      },
      {
        id: 'using-multiple-advisors',
        title: 'Getting the Most from Multiple Advisors',
        content: `Use **Panel Mode** when you want diverse perspectives on a decision. For example, asking "Should I take a summer internship or summer classes?" will get different angles from the Career Coach, Academic Planner, and Wellness Advisor.\n\nIf one advisor's response resonates, **reply directly** to continue that thread. You can always switch back to panel mode for your next question.`
      },
      {
        id: 'document-workflow',
        title: 'Document Review Workflow',
        content: `For the best document review experience:\n\n1. Upload your document (essay, resume, syllabus, etc.)\n2. Ask a specific question: "Review my resume and suggest improvements for tech internships"\n3. Follow up on specific feedback: "Can you elaborate on the bullet point suggestions?"\n4. Try asking different advisors — the Writing Tutor focuses on structure and clarity, while the Career Coach focuses on content and impact.`
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
