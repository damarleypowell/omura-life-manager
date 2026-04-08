/**
 * Life Overview — Calendar, to-dos, habits, AI-prioritized daily agenda.
 */

import React, { useState, useEffect } from 'react';
import {
  FiCalendar, FiCheckSquare, FiClock, FiStar, FiAlertCircle,
  FiZap, FiSunrise, FiCheck, FiRefreshCw,
} from 'react-icons/fi';
import { dashboard, tasks as tasksApi, calendar as calendarApi, ai } from '../../services/apiService';
import { notifySuccess, notifyError } from '../Shared/Notifications';

function AgendaItem({ item, type, onComplete }) {
  const icons  = { event: FiCalendar, task: FiCheckSquare, overdue: FiAlertCircle };
  const colors = { event: 'text-blue-400', task: 'text-purple-400', overdue: 'text-red-400' };
  const bgColors = { event: 'bg-blue-500/10', task: 'bg-purple-500/10', overdue: 'bg-red-500/10' };
  const Icon = icons[type] || FiClock;

  return (
    <div className="flex items-center gap-3 p-3.5 rounded-xl glass-inner group">
      <div className={`p-2.5 rounded-lg ${bgColors[type] || 'bg-white/5'}`}>
        <Icon className={colors[type] || 'text-slate-400'} size={16} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white/90 truncate group-hover:text-white transition-colors">
          {item.title}
        </p>
        {item.time && <p className="text-xs text-slate-500 mt-0.5">{item.time}</p>}
        {item.due_date && !item.time && (
          <p className="text-xs text-slate-500 mt-0.5">{new Date(item.due_date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
        )}
      </div>
      {item.priority && (
        <span className={`badge ${item.priority === 'critical' ? 'badge-danger' : item.priority === 'high' ? 'badge-warning' : 'badge-info'}`}>
          {item.priority}
        </span>
      )}
      {(type === 'task' || type === 'overdue') && onComplete && (
        <button
          onClick={() => onComplete(item.id)}
          title="Mark complete"
          className="w-7 h-7 rounded-lg bg-emerald-500/10 border border-emerald-500/20 hover:bg-emerald-500/30 flex items-center justify-center transition-all flex-shrink-0"
        >
          <FiCheck className="text-emerald-400" size={12} />
        </button>
      )}
    </div>
  );
}

function StatSkeleton() {
  return (
    <div className="stat-card">
      <div className="skeleton w-8 h-8 rounded-xl mx-auto mb-3" />
      <div className="skeleton w-14 h-8 rounded-lg mx-auto mb-2" />
      <div className="skeleton w-20 h-3 rounded mx-auto" />
    </div>
  );
}

function ListSkeleton({ rows = 3 }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 p-3.5 rounded-xl glass-inner">
          <div className="skeleton w-10 h-10 rounded-lg flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <div className="skeleton w-3/4 h-4 rounded" />
            <div className="skeleton w-1/3 h-3 rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}

function EmptyState({ icon: Icon, color, message }) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">
        <Icon className={color || 'text-slate-500'} size={22} />
      </div>
      <p>{message}</p>
    </div>
  );
}

export default function LifeOverview() {
  const [data, setData]           = useState(null);
  const [loading, setLoading]     = useState(true);
  const [agenda, setAgenda]       = useState(null);
  const [agendaLoading, setAgendaLoading] = useState(false);
  const [completingTask, setCompletingTask] = useState(null);

  useEffect(() => { loadData(); }, []);

  async function loadData() {
    try {
      const result = await dashboard.getLifeOverview();
      setData(result);
      loadAgenda();
    } catch {
      setData({ todays_events: [], tasks_today: [], overdue_tasks: [], health_entries: [] });
    } finally { setLoading(false); }
  }

  async function loadAgenda() {
    setAgendaLoading(true);
    try {
      const result = await ai.execute('project', 'generate_daily_agenda', {});
      setAgenda(result?.result || result);
    } catch {
      setAgenda(null);
    } finally { setAgendaLoading(false); }
  }

  async function handleCompleteTask(taskId) {
    setCompletingTask(taskId);
    try {
      await tasksApi.update(taskId, { status: 'done' });
      notifySuccess('Task marked complete');
      await loadData();
    } catch {
      notifyError('Failed to complete task');
    } finally { setCompletingTask(null); }
  }

  async function handleAddTask() {
    const title = window.prompt('Task title:');
    if (!title?.trim()) return;
    const dueInput = window.prompt('Due date & time (e.g. "today 3pm" or "2026-04-09T15:00") — leave blank for end of today:');
    let due_date;
    if (dueInput?.trim()) {
      const parsed = new Date(dueInput.trim());
      due_date = isNaN(parsed.getTime()) ? new Date().setHours(23, 59, 0, 0) : parsed.toISOString();
    } else {
      const eod = new Date(); eod.setHours(23, 59, 0, 0);
      due_date = eod.toISOString();
    }
    // Optimistic update — show immediately
    const temp = { id: `temp-${Date.now()}`, title: title.trim(), due_date, priority: 'medium' };
    setData((prev) => ({ ...prev, tasks_today: [...(prev?.tasks_today || []), temp] }));
    try {
      await tasksApi.create({ title: title.trim(), due_date });
      notifySuccess('Task added');
      await loadData();
    } catch {
      // Rollback optimistic update
      setData((prev) => ({ ...prev, tasks_today: (prev?.tasks_today || []).filter((t) => t.id !== temp.id) }));
      notifyError('Failed to create task');
    }
  }

  async function handleAddEvent() {
    const title = window.prompt('Event name:');
    if (!title?.trim()) return;
    const timeInput = window.prompt('Start time (e.g. "9am", "14:30") — leave blank for now:');
    let start_time = new Date();
    if (timeInput?.trim()) {
      const [h, m] = timeInput.trim().replace('am','').replace('pm','').split(':').map(Number);
      const isPm = timeInput.toLowerCase().includes('pm') && h !== 12;
      const isAm = timeInput.toLowerCase().includes('am') && h === 12;
      start_time.setHours(isPm ? h + 12 : isAm ? 0 : h, m || 0, 0, 0);
    }
    const end_time = new Date(start_time.getTime() + 3600000);
    // Optimistic update
    const temp = {
      id: `temp-${Date.now()}`,
      title: title.trim(),
      start_time: start_time.toISOString(),
      end_time: end_time.toISOString(),
      time: start_time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setData((prev) => ({ ...prev, todays_events: [...(prev?.todays_events || []), temp] }));
    try {
      await calendarApi.create({ title: title.trim(), start_time: start_time.toISOString(), end_time: end_time.toISOString() });
      notifySuccess('Event added');
      await loadData();
    } catch {
      setData((prev) => ({ ...prev, todays_events: (prev?.todays_events || []).filter((e) => e.id !== temp.id) }));
      notifyError('Failed to create event');
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-4 gap-5">
          <StatSkeleton /><StatSkeleton /><StatSkeleton /><StatSkeleton />
        </div>
        <div className="grid grid-cols-2 gap-6">
          <div className="glass-card p-7"><div className="flex items-center gap-3 mb-5"><div className="skeleton w-10 h-10 rounded-xl" /><div className="skeleton w-36 h-5 rounded" /></div><ListSkeleton rows={3} /></div>
          <div className="glass-card p-7"><div className="flex items-center gap-3 mb-5"><div className="skeleton w-10 h-10 rounded-xl" /><div className="skeleton w-36 h-5 rounded" /></div><ListSkeleton rows={3} /></div>
        </div>
        <div className="glass-card p-7"><div className="skeleton w-52 h-5 rounded mb-4" /><div className="skeleton w-full h-24 rounded-xl" /></div>
      </div>
    );
  }

  const {
    todays_events = [],
    tasks_today   = [],
    overdue_tasks = [],
  } = data || {};

  const stats = [
    { value: todays_events.length, label: 'Events Today',   icon: FiCalendar,    color: 'text-blue-400',    iconBg: 'bg-blue-500/10' },
    { value: tasks_today.length,   label: 'Tasks Due',      icon: FiCheckSquare, color: 'text-purple-400',  iconBg: 'bg-purple-500/10' },
    { value: overdue_tasks.length, label: 'Overdue',        icon: FiAlertCircle, color: overdue_tasks.length > 0 ? 'text-red-400' : 'text-slate-500', iconBg: 'bg-red-500/10' },
    {
      value: agenda?.estimated_productive_hours != null ? `${agenda.estimated_productive_hours}h` : '--',
      label: 'Focus Hours',
      icon: FiZap, color: 'text-emerald-400', iconBg: 'bg-emerald-500/10',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-4 gap-5">
        {stats.map((stat, i) => {
          const Icon = stat.icon;
          return (
            <div key={i} className={`stat-card group animate-fade-in-up-${i + 1}`}>
              <div className={`w-10 h-10 rounded-xl ${stat.iconBg} flex items-center justify-center mx-auto mb-3`}>
                <Icon className={stat.color} size={20} />
              </div>
              <p className={`text-3xl font-extrabold leading-none ${stat.color}`}>{stat.value}</p>
              <p className="stat-label">{stat.label}</p>
            </div>
          );
        })}
      </div>

      {/* Calendar + Tasks */}
      <div className="grid grid-cols-2 gap-6">
        {/* Today's Schedule */}
        <div className="glass-card p-7">
          <div className="section-header">
            <div className="section-header-icon bg-blue-500/10">
              <FiCalendar className="text-blue-400" size={18} />
            </div>
            <h3 className="font-bold text-white text-base flex-1">Today's Schedule</h3>
            <button onClick={handleAddEvent} className="text-xs bg-blue-500/20 hover:bg-blue-500/40 text-blue-400 py-1.5 px-3 rounded-lg font-medium transition-colors border border-blue-500/20">
              + New
            </button>
          </div>
          {todays_events.length > 0 ? (
            <div className="space-y-2">
              {todays_events.map((event) => (
                <AgendaItem key={event.id} item={event} type="event" />
              ))}
            </div>
          ) : (
            <EmptyState icon={FiCalendar} color="text-blue-400/50" message="No events today. Add one to get started." />
          )}
        </div>

        {/* Tasks Due Today */}
        <div className="glass-card p-7">
          <div className="section-header">
            <div className="section-header-icon bg-purple-500/10">
              <FiCheckSquare className="text-purple-400" size={18} />
            </div>
            <h3 className="font-bold text-white text-base flex-1">Tasks Due Today</h3>
            {overdue_tasks.length > 0 && (
              <span className="badge badge-danger mr-3">{overdue_tasks.length} overdue</span>
            )}
            <button onClick={handleAddTask} className="text-xs bg-purple-500/20 hover:bg-purple-500/40 text-purple-400 py-1.5 px-3 rounded-lg font-medium transition-colors border border-purple-500/20">
              + New
            </button>
          </div>
          {tasks_today.length > 0 || overdue_tasks.length > 0 ? (
            <div className="space-y-2">
              {overdue_tasks.map((task) => (
                <AgendaItem
                  key={`o-${task.id}`} item={task} type="overdue"
                  onComplete={completingTask === task.id ? null : handleCompleteTask}
                />
              ))}
              {tasks_today.map((task) => (
                <AgendaItem
                  key={`t-${task.id}`} item={task} type="task"
                  onComplete={completingTask === task.id ? null : handleCompleteTask}
                />
              ))}
            </div>
          ) : (
            <EmptyState icon={FiCheckSquare} color="text-purple-400/50" message="All caught up! Tasks will appear here when due." />
          )}
        </div>
      </div>

      {/* AI Daily Agenda */}
      <div className="glass-card p-7">
        <div className="section-header">
          <div className="section-header-icon bg-amber-500/10">
            <FiStar className="text-amber-400" size={18} />
          </div>
          <h3 className="font-bold text-white text-base">AI-Prioritized Daily Agenda</h3>
          <span className="badge badge-accent ml-2">AI Generated</span>
          <button
            onClick={loadAgenda}
            disabled={agendaLoading}
            className="ml-auto btn btn-ghost text-xs"
          >
            <FiRefreshCw size={12} className={agendaLoading ? 'animate-spin' : ''} />
            {agendaLoading ? 'Generating...' : 'Regenerate'}
          </button>
        </div>

        {agendaLoading ? (
          <div className="glass-inner p-5 space-y-3">
            <div className="skeleton w-2/5 h-4 rounded" />
            <div className="skeleton w-full h-3 rounded" />
            <div className="skeleton w-4/5 h-3 rounded" />
            <div className="skeleton w-2/5 h-4 rounded mt-2" />
            <div className="skeleton w-full h-3 rounded" />
          </div>
        ) : agenda ? (
          <div className="space-y-4">
            {/* Focus Areas */}
            {agenda.focus_areas?.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {agenda.focus_areas.map((area, i) => (
                  <span key={i} className="badge badge-accent">{area}</span>
                ))}
              </div>
            )}

            {/* Time Blocks */}
            {agenda.time_blocks?.length > 0 ? (
              <div className="space-y-2">
                {agenda.time_blocks.map((block, i) => (
                  <div key={i} className="glass-inner flex items-start gap-3 p-3">
                    <div className="text-xs font-mono text-slate-500 min-w-[90px] mt-0.5">
                      {block.start_time} – {block.end_time}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm text-white/90">{block.activity}</p>
                      {block.type && <span className="badge badge-info mt-1">{block.type}</span>}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="glass-inner p-5 text-sm text-slate-400 leading-relaxed whitespace-pre-line">
                {typeof agenda === 'string' ? agenda : JSON.stringify(agenda, null, 2)}
              </div>
            )}

            {/* Tips */}
            {agenda.tips?.length > 0 && (
              <div className="glass-inner p-4 border-amber-500/10 bg-amber-500/5">
                <p className="text-xs text-amber-400 font-semibold mb-2">AI Tips</p>
                <ul className="space-y-1">
                  {agenda.tips.map((tip, i) => (
                    <li key={i} className="text-xs text-slate-400">• {tip}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : todays_events.length === 0 && tasks_today.length === 0 && overdue_tasks.length === 0 ? (
          <EmptyState
            icon={FiSunrise} color="text-amber-400/50"
            message="Add events or tasks and the AI will generate a daily plan for you."
          />
        ) : (
          <div className="text-center py-8 text-slate-500 text-sm">
            Click "Regenerate" to generate your AI agenda.
          </div>
        )}
      </div>
    </div>
  );
}
