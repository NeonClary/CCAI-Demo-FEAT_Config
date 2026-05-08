import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { HelpCircle } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { useAppConfig } from '../contexts/AppConfigContext';
import Sidebar from '../components/Sidebar';
import AppHeader from '../components/AppHeader';
import Icon from '../components/canvas/CanvasIcon';
import {
  INSIGHTS, WIDGET_CATALOG, DEFAULT_LAYOUT, EMPTY_STATE, WORKSPACE_PRESETS,
} from '../components/canvas/canvasData';
import {
  BibliographyWidget, KanbanWidget, PomodoroWidget, WritingWidget,
  DeadlinesWidget, BudgetWidget, ReadingQueueWidget, NotesWidget,
  HabitsWidget, GoalsWidget, MeetingsWidget,
  OutlineWidget, HighlightsWidget, LatexWidget,
  CalendarWidget, DocumenterWidget, ActivityWidget,
  StubWidget,
} from '../components/canvas/CanvasWidgets';
import {
  Reviewer2Widget, DevilsAdvocateWidget, ScopeRealismWidget,
  ReviewerModal, DevilsModal, ScopeModal,
} from '../components/canvas/CanvasCriticWidgets';
import {
  AddCitationModal, AddTaskModal, AddDeadlineModal, LogWordsModal,
  ConfirmRemoveModal, ReadingPaperModal, BudgetItemModal,
  NoteModal, HabitModal, GoalModal, MeetingModal,
  PaletteModal, CommandPaletteModal, GlobalSearchModal,
} from '../components/canvas/CanvasModals';
import CanvasWelcomeTour from '../components/canvas/CanvasWelcomeTour';
import DeliverablesView, { TEMPLATES as DELIVERABLE_TEMPLATES } from '../components/canvas/CanvasDeliverables';
import '../styles/CanvasPage.css';

const LAYOUT_KEY = 'canvas-layout-v2';
const STATES_KEY = 'canvas-states-v2';
const VIEW_KEY = 'canvas-view-v2';

function renderWidget(type, state, setState, openModal, allStates) {
  const props = { state, setState, openModal, allStates };
  switch (type) {
    case 'bibliography': return <BibliographyWidget {...props}/>;
    case 'kanban': return <KanbanWidget {...props}/>;
    case 'pomodoro': return <PomodoroWidget {...props}/>;
    case 'writing': return <WritingWidget {...props}/>;
    case 'deadlines': return <DeadlinesWidget {...props}/>;
    case 'budget': return <BudgetWidget {...props}/>;
    case 'reading-queue': return <ReadingQueueWidget {...props}/>;
    case 'notes': return <NotesWidget {...props}/>;
    case 'habits': return <HabitsWidget {...props}/>;
    case 'goals': return <GoalsWidget {...props}/>;
    case 'meeting-log': return <MeetingsWidget {...props}/>;
    case 'reviewer-2': return <Reviewer2Widget {...props}/>;
    case 'devils-advocate': return <DevilsAdvocateWidget {...props}/>;
    case 'scope-realism': return <ScopeRealismWidget {...props}/>;
    case 'outline': return <OutlineWidget {...props}/>;
    case 'highlights': return <HighlightsWidget {...props}/>;
    case 'latex': return <LatexWidget {...props}/>;
    case 'calendar': return <CalendarWidget {...props}/>;
    case 'documenter': return <DocumenterWidget {...props}/>;
    case 'activity': return <ActivityWidget {...props}/>;
    default: {
      const meta = WIDGET_CATALOG.find(w => w.type === type);
      return <StubWidget meta={meta}/>;
    }
  }
}

