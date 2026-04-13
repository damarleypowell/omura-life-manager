/**
 * Knowledge Hub — Notes, research, strategy summaries.
 * Premium dark glassmorphism design.
 */

import React, { useState, useEffect } from 'react';
import { FiBook, FiPlus, FiSearch, FiTag, FiEdit2, FiTrash2 } from 'react-icons/fi';
import { notes as notesApi } from '../../services/apiService';

// Lightweight markdown renderer — no external dependency
function MarkdownBlock({ text }) {
  if (!text) return null;
  const lines = text.split('\n');
  const elements = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (/^### /.test(line)) {
      elements.push(<h3 key={i} className="text-base font-bold text-white mt-4 mb-1">{inline(line.slice(4))}</h3>);
    } else if (/^## /.test(line)) {
      elements.push(<h2 key={i} className="text-lg font-bold text-white mt-5 mb-2">{inline(line.slice(3))}</h2>);
    } else if (/^# /.test(line)) {
      elements.push(<h1 key={i} className="text-xl font-bold text-white mt-5 mb-2">{inline(line.slice(2))}</h1>);
    } else if (/^---+$/.test(line.trim())) {
      elements.push(<hr key={i} className="border-white/10 my-3" />);
    } else if (/^[-*] /.test(line)) {
      elements.push(<li key={i} className="ml-4 list-disc text-slate-300">{inline(line.slice(2))}</li>);
    } else if (/^\d+\. /.test(line)) {
      elements.push(<li key={i} className="ml-4 list-decimal text-slate-300">{inline(line.replace(/^\d+\. /, ''))}</li>);
    } else if (line.trim() === '') {
      elements.push(<div key={i} className="h-2" />);
    } else {
      elements.push(<p key={i} className="text-slate-300 leading-relaxed">{inline(line)}</p>);
    }
    i++;
  }
  return <div className="space-y-0.5">{elements}</div>;
}

function inline(text) {
  // **bold**, *italic*, `code`
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g);
  return parts.map((p, i) => {
    if (/^\*\*.*\*\*$/.test(p)) return <strong key={i} className="text-white font-semibold">{p.slice(2, -2)}</strong>;
    if (/^\*.*\*$/.test(p)) return <em key={i} className="italic text-slate-200">{p.slice(1, -1)}</em>;
    if (/^`.*`$/.test(p)) return <code key={i} className="bg-white/10 px-1 rounded text-xs font-mono text-blue-300">{p.slice(1, -1)}</code>;
    return p;
  });
}

const CATEGORY_COLORS = {
  research: 'badge-info',
  strategy: 'badge-accent',
  idea: 'badge-warning',
  meeting_notes: 'badge-success',
};

const CATEGORY_GLOW = {
  research: 'from-blue-500/20 to-cyan-500/20',
  strategy: 'from-violet-500/20 to-purple-500/20',
  idea: 'from-amber-500/20 to-yellow-500/20',
  meeting_notes: 'from-emerald-500/20 to-green-500/20',
};

function NoteCardSkeleton({ index }) {
  return (
    <div className={`glass-inner rounded-2xl p-5 animate-pulse animate-fade-in-up-${index + 1}`}>
      <div className="flex items-center gap-2 mb-3">
        <div className="h-5 w-16 bg-white/10 rounded-full" />
      </div>
      <div className="h-4 w-3/4 bg-white/10 rounded-lg mb-2" />
      <div className="h-3 w-full bg-white/[0.06] rounded-lg mb-1" />
      <div className="h-3 w-2/3 bg-white/[0.06] rounded-lg" />
      <div className="flex gap-2 mt-3">
        <div className="h-5 w-14 bg-white/[0.06] rounded-full" />
        <div className="h-5 w-12 bg-white/[0.06] rounded-full" />
      </div>
    </div>
  );
}

