import React, { useState, useEffect, useCallback, useRef } from 'react';
import { X, ChevronRight, ChevronLeft, GraduationCap, Sparkles, Volume2, VolumeX, Loader2 } from 'lucide-react';
import '../styles/Tutorial.css';

const STEPS = [
  {
    id: 'welcome',
    type: 'modal',
    title: 'Welcome to CU Undergraduate Advisor!',
    body: "Let\u2019s take a quick tour of the key features. We\u2019ll start by asking a question, search for courses, and explore the different response modes.",
    buttonText: "Let\u2019s Go!",
  },
  {
    id: 'click-suggestion',
    type: 'highlight',
    target: '.suggestions-grid',
    title: 'Ask a Question',
    body: 'Click any of the Getting Started questions below to send it to your advisors. Watch how the panel responds!',
    position: 'top',
  },
  {
    id: 'course-search',
    type: 'highlight',
    target: '.main-textarea',
    title: 'Search for Courses',
    body: "We\u2019ve pre-filled a course search for you. Edit it if you like, then press Enter or click Send.\n\nThe Course Advisor searches the real CU Boulder catalog \u2014 sections, schedules, and professor ratings.",
    position: 'top',
    extraGap: 60,
    prefill: 'Find CSCI 1300 sections for Spring 2026 with professors rated 4+',
  },
  {
    id: 'panel-toggle',
    type: 'highlight',
    target: '[title="Aggregate synthesized answer"]',
    title: 'Response Mode',
    body: 'Your first question got a Panel response \u2014 each advisor answers separately.\n\nClick "Aggregate" to switch to a single merged answer. Try it now!',
    position: 'top-left',
    extraGap: 60,
  },
  {
    id: 'single-query',
    type: 'highlight',
    target: '.main-textarea',
    title: 'Try Aggregate Mode',
    body: "Here\u2019s another query to try in Aggregate mode. Send it to see how an aggregate synthesized answer looks compared to the panel view.",
    position: 'top',
    prefill: 'What are the best electives for a Computer Science major?',
  },
  {
    id: 'advisor-selection',
    type: 'highlight',
    target: '.advisor-status-dropdown',
    title: 'Choose Your Advisors',
    body: 'Click here to see all available advisors. You can toggle individual advisors on or off \u2014 only active advisors will respond to your questions.',
    position: 'bottom-right',
  },
  {
    id: 'upload-docs',
    type: 'highlight',
    target: '.add-docs-btn',
    title: 'Upload Documents',
    body: 'Upload PDFs, Word docs, or text files. Advisors will reference your actual document content \u2014 perfect for resume reviews, essay feedback, or syllabus analysis.',
    position: 'top',
    extraGap: 60,
  },
  {
    id: 'new-chat',
    type: 'highlight',
    target: '.new-chat-button',
    title: 'Start New Conversations',
    body: 'Click here to start a fresh chat. Each conversation is saved and you can switch between them from the sidebar.',
    position: 'right',
  },
  {
    id: 'theme-toggle',
    type: 'highlight',
    target: '.theme-toggle',
    title: 'Light & Dark Mode',
    body: 'Click to toggle between light and dark themes. Your preference is saved automatically.',
    position: 'bottom-left',
  },
  {
    id: 'canvas-btn',
    type: 'highlight',
    target: '.sidebar-canvas-btn',
    title: 'Advisor Canvas',
    body: 'The Canvas organizes insights from your chats into a structured summary \u2014 action items, academic plans, and more. Click to take a look!',
    position: 'right',
  },
  {
    id: 'user-guide',
    type: 'highlight',
    target: '.user-menu-button',
    title: 'Find the User Guide',
    body: 'Use the back button to get back to the chat window. Then click the three dots near your name to open the Settings menu. Inside you\u2019ll find the User Guide with detailed documentation on every feature.',
    position: 'right',
  },
  {
    id: 'complete',
    type: 'modal',
    title: "You\u2019re All Set!",
    body: "You now know the essentials. Here are some things to try:\n\n\u2022 Search for courses: \u201cMATH 2400 MWF sections\u201d\n\u2022 Ask for advice: \u201cHow do I choose a minor?\u201d\n\u2022 Upload a resume for career feedback\n\u2022 Toggle Aggregate mode for quick answers\n\nThe tutorial is always available from the Settings menu. Enjoy!",
    buttonText: 'Done',
    isFinal: true,
  },
];

