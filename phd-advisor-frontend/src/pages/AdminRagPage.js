import React, { useState, useEffect, useCallback } from 'react';
import { ArrowLeft, Upload, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import '../styles/ChatPage.css';

const AdminRagPage = ({ authToken, onNavigateToChat }) => {
  const { isDark } = useTheme();
  const [personas, setPersonas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState({});
  const [file, setFile] = useState(null);
  const [citationTitle, setCitationTitle] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  const loadPersonas = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${process.env.REACT_APP_API_URL}/api/admin/rag/personas`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (resp.status === 403) {
        setError('You do not have admin access. Set ADMIN_EMAILS on the server to include your account email.');
        setPersonas([]);
        return;
      }
      if (!resp.ok) throw new Error('Failed to load personas');
      const data = await resp.json();
      setPersonas(data.personas || []);
    } catch (e) {
      setError(e.message || 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, [authToken]);

  useEffect(() => {
    loadPersonas();
  }, [loadPersonas]);

  const togglePersona = (id) => {
    setSelected((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage(null);
    setError(null);
    const ids = Object.entries(selected).filter(([, v]) => v).map(([k]) => k);
    if (!file || ids.length === 0) {
      setError('Choose a file and at least one advisor persona.');
      return;
    }
    setSaving(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('persona_ids', JSON.stringify(ids));
      fd.append('citation_title', citationTitle || file.name);
      fd.append('source_url', sourceUrl || '');
      const resp = await fetch(`${process.env.REACT_APP_API_URL}/api/admin/rag/persona-document`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${authToken}` },
        body: fd,
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        const detail = data.detail;
        const msg = typeof detail === 'string' ? detail : JSON.stringify(detail || data);
        throw new Error(msg || resp.statusText);
      }
      setMessage(`Ingested ${data.chunks_created} chunk(s) for ${(data.persona_ids || []).join(', ')}.`);
      setFile(null);
      setCitationTitle('');
      setSourceUrl('');
      setSelected({});
    } catch (err) {
      setError(err.message || 'Upload failed');
    } finally {
      setSaving(false);
    }
  };

  const bg = isDark ? '#111827' : '#f9fafb';
  const card = isDark ? '#1f2937' : '#fff';
  const text = isDark ? '#e5e7eb' : '#111827';
  const muted = isDark ? '#9ca3af' : '#6b7280';

  return (
    <div style={{ minHeight: '100vh', background: bg, color: text, padding: '24px' }}>
      <button
        type="button"
        onClick={onNavigateToChat}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 8,
          marginBottom: 24,
          padding: '8px 14px',
          borderRadius: 8,
          border: `1px solid ${isDark ? '#374151' : '#e5e7eb'}`,
          background: card,
          color: text,
          cursor: 'pointer',
        }}
      >
        <ArrowLeft size={18} /> Back to chat
      </button>

      <div style={{ maxWidth: 640, margin: '0 auto' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 8 }}>Admin — Persona knowledge (RAG)</h1>
        <p style={{ color: muted, marginBottom: 24, lineHeight: 1.6 }}>
          Upload PDF, TXT, or DOCX. Each file is embedded once per selected advisor; only those advisors retrieve it in chat.
          Optional URL and title are used for markdown citations in answers.
        </p>

        {loading && (
          <p style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Loader2 className="spinning" size={18} /> Loading personas…
          </p>
        )}

        {error && (
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, padding: 12, borderRadius: 8, background: isDark ? '#422006' : '#fef2f2', color: isDark ? '#fdba74' : '#b91c1c', marginBottom: 16 }}>
            <AlertCircle size={18} style={{ flexShrink: 0, marginTop: 2 }} />
            <span>{error}</span>
          </div>
        )}

        {message && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: 12, borderRadius: 8, background: isDark ? '#14532d' : '#ecfdf5', color: isDark ? '#86efac' : '#166534', marginBottom: 16 }}>
            <CheckCircle size={18} />
            <span>{message}</span>
          </div>
        )}

        {!loading && personas.length > 0 && (
          <form onSubmit={handleSubmit} style={{ background: card, padding: 24, borderRadius: 12, border: `1px solid ${isDark ? '#374151' : '#e5e7eb'}` }}>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 600 }}>File</label>
            <input
              type="file"
              accept=".pdf,.txt,.doc,.docx"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              style={{ marginBottom: 20, width: '100%' }}
            />

            <label style={{ display: 'block', marginBottom: 8, fontWeight: 600 }}>Assign to advisors</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 20 }}>
              {personas.map((p) => (
                <label key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={!!selected[p.id]}
                    onChange={() => togglePersona(p.id)}
                  />
                  <span><strong>{p.name}</strong> <span style={{ color: muted }}>({p.id})</span></span>
                </label>
              ))}
            </div>

            <label style={{ display: 'block', marginBottom: 8, fontWeight: 600 }}>Citation title</label>
            <input
              type="text"
              value={citationTitle}
              onChange={(e) => setCitationTitle(e.target.value)}
              placeholder="e.g. Company safety manual 2026"
              style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: `1px solid ${isDark ? '#4b5563' : '#d1d5db'}`, background: isDark ? '#111827' : '#fff', color: text, marginBottom: 16 }}
            />

            <label style={{ display: 'block', marginBottom: 8, fontWeight: 600 }}>Source URL (optional)</label>
            <input
              type="url"
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
              placeholder="https://..."
              style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: `1px solid ${isDark ? '#4b5563' : '#d1d5db'}`, background: isDark ? '#111827' : '#fff', color: text, marginBottom: 20 }}
            />

            <button
              type="submit"
              disabled={saving}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                padding: '10px 20px',
                borderRadius: 8,
                border: 'none',
                background: '#7c3aed',
                color: '#fff',
                fontWeight: 600,
                cursor: saving ? 'not-allowed' : 'pointer',
                opacity: saving ? 0.7 : 1,
              }}
            >
              {saving ? <Loader2 size={18} className="spinning" /> : <Upload size={18} />}
              Ingest document
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

export default AdminRagPage;