function NoteCard({ note, onSelect, isSelected, animIndex }) {
  return (
    <div
      onClick={() => onSelect(note)}
      className={`glass-inner rounded-2xl p-5 cursor-pointer transition-all duration-300 group animate-fade-in-up-${animIndex}
        ${isSelected
          ? 'bg-white/[0.10] border border-blue-500/40 shadow-lg shadow-blue-500/10'
          : 'hover:bg-white/[0.07] hover:shadow-lg hover:shadow-white/5 hover:-translate-y-0.5 border border-transparent'
        }`}
    >
      <div className="flex items-center gap-2 mb-3">
        <span className={`badge ${CATEGORY_COLORS[note.category] || 'badge-info'}`}>
          {(note.category || 'general').replace('_', ' ')}
        </span>
      </div>
      <h4 className="text-sm font-semibold text-white group-hover:text-blue-300 transition-colors">
        {note.title}
      </h4>
      <p className="text-xs text-slate-400 mt-2 line-clamp-2 leading-relaxed">{note.content}</p>
      {note.tags && note.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {note.tags.map((tag, i) => (
            <span
              key={i}
              className="bg-white/[0.08] text-[11px] px-2.5 py-1 rounded-full text-slate-400 flex items-center gap-1 hover:bg-white/[0.12] transition-colors"
            >
              <FiTag size={9} /> {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

const EMPTY_FORM = { title: '', content: '', category: 'idea', tags: '' };

export default function KnowledgeHub() {
  const [notesList, setNotesList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedNote, setSelectedNote] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterCategory, setFilterCategory] = useState('all');
  const [showModal, setShowModal] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const result = await notesApi.list();
      setNotesList(Array.isArray(result) ? result : []);
    } catch {
      setNotesList([]);
    } finally { setLoading(false); }
  }

  function openNew() {
    setForm(EMPTY_FORM);
    setEditMode(false);
    setShowModal(true);
  }

  function openEdit(note) {
    setForm({ title: note.title, content: note.content, category: note.category || 'idea', tags: (note.tags || []).join(', ') });
    setEditMode(true);
    setShowModal(true);
  }

  async function handleSave() {
    if (!form.title.trim()) return;
    setSaving(true);
    try {
      const payload = {
        title: form.title.trim(),
        content: form.content.trim(),
        category: form.category,
        tags: form.tags.split(',').map((t) => t.trim()).filter(Boolean),
      };
      if (editMode && selectedNote) {
        await notesApi.update(selectedNote.id, payload);
      } else {
        await notesApi.create(payload);
      }
      setShowModal(false);
      setSelectedNote(null);
      await loadData();
    } catch { /* silently handled */ } finally { setSaving(false); }
  }

  async function handleDelete(note) {
    if (!window.confirm(`Delete "${note.title}"?`)) return;
    setDeleting(true);
    try {
      await notesApi.delete(note.id);
      setSelectedNote(null);
      await loadData();
    } catch { /* silently handled */ } finally { setDeleting(false); }
  }

  const filtered = notesList.filter((n) => {
    const matchesSearch = !searchQuery ||
      n.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (n.content && n.content.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesCategory = filterCategory === 'all' || n.category === filterCategory;
    return matchesSearch && matchesCategory;
  });

  /* ── Loading skeleton ── */
  if (loading) {
    return (
      <div className="space-y-7">
        {/* Skeleton controls */}
        <div className="flex items-center gap-4 animate-pulse">
          <div className="h-11 flex-1 max-w-md bg-white/[0.06] rounded-xl" />
          <div className="flex gap-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-8 w-16 bg-white/[0.06] rounded-lg" />
            ))}
          </div>
          <div className="h-10 w-28 bg-white/[0.06] rounded-xl" />
        </div>
        <div className="grid grid-cols-3 gap-6">
          <div className="col-span-1 space-y-4">
            {[0, 1, 2, 3].map((i) => (
              <NoteCardSkeleton key={i} index={i} />
            ))}
          </div>
          <div className="col-span-2 glass-card rounded-[20px] p-7 animate-pulse">
            <div className="flex items-center justify-center h-96 text-slate-600 text-sm">
              <div className="h-5 w-48 bg-white/[0.06] rounded-lg" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-7">
      {/* ── Controls ── */}
      <div className="flex items-center gap-4 animate-fade-in-up-1">
        <div className="relative flex-1 max-w-md">
          <FiSearch className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
          <input
            type="text"
            placeholder="Search notes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="glass-input pl-11 h-11 rounded-xl w-full bg-white/[0.04] border border-white/[0.08] text-white placeholder-slate-500 focus:border-blue-500/40 focus:bg-white/[0.06] transition-all duration-300"
          />
        </div>
        <div className="flex gap-1.5 bg-white/[0.04] rounded-xl p-1 border border-white/[0.06]">
          {['all', 'research', 'strategy', 'idea', 'meeting_notes'].map((cat) => (
            <button
              key={cat}
              onClick={() => setFilterCategory(cat)}
              className={`px-3.5 py-1.5 text-xs font-medium capitalize rounded-lg transition-all duration-300
                ${filterCategory === cat
                  ? 'bg-white/[0.12] text-white shadow-sm'
                  : 'text-slate-400 hover:text-white hover:bg-white/[0.06]'
                }`}
            >
              {cat === 'all' ? 'All' : cat.replace('_', ' ')}
            </button>
          ))}
        </div>
        <button onClick={openNew} className="btn btn-primary rounded-xl px-5 h-10 flex items-center gap-2 font-medium">
          <FiPlus size={16} /> New Note
        </button>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* ── Notes List ── */}
        <div className="col-span-1 space-y-4 max-h-[650px] overflow-y-auto pr-2 custom-scrollbar">
          {filtered.length > 0 ? (
            filtered.map((note, i) => (
              <NoteCard
                key={note.id}
                note={note}
                onSelect={setSelectedNote}
                isSelected={selectedNote?.id === note.id}
                animIndex={(i % 5) + 1}
              />
            ))
          ) : notesList.length === 0 ? (
            /* True empty — no notes exist at all */
            <div className="empty-state flex flex-col items-center justify-center py-16 text-center animate-fade-in-up-1">
              <div className="empty-state-icon w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500/20 to-violet-500/20 flex items-center justify-center mb-5 border border-white/[0.08]">
                <FiBook className="text-blue-400" size={28} />
              </div>
              <p className="text-sm font-medium text-slate-300 mb-1">No notes yet</p>
              <p className="text-xs text-slate-500 max-w-[200px] leading-relaxed">
                Start capturing your thoughts, research, and strategies
              </p>
            </div>
          ) : (
            /* Notes exist but search/filter returned nothing */
            <div className="empty-state flex flex-col items-center justify-center py-16 text-center animate-fade-in-up-1">
              <div className="empty-state-icon w-14 h-14 rounded-2xl bg-white/[0.06] flex items-center justify-center mb-4 border border-white/[0.06]">
                <FiSearch className="text-slate-500" size={22} />
              </div>
              <p className="text-sm text-slate-400">No notes match your search</p>
              <p className="text-xs text-slate-600 mt-1">Try a different keyword or filter</p>
            </div>
          )}
        </div>

        {/* ── Note Detail Pane ── */}
        <div className="col-span-2 glass-card rounded-[20px] p-7 animate-fade-in-up-2">
          {selectedNote ? (
            <div>
              <div className="flex items-start justify-between mb-6">
                <div>
                  <span className={`badge ${CATEGORY_COLORS[selectedNote.category] || 'badge-info'} mb-3`}>
                    {(selectedNote.category || 'general').replace('_', ' ')}
                  </span>
                  <h2 className="text-xl font-bold text-white tracking-tight">{selectedNote.title}</h2>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => openEdit(selectedNote)} className="btn btn-ghost text-xs rounded-xl px-4 py-2 hover:bg-white/[0.08] transition-all">
                    <FiEdit2 size={14} /> Edit
                  </button>
                  <button onClick={() => handleDelete(selectedNote)} disabled={deleting} className="btn btn-ghost text-xs rounded-xl px-3 py-2 text-red-400 hover:bg-red-500/10 transition-all">
                    <FiTrash2 size={14} />
                  </button>
                </div>
              </div>
              <div
                className={`glass-inner rounded-2xl p-6 text-sm bg-gradient-to-br ${CATEGORY_GLOW[selectedNote.category] || 'from-white/[0.02] to-white/[0.01]'} border border-white/[0.06]`}
              >
                <MarkdownBlock text={selectedNote.content} />
              </div>
              {selectedNote.tags && selectedNote.tags.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-5">
                  {selectedNote.tags.map((tag, i) => (
                    <span
                      key={i}
                      className="bg-white/[0.08] text-xs px-3 py-1.5 rounded-full text-slate-400 flex items-center gap-1.5 hover:bg-white/[0.12] transition-colors cursor-default"
                    >
                      <FiTag size={10} /> {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="empty-state flex flex-col items-center justify-center h-96 text-center">
              <div className="empty-state-icon w-20 h-20 rounded-3xl bg-gradient-to-br from-white/[0.04] to-white/[0.02] flex items-center justify-center mb-6 border border-white/[0.06]">
                <FiBook className="text-slate-500" size={32} />
              </div>
              <p className="text-sm font-medium text-slate-400 mb-1">Select a note to view</p>
              <p className="text-xs text-slate-600">Click on any note from the list to see its details</p>
            </div>
          )}
        </div>
      </div>

      {/* ── New / Edit Note Modal ── */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="glass-card w-full max-w-lg p-7 rounded-2xl border border-white/[0.10] shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-5">{editMode ? 'Edit Note' : 'New Note'}</h3>
            <div className="space-y-4">
              <input
                type="text"
                placeholder="Title"
                value={form.title}
                onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                className="glass-input w-full h-11 rounded-xl px-4 bg-white/[0.05] border border-white/[0.08] text-white placeholder-slate-500 focus:border-blue-500/50 transition-all"
              />
              <select
                value={form.category}
                onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
                className="glass-input w-full h-11 rounded-xl px-4 bg-white/[0.05] border border-white/[0.08] text-white focus:border-blue-500/50 transition-all"
              >
                <option value="idea">Idea</option>
                <option value="research">Research</option>
                <option value="strategy">Strategy</option>
                <option value="meeting_notes">Meeting Notes</option>
              </select>
              <textarea
                placeholder="Content..."
                value={form.content}
                onChange={(e) => setForm((f) => ({ ...f, content: e.target.value }))}
                rows={5}
                className="glass-input w-full rounded-xl px-4 py-3 bg-white/[0.05] border border-white/[0.08] text-white placeholder-slate-500 focus:border-blue-500/50 transition-all resize-none"
              />
              <input
                type="text"
                placeholder="Tags (comma-separated)"
                value={form.tags}
                onChange={(e) => setForm((f) => ({ ...f, tags: e.target.value }))}
                className="glass-input w-full h-11 rounded-xl px-4 bg-white/[0.05] border border-white/[0.08] text-white placeholder-slate-500 focus:border-blue-500/50 transition-all"
              />
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowModal(false)} className="btn btn-ghost rounded-xl px-5">Cancel</button>
              <button onClick={handleSave} disabled={saving || !form.title.trim()} className="btn btn-primary rounded-xl px-6">
                {saving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
