import React, { useState, useEffect } from 'react';
import { Columns3, FileOutput, User, ChevronDown, ChevronRight } from 'lucide-react';
import './ResponseModeDropdown.css';

/**
 * Response mode: panel (multi-advisor), aggregate (synthesized), or single (one chosen advisor).
 * Renders to the right of the advisor selector in the chat header.
 */
const ResponseModeDropdown = ({
  advisors,
  activeAdvisors,
  responseMode,
  onResponseModeChange,
  singleAdvisorId,
  onSingleAdvisorChange,
  getAdvisorColors,
  isDark = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [singleSubOpen, setSingleSubOpen] = useState(true);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (isOpen && !event.target.closest('.response-mode-dropdown')) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  if (!advisors || typeof advisors !== 'object') {
    return null;
  }

  const entries = Object.entries(advisors);
  const allowedIds = activeAdvisors && activeAdvisors.length > 0
    ? entries.filter(([id]) => activeAdvisors.includes(id))
    : entries;

  const triggerLabel =
    responseMode === 'panel'
      ? 'Panel'
      : responseMode === 'aggregate'
        ? 'Aggregate'
        : `Single — ${advisors[singleAdvisorId]?.name || 'Advisor'}`;

  const selectMode = (mode) => {
    onResponseModeChange(mode);
    if (mode !== 'single') {
      setIsOpen(false);
    }
  };

  const selectSingleAdvisor = (id) => {
    onResponseModeChange('single');
    onSingleAdvisorChange(id);
    setIsOpen(false);
  };

  return (
    <div className="response-mode-dropdown">
      <button
        type="button"
        className={`response-mode-dropdown-trigger ${isOpen ? 'open' : ''}`}
        onClick={() => setIsOpen((o) => !o)}
        title="Response mode: panel, aggregate, or single advisor"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-label={`Response mode: ${triggerLabel}`}
      >
        <span className="response-mode-trigger-label">{triggerLabel}</span>
        <ChevronDown size={14} className={`response-mode-arrow ${isOpen ? 'rotated' : ''}`} />
      </button>

      {isOpen && (
        <div className="response-mode-dropdown-panel" role="listbox">
          <button
            type="button"
            role="option"
            aria-selected={responseMode === 'panel'}
            className={`response-mode-option ${responseMode === 'panel' ? 'selected' : ''}`}
            onClick={() => selectMode('panel')}
          >
            <Columns3 size={16} />
            <span>
              <span className="response-mode-option-title">Panel</span>
              <span className="response-mode-option-desc">Up to three advisors answer separately</span>
            </span>
          </button>
          <button
            type="button"
            role="option"
            aria-selected={responseMode === 'aggregate'}
            className={`response-mode-option ${responseMode === 'aggregate' ? 'selected' : ''}`}
            onClick={() => selectMode('aggregate')}
          >
            <FileOutput size={16} />
            <span>
              <span className="response-mode-option-title">Aggregate</span>
              <span className="response-mode-option-desc">One synthesized answer from multiple advisors</span>
            </span>
          </button>

          <div className="response-mode-single-block">
            <button
              type="button"
              className={`response-mode-single-header ${responseMode === 'single' ? 'selected' : ''}`}
              onClick={() => setSingleSubOpen((s) => !s)}
            >
              <User size={16} />
              <span className="response-mode-option-title">Single advisor</span>
              <ChevronRight
                size={14}
                className={`response-mode-sub-chevron ${singleSubOpen ? 'open' : ''}`}
              />
            </button>

            {singleSubOpen && (
              <div className="response-mode-single-submenu" role="group" aria-label="Choose advisor">
                {allowedIds.map(([id, advisor]) => {
                  const IconComponent = advisor.icon;
                  const colors = getAdvisorColors(id, isDark);
                  const selected = responseMode === 'single' && singleAdvisorId === id;
                  return (
                    <button
                      key={id}
                      type="button"
                      role="option"
                      aria-selected={selected}
                      className={`response-mode-advisor-pick ${selected ? 'selected' : ''}`}
                      style={{
                        '--rm-color': colors.color,
                        '--rm-bg': colors.bgColor,
                      }}
                      onClick={() => selectSingleAdvisor(id)}
                    >
                      <span className="response-mode-advisor-icon">
                        {advisor.avatar ? (
                          <img src={advisor.avatar} alt="" />
                        ) : (
                          <IconComponent size={14} />
                        )}
                      </span>
                      <span className="response-mode-advisor-name">{advisor.name}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ResponseModeDropdown;
