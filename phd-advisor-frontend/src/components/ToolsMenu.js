import React, { useState, useRef, useEffect } from 'react';
import { Wrench, ChevronDown } from 'lucide-react';
import { useAppConfig } from '../contexts/AppConfigContext';

const ToolsMenu = ({ onToolSelect }) => {
  const { tools } = useAppConfig();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const handleClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    if (open) document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  if (!tools || tools.length === 0) return null;

  return (
    <div className="tools-menu-wrapper" ref={ref} style={{ position: 'relative' }}>
      <button
        className="tools-menu-trigger"
        onClick={() => setOpen(p => !p)}
        title="Tools"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          padding: '6px 10px',
          borderRadius: 8,
          border: '1px solid var(--border-primary, #e5e7eb)',
          background: 'var(--bg-secondary, #f9fafb)',
          color: 'var(--text-primary, #374151)',
          cursor: 'pointer',
          fontSize: 13,
          fontWeight: 500,
          transition: 'all 0.15s ease',
        }}
      >
        <Wrench size={15} />
        <span>Tools</span>
        <ChevronDown size={14} style={{
          transform: open ? 'rotate(180deg)' : 'rotate(0)',
          transition: 'transform 0.15s ease',
        }} />
      </button>

      {open && (
        <div
          className="tools-menu-dropdown"
          style={{
            position: 'absolute',
            top: 'calc(100% + 6px)',
            right: 0,
            minWidth: 260,
            background: 'var(--bg-primary, #fff)',
            border: '1px solid var(--border-primary, #e5e7eb)',
            borderRadius: 12,
            boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
            zIndex: 200,
            padding: 6,
          }}
        >
          <div style={{
            padding: '6px 10px 8px',
            fontSize: 11,
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--text-tertiary, #9ca3af)',
          }}>
            Available Tools
          </div>
          {tools.map(tool => {
            const Icon = tool.icon || Wrench;
            return (
              <button
                key={tool.id}
                onClick={() => { setOpen(false); if (onToolSelect) onToolSelect(tool); }}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 10,
                  width: '100%',
                  padding: '8px 10px',
                  border: 'none',
                  background: 'none',
                  borderRadius: 8,
                  cursor: 'pointer',
                  textAlign: 'left',
                  color: 'var(--text-primary, #374151)',
                  transition: 'background 0.1s',
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-secondary, #f3f4f6)'}
                onMouseLeave={e => e.currentTarget.style.background = 'none'}
              >
                <div style={{
                  width: 32, height: 32,
                  borderRadius: 8,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: 'var(--bg-tertiary, #e5e7eb)',
                  flexShrink: 0,
                }}>
                  <Icon size={16} />
                </div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13, lineHeight: 1.3 }}>{tool.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary, #6b7280)', lineHeight: 1.3, marginTop: 2 }}>
                    {tool.description}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ToolsMenu;
