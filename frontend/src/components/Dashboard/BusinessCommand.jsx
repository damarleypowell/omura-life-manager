/**
 * Business Command — Projects, revenue, KPIs, AI agent logs.
 * Cryptix / Dreelio dark glassmorphism theme.
 */

import React, { useState, useEffect } from 'react';
import { FiBriefcase, FiDollarSign, FiTrendingUp, FiUsers, FiActivity } from 'react-icons/fi';
import { dashboard, leads as leadsApi, projects as projectsApi } from '../../services/apiService';

function KPICard({ label, value, change, icon: Icon, color, bgColor, borderColor, animClass }) {
  const isPositive = change != null && change >= 0;
  const hasChange = change != null;

  return (
    <div className={`stat-card group hover-glow-blue ${animClass || ''}`}>
      <div className="flex items-center justify-between mb-4">
        <div className={`p-3 rounded-xl ${bgColor || 'bg-blue-500/10'} border ${borderColor || 'border-blue-500/20'}
          group-hover:scale-110 transition-transform duration-300`}>
          <Icon className={color} size={20} />
        </div>
        {hasChange && (
          <span className={`text-xs font-semibold px-2.5 py-1 rounded-full
            ${isPositive
              ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20'
              : 'bg-red-500/15 text-red-400 border border-red-500/20'
            }`}>
            {isPositive ? '+' : ''}{change}%
          </span>
        )}
      </div>
      <p className={`stat-value text-2xl font-extrabold bg-clip-text text-transparent
        bg-gradient-to-br from-white to-white/60`}>
        {value}
      </p>
      <p className="stat-label text-xs text-slate-500 mt-1.5 tracking-wide uppercase">{label}</p>
    </div>
  );
}

function ProjectRow({ project }) {
  const statusColors = {
    todo: 'badge-info',
    in_progress: 'badge-accent',
    blocked: 'badge-danger',
    done: 'badge-success',
  };

  return (
    <div className="flex items-center gap-4 p-4 rounded-[14px] glass-inner group
      hover:bg-white/[0.04] transition-all duration-300">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-white/90 truncate group-hover:text-white transition-colors duration-300">
          {project.name}
        </p>
        <p className="text-xs text-slate-500 mt-1">{project.deadline || 'No deadline'}</p>
      </div>
      <div className="w-32">
        <div className="h-2 bg-white/5 rounded-full overflow-hidden">
          <div
            className="h-2 rounded-full gradient-blue-purple transition-all duration-700 ease-out"
            style={{ width: `${project.progress_pct || 0}%` }}
          />
        </div>
        <p className="text-[11px] text-slate-500 mt-1.5 text-right font-medium">
          {Math.round(project.progress_pct || 0)}%
        </p>
      </div>
      <span className={`badge ${statusColors[project.status] || 'badge-info'}`}>
        {(project.status || 'todo').replace('_', ' ')}
      </span>
    </div>
  );
}

