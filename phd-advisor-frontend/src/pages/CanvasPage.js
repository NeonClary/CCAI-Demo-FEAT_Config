import React, { useState, useEffect, useCallback } from 'react';
import { HelpCircle } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { useAppConfig } from '../contexts/AppConfigContext';
import Sidebar from '../components/Sidebar';
import AppHeader from '../components/AppHeader';
import Icon from '../components/canvas/CanvasIcon';
import {
  INSIGHTS, WIDGET_CATALOG, DEFAULT_LAYOUT, EMPTY_STATE,
} from '../components/canvas/canvasData';
import {
  BibliographyWidget, KanbanWidget, PomodoroWidget, WritingWidget,
  DeadlinesWidget, BudgetWidget, ReadingQueueWidget, NotesWidget,
  HabitsWidget, GoalsWidget, MeetingsWidget,
  OutlineWidget, HighlightsWidget, LatexWidget,
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
  PaletteModal, CommandPaletteModal,
} from '../components/canvas/CanvasModals';
import CanvasWelcomeTour from '../components/canvas/CanvasWelcomeTour';
import '../styles/CanvasPage.css';

const LAYOUT_KEY = 'canvas-layout-v2';
const STATES_KEY = 'canvas-states-v2';
const VIEW_KEY = 'canvas-view-v2';

function renderWidget(type, state, setState, openModal) {
  const props = { state, setState, openModal };
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
    default: {
      const meta = WIDGET_CATALOG.find(w => w.type === type);
      return <StubWidget meta={meta}/>;
    }
  }
}

function CanvasWidget({ widget, isDragging, isDragOver, onDragStart, onDragOver, onDragEnd, onDrop, state, setState, onRemove, onResize, openModal }) {
  const meta = WIDGET_CATALOG.find(w => w.type === widget.type);
  if (!meta) return null;
  const sizes = ['S', 'M', 'L'];
  const cycleSize = () => onResize(widget.id, sizes[(sizes.indexOf(widget.size) + 1) % sizes.length]);

  return (
    <div
      className={`widget size-${widget.size} ${meta.critic ? 'critic' : ''} ${isDragging ? 'dragging' : ''} ${isDragOver ? 'drag-over' : ''}`}
      data-widget-id={widget.id}
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
        {renderWidget(widget.type, state, setState, openModal)}
      </div>
    </div>
  );
}

function InsightsView() {
  const [pinned, setPinned] = useState(new Set(INSIGHTS.filter(i => i.pinned).map(i => i.id)));
  const togglePin = (id) => {
    const n = new Set(pinned);
    if (n.has(id)) n.delete(id); else n.add(id);
    setPinned(n);
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
              <button className="chip"><Icon name="message" size={11}/>Ask follow-up</button>
              <button className="chip"><Icon name="task" size={11}/>To task</button>
              <button className="chip"><Icon name="cite" size={11}/>Cite</button>
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

  const setWState = (type) => (newState) => {
    setWidgetStates(s => ({ ...s, [type]: newState }));
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
      // Always reset to a fresh empty state when a widget is added (even if previously removed)
      setWidgetStates(s => ({ ...s, [meta.type]: JSON.parse(JSON.stringify(EMPTY_STATE[meta.type])) }));
    }
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
      <div className="workspace">
        {layout.length === 0 && (
          <div className="empty-cell">
            <Icon name="layout" size={32} style={{ color: 'var(--canvas-text-4)' }}/>
            <div style={{ fontSize: 14, color: 'var(--canvas-text-2)', fontWeight: 500 }}>Empty workspace</div>
            <div>Add widgets from the palette to start composing your canvas.</div>
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

  // Esc closes modal, ⌘K opens command palette
  useEffect(() => {
    const k = (e) => {
      if (e.key === 'Escape') closeModal();
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        openCommandPalette();
      }
    };
    window.addEventListener('keydown', k);
    return () => window.removeEventListener('keydown', k);
  }, [closeModal, openCommandPalette]);

  const canvasSidebarItems = layout.map(w => {
    const meta = WIDGET_CATALOG.find(m => m.type === w.type);
    return {
      id: w.id,
      label: meta?.name || w.type,
      sub: meta?.cat || '',
      onClick: () => {
        const el = document.querySelector(`[data-widget-id="${w.id}"]`);
        if (el) {
          el.scrollIntoView({ block: 'center', behavior: 'smooth' });
          el.style.boxShadow = '0 0 0 2px var(--canvas-accent), 0 0 24px var(--canvas-accent-glow)';
          setTimeout(() => { el.style.boxShadow = ''; }, 1400);
        }
      },
    };
  });

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
        canvasItems={canvasSidebarItems}
      />
      <div className={`canvas-main-area ${isSidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        <div className="canvas-app-shell">
          <AppHeader
            currentPage="canvas"
            onNavigateToHome={onNavigateToHome}
            onNavigateToChat={onNavigateToChat}
            onNavigateToCanvas={(v) => setView(v || 'workspace')}
            onMobileMenu={() => setIsMobileMenuOpen(true)}
          >
            <button className="icon-btn" onClick={() => setTourForceShow(n => n + 1)} title="Show tour">
              <HelpCircle size={18}/>
            </button>
            <button className="icon-btn" onClick={openCommandPalette} title="Search & commands (⌘K)">
              <Icon name="search" size={16}/>
            </button>
          </AppHeader>
          <div className="canvas-content">
            {view === 'insights'
              ? <InsightsView/>
              : <WorkspaceView openModal={openModal} layout={layout} setLayout={setLayout} widgetStates={widgetStates} setWidgetStates={setWidgetStates}/>}
          </div>
        </div>
      </div>
      <ModalRouter modal={modal} onClose={closeModal}/>
      <ToastStack/>
      <CanvasWelcomeTour key={tourForceShow} forceShow={tourForceShow > 0}/>
    </div>
  );
};

export default CanvasPage;
