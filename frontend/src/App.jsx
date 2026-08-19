import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowRight, Search, Check, AlertCircle, FileText,
  RotateCcw, Eye, ShieldCheck, Zap, Split, PenLine, Award,
  Copy, Download, LogOut, MessageSquareText
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './index.css';

const STAGES = [
  { id: 'planner', num: '01', label: 'Planning', desc: 'Structuring research into focused questions', icon: Split },
  { id: 'research', num: '02', label: 'Research', desc: 'Gathering multi-source data parallelly', icon: Search },
  { id: 'claim_extraction', num: '03', label: 'Claim Extraction', desc: 'Extracting key factual claims requiring verification', icon: Zap },
  { id: 'claim_fidelity', num: '04', label: 'Claim Fidelity Check', desc: 'Auditing extracted claims against source text neutrality', icon: Check },
  { id: 'fact_verification', num: '05', label: 'Fact Verification', desc: 'Searching evidence and verifying claims in parallel', icon: ShieldCheck },
  { id: 'analysis', num: '06', label: 'Analysis & Synthesis', desc: 'Extracting insights and integrating contrarian views', icon: Eye },
  { id: 'writer', num: '07', label: 'Writing', desc: 'Composing initial research report', icon: PenLine },
  { id: 'critic_loop', num: '08', label: 'Quality Loop', desc: 'Iterative refinement and scoring', icon: AlertCircle },
  { id: 'grounded_citations', num: '09', label: 'Grounded Citations', desc: 'Aligning evidence, inline references and footnotes', icon: Award }
];

