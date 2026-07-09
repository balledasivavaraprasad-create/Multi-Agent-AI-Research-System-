// Copyright (c) 2026 Siva. All rights reserved.
// This software and associated documentation files are the proprietary property of Siva.
// Unauthorized copying, distribution, or modification is strictly prohibited.

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowRight, Search, Check, AlertCircle, FileText,
  RotateCcw, Eye, ShieldCheck, Zap, Split, PenLine, Award, Sparkles
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './index.css';

const STAGES = [
  { id: 'planner', num: '01', label: 'Planning', desc: 'Structuring research into focused questions', icon: Split },
  { id: 'research', num: '02', label: 'Research', desc: 'Gathering top-ranked sources comprehensively', icon: Search },
  { id: 'factcheck', num: '03', label: 'Verification', desc: 'Validating claims, statistics, and sources', icon: ShieldCheck },
  { id: 'analysis', num: '04', label: 'Analysis', desc: 'Extracting insights with source mapping', icon: Zap },
  { id: 'contrarian', num: '05', label: 'Perspective', desc: 'Challenging assumptions and finding gaps', icon: Eye },
  { id: 'writer', num: '06', label: 'Writing', desc: 'Composing report with citations', icon: PenLine },
  { id: 'critic_loop', num: '07', label: 'Quality Loop', desc: 'Iterative refinement and review', icon: AlertCircle },
  { id: 'confidence', num: '08', label: 'Confidence', desc: 'Generate references and quality score', icon: Award }
];

export default function App() {
  const [topic, setTopic] = useState('');
  const [phase, setPhase] = useState('idle'); 
  const [status, setStatus] = useState({});
  const [results, setResults] = useState({});
  const [metadata, setMetadata] = useState({});
  const [errorMsg, setErrorMsg] = useState('');
  
  const inputRef = useRef(null);
  const runTopic = useRef('');

  const runPipeline = async () => {
    if (!topic.trim() || phase === 'running') return;
    
    runTopic.current = topic.trim();
    setPhase('running');
    setStatus({});
    setResults({});
    setMetadata({});
    setErrorMsg('');

    
    const initialStatus = {};
    STAGES.forEach(s => { initialStatus[s.id] = 'idle'; });
    setStatus(initialStatus);

    const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:7860";
    
    try {
      const response = await fetch(`${API_BASE}/api/research-stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
              } else if (event.type === "complete") {
                setResults(event.results);
                setMetadata(event.metadata);
                setPhase('done');
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

  const reset = () => {
    setPhase('idle');
    setTopic('');
    setResults({});
    setStatus({});
    setTimeout(() => inputRef.current?.focus(), 100);
  };

  return (
    <div className="min-h-screen flex flex-col relative" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header className="glass-panel" style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '1.25rem 2.5rem', position: 'sticky', top: 0, zIndex: 100,
        borderBottom: '1px solid var(--border-base)', borderTop: 'none', borderLeft: 'none', borderRight: 'none'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <img src="/logo.png" alt="Logo" style={{ height: '32px', width: 'auto', objectFit: 'contain', display: 'block', transform: 'translateY(-1px)' }} />
          <span style={{ fontFamily: 'var(--font-serif)', fontSize: '1.5rem', fontWeight: 600, letterSpacing: '0.05em', lineHeight: 1 }}>
            ARC<span style={{ color: 'var(--accent-base)' }}>S</span>
          </span>
        </div>
        
        <AnimatePresence>
          {phase !== 'idle' && (
            <motion.div 
              initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              style={{ flex: 1, display: 'flex', justifyContent: 'center' }}
            >
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-tertiary)',
                maxWidth: '400px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'
              }}>
                <span style={{ color: 'var(--accent-base)', marginRight: '8px', letterSpacing: '0.1em' }}>TOPIC:</span>
                {runTopic.current}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {phase !== 'idle' && (
            <button onClick={reset} style={{
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
                        {isDone ? <Check size={20} color="var(--success-base)" /> : <Icon size={20} color={isActive ? "var(--accent-base)" : "var(--text-tertiary)"} />}
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
                      {metadata.confidence_score && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'var(--success-dim)', border: '1px solid var(--success-base)', padding: '0.25rem 0.75rem', borderRadius: '20px', color: 'var(--success-base)', fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                          <ShieldCheck size={14} /> CONFIDENCE: {metadata.confidence_score}/10
                        </div>
                      )}
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
          <span style={{ width: '4px', height: '4px', borderRadius: '50%', background: 'var(--border-base)' }} />
          <span>v2.0.0</span>
        </div>
      </footer>
    </div>
  );
}
