/**
 * EmailDraftModal — AI-generated contextual email drafts.
 *
 * Template auto-selects based on health score:
 * - health < 50: health_drop
 * - 50-69: renewal
 * - >= 70: expansion
 *
 * Generates via POST /api/executive/ask-v2 with email drafting prompt.
 * Shows editable subject + body, "Copy to Clipboard" + "Open in Mail Client".
 */

import React, { useState, useCallback } from 'react';
import { Mail, X, Copy, ExternalLink, RefreshCw, AlertTriangle, Check } from 'lucide-react';

interface EmailDraftModalProps {
  accountId: number;
  accountName: string;
  healthScore: number;
  customerId: string;
  onClose: () => void;
}

const TEMPLATES = [
  { id: 'health_drop', label: 'Health Drop', description: 'Proactive outreach for declining health' },
  { id: 'qbr_prep', label: 'QBR Prep', description: 'Quarterly business review agenda' },
  { id: 'expansion', label: 'Expansion', description: 'Upsell / cross-sell conversation starter' },
  { id: 'renewal', label: 'Renewal', description: 'Renewal check-in and value summary' },
];

function autoTemplate(health: number): string {
  if (health < 50) return 'health_drop';
  if (health < 70) return 'renewal';
  return 'expansion';
}

const EmailDraftModal: React.FC<EmailDraftModalProps> = ({
  accountId,
  accountName,
  healthScore,
  customerId,
  onClose,
}) => {
  const [template, setTemplate] = useState(autoTemplate(healthScore));
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  const generateDraft = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const prompt = `Draft a brief professional email for the ${template.replace('_', ' ')} template.
Account: ${accountName} (Health Score: ${healthScore}/100).
Keep it under 150 words. Include a subject line on the first line prefixed with "Subject: ".
The rest is the email body. Be specific to the account context.`;

      const resp = await fetch('/api/executive/ask-v2', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Customer-ID': customerId,
        },
        credentials: 'include',
        body: JSON.stringify({
          query: prompt,
          persona: 'csm',
          customer_id: parseInt(customerId),
        }),
      });

      if (!resp.ok) throw new Error(`API returned ${resp.status}`);
      const data = await resp.json();
      const text = data.response || data.answer || data.text || '';

      // Parse subject from response
      const lines = text.split('\n').filter((l: string) => l.trim());
      const subjectLine = lines.find((l: string) => l.toLowerCase().startsWith('subject:'));
      if (subjectLine) {
        setSubject(subjectLine.replace(/^subject:\s*/i, '').trim());
        setBody(lines.filter((l: string) => l !== subjectLine).join('\n').trim());
      } else {
        setSubject(`${template.replace('_', ' ')} — ${accountName}`);
        setBody(text.trim());
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to generate draft');
    } finally {
      setLoading(false);
    }
  }, [template, accountName, healthScore, customerId]);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const openInMail = () => {
    const mailto = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    window.open(mailto, '_blank');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 shrink-0">
          <div className="flex items-center gap-2">
            <Mail className="w-5 h-5 text-blue-600" />
            <h2 className="text-base font-semibold text-gray-900">Draft Email</h2>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-lg">
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </div>

        {/* Body */}
        <div className="px-5 py-4 space-y-4 overflow-y-auto flex-1">
          {/* Account context */}
          <div className="text-sm text-gray-600">
            <span className="font-medium text-gray-900">{accountName}</span>
            <span className="text-gray-400 ml-2">Health: {healthScore}</span>
          </div>

          {/* Template selector */}
          <div>
            <label className="text-xs font-medium text-gray-700 block mb-1.5">Template</label>
            <div className="flex gap-2 flex-wrap">
              {TEMPLATES.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setTemplate(t.id)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition ${
                    template === t.id
                      ? 'bg-blue-50 border-blue-300 text-blue-700'
                      : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
                  }`}
                  title={t.description}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Generate button */}
          {!subject && !body && (
            <button
              onClick={generateDraft}
              disabled={loading}
              className="flex items-center justify-center gap-2 w-full py-3 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
            >
              {loading ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Mail className="w-4 h-4" />
              )}
              {loading ? 'Generating...' : 'Generate Draft'}
            </button>
          )}

          {/* Draft preview */}
          {(subject || body) && (
            <>
              <div>
                <label className="text-xs font-medium text-gray-700 block mb-1">Subject</label>
                <input
                  type="text"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-700 block mb-1">Body</label>
                <textarea
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none h-40 focus:outline-none focus:ring-2 focus:ring-blue-300"
                />
              </div>
              <button
                onClick={generateDraft}
                disabled={loading}
                className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
              >
                <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
                Regenerate
              </button>
            </>
          )}

          {error && (
            <div className="flex items-center gap-2 text-xs text-red-600 bg-red-50 px-3 py-2 rounded">
              <AlertTriangle className="w-3.5 h-3.5" /> {error}
            </div>
          )}
        </div>

        {/* Footer */}
        {(subject || body) && (
          <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-gray-100 bg-gray-50 shrink-0">
            <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-200 rounded-lg transition">
              Cancel
            </button>
            <button
              onClick={copyToClipboard}
              className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5" />}
              {copied ? 'Copied!' : 'Copy'}
            </button>
            <button
              onClick={openInMail}
              className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              Open in Mail
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default EmailDraftModal;
