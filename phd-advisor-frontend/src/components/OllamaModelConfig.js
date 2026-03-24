import React, { useState, useEffect, useCallback } from 'react';
import { X, RefreshCw, Cpu, ChevronDown, Check, AlertCircle, Loader2, Settings2, Users } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

const OllamaModelConfig = ({ isOpen, onClose, advisors, currentAssignments, onSaveAssignments, currentProvider }) => {
  const { isDark } = useTheme();
  const [models, setModels] = useState([]);
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [error, setError] = useState(null);
  const [orchestratorModel, setOrchestratorModel] = useState(null);
  const [defaultModel, setDefaultModel] = useState(null);
  const [perPersona, setPerPersona] = useState(false);
  const [personaModels, setPersonaModels] = useState({});
  const [isSaving, setIsSaving] = useState(false);

  const loadModels = useCallback(async () => {
    setIsLoadingModels(true);
    setError(null);
    try {
      const resp = await fetch(`${process.env.REACT_APP_API_URL}/ollama/models`);
      if (!resp.ok) throw new Error('Failed to fetch models');
      const data = await resp.json();
      setModels(data.models || []);
      if (data.models?.length === 0) {
        setError('No models found on any vLLM server. Check that your inference servers are running.');
      }
    } catch (err) {
      setError('Could not reach the model discovery endpoint. Please check that the backend is running.');
      console.error('Model discovery error:', err);
    } finally {
      setIsLoadingModels(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      loadModels();
    }
  }, [isOpen, loadModels]);

  useEffect(() => {
    if (!currentAssignments) return;
    if (currentAssignments.orchestrator) {
      setOrchestratorModel(currentAssignments.orchestrator);
    }
    if (currentAssignments.default) {
      setDefaultModel(currentAssignments.default);
    }
    if (currentAssignments.personas && Object.keys(currentAssignments.personas).length > 0) {
      setPerPersona(true);
      setPersonaModels(currentAssignments.personas);
    }
  }, [currentAssignments]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const body = {
        orchestrator: orchestratorModel || defaultModel || null,
        default: defaultModel || null,
        personas: perPersona ? personaModels : null,
      };
      await onSaveAssignments(body);
      onClose();
    } catch (err) {
      setError('Failed to save assignments: ' + err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const modelKey = (m) => `${m.client_id}::${m.model_id}`;

  const modelDisplayName = (m) => {
    if (!m) return 'Not selected';
    if (m.client_id === 'gemini') return `Gemini — ${m.model_id}`;
    const shortModel = m.model_id.split('/').pop();
    return `${shortModel} (${m.client_name || m.client_id})`;
  };

  if (!isOpen) return null;

  const advisorEntries = advisors ? Object.entries(advisors) : [];

  return (
    <div className="ollama-config-overlay" onClick={onClose}>
      <div className="ollama-config-modal" onClick={e => e.stopPropagation()}>
        <div className="ollama-config-header">
          <div className="ollama-config-title">
            <Settings2 size={20} />
            <h2>{currentProvider === 'hybrid' ? 'Configure Hybrid Models' : 'Configure LLM Models'}</h2>
          </div>
          <button className="ollama-config-close" onClick={onClose}><X size={18} /></button>
        </div>

        <div className="ollama-config-body">
          {error && (
            <div className="ollama-config-error">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <div className="ollama-config-refresh-row">
            <span className="ollama-config-model-count">
              {isLoadingModels ? 'Scanning servers...' : `${models.length} model${models.length !== 1 ? 's' : ''} available`}
            </span>
            <button
              className="ollama-config-refresh-btn"
              onClick={loadModels}
              disabled={isLoadingModels}
            >
              {isLoadingModels ? <Loader2 size={14} className="spinning" /> : <RefreshCw size={14} />}
              Refresh
            </button>
          </div>

          {/* Orchestrator LLM */}
          <div className="ollama-config-section">
            <label className="ollama-config-label">
              <Cpu size={15} />
              Orchestrator LLM
            </label>
            <p className="ollama-config-hint">Handles clarification questions and routing logic</p>
            <ModelSelect
              models={models}
              value={orchestratorModel}
              onChange={setOrchestratorModel}
              placeholder="Select orchestrator model..."
              modelKey={modelKey}
              modelDisplayName={modelDisplayName}
              isDark={isDark}
            />
          </div>

          {/* Default Persona LLM */}
          <div className="ollama-config-section">
            <label className="ollama-config-label">
              <Users size={15} />
              Default Advisor LLM
            </label>
            <p className="ollama-config-hint">Used for all advisors unless overridden below</p>
            <ModelSelect
              models={models}
              value={defaultModel}
              onChange={setDefaultModel}
              placeholder="Select default advisor model..."
              modelKey={modelKey}
              modelDisplayName={modelDisplayName}
              isDark={isDark}
            />
          </div>

          {/* Per-persona toggle */}
          <div className="ollama-config-toggle-row">
            <label className="ollama-config-toggle-label" htmlFor="per-persona-toggle">
              Customize LLM per advisor
            </label>
            <label className="ollama-toggle-switch">
              <input
                id="per-persona-toggle"
                type="checkbox"
                checked={perPersona}
                onChange={e => setPerPersona(e.target.checked)}
              />
              <span className="ollama-toggle-slider" />
            </label>
          </div>

          {/* Per-persona selectors */}
          {perPersona && (
            <div className="ollama-config-persona-list">
              {advisorEntries.map(([id, advisor]) => (
                <div key={id} className="ollama-config-persona-row">
                  <div className="ollama-persona-info">
                    {advisor.avatar ? (
                      <img src={advisor.avatar} alt="" className="ollama-persona-avatar" />
                    ) : (
                      <div className="ollama-persona-icon-placeholder" />
                    )}
                    <span className="ollama-persona-name">{advisor.name}</span>
                  </div>
                  <ModelSelect
                    models={models}
                    value={personaModels[id] || null}
                    onChange={(val) => setPersonaModels(prev => ({ ...prev, [id]: val }))}
                    placeholder="Use default"
                    modelKey={modelKey}
                    modelDisplayName={modelDisplayName}
                    isDark={isDark}
                    compact
                  />
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="ollama-config-footer">
          <button className="ollama-config-cancel-btn" onClick={onClose}>Cancel</button>
          <button
            className="ollama-config-save-btn"
            onClick={handleSave}
            disabled={isSaving || (!defaultModel && !orchestratorModel)}
          >
            {isSaving ? <Loader2 size={14} className="spinning" /> : <Check size={14} />}
            Apply &amp; Save
          </button>
        </div>
      </div>

      <style>{`
        .ollama-config-overlay {
          position: fixed;
          inset: 0;
          z-index: 9999;
          display: flex;
          align-items: center;
          justify-content: center;
          background: rgba(0,0,0,0.5);
          backdrop-filter: blur(4px);
        }
        .ollama-config-modal {
          background: ${isDark ? '#1e1e2e' : '#fff'};
          border-radius: 16px;
          width: 520px;
          max-width: 95vw;
          max-height: 85vh;
          display: flex;
          flex-direction: column;
          box-shadow: 0 20px 60px rgba(0,0,0,0.3);
          border: 1px solid ${isDark ? '#333' : '#e5e7eb'};
        }
        .ollama-config-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 20px 24px 16px;
          border-bottom: 1px solid ${isDark ? '#333' : '#e5e7eb'};
        }
        .ollama-config-title {
          display: flex;
          align-items: center;
          gap: 10px;
          color: ${isDark ? '#e0e0e0' : '#111'};
        }
        .ollama-config-title h2 {
          margin: 0;
          font-size: 18px;
          font-weight: 600;
        }
        .ollama-config-close {
          background: none;
          border: none;
          cursor: pointer;
          color: ${isDark ? '#888' : '#666'};
          padding: 4px;
          border-radius: 6px;
        }
        .ollama-config-close:hover {
          background: ${isDark ? '#333' : '#f3f4f6'};
        }
        .ollama-config-body {
          padding: 20px 24px;
          overflow-y: auto;
          flex: 1;
        }
        .ollama-config-error {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          padding: 12px;
          border-radius: 8px;
          margin-bottom: 16px;
          background: ${isDark ? '#3b1c1c' : '#fef2f2'};
          color: ${isDark ? '#fca5a5' : '#dc2626'};
          font-size: 13px;
          line-height: 1.4;
        }
        .ollama-config-refresh-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 20px;
        }
        .ollama-config-model-count {
          font-size: 13px;
          color: ${isDark ? '#888' : '#666'};
        }
        .ollama-config-refresh-btn {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          border-radius: 8px;
          border: 1px solid ${isDark ? '#444' : '#d1d5db'};
          background: ${isDark ? '#2a2a3a' : '#f9fafb'};
          color: ${isDark ? '#ccc' : '#374151'};
          font-size: 13px;
          cursor: pointer;
          transition: all 0.15s;
        }
        .ollama-config-refresh-btn:hover:not(:disabled) {
          background: ${isDark ? '#333' : '#f3f4f6'};
        }
        .ollama-config-refresh-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        .ollama-config-section {
          margin-bottom: 20px;
        }
        .ollama-config-label {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 14px;
          font-weight: 600;
          color: ${isDark ? '#e0e0e0' : '#111'};
          margin-bottom: 4px;
        }
        .ollama-config-hint {
          font-size: 12px;
          color: ${isDark ? '#777' : '#6b7280'};
          margin: 0 0 8px;
        }
        .ollama-config-toggle-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 12px 0;
          border-top: 1px solid ${isDark ? '#333' : '#e5e7eb'};
          margin-bottom: 12px;
        }
        .ollama-config-toggle-label {
          font-size: 14px;
          font-weight: 500;
          color: ${isDark ? '#ccc' : '#374151'};
        }
        .ollama-toggle-switch {
          position: relative;
          width: 40px;
          height: 22px;
          display: inline-block;
        }
        .ollama-toggle-switch input {
          opacity: 0;
          width: 0;
          height: 0;
        }
        .ollama-toggle-slider {
          position: absolute;
          inset: 0;
          border-radius: 22px;
          background: ${isDark ? '#444' : '#d1d5db'};
          cursor: pointer;
          transition: 0.2s;
        }
        .ollama-toggle-slider::before {
          content: '';
          position: absolute;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: #fff;
          left: 3px;
          top: 3px;
          transition: 0.2s;
        }
        .ollama-toggle-switch input:checked + .ollama-toggle-slider {
          background: #7c3aed;
        }
        .ollama-toggle-switch input:checked + .ollama-toggle-slider::before {
          transform: translateX(18px);
        }
        .ollama-config-persona-list {
          display: flex;
          flex-direction: column;
          gap: 10px;
          padding-bottom: 4px;
        }
        .ollama-config-persona-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          padding: 8px 12px;
          border-radius: 10px;
          background: ${isDark ? '#262636' : '#f9fafb'};
        }
        .ollama-persona-info {
          display: flex;
          align-items: center;
          gap: 8px;
          min-width: 0;
          flex-shrink: 0;
        }
        .ollama-persona-avatar {
          width: 28px;
          height: 28px;
          border-radius: 50%;
          object-fit: cover;
        }
        .ollama-persona-icon-placeholder {
          width: 28px;
          height: 28px;
          border-radius: 50%;
          background: ${isDark ? '#444' : '#e5e7eb'};
        }
        .ollama-persona-name {
          font-size: 13px;
          font-weight: 500;
          color: ${isDark ? '#ccc' : '#374151'};
          white-space: nowrap;
        }
        .ollama-config-footer {
          display: flex;
          justify-content: flex-end;
          gap: 10px;
          padding: 16px 24px;
          border-top: 1px solid ${isDark ? '#333' : '#e5e7eb'};
        }
        .ollama-config-cancel-btn {
          padding: 8px 16px;
          border-radius: 8px;
          border: 1px solid ${isDark ? '#444' : '#d1d5db'};
          background: transparent;
          color: ${isDark ? '#ccc' : '#374151'};
          font-size: 14px;
          cursor: pointer;
        }
        .ollama-config-cancel-btn:hover {
          background: ${isDark ? '#333' : '#f3f4f6'};
        }
        .ollama-config-save-btn {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 8px 20px;
          border-radius: 8px;
          border: none;
          background: #7c3aed;
          color: #fff;
          font-size: 14px;
          font-weight: 500;
          cursor: pointer;
          transition: 0.15s;
        }
        .ollama-config-save-btn:hover:not(:disabled) {
          background: #6d28d9;
        }
        .ollama-config-save-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .spinning {
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};


const ModelSelect = ({ models, value, onChange, placeholder, modelKey, modelDisplayName, isDark, compact }) => {
  const [isOpen, setIsOpen] = useState(false);

  const handleSelect = (model) => {
    onChange({
      model_id: model.model_id,
      client_id: model.client_id,
      client_name: model.client_name,
      api_url: model.api_url,
    });
    setIsOpen(false);
  };

  const handleClear = (e) => {
    e.stopPropagation();
    onChange(null);
  };

  return (
    <div className={`model-select ${compact ? 'compact' : ''}`} style={{ position: 'relative' }}>
      <button
        className="model-select-trigger"
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          width: compact ? '200px' : '100%',
          padding: compact ? '6px 10px' : '10px 14px',
          borderRadius: '10px',
          border: `1px solid ${isDark ? '#444' : '#d1d5db'}`,
          background: isDark ? '#2a2a3a' : '#fff',
          color: value ? (isDark ? '#e0e0e0' : '#111') : (isDark ? '#666' : '#9ca3af'),
          fontSize: compact ? '12px' : '14px',
          cursor: 'pointer',
          textAlign: 'left',
          gap: '8px',
        }}
      >
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
          {value ? modelDisplayName(value) : placeholder}
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0 }}>
          {value && (
            <span
              onClick={handleClear}
              style={{ cursor: 'pointer', opacity: 0.5, fontSize: '12px', lineHeight: 1 }}
              title="Clear selection"
            >✕</span>
          )}
          <ChevronDown size={compact ? 12 : 14} style={{ opacity: 0.5, transform: isOpen ? 'rotate(180deg)' : 'none', transition: '0.15s' }} />
        </div>
      </button>

      {isOpen && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: compact ? 'auto' : 0,
            width: compact ? '280px' : undefined,
            marginTop: '4px',
            borderRadius: '10px',
            border: `1px solid ${isDark ? '#444' : '#d1d5db'}`,
            background: isDark ? '#1e1e2e' : '#fff',
            boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
            zIndex: 50,
            maxHeight: '200px',
            overflowY: 'auto',
          }}
        >
          {models.length === 0 ? (
            <div style={{ padding: '16px', textAlign: 'center', color: isDark ? '#666' : '#9ca3af', fontSize: '13px' }}>
              No models available
            </div>
          ) : (
            models.map(m => {
              const isSelected = value && modelKey(value) === modelKey(m);
              return (
                <button
                  key={modelKey(m)}
                  onClick={() => handleSelect(m)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    width: '100%',
                    padding: '10px 14px',
                    border: 'none',
                    background: isSelected ? (isDark ? '#333' : '#f3f4f6') : 'transparent',
                    color: isDark ? '#e0e0e0' : '#111',
                    fontSize: '13px',
                    cursor: 'pointer',
                    textAlign: 'left',
                    borderBottom: `1px solid ${isDark ? '#2a2a3a' : '#f3f4f6'}`,
                  }}
                  onMouseOver={e => { if (!isSelected) e.currentTarget.style.background = isDark ? '#2a2a3a' : '#f9fafb'; }}
                  onMouseOut={e => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', minWidth: 0, flex: 1 }}>
                    <span style={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {m.model_id.split('/').pop()}
                    </span>
                    <span style={{ fontSize: '11px', color: isDark ? '#666' : '#9ca3af' }}>
                      {m.client_name} &middot; {m.client_id}
                    </span>
                  </div>
                  {isSelected && <Check size={14} style={{ color: '#7c3aed', flexShrink: 0 }} />}
                </button>
              );
            })
          )}
        </div>
      )}
    </div>
  );
};

export default OllamaModelConfig;