/* ── Tooltip positioning ─────────────────────────────────────────── */

function getTooltipStyle(targetRect, position, tooltipEl, extraGap = 0) {
  if (!targetRect) return {};
  const pad = 16;
  const tooltipW = tooltipEl?.offsetWidth || 340;
  const tooltipH = tooltipEl?.offsetHeight || 220;
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  let top, left;

  switch (position) {
    case 'top':
      top = targetRect.top - tooltipH - pad - extraGap;
      left = targetRect.left + targetRect.width / 2 - tooltipW / 2;
      break;
    case 'top-left':
      top = targetRect.top - tooltipH - pad - extraGap;
      left = targetRect.right - tooltipW;
      break;
    case 'bottom':
      top = targetRect.bottom + pad;
      left = targetRect.left + targetRect.width / 2 - tooltipW / 2;
      break;
    case 'bottom-left':
      top = targetRect.bottom + pad;
      left = targetRect.right - tooltipW;
      break;
    case 'bottom-right':
      top = targetRect.bottom + pad;
      left = targetRect.right + pad;
      break;
    case 'left':
      top = targetRect.top + targetRect.height / 2 - tooltipH / 2;
      left = targetRect.left - tooltipW - pad;
      break;
    case 'right':
    default:
      top = targetRect.top + targetRect.height / 2 - tooltipH / 2;
      left = targetRect.right + pad;
      break;
  }

  // Clamp to viewport
  if (left < 8) left = 8;
  if (left + tooltipW > vw - 8) left = vw - tooltipW - 8;
  if (top < 8) top = 8;
  if (top + tooltipH > vh - 8) top = vh - tooltipH - 8;

  // Prevent overlap with target: if tooltip covers the target, push it away
  const tooltipBottom = top + tooltipH;
  const tooltipRight = left + tooltipW;
  const overlapX = tooltipRight > targetRect.left && left < targetRect.right;
  const overlapY = tooltipBottom > targetRect.top && top < targetRect.bottom;
  if (overlapX && overlapY) {
    if (position.startsWith('top')) {
      top = targetRect.top - tooltipH - pad;
    } else if (position.startsWith('bottom')) {
      top = targetRect.bottom + pad;
    } else if (position === 'left') {
      left = targetRect.left - tooltipW - pad;
    } else {
      left = targetRect.right + pad;
    }
  }

  return { top: `${top}px`, left: `${left}px` };
}

/* ── Programmatically set a React-controlled textarea ────────────── */

function fillTextarea(selector, text) {
  const el = document.querySelector(selector);
  if (!el) return;
  const setter = Object.getOwnPropertyDescriptor(
    window.HTMLTextAreaElement.prototype,
    'value',
  ).set;
  setter.call(el, text);
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.focus();
}

/* ── TTS helpers ─────────────────────────────────────────────────── */

function getStepTTSText(stepDef) {
  if (!stepDef) return '';
  let text = stepDef.title + '. ' + (stepDef.body || '');
  return text
    .replace(/\u2022/g, ',')
    .replace(/[\u201c\u201d]/g, '"')
    .replace(/\u2019/g, "'")
    .replace(/\u2014/g, ', ')
    .replace(/\n+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

async function fetchTTSBlob(text, retries = 2) {
  const token = localStorage.getItem('authToken');
  if (!token || !text) return null;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const resp = await fetch(`${process.env.REACT_APP_API_URL}/api/tts`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text }),
      });
      if (resp.ok) return await resp.blob();
      if (attempt < retries) await new Promise(r => setTimeout(r, 3000));
    } catch {
      if (attempt < retries) await new Promise(r => setTimeout(r, 3000));
    }
  }
  return null;
}

/* ══════════════════════════════════════════════════════════════════ */