function CanvasWidget({ widget, isDragging, isDragOver, onDragStart, onDragOver, onDragEnd, onDrop, state, setState, onRemove, onResize, openModal, allStates }) {
  const meta = WIDGET_CATALOG.find(w => w.type === widget.type);
  if (!meta) return null;
  const sizes = ['S', 'M', 'L'];
  const cycleSize = () => onResize(widget.id, sizes[(sizes.indexOf(widget.size) + 1) % sizes.length]);

  return (
    <div
      className={`widget size-${widget.size} ${meta.critic ? 'critic' : ''} ${isDragging ? 'dragging' : ''} ${isDragOver ? 'drag-over' : ''}`}
      data-widget-id={widget.id}
      data-widget-type={widget.type}
      onDragOver={(e) => { e.preventDefault(); onDragOver(widget.id); }}
      onDrop={(e) => { e.preventDefault(); onDrop(widget.id); }}
    >
      <div
        className="widget-head"
        draggable
        onDragStart={(e) => { onDragStart(widget.id); e.dataTransfer.effectAllowed = 'move'; }}
        onDragEnd={onDragEnd}
      >
        <span className="drag-grip"><Icon name="grip" size={14}/></span>
        <div className="widget-icon"><Icon name={meta.icon} size={14}/></div>
        <div className="widget-title">{meta.name}</div>
        {meta.critic && <span className="widget-tag">wedge</span>}
        <span className="size-pill" onClick={cycleSize} title="Cycle size S → M → L">{widget.size}</span>
        <div className="widget-actions">
          <button className="icon-btn" onClick={() => onRemove(widget.id, meta.name)} title="Remove"><Icon name="trash" size={13}/></button>
        </div>
      </div>
      <div className="widget-body">
        {renderWidget(widget.type, state, setState, openModal, allStates)}
      </div>
    </div>
  );
}

