/**
 * Content Studio — Drafts, schedules, performance analytics.
 */

import React, { useState, useEffect } from 'react';
import { FiEdit3, FiCalendar, FiBarChart2, FiPlus, FiInstagram, FiYoutube, FiFacebook, FiX, FiSave } from 'react-icons/fi';
import { dashboard, content as contentApi, ai } from '../../services/apiService';
import { notifySuccess, notifyError } from '../Shared/Notifications';

const PLATFORM_ICONS  = { instagram: FiInstagram, youtube: FiYoutube, facebook: FiFacebook, tiktok: FiEdit3 };
const PLATFORM_COLORS = { instagram: 'text-pink-400', youtube: 'text-red-400', facebook: 'text-blue-400', tiktok: 'text-cyan-400' };
const STATUS_STYLES   = { idea: 'badge-info', draft: 'badge-accent', review: 'badge-warning', scheduled: 'badge-success', published: 'badge-success' };
const PLATFORMS       = ['instagram', 'tiktok', 'youtube', 'facebook'];

function ContentCard({ item, onStatusChange, onDelete }) {
  const PlatformIcon = PLATFORM_ICONS[item.platform] || FiEdit3;
  const platformColor = PLATFORM_COLORS[item.platform] || 'text-slate-400';
  const nextStatus = { idea: 'draft', draft: 'review', review: 'scheduled', scheduled: 'published' };

  return (
    <div className="p-4 rounded-xl glass-inner group">
      <div className="flex items-center gap-2 mb-2">
        <PlatformIcon size={13} className={platformColor} />
        <span className={`badge ${STATUS_STYLES[item.status] || 'badge-info'}`}>{item.status}</span>
        {item.scheduled_at && (
          <span className="text-[11px] text-slate-500 ml-auto">
            {new Date(item.scheduled_at).toLocaleDateString()}
          </span>
        )}
      </div>
      <p className="text-sm font-medium text-white/90 mb-1 group-hover:text-white transition-colors">{item.title}</p>
      {item.caption && <p className="text-xs text-slate-500 line-clamp-2 mb-2">{item.caption}</p>}
      {item.hashtags?.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {item.hashtags.slice(0, 4).map((tag, i) => (
            <span key={i} className="text-[11px] text-blue-400/70">#{tag}</span>
          ))}
        </div>
      )}
      <div className="flex gap-1.5 mt-2">
        {nextStatus[item.status] && (
          <button
            onClick={() => onStatusChange(item.id, nextStatus[item.status])}
            className="text-[11px] bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06] text-slate-400 hover:text-white px-2 py-1 rounded-lg transition-all flex-1"
          >
            → {nextStatus[item.status]}
          </button>
        )}
        <button
          onClick={() => onDelete(item.id)}
          className="text-[11px] text-red-400/60 hover:text-red-400 px-2 py-1 rounded-lg transition-colors"
        >
          <FiX size={11} />
        </button>
      </div>
    </div>
  );
}