export default function Tutorial({ active, onClose }) {
  const [step, setStep] = useState(() => {
    const saved = parseInt(localStorage.getItem('tutorialStep'), 10);
    return Number.isFinite(saved) && saved >= 0 && saved < STEPS.length ? saved : 0;
  });
  const [targetRect, setTargetRect] = useState(null);
  const [floatingFlash, setFloatingFlash] = useState(false);

  const tooltipRef = useRef(null);
  const highlightedElRef = useRef(null);
  const prevTargetRectRef = useRef(null);
  const timersRef = useRef([]);

  /* ── TTS state ──────────────────────────────────────────────────── */
  const ttsCacheRef = useRef(new Map());
  const currentAudioRef = useRef(null);
  const mountedRef = useRef(true);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoadingAudio, setIsLoadingAudio] = useState(false);

  const current = STEPS[step];

  /* ── helpers ───────────────────────────────────────────────────── */

  const stopAudio = useCallback(() => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    setIsPlaying(false);
    setIsLoadingAudio(false);
  }, []);

  const clearTimers = useCallback(() => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  }, []);

  const removeHighlight = useCallback(() => {
    if (highlightedElRef.current) {
      highlightedElRef.current.classList.remove('tutorial-spotlight-target');
      highlightedElRef.current = null;
    }
  }, []);

  const doCleanup = useCallback(() => {
    clearTimers();
    removeHighlight();
    stopAudio();
    setTargetRect(null);
  }, [clearTimers, removeHighlight, stopAudio]);

  /* ── TTS playback ───────────────────────────────────────────────── */

  const playStepAudio = useCallback(async (stepIndex) => {
    stopAudio();

    const stepDef = STEPS[stepIndex];
    if (!stepDef) return;

    setIsLoadingAudio(true);

    let blob = ttsCacheRef.current.get(stepIndex);
    if (!blob) {
      blob = await fetchTTSBlob(getStepTTSText(stepDef));
      if (blob && mountedRef.current) {
        ttsCacheRef.current.set(stepIndex, blob);
      }
    }

    if (!blob || !mountedRef.current) {
      setIsLoadingAudio(false);
      return;
    }

    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    currentAudioRef.current = audio;
    setIsLoadingAudio(false);
    setIsPlaying(true);

    audio.onended = () => {
      setIsPlaying(false);
      URL.revokeObjectURL(url);
      currentAudioRef.current = null;
    };
    audio.onerror = () => {
      setIsPlaying(false);
      URL.revokeObjectURL(url);
      currentAudioRef.current = null;
    };
    audio.play().catch(() => {
      setIsPlaying(false);
      URL.revokeObjectURL(url);
      currentAudioRef.current = null;
    });
  }, [stopAudio]);

  const toggleAudio = useCallback(() => {
    if (isLoadingAudio) return;
    if (isPlaying && currentAudioRef.current) {
      currentAudioRef.current.pause();
      setIsPlaying(false);
    } else if (currentAudioRef.current && currentAudioRef.current.paused) {
      currentAudioRef.current.play().catch(() => {});
      setIsPlaying(true);
    } else {
      playStepAudio(step);
    }
  }, [isPlaying, isLoadingAudio, step, playStepAudio]);

  const preloadSteps = useCallback(async (indices) => {
    for (const i of indices) {
      if (!mountedRef.current) break;
      if (ttsCacheRef.current.has(i)) continue;
      const blob = await fetchTTSBlob(getStepTTSText(STEPS[i]), 2);
      if (blob && mountedRef.current) {
        ttsCacheRef.current.set(i, blob);
      }
    }
  }, []);

  /* ── navigation (never used as an effect dependency) ───────────── */

  const advance = useCallback(() => {
    doCleanup();
    if (step >= STEPS.length - 1) {
      setStep(0);
      localStorage.removeItem('tutorialStep');
      onClose();
    } else {
      setStep(s => s + 1);
    }
  }, [step, doCleanup, onClose]);

  const goBack = useCallback(() => {
    doCleanup();
    setStep(s => (s > 0 ? s - 1 : s));
  }, [doCleanup]);

  const handleClose = useCallback(() => {
    doCleanup();
    onClose();
  }, [doCleanup, onClose]);

  const handleFinish = useCallback(() => {
    doCleanup();
    setStep(0);
    localStorage.removeItem('tutorialStep');
    onClose();
  }, [doCleanup, onClose]);

  /* ── Effect: highlight target when step changes ────────────────── */

  const stepRef = useRef(step);
  stepRef.current = step;

  useEffect(() => {
    localStorage.setItem('tutorialStep', String(step));
  }, [step]);

  useEffect(() => {
    if (!active) return;
    const stepDef = STEPS[stepRef.current];
    if (!stepDef || stepDef.type !== 'highlight') return;

    let cancelled = false;

    const findTarget = () => {
      const selectors = stepDef.target.split(',').map(s => s.trim());
      for (const sel of selectors) {
        const el = document.querySelector(sel);
        if (el) return el;
      }
      return null;
    };

    const tryFind = () => {
      if (cancelled) return;
      const el = findTarget();
      if (!el) {
        const t = setTimeout(tryFind, 500);
        timersRef.current.push(t);
        return;
      }

      const rect = el.getBoundingClientRect();
      const inView =
        rect.top >= 0 &&
        rect.bottom <= window.innerHeight &&
        rect.left >= 0 &&
        rect.right <= window.innerWidth;
      if (!inView) {
        el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }

      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          if (cancelled) return;
          setTargetRect(el.getBoundingClientRect());
          el.classList.add('tutorial-spotlight-target');
          highlightedElRef.current = el;

          if (stepDef.prefill) {
            fillTextarea('.main-textarea', stepDef.prefill);
          }
        });
      });
    };

    tryFind();

    const updateRect = () => {
      const el = findTarget();
      if (el) {
        setTargetRect(el.getBoundingClientRect());
      } else if (highlightedElRef.current) {
        highlightedElRef.current.classList.remove('tutorial-spotlight-target');
        highlightedElRef.current = null;
        setTargetRect(null);
      }
    };
    window.addEventListener('scroll', updateRect, true);
    window.addEventListener('resize', updateRect);

    const poll = setInterval(() => {
      if (cancelled) return;
      if (highlightedElRef.current && !document.contains(highlightedElRef.current)) {
        highlightedElRef.current = null;
        setTargetRect(null);
      }
    }, 500);

    return () => {
      cancelled = true;
      clearTimers();
      clearInterval(poll);
      removeHighlight();
      window.removeEventListener('scroll', updateRect, true);
      window.removeEventListener('resize', updateRect);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, step]);

  // Detect transition to floating mode and trigger flash
  useEffect(() => {
    if (prevTargetRectRef.current && !targetRect && active) {
      setFloatingFlash(true);
      const t = setTimeout(() => setFloatingFlash(false), 2800);
      return () => clearTimeout(t);
    }
    prevTargetRectRef.current = targetRect;
  }, [targetRect, active]);

  // Clean up when deactivated
  useEffect(() => {
    if (!active) doCleanup();
  }, [active, doCleanup]);

  /* ── TTS effects ────────────────────────────────────────────────── */

  // Track mount/unmount for async safety
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      stopAudio();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Preload first 2 steps on mount if tutorial not yet completed
  useEffect(() => {
    const dismissed = localStorage.getItem('tutorialDismissed') === 'true';
    if (!dismissed) {
      preloadSteps([0, 1]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // When tutorial becomes active, preload remaining steps (2+)
  useEffect(() => {
    if (active) {
      const remaining = Array.from({ length: STEPS.length }, (_, i) => i).filter(i => i >= 2);
      preloadSteps(remaining);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  // Auto-play audio when step changes and tutorial is active
  useEffect(() => {
    if (!active) return;
    playStepAudio(step);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, step]);

  /* ── Render ─────────────────────────────────────────────────────── */

  if (!active) return null;

  const progress = ((step + 1) / STEPS.length) * 100;

  const audioButton = (size = 14) => (
    <button
      className={`tutorial-audio-btn ${isPlaying ? 'playing' : ''}`}
      onClick={toggleAudio}
      title={isLoadingAudio ? 'Loading audio...' : isPlaying ? 'Pause narration' : 'Play narration'}
    >
      {isLoadingAudio
        ? <Loader2 size={size} className="spinning" />
        : isPlaying
          ? <Volume2 size={size} />
          : <VolumeX size={size} />
      }
    </button>
  );

  /* ── Modal step ────────────────────────────────────────────────── */
  if (current.type === 'modal') {
    return (
      <div className="tutorial-overlay">
        <div className={`tutorial-modal ${current.isFinal ? 'final' : ''}`}>
          <div className="tutorial-modal-top-actions">
            {audioButton(16)}
            <button className="tutorial-close" onClick={handleClose} title="Exit tutorial">
              <X size={18} />
            </button>
          </div>
          <div className="tutorial-modal-icon">
            {current.isFinal ? <Sparkles size={32} /> : <GraduationCap size={32} />}
          </div>
          <h2 className="tutorial-modal-title">{current.title}</h2>
          <p className="tutorial-modal-body">{current.body}</p>
          <div className="tutorial-modal-footer">
            {step > 0 && !current.isFinal && (
              <button className="tutorial-back-btn" onClick={goBack}>
                <ChevronLeft size={16} /> Back
              </button>
            )}
            <button
              className="tutorial-primary-btn"
              onClick={current.isFinal ? handleFinish : advance}
            >
              {current.buttonText || 'Next'}
              {!current.isFinal && <ChevronRight size={16} />}
            </button>
          </div>
          <div className="tutorial-progress">
            <div className="tutorial-progress-bar" style={{ width: `${progress}%` }} />
          </div>
          <span className="tutorial-step-counter">{step + 1} / {STEPS.length}</span>
        </div>
      </div>
    );
  }

  /* ── Highlight step ────────────────────────────────────────────── */
  const cutout = targetRect
    ? {
        top: targetRect.top - 6,
        left: targetRect.left - 6,
        width: targetRect.width + 12,
        height: targetRect.height + 12,
        rx: 8,
      }
    : null;

  if (!targetRect) {
    return (
      <div className={`tutorial-tooltip tutorial-tooltip-floating${floatingFlash ? ' tutorial-flash' : ''}`}>
        <div className="tutorial-tooltip-actions">
          {audioButton()}
          <button className="tutorial-close" onClick={handleClose} title="Exit tutorial">
            <X size={16} />
          </button>
        </div>
        <h3 className="tutorial-tooltip-title">{current.title}</h3>
        <p className="tutorial-tooltip-body">{current.body}</p>
        <div className="tutorial-tooltip-footer">
          <div className="tutorial-tooltip-nav">
            {step > 0 && (
              <button className="tutorial-back-btn" onClick={goBack}>
                <ChevronLeft size={14} /> Back
              </button>
            )}
            <button className="tutorial-next-btn" onClick={advance}>
              Next <ChevronRight size={14} />
            </button>
          </div>
          <span className="tutorial-step-counter">{step + 1} / {STEPS.length}</span>
        </div>
        <div className="tutorial-progress">
          <div className="tutorial-progress-bar" style={{ width: `${progress}%` }} />
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Dark overlay with spotlight cutout */}
      <svg className="tutorial-svg-overlay">
        <defs>
          <mask id="tutorial-mask">
            <rect x="0" y="0" width="100%" height="100%" fill="white" />
            {cutout && (
              <rect
                x={cutout.left} y={cutout.top}
                width={cutout.width} height={cutout.height}
                rx={cutout.rx} fill="black"
              />
            )}
          </mask>
        </defs>
        <rect
          x="0" y="0" width="100%" height="100%"
          fill="rgba(0,0,0,0.55)"
          mask="url(#tutorial-mask)"
        />
      </svg>

      {/* Pulse ring around the target */}
      {cutout && (
        <div
          className="tutorial-pulse-ring"
          style={{
            top: cutout.top, left: cutout.left,
            width: cutout.width, height: cutout.height,
            borderRadius: `${cutout.rx}px`,
          }}
        />
      )}

      {/* Tooltip */}
      <div
        className="tutorial-tooltip"
        ref={tooltipRef}
        style={getTooltipStyle(targetRect, current.position, tooltipRef.current, current.extraGap)}
      >
        <div className="tutorial-tooltip-actions">
          {audioButton()}
          <button className="tutorial-close" onClick={handleClose} title="Exit tutorial">
            <X size={16} />
          </button>
        </div>

        <h3 className="tutorial-tooltip-title">{current.title}</h3>
        <p className="tutorial-tooltip-body">{current.body}</p>

        <div className="tutorial-tooltip-footer">
          <div className="tutorial-tooltip-nav">
            {step > 0 && (
              <button className="tutorial-back-btn" onClick={goBack}>
                <ChevronLeft size={14} /> Back
              </button>
            )}
            <button className="tutorial-next-btn" onClick={advance}>
              Next <ChevronRight size={14} />
            </button>
          </div>
          <span className="tutorial-step-counter">{step + 1} / {STEPS.length}</span>
        </div>
        <div className="tutorial-progress">
          <div className="tutorial-progress-bar" style={{ width: `${progress}%` }} />
        </div>
      </div>
    </>
  );
}

/* ── Floating "Start Tutorial" button ────────────────────────────── */

export function TutorialButton({ onClick }) {
  return (
    <button className="tutorial-fab" onClick={onClick} title="Start Tutorial">
      <GraduationCap size={20} />
      <span>Start Tutorial</span>
    </button>
  );
}
