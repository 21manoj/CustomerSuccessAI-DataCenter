/**
 * CSM Dashboard — Entry Point with Layout Switcher
 * =================================================
 *
 * Provides two CSM-optimized layouts:
 * - Focus Flow: Sequential task queue (Superhuman-inspired)
 * - Cockpit: Kanban board with contextual drawer (Linear-inspired)
 *
 * Layout preference is persisted in localStorage.
 * Includes floating AI chatbot available in both layouts.
 */

import React, { useState, useCallback } from 'react';
import { MessageSquare, X, Layout, Layers } from 'lucide-react';
import CSMFocusFlow from './CSMFocusFlow';
import CSMCockpit from './CSMCockpit';

type LayoutMode = 'focus' | 'cockpit';

const CSMDashboard: React.FC = () => {
  const [layout, setLayout] = useState<LayoutMode>(() => {
    return (localStorage.getItem('csm_layout') as LayoutMode) || 'focus';
  });
  const [chatOpen, setChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState<Array<{ role: 'user' | 'ai'; text: string }>>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);

  const switchLayout = useCallback((mode: LayoutMode) => {
    setLayout(mode);
    localStorage.setItem('csm_layout', mode);
  }, []);

  const handleChatSend = useCallback(async () => {
    if (!chatInput.trim() || chatLoading) return;
    const userMsg = chatInput.trim();
    setChatInput('');
    setChatMessages(prev => [...prev, { role: 'user', text: userMsg }]);
    setChatLoading(true);

    try {
      const customerId = localStorage.getItem('customer_id') || '';
      const res = await fetch('/api/rag-query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Customer-ID': customerId },
        body: JSON.stringify({ query: userMsg, query_type: 'account_analysis' }),
      });
      if (res.ok) {
        const data = await res.json();
        const answer = data.answer || data.response || 'No response available.';
        setChatMessages(prev => [...prev, { role: 'ai', text: answer }]);
      } else {
        setChatMessages(prev => [...prev, { role: 'ai', text: 'Sorry, I could not process that request.' }]);
      }
    } catch {
      setChatMessages(prev => [...prev, { role: 'ai', text: 'Connection error. Please try again.' }]);
    } finally {
      setChatLoading(false);
    }
  }, [chatInput, chatLoading]);

  return (
    <div className="relative min-h-screen">
      {/* Layout Switcher — fixed bottom-left */}
      <div className="fixed bottom-6 left-6 z-40 flex items-center gap-1 bg-white rounded-full shadow-lg border border-gray-200 p-1">
        <button
          onClick={() => switchLayout('focus')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
            layout === 'focus' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'
          }`}
          title="Focus Flow — Sequential task queue"
        >
          <Layout className="h-3.5 w-3.5" />
          Focus
        </button>
        <button
          onClick={() => switchLayout('cockpit')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
            layout === 'cockpit' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'
          }`}
          title="Cockpit — Kanban board"
        >
          <Layers className="h-3.5 w-3.5" />
          Board
        </button>
      </div>

      {/* Active Layout */}
      {layout === 'focus' ? <CSMFocusFlow /> : <CSMCockpit />}

      {/* Floating AI Chat Button */}
      <button
        onClick={() => setChatOpen(!chatOpen)}
        className={`fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full shadow-lg flex items-center justify-center transition-all ${
          chatOpen
            ? 'bg-gray-700 text-white hover:bg-gray-800'
            : 'bg-blue-600 text-white hover:bg-blue-700 hover:scale-105'
        }`}
      >
        {chatOpen ? <X className="h-6 w-6" /> : <MessageSquare className="h-6 w-6" />}
      </button>

      {/* AI Chat Panel */}
      {chatOpen && (
        <div className="fixed bottom-24 right-6 z-50 w-96 h-[60vh] bg-white rounded-2xl shadow-2xl border border-gray-200 flex flex-col overflow-hidden">
          {/* Chat Header */}
          <div className="px-4 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              <span className="font-semibold text-sm">AI Assistant</span>
            </div>
            <span className="text-xs text-blue-200">Ask about any account</span>
          </div>

          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {chatMessages.length === 0 && (
              <div className="text-center text-gray-400 text-sm mt-8">
                <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>Ask me anything about your accounts.</p>
                <p className="text-xs mt-1">e.g., "Why is Quantum Corp at risk?"</p>
              </div>
            )}
            {chatMessages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white rounded-br-md'
                      : 'bg-gray-100 text-gray-800 rounded-bl-md'
                  }`}
                >
                  {msg.text}
                </div>
              </div>
            ))}
            {chatLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-2xl rounded-bl-md px-4 py-2.5 text-sm text-gray-500">
                  <span className="animate-pulse">Thinking...</span>
                </div>
              </div>
            )}
          </div>

          {/* Chat Input */}
          <div className="border-t border-gray-200 p-3">
            <div className="flex gap-2">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleChatSend()}
                placeholder="Ask about an account..."
                className="flex-1 px-4 py-2 text-sm border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <button
                onClick={handleChatSend}
                disabled={chatLoading || !chatInput.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-full text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CSMDashboard;
