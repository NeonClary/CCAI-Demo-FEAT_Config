import React, { useState, useEffect } from 'react';
import { X, ChevronLeft, ChevronRight, Check } from 'lucide-react';

const STEPS = [
  {
    title: 'Academic Info',
    fields: [
      { key: 'major', label: 'Major', type: 'text', placeholder: 'e.g. Computer Science' },
      { key: 'minor', label: 'Minor (optional)', type: 'text', placeholder: 'e.g. Mathematics' },
      { key: 'year', label: 'Year', type: 'select', options: ['Freshman', 'Sophomore', 'Junior', 'Senior', 'Graduate'] },
      { key: 'gpa_range', label: 'GPA Range', type: 'select', options: ['Below 2.0', '2.0-2.5', '2.5-3.0', '3.0-3.5', '3.5-4.0'] },
    ],
  },
  {
    title: 'Goals & Plans',
    fields: [
      { key: 'career_goals', label: 'Career Goals', type: 'textarea', placeholder: 'What do you want to do after graduation?' },
      { key: 'courses_completed', label: 'Courses Completed (comma-separated)', type: 'text', placeholder: 'e.g. CSCI 1300, MATH 2400' },
      { key: 'courses_planned', label: 'Planned Courses (comma-separated)', type: 'text', placeholder: 'e.g. CSCI 3104, ENES 1010' },
    ],
  },
  {
    title: 'Preferences',
    fields: [
      { key: 'schedule_preferences', label: 'Schedule Preferences', type: 'text', placeholder: 'e.g. No classes before 10am' },
      { key: 'learning_style', label: 'Learning Style', type: 'text', placeholder: 'e.g. Visual, hands-on' },
      { key: 'extracurriculars', label: 'Extracurriculars', type: 'textarea', placeholder: 'Clubs, sports, organizations...' },
    ],
  },
];

