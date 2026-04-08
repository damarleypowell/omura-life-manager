/**
 * Outreach Pipeline — Hunter.io lead gen, research, personalized copy, approve & send.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  FiSearch, FiSend, FiMail, FiUser, FiGlobe, FiZap,
  FiCheckCircle, FiClock, FiAlertCircle, FiChevronDown,
  FiChevronUp, FiRefreshCw, FiTarget, FiLinkedin, FiMessageSquare,
} from 'react-icons/fi';
import { outreach as outreachApi, leads as leadsApi } from '../../services/apiService';

/* ─── helpers ─────────────────────────────────────────────── */
function parseNotesSection(notes, header) {
  if (!notes) return '';
  const start = notes.indexOf(`[${header}]`);
  if (start === -1) return '';
  const afterHeader = notes.indexOf('\n', start) + 1;
  const nextBracket = notes.indexOf('\n[', afterHeader);
  return (nextBracket === -1 ? notes.slice(afterHeader) : notes.slice(afterHeader, nextBracket)).trim();
}

function parseOutreachCopy(notes) {
  const block = parseNotesSection(notes, 'OUTREACH COPY');
  if (!block) return null;
  const lines = block.split('\n');
  const subject = lines.find(l => l.startsWith('Subject:'))?.replace('Subject:', '').trim() || '';
  const bodyStart = lines.findIndex(l => l.startsWith('Body:'));
  const dmStart   = lines.findIndex(l => l.startsWith('DM:'));
  const liStart   = lines.findIndex(l => l.startsWith('LinkedIn:'));
  const body = bodyStart !== -1
    ? lines.slice(bodyStart + 1, dmStart !== -1 ? dmStart : undefined).join('\n').trim() ||
      lines[bodyStart].replace('Body:', '').trim()
    : '';
  const dm = dmStart !== -1
    ? lines[dmStart].replace('DM:', '').trim()
    : '';
  const linkedin = liStart !== -1
    ? lines[liStart].replace('LinkedIn:', '').trim()
    : '';
  return { subject, body, dm, linkedin };
}

function parseResearch(notes) {
  const block = parseNotesSection(notes, 'RESEARCH');
  if (!block) return null;
  const lines = block.split('\n');
  const does = lines.find(l => l.startsWith('Does:'))?.replace('Does:', '').trim() || '';
  const painLine = lines.findIndex(l => l.startsWith('Pain:'));
  const hookLine = lines.findIndex(l => l.startsWith('Hook:'));
  const pain = painLine !== -1
    ? lines.slice(painLine, hookLine !== -1 ? hookLine : undefined)
        .join('\n').replace('Pain:', '').trim()
    : '';
  const hook = hookLine !== -1
    ? lines.slice(hookLine).join('\n').replace('Hook:', '').trim()
    : '';
  return { does, pain, hook };
}