function InsightsView({ widgetStates, setWidgetStates }) {
  const [pinned, setPinned] = useState(new Set(INSIGHTS.filter(i => i.pinned).map(i => i.id)));
  const togglePin = (id) => {
    const n = new Set(pinned);
    if (n.has(id)) n.delete(id); else n.add(id);
    setPinned(n);
  };

  // Strip HTML, take first 80 chars for the kanban card title.
  const insightToTaskTitle = (ins) => {
    const plain = (ins.bullets[0] || ins.summary || ins.title).replace(/<[^>]+>/g, '');
    return plain.length > 80 ? plain.slice(0, 77) + '…' : plain;
  };

  const sendToKanban = (ins) => {
    if (!setWidgetStates) return;
    const kanban = widgetStates.kanban || EMPTY_STATE.kanban;
    const card = {
      id: 'k' + Date.now(),
      col: 'todo',
      title: insightToTaskTitle(ins),
      priority: 'med',
      meta: `from Insights · ${ins.title}`,
    };
    setWidgetStates(s => ({ ...s, kanban: { ...kanban, cards: [...kanban.cards, card] } }));
    window.dispatchEvent(new CustomEvent('canvas-toast', { detail: { msg: 'Sent to Kanban (To Do)', kind: 'success' } }));
  };

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Insights</h1>
          <div className="page-sub">AI-synthesized from your research conversations · {INSIGHTS.length} sections</div>
        </div>
        <div className="page-meta">
          <span className="dot"/>
          <span>updated 3 min ago</span>
          <button className="icon-btn" title="Refresh"><Icon name="refresh" size={14}/></button>
        </div>
      </div>
      <div className="insight-grid">
        {INSIGHTS.map(ins => (
          <div key={ins.id} className="insight">
            <div className="insight-head">
              <div className="insight-icon"><Icon name={ins.icon} size={15}/></div>
              <div className="insight-title">{ins.title}</div>
              <div className="confidence">
                <div className="conf-bar"><i style={{ width: ins.confidence + '%' }}/></div>
                <span>{ins.confidence}%</span>
              </div>
            </div>
            <div className="insight-body">
              <div>{ins.summary}</div>
              <ul>
                {ins.bullets.map((b, i) => <li key={i} dangerouslySetInnerHTML={{ __html: b }}/>)}
              </ul>
            </div>
            <div className="insight-actions">
              {/* TODO(LLM): wire "Ask follow-up" to chat endpoint with insight context */}
              <button className="chip" disabled title="Needs LLM endpoint"><Icon name="message" size={11}/>Ask follow-up</button>
              <button className="chip" onClick={() => sendToKanban(ins)}><Icon name="task" size={11}/>To task</button>
              {/* TODO(LLM): wire "Cite" to search Bibliography for the source paper */}
              <button className="chip" disabled title="Coming soon"><Icon name="cite" size={11}/>Cite</button>
              <button className="chip"><Icon name="expand" size={11}/>Expand</button>
              <button className={`chip ${pinned.has(ins.id) ? 'pinned' : ''}`} onClick={() => togglePin(ins.id)}>
                <Icon name="pin" size={11}/>{pinned.has(ins.id) ? 'Pinned' : 'Pin'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

function PresetPicker({ onPick }) {
  return (
    <div className="canvas-presets">
      <div className="canvas-presets-head">
        <div className="canvas-presets-title">Start from a preset</div>
        <div className="canvas-presets-sub">Or skip and add widgets one at a time.</div>
      </div>
      <div className="canvas-presets-grid">
        {WORKSPACE_PRESETS.map(p => (
          <button key={p.id} className="canvas-preset-card" onClick={() => onPick(p)}>
            <div className="canvas-preset-icon"><Icon name={p.icon} size={18}/></div>
            <div className="canvas-preset-content">
              <div className="canvas-preset-name">{p.name}</div>
              <div className="canvas-preset-desc">{p.desc}</div>
              <div className="canvas-preset-meta">{p.layout.length} widgets</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function WorkspaceView({ openModal, layout, setLayout, widgetStates, setWidgetStates }) {
  const [dragId, setDragId] = useState(null);
  const [dragOverId, setDragOverId] = useState(null);

  const onDragStart = (id) => setDragId(id);
  const onDragOver = (id) => { if (id !== dragId) setDragOverId(id); };
  const onDragEnd = () => { setDragId(null); setDragOverId(null); };
  const onDrop = (targetId) => {
    if (!dragId || dragId === targetId) { onDragEnd(); return; }
    const next = [...layout];
    const fromIdx = next.findIndex(w => w.id === dragId);
    const toIdx = next.findIndex(w => w.id === targetId);
    const [moved] = next.splice(fromIdx, 1);
    next.splice(toIdx, 0, moved);
    setLayout(next);
    onDragEnd();
  };

  const setWState = (type) => (updater) => {
    setWidgetStates(s => ({
      ...s,
      [type]: typeof updater === 'function' ? updater(s[type]) : updater,
    }));
  };

  const removeWidget = (id, label) => {
    openModal('confirm-remove', {
      label,
      onConfirm: () => {
        setLayout(l => l.filter(w => w.id !== id));
        window.dispatchEvent(new CustomEvent('canvas-toast', { detail: { msg: label + ' removed', kind: 'success' } }));
      },
    });
  };

  const resizeWidget = (id, size) => setLayout(l => l.map(w => w.id === id ? { ...w, size } : w));

  // Each widget starts from scratch — fresh empty state, no demo content.
  const addWidget = (meta) => {
    const id = 'w-' + Date.now();
    setLayout(l => [...l, { id, type: meta.type, size: meta.defaultSize, critic: meta.critic }]);
    if (EMPTY_STATE[meta.type]) {
      setWidgetStates(s => ({ ...s, [meta.type]: JSON.parse(JSON.stringify(EMPTY_STATE[meta.type])) }));
    }
  };

  const applyPreset = (preset) => {
    setLayout(preset.layout.map(w => ({ ...w })));
    // Seed empty state for any widget types not already present
    const seeds = {};
    preset.layout.forEach(w => {
      if (!widgetStates[w.type] && EMPTY_STATE[w.type]) {
        seeds[w.type] = JSON.parse(JSON.stringify(EMPTY_STATE[w.type]));
      }
    });
    if (Object.keys(seeds).length) setWidgetStates(s => ({ ...s, ...seeds }));
    window.dispatchEvent(new CustomEvent('canvas-toast', { detail: { msg: `${preset.name} preset loaded`, kind: 'success' } }));
  };

  const reset = () => {
    if (!window.confirm('Reset workspace? All widgets and content will be cleared.')) return;
    setLayout([]);
    setWidgetStates({});
    localStorage.removeItem(LAYOUT_KEY);
    localStorage.removeItem(STATES_KEY);
  };

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Workspace</h1>
          <div className="page-sub">{layout.length} widgets · {layout.filter(w => w.critic).length} anti-yes-man · drag headers to reorder, click size pill to resize</div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-ghost" onClick={reset} title="Reset layout"><Icon name="reset" size={13}/>Reset</button>
          <button className="btn btn-primary" onClick={() => openModal('palette', {
            layout, onAdd: addWidget,
          })}><Icon name="plus" size={13}/>Add widget</button>
        </div>
      </div>
      {layout.length === 0 && (
        <PresetPicker onPick={applyPreset}/>
      )}
      <div className="workspace">
        {layout.length === 0 && (
          <div className="empty-cell">
            <Icon name="layout" size={28} style={{ color: 'var(--canvas-text-4)' }}/>
            <div style={{ fontSize: 14, color: 'var(--canvas-text-2)', fontWeight: 500 }}>Or build from scratch</div>
            <button className="btn btn-primary" onClick={() => openModal('palette', { layout, onAdd: addWidget })} style={{ marginTop: 6 }}>
              <Icon name="plus" size={13}/>Add your first widget
            </button>
          </div>
        )}
        {layout.map((w) => (
          <CanvasWidget
            key={w.id}
            widget={w}
            isDragging={dragId === w.id}
            isDragOver={dragOverId === w.id}
            onDragStart={onDragStart}
            onDragOver={onDragOver}
            onDragEnd={onDragEnd}
            onDrop={onDrop}
            state={widgetStates[w.type] ?? (EMPTY_STATE[w.type] ?? {})}
            setState={setWState(w.type)}
            onRemove={removeWidget}
            onResize={resizeWidget}
            openModal={openModal}
            allStates={widgetStates}
          />
        ))}
      </div>
    </>
  );
}

function ModalRouter({ modal, onClose }) {
  if (!modal) return null;
  const handleBackdropClick = (e) => { if (e.target === e.currentTarget) onClose(); };
  let content = null;
  switch (modal.kind) {
    case 'palette':         content = <PaletteModal data={modal.data} onClose={onClose}/>; break;
    case 'add-citation':    content = <AddCitationModal data={modal.data} onClose={onClose}/>; break;
    case 'add-task':        content = <AddTaskModal data={modal.data} onClose={onClose}/>; break;
    case 'add-deadline':    content = <AddDeadlineModal data={modal.data} onClose={onClose}/>; break;
    case 'log-words':       content = <LogWordsModal data={modal.data} onClose={onClose}/>; break;
    case 'confirm-remove':  content = <ConfirmRemoveModal data={modal.data} onClose={onClose}/>; break;
    case 'reviewer-2':      content = <ReviewerModal data={modal.data} onClose={onClose}/>; break;
    case 'devils-advocate': content = <DevilsModal data={modal.data} onClose={onClose}/>; break;
    case 'scope-realism':   content = <ScopeModal data={modal.data} onClose={onClose}/>; break;
    case 'reading-paper':   content = <ReadingPaperModal data={modal.data} onClose={onClose}/>; break;
    case 'budget-item':     content = <BudgetItemModal data={modal.data} onClose={onClose}/>; break;
    case 'note':            content = <NoteModal data={modal.data} onClose={onClose}/>; break;
    case 'habit':           content = <HabitModal data={modal.data} onClose={onClose}/>; break;
    case 'goal':            content = <GoalModal data={modal.data} onClose={onClose}/>; break;
    case 'meeting':         content = <MeetingModal data={modal.data} onClose={onClose}/>; break;
    case 'command':         content = <CommandPaletteModal data={modal.data} onClose={onClose}/>; break;
    case 'global-search':   content = <GlobalSearchModal data={modal.data} onClose={onClose}/>; break;
    default: return null;
  }
  return <div className="canvas-modal-backdrop" onClick={handleBackdropClick}>{content}</div>;
}

function ToastStack() {
  const [toasts, setToasts] = useState([]);
  useEffect(() => {
    const handler = (e) => {
      const id = Date.now() + Math.random();
      setToasts(t => [...t, { id, ...e.detail }]);
      setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 3500);
    };
    window.addEventListener('canvas-toast', handler);
    return () => window.removeEventListener('canvas-toast', handler);
  }, []);
  return (
    <div className="toast-stack">
      {toasts.map(t => (
        <div key={t.id} className={`toast ${t.kind || 'success'}`}>
          <Icon name={t.kind === 'critic' ? 'gavel' : t.kind === 'danger' ? 'alert' : 'check'} size={14}/>
          <span>{t.msg}</span>
        </div>
      ))}
    </div>
  );
}


const CanvasPage = ({ user, authToken, onNavigateToHome, onNavigateToChat, onSignOut }) => {
  const { theme, toggleTheme } = useTheme();
  useAppConfig();
  const [view, setView] = useState(() => localStorage.getItem(VIEW_KEY) || 'workspace');
  const [modal, setModal] = useState(null);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [tourForceShow, setTourForceShow] = useState(0);

  const [layout, setLayout] = useState(() => {
    try {
      const saved = localStorage.getItem(LAYOUT_KEY);
      return saved ? JSON.parse(saved) : DEFAULT_LAYOUT;
    } catch { return DEFAULT_LAYOUT; }
  });
  const [widgetStates, setWidgetStates] = useState(() => {
    try {
      const saved = localStorage.getItem(STATES_KEY);
      return saved ? JSON.parse(saved) : {};
    } catch { return {}; }
  });

  useEffect(() => { localStorage.setItem(LAYOUT_KEY, JSON.stringify(layout)); }, [layout]);
  useEffect(() => { localStorage.setItem(STATES_KEY, JSON.stringify(widgetStates)); }, [widgetStates]);
  useEffect(() => { localStorage.setItem(VIEW_KEY, view); }, [view]);

  // Apply canvas theme attribute on body for scoped styling
  useEffect(() => {
    document.body.dataset.canvasTheme = theme;
    return () => { delete document.body.dataset.canvasTheme; };
  }, [theme]);

  const openModal = useCallback((kind, data = {}) => setModal({ kind, data }), []);
  const closeModal = useCallback(() => setModal(null), []);

  const exportWorkspace = useCallback(() => {
    const data = { layout, states: widgetStates };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'canvas-workspace.json';
    a.click();
    window.dispatchEvent(new CustomEvent('canvas-toast', { detail: { msg: 'Workspace exported as JSON', kind: 'success' } }));
  }, [layout, widgetStates]);

  const openCommandPalette = useCallback(() => {
    openModal('command', {
      layout,
      onSetView: (v) => setView(v),
      onAddWidget: (meta) => {
        const id = 'w-' + Date.now();
        setLayout(l => [...l, { id, type: meta.type, size: meta.defaultSize, critic: meta.critic }]);
        if (EMPTY_STATE[meta.type]) {
          setWidgetStates(s => ({ ...s, [meta.type]: JSON.parse(JSON.stringify(EMPTY_STATE[meta.type])) }));
        }
      },
      onToggleTheme: toggleTheme,
      onExport: exportWorkspace,
    });
  }, [openModal, layout, toggleTheme, exportWorkspace]);

  const openGlobalSearch = useCallback(() => {
    openModal('global-search', { states: widgetStates });
  }, [openModal, widgetStates]);

  // Esc closes modal, ⌘K opens command palette, ⌘/ opens global content search,
  // ? opens the welcome tour for help (matches the icon in the topbar).
  useEffect(() => {
    const k = (e) => {
      if (e.key === 'Escape') closeModal();
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        openCommandPalette();
      }
      if ((e.metaKey || e.ctrlKey) && e.key === '/') {
        e.preventDefault();
        openGlobalSearch();
      }
      // ? key (Shift+/) — only when the user isn't typing in an input
      if (e.key === '?' && !['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {
        e.preventDefault();
        setTourForceShow(n => n + 1);
      }
    };
    window.addEventListener('keydown', k);
    return () => window.removeEventListener('keydown', k);
  }, [closeModal, openCommandPalette, openGlobalSearch]);

  // Highlight a widget when picked from the sidebar
  const flashScrollTo = (selector) => {
    const el = document.querySelector(selector);
    if (!el) return;
    el.scrollIntoView({ block: 'center', behavior: 'smooth' });
    el.style.boxShadow = '0 0 0 2px var(--canvas-accent), 0 0 24px var(--canvas-accent-glow)';
    setTimeout(() => { el.style.boxShadow = ''; }, 1400);
  };

  // Workspace: group widgets by category for the new sidebar
  const widgetGroups = useMemo(() => {
    const groups = {};
    layout.forEach(w => {
      const meta = WIDGET_CATALOG.find(m => m.type === w.type);
      if (!meta) return;
      const cat = meta.cat;
      (groups[cat] ||= { id: cat, label: cat, items: [] }).items.push({
        id: w.id,
        label: meta.name,
        icon: meta.icon,
        critic: meta.critic,
        onClick: () => flashScrollTo(`[data-widget-id="${w.id}"]`),
      });
    });
    // Order: critic last
    const order = ['research', 'writing', 'project', 'wellness', 'career', 'data', 'practical', 'critic'];
    return order.map(c => groups[c]).filter(Boolean);
  }, [layout]);

  // Deliverables: list of projects with sections + history actions
  const deliverableProjects = useMemo(() => {
    try {
      const dStore = JSON.parse(localStorage.getItem('canvas-deliverables-v2') || '{}');
      const projects = Object.values(dStore.projects || {});
      return projects.map(p => {
        const t = DELIVERABLE_TEMPLATES.find(x => x.id === p.templateId);
        return {
          id: p.id,
          name: p.name,
          icon: t?.icon || 'book',
          versions: p.versions?.length || 0,
          isActive: p.id === dStore.activeProjectId,
          sections: (t?.sections || []).map(s => ({
            id: s.id,
            name: s.name,
            wc: ((p.sections || {})[s.id] || '').trim().split(/\s+/).filter(Boolean).length,
            onClick: () => {
              if (p.id !== dStore.activeProjectId) {
                // Open this project first; section scroll happens after a tick.
                const next = { ...dStore, activeProjectId: p.id };
                localStorage.setItem('canvas-deliverables-v2', JSON.stringify(next));
                window.dispatchEvent(new Event('storage'));
              }
              setTimeout(() => flashScrollTo(`#notion-section-${s.id}`), 80);
            },
          })),
          onOpen: () => {
            const next = { ...dStore, activeProjectId: p.id };
            localStorage.setItem('canvas-deliverables-v2', JSON.stringify(next));
            window.dispatchEvent(new Event('storage'));
          },
        };
      });
    } catch { return []; }
    // re-derive when view or layout changes (layout proxy for "user did something")
  }, [view, layout, widgetStates]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="canvas-page-with-sidebar" data-canvas-theme={theme}>
      <Sidebar
        user={user}
        authToken={authToken}
        onSignOut={onSignOut}
        onSidebarToggle={setIsSidebarCollapsed}
        isMobileOpen={isMobileMenuOpen}
        onMobileToggle={setIsMobileMenuOpen}
        onNavigateToCanvas={() => {}}
        onSelectSession={(id) => onNavigateToChat && onNavigateToChat(id)}
        onNewChat={() => onNavigateToChat && onNavigateToChat()}
        pageContext="canvas"
        canvasSubview={view}
        widgetGroups={widgetGroups}
        deliverableProjects={deliverableProjects}
      />
      <div className={`canvas-main-area ${isSidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        <div className="canvas-app-shell">
          <AppHeader
            currentPage={`canvas-${view}`}
            onNavigateToHome={onNavigateToHome}
            onNavigateToChat={onNavigateToChat}
            onNavigateToCanvas={(v) => setView(v || 'workspace')}
            onMobileMenu={() => setIsMobileMenuOpen(true)}
          >
            <button className="icon-btn" onClick={() => setTourForceShow(n => n + 1)} title="Show tour">
              <HelpCircle size={18}/>
            </button>
            <button className="icon-btn" onClick={openGlobalSearch} title="Search canvas content (⌘/)">
              <Icon name="search" size={16}/>
            </button>
            <button className="icon-btn" onClick={openCommandPalette} title="Commands (⌘K)">
              <Icon name="zap" size={16}/>
            </button>
          </AppHeader>
          <div className="canvas-content">
            {view === 'insights' && <InsightsView widgetStates={widgetStates} setWidgetStates={setWidgetStates}/>}
            {view === 'workspace' && <WorkspaceView openModal={openModal} layout={layout} setLayout={setLayout} widgetStates={widgetStates} setWidgetStates={setWidgetStates}/>}
            {view === 'deliverables' && <DeliverablesView allStates={widgetStates}/>}
          </div>
        </div>
      </div>
      <ModalRouter modal={modal} onClose={closeModal}/>
      <ToastStack/>
      <CanvasWelcomeTour key={tourForceShow} forceShow={tourForceShow > 0}/>
      <ShortcutHint/>
    </div>
  );
};

// Subtle floating hint bar showing the most-used keyboard shortcuts.
// Auto-hides on small screens and after the first 12s, until the user hovers.
function ShortcutHint() {
  const [visible, setVisible] = useState(true);
  useEffect(() => {
    const t = setTimeout(() => setVisible(false), 12000);
    return () => clearTimeout(t);
  }, []);
  return (
    <div
      className={`canvas-shortcut-hint ${visible ? 'visible' : ''}`}
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      <span><kbd>⌘</kbd><kbd>K</kbd> commands</span>
      <span><kbd>⌘</kbd><kbd>/</kbd> search</span>
      <span><kbd>?</kbd> help</span>
    </div>
  );
}

export default CanvasPage;
