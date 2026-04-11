/**
 * ChatInterface — Multi-conversation AI chat.
 * Conversations are stored in the database and browsable.
 * Each conversation has its own thread with full history.
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { conversations as convApi } from '../../services/apiService';

// ── Conversation List View ──
function ConversationList({ onSelect, onNew }) {
  const [convs, setConvs] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    convApi.list()
      .then((data) => setConvs(Array.isArray(data) ? data : []))
      .catch(() => setConvs([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleDelete(e, id) {
    e.stopPropagation();
    await convApi.delete(id).catch(() => {});
    setConvs((prev) => prev.filter((c) => c.id !== id));
  }

  function groupByDate(list) {
    const today = new Date().toDateString();
    const yesterday = new Date(Date.now() - 86400000).toDateString();
    const groups = { Today: [], Yesterday: [], Earlier: [] };
    for (const c of list) {
      const d = new Date(c.updated_at || c.created_at).toDateString();
      if (d === today) groups.Today.push(c);
      else if (d === yesterday) groups.Yesterday.push(c);
      else groups.Earlier.push(c);
    }
    return groups;
  }

  const groups = groupByDate(convs);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl gradient-blue-purple flex items-center justify-center shadow-glow-blue">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
            </svg>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Omura AI</h3>
            <p className="text-[10px] text-slate-500">{convs.length} conversation{convs.length !== 1 ? 's' : ''}</p>
          </div>
        </div>
        <button
          onClick={onNew}
          className="flex items-center gap-1.5 text-xs bg-blue-500/15 hover:bg-blue-500/25 text-blue-400
            border border-blue-500/20 py-1.5 px-3 rounded-lg font-medium transition-all"
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New
        </button>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto px-3 py-3">
        {loading ? (
          <div className="space-y-2 px-1">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-14 rounded-xl bg-white/[0.03] animate-pulse" />
            ))}
          </div>
        ) : convs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <div className="w-14 h-14 rounded-2xl gradient-blue-purple mx-auto mb-4 flex items-center justify-center opacity-60">
              <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <p className="text-sm text-slate-400 mb-1">No conversations yet</p>
            <p className="text-xs text-slate-600">Start a new one below</p>
            <button
              onClick={onNew}
              className="mt-4 btn btn-primary text-xs py-2 px-5"
            >
              Start chatting
            </button>
          </div>
        ) : (
          Object.entries(groups).map(([group, items]) =>
            items.length === 0 ? null : (
              <div key={group} className="mb-3">
                <p className="text-[10px] text-slate-600 uppercase tracking-[0.15em] font-semibold px-2 mb-1.5">{group}</p>
                <div className="space-y-1">
                  {items.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => onSelect(c)}
                      className="w-full text-left px-3 py-3 rounded-xl bg-white/[0.02] hover:bg-white/[0.05]
                        border border-white/[0.04] hover:border-white/[0.08] transition-all group"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium text-white/85 truncate flex-1 leading-tight">
                          {c.title}
                        </p>
                        <button
                          onClick={(e) => handleDelete(e, c.id)}
                          className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-600
                            hover:text-red-400 mt-0.5 flex-shrink-0"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                      {c.preview && (
                        <p className="text-[11px] text-slate-600 truncate mt-0.5">{c.preview}</p>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )
          )
        )}
      </div>
    </div>
  );
}

// ── Tool icon map for live activity feed ──
const TOOL_ICONS = {
  thinking: { icon: '🧠', color: 'text-purple-400', label: 'Thinking' },
  tool_start: { icon: '⚡', color: 'text-blue-400', label: 'Running' },
  tool_done: { icon: '✓', color: 'text-emerald-400', label: 'Done' },
  error: { icon: '✕', color: 'text-red-400', label: 'Error' },
};

const TOOL_NICE_NAMES = {
  run_outreach_pipeline: 'Outreach pipeline',
  send_outreach_email: 'Send outreach email',
  bulk_send_outreach: 'Bulk email send',
  request_internet: 'Web fetch',
  create_lead: 'Create lead',
  update_lead: 'Update lead',
  create_task: 'Create task',
  create_note: 'Save note',
  create_calendar_event: 'Calendar event',
  get_system_state: 'Load system state',
  run_agent: 'Run agent',
};

// ── Single Conversation Chat View ──
function ConversationChat({ conv, onBack }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  // Live activity feed while agent is working
  const [activity, setActivity] = useState([]); // [{type, label, detail, ts}]
  const messagesEndRef = useRef(null);
  const activityEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (!conv.id) { setLoadingHistory(false); return; }
    setLoadingHistory(true);
    convApi.messages(conv.id)
      .then((data) => setMessages(Array.isArray(data) ? data.map((m) => ({ role: m.role, text: m.content, actions: m.actions_taken || [] })) : []))
      .catch(() => setMessages([]))
      .finally(() => setLoadingHistory(false));
  }, [conv.id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  useEffect(() => {
    activityEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activity]);

  useEffect(() => {
    if (!loadingHistory) inputRef.current?.focus();
  }, [loadingHistory]);

  async function handleSend(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', text }]);
    setLoading(true);
    setActivity([]);

    try {
      let convId = conv.id;
      if (!convId) {
        const created = await convApi.create('New Conversation');
        convId = created.id;
        conv.id = convId;
      }

      // Use SSE streaming endpoint
      const resp = await fetch(`/api/conversations/${convId}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(typeof window !== 'undefined' && localStorage.getItem('omura_token')
            ? { Authorization: `Bearer ${localStorage.getItem('omura_token')}` }
            : {}),
        },
        body: JSON.stringify({ message: text }),
      });

      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let finalReply = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // SSE lines: "data: {...}\n\n"
        const lines = buffer.split('\n\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const event = JSON.parse(line.slice(6));
            if (event.type === 'done') {
              finalReply = event.reply || '';
            } else if (event.type === 'error') {
              finalReply = `Error: ${event.message}`;
            } else {
              // Live activity event
              const ts = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
              let label = '';
              let detail = '';

              if (event.type === 'thinking') {
                label = event.message || 'Thinking...';
              } else if (event.type === 'tool_start') {
                label = TOOL_NICE_NAMES[event.tool] || event.tool?.replace(/_/g, ' ');
                const inp = event.input || {};
                const preview = inp.industries?.join(', ') || inp.locations?.join(', ') || inp.name || inp.to || inp.email || '';
                if (preview) detail = preview;
              } else if (event.type === 'tool_done') {
                label = event.summary || (TOOL_NICE_NAMES[event.tool] || event.tool?.replace(/_/g, ' '));
                detail = event.success === false ? 'failed' : '';
              }

              setActivity((prev) => [...prev, { type: event.type, label, detail, ts, tool: event.tool }]);
            }
          } catch {
            // malformed JSON — skip
          }
        }
      }

      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: finalReply || 'No response.', actions: [] },
      ]);
    } catch (err) {
      const msg = err?.message || 'Connection failed';
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: `Error: ${msg}`, actions: [] },
      ]);
      console.error('[Chat SSE error]', err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3.5 border-b border-white/[0.06]">
        <button
          onClick={onBack}
          className="w-7 h-7 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] flex items-center justify-center transition-all flex-shrink-0"
        >
          <svg className="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-white truncate">{conv.title}</p>
        </div>
        <div className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]" />
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-0">
        {loadingHistory ? (
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <div key={i} className={`flex ${i % 2 === 0 ? 'justify-end' : 'justify-start'}`}>
                <div className="h-10 w-48 rounded-2xl bg-white/[0.03] animate-pulse" />
              </div>
            ))}
          </div>
        ) : messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <p className="text-sm text-slate-400">Ask Omura anything</p>
              <p className="text-xs text-slate-600 mt-1">Tasks, leads, strategy, content...</p>
            </div>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div
                className={`max-w-[82%] px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
                  msg.role === 'user'
                    ? 'bg-gradient-to-br from-blue-600 to-blue-500 text-white rounded-2xl rounded-br-md'
                    : 'bg-white/[0.04] border border-white/[0.06] text-slate-300 rounded-2xl rounded-bl-md'
                }`}
              >
                {msg.text}
              </div>
              {msg.actions && msg.actions.length > 0 && (
                <div className="mt-1 space-y-1 ml-1">
                  {msg.actions.map((act, idx) => (
                    <div key={idx} className="flex items-center gap-1.5 text-[10px] text-slate-500 bg-white/[0.02] border border-white/[0.04] px-2.5 py-1 rounded-lg">
                      <span className="text-blue-400">⚡</span>
                      {typeof act === 'string' ? act : (act.tool || act.action || JSON.stringify(act))}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))
        )}

        {/* Live activity feed */}
        {loading && (
          <div className="flex justify-start">
            <div className="w-full max-w-[90%] bg-white/[0.03] border border-white/[0.06] rounded-2xl rounded-bl-md overflow-hidden">
              {/* Activity header */}
              <div className="flex items-center gap-2 px-3 py-2 border-b border-white/[0.05]">
                <div className="flex gap-1">
                  <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
                <span className="text-[10px] text-slate-500 font-medium tracking-wide uppercase">Agent working</span>
              </div>
              {/* Activity rows */}
              <div className="px-3 py-2 space-y-1.5 max-h-40 overflow-y-auto">
                {activity.length === 0 ? (
                  <div className="text-[11px] text-slate-600 py-1">Connecting to AI...</div>
                ) : (
                  activity.map((item, idx) => {
                    const cfg = TOOL_ICONS[item.type] || TOOL_ICONS.tool_start;
                    const isLatest = idx === activity.length - 1;
                    return (
                      <div
                        key={idx}
                        className={`flex items-start gap-2 text-[11px] transition-opacity duration-300 ${isLatest ? 'opacity-100' : 'opacity-50'}`}
                      >
                        <span className={`flex-shrink-0 mt-px ${cfg.color} font-bold`}>{cfg.icon}</span>
                        <div className="flex-1 min-w-0">
                          <span className="text-slate-300">{item.label}</span>
                          {item.detail && (
                            <span className="text-slate-600 ml-1 truncate">— {item.detail}</span>
                          )}
                        </div>
                        <span className="flex-shrink-0 text-slate-700 font-mono text-[9px]">{item.ts}</span>
                      </div>
                    );
                  })
                )}
                <div ref={activityEndRef} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSend} className="px-4 py-3 border-t border-white/[0.06]">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask Omura anything..."
            disabled={loading || loadingHistory}
            className="flex-1 bg-white/[0.03] border border-white/[0.06] rounded-xl text-sm py-2.5 px-4
              text-white placeholder-slate-600 outline-none
              focus:border-blue-500/30 focus:shadow-[0_0_0_3px_rgba(59,130,246,0.06)]
              transition-all duration-300"
          />
          <button
            type="submit"
            disabled={loading || loadingHistory || !input.trim()}
            className="w-10 h-10 rounded-xl gradient-blue-purple flex items-center justify-center
              disabled:opacity-30 hover:shadow-glow-blue transition-all"
          >
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          </button>
        </div>
      </form>
    </div>
  );
}

