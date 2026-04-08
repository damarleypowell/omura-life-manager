/**
 * Health & Fitness Dashboard — Workouts, sleep, supplements, energy score.
 */

import React, { useState, useEffect } from 'react';
import { FiActivity, FiMoon, FiSun, FiHeart, FiZap, FiPlus } from 'react-icons/fi';
import { health as healthApi, ai } from '../../services/apiService';

function StatRing({ value, max, label, color, icon: Icon }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="stat-card">
      <div className="relative inline-flex items-center justify-center w-20 h-20 mb-2">
        <svg className="w-20 h-20 -rotate-90" viewBox="0 0 36 36">
          <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="3" />
          <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none" stroke={color} strokeWidth="3"
            strokeDasharray={`${pct}, 100`} strokeLinecap="round" />
        </svg>
        <div className="absolute">
          <Icon size={18} style={{ color }} />
        </div>
      </div>
      <p className="text-lg font-bold text-white">{value}<span className="text-xs text-slate-500">/{max}</span></p>
      <p className="text-xs text-slate-400">{label}</p>
    </div>
  );
}

const EMPTY_WORKOUT = { type: '', duration: '', intensity: 'Moderate', notes: '' };
const EMPTY_SLEEP = { hours: '', quality: 'Good', notes: '' };

export default function HealthDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null); // 'workout' | 'sleep' | null
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const entries = await healthApi.list({ days: 7 });
      setData(entries);
    } catch {
      setData({
        energy_score: 0,
        sleep: {},
        workouts: {},
        supplements: [],
        recent_workouts: [],
        sleep_log: [],
        ai_recommendation: '',
      });
    } finally { setLoading(false); }
  }

  function openWorkout() { setForm(EMPTY_WORKOUT); setModal('workout'); }
  function openSleep() { setForm(EMPTY_SLEEP); setModal('sleep'); }

  async function handleSave() {
    setSaving(true);
    try {
      const payload = modal === 'workout'
        ? { entry_type: 'workout', ...form }
        : { entry_type: 'sleep', ...form };
      await healthApi.create(payload);
      setModal(null);
      await loadData();
    } catch { /* silently handled */ } finally { setSaving(false); }
  }

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="grid grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className={`stat-card animate-fade-in-up-${i}`}>
              <div className="skeleton w-20 h-20 rounded-full mx-auto mb-2" />
              <div className="skeleton w-16 h-5 rounded mx-auto mb-1" />
              <div className="skeleton w-20 h-3 rounded mx-auto" />
            </div>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-6">
          {[1, 2].map((i) => (
            <div key={i} className="glass-card">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className="skeleton w-5 h-5 rounded" />
                  <div className="skeleton w-32 h-5 rounded" />
                </div>
                <div className="skeleton w-24 h-8 rounded-xl" />
              </div>
              {[1, 2, 3].map((j) => (
                <div key={j} className="skeleton w-full h-14 rounded-xl mb-2" />
              ))}
            </div>
          ))}
        </div>
        <div className="glass-card">
          <div className="flex items-center gap-2 mb-4">
            <div className="skeleton w-5 h-5 rounded" />
            <div className="skeleton w-36 h-5 rounded" />
          </div>
          <div className="grid grid-cols-4 gap-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="skeleton w-full h-16 rounded-xl" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  const { energy_score = 0, sleep = {}, workouts = {}, supplements = [], recent_workouts = [], sleep_log = [], ai_recommendation = '' } = data || {};

  return (
    <div className="space-y-6">
      {/* Score rings */}
      <div className="grid grid-cols-4 gap-4">
        <StatRing value={energy_score} max={100} label="Energy Score" color="#6366f1" icon={FiZap} />
        <StatRing value={sleep.score || 0} max={100} label="Sleep Score" color="#3b82f6" icon={FiMoon} />
        <StatRing value={workouts.sessions || 0} max={7} label="Workouts/Week" color="#22c55e" icon={FiActivity} />
        <StatRing value={workouts.streak || 0} max={30} label="Day Streak" color="#f59e0b" icon={FiHeart} />
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Recent Workouts */}
        <div className="glass-card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold flex items-center gap-2 text-white">
              <FiActivity className="text-emerald-400" /> Recent Workouts
            </h3>
            <button onClick={openWorkout} className="btn btn-primary text-xs"><FiPlus size={14} /> Add Entry</button>
          </div>
          {recent_workouts.length > 0 ? (
            <div className="space-y-2">
              {recent_workouts.map((w, i) => (
                <div key={i} className="glass-inner flex items-center gap-3 p-3 hover:bg-white/[0.06] transition-all">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-white">{w.type}</p>
                    <p className="text-xs text-slate-500">{w.date} &middot; {w.duration}</p>
                  </div>
                  <span className={`badge ${w.intensity === 'High' ? 'badge-danger' : w.intensity === 'Moderate' ? 'badge-warning' : 'badge-info'}`}>
                    {w.intensity}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-3">
                <FiActivity className="text-emerald-400/60" size={20} />
              </div>
              <p className="text-sm text-slate-400">No workouts logged yet</p>
              <p className="text-xs text-slate-600 mt-1">Add your first workout to start tracking</p>
            </div>
          )}
        </div>

        {/* Sleep Log */}
        <div className="glass-card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold flex items-center gap-2 text-white">
              <FiMoon className="text-blue-400" /> Sleep Log
            </h3>
            <button onClick={openSleep} className="btn btn-ghost text-xs"><FiPlus size={14} /> Log</button>
          </div>
          {sleep_log.length > 0 ? (
            <div className="space-y-2">
              {sleep_log.map((s, i) => (
                <div key={i} className="glass-inner flex items-center gap-3 p-3 hover:bg-white/[0.06] transition-all">
                  <FiMoon className="text-blue-400" size={16} />
                  <div className="flex-1">
                    <p className="text-sm text-white">{s.hours} hours</p>
                    <p className="text-xs text-slate-500">{s.date}</p>
                  </div>
                  <span className={`badge ${s.quality === 'Excellent' ? 'badge-success' : s.quality === 'Good' ? 'badge-info' : 'badge-warning'}`}>
                    {s.quality}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <div className="w-12 h-12 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mx-auto mb-3">
                <FiMoon className="text-blue-400/60" size={20} />
              </div>
              <p className="text-sm text-slate-400">No sleep data yet</p>
              <p className="text-xs text-slate-600 mt-1">Log your sleep to track patterns</p>
            </div>
          )}
        </div>
      </div>

      {/* Supplements */}
      <div className="glass-card">
        <h3 className="font-semibold mb-4 flex items-center gap-2 text-white">
          <FiSun className="text-amber-400" /> Today's Supplements
        </h3>
        {supplements.length > 0 ? (
          <div className="grid grid-cols-4 gap-3">
            {supplements.map((s, i) => (
              <div key={i} className={`glass-inner p-3 transition-all ${s.taken ? 'border-emerald-500/30 bg-emerald-500/5' : ''}`}>
                <div className="flex items-center gap-2 mb-1">
                  <div className={`w-3 h-3 rounded-full ${s.taken ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                  <p className="text-sm font-medium text-white">{s.name}</p>
                </div>
                <p className="text-xs text-slate-400">{s.dose} &middot; {s.time}</p>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <div className="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto mb-3">
              <FiSun className="text-amber-400/60" size={20} />
            </div>
            <p className="text-sm text-slate-400">No supplements tracked</p>
            <p className="text-xs text-slate-600 mt-1">Add your supplement stack to track daily intake</p>
          </div>
        )}
      </div>

      {/* AI Recommendation */}
      <div className="glass-card">
        <h3 className="font-semibold mb-3 flex items-center gap-2 text-white">
          <FiZap className="text-blue-400" /> AI Health Recommendation
          <span className="badge badge-accent ml-2">AI Generated</span>
        </h3>
        {ai_recommendation ? (
          <div className="glass-inner p-4 text-sm leading-relaxed text-slate-300 border-blue-500/10 bg-blue-500/5">
            {ai_recommendation}
          </div>
        ) : (
          <div className="text-center py-8">
            <p className="text-sm text-slate-500">Log health data to receive AI-powered recommendations</p>
          </div>
        )}
      </div>

      {/* ── Health Entry Modal ── */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="glass-card w-full max-w-md p-7 rounded-2xl border border-white/[0.10] shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-5">
              {modal === 'workout' ? 'Log Workout' : 'Log Sleep'}
            </h3>
            <div className="space-y-4">
              {modal === 'workout' ? (
                <>
                  <input
                    type="text"
                    placeholder="Workout type (e.g. Running, Weightlifting)"
                    value={form.type || ''}
                    onChange={(e) => setForm((f) => ({ ...f, type: e.target.value }))}
                    className="glass-input w-full h-11 rounded-xl px-4 bg-white/[0.05] border border-white/[0.08] text-white placeholder-slate-500 focus:border-emerald-500/50 transition-all"
                  />
                  <input
                    type="text"
                    placeholder="Duration (e.g. 45 min)"
                    value={form.duration || ''}
                    onChange={(e) => setForm((f) => ({ ...f, duration: e.target.value }))}
                    className="glass-input w-full h-11 rounded-xl px-4 bg-white/[0.05] border border-white/[0.08] text-white placeholder-slate-500 focus:border-emerald-500/50 transition-all"
                  />
                  <select
                    value={form.intensity || 'Moderate'}
                    onChange={(e) => setForm((f) => ({ ...f, intensity: e.target.value }))}
                    className="glass-input w-full h-11 rounded-xl px-4 bg-white/[0.05] border border-white/[0.08] text-white focus:border-emerald-500/50 transition-all"
                  >
                    <option value="Low">Low</option>
                    <option value="Moderate">Moderate</option>
                    <option value="High">High</option>
                  </select>
                </>
              ) : (
                <>
                  <input
                    type="number"
                    placeholder="Hours slept"
                    value={form.hours || ''}
                    onChange={(e) => setForm((f) => ({ ...f, hours: e.target.value }))}
                    className="glass-input w-full h-11 rounded-xl px-4 bg-white/[0.05] border border-white/[0.08] text-white placeholder-slate-500 focus:border-blue-500/50 transition-all"
                    min="0" max="24" step="0.5"
                  />
                  <select
                    value={form.quality || 'Good'}
                    onChange={(e) => setForm((f) => ({ ...f, quality: e.target.value }))}
                    className="glass-input w-full h-11 rounded-xl px-4 bg-white/[0.05] border border-white/[0.08] text-white focus:border-blue-500/50 transition-all"
                  >
                    <option value="Poor">Poor</option>
                    <option value="Fair">Fair</option>
                    <option value="Good">Good</option>
                    <option value="Excellent">Excellent</option>
                  </select>
                </>
              )}
              <input
                type="text"
                placeholder="Notes (optional)"
                value={form.notes || ''}
                onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                className="glass-input w-full h-11 rounded-xl px-4 bg-white/[0.05] border border-white/[0.08] text-white placeholder-slate-500 focus:border-blue-500/50 transition-all"
              />
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setModal(null)} className="btn btn-ghost rounded-xl px-5">Cancel</button>
              <button onClick={handleSave} disabled={saving} className="btn btn-primary rounded-xl px-6">
                {saving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
