/**
 * AskAnythingDialog — Executive AI Advisor
 * ==========================================
 * Floating dialog for CRO/CFO/CEO to ask natural language questions.
 * Backed by RAG + context graph + Power of 1 data.
 *
 * Usage: <AskAnythingDialog persona="cro" />
 * Personas: cro | cfo | ceo — only changes system prompt + suggested Qs
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  MessageCircle, X, Send, Sparkles, Loader2,
  ChevronRight, RotateCcw, User, Bot, Lightbulb,
  TrendingUp, DollarSign, Shield, Zap,
} from 'lucide-react';
import { apiCall, getCustomerIdentifier } from '../../utils/api';
import { useSession } from '../../contexts/SessionContext';

// ── Types ────────────────────────────────────────────────────────────────────

type Persona = 'cro' | 'cfo' | 'ceo';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  elapsed_ms?: number;
  context_stats?: {
    accounts: number;
    signals: number;
    decisions: number;
    outcomes: number;
    stakeholders: number;
    causal_edges: number;
    total_arr: number;
  };
  suggested_followups?: string[];
}

interface Props {
  persona: Persona;
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
};

const DEFAULT_SUGGESTIONS: Record<Persona, string[]> = {
  cro: [
    'Which accounts have the highest churn risk?',
    'Where is our biggest expansion opportunity?',
    'What story arcs should I worry about?',
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
};

// ── Component ────────────────────────────────────────────────────────────────

const AskAnythingDialog: React.FC<Props> = ({ persona }) => {
  const { session } = useSession();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const meta = PERSONA_META[persona];
  const Icon = meta.icon;

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  // Load conversation from localStorage
  useEffect(() => {
    const key = `exec_ask_${persona}_${session?.customer_id}`;
    const saved = localStorage.getItem(key);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setMessages(parsed.map((m: any) => ({ ...m, timestamp: new Date(m.timestamp) })));
      } catch { /* ignore */ }
    }
  }, [persona, session?.customer_id]);

  // Save conversation to localStorage
  useEffect(() => {
    if (messages.length > 0) {
      const key = `exec_ask_${persona}_${session?.customer_id}`;
      localStorage.setItem(key, JSON.stringify(messages.slice(-20)));  // keep last 20
    }
  }, [messages, persona, session?.customer_id]);

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
    setError(null);

    try {
      // Build conversation history for context
      const history = messages
        .reduce<{ query: string; response: string; customer_id: number }[]>((acc, m, i, arr) => {
          if (m.role === 'user' && arr[i + 1]?.role === 'assistant') {
            acc.push({
              query: m.content,
              response: arr[i + 1].content,
              customer_id: session?.customer_id || 0,
            });
          }
          return acc;
        }, [])
        .slice(-3);  // last 3 exchanges

      const res = await apiCall('/api/executive/ask', {
        method: 'POST',
        headers: { 'X-Customer-ID': getCustomerIdentifier(session) },
        body: JSON.stringify({
          query: text.trim(),
          persona,
          conversation_history: history,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: 'Request failed' }));
        throw new Error(err.error || err.message || `HTTP ${res.status}`);
      }

      const data = await res.json();

      const assistantMsg: Message = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
        elapsed_ms: data.elapsed_ms,
        context_stats: data.context_stats,
        suggested_followups: data.suggested_followups,
      };

      setMessages(prev => [...prev, assistantMsg]);
    } catch (err: any) {
      setError(err.message || 'Failed to get response');
    } finally {
      setLoading(false);
    }
  }, [loading, messages, persona, session]);

  const clearConversation = () => {
    setMessages([]);
    const key = `exec_ask_${persona}_${session?.customer_id}`;
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

  return (
    <div className="fixed bottom-6 right-6 z-50 w-[440px] flex flex-col
                    bg-[#0d1117] border border-gray-700/50 rounded-2xl shadow-2xl shadow-black/40
                    overflow-hidden" style={{ maxHeight: 'calc(100vh - 100px)' }}>

      {/* ── Header ── */}
      <div className={`flex items-center justify-between px-4 py-3 bg-gradient-to-r ${meta.gradient} border-b border-gray-700/50`}>
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-[#1a1f2e] rounded-lg">
            <Icon className={`h-4 w-4 ${meta.accent}`} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">{meta.title}</h3>
            <p className="text-[10px] text-gray-400">{meta.subtitle}</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
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

        {/* Welcome message when empty */}
        {messages.length === 0 && (
          <div className="text-center py-6">
            <div className="inline-flex p-3 bg-[#1a1f2e] rounded-xl mb-3">
              <Sparkles className={`h-6 w-6 ${meta.accent}`} />
            </div>
            <h4 className="text-sm font-medium text-white mb-1">
              Ask me anything about your portfolio
            </h4>
            <p className="text-xs text-gray-500 mb-4">
              I have access to all {persona === 'cro' ? 'revenue & pipeline' : persona === 'cfo' ? 'investment & ROI' : 'portfolio'} data,
              context graph signals, and playbook history.
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
            <div className={`max-w-[85%] ${
              msg.role === 'user'
                ? 'bg-cyan-600/20 border border-cyan-500/30 text-cyan-50'
                : 'bg-[#1a1f2e] border border-gray-700/50 text-gray-200'
            } rounded-xl px-3 py-2`}>
              <div className="text-xs leading-relaxed whitespace-pre-wrap">
                {renderMarkdown(msg.content)}
              </div>
              {/* Context stats badge */}
              {msg.context_stats && (
                <div className="flex items-center gap-2 mt-2 pt-2 border-t border-gray-700/30">
                  <span className="text-[9px] text-gray-500">
                    {msg.context_stats.accounts} accounts · {msg.context_stats.signals} signals · {msg.context_stats.causal_edges} causal edges
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

        {/* Loading indicator */}
        {loading && (
          <div className="flex gap-2">
            <div className="flex-shrink-0 mt-1">
              <div className="p-1 bg-[#1a1f2e] rounded-md">
                <Bot className={`h-3.5 w-3.5 ${meta.accent}`} />
              </div>
            </div>
            <div className="bg-[#1a1f2e] border border-gray-700/50 rounded-xl px-3 py-2">
              <div className="flex items-center gap-2">
                <Loader2 className="h-3 w-3 text-gray-400 animate-spin" />
                <span className="text-xs text-gray-400">Analyzing portfolio data...</span>
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

      {/* ── Suggested Questions ── */}
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
            placeholder={`Ask your ${PERSONA_META[persona].title.toLowerCase()}...`}
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
          Powered by context graph · {messages.filter(m => m.role === 'assistant').length} responses this session
        </p>
      </div>
    </div>
  );
};

// ── Markdown-lite renderer ───────────────────────────────────────────────────

function renderMarkdown(text: string): React.ReactNode {
  if (!text) return null;

  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];

  lines.forEach((line, i) => {
    const trimmed = line.trim();
    if (!trimmed) {
      elements.push(<br key={`br-${i}`} />);
      return;
    }

    // Bold: **text**
    const parts = trimmed.split(/(\*\*[^*]+\*\*)/g);
    const rendered = parts.map((part, j) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={j} className="text-white font-semibold">{part.slice(2, -2)}</strong>;
      }
      return part;
    });

    // Bullet points
    if (trimmed.startsWith('- ') || trimmed.startsWith('• ')) {
      elements.push(
        <div key={i} className="flex gap-1.5 ml-1">
          <span className="text-gray-500 mt-0.5">•</span>
          <span>{rendered.map((r, idx) => typeof r === 'string' ? r.replace(/^[-•]\s*/, '') : r)}</span>
        </div>
      );
    } else {
      elements.push(<p key={i} className="mb-1">{rendered}</p>);
    }
  });

  return <>{elements}</>;
}

export default AskAnythingDialog;