// ── Floating Chat Widget (bottom-right button) ──
export default function ChatInterface() {
  const [open, setOpen] = useState(false);
  const [activeConv, setActiveConv] = useState(null);
  const [listKey, setListKey] = useState(0); // force list refresh

  async function handleNewConversation() {
    try {
      const conv = await convApi.create('New Conversation');
      setActiveConv(conv);
    } catch {
      // fallback: open with a temp obj, backend will create on first message
      setActiveConv({ id: null, title: 'New Conversation' });
    }
  }

  function handleSelectConversation(conv) {
    setActiveConv(conv);
  }

  function handleBack() {
    setActiveConv(null);
    setListKey((k) => k + 1); // refresh list to show updated titles
  }

  return (
    <>
      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-24 right-6 z-[9998] w-[400px]
          bg-[#08090F]/95 backdrop-blur-2xl border border-white/[0.06]
          rounded-3xl shadow-[0_16px_60px_rgba(0,0,0,0.5)] overflow-hidden
          animate-slide-up"
          style={{ height: 'calc(100vh - 140px)', maxHeight: '36rem' }}>
          {activeConv ? (
            <ConversationChat conv={activeConv} onBack={handleBack} />
          ) : (
            <ConversationList
              key={listKey}
              onSelect={handleSelectConversation}
              onNew={handleNewConversation}
            />
          )}
        </div>
      )}

      {/* Floating toggle button — always on top */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-6 right-6 z-[9999] w-14 h-14 rounded-2xl gradient-blue-purple
          flex items-center justify-center
          shadow-[0_0_30px_rgba(59,130,246,0.25)]
          hover:shadow-[0_0_40px_rgba(59,130,246,0.4)]
          hover:scale-105 transition-all duration-300"
        aria-label="Toggle AI chat"
      >
        {open ? (
          <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        )}
      </button>
    </>
  );
}