function statusBadge(status) {
  const map = {
    new:      { label: 'New',       cls: 'bg-blue-500/15 text-blue-400 border-blue-500/25' },
    contacted:{ label: 'Contacted', cls: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/25' },
    qualified:{ label: 'Qualified', cls: 'bg-purple-500/15 text-purple-400 border-purple-500/25' },
    proposal: { label: 'Proposal',  cls: 'bg-orange-500/15 text-orange-400 border-orange-500/25' },
    won:      { label: 'Won',       cls: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/25' },
    lost:     { label: 'Lost',      cls: 'bg-red-500/15 text-red-400 border-red-500/25' },
  };
  const { label, cls } = map[status] || map.new;
  return (
    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${cls}`}>
      {label}
    </span>
  );
}

/* ─── Lead Card ──────────────────────────────────────────── */
function LeadCard({ lead, onSend }) {
  const [expanded, setExpanded] = useState(false);
  const [sending, setSending]   = useState(false);
  const [sent, setSent]         = useState(lead.status === 'contacted');
  const copy     = parseOutreachCopy(lead.notes);
  const research = parseResearch(lead.notes);
  const hasCopy  = !!copy?.subject;

  async function handleSend() {
    setSending(true);
    try {
      await outreachApi.sendInitial(lead.id);
      setSent(true);
      onSend(lead.id);
    } catch (e) {
      alert(e.message || 'Send failed');
    } finally { setSending(false); }
  }

  return (
    <div className={`rounded-2xl border transition-all duration-300
      ${sent
        ? 'bg-emerald-500/[0.04] border-emerald-500/20'
        : 'bg-white/[0.03] border-white/[0.06] hover:border-white/[0.1]'
      }`}>
      {/* Header row */}
      <div className="flex items-center gap-4 p-4">
        {/* Avatar */}
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/20 to-purple-500/20
          border border-blue-500/20 flex items-center justify-center flex-shrink-0">
          <FiUser size={16} className="text-blue-400" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-semibold text-white/90">{lead.name}</p>
            {statusBadge(sent ? 'contacted' : lead.status)}
            {hasCopy && !sent && (
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full
                bg-purple-500/15 text-purple-400 border border-purple-500/25">
                Copy Ready
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-0.5">
            <p className="text-xs text-slate-500">{lead.company}</p>
            <span className="text-slate-700">·</span>
            <p className="text-xs text-slate-600">{lead.email}</p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {hasCopy && !sent && (
            <button
              onClick={handleSend}
              disabled={sending}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold
                bg-gradient-to-r from-blue-500/20 to-purple-500/20 border border-blue-500/30
                text-blue-300 hover:from-blue-500/30 hover:to-purple-500/30
                disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
            >
              {sending ? (
                <FiRefreshCw size={12} className="animate-spin" />
              ) : (
                <FiSend size={12} />
              )}
              {sending ? 'Sending…' : 'Send'}
            </button>
          )}
          {sent && (
            <div className="flex items-center gap-1.5 text-xs text-emerald-400">
              <FiCheckCircle size={13} />
              Sent
            </div>
          )}
          {hasCopy && (
            <button
              onClick={() => setExpanded(e => !e)}
              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-300
                hover:bg-white/[0.05] transition-all duration-200"
            >
              {expanded ? <FiChevronUp size={15} /> : <FiChevronDown size={15} />}
            </button>
          )}
        </div>
      </div>

      {/* Expanded copy */}
      {expanded && hasCopy && (
        <div className="px-4 pb-4 space-y-4 border-t border-white/[0.04] pt-4">
          {/* Email copy */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs text-slate-400 font-semibold uppercase tracking-wider">
              <FiMail size={12} className="text-blue-400" />
              Email
            </div>
            <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-3 space-y-2">
              <p className="text-xs font-semibold text-white/70">Subject: {copy.subject}</p>
              <p className="text-xs text-slate-400 whitespace-pre-line leading-relaxed">{copy.body}</p>
            </div>
          </div>

          {/* DM + LinkedIn row */}
          <div className="grid grid-cols-2 gap-3">
            {copy.dm && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs text-slate-400 font-semibold uppercase tracking-wider">
                  <FiMessageSquare size={12} className="text-pink-400" />
                  DM
                </div>
                <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-3">
                  <p className="text-xs text-slate-400 leading-relaxed">{copy.dm}</p>
                </div>
              </div>
            )}
            {copy.linkedin && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs text-slate-400 font-semibold uppercase tracking-wider">
                  <FiLinkedin size={12} className="text-cyan-400" />
                  LinkedIn
                </div>
                <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-3">
                  <p className="text-xs text-slate-400 leading-relaxed">{copy.linkedin}</p>
                </div>
              </div>
            )}
          </div>

          {/* Research */}
          {research && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs text-slate-400 font-semibold uppercase tracking-wider">
                <FiTarget size={12} className="text-orange-400" />
                Research
              </div>
              <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-3 space-y-2">
                {research.does && (
                  <p className="text-xs text-slate-500 leading-relaxed">
                    <span className="text-slate-400 font-medium">What they do: </span>{research.does}
                  </p>
                )}
                {research.hook && (
                  <p className="text-xs text-orange-400/80 leading-relaxed">
                    <span className="font-medium">Hook: </span>{research.hook}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── CRM Pipeline Board ─────────────────────────────────── */
const STAGES = [
  { id: 'new',       label: 'New',       color: 'border-blue-500/30',    dot: 'bg-blue-400' },
  { id: 'contacted', label: 'Contacted', color: 'border-yellow-500/30',  dot: 'bg-yellow-400' },
  { id: 'qualified', label: 'Qualified', color: 'border-purple-500/30',  dot: 'bg-purple-400' },
  { id: 'proposal',  label: 'Proposal',  color: 'border-orange-500/30',  dot: 'bg-orange-400' },
  { id: 'won',       label: 'Won',       color: 'border-emerald-500/30', dot: 'bg-emerald-400' },
];

function PipelineBoard({ leads, onMove }) {
  return (
    <div className="grid grid-cols-5 gap-3">
      {STAGES.map(stage => {
        const col = leads.filter(l => l.status === stage.id);
        return (
          <div key={stage.id} className={`rounded-2xl border ${stage.color} bg-white/[0.02] p-3`}>
            <div className="flex items-center gap-2 mb-3">
              <div className={`w-2 h-2 rounded-full ${stage.dot}`} />
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wide">{stage.label}</span>
              <span className="ml-auto text-xs text-slate-600 font-medium">{col.length}</span>
            </div>
            <div className="space-y-2">
              {col.map(lead => (
                <div key={lead.id}
                  className="rounded-xl bg-white/[0.04] border border-white/[0.06] p-3 group hover:border-white/[0.12] transition-all">
                  <p className="text-xs font-semibold text-white/80 truncate">{lead.name}</p>
                  <p className="text-[11px] text-slate-500 truncate mt-0.5">{lead.company}</p>
                  {lead.score > 0 && (
                    <p className="text-[11px] text-blue-400/70 mt-1">Score: {Math.round(lead.score)}</p>
                  )}
                  {/* Stage move buttons */}
                  <div className="flex gap-1 mt-2 opacity-0 group-hover:opacity-100 transition-opacity flex-wrap">
                    {STAGES.filter(s => s.id !== stage.id).map(s => (
                      <button
                        key={s.id}
                        onClick={() => onMove(lead.id, s.id)}
                        className="text-[10px] px-1.5 py-0.5 rounded-md bg-white/[0.05]
                          text-slate-500 hover:text-slate-300 border border-white/[0.06]
                          hover:border-white/[0.12] transition-all"
                      >
                        → {s.label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
              {col.length === 0 && (
                <div className="text-center py-6 text-[11px] text-slate-700">Empty</div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ─── Main Component ─────────────────────────────────────── */
export default function OutreachPipeline() {
  const [tab, setTab]                 = useState('outreach');
  const [domains, setDomains]         = useState('');
  const [running, setRunning]         = useState(false);
  const [result, setResult]           = useState(null);
  const [leads, setLeads]             = useState([]);
  const [loading, setLoading]         = useState(true);
  const [filter, setFilter]           = useState('all');
  const [stats, setStats]             = useState({ total: 0, hunter: 0, contacted: 0, pending: 0 });

  const loadLeads = useCallback(async () => {
    try {
      const all = await leadsApi.list({ limit: 200 });
      const arr = Array.isArray(all) ? all : [];
      // Show hunter/outreach leads first, all others below
      const hunter = arr.filter(l => l.source === 'hunter');
      const others = arr.filter(l => l.source !== 'hunter');
      setLeads([...hunter, ...others]);
      setStats({
        total:     arr.length,
        hunter:    hunter.length,
        contacted: arr.filter(l => l.status === 'contacted').length,
        pending:   hunter.filter(l => l.status === 'new').length,
      });
    } catch { /* non-fatal */ }
    setLoading(false);
  }, []);

  useEffect(() => { loadLeads(); }, [loadLeads]);

  async function runPipeline() {
    const domainList = domains
      .split(/[\n,\s]+/)
      .map(d => d.trim().toLowerCase().replace(/^https?:\/\//, '').replace(/\/.*$/, ''))
      .filter(Boolean);
    if (!domainList.length) return;
    setRunning(true);
    setResult(null);
    try {
      const res = await outreachApi.runPipeline({ domains: domainList });
      setResult(res);
      await loadLeads();
    } catch (e) {
      setResult({ error: e.message || 'Pipeline failed' });
    } finally { setRunning(false); }
  }

  function handleSent(leadId) {
    setLeads(prev => prev.map(l => l.id === leadId ? { ...l, status: 'contacted' } : l));
    setStats(prev => ({ ...prev, contacted: prev.contacted + 1, pending: Math.max(0, prev.pending - 1) }));
  }

  async function handleMove(leadId, newStatus) {
    setLeads(prev => prev.map(l => l.id === leadId ? { ...l, status: newStatus } : l));
    try {
      await leadsApi.update(leadId, { status: newStatus });
    } catch { /* revert on fail */
      await loadLeads();
    }
  }

  const filtered = leads.filter(l => {
    if (filter === 'outreach') return l.source === 'hunter';
    if (filter === 'pending')  return l.source === 'hunter' && l.status === 'new';
    if (filter === 'sent')     return l.status === 'contacted';
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Tab switcher */}
      <div className="flex items-center gap-1 bg-white/[0.03] rounded-2xl p-1 border border-white/[0.06] w-fit">
        {[
          { id: 'outreach', label: 'Outreach', icon: FiZap },
          { id: 'crm',      label: 'CRM Pipeline', icon: FiTarget },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200
              ${tab === id
                ? 'bg-white/[0.08] text-white border border-white/[0.1]'
                : 'text-slate-500 hover:text-slate-300'
              }`}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {/* CRM Board tab */}
      {tab === 'crm' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-500">Drag leads across stages by hovering and clicking → buttons</p>
            <button onClick={loadLeads} className="p-2 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-white/[0.05] transition-all">
              <FiRefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
          {loading ? (
            <div className="flex items-center justify-center py-20 text-slate-600">
              <FiRefreshCw size={18} className="animate-spin mr-2" /> Loading…
            </div>
          ) : (
            <PipelineBoard leads={leads} onMove={handleMove} />
          )}
        </div>
      )}

      {/* Outreach tab */}
      {tab === 'outreach' && <>
      {/* Header stats */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Total Leads',    value: stats.total,     icon: FiUser,        color: 'text-blue-400',   bg: 'bg-blue-500/10',    border: 'border-blue-500/20' },
          { label: 'From Hunter.io', value: stats.hunter,    icon: FiGlobe,       color: 'text-purple-400', bg: 'bg-purple-500/10',  border: 'border-purple-500/20' },
          { label: 'Pending Send',   value: stats.pending,   icon: FiClock,       color: 'text-yellow-400', bg: 'bg-yellow-500/10',  border: 'border-yellow-500/20' },
          { label: 'Emails Sent',    value: stats.contacted, icon: FiCheckCircle, color: 'text-emerald-400',bg: 'bg-emerald-500/10', border: 'border-emerald-500/20' },
        ].map(({ label, value, icon: Icon, color, bg, border }) => (
          <div key={label} className="rounded-2xl bg-white/[0.03] border border-white/[0.06] p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className={`p-2 rounded-xl ${bg} border ${border}`}>
                <Icon size={16} className={color} />
              </div>
            </div>
            <p className="text-2xl font-extrabold text-white">{value}</p>
            <p className="text-xs text-slate-500 mt-1 uppercase tracking-wide">{label}</p>
          </div>
        ))}
      </div>

      {/* Pipeline runner */}
      <div className="rounded-2xl bg-white/[0.03] border border-white/[0.06] p-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="p-2 rounded-xl bg-blue-500/10 border border-blue-500/20">
            <FiZap size={18} className="text-blue-400" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white/90">Run Outreach Pipeline</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Hunter.io finds named decision-maker emails · Claude researches & drafts personalized copy · follow-ups auto-queued
            </p>
          </div>
        </div>

        <div className="space-y-3">
          <textarea
            value={domains}
            onChange={e => setDomains(e.target.value)}
            placeholder="Paste company domains, one per line or comma-separated&#10;e.g. digiceljamaica.com, sagicor.com, flowjamaica.com"
            rows={4}
            className="w-full rounded-xl bg-white/[0.04] border border-white/[0.08] px-4 py-3
              text-sm text-white/90 placeholder-slate-600 resize-none
              focus:outline-none focus:border-blue-500/40 focus:bg-white/[0.06]
              transition-all duration-200"
          />

          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-600">
              Skips info@, contact@, hello@, support@ — named contacts only
            </p>
            <button
              onClick={runPipeline}
              disabled={running || !domains.trim()}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold
                bg-gradient-to-r from-blue-500 to-purple-600 text-white
                hover:from-blue-400 hover:to-purple-500 shadow-[0_0_20px_rgba(59,130,246,0.25)]
                disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
            >
              {running ? (
                <>
                  <FiRefreshCw size={14} className="animate-spin" />
                  Running Pipeline…
                </>
              ) : (
                <>
                  <FiZap size={14} />
                  Find &amp; Draft
                </>
              )}
            </button>
          </div>
        </div>

        {/* Pipeline result */}
        {result && (
          <div className={`mt-4 rounded-xl p-4 border text-sm
            ${result.error
              ? 'bg-red-500/10 border-red-500/20 text-red-400'
              : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
            }`}>
            {result.error ? (
              <div className="flex items-center gap-2">
                <FiAlertCircle size={14} />
                {result.error}
              </div>
            ) : (
              <div className="space-y-2">
                <div className="flex items-center gap-2 font-semibold">
                  <FiCheckCircle size={14} />
                  Pipeline complete — {result.queued ?? 0} lead{result.queued !== 1 ? 's' : ''} queued
                </div>
                {Array.isArray(result.leads) && result.leads.map((l, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs text-emerald-300/80 pl-5">
                    <FiMail size={11} />
                    <span className="font-medium">{l.name}</span>
                    <span className="text-emerald-500/60">·</span>
                    <span className="text-emerald-400/70">{l.subject}</span>
                  </div>
                ))}
                {result.skipped > 0 && (
                  <p className="text-xs text-slate-500 pl-5">
                    {result.skipped} skipped (no named contact found or generic email)
                  </p>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Leads list */}
      <div className="rounded-2xl bg-white/[0.03] border border-white/[0.06] p-6">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-purple-500/10 border border-purple-500/20">
              <FiTarget size={18} className="text-purple-400" />
            </div>
            <h3 className="text-sm font-bold text-white/90">Leads &amp; Outreach</h3>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={loadLeads}
              className="p-2 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-white/[0.05] transition-all"
            >
              <FiRefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            </button>

            {/* Filter tabs */}
            <div className="flex items-center gap-1 bg-white/[0.03] rounded-xl p-1 border border-white/[0.06]">
              {[
                { id: 'all',      label: 'All' },
                { id: 'outreach', label: 'Outreach' },
                { id: 'pending',  label: 'Pending' },
                { id: 'sent',     label: 'Sent' },
              ].map(({ id, label }) => (
                <button
                  key={id}
                  onClick={() => setFilter(id)}
                  className={`px-3 py-1 rounded-lg text-xs font-medium transition-all duration-200
                    ${filter === id
                      ? 'bg-white/[0.08] text-white/90'
                      : 'text-slate-500 hover:text-slate-300'
                    }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16 text-slate-600">
            <FiRefreshCw size={18} className="animate-spin mr-2" />
            Loading leads…
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-12 h-12 rounded-2xl bg-white/[0.03] border border-white/[0.06]
              flex items-center justify-center mx-auto mb-3">
              <FiSearch size={20} className="text-slate-600" />
            </div>
            <p className="text-sm text-slate-500">
              {filter === 'all' ? 'No leads yet — run the pipeline above' : `No ${filter} leads`}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map(lead => (
              <LeadCard key={lead.id} lead={lead} onSend={handleSent} />
            ))}
          </div>
        )}
      </div>
      </>}
    </div>
  );
}
