/**
 * AskAIPortal — Unified Claude-powered AI Assistant
 * ====================================================
 * Consolidates AskAnythingDialog + CSM chatbot into one component.
 * Uses Ask AI v2 backend (Claude tool_use) with rich artifact rendering.
 * Falls back to v1 (GPT-4o) if v2 is not available.
 *
 * Behind feature flag: FEATURE_ASK_AI_V2
 * Usage: <AskAIPortal persona="cro" />
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  X, Send, Sparkles, Loader2,
  RotateCcw, User, Bot, Lightbulb,
  TrendingUp, DollarSign, Shield, Wrench,
  ChevronRight, Maximize2, Minimize2,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { apiCall, getCustomerIdentifier } from '../../utils/api';
import { useSession } from '../../contexts/SessionContext';
import { ArtifactRenderer, Artifact } from './ArtifactRenderer';

// ── Types ────────────────────────────────────────────────────────────────────

type Persona = 'cro' | 'cfo' | 'ceo' | 'vpcs' | 'sales';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  elapsed_ms?: number;
  artifacts?: Artifact[];
  tools_called?: string[];
  context_stats?: {
    accounts?: number;
    signals?: number;
    decisions?: number;
    outcomes?: number;
    stakeholders?: number;
    causal_edges?: number;
    total_arr?: number;
    tool_rounds?: number;
    tools_used?: number;
    unique_tools?: string[];
  };
  suggested_followups?: string[];
  version?: 'v1' | 'v2';
}

interface Props {
  persona: Persona;
  defaultOpen?: boolean;
}

// ── Constants ────────────────────────────────────────────────────────────────

const PERSONA_META: Record<Persona, {
  title: string;
  subtitle: string;
  icon: React.ComponentType<{ className?: string }>;
  gradient: string;
  accent: string;
}> = {
  cro: {
    title: 'Revenue Advisor',
    subtitle: 'Ask about pipeline, churn risk, expansion',
    icon: TrendingUp,
    gradient: 'from-cyan-500/20 to-blue-500/20',
    accent: 'text-cyan-400',
  },
  cfo: {
    title: 'Investment Advisor',
    subtitle: 'Ask about ROI, costs, payback periods',
    icon: DollarSign,
    gradient: 'from-emerald-500/20 to-teal-500/20',
    accent: 'text-emerald-400',
  },
  ceo: {
    title: 'Strategic Advisor',
    subtitle: 'Ask about portfolio health, board narrative',
    icon: Shield,
    gradient: 'from-violet-500/20 to-purple-500/20',
    accent: 'text-violet-400',
  },
  vpcs: {
    title: 'CS Team Advisor',
    subtitle: 'Ask about team performance, renewals, playbooks',
    icon: Shield,
    gradient: 'from-teal-500/20 to-cyan-500/20',
    accent: 'text-teal-400',
  },
  sales: {
    title: 'Expansion Advisor',
    subtitle: 'Ask about upsell, whitespace, QBR prep',
    icon: TrendingUp,
    gradient: 'from-amber-500/20 to-orange-500/20',
    accent: 'text-amber-400',
  },
};

const DEFAULT_SUGGESTIONS: Record<Persona, string[]> = {
  cro: [
    'Which accounts have the highest churn risk?',
    'Where is our biggest expansion opportunity?',
    'Show me the context graph for our most critical account.',
    'How are playbooks translating to revenue protection?',
  ],
  cfo: [
    'What is our CS investment returning per dollar?',
    'Which pillars have the worst ROI?',
    'What is the cost per account?',
    'Give me the board-ready CS investment summary.',
  ],
  ceo: [
    'Give me the 30-second board summary.',
    'What is our single biggest strategic risk?',
    'What would 1% improvement across all metrics be worth?',
    'How should I think about CS investment next year?',
  ],
  vpcs: [
    'What should my CSMs focus on today?',
    'Which accounts need immediate attention?',
    'Which playbooks are most effective this quarter?',
    'Show me renewals coming up in the next 90 days.',
  ],
  sales: [
    'Which accounts are ready for expansion?',
    'What is the product whitespace across my top 10 accounts?',
    'Prepare a QBR brief for my next renewal.',
    'What accounts have the highest upsell potential?',
  ],
};

// ── Component ────────────────────────────────────────────────────────────────

const AskAIPortal: React.FC<Props> = ({ persona, defaultOpen = false }) => {
  const { session } = useSession();
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [isWide, setIsWide] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState('');
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const meta = PERSONA_META[persona];
  const Icon = meta.icon;

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) setTimeout(() => inputRef.current?.focus(), 100);
  }, [isOpen]);

  // Load conversation from localStorage
  useEffect(() => {
    const key = `ask_ai_v2_${persona}_${session?.customer_id}`;
    const saved = localStorage.getItem(key);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setMessages(parsed.map((m: any) => ({ ...m, timestamp: new Date(m.timestamp) })));
      } catch { /* ignore corrupt data */ }
    }
  }, [persona, session?.customer_id]);

  // Save conversation
  useEffect(() => {
    if (messages.length > 0) {
      const key = `ask_ai_v2_${persona}_${session?.customer_id}`;
      localStorage.setItem(key, JSON.stringify(messages.slice(-20)));
    }
  }, [messages, persona, session?.customer_id]);

  // ── Send Message ──

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsg: Message = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: text.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);
    setLoadingStatus('Connecting to AI...');
    setError(null);

    try {
      // Build conversation history
      const history = messages
        .reduce<{ query: string; response: string }[]>((acc, m, i, arr) => {
          if (m.role === 'user' && arr[i + 1]?.role === 'assistant') {
            acc.push({ query: m.content, response: arr[i + 1].content });
          }
          return acc;
        }, [])
        .slice(-3);

      // Try v2 first, fall back to v1
      let assistantMsg: Message;

      try {
        assistantMsg = await callV2(text.trim(), persona, history, session);
      } catch (v2Err: any) {
        // If v2 returns fallback signal or is unavailable, try v1
        if (v2Err.fallback || v2Err.status === 503 || v2Err.status === 404) {
          setLoadingStatus('Falling back to standard AI...');
          assistantMsg = await callV1(text.trim(), persona, history, session);
        } else {
          throw v2Err;
        }
      }

      setMessages(prev => [...prev, assistantMsg]);
    } catch (err: any) {
      setError(err.message || 'Failed to get response');
    } finally {
      setLoading(false);
      setLoadingStatus('');
    }
  }, [loading, messages, persona, session]);

  const clearConversation = () => {
    setMessages([]);
    const key = `ask_ai_v2_${persona}_${session?.customer_id}`;
    localStorage.removeItem(key);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  // ── Render: Floating Button ──

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3
                   bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500
                   text-white rounded-full shadow-lg shadow-cyan-500/20
                   transition-all duration-200 hover:scale-105 group"
      >
        <Sparkles className="h-5 w-5 group-hover:animate-pulse" />
        <span className="text-sm font-medium">Ask AI</span>
      </button>
    );
  }

  // ── Render: Dialog ──

  const suggestions = messages.length === 0
    ? DEFAULT_SUGGESTIONS[persona]
    : (messages[messages.length - 1]?.suggested_followups || []);

  const panelWidth = isWide ? 'w-[680px]' : 'w-[520px]';

  return (
    <div className={`fixed bottom-6 right-6 z-50 ${panelWidth} flex flex-col
                    bg-[#0d1117] border border-gray-700/50 rounded-2xl shadow-2xl shadow-black/40
                    overflow-hidden transition-all duration-300`}
         style={{ maxHeight: 'calc(100vh - 100px)' }}>

      {/* ── Header ── */}
      <div className={`flex items-center justify-between px-4 py-3 bg-gradient-to-r ${meta.gradient} border-b border-gray-700/50`}>
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-[#1a1f2e] rounded-lg">
            <Icon className={`h-4 w-4 ${meta.accent}`} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">{meta.title}</h3>
            <p className="text-[10px] text-gray-400">{meta.subtitle} · v2</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setIsWide(!isWide)}
            className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
            title={isWide ? 'Narrow view' : 'Wide view'}
          >
            {isWide ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
          </button>
          {messages.length > 0 && (
            <button
              onClick={clearConversation}
              className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
              title="Clear conversation"
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </button>
          )}
          <button
            onClick={() => setIsOpen(false)}
            className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* ── Messages ── */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4 min-h-[200px] max-h-[500px]">

        {/* Welcome */}
        {messages.length === 0 && (
          <div className="text-center py-6">
            <div className="inline-flex p-3 bg-[#1a1f2e] rounded-xl mb-3">
              <Sparkles className={`h-6 w-6 ${meta.accent}`} />
            </div>
            <h4 className="text-sm font-medium text-white mb-1">
              Ask me anything about your portfolio
            </h4>
            <p className="text-xs text-gray-500 mb-1">
              I can fetch live data, render context graphs, show revenue intelligence,
              and recommend playbooks — all from your CS Pulse data.
            </p>
            <p className="text-[10px] text-gray-600">
              Powered by Claude · Context Graph · Revenue Intelligence
            </p>
          </div>
        )}

        {/* Message bubbles */}
        {messages.map(msg => (
          <div key={msg.id} className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="flex-shrink-0 mt-1">
                <div className="p-1 bg-[#1a1f2e] rounded-md">
                  <Bot className={`h-3.5 w-3.5 ${meta.accent}`} />
                </div>
              </div>
            )}
            <div className={`max-w-[90%] ${
              msg.role === 'user'
                ? 'bg-cyan-600/20 border border-cyan-500/30 text-cyan-50'
                : 'bg-[#1a1f2e] border border-gray-700/50 text-gray-200'
            } rounded-xl px-3 py-2`}>
              {/* Text content with markdown */}
              <div className="text-xs leading-relaxed prose prose-invert prose-xs max-w-none
                              prose-strong:text-white prose-strong:font-semibold
                              prose-p:mb-1 prose-p:mt-0
                              prose-ul:my-1 prose-li:my-0
                              prose-headings:text-white prose-headings:mb-1 prose-headings:mt-2">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {msg.content}
                </ReactMarkdown>
              </div>

              {/* Artifacts */}
              {msg.artifacts && msg.artifacts.length > 0 && (
                <div className="mt-2 space-y-2">
                  {msg.artifacts.map((artifact, i) => (
                    <ArtifactRenderer key={`${msg.id}-art-${i}`} artifact={artifact} />
                  ))}
                </div>
              )}

              {/* Context stats badge */}
              {msg.context_stats && (
                <div className="flex items-center gap-2 mt-2 pt-2 border-t border-gray-700/30">
                  <span className="text-[9px] text-gray-500">
                    {msg.version === 'v2' ? (
                      <>
                        {msg.context_stats.tools_used || 0} tools called
                        {msg.tools_called && msg.tools_called.length > 0 && (
                          <> · {msg.tools_called.map(t => t.replace('get_', '').replace(/_/g, ' ')).join(', ')}</>
                        )}
                      </>
                    ) : (
                      <>
                        {msg.context_stats.accounts || 0} accounts · {msg.context_stats.signals || 0} signals
                      </>
                    )}
                  </span>
                  {msg.elapsed_ms && (
                    <span className="text-[9px] text-gray-600">{(msg.elapsed_ms / 1000).toFixed(1)}s</span>
                  )}
                </div>
              )}
            </div>
            {msg.role === 'user' && (
              <div className="flex-shrink-0 mt-1">
                <div className="p-1 bg-cyan-600/20 rounded-md">
                  <User className="h-3.5 w-3.5 text-cyan-400" />
                </div>
              </div>
            )}
          </div>
        ))}

        {/* Loading indicator with status */}
        {loading && (
          <div className="flex gap-2">
            <div className="flex-shrink-0 mt-1">
              <div className="p-1 bg-[#1a1f2e] rounded-md">
                <Bot className={`h-3.5 w-3.5 ${meta.accent}`} />
              </div>
            </div>
            <div className="bg-[#1a1f2e] border border-gray-700/50 rounded-xl px-3 py-2">
              <div className="flex items-center gap-2">
                <Loader2 className="h-3 w-3 text-cyan-400 animate-spin" />
                <span className="text-xs text-gray-400">{loadingStatus || 'Analyzing portfolio data...'}</span>
              </div>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-900/20 border border-red-500/30 rounded-xl px-3 py-2">
            <p className="text-xs text-red-400">{error}</p>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* ── Suggestions ── */}
      {suggestions.length > 0 && !loading && (
        <div className="px-4 py-2 border-t border-gray-800/50">
          <div className="flex items-center gap-1 mb-1.5">
            <Lightbulb className="h-3 w-3 text-amber-400" />
            <span className="text-[10px] text-gray-500 uppercase tracking-wide">
              {messages.length === 0 ? 'Try asking' : 'Follow up'}
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {suggestions.map((q, i) => (
              <button
                key={i}
                onClick={() => sendMessage(q)}
                className="text-[10px] text-gray-400 hover:text-white bg-[#1a1f2e] hover:bg-[#252b3d]
                           border border-gray-700/30 hover:border-gray-600/50 rounded-lg px-2 py-1
                           transition-colors text-left"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Input ── */}
      <div className="px-3 py-3 border-t border-gray-700/50 bg-[#0a0e14]">
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Ask your ${meta.title.toLowerCase()}...`}
            disabled={loading}
            className="flex-1 bg-[#1a1f2e] border border-gray-700/50 rounded-lg px-3 py-2 text-xs text-white
                       placeholder-gray-500 outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20
                       disabled:opacity-50"
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || loading}
            className="p-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-gray-700 disabled:text-gray-500
                       text-white rounded-lg transition-colors"
          >
            <Send className="h-3.5 w-3.5" />
          </button>
        </div>
        <p className="text-[9px] text-gray-600 mt-1.5 text-center">
          Powered by Claude · {messages.filter(m => m.role === 'assistant').length} responses this session
        </p>
      </div>
    </div>
  );
};

// ── API Calls ────────────────────────────────────────────────────────────────

async function callV2(
  query: string,
  persona: string,
  history: { query: string; response: string }[],
  session: any,
): Promise<Message> {
  const res = await apiCall('/api/executive/ask-v2', {
    method: 'POST',
    headers: { 'X-Customer-ID': getCustomerIdentifier(session) },
    body: JSON.stringify({ query, persona, conversation_history: history }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Request failed' }));
    const error: any = new Error(err.error || err.message || `HTTP ${res.status}`);
    error.fallback = err.fallback;
    error.status = res.status;
    throw error;
  }

  const data = await res.json();

  return {
    id: `a-${Date.now()}`,
    role: 'assistant',
    content: data.response,
    timestamp: new Date(),
    elapsed_ms: data.elapsed_ms,
    artifacts: data.artifacts || [],
    tools_called: data.tools_called || [],
    context_stats: data.context_stats,
    suggested_followups: data.suggested_followups,
    version: 'v2',
  };
}

async function callV1(
  query: string,
  persona: string,
  history: { query: string; response: string }[],
  session: any,
): Promise<Message> {
  const res = await apiCall('/api/executive/ask', {
    method: 'POST',
    headers: { 'X-Customer-ID': getCustomerIdentifier(session) },
    body: JSON.stringify({
      query,
      persona,
      conversation_history: history.map(h => ({
        ...h,
        customer_id: session?.customer_id || 0,
      })),
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Request failed' }));
    throw new Error(err.error || err.message || `HTTP ${res.status}`);
  }

  const data = await res.json();

  return {
    id: `a-${Date.now()}`,
    role: 'assistant',
    content: data.response,
    timestamp: new Date(),
    elapsed_ms: data.elapsed_ms,
    context_stats: data.context_stats,
    suggested_followups: data.suggested_followups,
    version: 'v1',
  };
}

export default AskAIPortal;
