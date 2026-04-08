/**
 * Omura Sidebar — Premium glassmorphism navigation.
 */

import React from 'react';
import {
  FiHome, FiBriefcase, FiEdit3, FiMessageSquare,
  FiBook, FiCpu, FiTrendingUp, FiSettings, FiLogOut,
  FiActivity, FiMessageCircle, FiTarget
} from 'react-icons/fi';
import { logout } from '../../services/authService';

const NAV_ITEMS = [
  { id: 'life',          label: 'Life Overview',       icon: FiHome },
  { id: 'business',      label: 'Business Command',    icon: FiBriefcase },
  { id: 'content',       label: 'Content Studio',      icon: FiEdit3 },
  { id: 'communication', label: 'Communication',       icon: FiMessageSquare },
  { id: 'knowledge',     label: 'Knowledge Hub',       icon: FiBook },
  { id: 'automation',    label: 'Automation Control',   icon: FiCpu },
  { id: 'outreach',      label: 'Outreach Pipeline',    icon: FiTarget },
  { id: 'scenarios',     label: 'Scenario Simulator',   icon: FiTrendingUp },
  { id: 'health',        label: 'Health & Fitness',     icon: FiActivity },
  { id: 'chat',          label: 'AI Chat',              icon: FiMessageCircle },
];

export default function Sidebar({ activeSection, onNavigate }) {
  return (
    <aside className="fixed left-0 top-0 h-screen w-72 z-50 flex flex-col
      bg-[#060709]/90 backdrop-blur-3xl border-r border-white/[0.06]">

      {/* Logo */}
      <div className="px-7 pt-8 pb-6">
        <div className="flex items-center gap-3.5">
          <div className="relative">
            <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-blue-500 via-purple-500 to-pink-500 flex items-center justify-center
              shadow-[0_0_20px_rgba(59,130,246,0.3),0_0_40px_rgba(124,58,237,0.15)]">
              <span className="text-white font-black text-lg tracking-tight">O</span>
            </div>
            <div className="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full bg-emerald-400 border-2 border-[#060709]
              shadow-[0_0_8px_rgba(52,211,153,0.5)]" />
          </div>
          <div>
            <h1 className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-white to-white/70 bg-clip-text text-transparent">
              Omura
            </h1>
            <p className="text-[10px] text-slate-500 tracking-[0.2em] uppercase font-medium">Life Operating System</p>
          </div>
        </div>
        {/* Gradient divider */}
        <div className="mt-7 h-px bg-gradient-to-r from-transparent via-blue-500/30 to-transparent" />
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-4 pb-4">
        <p className="text-[10px] text-slate-600 uppercase tracking-[0.2em] font-semibold px-3 mb-3">Dashboard</p>
        <div className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = activeSection === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={`w-full flex items-center gap-3.5 px-4 py-3 rounded-2xl text-[13px] font-medium
                  transition-all duration-300 group relative
                  ${isActive
                    ? 'bg-gradient-to-r from-blue-500/[0.12] to-purple-500/[0.06] text-white border border-blue-500/20 shadow-[0_0_20px_rgba(59,130,246,0.08)]'
                    : 'text-slate-500 hover:text-slate-200 hover:bg-white/[0.04] border border-transparent'
                  }`}
              >
                {/* Active bar indicator */}
                {isActive && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-8 rounded-r-full
                    bg-gradient-to-b from-blue-400 to-purple-500
                    shadow-[0_0_8px_rgba(59,130,246,0.5)]" />
                )}
                <div className={`w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-300
                  ${isActive
                    ? 'bg-gradient-to-br from-blue-500/25 to-purple-500/20 shadow-[0_0_12px_rgba(59,130,246,0.15)]'
                    : 'bg-white/[0.03] group-hover:bg-white/[0.07]'
                  }`}>
                  <Icon size={17} className={`transition-colors duration-300 ${
                    isActive ? 'text-blue-400' : 'text-slate-500 group-hover:text-slate-300'
                  }`} />
                </div>
                <span className="flex-1 text-left">{item.label}</span>
                {isActive && (
                  <div className="w-1.5 h-1.5 rounded-full bg-blue-400
                    shadow-[0_0_6px_rgba(59,130,246,0.8),0_0_12px_rgba(59,130,246,0.4)]
                    animate-pulse" />
                )}
              </button>
            );
          })}
        </div>
      </nav>

      {/* Bottom actions */}
      <div className="px-4 pb-6">
        <div className="h-px bg-gradient-to-r from-transparent via-white/[0.08] to-transparent mb-4" />
        <div className="space-y-1">
          <button
            onClick={() => onNavigate('settings')}
            className="w-full flex items-center gap-3.5 px-4 py-3 rounded-2xl text-[13px] text-slate-500
              hover:text-slate-200 hover:bg-white/[0.04] transition-all duration-300 group"
          >
            <div className="w-9 h-9 rounded-xl bg-white/[0.03] group-hover:bg-white/[0.07] flex items-center justify-center transition-all">
              <FiSettings size={17} className="text-slate-500 group-hover:text-slate-300" />
            </div>
            Settings
          </button>
          <button
            onClick={logout}
            className="w-full flex items-center gap-3.5 px-4 py-3 rounded-2xl text-[13px] text-red-500/40
              hover:text-red-400 hover:bg-red-500/[0.05] transition-all duration-300 group"
          >
            <div className="w-9 h-9 rounded-xl bg-white/[0.03] group-hover:bg-red-500/[0.1] flex items-center justify-center transition-all">
              <FiLogOut size={17} />
            </div>
            Logout
          </button>
        </div>
      </div>
    </aside>
  );
}