export default function BusinessCommand() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [followingUp, setFollowingUp] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const result = await dashboard.getBusinessCommand();
      setData(result);
    } catch (err) {
      console.error('Failed to load business command:', err);
      setData({
        active_projects: [],
        kpis: {},
        hot_leads: [],
        recent_agent_logs: [],
      });
    } finally {
      setLoading(false);
    }
  }

  async function handleFollowUp(lead) {
    setFollowingUp(lead.id);
    try {
      // Schedule a follow-up date only. (There is no 'follow_up' LeadStatus —
      // sending one 500s; valid statuses are new/contacted/qualified/proposal/won/lost/invalid.)
      await leadsApi.update(lead.id, { next_followup: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString() });
      await loadData();
    } catch (e) { console.error('Failed to schedule follow-up:', e); } finally { setFollowingUp(null); }
  }

  async function handleAddProject() {
    const name = window.prompt("Enter new project name:");
    if (!name?.trim()) return;
    try {
      await projectsApi.create({ name: name.trim() });
      await loadData();
    } catch (err) {
      console.error("Failed to create project", err);
    }
  }

  async function handleAddLead() {
    const name = window.prompt("Enter new lead name:");
    if (!name?.trim()) return;
    try {
      await leadsApi.create({ name: name.trim() });
      await loadData();
    } catch (err) {
      console.error("Failed to create lead", err);
    }
  }

  if (loading) {
    return (
      <div className="space-y-5 animate-fade-in">
        {/* Skeleton KPI cards */}
        <div className="grid grid-cols-4 gap-5">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className={`stat-card animate-fade-in-up-${i}`}>
              <div className="flex items-center justify-between mb-4">
                <div className="skeleton w-11 h-11 rounded-xl" />
                <div className="skeleton w-14 h-6 rounded-full" />
              </div>
              <div className="skeleton w-20 h-7 rounded-lg mb-2" />
              <div className="skeleton w-24 h-3 rounded" />
            </div>
          ))}
        </div>
        {/* Skeleton content cards */}
        <div className="grid grid-cols-2 gap-5">
          {[1, 2].map((i) => (
            <div key={i} className="glass-card p-7">
              <div className="flex items-center gap-3 mb-5">
                <div className="skeleton w-10 h-10 rounded-xl" />
                <div className="skeleton w-32 h-5 rounded-lg" />
              </div>
              <div className="space-y-3">
                {[1, 2, 3].map((j) => (
                  <div key={j} className="skeleton w-full h-16 rounded-[14px]" />
                ))}
              </div>
            </div>
          ))}
        </div>
        {/* Skeleton agent activity */}
        <div className="glass-card p-7">
          <div className="flex items-center gap-3 mb-5">
            <div className="skeleton w-10 h-10 rounded-xl" />
            <div className="skeleton w-48 h-5 rounded-lg" />
          </div>
          <div className="skeleton w-full h-20 rounded-[14px]" />
        </div>
      </div>
    );
  }

  const {
    active_projects = [],
    kpis = {},
    hot_leads = [],
    recent_agent_logs = [],
  } = data || {};

  const kpiCards = [
    {
      label: 'Monthly Revenue',
      value: kpis.monthly_revenue != null ? `$${kpis.monthly_revenue.toLocaleString()}` : '--',
      change: kpis.revenue_change ?? null,
      icon: FiDollarSign,
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/10',
      borderColor: 'border-emerald-500/20',
    },
    {
      label: 'Active Projects',
      value: active_projects.length,
      change: kpis.projects_change ?? null,
      icon: FiBriefcase,
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/10',
      borderColor: 'border-blue-500/20',
    },
    {
      label: 'Conversion Rate',
      value: kpis.conversion_rate != null ? `${kpis.conversion_rate}%` : '--',
      change: kpis.conversion_change ?? null,
      icon: FiTrendingUp,
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/10',
      borderColor: 'border-purple-500/20',
    },
    {
      label: 'Hot Leads',
      value: hot_leads.length,
      change: kpis.leads_change ?? null,
      icon: FiUsers,
      color: 'text-amber-400',
      bgColor: 'bg-amber-500/10',
      borderColor: 'border-amber-500/20',
    },
  ];

  return (
    <div className="space-y-5 animate-fade-in">
      {/* KPI Row */}
      <div className="grid grid-cols-4 gap-5">
        {kpiCards.map((kpi, i) => (
          <KPICard
            key={i}
            label={kpi.label}
            value={kpi.value}
            change={kpi.change}
            icon={kpi.icon}
            color={kpi.color}
            bgColor={kpi.bgColor}
            borderColor={kpi.borderColor}
            animClass={`animate-fade-in-up-${i + 1}`}
          />
        ))}
      </div>

      <div className="grid grid-cols-2 gap-5">
        {/* Active Projects */}
        <div className="glass-card p-7 animate-fade-in-up-1" style={{ borderRadius: 20 }}>
          <div className="section-header flex items-center gap-3 mb-5">
            <div className="section-header-icon p-3 rounded-xl bg-blue-500/10 border border-blue-500/20">
              <FiBriefcase className="text-blue-400" size={18} />
            </div>
            <h3 className="font-semibold text-white text-base flex-1">Active Projects</h3>
            {active_projects.length > 0 && (
              <span className="text-xs text-slate-500 font-medium mr-3">
                {active_projects.length} project{active_projects.length !== 1 ? 's' : ''}
              </span>
            )}
            <button onClick={handleAddProject} className="text-xs bg-blue-500/20 hover:bg-blue-500/40 text-blue-400 py-1.5 px-3 rounded-lg font-medium transition-colors border border-blue-500/20">
              + New
            </button>
          </div>
          <div className="space-y-2.5">
            {active_projects.length > 0 ? (
              active_projects.map((p) => <ProjectRow key={p.id} project={p} />)
            ) : (
              <div className="empty-state py-10 text-center">
                <div className="empty-state-icon mx-auto mb-4 w-14 h-14 rounded-2xl bg-blue-500/10
                  border border-blue-500/20 flex items-center justify-center">
                  <FiBriefcase className="text-blue-400/60" size={22} />
                </div>
                <p className="text-sm font-medium text-slate-400">No active projects</p>
                <p className="text-xs text-slate-600 mt-1">Projects will appear here once created</p>
              </div>
            )}
          </div>
        </div>

        {/* Hot Leads */}
        <div className="glass-card p-7 animate-fade-in-up-2" style={{ borderRadius: 20 }}>
          <div className="section-header flex items-center gap-3 mb-5">
            <div className="section-header-icon p-3 rounded-xl bg-amber-500/10 border border-amber-500/20">
              <FiUsers className="text-amber-400" size={18} />
            </div>
            <h3 className="font-semibold text-white text-base flex-1">Hot Leads</h3>
            {hot_leads.length > 0 && (
              <span className="text-xs text-slate-500 font-medium mr-3">
                {hot_leads.length} lead{hot_leads.length !== 1 ? 's' : ''}
              </span>
            )}
            <button onClick={handleAddLead} className="text-xs bg-amber-500/20 hover:bg-amber-500/40 text-amber-400 py-1.5 px-3 rounded-lg font-medium transition-colors border border-amber-500/20">
              + New
            </button>
          </div>
          <div className="space-y-2.5">
            {hot_leads.length > 0 ? (
              hot_leads.map((lead) => (
                <div key={lead.id} className="flex items-center gap-4 p-4 rounded-[14px] glass-inner group
                  hover:bg-white/[0.04] transition-all duration-300">
                  <div className="w-11 h-11 rounded-xl bg-amber-500/15 border border-amber-500/20
                    flex items-center justify-center text-amber-400 text-xs font-bold
                    group-hover:scale-110 transition-transform duration-300">
                    {lead.score}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-white/90 truncate group-hover:text-white transition-colors duration-300">
                      {lead.name}
                    </p>
                    <p className="text-xs text-slate-500 capitalize mt-0.5">{lead.status}</p>
                  </div>
                  <button
                    onClick={() => handleFollowUp(lead)}
                    disabled={followingUp === lead.id}
                    className="btn btn-ghost text-xs"
                  >
                    {followingUp === lead.id ? 'Saving...' : 'Follow up'}
                  </button>
                </div>
              ))
            ) : (
              <div className="empty-state py-10 text-center">
                <div className="empty-state-icon mx-auto mb-4 w-14 h-14 rounded-2xl bg-amber-500/10
                  border border-amber-500/20 flex items-center justify-center">
                  <FiUsers className="text-amber-400/60" size={22} />
                </div>
                <p className="text-sm font-medium text-slate-400">No hot leads</p>
                <p className="text-xs text-slate-600 mt-1">Leads with high scores will show up here</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Recent AI Agent Activity */}
      <div className="glass-card p-7 animate-fade-in-up-3" style={{ borderRadius: 20 }}>
        <div className="section-header flex items-center gap-3 mb-5">
          <div className="section-header-icon p-3 rounded-xl bg-purple-500/10 border border-purple-500/20">
            <FiActivity className="text-purple-400" size={18} />
          </div>
          <h3 className="font-semibold text-white text-base">Recent AI Agent Activity</h3>
        </div>
        {recent_agent_logs.length > 0 ? (
          <div className="space-y-1 text-sm">
            {recent_agent_logs.map((log, i) => (
              <div key={i} className="flex items-center gap-4 py-3.5 border-b border-white/[0.05] last:border-0
                hover:bg-white/[0.02] transition-colors duration-200 rounded-lg px-2">
                <span className="badge badge-accent">{log.agent_name}</span>
                <span className="text-slate-400 flex-1">{log.action}</span>
                <span className="text-xs text-slate-600 font-medium">{log.created_at}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state py-10 text-center">
            <div className="empty-state-icon mx-auto mb-4 w-14 h-14 rounded-2xl bg-purple-500/10
              border border-purple-500/20 flex items-center justify-center">
              <FiActivity className="text-purple-400/60" size={22} />
            </div>
            <p className="text-sm font-medium text-slate-400">No recent agent activity</p>
            <p className="text-xs text-slate-600 mt-1">AI agents will log actions here as they work</p>
          </div>
        )}
      </div>
    </div>
  );
}