function CreateModal({ onClose, onSaved }) {
  const [form, setForm] = useState({ title: '', platform: 'instagram', caption: '', hashtags: '', status: 'idea' });
  const [saving, setSaving] = useState(false);

  async function handleSave() {
    if (!form.title.trim()) return;
    setSaving(true);
    try {
      await contentApi.create({
        title: form.title.trim(),
        platform: form.platform,
        caption: form.caption.trim() || null,
        hashtags: form.hashtags ? form.hashtags.split(',').map(t => t.trim().replace(/^#/, '')).filter(Boolean) : [],
        status: form.status,
      });
      notifySuccess('Content item created');
      onSaved();
    } catch { notifyError('Failed to create content'); }
    finally { setSaving(false); }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="glass-card w-full max-w-md mx-4 shadow-2xl">
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-bold text-white">New Content Item</h3>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors"><FiX size={18} /></button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Title *</label>
            <input
              type="text" placeholder="Content title..."
              value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              className="glass-input"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Platform</label>
              <select value={form.platform} onChange={e => setForm(f => ({ ...f, platform: e.target.value }))} className="glass-input">
                {PLATFORMS.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Status</label>
              <select value={form.status} onChange={e => setForm(f => ({ ...f, status: e.target.value }))} className="glass-input">
                {['idea', 'draft', 'review', 'scheduled'].map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Caption</label>
            <textarea
              rows={3} placeholder="Write your caption..."
              value={form.caption} onChange={e => setForm(f => ({ ...f, caption: e.target.value }))}
              className="glass-input resize-none"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Hashtags (comma-separated)</label>
            <input
              type="text" placeholder="ai, productivity, business"
              value={form.hashtags} onChange={e => setForm(f => ({ ...f, hashtags: e.target.value }))}
              className="glass-input"
            />
          </div>
        </div>
        <div className="flex gap-3 mt-5">
          <button onClick={onClose} className="btn btn-ghost flex-1 justify-center">Cancel</button>
          <button onClick={handleSave} disabled={saving || !form.title.trim()} className="btn btn-primary flex-1 justify-center">
            <FiSave size={14} /> {saving ? 'Saving...' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ContentStudio() {
  const [pipeline, setPipeline]       = useState([]);
  const [loading, setLoading]         = useState(true);
  const [generating, setGenerating]   = useState(false);
  const [showCreate, setShowCreate]   = useState(false);

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const result = await dashboard.getContentStudio();
      setPipeline(result.pipeline || []);
    } catch { setPipeline([]); }
    finally { setLoading(false); }
  }

  async function handleGenerateIdea() {
    setGenerating(true);
    try {
      const res = await ai.execute('content', 'suggest_content_ideas', {
        recent_trends: ['AI tools', 'remote work', 'productivity', 'personal branding'],
      });
      const ideas = res?.result?.ideas || res?.ideas || [];

      // Save each AI-generated idea as a content item in DB
      await Promise.all(
        ideas.slice(0, 3).map((idea) =>
          contentApi.create({
            title: idea.title,
            platform: idea.suggested_platform || 'instagram',
            caption: idea.description || '',
            hashtags: [],
            status: 'idea',
          })
        )
      );
      notifySuccess(`${Math.min(ideas.length, 3)} content ideas generated`);
      await loadData();
    } catch {
      // Fallback: create a single mock idea
      try {
        await contentApi.create({
          title: 'New Content Idea — ' + new Date().toLocaleDateString(),
          platform: 'tiktok',
          caption: 'AI-generated content idea',
          hashtags: ['ai', 'automation'],
          status: 'idea',
        });
        notifySuccess('Content idea created');
        await loadData();
      } catch { notifyError('Failed to generate ideas'); }
    } finally { setGenerating(false); }
  }

  async function handleStatusChange(id, newStatus) {
    try {
      await contentApi.update(id, { status: newStatus });
      await loadData();
      notifySuccess(`Moved to ${newStatus}`);
    } catch { notifyError('Failed to update status'); }
  }

  async function handleDelete(id) {
    try {
      await contentApi.delete(id);
      await loadData();
      notifySuccess('Deleted');
    } catch { notifyError('Failed to delete'); }
  }

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="grid grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="stat-card">
              <div className="skeleton w-12 h-7 rounded-lg mx-auto mb-2" />
              <div className="skeleton w-16 h-3 rounded mx-auto" />
            </div>
          ))}
        </div>
        <div className="flex gap-3">
          <div className="skeleton w-40 h-10 rounded-xl" />
          <div className="skeleton w-32 h-10 rounded-xl" />
          <div className="skeleton w-28 h-10 rounded-xl" />
        </div>
        <div className="grid grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="glass-card">
              <div className="flex items-center gap-2 mb-3">
                <div className="skeleton w-2 h-2 rounded-full" />
                <div className="skeleton w-16 h-4 rounded" />
              </div>
              <div className="space-y-3">
                {[1, 2].map((j) => <div key={j} className="skeleton w-full h-24 rounded-xl" />)}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const grouped = {
    idea:      pipeline.filter(c => c.status === 'idea'),
    draft:     pipeline.filter(c => c.status === 'draft'),
    review:    pipeline.filter(c => c.status === 'review'),
    scheduled: pipeline.filter(c => c.status === 'scheduled'),
  };

  const columnMeta = {
    idea:      { label: 'Ideas',     dot: 'bg-blue-400'   },
    draft:     { label: 'Drafts',    dot: 'bg-purple-400' },
    review:    { label: 'In Review', dot: 'bg-amber-400'  },
    scheduled: { label: 'Scheduled', dot: 'bg-emerald-400'},
  };

  return (
    <>
      {showCreate && (
        <CreateModal onClose={() => setShowCreate(false)} onSaved={() => { setShowCreate(false); loadData(); }} />
      )}

      <div className="space-y-6 animate-fade-in">
        {/* Stats */}
        <div className="grid grid-cols-4 gap-4">
          {[
            { value: grouped.idea.length,      label: 'Ideas',      color: 'text-blue-400' },
            { value: grouped.draft.length,     label: 'Drafts',     color: 'text-purple-400' },
            { value: grouped.review.length,    label: 'In Review',  color: 'text-amber-400' },
            { value: grouped.scheduled.length, label: 'Scheduled',  color: 'text-emerald-400' },
          ].map((stat, i) => (
            <div key={i} className="stat-card">
              <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
              <p className="text-xs text-slate-500 mt-1">{stat.label}</p>
            </div>
          ))}
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button className="btn btn-primary hover-glow-purple" onClick={handleGenerateIdea} disabled={generating}>
            <FiPlus size={15} />
            {generating ? 'Generating...' : 'AI Generate Ideas'}
          </button>
          <button className="btn btn-ghost" onClick={() => setShowCreate(true)}>
            <FiEdit3 size={15} /> Create Manually
          </button>
          <button className="btn btn-ghost">
            <FiBarChart2 size={15} /> Analytics
          </button>
        </div>

        {/* Kanban pipeline */}
        <div className="grid grid-cols-4 gap-4">
          {['idea', 'draft', 'review', 'scheduled'].map((status) => (
            <div key={status} className="glass-card">
              <div className="flex items-center gap-2 mb-3">
                <div className={`w-2 h-2 rounded-full ${columnMeta[status].dot}`} />
                <h3 className="font-semibold text-sm text-white">{columnMeta[status].label}</h3>
                <span className="text-xs text-slate-500 ml-auto">{grouped[status].length}</span>
              </div>
              <div className="space-y-3">
                {grouped[status].map((item) => (
                  <ContentCard
                    key={item.id} item={item}
                    onStatusChange={handleStatusChange}
                    onDelete={handleDelete}
                  />
                ))}
                {grouped[status].length === 0 && (
                  <div className="text-center py-8">
                    <div className="w-10 h-10 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center mx-auto mb-3">
                      <FiEdit3 className="text-slate-600" size={15} />
                    </div>
                    <p className="text-xs text-slate-500">No items</p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
