/**
 * Omura Header — Premium glass header with search, notifications, user.
 */

import React, { useState, useRef, useEffect } from 'react';
import { FiSearch, FiBell, FiUser, FiRefreshCw } from 'react-icons/fi';
import NotificationPanel from './Notifications';

export default function Header({ title, notifications = [], onDismissNotification, onDismissAllNotifications, onSync, syncing }) {
  const [searchQuery, setSearchQuery]     = useState('');
  const [showNotifPanel, setShowNotifPanel] = useState(false);
  const notifRef = useRef(null);

  // Close panel on outside click
  useEffect(() => {
    if (!showNotifPanel) return;
    function handleClick(e) {
      if (notifRef.current && !notifRef.current.contains(e.target)) {
        setShowNotifPanel(false);
      }
    }
    // Use setTimeout so the click that opened the panel doesn't immediately close it
    const timer = setTimeout(() => document.addEventListener('mousedown', handleClick), 0);
    return () => { clearTimeout(timer); document.removeEventListener('mousedown', handleClick); };
  }, [showNotifPanel]);

  return (
    <header className="sticky top-0 z-40 bg-[#050507]/70 backdrop-blur-3xl">
      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-blue-500/25 to-transparent" />

      <div className="flex items-center justify-between px-8 py-5">
        {/* Title */}
        <div>
          <h2 className="text-2xl font-extrabold tracking-tight bg-gradient-to-r from-white to-white/70 bg-clip-text text-transparent">
            {title}
          </h2>
          <p className="text-xs text-slate-600 mt-0.5 font-medium">Welcome back, Damarley</p>
        </div>

        {/* Right controls */}
        <div className="flex items-center gap-3">
          {/* Search */}
          <div className="relative group">
            <FiSearch className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-600 group-focus-within:text-blue-400 transition-colors" size={15} />
            <input
              type="text"
              placeholder="Search Omura..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-white/[0.04] border border-white/[0.06] rounded-2xl pl-10 pr-4 py-2.5 w-72 text-sm
                text-white placeholder-slate-600 outline-none
                focus:border-blue-500/40 focus:bg-white/[0.06]
                focus:shadow-[0_0_0_3px_rgba(59,130,246,0.08),0_0_20px_rgba(59,130,246,0.06)]
                transition-all duration-300"
            />
          </div>

          {/* Sync */}
          <button
            onClick={onSync}
            className="w-10 h-10 flex items-center justify-center text-slate-500
              hover:text-blue-400 transition-all duration-300
              rounded-xl bg-white/[0.04] border border-white/[0.06]
              hover:border-blue-500/25 hover:bg-blue-500/[0.06]
              hover:shadow-[0_0_20px_rgba(59,130,246,0.12)]
              active:scale-95"
            title="Sync all data"
          >
            <FiRefreshCw size={15} className={syncing ? 'animate-spin text-blue-400' : ''} />
          </button>

          {/* Notifications bell */}
          <div className="relative" ref={notifRef}>
            <button
              onClick={() => setShowNotifPanel(v => !v)}
              className={`relative w-10 h-10 flex items-center justify-center transition-all duration-300
                rounded-xl bg-white/[0.04] border border-white/[0.06]
                hover:border-blue-500/25 hover:bg-blue-500/[0.06]
                active:scale-95 ${showNotifPanel ? 'text-blue-400 border-blue-500/25 bg-blue-500/[0.06]' : 'text-slate-500 hover:text-blue-400'}`}
              title="Notifications"
            >
              <FiBell size={15} />
              {notifications.length > 0 && (
                <span className="absolute -top-1.5 -right-1.5 w-5 h-5 flex items-center justify-center
                  text-[10px] font-bold text-white rounded-full
                  bg-gradient-to-br from-blue-500 to-purple-600
                  shadow-[0_0_12px_rgba(59,130,246,0.5)]
                  animate-pulse">
                  {notifications.length > 9 ? '9+' : notifications.length}
                </span>
              )}
            </button>

            {showNotifPanel && (
              <div className="absolute top-14 right-0 z-[9999]">
                <NotificationPanel
                  notifications={notifications}
                  onDismiss={(idx) => { onDismissNotification?.(idx); }}
                  onDismissAll={() => { onDismissAllNotifications?.(); setShowNotifPanel(false); }}
                />
              </div>
            )}
          </div>

          {/* Divider */}
          <div className="w-px h-8 bg-gradient-to-b from-transparent via-white/[0.08] to-transparent mx-1" />

          {/* User */}
          <div className="flex items-center gap-3 group cursor-pointer">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 via-purple-500 to-pink-500 flex items-center justify-center
              shadow-[0_0_16px_rgba(59,130,246,0.2)]
              group-hover:shadow-[0_0_24px_rgba(59,130,246,0.3)]
              transition-all duration-300">
              <FiUser size={15} className="text-white" />
            </div>
            <div>
              <p className="text-sm font-bold text-white">Damarley</p>
              <p className="text-[10px] text-slate-600 font-medium">Admin</p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
