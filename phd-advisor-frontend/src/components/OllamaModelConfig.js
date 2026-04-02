import React, { useState, useEffect, useCallback } from 'react';
import { X, RefreshCw, Cpu, Cloud, ChevronDown, Check, AlertCircle, Loader2, Settings2, Users, User2 } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

const OllamaModelConfig = ({ isOpen, onClose, advisors, currentAssignments, onSaveAssignments, currentProvider }) => {
  const { isDark } = useTheme();
  const [neonModels, setNeonModels] = useState([]);
  const [vllmModels, setVllmModels] = useState([]);
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
      const resp = await fetch(`${process.env.REACT_APP_API_URL}/neon/models`);
      if (!resp.ok) throw new Error('Failed to fetch models');
      const data = await resp.json();
      setNeonModels(data.neon_models || []);
      setVllmModels(data.vllm_models || []);
      if ((data.neon_models || []).length === 0 && (data.vllm_models || []).length === 0) {
        setError('No models found. Check that HANA BrainForge credentials or vLLM servers are configured.');
      }
    } catch (err) {
      setError('Could not reach the model discovery endpoint. Please check that the backend is running.');
      console.error('Model discovery error:', err);
    } finally {
      setIsLoadingModels(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) loadModels();
  }, [isOpen, loadModels]);

  useEffect(() => {
    if (!currentAssignments) return;
    if (currentAssignments.orchestrator) setOrchestratorModel(currentAssignments.orchestrator);
    if (currentAssignments.default) setDefaultModel(currentAssignments.default);
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

  if (!isOpen) return null;

  const advisorEntries = advisors ? Object.entries(advisors) : [];
  const totalModels = neonModels.length + 1;

  return (
    <div className="ollama-config-overlay" onClick={onClose}>
      <div className="ollama-config-modal" onClick={e => e.stopPropagation()}>
        <div className="ollama-config-header">
          <div className="ollama-config-title">
            <Settings2 size={20} />
            <h2>{currentProvider === 'hybrid' ? 'Configure Hybrid Models' : 'Configure Neon.ai Models'}</h2>
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
              {isLoadingModels ? 'Discovering models & personas...' : `${totalModels} model${totalModels !== 1 ? 's' : ''} available`}
            </span>
            <button className="ollama-config-refresh-btn" onClick={loadModels} disabled={isLoadingModels}>
              {isLoadingModels ? <Loader2 size={14} className="spinning" /> : <RefreshCw size={14} />}
              Refresh
            </button>
          </div>

          {/* Orchestrator LLM */}
          <div className="ollama-config-section">
            <label className="ollama-config-label"><Cpu size={15} /> Orchestrator LLM</label>
            <p className="ollama-config-hint">Handles clarification questions and routing logic</p>
            <NeonModelSelect
              neonModels={neonModels}
              vllmModels={vllmModels}
              value={orchestratorModel}
              onChange={setOrchestratorModel}
              placeholder="Select orchestrator model..."
              isDark={isDark}
            />
          </div>

          {/* Default Advisor LLM */}
          <div className="ollama-config-section">
            <label className="ollama-config-label"><Users size={15} /> Default Advisor LLM</label>
            <p className="ollama-config-hint">Used for all advisors unless overridden below</p>
            <NeonModelSelect
              neonModels={neonModels}
              vllmModels={vllmModels}
              value={defaultModel}
              onChange={setDefaultModel}
              placeholder="Select default advisor model..."
              isDark={isDark}
            />
          </div>

          {/* Per-persona toggle */}
          <div className="ollama-config-toggle-row">
            <label className="ollama-config-toggle-label" htmlFor="per-persona-toggle">
              Customize LLM per advisor
            </label>
            <label className="ollama-toggle-switch">
              <input id="per-persona-toggle" type="checkbox" checked={perPersona} onChange={e => setPerPersona(e.target.checked)} />
              <span className="ollama-toggle-slider" />
            </label>
          </div>

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
                  <NeonModelSelect
                    neonModels={neonModels}
                    vllmModels={vllmModels}
                    value={personaModels[id] || null}
                    onChange={(val) => setPersonaModels(prev => ({ ...prev, [id]: val }))}
                    placeholder="Use default"
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
        .ollama-config-overlay { position: fixed; inset: 0; z-index: 9999; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.5); backdrop-filter: blur(4px); }
        .ollama-config-modal { background: ${isDark ? '#1e1e2e' : '#fff'}; border-radius: 16px; width: 560px; max-width: 95vw; max-height: 85vh; display: flex; flex-direction: column; box-shadow: 0 20px 60px rgba(0,0,0,0.3); border: 1px solid ${isDark ? '#333' : '#e5e7eb'}; }
        .ollama-config-header { display: flex; align-items: center; justify-content: space-between; padding: 20px 24px 16px; border-bottom: 1px solid ${isDark ? '#333' : '#e5e7eb'}; }
        .ollama-config-title { display: flex; align-items: center; gap: 10px; color: ${isDark ? '#e0e0e0' : '#111'}; }
        .ollama-config-title h2 { margin: 0; font-size: 18px; font-weight: 600; }
        .ollama-config-close { background: none; border: none; cursor: pointer; color: ${isDark ? '#888' : '#666'}; padding: 4px; border-radius: 6px; }
        .ollama-config-close:hover { background: ${isDark ? '#333' : '#f3f4f6'}; }
        .ollama-config-body { padding: 20px 24px; overflow-y: auto; flex: 1; }
        .ollama-config-error { display: flex; align-items: flex-start; gap: 8px; padding: 12px; border-radius: 8px; margin-bottom: 16px; background: ${isDark ? '#3b1c1c' : '#fef2f2'}; color: ${isDark ? '#fca5a5' : '#dc2626'}; font-size: 13px; line-height: 1.4; }
        .ollama-config-refresh-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
        .ollama-config-model-count { font-size: 13px; color: ${isDark ? '#888' : '#666'}; }
        .ollama-config-refresh-btn { display: flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 8px; border: 1px solid ${isDark ? '#444' : '#d1d5db'}; background: ${isDark ? '#2a2a3a' : '#f9fafb'}; color: ${isDark ? '#ccc' : '#374151'}; font-size: 13px; cursor: pointer; transition: all 0.15s; }
        .ollama-config-refresh-btn:hover:not(:disabled) { background: ${isDark ? '#333' : '#f3f4f6'}; }
        .ollama-config-refresh-btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .ollama-config-section { margin-bottom: 20px; }
        .ollama-config-label { display: flex; align-items: center; gap: 6px; font-size: 14px; font-weight: 600; color: ${isDark ? '#e0e0e0' : '#111'}; margin-bottom: 4px; }
        .ollama-config-hint { font-size: 12px; color: ${isDark ? '#777' : '#6b7280'}; margin: 0 0 8px; }
        .ollama-config-toggle-row { display: flex; align-items: center; justify-content: space-between; padding: 12px 0; border-top: 1px solid ${isDark ? '#333' : '#e5e7eb'}; margin-bottom: 12px; }
        .ollama-config-toggle-label { font-size: 14px; font-weight: 500; color: ${isDark ? '#ccc' : '#374151'}; }
        .ollama-toggle-switch { position: relative; width: 40px; height: 22px; display: inline-block; }
        .ollama-toggle-switch input { opacity: 0; width: 0; height: 0; }
        .ollama-toggle-slider { position: absolute; inset: 0; border-radius: 22px; background: ${isDark ? '#444' : '#d1d5db'}; cursor: pointer; transition: 0.2s; }
        .ollama-toggle-slider::before { content: ''; position: absolute; width: 16px; height: 16px; border-radius: 50%; background: #fff; left: 3px; top: 3px; transition: 0.2s; }
        .ollama-toggle-switch input:checked + .ollama-toggle-slider { background: #7c3aed; }
        .ollama-toggle-switch input:checked + .ollama-toggle-slider::before { transform: translateX(18px); }
        .ollama-config-persona-list { display: flex; flex-direction: column; gap: 10px; padding-bottom: 4px; }
        .ollama-config-persona-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 8px 12px; border-radius: 10px; background: ${isDark ? '#262636' : '#f9fafb'}; }
        .ollama-persona-info { display: flex; align-items: center; gap: 8px; min-width: 0; flex-shrink: 0; }
        .ollama-persona-avatar { width: 28px; height: 28px; border-radius: 50%; object-fit: cover; }
        .ollama-persona-icon-placeholder { width: 28px; height: 28px; border-radius: 50%; background: ${isDark ? '#444' : '#e5e7eb'}; }
        .ollama-persona-name { font-size: 13px; font-weight: 500; color: ${isDark ? '#ccc' : '#374151'}; white-space: nowrap; }
        .ollama-config-footer { display: flex; justify-content: flex-end; gap: 10px; padding: 16px 24px; border-top: 1px solid ${isDark ? '#333' : '#e5e7eb'}; }
        .ollama-config-cancel-btn { padding: 8px 16px; border-radius: 8px; border: 1px solid ${isDark ? '#444' : '#d1d5db'}; background: transparent; color: ${isDark ? '#ccc' : '#374151'}; font-size: 14px; cursor: pointer; }
        .ollama-config-cancel-btn:hover { background: ${isDark ? '#333' : '#f3f4f6'}; }
        .ollama-config-save-btn { display: flex; align-items: center; gap: 6px; padding: 8px 20px; border-radius: 8px; border: none; background: #7c3aed; color: #fff; font-size: 14px; font-weight: 500; cursor: pointer; transition: 0.15s; }
        .ollama-config-save-btn:hover:not(:disabled) { background: #6d28d9; }
        .ollama-config-save-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .spinning { animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
};


const GEMINI_OPTION = {
  model_id: 'gemini-2.5-flash',
  client_id: 'gemini',
  client_name: 'Google Gemini',
  api_url: '',
  persona_name: '',
  system_prompt: '',
};

const NeonModelSelect = ({ neonModels, vllmModels, value, onChange, placeholder, isDark, compact }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [personaOpen, setPersonaOpen] = useState(null);

  const handleSelectNeonModel = (model, persona) => {
    const firstVllm = vllmModels.find(v =>
      v.model_id.toLowerCase().includes(model.name.toLowerCase())
    );
    onChange({
      model_id: firstVllm ? firstVllm.model_id : model.model_id,
      client_id: firstVllm ? firstVllm.client_id : 'neon',
      client_name: firstVllm ? firstVllm.client_name : 'Neon.ai',
      api_url: firstVllm ? firstVllm.api_url : '',
      persona_name: persona?.persona_name || '',
      system_prompt: persona?.system_prompt || '',
    });
    setIsOpen(false);
    setPersonaOpen(null);
  };

  const handleSelectGemini = () => {
    onChange({ ...GEMINI_OPTION });
    setIsOpen(false);
  };

  const handleClear = (e) => {
    e.stopPropagation();
    onChange(null);
  };

  const displayName = () => {
    if (!value) return placeholder;
    if (value.client_id === 'gemini') return `Gemini (${value.model_id})`;
    const short = (value.model_id || '').split('/').pop();
    if (value.persona_name) return `${short} · ${value.persona_name}`;
    return `${short} (${value.client_name || value.client_id})`;
  };

  const isGeminiSelected = value?.client_id === 'gemini';

  return (
    <div style={{ position: 'relative' }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          width: compact ? '220px' : '100%', padding: compact ? '6px 10px' : '10px 14px',
          borderRadius: '10px', border: `1px solid ${isDark ? '#444' : '#d1d5db'}`,
          background: isDark ? '#2a2a3a' : '#fff',
          color: value ? (isDark ? '#e0e0e0' : '#111') : (isDark ? '#666' : '#9ca3af'),
          fontSize: compact ? '12px' : '14px', cursor: 'pointer', textAlign: 'left', gap: '8px',
        }}
      >
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
          {displayName()}
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0 }}>
          {value && <span onClick={handleClear} style={{ cursor: 'pointer', opacity: 0.5, fontSize: '12px' }} title="Clear">✕</span>}
          <ChevronDown size={compact ? 12 : 14} style={{ opacity: 0.5, transform: isOpen ? 'rotate(180deg)' : 'none', transition: '0.15s' }} />
        </div>
      </button>

      {isOpen && (
        <div style={{
          position: 'absolute', top: '100%', left: 0,
          right: compact ? 'auto' : 0, width: compact ? '320px' : undefined,
          marginTop: '4px', borderRadius: '10px',
          border: `1px solid ${isDark ? '#444' : '#d1d5db'}`,
          background: isDark ? '#1e1e2e' : '#fff',
          boxShadow: '0 8px 24px rgba(0,0,0,0.15)', zIndex: 50,
          maxHeight: '320px', overflowY: 'auto',
        }}>
          {/* Cloud models (Gemini) */}
          <div>
            <div style={{
              padding: '8px 14px', fontSize: '11px', fontWeight: 700,
              textTransform: 'uppercase', letterSpacing: '0.5px',
              color: isDark ? '#3b82f6' : '#2563eb',
              borderBottom: `1px solid ${isDark ? '#2a2a3a' : '#f3f4f6'}`,
            }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                <Cloud size={11} /> Cloud
              </span>
            </div>
            <button
              onClick={handleSelectGemini}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                width: '100%', padding: '10px 14px', border: 'none',
                background: isGeminiSelected ? (isDark ? '#333' : '#f3f4f6') : 'transparent',
                color: isDark ? '#e0e0e0' : '#111', fontSize: '13px',
                cursor: 'pointer', textAlign: 'left',
                borderBottom: `1px solid ${isDark ? '#2a2a3a' : '#f3f4f6'}`,
              }}
              onMouseOver={e => { if (!isGeminiSelected) e.currentTarget.style.background = isDark ? '#2a2a3a' : '#f9fafb'; }}
              onMouseOut={e => { if (!isGeminiSelected) e.currentTarget.style.background = isGeminiSelected ? (isDark ? '#333' : '#f3f4f6') : 'transparent'; }}
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', minWidth: 0, flex: 1 }}>
                <span style={{ fontWeight: 500 }}>Gemini 2.5 Flash</span>
                <span style={{ fontSize: '11px', color: isDark ? '#666' : '#9ca3af' }}>Google Cloud AI</span>
              </div>
              {isGeminiSelected && <Check size={14} style={{ color: '#3b82f6', flexShrink: 0 }} />}
            </button>
          </div>

          {/* Neon BrainForge models with personas */}
          {neonModels.length > 0 && (
            <div>
              <div style={{
                padding: '8px 14px', fontSize: '11px', fontWeight: 700,
                textTransform: 'uppercase', letterSpacing: '0.5px',
                color: isDark ? '#7c3aed' : '#6d28d9',
                borderBottom: `1px solid ${isDark ? '#2a2a3a' : '#f3f4f6'}`,
                borderTop: `1px solid ${isDark ? '#333' : '#e5e7eb'}`,
              }}>
                Neon.ai BrainForge
              </div>
              {neonModels.map(model => (
                <div key={model.model_id}>
                  <button
                    onClick={() => {
                      if (model.personas?.length > 0) {
                        setPersonaOpen(personaOpen === model.model_id ? null : model.model_id);
                      } else {
                        handleSelectNeonModel(model, null);
                      }
                    }}
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      width: '100%', padding: '10px 14px', border: 'none',
                      background: 'transparent', color: isDark ? '#e0e0e0' : '#111',
                      fontSize: '13px', cursor: 'pointer', textAlign: 'left',
                      borderBottom: `1px solid ${isDark ? '#2a2a3a' : '#f3f4f6'}`,
                    }}
                    onMouseOver={e => e.currentTarget.style.background = isDark ? '#2a2a3a' : '#f9fafb'}
                    onMouseOut={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', flex: 1, minWidth: 0 }}>
                      <span style={{ fontWeight: 500 }}>{model.name}</span>
                      <span style={{ fontSize: '11px', color: isDark ? '#666' : '#9ca3af' }}>
                        v{model.version} · {(model.personas || []).length} persona{(model.personas || []).length !== 1 ? 's' : ''}
                      </span>
                    </div>
                    {model.personas?.length > 0 && (
                      <ChevronDown size={14} style={{
                        opacity: 0.5, flexShrink: 0,
                        transform: personaOpen === model.model_id ? 'rotate(180deg)' : 'none',
                        transition: '0.15s',
                      }} />
                    )}
                  </button>
                  {personaOpen === model.model_id && model.personas?.map(p => {
                    const isSelected = value?.persona_name === p.persona_name &&
                      (value?.model_id || '').includes(model.name);
                    return (
                      <button
                        key={p.id || p.persona_name}
                        onClick={() => handleSelectNeonModel(model, p)}
                        style={{
                          display: 'flex', alignItems: 'center', gap: '8px',
                          width: '100%', padding: '8px 14px 8px 28px', border: 'none',
                          background: isSelected ? (isDark ? '#333' : '#f3f4f6') : 'transparent',
                          color: isDark ? '#ccc' : '#374151', fontSize: '12px',
                          cursor: 'pointer', textAlign: 'left',
                          borderBottom: `1px solid ${isDark ? '#222' : '#f9fafb'}`,
                        }}
                        onMouseOver={e => { if (!isSelected) e.currentTarget.style.background = isDark ? '#262636' : '#fafafa'; }}
                        onMouseOut={e => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
                      >
                        <User2 size={12} style={{ flexShrink: 0, opacity: 0.6 }} />
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1px', flex: 1, minWidth: 0 }}>
                          <span style={{ fontWeight: 500 }}>{p.persona_name}</span>
                          {p.description && (
                            <span style={{ fontSize: '11px', color: isDark ? '#555' : '#9ca3af', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {p.description}
                            </span>
                          )}
                        </div>
                        {isSelected && <Check size={12} style={{ color: '#7c3aed', flexShrink: 0 }} />}
                      </button>
                    );
                  })}
                </div>
              ))}
            </div>
          )}

          {neonModels.length === 0 && (
            <div style={{ padding: '16px', textAlign: 'center', color: isDark ? '#666' : '#9ca3af', fontSize: '13px' }}>
              No Neon.ai models available
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default OllamaModelConfig;
