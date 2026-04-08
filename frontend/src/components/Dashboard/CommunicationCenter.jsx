/**
 * Communication Center — Inbox summary, flagged messages, AI-suggested responses.
 */

import React, { useState, useEffect } from 'react';
import { FiMail, FiFlag, FiAlertTriangle, FiSend, FiMessageSquare } from 'react-icons/fi';
import { dashboard, communications, ai } from '../../services/apiService';

function stripHtml(html) {
  if (!html) return '';
  if (typeof window !== 'undefined' && window.DOMParser) {
    try {
      const doc = new DOMParser().parseFromString(html, 'text/html');
      return (doc.body.textContent || '').replace(/\s+/g, ' ').trim();
    } catch { /* fall through */ }
  }
  return html.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
}

const PLATFORM_COLORS = {
  gmail: 'text-red-400',
  instagram: 'text-pink-400',
  facebook: 'text-blue-400',
  tiktok: 'text-cyan-400',
  youtube: 'text-red-500',
};

function MessageRow({ message, onSelect, isSelected }) {
  return (
    <div
      onClick={() => onSelect(message)}
      className={`glass-inner flex items-start gap-3 p-3 cursor-pointer transition-all
        ${isSelected ? 'bg-white/[0.08] border-blue-500/30' : 'hover:bg-white/[0.06]'}`}
    >
      <div className={`mt-0.5 ${PLATFORM_COLORS[message.platform] || 'text-slate-400'}`}>
        <FiMessageSquare size={16} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-white truncate">{message.sender}</p>
          {message.is_flagged && <FiFlag size={12} className="text-amber-400" />}
          {message.urgency === 'high' || message.urgency === 'critical' ? (
            <FiAlertTriangle size={12} className="text-red-400" />
          ) : null}
        </div>
        <p className="text-xs text-slate-400 truncate">{message.subject || stripHtml(message.body)}</p>
        <p className="text-xs text-slate-500 mt-1">{message.platform} &middot; {message.received_at || 'Just now'}</p>
      </div>
      {!message.is_read && (
        <span className="badge badge-info text-[0.6rem] mt-1">NEW</span>
      )}
    </div>
  );
}