const CircularProgress = ({ value }) => {
  const radius = 14;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (Math.min(value, 100) / 100) * circumference;
  return (
    <div style={{ position: 'relative', width: '36px', height: '36px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <svg width="36" height="36" style={{ transform: 'rotate(-90deg)' }}>
        <circle
          cx="18"
          cy="18"
          r={radius}
          fill="transparent"
          stroke="rgba(255,255,255,0.03)"
          strokeWidth="3"
        />
        <motion.circle
          cx="18"
          cy="18"
          r={radius}
          fill="transparent"
          stroke="var(--accent-base)"
          strokeWidth="3"
          strokeDasharray={circumference}
          animate={{ strokeDashoffset }}
          transition={{ duration: 0.2, ease: 'linear' }}
        />
      </svg>
      <span style={{ position: 'absolute', fontFamily: 'var(--font-mono)', fontSize: '0.6rem', fontWeight: 600, color: 'var(--accent-base)' }}>
        {Math.round(value)}%
      </span>
    </div>
  );
};

export default function App() {
  const [researchTopic, setResearchTopic] = useState('');
  const [executionPhase, setExecutionPhase] = useState('idle'); 
  const [stageExecutionStatus, setStageExecutionStatus] = useState({});
  const [pipelineStageOutputs, setPipelineStageOutputs] = useState({});
  const [pipelineMetadata, setPipelineMetadata] = useState({});
  const [pipelineExecutionError, setPipelineExecutionError] = useState('');
  const [activeStageProgress, setActiveStageProgress] = useState({});
  const [hasCopiedToClipboard, setHasCopiedToClipboard] = useState(false);
  const [selectedResultTab, setSelectedResultTab] = useState('report');
  
  const [sessionJwtToken, setSessionJwtToken] = useState(localStorage.getItem('arcs_token') || '');
  const [authenticatedUserEmail, setAuthenticatedUserEmail] = useState(localStorage.getItem('arcs_email') || '');
  const [archivedResearchRuns, setArchivedResearchRuns] = useState([]);
  const [authenticationMode, setAuthenticationMode] = useState('login');
  const [inputUserEmail, setInputUserEmail] = useState('');
  const [inputUserPassword, setInputUserPassword] = useState('');
  const [authenticationError, setAuthenticationError] = useState('');
  const [isAuthenticationPending, setIsAuthenticationPending] = useState(false);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [selectedHistoryRecordId, setSelectedHistoryRecordId] = useState(null);

  const topicInputReference = useRef(null);
  const activePipelineTopicRef = useRef('');

  const API_BASE_URL = import.meta.env.VITE_API_BASE || import.meta.env.VITE_API_URL || (
    window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" 
      ? "http://localhost:7860" 
      : "https://arcs-backend-siva.onrender.com"
  );

  const fetchArchivedResearchHistory = async (activeToken) => {
    if (!activeToken) return;
    setIsHistoryLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/history`, {
        headers: { 'Authorization': `Bearer ${activeToken}` }
      });
      const responseData = await response.json();
      if (response.ok) {
        setArchivedResearchRuns(responseData.history || []);
      } else if (response.status === 401) {
        handleUserLogout();
      }
    } catch (err) {
      console.error("Error fetching history:", err);
    } finally {
      setIsHistoryLoading(false);
    }
  };

  useEffect(() => {
    if (sessionJwtToken) {
      fetchArchivedResearchHistory(sessionJwtToken);
    } else {
      setArchivedResearchRuns([]);
    }
  }, [sessionJwtToken]);

  const handleUserLogin = async (e) => {
    e.preventDefault();
    setIsAuthenticationPending(true);
    setAuthenticationError('');
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: inputUserEmail, password: inputUserPassword })
      });
      const responseData = await response.json();
      if (response.ok) {
        localStorage.setItem('arcs_token', responseData.token);
        localStorage.setItem('arcs_email', responseData.email);
        setSessionJwtToken(responseData.token);
        setAuthenticatedUserEmail(responseData.email);
        setInputUserPassword('');
        setInputUserEmail('');
      } else {
        setAuthenticationError(responseData.error || 'Login failed');
      }
    } catch (err) {
      setAuthenticationError('Connection failed. Please check backend server.');
    } finally {
      setIsAuthenticationPending(false);
    }
  };

  const handleUserRegistration = async (e) => {
    e.preventDefault();
    setIsAuthenticationPending(true);
    setAuthenticationError('');
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: inputUserEmail, password: inputUserPassword })
      });
      const responseData = await response.json();
      if (response.ok) {
        setAuthenticationMode('login');
        const loginResponse = await fetch(`${API_BASE_URL}/api/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: inputUserEmail, password: inputUserPassword })
        });
        const loginData = await loginResponse.json();
        if (loginResponse.ok) {
          localStorage.setItem('arcs_token', loginData.token);
          localStorage.setItem('arcs_email', loginData.email);
          setSessionJwtToken(loginData.token);
          setAuthenticatedUserEmail(loginData.email);
          setInputUserPassword('');
          setInputUserEmail('');
        } else {
          setAuthenticationError('Registered successfully, but login failed.');
        }
      } else {
        setAuthenticationError(responseData.error || 'Registration failed');
      }
    } catch (err) {
      setAuthenticationError('Connection failed. Please check backend server.');
    } finally {
      setIsAuthenticationPending(false);
    }
  };

  const handleUserLogout = () => {
    localStorage.removeItem('arcs_token');
    localStorage.removeItem('arcs_email');
    setSessionJwtToken('');
    setAuthenticatedUserEmail('');
    setArchivedResearchRuns([]);
    setResearchTopic('');
    setExecutionPhase('idle');
    setStageExecutionStatus({});
    setPipelineStageOutputs({});
    setPipelineMetadata({});
    setSelectedHistoryRecordId(null);
  };

  const loadHistoryItemDetail = async (recordId) => {
    if (!sessionJwtToken) return;
    setSelectedHistoryRecordId(recordId);
    setExecutionPhase('streaming');
    setPipelineExecutionError('');
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/history/${recordId}`, {
        headers: { 'Authorization': `Bearer ${sessionJwtToken}` }
      });
      const recordData = await response.json();
      if (response.ok) {
        setResearchTopic(recordData.topic);
        activePipelineTopicRef.current = recordData.topic;
        setPipelineStageOutputs(recordData.results || {});
        setPipelineMetadata(recordData.metadata || {});
        
        const completedStagesMap = {};
        const completedPercentagesMap = {};
        STAGES.forEach(s => {
          completedStagesMap[s.id] = 'done';
          completedPercentagesMap[s.id] = 100;
        });
        setStageExecutionStatus(completedStagesMap);
        setActiveStageProgress(completedPercentagesMap);
        setExecutionPhase('done');
      } else {
        setPipelineExecutionError(recordData.error || 'Failed to load history detail');
        setExecutionPhase('error');
      }
    } catch (err) {
      setPipelineExecutionError('Failed to load history detail from server.');
      setExecutionPhase('error');
    }
  };

  const handleCopyToClipboard = () => {
    if (pipelineStageOutputs.writer) {
      navigator.clipboard.writeText(pipelineStageOutputs.writer);
      setHasCopiedToClipboard(true);
      setTimeout(() => setHasCopiedToClipboard(false), 2000);
    }
  };

  const handleExportPdfReport = () => {
    const printWindow = window.open('', '_blank');
    if (!printWindow) return;

    const reportHtml = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>ARCS Research Report - ${activePipelineTopicRef.current}</title>
          <style>
            body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; padding: 40px; color: #111; line-height: 1.6; }
            h1 { font-size: 28px; margin-bottom: 5px; color: #000; }
            h2 { font-size: 20px; margin-top: 30px; border-bottom: 1px solid #ccc; padding-bottom: 5px; }
            h3 { font-size: 16px; margin-top: 20px; }
            p { margin-bottom: 15px; }
            code { background: #f4f4f4; padding: 2px 5px; border-radius: 3px; font-family: monospace; }
            pre { background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }
            blockquote { border-left: 4px solid #333; padding-left: 15px; color: #555; margin: 20px 0; }
            .meta { font-size: 12px; color: #666; margin-bottom: 30px; }
          </style>
        </head>
        <body>
          <h1>${activePipelineTopicRef.current}</h1>
          <div class="meta">Research Report Generated by ARCS on ${new Date().toLocaleDateString()}</div>
          <hr />
          <div>${document.querySelector('.prose')?.innerHTML || pipelineStageOutputs.writer}</div>
        </body>
      </html>
    `;
    printWindow.document.write(reportHtml);
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => {
      printWindow.print();
    }, 500);
  };

  const resetResearchSession = () => {
    setExecutionPhase('idle');
    setResearchTopic('');
    setStageExecutionStatus({});
    setPipelineStageOutputs({});
    setPipelineMetadata({});
    setPipelineExecutionError('');
    setActiveStageProgress({});
    setSelectedHistoryRecordId(null);
    setTimeout(() => topicInputReference.current?.focus(), 100);
  };

  const executeResearchPipeline = async () => {
    if (!researchTopic.trim() || executionPhase === 'streaming') return;

    const currentTopicQuery = researchTopic.trim();
    activePipelineTopicRef.current = currentTopicQuery;
    setExecutionPhase('streaming');
    setStageExecutionStatus({});
    setPipelineStageOutputs({});
    setPipelineMetadata({});
    setPipelineExecutionError('');
    setSelectedHistoryRecordId(null);

    const stageWeights = {
      planner: 10,
      research: 15,
      claim_extraction: 10,
      claim_fidelity: 10,
      fact_verification: 15,
      analysis: 10,
      writer: 15,
      critic_loop: 10,
      grounded_citations: 5
    };

    try {
      const response = await fetch(`${API_BASE_URL}/api/research-stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(sessionJwtToken ? { 'Authorization': `Bearer ${sessionJwtToken}` } : {})
        },
        body: JSON.stringify({ topic: currentTopicQuery })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonStr = line.slice(6).trim();
            if (!jsonStr) continue;

            try {
              const event = JSON.parse(jsonStr);

              if (event.type === 'stage_started') {
                setStageExecutionStatus(prev => ({ ...prev, [event.stage]: 'running' }));
                setActiveStageProgress(prev => ({ ...prev, [event.stage]: 30 }));
              } else if (event.type === 'stage_progress') {
                setActiveStageProgress(prev => ({ ...prev, [event.stage]: Math.min(60 + (event.iteration || 1) * 10, 90) }));
              } else if (event.type === 'stage_completed') {
                setStageExecutionStatus(prev => ({ ...prev, [event.stage]: 'done' }));
                setActiveStageProgress(prev => ({ ...prev, [event.stage]: 100 }));
                setPipelineStageOutputs(prev => ({ ...prev, [event.stage]: event.result }));
              } else if (event.type === 'complete') {
                setPipelineStageOutputs(event.results);
                setPipelineMetadata(event.metadata);
                setExecutionPhase('done');
                fetchArchivedResearchHistory(sessionJwtToken);
              } else if (event.type === 'error') {
                setPipelineExecutionError(event.error);
                setExecutionPhase('error');
                return;
              }
            } catch (e) {
              console.error("Parse error:", e);
            }
          }
        }
      }
    } catch (err) {
      setPipelineExecutionError(err.message);
      setExecutionPhase('error');
    }
  };

  if (!sessionJwtToken) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'radial-gradient(circle at top left, #121820, #080a0f)',
        padding: '1.5rem',
        fontFamily: 'var(--font-sans)'
      }}>
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
          style={{
            background: 'rgba(255, 255, 255, 0.02)',
            backdropFilter: 'blur(20px)',
            border: '1px solid rgba(255, 255, 255, 0.05)',
            borderRadius: '16px',
            padding: '2.5rem',
            width: '100%',
            maxWidth: '400px',
            boxShadow: '0 20px 40px rgba(0, 0, 0, 0.5)'
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem', marginBottom: '2rem' }}>
            <img src="/logo.png" alt="ARCS Logo" style={{ height: '64px', width: 'auto', marginBottom: '0.5rem' }} />
            <h1 style={{
              fontSize: '1.8rem',
              fontWeight: 700,
              color: 'var(--accent-base)',
              letterSpacing: '-0.05em',
              marginBottom: '0.25rem'
            }}>
              ARCS
            </h1>
            <p style={{ fontSize: '0.8rem', color: '#888', fontWeight: 500 }}>
              Advanced Research & Curation System
            </p>
          </div>

          <form onSubmit={authenticationMode === 'login' ? handleUserLogin : handleUserRegistration}>
            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ display: 'block', fontSize: '0.75rem', color: '#aaa', marginBottom: '0.5rem', fontWeight: 600 }}>EMAIL ADDRESS</label>
              <input
                type="email"
                required
                value={inputUserEmail}
                onChange={(e) => setInputUserEmail(e.target.value)}
                placeholder="you@example.com"
                style={{
                  width: '100%',
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                  padding: '0.75rem 1rem',
                  color: '#fff',
                  fontSize: '0.9rem',
                  outline: 'none',
                  boxSizing: 'border-box'
                }}
              />
            </div>

            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'block', fontSize: '0.75rem', color: '#aaa', marginBottom: '0.5rem', fontWeight: 600 }}>PASSWORD</label>
              <input
                type="password"
                required
                value={inputUserPassword}
                onChange={(e) => setInputUserPassword(e.target.value)}
                placeholder="••••••••"
                style={{
                  width: '100%',
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                  padding: '0.75rem 1rem',
                  color: '#fff',
                  fontSize: '0.9rem',
                  outline: 'none',
                  boxSizing: 'border-box'
                }}
              />
            </div>

            {authenticationError && (
              <div style={{
                background: 'rgba(220, 38, 38, 0.1)',
                border: '1px solid rgba(220, 38, 38, 0.2)',
                borderRadius: '8px',
                padding: '0.75rem',
                color: '#f87171',
                fontSize: '0.8rem',
                marginBottom: '1.25rem',
                textAlign: 'center'
              }}>
                {authenticationError}
              </div>
            )}

            <button
              type="submit"
              disabled={isAuthenticationPending}
              style={{
                width: '100%',
                background: 'var(--accent-base)',
                color: '#000',
                border: 'none',
                borderRadius: '8px',
                padding: '0.85rem',
                fontSize: '0.9rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'opacity 0.2s',
                opacity: isAuthenticationPending ? 0.7 : 1
              }}
            >
              {isAuthenticationPending ? 'Please wait...' : authenticationMode === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>

          <div style={{ textAlign: 'center', marginTop: '1.5rem' }}>
            <span style={{ fontSize: '0.8rem', color: '#666' }}>
              {authenticationMode === 'login' ? "Don't have an account? " : "Already have an account? "}
            </span>
            <button
              onClick={() => {
                setAuthenticationMode(authenticationMode === 'login' ? 'register' : 'login');
                setAuthenticationError('');
              }}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--accent-base)',
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: 'pointer',
                padding: 0
              }}
            >
              {authenticationMode === 'login' ? 'Register' : 'Sign In'}
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-base)', color: 'var(--text-primary)', overflow: 'hidden' }}>
      <aside className="glass-panel" style={{
        width: '320px',
        borderRight: '1px solid var(--border-base)',
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0,
        background: 'var(--bg-surface)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '1.5rem', borderBottom: '1px solid var(--border-base)' }}>
          <img src="/logo.png" alt="Logo" style={{ height: '28px', width: 'auto', objectFit: 'contain' }} />
          <span style={{ fontFamily: 'var(--font-serif)', fontSize: '1.4rem', fontWeight: 600, letterSpacing: '0.05em' }}>
            ARC<span style={{ color: 'var(--accent-base)' }}>S</span>
          </span>
        </div>

        <div style={{
          margin: '1rem 1rem 1rem',
          padding: '0.85rem',
          background: 'rgba(255, 255, 255, 0.015)',
          border: '1px solid var(--border-base)',
          borderRadius: '10px',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.75rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              background: 'rgba(255, 255, 255, 0.04)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontFamily: 'var(--font-mono)',
              fontWeight: 600,
              fontSize: '0.85rem',
              color: 'var(--accent-base)'
            }}>
              {authenticatedUserEmail ? authenticatedUserEmail[0].toUpperCase() : 'U'}
            </div>
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {authenticatedUserEmail}
              </div>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-tertiary)' }}>Authenticated User</div>
            </div>
            <button
              onClick={handleUserLogout}
              title="Logout"
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-tertiary)',
                cursor: 'pointer',
                padding: '0.25rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'color 0.2s'
              }}
              onMouseOver={e => e.currentTarget.style.color = '#f87171'}
              onMouseOut={e => e.currentTarget.style.color = 'var(--text-tertiary)'}
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>

        <div style={{ padding: '0 1rem 1rem 1rem' }}>
          <button
            onClick={resetResearchSession}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              background: 'var(--accent-base)',
              color: '#000',
              border: 'none',
              borderRadius: '8px',
              padding: '0.75rem',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'opacity 0.2s'
            }}
          >
            <RotateCcw size={16} /> New Research Session
          </button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '0 1rem 1rem 1rem' }}>
          <div style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)', marginBottom: '0.75rem', letterSpacing: '0.1em' }}>
            RECENT RESEARCH
          </div>
          {isHistoryLoading ? (
            <div style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)', textAlign: 'center', padding: '1rem' }}>Loading history...</div>
          ) : archivedResearchRuns.length === 0 ? (
            <div style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)', textAlign: 'center', padding: '1rem' }}>No past research runs.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {archivedResearchRuns.map((record) => {
                const isSelected = selectedHistoryRecordId === record.id;
                return (
                  <motion.div
                    key={record.id}
                    onClick={() => loadHistoryItemDetail(record.id)}
                    whileHover={{ scale: 1.01 }}
                    style={{
                      padding: '0.75rem',
                      borderRadius: '8px',
                      background: isSelected ? 'var(--accent-dim)' : 'rgba(255, 255, 255, 0.015)',
                      border: `1px solid ${isSelected ? 'var(--accent-base)' : 'var(--border-base)'}`,
                      cursor: 'pointer',
                      transition: 'all 0.2s'
                    }}
                  >
                    <div style={{ fontSize: '0.85rem', fontWeight: 500, color: isSelected ? 'var(--accent-base)' : 'var(--text-primary)', marginBottom: '0.25rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {record.topic}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                      <span>{new Date(record.timestamp).toLocaleDateString()}</span>
                      <span>Quality: {record.metadata?.quality_score || 8.0}/10</span>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          )}
        </div>
      </aside>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
        <header style={{
          padding: '1.25rem 2.5rem',
          borderBottom: '1px solid var(--border-base)',
          background: 'var(--bg-surface)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          zIndex: 10
        }}>
          <div>
            <span style={{ color: 'var(--text-tertiary)', fontSize: '0.85rem', fontFamily: 'var(--font-mono)' }}>
              {activePipelineTopicRef.current ? `SESSION: ${activePipelineTopicRef.current}` : 'NEW SESSION'}
            </span>
          </div>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)' }}>Advanced Research & Curation System</span>
          </div>
        </header>

        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
          <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            <AnimatePresence mode="wait">
              {executionPhase === 'idle' && (
                <motion.div
                  key="idle"
                  initial={{ opacity: 0, scale: 0.98 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.98 }}
                  transition={{ type: "spring", stiffness: 300, damping: 30 }}
                  style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '4rem 2rem' }}
                >
                  <div style={{
                    position: 'absolute', top: '20%', width: '600px', height: '600px',
                    background: 'radial-gradient(circle, var(--accent-glow) 0%, transparent 60%)',
                    pointerEvents: 'none', zIndex: 0, opacity: 0.6
                  }} />

                  <div style={{ position: 'relative', zIndex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%', maxWidth: '800px' }}>
                    <motion.h1 
                      initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.1 }}
                      style={{
                        fontFamily: 'var(--font-serif)', fontSize: 'clamp(3rem, 6vw, 5rem)', fontWeight: 300,
                        lineHeight: 1.1, textAlign: 'center', marginBottom: '3rem', letterSpacing: '-0.02em'
                      }}
                    >
                      Synthesize the world's <br/>
                      <em style={{ color: 'var(--accent-base)', fontStyle: 'italic' }}>deepest knowledge.</em>
                    </motion.h1>

                    <motion.div 
                      initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.2 }}
                      style={{ width: '100%', position: 'relative' }}
                    >
                      <input
                        ref={topicInputReference}
                        value={researchTopic}
                        onChange={e => setResearchTopic(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && executeResearchPipeline()}
                        placeholder="E.g., The geopolitical implications of solid-state batteries..."
                        style={{
                          width: '100%', background: 'var(--bg-surface-highlight)', border: '1px solid var(--border-focus)',
                          borderRadius: '12px', padding: '1.25rem 4rem 1.25rem 1.5rem',
                          fontFamily: 'var(--font-sans)', fontSize: '1.1rem', color: 'var(--text-primary)',
                          outline: 'none', boxShadow: '0 10px 30px rgba(0,0,0,0.5)', transition: 'all 0.3s'
                        }}
                        onFocus={e => { e.target.style.borderColor = 'var(--accent-base)'; e.target.style.boxShadow = '0 0 0 3px var(--accent-dim), 0 10px 30px rgba(0,0,0,0.5)'; }}
                        onBlur={e => { e.target.style.borderColor = 'var(--border-focus)'; e.target.style.boxShadow = '0 10px 30px rgba(0,0,0,0.5)'; }}
                        autoFocus
                      />
                      <button
                        onClick={executeResearchPipeline}
                        disabled={!researchTopic.trim()}
                        style={{
                          position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)',
                          background: 'var(--accent-base)', border: 'none', borderRadius: '8px',
                          color: 'var(--bg-base)', padding: '0.75rem', cursor: researchTopic.trim() ? 'pointer' : 'not-allowed',
                          opacity: researchTopic.trim() ? 1 : 0.5, transition: 'all 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center'
                        }}
                        onMouseOver={e => !e.currentTarget.disabled && (e.currentTarget.style.background = 'var(--accent-hover)')}
                        onMouseOut={e => !e.currentTarget.disabled && (e.currentTarget.style.background = 'var(--accent-base)')}
                      >
                        <ArrowRight size={20} />
                      </button>
                    </motion.div>
                  </div>
                </motion.div>
              )}

              {executionPhase !== 'idle' && (
                <motion.div
                  key="pipeline"
                  initial={{ opacity: 0, y: 40 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                  style={{ width: '100%', maxWidth: '900px', margin: '0 auto', padding: '4rem 2rem' }}
                >
                  {executionPhase === 'error' && (
                    <div style={{
                      background: 'var(--error-dim)', border: '1px solid var(--error-base)',
                      color: '#ff8080', padding: '1rem 1.5rem', borderRadius: '8px', marginBottom: '2rem',
                      display: 'flex', alignItems: 'center', gap: '0.75rem', fontFamily: 'var(--font-mono)', fontSize: '0.85rem'
                    }}>
                      <AlertCircle size={18} />
                      Pipeline Error: {pipelineExecutionError}
                    </div>
                  )}

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '4rem' }}>
                    {STAGES.map((s) => {
                      const st = stageExecutionStatus[s.id] || 'idle';
                      const isActive = st === 'running';
                      const isDone = st === 'done';
                      const Icon = s.icon;
                      
                      return (
                        <motion.div key={s.id} layout
                          style={{
                            background: 'var(--bg-surface)',
                            border: `1px solid ${isActive ? 'var(--accent-base)' : isDone ? 'var(--border-focus)' : 'var(--border-base)'}`,
                            borderRadius: '12px', padding: '1.25rem 1.5rem',
                            display: 'flex', alignItems: 'flex-start', gap: '1.5rem',
                            boxShadow: isActive ? '0 10px 30px var(--accent-dim)' : 'none',
                            transition: 'all 0.3s ease',
                            position: 'relative', overflow: 'hidden'
                          }}
                        >
                          {isActive && (
                            <motion.div
                              animate={{ x: ['-100%', '200%'] }}
                              transition={{ repeat: Infinity, duration: 1.8, ease: "linear" }}
                              style={{
                                position: 'absolute', top: 0, bottom: 0, left: 0, width: '50%',
                                background: 'linear-gradient(90deg, transparent, var(--accent-dim), transparent)',
                                zIndex: 0
                              }}
                            />
                          )}

                          <div style={{
                            width: '48px', height: '48px', borderRadius: '10px', flexShrink: 0,
                            background: isActive ? 'var(--accent-dim)' : isDone ? 'var(--success-dim)' : 'var(--bg-surface-elevated)',
                            border: `1px solid ${isActive ? 'rgba(223,160,32,0.3)' : isDone ? 'rgba(88,176,100,0.3)' : 'var(--border-base)'}`,
                            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1
                          }}>
                            {isActive ? (
                              <CircularProgress value={activeStageProgress[s.id] || 0} />
                            ) : isDone ? (
                              <Check size={20} color="var(--success-base)" />
                            ) : (
                              <Icon size={20} color="var(--text-tertiary)" />
                            )}
                          </div>

                          <div style={{ flex: 1, zIndex: 1 }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                              <h3 style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: '1.1rem', color: isActive || isDone ? 'var(--text-primary)' : 'var(--text-tertiary)' }}>
                                {s.label}
                              </h3>
                              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: isActive ? 'var(--accent-base)' : isDone ? 'var(--success-base)' : 'var(--text-tertiary)', letterSpacing: '0.1em' }}>
                                {st.toUpperCase()}
                              </span>
                            </div>
                            <p style={{ fontFamily: 'var(--font-sans)', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                              {s.desc}
                            </p>
                          </div>
                        </motion.div>
                      );
                    })}
                  </div>

                  {executionPhase === 'done' && pipelineStageOutputs.writer && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                      {pipelineMetadata.metrics && (
                        <div className="glass-panel" style={{
                          padding: '2rem', borderRadius: '16px',
                          background: 'var(--bg-surface)', border: '1px solid var(--border-focus)',
                          display: 'flex', flexDirection: 'column', gap: '1.5rem',
                          boxShadow: '0 20px 40px rgba(0,0,0,0.4)'
                        }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent-base)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem', letterSpacing: '0.1em' }}>
                            <Zap size={16} /> ENGINE EXECUTION METRICS
                          </div>
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem' }}>
                            <div style={{ background: 'rgba(255,255,255,0.01)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-base)' }}>
                              <div style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)', marginBottom: '0.5rem', letterSpacing: '0.05em' }}>SOURCE QUALITY</div>
                              <div style={{ fontSize: '1.4rem', fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                                {pipelineMetadata.metrics.overall_source_quality}/10
                              </div>
                            </div>
                            <div style={{ background: 'rgba(255,255,255,0.01)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-base)' }}>
                              <div style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)', marginBottom: '0.5rem', letterSpacing: '0.05em' }}>FACT-CHECK ACCURACY</div>
                              <div style={{ fontSize: '1.4rem', fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                                {pipelineMetadata.metrics.verification_confidence}%
                              </div>
                            </div>
                          </div>

                          {pipelineMetadata.metrics.source_breakdowns && pipelineMetadata.metrics.source_breakdowns.length > 0 && (
                            <div style={{ borderTop: '1px solid var(--border-base)', paddingTop: '1.5rem' }}>
                              <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)', marginBottom: '1rem', letterSpacing: '0.05em' }}>MULTI-FACTOR SOURCE TRUST BREAKDOWN</div>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                {pipelineMetadata.metrics.source_breakdowns.map((item, idx) => (
                                  <div key={idx} style={{ background: 'rgba(255,255,255,0.015)', padding: '0.75rem 1rem', borderRadius: '8px', border: '1px solid var(--border-base)', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                      <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>{item.domain}</span>
                                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--accent-base)', fontWeight: 600 }}>{item.score}/10</span>
                                    </div>
                                    {item.breakdown && (
                                      <div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginTop: '0.25rem' }}>
                                        <span>• Domain: {item.breakdown.domain_tier}</span>
                                        <span>• Recency: {item.breakdown.recency}</span>
                                        <span>• Corroboration: {item.breakdown.corroboration}</span>
                                        <span>• Citations: {item.breakdown.primary_citations}</span>
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          <div style={{ borderTop: '1px solid var(--border-base)', paddingTop: '1.5rem' }}>
                            <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)', marginBottom: '1rem', letterSpacing: '0.05em' }}>LATENCY PROFILE BY STAGE</div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                              {Object.entries(pipelineMetadata.metrics.latencies).map(([stageId, latency]) => {
                                const matchedStage = STAGES.find(s => s.id === stageId);
                                const stageName = matchedStage ? matchedStage.label : stageId;
                                const maxLatency = Math.max(...Object.values(pipelineMetadata.metrics.latencies), 1);
                                const widthPercent = (latency / maxLatency) * 100;
                                return (
                                  <div key={stageId} style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                    <div style={{ width: '160px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{stageName}</div>
                                    <div style={{ flex: 1, height: '6px', background: 'rgba(255,255,255,0.03)', borderRadius: '3px', overflow: 'hidden' }}>
                                      <div style={{ width: `${widthPercent}%`, height: '100%', background: 'var(--accent-base)', borderRadius: '3px' }} />
                                    </div>
                                    <div style={{ width: '50px', fontSize: '0.8rem', color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', textAlign: 'right' }}>{latency}s</div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        </div>
                      )}

                      <motion.div 
                        initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
                        style={{
                          background: 'var(--bg-surface)', border: '1px solid var(--border-focus)',
                          borderRadius: '16px', overflow: 'hidden', boxShadow: '0 20px 40px rgba(0,0,0,0.4)'
                        }}
                      >
                        <div style={{
                          padding: '1.5rem 2rem', borderBottom: '1px solid var(--border-base)',
                          background: 'linear-gradient(180deg, var(--bg-surface-elevated) 0%, var(--bg-surface) 100%)',
                          display: 'flex', alignItems: 'center', justifyContent: 'space-between'
                        }}>
                          <div style={{ display: 'flex', gap: '1rem' }}>
                            <button
                              onClick={() => setSelectedResultTab('report')}
                              style={{
                                background: selectedResultTab === 'report' ? 'var(--accent-dim)' : 'transparent',
                                border: `1px solid ${selectedResultTab === 'report' ? 'var(--accent-base)' : 'transparent'}`,
                                color: selectedResultTab === 'report' ? 'var(--accent-base)' : 'var(--text-tertiary)',
                                padding: '0.5rem 1rem', borderRadius: '8px', cursor: 'pointer',
                                fontSize: '0.85rem', fontWeight: 600, fontFamily: 'var(--font-mono)',
                                display: 'flex', alignItems: 'center', gap: '0.5rem', transition: 'all 0.2s'
                              }}
                            >
                              <FileText size={16} /> FINAL RESEARCH REPORT
                            </button>
                            {pipelineStageOutputs.critic_loop && (
                              <button
                                onClick={() => setSelectedResultTab('critic')}
                                style={{
                                  background: selectedResultTab === 'critic' ? 'var(--accent-dim)' : 'transparent',
                                  border: `1px solid ${selectedResultTab === 'critic' ? 'var(--accent-base)' : 'transparent'}`,
                                  color: selectedResultTab === 'critic' ? 'var(--accent-base)' : 'var(--text-tertiary)',
                                  padding: '0.5rem 1rem', borderRadius: '8px', cursor: 'pointer',
                                  fontSize: '0.85rem', fontWeight: 600, fontFamily: 'var(--font-mono)',
                                  display: 'flex', alignItems: 'center', gap: '0.5rem', transition: 'all 0.2s'
                                }}
                              >
                                <MessageSquareText size={16} /> CRITIC EVALUATION & USER SUGGESTIONS
                              </button>
                            )}
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            <button
                              onClick={handleCopyToClipboard}
                              style={{
                                display: 'flex', alignItems: 'center', gap: '0.35rem',
                                background: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--border-base)',
                                borderRadius: '6px', padding: '0.35rem 0.75rem', color: 'var(--text-secondary)',
                                cursor: 'pointer', fontFamily: 'var(--font-sans)', fontSize: '0.75rem', transition: 'all 0.2s'
                              }}
                              className="btn-action"
                            >
                              <Copy size={13} /> {hasCopiedToClipboard ? 'Copied' : 'Copy'}
                            </button>
                            <button
                              onClick={handleExportPdfReport}
                              style={{
                                display: 'flex', alignItems: 'center', gap: '0.35rem',
                                background: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--border-base)',
                                borderRadius: '6px', padding: '0.35rem 0.75rem', color: 'var(--text-secondary)',
                                cursor: 'pointer', fontFamily: 'var(--font-sans)', fontSize: '0.75rem', transition: 'all 0.2s'
                              }}
                              className="btn-action"
                            >
                              <Download size={13} /> PDF
                            </button>
                            {pipelineMetadata.confidence_score && (
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'var(--success-dim)', border: '1px solid var(--success-base)', padding: '0.25rem 0.75rem', borderRadius: '20px', color: 'var(--success-base)', fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                                <ShieldCheck size={14} /> CONFIDENCE: {Number(pipelineMetadata.confidence_score).toFixed(2)}/10
                              </div>
                            )}
                          </div>
                        </div>

                        {selectedResultTab === 'report' ? (
                          <div style={{ padding: '3rem 2.5rem' }}>
                            <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '2.5rem', fontWeight: 400, color: 'var(--text-primary)', lineHeight: 1.1, marginBottom: '2rem' }}>
                              {activePipelineTopicRef.current}
                            </h2>
                            <div className="prose">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {pipelineStageOutputs.writer}
                              </ReactMarkdown>
                            </div>
                          </div>
                        ) : (
                          <div style={{ padding: '3rem 2.5rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem', background: 'var(--accent-dim)', border: '1px solid var(--accent-base)', padding: '1rem 1.25rem', borderRadius: '12px', color: 'var(--accent-base)' }}>
                              <MessageSquareText size={20} />
                              <div>
                                <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 600 }}>Critic Agent Review & Recommendations</h4>
                                <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                  Actionable insights on strengths, quality score, and direct suggestions for independent report refinement.
                                </p>
                              </div>
                            </div>
                            <div className="prose">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {pipelineStageOutputs.critic_loop}
                              </ReactMarkdown>
                            </div>
                          </div>
                        )}
                      </motion.div>
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </main>

          <footer style={{
            padding: '2rem 2.5rem',
            borderTop: '1px solid var(--border-base)',
            background: 'var(--bg-surface)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontFamily: 'var(--font-sans)',
            fontSize: '0.85rem',
            color: 'var(--text-secondary)',
            zIndex: 10
          }}>
            <div>
              © 2026 <span style={{ color: 'var(--accent-base)', fontWeight: 500 }}>Siva</span>. All Rights Reserved.
            </div>
            <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center' }}>
              <span style={{ color: 'var(--text-tertiary)' }}>Advanced Research & Curation System</span>
            </div>
          </footer>
        </div>
      </div>
    </div>
  );
}