const ProfileWalkthrough = ({ authToken, onClose, existingProfile }) => {
  const [step, setStep] = useState(0);
  const [formData, setFormData] = useState({});
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const fetchProfile = async () => {
      try {
        const resp = await fetch(`${process.env.REACT_APP_API_URL}/api/users/me/profile`, {
          headers: { 'Authorization': `Bearer ${authToken}` },
        });
        if (resp.ok && !cancelled) {
          const profile = await resp.json();
          const init = {};
          STEPS.forEach(s => s.fields.forEach(f => {
            const val = profile[f.key];
            if (Array.isArray(val)) init[f.key] = val.join(', ');
            else if (val) init[f.key] = val;
          }));
          setFormData(init);
        }
      } catch (e) {
        // Fall back to existingProfile prop
        if (!cancelled && existingProfile) {
          const init = {};
          STEPS.forEach(s => s.fields.forEach(f => {
            const val = existingProfile[f.key];
            if (Array.isArray(val)) init[f.key] = val.join(', ');
            else if (val) init[f.key] = val;
          }));
          setFormData(init);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchProfile();
    return () => { cancelled = true; };
  }, [authToken, existingProfile]);

  const handleChange = (key, value) => setFormData(prev => ({ ...prev, [key]: value }));

  const saveProfile = async () => {
    const payload = { ...formData };
    ['courses_completed', 'courses_planned'].forEach(k => {
      if (typeof payload[k] === 'string') {
        payload[k] = payload[k].split(',').map(s => s.trim()).filter(Boolean);
      }
    });
    const hasData = Object.values(payload).some(v =>
      Array.isArray(v) ? v.length > 0 : Boolean(v)
    );
    if (!hasData) return;
    try {
      await fetch(`${process.env.REACT_APP_API_URL}/api/users/me/profile`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${authToken}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
    } catch (e) {
      console.error('Failed to save profile:', e);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    await saveProfile();
    setSaving(false);
    onClose();
  };

  const handleClose = async () => {
    await saveProfile();
    onClose();
  };

  const currentStep = STEPS[step];
  const isLast = step === STEPS.length - 1;

  return (
    <div onClick={handleClose} style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      background: 'rgba(0,0,0,0.5)', display: 'flex',
      alignItems: 'center', justifyContent: 'center',
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--bg-primary)', borderRadius: 16,
        width: '90%', maxWidth: 480, padding: 24,
        boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
      }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-secondary)', fontSize: 14 }}>
            Loading profile...
          </div>
        ) : <>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h3 style={{ margin: 0, fontSize: 16, color: 'var(--text-primary)' }}>
            {currentStep.title} ({step + 1}/{STEPS.length})
          </h3>
          <button onClick={handleClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}>
            <X size={18} />
          </button>
        </div>

        {/* Progress bar */}
        <div style={{ height: 4, background: 'var(--bg-secondary)', borderRadius: 2, marginBottom: 20 }}>
          <div style={{
            height: '100%', borderRadius: 2, background: 'var(--accent-primary)',
            width: `${((step + 1) / STEPS.length) * 100}%`, transition: 'width 0.3s',
          }} />
        </div>

        {/* Fields */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {currentStep.fields.map(f => (
            <div key={f.key}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>
                {f.label}
              </label>
              {f.type === 'select' ? (
                <select
                  value={formData[f.key] || ''}
                  onChange={e => handleChange(f.key, e.target.value)}
                  style={{
                    width: '100%', padding: '8px 10px', borderRadius: 8,
                    border: '1px solid var(--border-primary)', background: 'var(--bg-secondary)',
                    color: 'var(--text-primary)', fontSize: 13,
                  }}
                >
                  <option value="">Select...</option>
                  {f.options.map(o => <option key={o} value={o}>{o}</option>)}
                </select>
              ) : f.type === 'textarea' ? (
                <textarea
                  value={formData[f.key] || ''}
                  onChange={e => handleChange(f.key, e.target.value)}
                  placeholder={f.placeholder}
                  rows={3}
                  style={{
                    width: '100%', padding: '8px 10px', borderRadius: 8,
                    border: '1px solid var(--border-primary)', background: 'var(--bg-secondary)',
                    color: 'var(--text-primary)', fontSize: 13, resize: 'vertical',
                  }}
                />
              ) : (
                <input
                  type="text"
                  value={formData[f.key] || ''}
                  onChange={e => handleChange(f.key, e.target.value)}
                  placeholder={f.placeholder}
                  style={{
                    width: '100%', padding: '8px 10px', borderRadius: 8,
                    border: '1px solid var(--border-primary)', background: 'var(--bg-secondary)',
                    color: 'var(--text-primary)', fontSize: 13,
                  }}
                />
              )}
            </div>
          ))}
        </div>

        {/* Navigation */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 24 }}>
          <button
            onClick={() => setStep(s => s - 1)}
            disabled={step === 0}
            style={{
              display: 'flex', alignItems: 'center', gap: 4, padding: '8px 14px',
              borderRadius: 8, border: '1px solid var(--border-primary)',
              background: 'var(--bg-secondary)', color: 'var(--text-primary)',
              cursor: step === 0 ? 'default' : 'pointer', opacity: step === 0 ? 0.4 : 1,
              fontSize: 13,
            }}
          >
            <ChevronLeft size={14} /> Back
          </button>
          {isLast ? (
            <button
              onClick={handleSave}
              disabled={saving}
              style={{
                display: 'flex', alignItems: 'center', gap: 4, padding: '8px 16px',
                borderRadius: 8, border: 'none',
                background: 'var(--accent-primary)', color: '#fff',
                cursor: 'pointer', fontSize: 13, fontWeight: 600,
              }}
            >
              <Check size={14} /> {saving ? 'Saving...' : 'Save Profile'}
            </button>
          ) : (
            <button
              onClick={() => setStep(s => s + 1)}
              style={{
                display: 'flex', alignItems: 'center', gap: 4, padding: '8px 14px',
                borderRadius: 8, border: 'none',
                background: 'var(--accent-primary)', color: '#fff',
                cursor: 'pointer', fontSize: 13, fontWeight: 600,
              }}
            >
              Next <ChevronRight size={14} />
            </button>
          )}
        </div>
        </>}
      </div>
    </div>
  );
};

export default ProfileWalkthrough;