export default function CommunicationCenter() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedMsg, setSelectedMsg] = useState(null);
  const [filter, setFilter] = useState('all'); // all, unread, flagged, urgent
  const [editingResponse, setEditingResponse] = useState(null); // null or string
  const [sending, setSending] = useState(false);
  const [dismissed, setDismissed] = useState(new Set());

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const result = await dashboard.getCommunicationCenter();
      setData(result);
    } catch {
      setData({ unread: [], flagged: [], urgent: [] });
    } finally { setLoading(false); }
  }

  function handleSelectMsg(msg) {
    setSelectedMsg(msg);
    setEditingResponse(null);
  }

  async function handleSend(responseText) {
    setSending(true);
    try {
      await communications.update(selectedMsg.id, {
        action: 'send_response',
        response: responseText,
        is_read: true,
      });
      await loadData();
      setSelectedMsg(null);
    } catch { /* silently handled */ } finally { setSending(false); }
  }

  function handleDismiss(msgId) {
    setDismissed((prev) => new Set([...prev, msgId]));
  }

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="grid grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className={`stat-card animate-fade-in-up-${i}`}>
              <div className="skeleton w-12 h-7 rounded-lg mx-auto mb-2" />
              <div className="skeleton w-24 h-3 rounded mx-auto" />
            </div>
          ))}
        </div>
        <div className="flex gap-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton w-28 h-9 rounded-xl" />
          ))}
        </div>
        <div className="grid grid-cols-2 gap-6">
          <div className="glass-card">
            <div className="flex items-center gap-2 mb-4">
              <div className="skeleton w-4 h-4 rounded" />
              <div className="skeleton w-20 h-4 rounded" />
            </div>
            {[1, 2, 3].map((i) => (
              <div key={i} className="skeleton w-full h-16 rounded-xl mb-2" />
            ))}
          </div>
          <div className="glass-card">
            <div className="skeleton w-full h-64 rounded-xl" />
          </div>
        </div>
      </div>
    );
  }

  const { unread = [], flagged = [], urgent = [] } = data || {};
  const messages = filter === 'flagged' ? flagged : filter === 'urgent' ? urgent : unread;

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="stat-card">
          <p className="text-2xl font-bold text-blue-400">{unread.length}</p>
          <p className="text-xs text-slate-400 mt-1">Unread Messages</p>
        </div>
        <div className="stat-card">
          <p className="text-2xl font-bold text-amber-400">{flagged.length}</p>
          <p className="text-xs text-slate-400 mt-1">Flagged</p>
        </div>
        <div className="stat-card">
          <p className="text-2xl font-bold text-red-400">{urgent.length}</p>
          <p className="text-xs text-slate-400 mt-1">Urgent</p>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2">
        {['all', 'flagged', 'urgent'].map((f) => (
          <button key={f} onClick={() => setFilter(f)}
            className={`btn text-xs capitalize ${filter === f ? 'btn-primary' : 'btn-ghost'}`}>
            {f === 'all' ? `All Unread (${unread.length})` : f === 'flagged' ? `Flagged (${flagged.length})` : `Urgent (${urgent.length})`}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Message List */}
        <div className="glass-card max-h-[600px] overflow-y-auto">
          <h3 className="font-semibold mb-3 flex items-center gap-2 text-white">
            <FiMail size={16} className="text-blue-400" /> Messages
          </h3>
          <div className="space-y-2">
            {messages.map((msg) => (
              <MessageRow key={msg.id} message={msg} onSelect={handleSelectMsg} isSelected={selectedMsg?.id === msg.id} />
            ))}
            {messages.length === 0 && (
              <div className="text-center py-12">
                <div className="w-14 h-14 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mx-auto mb-4">
                  <FiMail className="text-blue-400/60" size={22} />
                </div>
                <p className="text-sm font-medium text-slate-400">No messages</p>
                <p className="text-xs text-slate-600 mt-1">Messages will appear here once your inbox is connected</p>
              </div>
            )}
          </div>
        </div>

        {/* Message Detail + AI Response */}
        <div className="glass-card">
          {selectedMsg ? (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className={`${PLATFORM_COLORS[selectedMsg.platform]} capitalize text-sm font-medium`}>{selectedMsg.platform}</span>
                {selectedMsg.urgency && (
                  <span className={`badge ${selectedMsg.urgency === 'critical' ? 'badge-danger' : selectedMsg.urgency === 'high' ? 'badge-warning' : 'badge-info'}`}>
                    {selectedMsg.urgency}
                  </span>
                )}
              </div>
              <h3 className="font-semibold text-white">{selectedMsg.subject || 'Direct Message'}</h3>
              <p className="text-sm text-slate-400 mt-1">From: {selectedMsg.sender}</p>
              <div className="mt-4 glass-inner p-4 text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">
                {stripHtml(selectedMsg.body)}
              </div>

              {selectedMsg.ai_suggested_response && !dismissed.has(selectedMsg.id) && (
                <div className="mt-4">
                  <p className="text-xs text-slate-500 mb-2 flex items-center gap-1">
                    <FiSend size={12} className="text-blue-400" /> AI Suggested Response:
                  </p>
                  {editingResponse !== null ? (
                    <textarea
                      value={editingResponse}
                      onChange={(e) => setEditingResponse(e.target.value)}
                      rows={4}
                      className="w-full rounded-xl px-4 py-3 bg-white/[0.05] border border-blue-500/30 text-sm text-slate-200 resize-none focus:outline-none focus:border-blue-500/60"
                    />
                  ) : (
                    <div className="p-3 bg-blue-500/5 border border-blue-500/20 rounded-xl text-sm text-slate-300">
                      {selectedMsg.ai_suggested_response}
                    </div>
                  )}
                  <div className="flex gap-2 mt-3">
                    <button
                      onClick={() => handleSend(editingResponse ?? selectedMsg.ai_suggested_response)}
                      disabled={sending}
                      className="btn btn-primary text-xs"
                    >
                      <FiSend size={14} /> {sending ? 'Sending...' : 'Send'}
                    </button>
                    {editingResponse === null
                      ? <button onClick={() => setEditingResponse(selectedMsg.ai_suggested_response)} className="btn btn-ghost text-xs">Edit</button>
                      : <button onClick={() => setEditingResponse(null)} className="btn btn-ghost text-xs">Cancel</button>
                    }
                    <button onClick={() => handleDismiss(selectedMsg.id)} className="btn btn-ghost text-xs">Dismiss</button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-64 text-slate-500 text-sm">
              Select a message to view details
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