// ── Full-page Chat (used as a dashboard section) ──
export function ChatPage() {
  const [activeConv, setActiveConv] = useState(null);
  const [listKey, setListKey] = useState(0);

  async function handleNewConversation() {
    try {
      const conv = await convApi.create('New Conversation');
      setActiveConv(conv);
    } catch {
      setActiveConv({ id: null, title: 'New Conversation' });
    }
  }

  function handleBack() {
    setActiveConv(null);
    setListKey((k) => k + 1);
  }

  return (
    <div className="grid grid-cols-[320px_1fr] gap-6 h-[calc(100vh-160px)]">
      {/* Left: conversation list */}
      <div className="glass-card overflow-hidden flex flex-col">
        <ConversationList
          key={listKey}
          onSelect={setActiveConv}
          onNew={handleNewConversation}
        />
      </div>

      {/* Right: active chat */}
      <div className="glass-card overflow-hidden flex flex-col">
        {activeConv ? (
          <ConversationChat conv={activeConv} onBack={handleBack} />
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-2xl gradient-blue-purple mx-auto mb-5 flex items-center justify-center shadow-glow-blue opacity-80">
              <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
            </div>
            <p className="text-base font-semibold text-white/80 mb-2">Select a conversation</p>
            <p className="text-sm text-slate-500 mb-6">or start a new one to talk to Omura AI</p>
            <button onClick={handleNewConversation} className="btn btn-primary py-2.5 px-6">
              New Conversation
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
