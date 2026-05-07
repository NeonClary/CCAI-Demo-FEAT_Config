// Deliverables view — pick a template, fill in structured sections, export.
// Static "missing" checks run locally. AI checks are stubbed (need LLM endpoint).
import React, { useState, useMemo, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Icon from './CanvasIcon';

const fireToast = (msg, kind = 'success') =>
  window.dispatchEvent(new CustomEvent('canvas-toast', { detail: { msg, kind } }));

const STORE_KEY = 'canvas-deliverables-v1';

// ---------- Template definitions ----------
const TEMPLATES = [
  {
    id: 'research-paper',
    name: 'Research Paper',
    desc: 'Abstract → Introduction → Methods → Results → Discussion → References',
    icon: 'book',
    mode: 'paper',
    sections: [
      { id: 'abstract', name: 'Abstract', target: 250, hint: 'One paragraph: question, method, finding, implication.', checks: ['hasNumber', 'hasFinding'] },
      { id: 'intro', name: 'Introduction', target: 1000, hint: 'Frame the problem, state the gap, name your contribution.', checks: ['hasGap', 'hasCitation'] },
      { id: 'methods', name: 'Methods', target: 800, hint: 'Reproducibility-first: subjects, materials, procedure, analysis.', checks: ['hasCitation', 'hasNumber'] },
      { id: 'results', name: 'Results', target: 800, hint: 'Lead with the effect. Numbers + figure refs. No interpretation here.', checks: ['hasNumber', 'hasFigure'] },
      { id: 'discussion', name: 'Discussion', target: 1000, hint: 'What it means, what it doesn\'t, limits, future work.', checks: ['hasLimit', 'hasCitation'] },
      { id: 'refs', name: 'References', target: 0, hint: 'Bibliography list. Drop @keys here from the Bibliography widget.', checks: [] },
    ],
  },
  {
    id: 'nsf-grfp',
    name: 'NSF GRFP',
    desc: 'Personal Statement (3 pages) + Research Plan (2 pages)',
    icon: 'award',
    mode: 'document',
    sections: [
      { id: 'personal', name: 'Personal Statement', target: 1500, hint: 'Background, experiences, broader impacts. Write as a story.', checks: ['hasBroaderImpacts'] },
      { id: 'research', name: 'Research Plan', target: 1000, hint: 'Question, hypothesis, approach, intellectual merit.', checks: ['hasHypothesis', 'hasMerit'] },
    ],
  },
  {
    id: 'conference-abstract',
    name: 'Conference Abstract',
    desc: 'Single section, 250 words. Lead with the result.',
    icon: 'send',
    mode: 'document',
    sections: [
      { id: 'abs', name: 'Abstract', target: 250, hint: 'One paragraph. Lead with finding, end with implication.', checks: ['hasFinding', 'hasNumber'] },
    ],
  },
  {
    id: 'defense-slides',
    name: 'Defense Slides',
    desc: 'Title → Outline → Background → Question → Methods → Results → Discussion → Q&A',
    icon: 'kanban',
    mode: 'slides',
    sections: [
      { id: 'title', name: 'Title slide', target: 30, hint: 'Title, your name, advisor, date.', checks: [] },
      { id: 'outline', name: 'Outline', target: 60, hint: '5–7 bullet points covering the talk arc.', checks: [] },
      { id: 'background', name: 'Background', target: 200, hint: 'Just enough context to follow the question.', checks: ['hasCitation'] },
      { id: 'question', name: 'Question', target: 80, hint: 'Single sentence, falsifiable.', checks: [] },
      { id: 'methods', name: 'Methods', target: 200, hint: 'High-level. Save details for backup slides.', checks: ['hasNumber'] },
      { id: 'results', name: 'Results', target: 300, hint: 'One slide per finding. Lead with the headline.', checks: ['hasFigure', 'hasNumber'] },
      { id: 'discussion', name: 'Discussion', target: 200, hint: 'Implications + limits + next steps.', checks: ['hasLimit'] },
      { id: 'qa', name: 'Anticipated Q&A', target: 300, hint: 'Hardest 5 questions and your answers.', checks: [] },
    ],
  },
  {
    id: 'thesis-chapter',
    name: 'Thesis Chapter',
    desc: 'Standard chapter scaffolding for a dissertation.',
    icon: 'book',
    mode: 'paper',
    sections: [
      { id: 'overview', name: 'Overview', target: 200, hint: 'What this chapter does and why it\'s here.', checks: [] },
      { id: 'background', name: 'Background', target: 1500, hint: 'Lit review focused on this chapter\'s question.', checks: ['hasCitation'] },
      { id: 'methods', name: 'Methods', target: 1500, hint: 'Reproducibility-first.', checks: ['hasCitation', 'hasNumber'] },
      { id: 'results', name: 'Results', target: 2000, hint: 'Findings + figures.', checks: ['hasFigure', 'hasNumber'] },
      { id: 'discussion', name: 'Discussion', target: 1500, hint: 'How it fits the larger thesis.', checks: ['hasLimit'] },
    ],
  },
];

// ---------- Static check rules ----------
const CHECKS = {
  hasNumber: { test: (s) => /\d/.test(s), label: 'Mentions at least one number' },
  hasCitation: { test: (s) => /@\w+/.test(s), label: 'Cites at least one source (@key)' },
  hasFinding: { test: (s) => /\b(we (find|show|report|demonstrate)|finding|result)/i.test(s), label: 'States a finding' },
  hasGap: { test: (s) => /\b(gap|lack|missing|unknown|unclear|despite)/i.test(s), label: 'Names a gap' },
  hasFigure: { test: (s) => /\b(fig(ure)?|table)\.?\s*\d/i.test(s), label: 'References a figure or table' },
  hasLimit: { test: (s) => /\b(limit|caveat|however|future work|did not|cannot)/i.test(s), label: 'Acknowledges a limit' },
  hasBroaderImpacts: { test: (s) => /\b(broader impact|outreach|community|underrepresented|access)/i.test(s), label: 'Addresses broader impacts' },
  hasHypothesis: { test: (s) => /\b(hypothes|predict)/i.test(s), label: 'States a hypothesis or prediction' },
  hasMerit: { test: (s) => /\b(intellectual merit|novel|advances|contribut)/i.test(s), label: 'Frames intellectual merit' },
};

const wordCount = (s) => (s || '').trim().split(/\s+/).filter(Boolean).length;

// ---------- Exporters ----------
const exportMarkdown = (template, sections) => {
  return [
    `# ${template.name}\n`,
    ...template.sections.map(s => `## ${s.name}\n\n${sections[s.id] || ''}\n`),
  ].join('\n');
};
const exportLatex = (template, sections) => {
  return [
    '\\documentclass{article}',
    `\\title{${template.name}}`,
    '\\begin{document}',
    '\\maketitle',
    ...template.sections.map(s => `\n\\section{${s.name}}\n${sections[s.id] || ''}\n`),
    '\\end{document}',
  ].join('\n');
};
const exportHtml = (template, sections) => {
  return [
    '<!doctype html>',
    `<html><head><title>${template.name}</title></head><body>`,
    `<h1>${template.name}</h1>`,
    ...template.sections.map(s => `<section><h2>${s.name}</h2><p>${(sections[s.id] || '').replace(/\n/g, '<br>')}</p></section>`),
    '</body></html>',
  ].join('\n');
};

const downloadFile = (filename, mime, contents) => {
  const blob = new Blob([contents], { type: mime });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
};

// ---------- Component ----------
const DeliverablesView = ({ allStates }) => {
  const [store, setStore] = useState(() => {
    try { return JSON.parse(localStorage.getItem(STORE_KEY) || '{}'); } catch { return {}; }
  });
  useEffect(() => { localStorage.setItem(STORE_KEY, JSON.stringify(store)); }, [store]);

  const activeId = store.activeTemplateId;
  const template = TEMPLATES.find(t => t.id === activeId);
  const sections = (store.templates && store.templates[activeId]) || {};
  const [activeSectionId, setActiveSectionId] = useState(template?.sections[0]?.id);
  const [generatingAi, setGeneratingAi] = useState(false);

  // Keep activeSectionId valid when template changes (re-mount from localStorage,
  // template switch, etc.). Falls back to the first section.
  useEffect(() => {
    if (!template) return;
    const valid = template.sections.some(s => s.id === activeSectionId);
    if (!valid) setActiveSectionId(template.sections[0].id);
  }, [activeId, template, activeSectionId]);

  // TODO(LLM): wire `runAiPass` to backend that returns per-section "missing" notes.
  // const runAiPass = async () => {
  //   const res = await fetch(`${process.env.REACT_APP_API_URL}/api/canvas/deliverable-check`, {
  //     method: 'POST',
  //     body: JSON.stringify({ template: template.id, sections, canvas: allStates }),
  //   });
  //   const { notes } = await res.json();
  //   setStore({ ...store, templates: { ...store.templates, [activeId]: { ...sections, _aiNotes: notes } } });
  // };
  const runAiPass = () => {
    setGeneratingAi(true);
    setTimeout(() => {
      const notes = template.sections.map(s => {
        const text = sections[s.id] || '';
        const wc = wordCount(text);
        if (wc === 0) return { sectionId: s.id, msg: `Empty — start with: "${s.hint}"` };
        if (wc < s.target * 0.3) return { sectionId: s.id, msg: `Thin (${wc} words). Target ${s.target}.` };
        return { sectionId: s.id, msg: `Looks reasonable for length (${wc} words). LLM-pass would suggest specifics here.` };
      });
      setStore(prev => ({
        ...prev,
        templates: { ...prev.templates, [activeId]: { ...sections, _aiNotes: notes } },
      }));
      setGeneratingAi(false);
      fireToast('AI pass complete (stub)');
    }, 700);
  };

  const pickTemplate = (id) => {
    setStore({ ...store, activeTemplateId: id });
    setActiveSectionId(TEMPLATES.find(t => t.id === id).sections[0].id);
  };

  const updateSection = (id, value) => {
    setStore(prev => ({
      ...prev,
      templates: {
        ...prev.templates,
        [activeId]: { ...(prev.templates?.[activeId] || {}), [id]: value },
      },
    }));
  };

  const exportAs = (format) => {
    const filename = `${template.name.replace(/\s+/g, '_')}.${format === 'latex' ? 'tex' : format === 'markdown' ? 'md' : 'html'}`;
    const mime = format === 'html' ? 'text/html' : 'text/plain';
    const contents = format === 'markdown' ? exportMarkdown(template, sections)
      : format === 'latex' ? exportLatex(template, sections)
      : exportHtml(template, sections);
    downloadFile(filename, mime, contents);
    fireToast(`Exported ${filename}`);
  };

  // Aggregated word count
  const totalWords = template ? template.sections.reduce((sum, s) => sum + wordCount(sections[s.id]), 0) : 0;
  const totalTarget = template ? template.sections.reduce((sum, s) => sum + s.target, 0) : 0;

  // Insertable elements from the canvas (citations, quotes, outline nodes, chapter drafts)
  const insertables = useMemo(() => {
    const items = [];
    (allStates?.bibliography?.entries || []).forEach(e => items.push({ kind: 'cite', label: `${e.title}`, snippet: ` (${e.authors}, ${e.year}; @${e.key})` }));
    (allStates?.highlights?.items || []).forEach(h => items.push({ kind: 'quote', label: h.text.slice(0, 60), snippet: `"${h.text}"${h.citeKey ? ` (@${h.citeKey})` : ''}` }));
    (allStates?.outline?.items || []).forEach(o => items.push({ kind: 'outline', label: o.text || '(empty)', snippet: '\n' + '  '.repeat(o.depth) + '- ' + (o.text || '') }));
    (allStates?.writing?.chapters || []).forEach(c => items.push({ kind: 'draft', label: c.name, snippet: c.draft || '' }));
    return items;
  }, [allStates]);

  const insertIntoActive = (snippet) => {
    if (!activeSectionId) return;
    const cur = sections[activeSectionId] || '';
    updateSection(activeSectionId, cur + (cur && !cur.endsWith('\n') ? ' ' : '') + snippet);
    fireToast('Inserted into ' + template.sections.find(s => s.id === activeSectionId)?.name);
  };

  // Empty state — pick a template
  if (!template) {
    return (
      <>
        <div className="page-header">
          <div>
            <h1 className="page-title">Deliverables</h1>
            <div className="page-sub">Pick a template; bring elements in from your canvas; export when ready.</div>
          </div>
        </div>
        <div className="canvas-presets-grid">
          {TEMPLATES.map(t => (
            <button key={t.id} className="canvas-preset-card" onClick={() => pickTemplate(t.id)}>
              <div className="canvas-preset-icon"><Icon name={t.icon} size={18}/></div>
              <div className="canvas-preset-content">
                <div className="canvas-preset-name">{t.name}</div>
                <div className="canvas-preset-desc">{t.desc}</div>
                <div className="canvas-preset-meta">{t.sections.length} sections</div>
              </div>
            </button>
          ))}
        </div>
        {/* TODO(LLM): "Upload project brief → AI generates a custom outline" button.
            Wire to backend that returns a synthesized template:
            const onUpload = async (file) => {
              const text = await file.text();
              const res = await fetch(`${API}/api/canvas/outline-from-brief`, { method:'POST', body: text });
              const { template, sections } = await res.json();
              // Inject as a new template into TEMPLATES at runtime, then pickTemplate(template.id);
            };
        */}
        <div className="canvas-presets" style={{ marginTop: 18 }}>
          <div className="canvas-presets-head">
            <div className="canvas-presets-title">From a project brief</div>
            <div className="canvas-presets-sub">Upload your brief and the AI will draft a custom outline. <em>(Needs LLM endpoint — coming soon.)</em></div>
          </div>
          <button className="btn" disabled title="Needs LLM endpoint">
            <Icon name="download" size={13} style={{ transform: 'rotate(180deg)' }}/>Upload project brief
          </button>
        </div>
      </>
    );
  }

  const aiNotes = sections._aiNotes;

  // Shared header + insertables panel — used by all editor modes.
  const Header = (
    <div className="page-header">
      <div>
        <button className="btn btn-ghost" style={{ padding: '4px 8px', fontSize: 12, marginBottom: 4, color: 'var(--canvas-text-3)' }} onClick={() => setStore({ ...store, activeTemplateId: undefined })}>
          <Icon name="back" size={12}/>Templates
        </button>
        <h1 className="page-title">{template.name}</h1>
        <div className="page-sub">
          {totalWords} / {totalTarget} words · {template.sections.length} {template.mode === 'slides' ? 'slides' : 'sections'}
        </div>
      </div>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <button className="btn btn-ghost" onClick={runAiPass} disabled={generatingAi} title="AI check (stub)">
          {generatingAi ? <><div className="spinner"/></> : <Icon name="sparkles" size={13}/>}
          AI check
        </button>
        <div style={{ position: 'relative' }}>
          <details className="canvas-export-menu">
            <summary className="btn btn-primary"><Icon name="download" size={13}/>Export</summary>
            <div className="canvas-export-menu-list">
              <button onClick={() => exportAs('markdown')}>Markdown (.md)</button>
              <button onClick={() => exportAs('latex')}>LaTeX (.tex)</button>
              <button onClick={() => exportAs('html')}>HTML (.html)</button>
            </div>
          </details>
        </div>
      </div>
    </div>
  );

  const InsertPanel = (
    <div className="deliverable-insertables">
      <div style={{ fontSize: 11, color: 'var(--canvas-text-4)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600, marginBottom: 8 }}>
        From canvas · {insertables.length}
      </div>
      {insertables.length === 0 && (
        <div style={{ padding: 12, fontSize: 11.5, color: 'var(--canvas-text-3)', background: 'var(--canvas-surface)', border: '1px dashed var(--canvas-border-2)', borderRadius: 7 }}>
          Add a Bibliography, Highlights, Outline, or Writing widget to your canvas; their content shows up here for one-click insert.
        </div>
      )}
      {insertables.map((it, i) => (
        <button key={i} onClick={() => insertIntoActive(it.snippet)} className="canvas-insert-row">
          <span className="tag-pill">{it.kind}</span>
          <span style={{ flex: 1, fontSize: 11.5, color: 'var(--canvas-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{it.label}</span>
          <Icon name="plus" size={12} style={{ color: 'var(--canvas-text-3)' }}/>
        </button>
      ))}
    </div>
  );

  // ---------- SLIDES MODE — PowerPoint / Google Slides feel ----------
  if (template.mode === 'slides') {
    const activeIdx = template.sections.findIndex(s => s.id === activeSectionId);
    const active = template.sections[activeIdx] || template.sections[0];
    const text = sections[active.id] || '';
    const aiForSlide = aiNotes && aiNotes.find(n => n.sectionId === active.id);
    // Render body as bullet points if it contains line breaks; otherwise as a paragraph.
    const lines = text.split(/\n+/).map(l => l.trim()).filter(Boolean);

    return (
      <>
        {Header}
        <div className="deliverable-slides-grid">
          {/* Slide thumbnails */}
          <div className="slide-thumbs">
            <div style={{ fontSize: 10, color: 'var(--canvas-text-4)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600, padding: '0 4px 6px' }}>
              {template.sections.length} slides
            </div>
            {template.sections.map((s, i) => {
              const t = sections[s.id] || '';
              const tLines = t.split(/\n+/).map(l => l.trim()).filter(Boolean);
              return (
                <button key={s.id}
                  className={`slide-thumb ${s.id === active.id ? 'active' : ''}`}
                  onClick={() => setActiveSectionId(s.id)}
                  title={s.name}>
                  <div className="slide-thumb-num">{i + 1}</div>
                  <div className="slide-thumb-canvas">
                    <div className="slide-thumb-title">{s.name}</div>
                    <div className="slide-thumb-body">
                      {tLines.slice(0, 3).map((l, j) => <div key={j}>• {l.slice(0, 30)}</div>)}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Big slide canvas */}
          <div>
            <div className="slide-canvas-wrap">
              <div className="slide-canvas">
                <div className="slide-canvas-title">{active.name}</div>
                <div className="slide-canvas-body">
                  {lines.length === 0 ? (
                    <div className="slide-placeholder">{active.hint}</div>
                  ) : lines.length === 1 ? (
                    <div className="slide-paragraph">{lines[0]}</div>
                  ) : (
                    <ul>{lines.map((l, j) => <li key={j}>{l}</li>)}</ul>
                  )}
                </div>
                <div className="slide-canvas-footer">{activeIdx + 1} / {template.sections.length}</div>
              </div>
            </div>

            {/* Edit pane below the canvas (so the slide stays the focus) */}
            <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 11, color: 'var(--canvas-text-4)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>
                  Slide content
                </span>
                <span style={{ fontSize: 11, color: 'var(--canvas-text-3)' }}>· One bullet per line</span>
                <span style={{ flex: 1 }}/>
                <span style={{ fontFamily: 'var(--canvas-mono)', fontSize: 10, color: 'var(--canvas-text-3)' }}>
                  {wordCount(text)}{active.target ? `/${active.target}` : ''} words
                </span>
              </div>
              <textarea
                className="textarea"
                value={text}
                onChange={e => updateSection(active.id, e.target.value)}
                placeholder={active.hint}
                style={{ minHeight: 110, fontSize: 13, lineHeight: 1.6 }}
              />
              {(active.checks || []).length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {active.checks.map(c => {
                    const check = CHECKS[c];
                    if (!check) return null;
                    const passed = check.test(text);
                    return (
                      <span key={c} className="check-pill" data-passed={passed}>
                        {passed ? <Icon name="check" size={10}/> : <span style={{ width: 10, height: 10, borderRadius: 2, border: '1px solid currentColor' }}/>}
                        {check.label}
                      </span>
                    );
                  })}
                </div>
              )}
              {aiForSlide && (
                <div className="review" style={{ borderLeftColor: 'var(--canvas-accent)' }}>
                  <span className="review-tag" style={{ color: 'var(--canvas-accent)' }}>AI suggestion · stub</span>
                  {aiForSlide.msg}
                </div>
              )}
            </div>
          </div>

          {InsertPanel}
        </div>
      </>
    );
  }

  // ---------- PAPER / DOCUMENT MODE — Notion-style single-surface page ----------
  const paperLike = template.mode === 'paper';
  return (
    <>
      {Header}
      <div className="notion-deliverable-grid">
        {/* TOC sidebar — subtle, no boxes */}
        <div className="notion-toc">
          <div className="notion-toc-label">On this page</div>
          {template.sections.map(s => {
            const wc = wordCount(sections[s.id]);
            return (
              <button key={s.id}
                className={`notion-toc-link ${activeSectionId === s.id ? 'active' : ''}`}
                onClick={() => {
                  setActiveSectionId(s.id);
                  const el = document.getElementById(`notion-section-${s.id}`);
                  if (el) el.scrollIntoView({ block: 'start', behavior: 'smooth' });
                }}>
                <span className="notion-toc-link-text">{s.name}</span>
                {wc > 0 && <span className="notion-toc-link-count">{wc}</span>}
              </button>
            );
          })}
        </div>

        {/* The page itself — what you see is what you edit */}
        <div className={`notion-page-wrap ${paperLike ? 'paper' : ''}`}>
          <div className={`notion-page ${paperLike ? 'serif' : ''}`}>
            <h1 className="notion-page-title">{template.name}</h1>
            <div className="notion-page-meta">
              {totalWords} words · {template.sections.length} sections{paperLike ? ' · academic paper' : ''}
            </div>
            {template.sections.map(s => {
              const text = sections[s.id] || '';
              const aiForSection = aiNotes ? aiNotes.find(n => n.sectionId === s.id) : null;
              const failed = (s.checks || []).filter(c => CHECKS[c] && !CHECKS[c].test(text));
              return (
                <div key={s.id} id={`notion-section-${s.id}`} className="notion-block">
                  <h2 className={`notion-h2 ${paperLike ? 'serif' : ''}`}>{s.name}</h2>
                  {!text && <div className="notion-hint">{s.hint}</div>}
                  <NotionTextarea
                    value={text}
                    onChange={(v) => updateSection(s.id, v)}
                    placeholder={`Start writing ${s.name.toLowerCase()}…`}
                    serif={paperLike}
                  />
                  {(s.checks || []).length > 0 && (
                    <div className="notion-block-meta">
                      {s.checks.map(c => {
                        const check = CHECKS[c];
                        if (!check) return null;
                        const passed = check.test(text);
                        return (
                          <span key={c} className="check-pill" data-passed={passed}>
                            {passed ? <Icon name="check" size={10}/> : <span style={{ width: 10, height: 10, borderRadius: 2, border: '1px solid currentColor' }}/>}
                            {check.label}
                          </span>
                        );
                      })}
                      {s.target > 0 && (
                        <span className="check-pill" data-passed={wordCount(text) >= s.target * 0.7}>
                          {wordCount(text)} / {s.target} words
                        </span>
                      )}
                    </div>
                  )}
                  {aiForSection && (
                    <div className="notion-callout">
                      <Icon name="sparkles" size={14}/>
                      <div>
                        <div className="notion-callout-label">AI suggestion · stub</div>
                        <div>{aiForSection.msg}</div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {InsertPanel}
      </div>
    </>
  );
};

// Auto-growing textarea styled to be invisible on the Notion page —
// looks like body text until the user clicks in.
function NotionTextarea({ value, onChange, placeholder, serif }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current) return;
    ref.current.style.height = 'auto';
    ref.current.style.height = ref.current.scrollHeight + 'px';
  }, [value]);
  return (
    <textarea
      ref={ref}
      className={`notion-text ${serif ? 'serif' : ''}`}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      rows={1}
    />
  );
}

export default DeliverablesView;
