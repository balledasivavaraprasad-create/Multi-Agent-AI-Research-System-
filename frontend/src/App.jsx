// Copyright (c) 2026 Siva. All rights reserved.
// This software and associated documentation files are the proprietary property of Siva.
// Unauthorized copying, distribution, or modification is strictly prohibited.

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowRight, Search, Check, AlertCircle, FileText,
  RotateCcw, Eye, ShieldCheck, Zap, Split, PenLine, Award, Sparkles,
  Copy, Download, LogOut
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
  const [topic, setTopic] = useState('');
  const [phase, setPhase] = useState('idle'); 
  const [status, setStatus] = useState({});
  const [results, setResults] = useState({});
  const [metadata, setMetadata] = useState({});
  const [errorMsg, setErrorMsg] = useState('');
  const [stagePercentages, setStagePercentages] = useState({});
  const [copied, setCopied] = useState(false);
  
  // MongoDB Auth & History State
  const [token, setToken] = useState(localStorage.getItem('arcs_token') || '');
  const [userEmail, setUserEmail] = useState(localStorage.getItem('arcs_email') || '');
  const [history, setHistory] = useState([]);
  const [authMode, setAuthMode] = useState('login'); // 'login' or 'register'
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [authLoading, setAuthLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [activeHistoryId, setActiveHistoryId] = useState(null);

  const inputRef = useRef(null);
  const runTopic = useRef('');

  const API_BASE = import.meta.env.VITE_API_BASE || import.meta.env.VITE_API_URL || (
    window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" 
      ? "http://localhost:7860" 
      : "https://arcs-backend-siva.onrender.com"
  );


  const fetchHistory = async (activeToken) => {
    if (!activeToken) return;
    setHistoryLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/history`, {
        headers: { 'Authorization': `Bearer ${activeToken}` }
      });
      const data = await response.json();
      if (response.ok) {
        setHistory(data.history || []);
      } else {
        if (response.status === 401) {
          handleLogout();
        }
      }
    } catch (err) {
      console.error("Error fetching history:", err);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchHistory(token);
    } else {
      setHistory([]);
    }
  }, [token]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError('');
    try {
      const response = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: authEmail, password: authPassword })
      });
      const data = await response.json();
      if (response.ok) {
        localStorage.setItem('arcs_token', data.token);
        localStorage.setItem('arcs_email', data.email);
        setToken(data.token);
        setUserEmail(data.email);
        setAuthPassword('');
        setAuthEmail('');
      } else {
        setAuthError(data.error || 'Login failed');
      }
    } catch (err) {
      setAuthError('Connection failed. Please check backend.');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError('');
    try {
      const response = await fetch(`${API_BASE}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: authEmail, password: authPassword })
      });
      const data = await response.json();
      if (response.ok) {
        setAuthMode('login');
        const loginResp = await fetch(`${API_BASE}/api/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: authEmail, password: authPassword })
        });
        const loginData = await loginResp.json();
        if (loginResp.ok) {
          localStorage.setItem('arcs_token', loginData.token);
          localStorage.setItem('arcs_email', loginData.email);
          setToken(loginData.token);
          setUserEmail(loginData.email);
          setAuthPassword('');
          setAuthEmail('');
        } else {
          setAuthError('Registered successfully, but login failed.');
        }
      } else {
        setAuthError(data.error || 'Registration failed');
      }
    } catch (err) {
      setAuthError('Connection failed. Please check backend.');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('arcs_token');
    localStorage.removeItem('arcs_email');
    setToken('');
    setUserEmail('');
    setHistory([]);
    setTopic('');
    setPhase('idle');
    setStatus({});
    setResults({});
    setMetadata({});
    setStagePercentages({});
    setActiveHistoryId(null);
  };

  const handleLoadHistoryItem = async (itemId) => {
    if (phase === 'running') return;
    setActiveHistoryId(itemId);
    setPhase('loading_history');
    try {
      const response = await fetch(`${API_BASE}/api/history/${itemId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      if (response.ok) {
        setTopic(data.topic);
        runTopic.current = data.topic;
        setResults(data.results || {});
        setMetadata(data.metadata || {});
        
        const completedStages = {};
        const percentages = {};
        STAGES.forEach(s => {
          completedStages[s.id] = 'done';
          percentages[s.id] = 100;
        });
        setStatus(completedStages);
        setStagePercentages(percentages);
        setPhase('done');
      } else {
        setErrorMsg(data.error || 'Failed to load report from history');
        setPhase('error');
      }
    } catch (err) {
      setErrorMsg('Failed to connect to backend.');
      setPhase('error');
    }
  };

  const handleNewQuery = () => {
    if (phase === 'running') return;
    setTopic('');
    setPhase('idle');
    setStatus({});
    setResults({});
    setMetadata({});
    setStagePercentages({});
    setActiveHistoryId(null);
    if (inputRef.current) {
      inputRef.current.value = '';
      inputRef.current.focus();
    }
  };

  const EXPECTED_DURATIONS = {
    planner: 8,
    research: 10,
    claim_extraction: 10,
    fact_verification: 20,
    analysis: 21,
    writer: 12,
    critic_loop: 60,
    grounded_citations: 14
  };

  useEffect(() => {
    const activeStage = Object.entries(status).find(([id, val]) => val === 'running')?.[0];
    if (!activeStage) return;

    setStagePercentages(prev => ({
      ...prev,
      [activeStage]: prev[activeStage] || 0
    }));

    const expected = EXPECTED_DURATIONS[activeStage] || 15;
    const intervalTime = 100;
    const increment = (100 / expected) * (intervalTime / 1000);

    const timer = setInterval(() => {
      setStagePercentages(prev => {
        const current = prev[activeStage] || 0;
        if (current >= 99) return prev;
        return {
          ...prev,
          [activeStage]: current + increment
        };
      });
    }, intervalTime);

    return () => clearInterval(timer);
  }, [status]);

  const handleCopy = () => {
    navigator.clipboard.writeText(results.writer || '');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadPdf = () => {
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
      <html>
        <head>
          <title>ARCS Research Report - ${runTopic.current}</title>
          <style>
            body {
              font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
              color: #333;
              line-height: 1.6;
              padding: 2.5rem;
              max-width: 800px;
              margin: 0 auto;
            }
            h1 { font-size: 2.2rem; color: #111; margin-bottom: 0.5rem; }
            h2 { font-size: 1.6rem; color: #222; margin-top: 1.5rem; }
            h3 { font-size: 1.25rem; color: #333; margin-top: 1.25rem; }
            p { margin-bottom: 1rem; font-size: 1rem; }
            ul, ol { margin-bottom: 1rem; padding-left: 1.5rem; }
            li { margin-bottom: 0.5rem; }
            blockquote { border-left: 4px solid #dfa020; padding-left: 1rem; margin: 1rem 0; font-style: italic; color: #555; }
            hr { border: 0; border-top: 1px solid #ddd; margin: 2rem 0; }
            .citations { margin-top: 2rem; font-family: monospace; font-size: 0.85rem; color: #666; whiteSpace: pre-wrap; }
          </style>
        </head>
        <body>
          <h1>${runTopic.current}</h1>
          <div style="font-size: 0.85rem; color: #666; margin-bottom: 2rem;">Research Report Generated by ARCS on ${new Date().toLocaleDateString()}</div>
          <div class="content">
            ${document.querySelector('.prose').innerHTML}
          </div>
          ${results.citations ? `<hr /><div class="citations"><h3>References & Citations</h3><pre style="white-space: pre-wrap;">${results.citations}</pre></div>` : ''}
          <script>
            window.onload = function() {
              window.print();
              window.close();
            };
          </script>
        </body>
      </html>
    `);
    printWindow.document.close();
  };

  const runPipeline = async () => {
    if (!topic.trim() || phase === 'running') return;
    
    runTopic.current = topic.trim();
    setPhase('running');
    setStatus({});
    setResults({});
    setMetadata({});
    setErrorMsg('');
    setStagePercentages({});

    
    const initialStatus = {};
    STAGES.forEach(s => { initialStatus[s.id] = 'idle'; });
    setStatus(initialStatus);

    const headers = { "Content-Type": "application/json" };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    
    try {
      const response = await fetch(`${API_BASE}/api/research-stream`, {
        method: "POST",
        headers: headers,
        body: JSON.stringify({ topic: runTopic.current }),
      });

      if (!response.ok) throw new Error(`Server error: ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const event = JSON.parse(line.slice(6));
              if (event.type === "stage_started") {
                setStatus(p => ({ ...p, [event.stage]: 'running' }));
              } else if (event.type === "stage_completed") {
                setStatus(p => ({ ...p, [event.stage]: 'done' }));
                setResults(p => ({ ...p, [event.stage]: event.result }));
                setStagePercentages(p => ({ ...p, [event.stage]: 100 }));
              } else if (event.type === "complete") {
                setResults(event.results);
                setMetadata(event.metadata);
                setPhase('done');
                fetchHistory(token);
              } else if (event.type === "error") {
                setErrorMsg(event.error);
                setPhase('error');
                return;
              }
            } catch (e) {
              console.error("Parse error:", e);
            }
          }
        }
      }
    } catch (err) {
      setErrorMsg(err.message);
      setPhase('error');
    }
  };

  if (!token) {
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
        <div style={{
          background: 'rgba(255, 255, 255, 0.02)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255, 255, 255, 0.05)',
          borderRadius: '16px',
          padding: '2.5rem',
          width: '100%',
          maxWidth: '400px',
          boxShadow: '0 20px 40px rgba(0, 0, 0, 0.5)'
        }}>
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

          <form onSubmit={authMode === 'login' ? handleLogin : handleRegister}>
            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ display: 'block', fontSize: '0.75rem', color: '#aaa', marginBottom: '0.5rem', fontWeight: 600 }}>EMAIL ADDRESS</label>
              <input
                type="email"
                required
                value={authEmail}
                onChange={(e) => setAuthEmail(e.target.value)}
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
                value={authPassword}
                onChange={(e) => setAuthPassword(e.target.value)}
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

            {authError && (
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
                {authError}
              </div>
            )}

            <button
              type="submit"
              disabled={authLoading}
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
                opacity: authLoading ? 0.7 : 1
              }}
            >
              {authLoading ? 'Please wait...' : authMode === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>

          <div style={{ textAlign: 'center', marginTop: '1.5rem' }}>
            <span style={{ fontSize: '0.8rem', color: '#666' }}>
              {authMode === 'login' ? "Don't have an account? " : "Already have an account? "}
            </span>
            <button
              onClick={() => {
                setAuthMode(authMode === 'login' ? 'register' : 'login');
                setAuthError('');
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
              {authMode === 'login' ? 'Register' : 'Sign In'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-base)', color: 'var(--text-primary)', overflow: 'hidden' }}>
      {/* LEFT SIDEBAR */}
      <aside className="glass-panel" style={{
        width: '320px',
        borderRight: '1px solid var(--border-base)',
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0,
        background: 'var(--bg-surface)'
      }}>
        {/* Sidebar Header: Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '1.5rem', borderBottom: '1px solid var(--border-base)' }}>
          <img src="/logo.png" alt="Logo" style={{ height: '28px', width: 'auto', objectFit: 'contain' }} />
          <span style={{ fontFamily: 'var(--font-serif)', fontSize: '1.4rem', fontWeight: 600, letterSpacing: '0.05em' }}>
            ARC<span style={{ color: 'var(--accent-base)' }}>S</span>
          </span>
        </div>

        {/* User Card */}
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
              fontWeight: 600,
              fontSize: '0.85rem',
              color: 'var(--accent-base)'
            }}>
              {userEmail ? userEmail.charAt(0).toUpperCase() : 'U'}
            </div>
            <div style={{ overflow: 'hidden', flex: 1 }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {userEmail ? userEmail.split('@')[0] : 'User'}
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {userEmail}
              </div>
            </div>
            <button
              onClick={handleLogout}
              title="Log Out"
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-tertiary)',
                cursor: 'pointer',
                padding: '4px',
                borderRadius: '4px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.2s'
              }}
              onMouseOver={e => e.currentTarget.style.color = '#ef4444'}
              onMouseOut={e => e.currentTarget.style.color = 'var(--text-tertiary)'}
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>

        {/* New Query Button */}
        <div style={{ padding: '0 1rem 1rem' }}>
          <button
            onClick={handleNewQuery}
            disabled={phase === 'running'}
            style={{
              width: '100%',
              background: 'var(--accent-base)',
              color: '#000',
              border: 'none',
              borderRadius: '8px',
              padding: '0.65rem',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: phase === 'running' ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              opacity: phase === 'running' ? 0.5 : 1,
              transition: 'all 0.2s'
            }}
          >
            + New Query
          </button>
        </div>

        {/* Recent Research History Title */}
        <div style={{
          fontSize: '0.7rem',
          fontWeight: 700,
          color: 'var(--text-tertiary)',
          letterSpacing: '0.08em',
          padding: '0.5rem 1rem',
          borderTop: '1px solid var(--border-base)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.02)'
        }}>
          RECENT RESEARCH
        </div>

        {/* Recent Research History list */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '0.5rem' }}>
          {historyLoading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '2rem', color: 'var(--text-tertiary)', fontSize: '0.8rem' }}>
              Loading history...
            </div>
          ) : history.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-tertiary)', fontSize: '0.8rem' }}>
              No recent searches
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              {history.map(item => {
                const isActive = activeHistoryId === item.id;
                const dateObj = new Date(item.timestamp);
                const timeStr = dateObj.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
                return (
                  <button
                    key={item.id}
                    onClick={() => handleLoadHistoryItem(item.id)}
                    disabled={phase === 'running'}
                    style={{
                      width: '100%',
                      background: isActive ? 'rgba(255, 255, 255, 0.03)' : 'transparent',
                      border: 'none',
                      borderRadius: '8px',
                      padding: '0.65rem 0.85rem',
                      textAlign: 'left',
                      cursor: phase === 'running' ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.15rem',
                      borderLeft: isActive ? '3px solid var(--accent-base)' : '3px solid transparent',
                      transition: 'all 0.2s',
                      boxSizing: 'border-box'
                    }}
                    onMouseOver={e => { if (!isActive && phase !== 'running') e.currentTarget.style.background = 'rgba(255, 255, 255, 0.015)'; }}
                    onMouseOut={e => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}
                  >
                    <div style={{
                      fontSize: '0.8rem',
                      fontWeight: isActive ? 600 : 500,
                      color: isActive ? 'var(--accent-base)' : 'var(--text-primary)',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      width: '100%'
                    }}>
                      {item.topic}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', fontSize: '0.65rem', color: 'var(--text-tertiary)' }}>
                      <span>Score: {item.metadata?.quality_score || 'N/A'}</span>
                      <span>{timeStr}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </aside>

      {/* RIGHT CONTENT CONTAINER */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* HEADER */}
        <header className="glass-panel" style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '1.25rem 2.5rem', borderBottom: '1px solid var(--border-base)',
          borderTop: 'none', borderLeft: 'none', borderRight: 'none', background: 'var(--bg-surface)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <img src="/logo.png" alt="ARCS Logo" style={{ height: '24px', width: 'auto' }} />
            <span style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '0.05em' }}>
              Advanced Research & Curation System
            </span>
            {phase !== 'idle' && (
              <span style={{ color: 'var(--text-tertiary)', fontSize: '0.8rem', marginLeft: '1rem', borderLeft: '1px solid var(--border-base)', paddingLeft: '1rem' }}>
                <span style={{ color: 'var(--accent-base)', marginRight: '6px', fontWeight: 500 }}>TOPIC:</span>
                {runTopic.current}
              </span>
            )}
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            {phase !== 'idle' && phase !== 'running' && (
              <button onClick={handleNewQuery} style={{
                display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'transparent',
                border: '1px solid var(--border-base)', color: 'var(--text-secondary)',
                fontFamily: 'var(--font-sans)', fontSize: '0.8rem', fontWeight: 500,
                padding: '0.5rem 1rem', borderRadius: '6px', cursor: 'pointer',
                transition: 'all 0.2s'
              }} onMouseOver={e => e.currentTarget.style.borderColor = 'var(--text-muted)'}
                 onMouseOut={e => e.currentTarget.style.borderColor = 'var(--border-base)'}>
                <RotateCcw size={14} /> New Query
              </button>
            )}
          </div>
        </header>

        {/* MAIN CONTAINER (SCROLLABLE) */}
        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
          <main style={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative' }}>
            <AnimatePresence mode="wait">
              {phase === 'idle' && (
            <motion.div
              key="hero"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, scale: 0.95, filter: 'blur(10px)' }}
              transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '4rem 2rem' }}
            >
              <div style={{
                position: 'absolute', top: '20%', width: '600px', height: '600px',
                background: 'radial-gradient(circle, var(--accent-glow) 0%, transparent 60%)',
                pointerEvents: 'none', zIndex: 0, opacity: 0.6
              }} />

              <div style={{ position: 'relative', zIndex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%', maxWidth: '800px' }}>
                <motion.div 
                  initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.1 }}
                  style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2rem' }}
                >
                  <Sparkles size={16} color="var(--accent-base)" />
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--accent-base)', letterSpacing: '0.2em', textTransform: 'uppercase' }}>
                    Multi-Agent Autonomous Research
                  </span>
                </motion.div>

                <motion.h1 
                  initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.2 }}
                  style={{
                    fontFamily: 'var(--font-serif)', fontSize: 'clamp(3rem, 6vw, 5rem)', fontWeight: 300,
                    lineHeight: 1.1, textAlign: 'center', marginBottom: '3rem', letterSpacing: '-0.02em'
                  }}
                >
                  Synthesize the world's <br/>
                  <em style={{ color: 'var(--accent-base)', fontStyle: 'italic' }}>deepest knowledge.</em>
                </motion.h1>

                <motion.div 
                  initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.3 }}
                  style={{ width: '100%', position: 'relative' }}
                >
                  <input
                    ref={inputRef}
                    value={topic}
                    onChange={e => setTopic(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && runPipeline()}
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
                    onClick={runPipeline}
                    disabled={!topic.trim()}
                    style={{
                      position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)',
                      background: 'var(--accent-base)', border: 'none', borderRadius: '8px',
                      color: 'var(--bg-base)', padding: '0.75rem', cursor: topic.trim() ? 'pointer' : 'not-allowed',
                      opacity: topic.trim() ? 1 : 0.5, transition: 'all 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center'
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

          {phase !== 'idle' && (
            <motion.div
              key="pipeline"
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
              style={{ width: '100%', maxWidth: '900px', margin: '0 auto', padding: '4rem 2rem' }}
            >
              {phase === 'error' && (
                <div style={{
                  background: 'var(--error-dim)', border: '1px solid var(--error-base)',
                  color: '#ff8080', padding: '1rem 1.5rem', borderRadius: '8px', marginBottom: '2rem',
                  display: 'flex', alignItems: 'center', gap: '0.75rem', fontFamily: 'var(--font-mono)', fontSize: '0.85rem'
                }}>
                  <AlertCircle size={18} />
                  Pipeline Error: {errorMsg}
                </div>
              )}

              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '4rem' }}>
                {STAGES.map((s, i) => {
                  const st = status[s.id] || 'idle';
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
                          transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
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
                          <CircularProgress value={stagePercentages[s.id] || 0} />
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

              {phase === 'done' && results.writer && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                  {metadata.metrics && (
                    <div className="glass-panel" style={{
                      padding: '2rem', borderRadius: '16px',
                      background: 'var(--bg-surface)', border: '1px solid var(--border-focus)',
                      display: 'flex', flexDirection: 'column', gap: '1.5rem',
                      boxShadow: '0 20px 40px rgba(0,0,0,0.4)'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent-base)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem', letterSpacing: '0.1em' }}>
                        <Zap size={16} /> ENGINE EXECUTION METRICS
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1.5rem' }}>
                        <div style={{ background: 'rgba(255,255,255,0.01)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-base)' }}>
                          <div style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)', marginBottom: '0.5rem', letterSpacing: '0.05em' }}>SOURCE QUALITY</div>
                          <div style={{ fontSize: '1.4rem', fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                            {metadata.metrics.overall_source_quality}/10
                          </div>
                        </div>
                        <div style={{ background: 'rgba(255,255,255,0.01)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-base)' }}>
                          <div style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)', marginBottom: '0.5rem', letterSpacing: '0.05em' }}>FACT-CHECK ACCURACY</div>
                          <div style={{ fontSize: '1.4rem', fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                            {metadata.metrics.verification_confidence}%
                          </div>
                        </div>
                        <div style={{ background: 'rgba(255,255,255,0.01)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-base)' }}>
                          <div style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)', marginBottom: '0.5rem', letterSpacing: '0.05em' }}>ESTIMATED RUN COST</div>
                          <div style={{ fontSize: '1.4rem', fontWeight: 600, color: 'var(--accent-base)', fontFamily: 'var(--font-mono)' }}>
                            ${Number(metadata.metrics.cost_usd || 0.00).toFixed(4)}
                          </div>
                        </div>
                      </div>

                      {metadata.metrics.source_breakdowns && metadata.metrics.source_breakdowns.length > 0 && (
                        <div style={{ borderTop: '1px solid var(--border-base)', paddingTop: '1.5rem' }}>
                          <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)', marginBottom: '1rem', letterSpacing: '0.05em' }}>MULTI-FACTOR SOURCE TRUST BREAKDOWN</div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                            {metadata.metrics.source_breakdowns.map((item, idx) => (
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
                          {Object.entries(metadata.metrics.latencies).map(([stageId, latency]) => {
                            const matchedStage = STAGES.find(s => s.id === stageId);
                            const stageName = matchedStage ? matchedStage.label : stageId;
                            const maxLatency = Math.max(...Object.values(metadata.metrics.latencies), 1);
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
                    initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
                    style={{
                      background: 'var(--bg-surface)', border: '1px solid var(--border-focus)',
                      borderRadius: '16px', overflow: 'hidden', boxShadow: '0 20px 40px rgba(0,0,0,0.4)'
                    }}
                  >
                    <div style={{
                      padding: '2rem', borderBottom: '1px solid var(--border-base)',
                      background: 'linear-gradient(180deg, var(--bg-surface-elevated) 0%, var(--bg-surface) 100%)'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent-base)', fontFamily: 'var(--font-mono)', fontSize: '0.8rem', letterSpacing: '0.1em' }}>
                          <FileText size={16} /> FINAL RESEARCH REPORT
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                          <button
                            onClick={handleCopy}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.35rem',
                              background: 'rgba(255, 255, 255, 0.03)',
                              border: '1px solid var(--border-base)',
                              borderRadius: '6px',
                              padding: '0.35rem 0.75rem',
                              color: 'var(--text-secondary)',
                              cursor: 'pointer',
                              fontFamily: 'var(--font-sans)',
                              fontSize: '0.75rem',
                              transition: 'all 0.2s'
                            }}
                            className="btn-action"
                          >
                            <Copy size={13} /> {copied ? 'Copied' : 'Copy'}
                          </button>
                          <button
                            onClick={handleDownloadPdf}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.35rem',
                              background: 'rgba(255, 255, 255, 0.03)',
                              border: '1px solid var(--border-base)',
                              borderRadius: '6px',
                              padding: '0.35rem 0.75rem',
                              color: 'var(--text-secondary)',
                              cursor: 'pointer',
                              fontFamily: 'var(--font-sans)',
                              fontSize: '0.75rem',
                              transition: 'all 0.2s'
                            }}
                            className="btn-action"
                          >
                            <Download size={13} /> PDF
                          </button>
                          {metadata.confidence_score && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'var(--success-dim)', border: '1px solid var(--success-base)', padding: '0.25rem 0.75rem', borderRadius: '20px', color: 'var(--success-base)', fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                              <ShieldCheck size={14} /> CONFIDENCE: {Number(metadata.confidence_score).toFixed(2)}/10
                            </div>
                          )}
                        </div>
                      </div>
                      <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '2.5rem', fontWeight: 400, color: 'var(--text-primary)', lineHeight: 1.1 }}>
                        {runTopic.current}
                      </h2>
                    </div>

                    <div style={{ padding: '3rem 2.5rem' }}>
                      <div className="prose">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {results.writer}
                        </ReactMarkdown>
                      </div>
                    </div>

                    {results.citations && (
                      <div style={{ padding: '2rem 2.5rem', background: 'var(--bg-base)', borderTop: '1px solid var(--border-base)' }}>
                        <h4 style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '1rem', letterSpacing: '0.1em' }}>REFERENCES & CITATIONS</h4>
                        <pre style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', wordBreak: 'break-word', opacity: 0.8 }}>
                          {results.citations}
                        </pre>
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
