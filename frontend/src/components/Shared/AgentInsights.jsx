/**
 * AgentInsights — reusable panel that shows recent agent runs as plain-English
 * briefs for a given dashboard section (never raw JSON).
 */

import React, { useEffect, useState } from 'react';
import { FiZap, FiRefreshCw } from 'react-icons/fi';
import { insights as insightsApi } from '../../services/apiService';

export default function AgentInsights({ section, title = 'Latest AI insights', limit = 6 }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const r = await insightsApi.list(section, limit);
      setItems(Array.isArray(r) ? r : []);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [section]);

  return (
    <div className="glass-card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold flex items-center gap-2 text-white">
          <FiZap className="text-violet-400" /> {title}
        </h3>
        <button onClick={load} className="btn btn-ghost text-xs">
          <FiRefreshCw size={13} /> Refresh
        </button>
      </div>
      {items.length > 0 ? (
        <div className="space-y-2">
          {items.map((it) => (
            <div key={it.id} className="glass-inner p-3">
              <div className="flex items-center gap-2 mb-1">
                <span className="badge badge-accent text-xs">{it.agent_name}</span>
                <span className="text-xs text-slate-500">{(it.action || '').replace(/_/g, ' ')}</span>
                <span className="text-[10px] text-slate-600 ml-auto">
                  {it.created_at ? new Date(it.created_at).toLocaleString() : ''}
                </span>
              </div>
              <p className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">{it.summary}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-slate-500">
          {loading ? 'Loading…' : 'No AI runs yet. Run an agent and the plain-English result shows up here.'}
        </p>
      )}
    </div>
  );
}
