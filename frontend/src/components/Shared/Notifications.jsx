/**
 * Omura Notifications — Toast helpers and notification panel.
 */

import React from 'react';
import toast from 'react-hot-toast';
import { FiCheckCircle, FiAlertTriangle, FiAlertCircle, FiInfo, FiX } from 'react-icons/fi';

// ── Toast wrappers ──────────────────────────────────────────────────

export function notifySuccess(message) {
  toast.custom((t) => (
    <div className={`omura-toast ${t.visible ? 'animate-enter' : 'animate-leave'}`}>
      <FiCheckCircle className="text-emerald-400 flex-shrink-0" size={18} />
      <span className="flex-1">{message}</span>
      <button onClick={() => toast.dismiss(t.id)} className="text-slate-500 hover:text-white transition-colors ml-1">
        <FiX size={14} />
      </button>
    </div>
  ), { duration: 4000 });
}

export function notifyWarning(message) {
  toast.custom((t) => (
    <div className={`omura-toast ${t.visible ? 'animate-enter' : 'animate-leave'}`}>
      <FiAlertTriangle className="text-amber-400 flex-shrink-0" size={18} />
      <span className="flex-1">{message}</span>
      <button onClick={() => toast.dismiss(t.id)} className="text-slate-500 hover:text-white transition-colors ml-1">
        <FiX size={14} />
      </button>
    </div>
  ), { duration: 5000 });
}

export function notifyError(message) {
  toast.custom((t) => (
    <div className={`omura-toast border-red-500/20 ${t.visible ? 'animate-enter' : 'animate-leave'}`}>
      <FiAlertCircle className="text-red-400 flex-shrink-0" size={18} />
      <span className="flex-1">{message}</span>
      <button onClick={() => toast.dismiss(t.id)} className="text-slate-500 hover:text-white transition-colors ml-1">
        <FiX size={14} />
      </button>
    </div>
  ), { duration: 6000 });
}

export function notifyInfo(message) {
  toast.custom((t) => (
    <div className={`omura-toast ${t.visible ? 'animate-enter' : 'animate-leave'}`}>
      <FiInfo className="text-blue-400 flex-shrink-0" size={18} />
      <span className="flex-1">{message}</span>
      <button onClick={() => toast.dismiss(t.id)} className="text-slate-500 hover:text-white transition-colors ml-1">
        <FiX size={14} />
      </button>
    </div>
  ), { duration: 4000 });
}

// ── Notification Panel (dropdown from bell icon) ────────────────────

const PANEL_CLS = `min-w-[300px] max-w-[380px] rounded-3xl border border-white/[0.09]
  bg-[#0c0d12]/95 backdrop-blur-3xl
  shadow-[0_24px_64px_rgba(0,0,0,0.6),0_0_0_1px_rgba(255,255,255,0.04)]`;

export default function NotificationPanel({ notifications = [], onDismiss, onDismissAll }) {
  if (notifications.length === 0) {
    return (
      <div className={`${PANEL_CLS} p-6 text-center`}>
        <div className="w-10 h-10 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center mx-auto mb-3">
          <FiInfo className="text-slate-600" size={16} />
        </div>
        <p className="text-sm text-slate-500">No notifications</p>
        <p className="text-xs text-slate-600 mt-1">You're all caught up</p>
      </div>
    );
  }

  return (
    <div className={`${PANEL_CLS} overflow-hidden`}>
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
        <h3 className="text-sm font-semibold text-white">
          Notifications
          <span className="ml-2 text-xs bg-blue-500/20 text-blue-400 border border-blue-500/20 px-1.5 py-0.5 rounded-full">
            {notifications.length}
          </span>
        </h3>
        <button
          onClick={onDismissAll}
          className="text-xs text-slate-500 hover:text-white transition-colors"
        >
          Clear all
        </button>
      </div>
      <div className="max-h-96 overflow-y-auto divide-y divide-white/[0.04]">
        {notifications.map((notif, idx) => (
          <div key={idx} className="flex items-start gap-3 px-4 py-3 hover:bg-white/[0.03] transition-colors">
            <div className={`mt-0.5 flex-shrink-0 ${
              notif.type === 'success' ? 'text-emerald-400' :
              notif.type === 'warning' ? 'text-amber-400' :
              notif.type === 'error'   ? 'text-red-400'    : 'text-blue-400'
            }`}>
              {notif.type === 'success' ? <FiCheckCircle size={15} /> :
               notif.type === 'warning' ? <FiAlertTriangle size={15} /> :
               notif.type === 'error'   ? <FiAlertCircle size={15} /> :
               <FiInfo size={15} />}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-white/80">{notif.message}</p>
              {notif.time && <p className="text-xs text-slate-600 mt-0.5">{notif.time}</p>}
            </div>
            <button
              onClick={() => onDismiss(idx)}
              className="text-slate-600 hover:text-slate-400 transition-colors flex-shrink-0"
            >
              <FiX size={13} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
